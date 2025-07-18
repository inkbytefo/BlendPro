"""
Settings Panel for BlendPro: AI Co-Pilot
Addon preferences and configuration interface
"""

import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty, EnumProperty

from ..config.settings import get_settings
from ..config.models import get_model_choices, get_vision_model_choices
from ..utils.api_client import get_api_client

class BLENDPROAddonPreferences(AddonPreferences):
    """BlendPro addon preferences"""
    bl_idname = __package__.split('.')[0]  # Get main package name
    
    # API Configuration
    api_key: StringProperty(
        name="OpenAI API Key",
        description="Your OpenAI API key for AI functionality",
        default="",
        subtype='PASSWORD'
    )
    
    custom_api_url: StringProperty(
        name="Custom API URL",
        description="Custom API endpoint URL (leave empty for OpenAI)",
        default=""
    )
    
    use_custom_model: BoolProperty(
        name="Use Custom Model",
        description="Use a custom model instead of the default",
        default=False
    )
    
    custom_model: StringProperty(
        name="Custom Model",
        description="Custom model name (e.g., gpt-4o-mini, gpt-4o, claude-3-5-sonnet)",
        default=""  # Will be set dynamically
    )
    
    # Vision Configuration
    vision_api_key: StringProperty(
        name="Vision API Key",
        description="API key for vision-capable models (can be same as main API key)",
        default="",
        subtype='PASSWORD'
    )
    
    vision_api_url: StringProperty(
        name="Vision API URL",
        description="API endpoint for vision models",
        default=""
    )
    
    vision_model: StringProperty(
        name="Vision Model",
        description="Model to use for vision tasks",
        default=""  # Will be set dynamically
    )
    
    # AI Behavior Settings
    temperature: FloatProperty(
        name="Temperature",
        description="Controls randomness in AI responses (0.0 = deterministic, 1.0 = creative)",
        default=0.7,
        min=0.0,
        max=2.0,
        step=0.1
    )
    
    max_tokens: IntProperty(
        name="Max Tokens",
        description="Maximum tokens in AI response",
        default=1500,
        min=100,
        max=4000
    )
    
    # Feature Toggles
    enable_vision_context: BoolProperty(
        name="Enable Vision Context",
        description="Include viewport screenshots in AI analysis",
        default=True
    )
    
    enable_multi_step_planning: BoolProperty(
        name="Enable Multi-Step Planning",
        description="Break complex tasks into multiple steps",
        default=True
    )
    
    enable_proactive_suggestions: BoolProperty(
        name="Enable Proactive Suggestions",
        description="Show AI-generated suggestions based on your workflow",
        default=True
    )
    
    enable_scene_monitoring: BoolProperty(
        name="Enable Scene Monitoring",
        description="Monitor scene health and provide real-time feedback",
        default=True
    )
    
    enable_auto_backup: BoolProperty(
        name="Enable Auto Backup",
        description="Automatically backup scene before code execution",
        default=True
    )
    
    enable_caching: BoolProperty(
        name="Enable Caching",
        description="Cache API responses to improve performance",
        default=True
    )
    
    # Performance Settings
    monitoring_interval: FloatProperty(
        name="Monitoring Interval",
        description="Seconds between scene health checks",
        default=2.0,
        min=0.5,
        max=10.0
    )
    
    max_concurrent_requests: IntProperty(
        name="Max Concurrent Requests",
        description="Maximum number of simultaneous API requests",
        default=3,
        min=1,
        max=10
    )
    
    max_suggestions: IntProperty(
        name="Max Suggestions",
        description="Maximum number of active suggestions to show",
        default=5,
        min=1,
        max=20
    )
    
    backup_interval: IntProperty(
        name="Backup Interval",
        description="Minimum seconds between automatic backups",
        default=300,  # 5 minutes
        min=60,
        max=3600
    )
    
    max_backups: IntProperty(
        name="Max Backups",
        description="Maximum number of backup files to keep",
        default=10,
        min=1,
        max=50
    )
    
    analysis_cooldown: FloatProperty(
        name="Analysis Cooldown",
        description="Minimum seconds between scene analyses",
        default=1.0,
        min=0.1,
        max=10.0
    )
    
    def draw(self, context):
        """Draw preferences interface"""
        layout = self.layout
        
        # API Configuration Section
        self._draw_api_configuration(layout)
        
        # AI Behavior Section
        self._draw_ai_behavior(layout)
        
        # Feature Toggles Section
        self._draw_feature_toggles(layout)
        
        # Performance Settings Section
        self._draw_performance_settings(layout)
        
        # System Status Section
        self._draw_system_status(layout)
    
    def _draw_api_configuration(self, layout):
        """Draw API configuration section"""
        box = layout.box()
        box.label(text="API Configuration", icon='WORLD')
        
        # Main API settings
        main_box = box.box()
        main_box.label(text="Main API", icon='PLUGIN')
        
        main_box.prop(self, "api_key")
        main_box.prop(self, "custom_api_url")
        
        # Model selection
        model_row = main_box.row()
        model_row.prop(self, "use_custom_model")
        
        if self.use_custom_model:
            model_row.prop(self, "custom_model", text="")
        
        # Vision API settings
        vision_box = box.box()
        vision_box.label(text="Vision API", icon='CAMERA_DATA')
        
        vision_box.prop(self, "vision_api_key")
        vision_box.prop(self, "vision_api_url")
        vision_box.prop(self, "vision_model")
        
        # Action buttons
        action_row = box.row(align=True)
        action_row.scale_y = 1.2
        action_row.operator("blendpro.initialize_ai", text="Initialize AI", icon='PLAY')
        action_row.operator("blendpro.test_api_connection", text="Test Connection", icon='LINKED')
    
    def _draw_ai_behavior(self, layout):
        """Draw AI behavior settings"""
        box = layout.box()
        box.label(text="AI Behavior", icon='SETTINGS')
        
        row = box.row()
        row.prop(self, "temperature")
        row.prop(self, "max_tokens")
    
    def _draw_feature_toggles(self, layout):
        """Draw feature toggle settings"""
        box = layout.box()
        box.label(text="Features", icon='MODIFIER')
        
        # Core features
        col = box.column()
        col.prop(self, "enable_vision_context")
        col.prop(self, "enable_multi_step_planning")
        col.prop(self, "enable_proactive_suggestions")
        col.prop(self, "enable_scene_monitoring")
        col.prop(self, "enable_auto_backup")
        col.prop(self, "enable_caching")
    
    def _draw_performance_settings(self, layout):
        """Draw performance settings"""
        box = layout.box()
        box.label(text="Performance", icon='PREFERENCES')
        
        # Monitoring settings
        monitor_box = box.box()
        monitor_box.label(text="Monitoring", icon='VIEWZOOM')
        
        row = monitor_box.row()
        row.prop(self, "monitoring_interval")
        row.prop(self, "analysis_cooldown")
        
        # Request settings
        request_box = box.box()
        request_box.label(text="Requests", icon='INTERNET')
        
        row = request_box.row()
        row.prop(self, "max_concurrent_requests")
        row.prop(self, "max_suggestions")
        
        # Backup settings
        backup_box = box.box()
        backup_box.label(text="Backups", icon='FILE_BACKUP')
        
        row = backup_box.row()
        row.prop(self, "backup_interval")
        row.prop(self, "max_backups")
    
    def _draw_system_status(self, layout):
        """Draw system status information"""
        box = layout.box()
        box.label(text="System Status", icon='SYSTEM')
        
        # API status
        api_client = get_api_client()
        
        status_row = box.row()
        if self.api_key:
            status_row.label(text="API: Configured", icon='CHECKMARK')
        else:
            status_row.label(text="API: Not Configured", icon='ERROR')
        
        # Cache stats
        cache_stats = api_client.get_cache_stats()
        cache_row = box.row()
        cache_row.label(text=f"Cached Requests: {cache_stats.get('cached_requests', 0)}")
        
        # System actions
        actions_row = box.row(align=True)
        actions_row.operator("blendpro.clear_cache", text="Clear Cache", icon='TRASH')
        actions_row.operator("blendpro.reset_settings", text="Reset Settings", icon='LOOP_BACK')

