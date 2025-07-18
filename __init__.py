"""
BlendPro: AI Co-Pilot for Blender
Advanced AI assistant with multi-modal capabilities, proactive suggestions, and intelligent workflow optimization

Author: inkbytefo
Version: 2.0.0
"""

bl_info = {
    "name": "BlendPro: AI Co-Pilot",
    "author": "inkbytefo",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar > BlendPro",
    "description": "Advanced AI assistant with multi-modal capabilities, proactive suggestions, and intelligent workflow optimization",
    "warning": "Requires OpenAI API key",
    "doc_url": "https://github.com/inkbytefo/BlendPro",
    "category": "3D View",
}

import bpy
import sys
import importlib
import traceback
from pathlib import Path
from typing import List, Any

# Add lib directory to Python path
addon_dir = Path(__file__).parent
lib_dir = addon_dir / "lib"
if lib_dir.exists() and str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

# Module registration order (important for dependencies)
# Only include modules that have register() functions
MODULE_REGISTRATION_ORDER = [
    # Core utilities first
    "utils.file_manager",
    "utils.api_client",
    "utils.backup_manager",
    "utils.code_executor",

    # Core AI functionality
    "core.conversation_memory",
    "core.task_classifier",
    "core.clarification_system",
    "core.multi_step_planner",
    "core.interaction_engine",

    # Vision system
    "vision.scene_analyzer",
    "vision.context_extractor",
    "vision.screenshot_manager",
    "vision.multi_modal_vision",

    # Workflow system
    "workflow.scene_monitor",
    "workflow.proactive_suggestions",
    "workflow.action_library",
    "workflow.auto_fix_system",

    # UI components last - main panel first, then sub-panels
    "ui.main_panel",
    "ui.settings_panel",
    "ui.interactive_messages",
    "ui.chat_interface",
    "ui.response_popup",
]

# Global module registry
_registered_modules = []

# Global timer reference for cleanup
_chat_history_timer = None

def _import_module(module_name: str):
    """Import a module with error handling"""
    try:
        full_module_name = f"{__name__}.{module_name}"

        # Import or reload module
        if full_module_name in sys.modules:
            importlib.reload(sys.modules[full_module_name])
        else:
            importlib.import_module(full_module_name)

        return sys.modules[full_module_name]

    except Exception as e:
        print(f"BlendPro: Failed to import {module_name}: {e}")
        traceback.print_exc()
        return None

def _register_module(module):
    """Register a module if it has register function"""
    if module and hasattr(module, 'register') and callable(module.register):
        try:
            module.register()
            return True
        except Exception as e:
            print(f"BlendPro: Failed to register {module.__name__}: {e}")
            traceback.print_exc()
            return False
    else:
        # Modülün register fonksiyonu yoksa sessizce geç
        return True

def _unregister_module(module):
    """Unregister a module if it has unregister function"""
    if module and hasattr(module, 'unregister'):
        try:
            module.unregister()
            return True
        except Exception as e:
            print(f"BlendPro: Failed to unregister {module.__name__}: {e}")
            return False
    return False

def register():
    """Register all BlendPro modules and components"""
    global _registered_modules

    print("BlendPro: Starting registration...")

    # Clear any existing registrations
    _registered_modules.clear()

    # Register modules in order
    for module_name in MODULE_REGISTRATION_ORDER:
        print(f"BlendPro: Registering {module_name}...")

        # Import module
        module = _import_module(module_name)

        if module:
            # Register module
            if _register_module(module):
                _registered_modules.append(module)
                print(f"BlendPro: ✓ {module_name} registered successfully")
            else:
                print(f"BlendPro: ✗ {module_name} registration failed")
        else:
            print(f"BlendPro: ✗ {module_name} import failed")

    # Initialize Blender properties
    try:
        from .utils.file_manager import init_props
        init_props()
        print("BlendPro: ✓ Blender properties initialized")
    except Exception as e:
        print(f"BlendPro: ✗ Failed to initialize properties: {e}")
        traceback.print_exc()

    # Load saved settings and chat history (deferred to avoid context restrictions)
    try:
        from .utils.file_manager import get_file_manager
        file_manager = get_file_manager()

        # Schedule chat history loading for later (when context is available)
        _chat_history_loaded = False

        def load_chat_history_safe():
            nonlocal _chat_history_loaded

            # If already loaded, don't repeat
            if _chat_history_loaded:
                return None  # Stop timer

            try:
                if hasattr(bpy.context, 'scene') and bpy.context.scene:
                    if hasattr(bpy.context.scene, 'blendpro_chat_history'):
                        file_manager.load_chat_history(bpy.context.scene.blendpro_chat_history)
                        print("BlendPro: ✓ Chat history loaded")
                        _chat_history_loaded = True
                        return None  # Stop timer
            except (AttributeError, RuntimeError):
                pass  # Context not available yet
            return 1.0  # Retry in 1 second

        # Use a timer to defer the loading with retry mechanism
        global _chat_history_timer
        _chat_history_timer = bpy.app.timers.register(load_chat_history_safe, first_interval=1.0)

    except Exception as e:
        print(f"BlendPro: ✗ Failed to setup deferred loading: {e}")

    print(f"BlendPro: Registration complete! {len(_registered_modules)}/{len(MODULE_REGISTRATION_ORDER)} modules registered")

