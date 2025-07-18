"""
Main Panel for BlendPro: AI Co-Pilot
Primary user interface panel in Blender's 3D viewport
"""

import bpy
from typing import Dict, Any, Optional

from ..config.settings import get_settings
from ..core.interaction_engine import get_interaction_engine
from ..workflow.scene_monitor import get_scene_health_monitor
from ..workflow.proactive_suggestions import get_proactive_suggestions
from ..utils.api_client import get_api_client

class BLENDPRO_PT_MainPanel(bpy.types.Panel):
    """Main BlendPro panel in 3D viewport"""
    bl_label = "BlendPro: AI Co-Pilot"
    bl_idname = "BLENDPRO_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlendPro"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        """Draw panel header with status indicator"""
        layout = self.layout
        
        # Status indicator
        settings = get_settings()
        if settings.api_key:
            layout.label(text="", icon='LINKED')
        else:
            layout.label(text="", icon='UNLINKED')
    
    def draw(self, context):
        """Draw main panel content"""
        layout = self.layout
        scene = context.scene
        settings = get_settings()
        
        # API Configuration Status
        if not settings.api_key:
            self._draw_setup_required(layout)
            return
        
        # Quick Actions Section
        self._draw_quick_actions(layout, context)
        
        # Chat Interface Section
        self._draw_chat_interface(layout, context)
        
        # Scene Health Section
        self._draw_scene_health(layout, context)
        
        # Proactive Suggestions Section
        self._draw_proactive_suggestions(layout, context)
        
        # System Status Section
        self._draw_system_status(layout, context)
    
    def _draw_setup_required(self, layout):
        """Draw setup required message"""
        box = layout.box()
        box.label(text="Setup Required", icon='ERROR')
        box.label(text="Please configure your API key")
        box.label(text="in the addon preferences.")
        
        # Quick setup button
        row = box.row()
        row.scale_y = 1.2
        row.operator("screen.userpref_show", text="Open Preferences", icon='PREFERENCES')
    
    def _draw_quick_actions(self, layout, context):
        """Draw quick action buttons"""
        box = layout.box()
        box.label(text="Quick Actions", icon='PLAY')

        # Quick action buttons
        col = box.column(align=True)

        row = col.row(align=True)
        row.operator("blendpro.analyze_scene_health", text="Health Check", icon='CHECKMARK')
        row.operator("blendpro.auto_fix_scene", text="Auto-Fix", icon='TOOL_SETTINGS')
        
        row = col.row(align=True)
        row.operator("blendpro.capture_screenshot", text="Screenshot", icon='CAMERA_DATA')
        row.operator("blendpro.toggle_scene_monitoring", text="Monitor", icon='VIEWZOOM')
    
    def _draw_chat_interface(self, layout, context):
        """Draw chat interface"""
        box = layout.box()
        box.label(text="AI Assistant", icon='COMMUNITY')
        
        # Chat input
        row = box.row()
        row.prop(context.scene, "blendpro_chat_input", text="", placeholder="Ask me anything...")
        
        # Send button
        send_row = box.row()
        send_row.scale_y = 1.2
        
        # Show processing state
        if context.scene.blendpro_button_pressed:
            send_row.enabled = False
            send_row.operator("blendpro.send_message", text="Processing...", icon='TIME')
        else:
            send_row.operator("blendpro.send_message", text="Send", icon='PLAY')
        
        # Recent chat history (last 3 messages)
        chat_history = context.scene.blendpro_chat_history
        if len(chat_history) > 0:
            history_box = box.box()
            history_box.label(text="Recent Messages:", icon='TEXT')
            
            # Show last 3 messages
            recent_messages = list(chat_history)[-3:]
            for message in recent_messages:
                msg_row = history_box.row()
                
                if message.type == 'user':
                    content = str(message.content)[:50] if message.content else ""
                    msg_row.label(text=f"You: {content}...", icon='USER')
                else:
                    content = str(message.content)[:50] if message.content else ""
                    msg_row.label(text=f"AI: {content}...", icon='COMMUNITY')
                
                # Show interactive options for plan messages
                if hasattr(message, 'is_interactive') and message.is_interactive:
                    interactive_row = history_box.row(align=True)

                    # Parse plan data
                    try:
                        import json
                        plan_data_str = str(message.plan_data).strip() if hasattr(message, 'plan_data') and message.plan_data else ""

                        # Comprehensive validation of plan_data before JSON parsing
                        if (not plan_data_str or
                            plan_data_str == "" or
                            plan_data_str in ["None", "null", "undefined"] or
                            plan_data_str.startswith("<") or
                            "PropertyDeferred" in plan_data_str or
                            len(plan_data_str) < 2):  # Minimum valid JSON is "{}" or "[]"
                            continue

                        # Safe JSON parsing with error handling
                        try:
                            plan_steps = json.loads(plan_data_str)
                        except (json.JSONDecodeError, ValueError, TypeError) as json_error:
                            print(f"JSON parsing error in main_panel plan_data: {json_error}")
                            continue

                        if plan_steps:
                            # Check interaction type
                            interaction_type = getattr(message, 'interaction_type', '')

                            if interaction_type == "next_step":
                                # Show next step button
                                next_step_number = getattr(message, 'next_step_number', 1)
                                next_op = interactive_row.operator("blendpro.approve_plan", text=f"Execute Step {next_step_number}", icon='FORWARD')
                                next_op.plan_id = str(message.plan_id).strip()
                                next_op.step_number = next_step_number

                                # Show step info if available
                                next_step_info = getattr(message, 'next_step_info', '')
                                if next_step_info:
                                    try:
                                        step_info = json.loads(next_step_info)
                                        info_row = layout.row()
                                        info_row.label(text=f"Next: {step_info.get('description', 'Continue')}", icon='INFO')
                                    except:
                                        pass
                            else:
                                # Regular plan approval
                                approve_op = interactive_row.operator("blendpro.approve_plan", text="Execute Plan", icon='CHECKMARK')

                                # Set plan data
                                if plan_data_str:
                                    approve_op.plan_steps_json = plan_data_str

                                # Set plan ID - must be available from message
                                if hasattr(message, 'plan_id') and message.plan_id and str(message.plan_id).strip():
                                    approve_op.plan_id = str(message.plan_id).strip()
                                else:
                                    # Skip if no plan_id available - operator will handle the error
                                    print("Warning: No plan_id available for plan execution")
                                    continue

                                interactive_row.operator("blendpro.reject_plan", text="Reject", icon='CANCEL')
                    except Exception as e:
                        print(f"Error parsing plan data in UI: {e}")
                        pass
    
    def _draw_scene_health(self, layout, context):
        """Draw scene health information"""
        box = layout.box()
        box.label(text="Scene Health", icon='HEART')
        
        # Monitoring status
        monitor = get_scene_health_monitor()
        status = monitor.get_monitoring_status()
        
        row = box.row()
        if status["active"]:
            row.label(text="Monitoring: Active", icon='REC')
        else:
            row.label(text="Monitoring: Inactive", icon='PAUSE')
        
        # Recent suggestions
        suggestions = monitor.get_recent_suggestions(limit=2)
        if suggestions:
            for suggestion in suggestions:
                suggestion_row = box.row()
                suggestion_row.alert = suggestion.get("type") == "health_alert"
                suggestion_row.label(text=suggestion.get("message", "")[:40] + "...", icon='INFO')
        
        # Clear suggestions button
        if suggestions:
            box.operator("blendpro.clear_suggestions", text="Clear", icon='X')
    
    def _draw_proactive_suggestions(self, layout, context):
        """Draw proactive suggestions"""
        box = layout.box()
        box.label(text="Suggestions", icon='OUTLINER_OB_LIGHT')
        
        # Get active suggestions
        proactive = get_proactive_suggestions()
        active_suggestions = proactive.get_active_suggestions()
        
        if active_suggestions:
            # Show top 2 suggestions
            for suggestion in active_suggestions[:2]:
                suggestion_box = box.box()
                
                # Title and priority
                title_row = suggestion_box.row()
                priority = suggestion.get("priority", 5)
                
                if priority >= 8:
                    title_row.alert = True
                    icon = 'ERROR'
                elif priority >= 6:
                    icon = 'INFO'
                else:
                    icon = 'QUESTION'
                
                title_row.label(text=suggestion.get("title", ""), icon=icon)
                
                # Description
                desc_row = suggestion_box.row()
                desc_row.label(text=suggestion.get("description", "")[:60] + "...")
                
                # Action buttons
                if suggestion.get("actionable", False):
                    action_row = suggestion_box.row(align=True)
                    
                    # Execute action button
                    execute_op = action_row.operator("blendpro.execute_suggestion", text="Apply", icon='CHECKMARK')
                    execute_op.suggestion_id = suggestion.get("id", "")
                    
                    # Dismiss button
                    dismiss_op = action_row.operator("blendpro.dismiss_suggestion", text="Dismiss", icon='X')
                    dismiss_op.suggestion_id = suggestion.get("id", "")
        else:
            box.label(text="No active suggestions", icon='CHECKMARK')
    
    def _draw_system_status(self, layout, context):
        """Draw system status information"""
        box = layout.box()
        box.label(text="System Status", icon='SYSTEM')
        
        # API Status
        api_client = get_api_client()
        cache_stats = api_client.get_cache_stats()
        
        row = box.row()
        row.label(text=f"Cached Requests: {cache_stats.get('cached_requests', 0)}")
        
        # Interaction Engine Status
        engine = get_interaction_engine()
        
        row = box.row()
        if hasattr(engine, '_processing') and engine._processing:
            row.label(text="Status: Processing", icon='TIME')
        else:
            row.label(text="Status: Ready", icon='CHECKMARK')
        
        # Settings shortcut
        settings_row = box.row()
        settings_row.scale_y = 0.8
        settings_row.operator("screen.userpref_show", text="Settings", icon='PREFERENCES')

