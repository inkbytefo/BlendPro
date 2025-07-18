"""
Dependency Loader for BlendPro: AI Co-Pilot
Centralized dependency management system with graceful fallbacks and comprehensive error handling

Author: inkbytefo
"""

import sys
import os
import importlib
import threading
import logging
from typing import Dict, Any, Optional, Union, Tuple, List
from pathlib import Path
import warnings

# Configure logging
logger = logging.getLogger(__name__)

class DependencyError(Exception):
    """Custom exception for dependency-related errors"""
    pass

class DependencyLoader:
    """
    Centralized dependency management system for BlendPro
    
    Features:
    - Safe import with fallback handling
    - Version compatibility checking
    - Lazy loading with caching
    - Thread-safe operations
    - Comprehensive logging
    - Graceful degradation for optional packages
    """
    
    def __init__(self):
        self._imported_modules: Dict[str, Any] = {}
        self._failed_imports: Dict[str, str] = {}
        self._feature_flags: Dict[str, bool] = {}
        self._lock = threading.RLock()
        self._lib_path_added = False
        
        # Initialize lib path
        self._ensure_lib_path()
    
    def _ensure_lib_path(self) -> None:
        """Add lib/ directory to sys.path safely without duplicates"""
        with self._lock:
            if self._lib_path_added:
                return
                
            try:
                # Get the addon directory (parent of utils)
                addon_dir = Path(__file__).parent.parent
                lib_dir = addon_dir / "lib"
                
                if lib_dir.exists():
                    lib_path_str = str(lib_dir)
                    
                    # Add to sys.path if not already present
                    if lib_path_str not in sys.path:
                        sys.path.insert(0, lib_path_str)
                        logger.info(f"Added lib directory to sys.path: {lib_path_str}")
                    
                    self._lib_path_added = True
                else:
                    logger.warning(f"Lib directory not found: {lib_dir}")
                    
            except Exception as e:
                logger.error(f"Failed to add lib directory to sys.path: {e}")
    
    def _parse_version(self, version_str: str) -> Tuple[int, ...]:
        """Parse version string into tuple of integers for comparison"""
        try:
            # Handle common version formats: "1.2.3", "1.2.3.dev0", "1.2.3a1"
            import re
            version_clean = re.match(r'^(\d+(?:\.\d+)*)', version_str)
            if version_clean:
                return tuple(map(int, version_clean.group(1).split('.')))
            return (0,)
        except Exception:
            return (0,)
    
    def _check_version_compatibility(self, package_name: str, module: Any, min_version: Optional[str] = None) -> bool:
        """Check if imported module meets minimum version requirements"""
        if not min_version:
            return True
            
        try:
            # Try common version attributes
            version_attrs = ['__version__', 'version', 'VERSION', '_version']
            module_version = None
            
            for attr in version_attrs:
                if hasattr(module, attr):
                    version_val = getattr(module, attr)
                    if isinstance(version_val, str):
                        module_version = version_val
                        break
                    elif hasattr(version_val, '__version__'):
                        module_version = version_val.__version__
                        break
            
            if not module_version:
                logger.warning(f"Could not determine version for {package_name}")
                return True  # Assume compatible if version cannot be determined
            
            # Compare versions
            current_version = self._parse_version(module_version)
            required_version = self._parse_version(min_version)
            
            is_compatible = current_version >= required_version
            
            if not is_compatible:
                logger.warning(
                    f"{package_name} version {module_version} is below minimum required {min_version}"
                )
            else:
                logger.debug(f"{package_name} version {module_version} meets requirement {min_version}")
            
            return is_compatible
            
        except Exception as e:
            logger.warning(f"Version check failed for {package_name}: {e}")
            return True  # Assume compatible on version check failure
    
    def safe_import(self, package_name: str, display_name: Optional[str] = None, 
                   required: bool = False, min_version: Optional[str] = None) -> Optional[Any]:
        """
        Safely import a package with comprehensive error handling
        
        Args:
            package_name: Name of the package to import (e.g., 'PIL', 'numpy')
            display_name: Human-readable name for error messages (e.g., 'Pillow (Image Processing)')
            required: Whether this package is required for core functionality
            min_version: Minimum version requirement (e.g., '1.0.0')
        
        Returns:
            Imported module or None if import failed and not required
            
        Raises:
            DependencyError: If required package cannot be imported or version is incompatible
        """
        with self._lock:
            # Check cache first
            if package_name in self._imported_modules:
                return self._imported_modules[package_name]
            
            # Check if import previously failed
            if package_name in self._failed_imports:
                if required:
                    raise DependencyError(self._failed_imports[package_name])
                return None
            
            display_name = display_name or package_name
            
            try:
                logger.debug(f"Attempting to import {package_name}")
                
                # Import the module
                module = importlib.import_module(package_name)
                
                # Check version compatibility
                if not self._check_version_compatibility(package_name, module, min_version):
                    error_msg = f"{display_name} version is incompatible (required: {min_version})"
                    if required:
                        raise DependencyError(error_msg)
                    else:
                        logger.warning(error_msg)
                        self._failed_imports[package_name] = error_msg
                        return None
                
                # Cache successful import
                self._imported_modules[package_name] = module
                self._feature_flags[package_name] = True
                
                logger.info(f"Successfully imported {display_name}")
                return module
                
            except ImportError as e:
                error_msg = f"{display_name} not available: {str(e)}"
                logger.warning(error_msg)
                
                # Cache failed import
                self._failed_imports[package_name] = error_msg
                self._feature_flags[package_name] = False
                
                if required:
                    detailed_error = (
                        f"Required dependency '{display_name}' could not be imported.\n"
                        f"Error: {str(e)}\n"
                        f"Please install it using: pip install {package_name}"
                    )
                    raise DependencyError(detailed_error)
                
                return None
                
            except Exception as e:
                error_msg = f"Unexpected error importing {display_name}: {str(e)}"
                logger.error(error_msg)
                
                self._failed_imports[package_name] = error_msg
                self._feature_flags[package_name] = False
                
                if required:
                    raise DependencyError(error_msg)
                
                return None
    
    def require_package(self, package_name: str, display_name: str, 
                       min_version: Optional[str] = None) -> Any:
        """
        Import a required package, raising DependencyError if unavailable
        
        Args:
            package_name: Name of the package to import
            display_name: Human-readable name for error messages
            min_version: Minimum version requirement
            
        Returns:
            Imported module
            
        Raises:
            DependencyError: If package cannot be imported or version is incompatible
        """
        return self.safe_import(package_name, display_name, required=True, min_version=min_version)
    
    def is_available(self, package_name: str) -> bool:
        """Check if a package is available (cached result)"""
        with self._lock:
            if package_name in self._feature_flags:
                return self._feature_flags[package_name]
            
            # Try importing if not cached
            result = self.safe_import(package_name, required=False)
            return result is not None
    
    def get_import_status(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive status of all import attempts"""
        with self._lock:
            status = {
                "successful_imports": {},
                "failed_imports": dict(self._failed_imports),
                "feature_flags": dict(self._feature_flags)
            }
            
            for package_name, module in self._imported_modules.items():
                version = "unknown"
                try:
                    if hasattr(module, '__version__'):
                        version = module.__version__
                    elif hasattr(module, 'version'):
                        version = str(module.version)
                except:
                    pass
                
                status["successful_imports"][package_name] = {
                    "version": version,
                    "module_path": getattr(module, '__file__', 'built-in')
                }
            
            return status
    
    def clear_cache(self) -> None:
        """Clear all cached imports and status"""
        with self._lock:
            self._imported_modules.clear()
            self._failed_imports.clear()
            self._feature_flags.clear()
            logger.info("Dependency cache cleared")

# Global instance
_dependency_loader = None
_loader_lock = threading.Lock()

def get_dependency_loader() -> DependencyLoader:
    """Get the global dependency loader instance (thread-safe singleton)"""
    global _dependency_loader
    
    if _dependency_loader is None:
        with _loader_lock:
            if _dependency_loader is None:
                _dependency_loader = DependencyLoader()
    
    return _dependency_loader

# Convenience functions for common usage patterns
def safe_import(package_name: str, display_name: Optional[str] = None, 
               required: bool = False, min_version: Optional[str] = None) -> Optional[Any]:
    """Convenience function for safe package import"""
    return get_dependency_loader().safe_import(package_name, display_name, required, min_version)

def require_package(package_name: str, display_name: str, 
                   min_version: Optional[str] = None) -> Any:
    """Convenience function for required package import"""
    return get_dependency_loader().require_package(package_name, display_name, min_version)

def is_available(package_name: str) -> bool:
    """Convenience function to check package availability"""
    return get_dependency_loader().is_available(package_name)

def get_import_status() -> Dict[str, Dict[str, Any]]:
    """Convenience function to get import status"""
    return get_dependency_loader().get_import_status()

def clear_dependency_cache() -> None:
    """Convenience function to clear dependency cache"""
    get_dependency_loader().clear_cache()