def unregister():
    """Unregister all BlendPro modules and components"""
    global _registered_modules, _chat_history_timer

    print("BlendPro: Starting unregistration...")

    # Clean up timer first
    if _chat_history_timer and bpy.app.timers.is_registered(_chat_history_timer):
        bpy.app.timers.unregister(_chat_history_timer)
        _chat_history_timer = None
        print("BlendPro: ✓ Chat history timer cleaned up")

    # Save current state before unregistering
    try:
        from .utils.file_manager import get_file_manager, clear_props

        # Save chat history
        if hasattr(bpy.context.scene, 'blendpro_chat_history'):
            file_manager = get_file_manager()
            file_manager.save_chat_history(bpy.context.scene.blendpro_chat_history)
            print("BlendPro: ✓ Chat history saved")

        # Clear properties
        clear_props()
        print("BlendPro: ✓ Blender properties cleared")

    except Exception as e:
        print(f"BlendPro: ✗ Failed to save state: {e}")

    # Stop any active monitoring
    try:
        from .workflow.scene_monitor import get_scene_health_monitor
        monitor = get_scene_health_monitor()
        monitor.stop_monitoring()
        # Thread'in bitmesini bekle
        if monitor._monitoring_thread:
            monitor._monitoring_thread.join(timeout=5.0)
        print("BlendPro: ✓ Scene monitoring stopped")
    except Exception as e:
        print(f"BlendPro: ✗ Failed to stop monitoring: {e}")

    # Unregister modules in reverse order
    for module in reversed(_registered_modules):
        module_name = getattr(module, '__name__', 'unknown')
        print(f"BlendPro: Unregistering {module_name}...")

        if _unregister_module(module):
            print(f"BlendPro: ✓ {module_name} unregistered successfully")
        else:
            print(f"BlendPro: ✗ {module_name} unregistration failed")

    # Clear module registry
    _registered_modules.clear()

    print("BlendPro: Unregistration complete!")

# Development utilities
def reload_addon():
    """Reload the entire addon (useful for development)"""
    print("BlendPro: Reloading addon...")

    try:
        unregister()

        # Clear module cache
        modules_to_remove = []
        for module_name in sys.modules:
            if module_name.startswith(__name__):
                modules_to_remove.append(module_name)

        for module_name in modules_to_remove:
            del sys.modules[module_name]

        # Re-import and register
        importlib.reload(sys.modules[__name__])
        register()

        print("BlendPro: ✓ Addon reloaded successfully")

    except Exception as e:
        print(f"BlendPro: ✗ Reload failed: {e}")

def get_addon_info():
    """Get addon information"""
    return {
        "name": bl_info["name"],
        "version": bl_info["version"],
        "author": bl_info["author"],
        "description": bl_info["description"],
        "registered_modules": len(_registered_modules),
        "total_modules": len(MODULE_REGISTRATION_ORDER)
    }

# Blender addon entry points
if __name__ == "__main__":
    register()

# Development operator for reloading
class BLENDPRO_OT_ReloadAddon(bpy.types.Operator):
    """Reload BlendPro addon (development only)"""
    bl_idname = "blendpro.reload_addon"
    bl_label = "Reload BlendPro"
    bl_options = {'REGISTER'}

    def execute(self, context):
        reload_addon()
        self.report({'INFO'}, "BlendPro addon reloaded")
        return {'FINISHED'}

# Register development operator
try:
    bpy.utils.register_class(BLENDPRO_OT_ReloadAddon)
except:
    pass  # Already registered or registration failed
