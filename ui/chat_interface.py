"""
Chat Interface for BlendPro: AI Co-Pilot
Advanced chat interface with history and interactive features
"""

import bpy
from typing import List, Dict, Any, Optional

from ..config.settings import get_settings
from ..utils.file_manager import get_file_manager

class ChatInterface:
    """Manages chat interface functionality"""
    
    def __init__(self):
        self.settings = get_settings()
        self.file_manager = get_file_manager()
    
    def get_chat_history(self, context) -> List[Dict[str, Any]]:
        """Get formatted chat history"""
        
        chat_history = context.scene.blendpro_chat_history
        formatted_history = []
        
        for message in chat_history:
            formatted_message = {
                "type": message.type,
                "content": message.content,
                "is_interactive": getattr(message, 'is_interactive', False),
                "plan_data": getattr(message, 'plan_data', "")
            }
            formatted_history.append(formatted_message)
        
        return formatted_history
    
    def clear_chat_history(self, context) -> None:
        """Clear chat history"""
        context.scene.blendpro_chat_history.clear()
        self.file_manager.save_chat_history(context.scene.blendpro_chat_history)
    
    def export_chat_history(self, context, file_path: str) -> bool:
        """Export chat history to file"""
        return self.file_manager.export_chat_history(context.scene.blendpro_chat_history, file_path)
    
    def import_chat_history(self, context, file_path: str) -> bool:
        """Import chat history from file"""
        return self.file_manager.import_chat_history(context.scene.blendpro_chat_history, file_path)

