"""
Initialization utilities for BlendPro: AI Co-Pilot
Handles proper initialization of settings and API clients
"""

import bpy
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def initialize_blendpro() -> Dict[str, Any]:
    """
    Initialize BlendPro with current addon preferences
    
    Returns:
        Dict with initialization status and any errors
    """
    try:
        # Get addon preferences
        addon_name = __package__.split('.')[0]
        if addon_name not in bpy.context.preferences.addons:
            return {
                "success": False,
                "error": f"Addon {addon_name} is not enabled",
                "step": "addon_check"
            }
        
        addon_prefs = bpy.context.preferences.addons[addon_name].preferences
        
        # Sync settings with preferences
        from ..config.settings import sync_from_preferences, get_settings
        sync_from_preferences(addon_prefs)
        
        settings = get_settings()
        
        # Validate API configuration
        if not settings.api_key:
            return {
                "success": False,
                "error": "No API key configured. Please set your OpenAI API key in addon preferences.",
                "step": "api_key_check"
            }
        
        # Initialize API client
        from ..utils.api_client import get_api_client
        api_client = get_api_client()
        
        # Test API connection
        test_result = api_client.test_connection()
        if not test_result["success"]:
            return {
                "success": False,
                "error": f"API connection failed: {test_result.get('error', 'Unknown error')}",
                "step": "api_test"
            }
        
        return {
            "success": True,
            "message": "BlendPro initialized successfully",
            "api_model": test_result.get("model", "unknown"),
            "settings": {
                "api_configured": bool(settings.api_key),
                "vision_enabled": settings.enable_vision_context,
                "monitoring_enabled": settings.enable_scene_monitoring,
                "caching_enabled": settings.enable_caching
            }
        }
        
    except Exception as e:
        logger.exception("Failed to initialize BlendPro")
        return {
            "success": False,
            "error": f"Initialization failed: {str(e)}",
            "step": "exception"
        }

def check_dependencies() -> Dict[str, Any]:
    """
    Check if all required dependencies are available
    
    Returns:
        Dict with dependency status
    """
    missing_deps = []
    available_deps = []
    
    # Check core dependencies
    dependencies = [
        ("openai", "OpenAI API Client"),
        ("PIL", "Pillow (Image Processing)"),
        ("numpy", "NumPy (Numerical Computing)"),
        ("requests", "Requests (HTTP Library)"),
        ("json5", "JSON5 Parser")
    ]
    
    for package, display_name in dependencies:
        try:
            __import__(package)
            available_deps.append(display_name)
        except ImportError:
            missing_deps.append(display_name)
    
    return {
        "success": len(missing_deps) == 0,
        "available": available_deps,
        "missing": missing_deps,
        "total": len(dependencies)
    }

def get_initialization_status() -> Dict[str, Any]:
    """
    Get current initialization status without re-initializing
    
    Returns:
        Dict with current status
    """
    try:
        from ..config.settings import get_settings
        from ..utils.api_client import get_api_client
        
        settings = get_settings()
        api_client = get_api_client()
        
        return {
            "initialized": True,
            "api_configured": bool(settings.api_key),
            "cache_stats": api_client.get_cache_stats(),
            "settings_summary": {
                "temperature": settings.temperature,
                "max_tokens": settings.max_tokens,
                "vision_enabled": settings.enable_vision_context,
                "monitoring_enabled": settings.enable_scene_monitoring
            }
        }
        
    except Exception as e:
        return {
            "initialized": False,
            "error": str(e)
        }

def force_reinitialize() -> Dict[str, Any]:
    """
    Force re-initialization of all BlendPro components
    
    Returns:
        Dict with re-initialization status
    """
    try:
        # Clear existing instances
        from ..config.settings import reset_settings
        reset_settings()
        
        # Clear API client cache
        from ..utils.api_client import get_api_client
        api_client = get_api_client()
        api_client.clear_cache()
        
        # Re-initialize
        return initialize_blendpro()
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Force re-initialization failed: {str(e)}"
        }