class BLENDPRO_PT_SettingsPanel(bpy.types.Panel):
    """Settings panel in 3D viewport"""
    bl_label = "Settings"
    bl_idname = "BLENDPRO_PT_settings_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlendPro"
    bl_parent_id = "BLENDPRO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw settings panel"""
        layout = self.layout
        
        # Quick settings
        self._draw_quick_settings(layout, context)
        
        # Link to full preferences
        prefs_row = layout.row()
        prefs_row.scale_y = 1.2
        prefs_row.operator("screen.userpref_show", text="Full Settings", icon='PREFERENCES')
    
    def _draw_quick_settings(self, layout, context):
        """Draw quick settings toggles"""
        box = layout.box()
        box.label(text="Quick Settings", icon='TOOL_SETTINGS')
        
        # Get addon preferences
        addon_prefs = context.preferences.addons[__package__.split('.')[0]].preferences
        
        # Feature toggles
        col = box.column()
        col.prop(addon_prefs, "enable_vision_context", text="Vision Context")
        col.prop(addon_prefs, "enable_multi_step_planning", text="Multi-Step Planning")
        col.prop(addon_prefs, "enable_proactive_suggestions", text="Suggestions")
        col.prop(addon_prefs, "enable_scene_monitoring", text="Scene Monitoring")