class BLENDPRO_PT_ChatPanel(bpy.types.Panel):
    """Dedicated chat panel for detailed conversation view"""
    bl_label = "Chat History"
    bl_idname = "BLENDPRO_PT_chat_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlendPro"
    bl_parent_id = "BLENDPRO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw chat panel content"""
        layout = self.layout
        scene = context.scene
        
        # Chat history controls
        self._draw_chat_controls(layout, context)
        
        # Chat history display
        self._draw_chat_history(layout, context)
    
    def _draw_chat_controls(self, layout, context):
        """Draw chat control buttons"""
        box = layout.box()
        box.label(text="Chat Controls", icon='TOOL_SETTINGS')
        
        row = box.row(align=True)
        row.operator("blendpro.clear_chat_history", text="Clear", icon='TRASH')
        row.operator("blendpro.export_chat_history", text="Export", icon='EXPORT')
        row.operator("blendpro.import_chat_history", text="Import", icon='IMPORT')
        
        # Chat statistics
        chat_history = context.scene.blendpro_chat_history
        stats_row = box.row()
        stats_row.label(text=f"Messages: {len(chat_history)}")
    
    def _draw_chat_history(self, layout, context):
        """Draw full chat history"""
        chat_history = context.scene.blendpro_chat_history
        
        if not chat_history:
            layout.label(text="No chat history", icon='INFO')
            return
        
        # Scrollable chat history
        box = layout.box()
        box.label(text="Conversation", icon='TEXT')
        
        # Show all messages with proper formatting
        for i, message in enumerate(chat_history):
            self._draw_message(box, message, i)
    
    def _draw_message(self, layout, message, index: int):
        """Draw individual message"""
        
        # Message container
        msg_box = layout.box()
        
        # Message header
        header_row = msg_box.row()
        
        if message.type == 'user':
            header_row.label(text=f"You (#{index + 1})", icon='USER')
        else:
            header_row.label(text=f"BlendPro (#{index + 1})", icon='COMMUNITY')
        
        # Message content
        content = str(message.content) if message.content else ""
        content_lines = content.split('\n')
        
        # Show first few lines, with expand option for long messages
        max_lines = 5
        
        for line_num, line in enumerate(content_lines[:max_lines]):
            if line.strip():  # Skip empty lines
                content_row = msg_box.row()
                content_row.label(text=line[:80] + ("..." if len(line) > 80 else ""))
        
        # Show expand button for long messages
        if len(content_lines) > max_lines:
            expand_row = msg_box.row()
            expand_row.operator("blendpro.expand_message", text=f"Show {len(content_lines) - max_lines} more lines...", icon='TRIA_DOWN')
        
        # Interactive message options
        if hasattr(message, 'is_interactive') and message.is_interactive:
            self._draw_interactive_options(msg_box, message)
        
        # Code preview for code messages
        if message.type == 'assistant' and '```' in message.content:
            code_row = msg_box.row()
            code_row.operator("blendpro.preview_message_code", text="Preview Code", icon='SCRIPT')
    
    def _draw_interactive_options(self, layout, message):
        """Draw interactive message options"""
        
        interactive_box = layout.box()
        interactive_box.label(text="Interactive Options", icon='SETTINGS')
        
        # Plan approval options
        if hasattr(message, 'plan_data') and message.plan_data:
            try:
                import json
                plan_data_str = str(message.plan_data).strip()

                # Comprehensive validation of plan_data before JSON parsing
                if (not plan_data_str or
                    plan_data_str == "" or
                    plan_data_str in ["None", "null", "undefined"] or
                    plan_data_str.startswith("<") or
                    "PropertyDeferred" in plan_data_str or
                    len(plan_data_str) < 2):  # Minimum valid JSON is "{}" or "[]"
                    return

                # Additional safety check: try to parse JSON and handle any parsing errors
                try:
                    plan_steps = json.loads(plan_data_str)
                except (json.JSONDecodeError, ValueError, TypeError) as json_error:
                    # Log the error for debugging but don't crash the UI
                    print(f"JSON parsing error in plan_data: {json_error}")
                    return

                if plan_steps:
                    plan_row = interactive_box.row(align=True)

                    # Check interaction type
                    interaction_type = getattr(message, 'interaction_type', '')

                    if interaction_type == "next_step":
                        # Show next step button
                        next_step_number = getattr(message, 'next_step_number', 1)
                        next_op = plan_row.operator("blendpro.approve_plan", text=f"Execute Step {next_step_number}", icon='FORWARD')
                        next_op.plan_id = str(message.plan_id).strip()
                        next_op.step_number = next_step_number

                        # Show step info if available
                        next_step_info = getattr(message, 'next_step_info', '')
                        if next_step_info:
                            try:
                                step_info = json.loads(next_step_info)
                                info_row = interactive_box.row()
                                info_row.label(text=f"Next: {step_info.get('description', 'Continue')}", icon='INFO')
                            except:
                                pass
                    else:
                        # Regular plan approval
                        approve_op = plan_row.operator("blendpro.approve_plan", text="Execute Plan", icon='CHECKMARK')
                        approve_op.plan_steps_json = plan_data_str

                        # Set plan ID - must be available from message
                        if hasattr(message, 'plan_id') and message.plan_id and str(message.plan_id).strip():
                            approve_op.plan_id = str(message.plan_id).strip()
                        else:
                            # Skip if no plan_id available - operator will handle the error
                            print("Warning: No plan_id available for plan execution")
                            return

                        plan_row.operator("blendpro.reject_plan", text="Reject Plan", icon='CANCEL')

                        # Show plan summary
                        summary_row = interactive_box.row()
                        summary_row.label(text=f"Plan: {len(plan_steps)} steps", icon='LIST')

            except json.JSONDecodeError as e:
                print(f"Error parsing plan data in chat interface: {e}")
                pass

