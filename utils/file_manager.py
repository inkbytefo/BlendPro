"""
File Manager for BlendPro: AI Co-Pilot
Handles file operations, chat history, and Blender properties
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
import bpy

from ..config.settings import get_settings
from ..config.models import get_model_choices, get_vision_model_choices

class FileManager:
    """Manages file operations and persistent data"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def get_user_data_dir(self) -> str:
        """Get user data directory for BlendPro"""
        user_data_dir = bpy.utils.user_resource('DATAFILES')
        blendpro_dir = os.path.join(user_data_dir, "blendpro")
        
        if not os.path.exists(blendpro_dir):
            os.makedirs(blendpro_dir)
        
        return blendpro_dir
    
    def get_chat_history_path(self) -> str:
        """Get path for chat history file"""
        return os.path.join(self.get_user_data_dir(), "chat_history.json")
    
    def save_chat_history(self, chat_history) -> bool:
        """Save chat history to file"""
        try:
            file_path = self.get_chat_history_path()
            history_data = []
            
            for message in chat_history:
                message_data = {
                    "type": str(message.type) if message.type else "user",
                    "content": str(message.content) if message.content else "",
                    "timestamp": time.time()
                }
                
                # Add interactive message data if present
                if hasattr(message, 'is_interactive') and message.is_interactive:
                    message_data["is_interactive"] = True
                    if hasattr(message, 'plan_data') and message.plan_data:
                        # Convert Blender property to string
                        message_data["plan_data"] = str(message.plan_data)
                    if hasattr(message, 'plan_id') and message.plan_id:
                        # Convert Blender property to string
                        message_data["plan_id"] = str(message.plan_id)
                
                history_data.append(message_data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving chat history: {e}")
            return False
    
    def load_chat_history(self, chat_history) -> bool:
        """Load chat history from file"""
        try:
            file_path = self.get_chat_history_path()
            
            if not os.path.exists(file_path):
                return True  # No history file is not an error
            
            with open(file_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # Clear existing history
            chat_history.clear()
            
            # Load history data
            for item in history_data:
                message = chat_history.add()
                message.type = item.get("type", "user")
                message.content = item.get("content", "")
                
                # Restore interactive message data if present
                if item.get("is_interactive", False):
                    message.is_interactive = True
                    if "plan_data" in item:
                        message.plan_data = item["plan_data"]
                    if "plan_id" in item:
                        message.plan_id = item["plan_id"]
            
            return True
            
        except Exception as e:
            print(f"Error loading chat history: {e}")
            return False
    
    def export_chat_history(self, chat_history, file_path: str) -> bool:
        """Export chat history to specified file"""
        try:
            history_data = []
            
            for message in chat_history:
                history_data.append({
                    "type": str(message.type) if message.type else "user",
                    "content": str(message.content) if message.content else "",
                    "timestamp": time.time()
                })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error exporting chat history: {e}")
            return False
    
    def import_chat_history(self, chat_history, file_path: str) -> bool:
        """Import chat history from specified file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # Clear existing history
            chat_history.clear()
            
            # Load imported history
            for item in history_data:
                message = chat_history.add()
                message.type = item.get("type", "user")
                message.content = item.get("content", "")
            
            # Save the imported history
            self.save_chat_history(chat_history)
            
            return True
            
        except Exception as e:
            print(f"Error importing chat history: {e}")
            return False
    
    def get_settings_path(self) -> str:
        """Get path for settings file"""
        return os.path.join(self.get_user_data_dir(), "settings.json")
    
    def save_settings(self, settings_dict: Dict[str, Any]) -> bool:
        """Save settings to file"""
        try:
            file_path = self.get_settings_path()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        try:
            file_path = self.get_settings_path()
            
            if not os.path.exists(file_path):
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {}

# Global file manager instance
_file_manager: Optional[FileManager] = None

def get_file_manager() -> FileManager:
    """Get global file manager instance"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager

# Custom PropertyGroup for chat messages
class BlendProChatMessage(bpy.types.PropertyGroup):
    """Property group for chat messages"""
    type = bpy.props.StringProperty()
    content = bpy.props.StringProperty()
    is_interactive = bpy.props.BoolProperty(default=False)
    plan_data = bpy.props.StringProperty(default="")
    plan_id = bpy.props.StringProperty(default="")

    # Multi-step execution properties
    interaction_type = bpy.props.StringProperty(default="")  # "plan_approval", "next_step", etc.
    next_step_number = bpy.props.IntProperty(default=0)
    next_step_info = bpy.props.StringProperty(default="")

def init_props():
    """Initialize Blender properties for BlendPro"""
    # PropertyGroup should already be registered by register() function
    # Just define the properties here

    # Chat system properties
    bpy.types.Scene.blendpro_chat_history = bpy.props.CollectionProperty(type=BlendProChatMessage)
    bpy.types.Scene.blendpro_chat_input = bpy.props.StringProperty(
        name="Message",
        description="Enter your message",
        default="",
    )
    bpy.types.Scene.blendpro_button_pressed = bpy.props.BoolProperty(default=False)

    # Model selection properties
    from ..config.models import get_default_model_for_task, get_vision_model

    # Get dynamic defaults
    default_model = get_default_model_for_task("general")
    default_vision_model = get_vision_model()

    bpy.types.Scene.blendpro_model = bpy.props.EnumProperty(
        name="AI Model",
        description="Select the AI model to use",
        items=get_model_choices(),
        default=default_model,
    )

    bpy.types.Scene.blendpro_vision_model = bpy.props.EnumProperty(
        name="Vision Model",
        description="Select the Vision model to use",
        items=get_vision_model_choices(),
        default=default_vision_model,
    )

    # Monitoring properties
    bpy.types.Scene.blendpro_monitoring_active = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.blendpro_monitoring_interval = bpy.props.FloatProperty(
        name="Monitoring Interval",
        description="Interval between scene checks (seconds)",
        default=2.0,
        min=0.5,
        max=10.0
    )

    # Load saved chat history
    file_manager = get_file_manager()
    try:
        # This will be called during registration, so we need to be careful
        # about accessing scene properties that might not exist yet
        pass
    except:
        pass

def clear_props():
    """Clear Blender properties for BlendPro"""
    # Save chat history before clearing (with context safety)
    try:
        file_manager = get_file_manager()
        if bpy.context.scene and hasattr(bpy.context.scene, 'blendpro_chat_history'):
            file_manager.save_chat_history(bpy.context.scene.blendpro_chat_history)
    except Exception:
        # Context might not be available during unregistration
        pass

    # Clear properties
    props_to_clear = [
        'blendpro_chat_history',
        'blendpro_chat_input',
        'blendpro_button_pressed',
        'blendpro_model',
        'blendpro_vision_model',
        'blendpro_monitoring_active',
        'blendpro_monitoring_interval'
    ]

    for prop in props_to_clear:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

    # Unregister custom PropertyGroup
    try:
        bpy.utils.unregister_class(BlendProChatMessage)
    except ValueError:
        # Already unregistered
        pass

def register():
    """Register file manager components"""
    # PropertyGroup'u sadece burada kayıt et
    if not hasattr(bpy.types, 'BlendProChatMessage'):
        bpy.utils.register_class(BlendProChatMessage)
    init_props()

def unregister():
    """Unregister file manager components"""
    clear_props()