# Settings-related operators
class BLENDPRO_OT_InitializeAI(bpy.types.Operator):
    """Initialize BlendPro AI system"""
    bl_idname = "blendpro.initialize_ai"
    bl_label = "Initialize AI"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            from ..utils.initialization import initialize_blendpro

            result = initialize_blendpro()

            if result["success"]:
                self.report({'INFO'}, f"✓ {result['message']}")
                if "api_model" in result:
                    self.report({'INFO'}, f"Using model: {result['api_model']}")
            else:
                self.report({'ERROR'}, f"✗ {result['error']}")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Initialization failed: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

class BLENDPRO_OT_TestAPIConnection(bpy.types.Operator):
    """Test API connection"""
    bl_idname = "blendpro.test_api_connection"
    bl_label = "Test API Connection"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            # Get addon preferences
            addon_prefs = context.preferences.addons[__package__.split('.')[0]].preferences

            # Update settings with current preferences
            from ..config.settings import update_settings
            update_settings(
                api_key=addon_prefs.api_key,
                base_url=addon_prefs.custom_api_url,
                temperature=addon_prefs.temperature,
                max_tokens=addon_prefs.max_tokens,
                vision_api_key=addon_prefs.vision_api_key or addon_prefs.api_key,
                vision_base_url=addon_prefs.vision_api_url or addon_prefs.custom_api_url
            )

            # Get API client
            api_client = get_api_client()

            # Test main API
            main_result = api_client.test_connection()

            if main_result["success"]:
                self.report({'INFO'}, "Main API connection successful")
            else:
                self.report({'ERROR'}, f"Main API failed: {main_result.get('error', 'Unknown error')}")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Test failed: {str(e)}")
            return {'CANCELLED'}
        
        # Test vision API if different
        settings = get_settings()
        vision_config = settings.get_vision_api_config()
        main_config = settings.get_api_config()
        
        if vision_config["api_key"] != main_config["api_key"] or vision_config["base_url"] != main_config["base_url"]:
            vision_result = api_client.test_connection(use_vision=True)
            
            if vision_result["success"]:
                self.report({'INFO'}, "Vision API connection also successful")
            else:
                self.report({'WARNING'}, f"Vision API failed: {vision_result.get('error', 'Unknown error')}")
        
        return {'FINISHED'}