# Chat-related operators
class BLENDPRO_OT_ClearChatHistory(bpy.types.Operator):
    """Clear chat history"""
    bl_idname = "blendpro.clear_chat_history"
    bl_label = "Clear Chat History"
    bl_options = {'REGISTER'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        chat_interface = ChatInterface()
        chat_interface.clear_chat_history(context)
        
        self.report({'INFO'}, "Chat history cleared")
        return {'FINISHED'}

class BLENDPRO_OT_ExportChatHistory(bpy.types.Operator):
    """Export chat history to file"""
    bl_idname = "blendpro.export_chat_history"
    bl_label = "Export Chat History"
    bl_options = {'REGISTER'}
    
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to export file",
        default="blendpro_chat_history.json",
        subtype='FILE_PATH'
    )
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        chat_interface = ChatInterface()
        
        if chat_interface.export_chat_history(context, self.filepath):
            self.report({'INFO'}, f"Chat history exported to {self.filepath}")
        else:
            self.report({'ERROR'}, "Failed to export chat history")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class BLENDPRO_OT_ImportChatHistory(bpy.types.Operator):
    """Import chat history from file"""
    bl_idname = "blendpro.import_chat_history"
    bl_label = "Import Chat History"
    bl_options = {'REGISTER'}
    
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to import file",
        subtype='FILE_PATH'
    )
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        chat_interface = ChatInterface()
        
        if chat_interface.import_chat_history(context, self.filepath):
            self.report({'INFO'}, f"Chat history imported from {self.filepath}")
        else:
            self.report({'ERROR'}, "Failed to import chat history")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class BLENDPRO_OT_ExpandMessage(bpy.types.Operator):
    """Expand long message to show full content"""
    bl_idname = "blendpro.expand_message"
    bl_label = "Expand Message"
    bl_options = {'REGISTER'}
    
    message_index: bpy.props.IntProperty()
    
    def execute(self, context):
        # This would show a popup or separate window with full message content
        # For now, just print to console
        chat_history = context.scene.blendpro_chat_history
        
        if 0 <= self.message_index < len(chat_history):
            message = chat_history[self.message_index]
            print(f"\n{'='*50}")
            print(f"Message #{self.message_index + 1} ({message.type}):")
            print(f"{'='*50}")
            print(message.content)
            print(f"{'='*50}\n")
            
            self.report({'INFO'}, "Full message printed to console")
        else:
            self.report({'ERROR'}, "Invalid message index")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class BLENDPRO_OT_PreviewMessageCode(bpy.types.Operator):
    """Preview code from message"""
    bl_idname = "blendpro.preview_message_code"
    bl_label = "Preview Code"
    bl_options = {'REGISTER'}
    
    message_index: bpy.props.IntProperty()
    
    def execute(self, context):
        chat_history = context.scene.blendpro_chat_history
        
        if 0 <= self.message_index < len(chat_history):
            message = chat_history[self.message_index]
            
            # Extract code from message
            import re
            code_blocks = re.findall(r'```(?:python)?\s*(.*?)```', message.content, re.DOTALL)
            
            if code_blocks:
                code = code_blocks[0].strip()
                # Show code preview
                bpy.ops.blendpro.code_preview('INVOKE_DEFAULT', code=code)
            else:
                self.report({'INFO'}, "No code found in message")
        else:
            self.report({'ERROR'}, "Invalid message index")
            return {'CANCELLED'}
        
        return {'FINISHED'}

def register():
    """Register Blender classes"""
    bpy.utils.register_class(BLENDPRO_PT_ChatPanel)
    bpy.utils.register_class(BLENDPRO_OT_ClearChatHistory)
    bpy.utils.register_class(BLENDPRO_OT_ExportChatHistory)
    bpy.utils.register_class(BLENDPRO_OT_ImportChatHistory)
    bpy.utils.register_class(BLENDPRO_OT_ExpandMessage)
    bpy.utils.register_class(BLENDPRO_OT_PreviewMessageCode)

def unregister():
    """Unregister Blender classes"""
    bpy.utils.unregister_class(BLENDPRO_OT_PreviewMessageCode)
    bpy.utils.unregister_class(BLENDPRO_OT_ExpandMessage)
    bpy.utils.unregister_class(BLENDPRO_OT_ImportChatHistory)
    bpy.utils.unregister_class(BLENDPRO_OT_ExportChatHistory)
    bpy.utils.unregister_class(BLENDPRO_OT_ClearChatHistory)
    bpy.utils.unregister_class(BLENDPRO_PT_ChatPanel)
