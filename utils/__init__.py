"""
Utilities module for BlendPro: AI Co-Pilot
Common utility functions and classes
"""

from .api_client import APIClient, APIError
from .backup_manager import BackupManager, BackupError
from .code_executor import CodeExecutor, CodeExecutionError
from .file_manager import FileManager, init_props, clear_props
from .dependency_loader import (
    DependencyLoader, DependencyError, get_dependency_loader,
    safe_import, require_package, is_available, get_import_status, clear_dependency_cache
)

__all__ = [
    'APIClient',
    'APIError',
    'BackupManager',
    'BackupError',
    'CodeExecutor',
    'CodeExecutionError',
    'FileManager',
    'init_props',
    'clear_props',
    'DependencyLoader',
    'DependencyError',
    'get_dependency_loader',
    'safe_import',
    'require_package',
    'is_available',
    'get_import_status',
    'clear_dependency_cache'
]