class BLENDPRO_OT_ClearCache(bpy.types.Operator):
    """Clear API cache"""
    bl_idname = "blendpro.clear_cache"
    bl_label = "Clear Cache"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        api_client = get_api_client()
        api_client.clear_cache()
        
        # Clear other caches
        from ..vision.scene_analyzer import get_scene_analyzer
        from ..workflow.scene_monitor import get_scene_health_monitor
        
        get_scene_analyzer().clear_cache()
        
        self.report({'INFO'}, "All caches cleared")
        return {'FINISHED'}

class BLENDPRO_OT_ResetSettings(bpy.types.Operator):
    """Reset settings to defaults"""
    bl_idname = "blendpro.reset_settings"
    bl_label = "Reset Settings"
    bl_options = {'REGISTER'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        # Reset addon preferences to defaults
        addon_prefs = context.preferences.addons[__package__.split('.')[0]].preferences
        
        # Reset to default values (this is a simplified approach)
        addon_prefs.temperature = 0.7
        addon_prefs.max_tokens = 1500
        addon_prefs.monitoring_interval = 2.0
        addon_prefs.max_concurrent_requests = 3
        addon_prefs.max_suggestions = 5
        addon_prefs.backup_interval = 300
        addon_prefs.max_backups = 10
        addon_prefs.analysis_cooldown = 1.0
        
        # Reset feature toggles
        addon_prefs.enable_vision_context = True
        addon_prefs.enable_multi_step_planning = True
        addon_prefs.enable_proactive_suggestions = True
        addon_prefs.enable_scene_monitoring = True
        addon_prefs.enable_auto_backup = True
        addon_prefs.enable_caching = True
        
        # Set dynamic defaults for models
        set_dynamic_model_defaults(addon_prefs)

        self.report({'INFO'}, "Settings reset to defaults")
        return {'FINISHED'}

def set_dynamic_model_defaults(preferences):
    """Set dynamic default values for model properties"""
    try:
        from ..config.models import get_default_model_for_task, get_vision_model

        # Set default models if not already set
        if not preferences.custom_model:
            preferences.custom_model = get_default_model_for_task("general")

        if not preferences.vision_model:
            preferences.vision_model = get_vision_model()

    except Exception as e:
        print(f"Warning: Could not set dynamic model defaults: {e}")
        # Fallback to hardcoded defaults
        if not preferences.custom_model:
            preferences.custom_model = "gpt-4o-mini"
        if not preferences.vision_model:
            preferences.vision_model = "gpt-4o-mini"

def register():
    """Register Blender classes"""
    bpy.utils.register_class(BLENDPROAddonPreferences)
    bpy.utils.register_class(BLENDPRO_PT_SettingsPanel)
    bpy.utils.register_class(BLENDPRO_OT_InitializeAI)
    bpy.utils.register_class(BLENDPRO_OT_TestAPIConnection)
    bpy.utils.register_class(BLENDPRO_OT_ClearCache)
    bpy.utils.register_class(BLENDPRO_OT_ResetSettings)

    # Set dynamic defaults for existing preferences
    try:
        addon_prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
        set_dynamic_model_defaults(addon_prefs)
    except:
        pass  # Ignore errors during registration

def unregister():
    """Unregister Blender classes"""
    bpy.utils.unregister_class(BLENDPRO_OT_ResetSettings)
    bpy.utils.unregister_class(BLENDPRO_OT_ClearCache)
    bpy.utils.unregister_class(BLENDPRO_OT_TestAPIConnection)
    bpy.utils.unregister_class(BLENDPRO_OT_InitializeAI)
    bpy.utils.unregister_class(BLENDPRO_PT_SettingsPanel)
    bpy.utils.unregister_class(BLENDPROAddonPreferences)