# Additional operators for main panel functionality
class BLENDPRO_OT_ClearSuggestions(bpy.types.Operator):
    """Clear all suggestions"""
    bl_idname = "blendpro.clear_suggestions"
    bl_label = "Clear Suggestions"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        monitor = get_scene_health_monitor()
        monitor.clear_suggestions()
        
        proactive = get_proactive_suggestions()
        proactive.clear_suggestions()
        
        self.report({'INFO'}, "Suggestions cleared")
        return {'FINISHED'}

class BLENDPRO_OT_ExecuteSuggestion(bpy.types.Operator):
    """Execute a proactive suggestion"""
    bl_idname = "blendpro.execute_suggestion"
    bl_label = "Execute Suggestion"
    bl_options = {'REGISTER', 'UNDO'}
    
    suggestion_id: bpy.props.StringProperty()
    
    def execute(self, context):
        if not self.suggestion_id:
            self.report({'ERROR'}, "No suggestion ID provided")
            return {'CANCELLED'}
        
        # This would execute the suggestion's action code
        # Implementation depends on how suggestions store their actions
        self.report({'INFO'}, f"Executed suggestion: {self.suggestion_id}")
        return {'FINISHED'}

class BLENDPRO_OT_DismissSuggestion(bpy.types.Operator):
    """Dismiss a proactive suggestion"""
    bl_idname = "blendpro.dismiss_suggestion"
    bl_label = "Dismiss Suggestion"
    bl_options = {'REGISTER'}
    
    suggestion_id: bpy.props.StringProperty()
    
    def execute(self, context):
        if not self.suggestion_id:
            self.report({'ERROR'}, "No suggestion ID provided")
            return {'CANCELLED'}
        
        proactive = get_proactive_suggestions()
        proactive.dismiss_suggestion(self.suggestion_id)
        
        self.report({'INFO'}, "Suggestion dismissed")
        return {'FINISHED'}

def register():
    """Register Blender classes"""
    bpy.utils.register_class(BLENDPRO_PT_MainPanel)
    bpy.utils.register_class(BLENDPRO_OT_ClearSuggestions)
    bpy.utils.register_class(BLENDPRO_OT_ExecuteSuggestion)
    bpy.utils.register_class(BLENDPRO_OT_DismissSuggestion)

def unregister():
    """Unregister Blender classes"""
    bpy.utils.unregister_class(BLENDPRO_OT_DismissSuggestion)
    bpy.utils.unregister_class(BLENDPRO_OT_ExecuteSuggestion)
    bpy.utils.unregister_class(BLENDPRO_OT_ClearSuggestions)
    bpy.utils.unregister_class(BLENDPRO_PT_MainPanel)
