"""
Response Popup for BlendPro: AI Co-Pilot
Shows AI responses in a dedicated popup window
"""

import bpy
import textwrap
from bpy.types import Operator
from bpy.props import StringProperty

class BLENDPRO_OT_show_response(Operator):
    """Show AI response in popup"""
    bl_idname = "blendpro.show_response"
    bl_label = "BlendPro AI Response"
    bl_options = {'REGISTER'}
    
    # Properties to store response data
    response_text: StringProperty(
        name="Response",
        description="AI response text",
        default=""
    )
    
    response_type: StringProperty(
        name="Type",
        description="Response type",
        default="answer"
    )

    plan_id: StringProperty(
        name="Plan ID",
        description="ID of the plan to execute",
        default=""
    )
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Set popup width based on content
        content_length = len(self.response_text)
        if content_length > 500:
            width = 600
        elif content_length > 200:
            width = 450
        else:
            width = 350
            
        return context.window_manager.invoke_props_dialog(self, width=width)
    
    def draw(self, context):
        layout = self.layout
        
        # Header with icon
        header = layout.row()
        if self.response_type == "error":
            header.label(text="Error", icon='ERROR')
        elif self.response_type == "warning":
            header.label(text="Warning", icon='ERROR')
        elif self.response_type == "code":
            header.label(text="Code Generated", icon='CONSOLE')
        elif self.response_type == "plan":
            header.label(text="Plan Created", icon='PRESET')
        else:
            header.label(text="AI Response", icon='COMMUNITY')
        
        layout.separator()
        
        # Response content
        if self.response_text:
            # Split long text into multiple lines
            max_line_length = 80
            lines = self.response_text.split('\n')
            
            for line in lines:
                if len(line) <= max_line_length:
                    layout.label(text=line)
                else:
                    # Wrap long lines
                    wrapped_lines = textwrap.wrap(line, width=max_line_length)
                    for wrapped_line in wrapped_lines:
                        layout.label(text=wrapped_line)
        else:
            layout.label(text="No response content")
        
        layout.separator()
        
        # Action buttons
        button_row = layout.row()
        button_row.alignment = 'CENTER'
        
        if self.response_type == "code":
            # Extract code from response text
            code_text = self.response_text
            if "Generated Code:" in code_text:
                code_text = code_text.split("Generated Code:")[-1].strip()

            exec_op = button_row.operator("blendpro.execute_code", text="Execute Code", icon='PLAY')
            exec_op.code = code_text
            button_row.operator("blendpro.copy_code", text="Copy Code", icon='COPYDOWN')
        elif self.response_type == "plan":
            # Use the plan_id passed to this popup operator
            if self.plan_id and str(self.plan_id).strip():
                approve_op = button_row.operator("blendpro.approve_plan", text="Approve Plan", icon='CHECKMARK')

                # Get the latest plan data from chat history for steps
                chat_history = context.scene.blendpro_chat_history
                latest_plan_message = None

                # Find the most recent plan message
                for message in reversed(chat_history):
                    if hasattr(message, 'is_interactive') and message.is_interactive and hasattr(message, 'plan_data'):
                        latest_plan_message = message
                        break

                if latest_plan_message and latest_plan_message.plan_data:
                    plan_data_str = str(latest_plan_message.plan_data)
                    approve_op.plan_steps_json = plan_data_str

                # Set plan ID from popup's own property
                approve_op.plan_id = str(self.plan_id).strip()
            else:
                # No plan_id available - show disabled button
                button_row.label(text="Plan ID missing - cannot execute", icon='ERROR')

            button_row.operator("blendpro.reject_plan", text="Reject Plan", icon='X')
        
        # Always show close button
        button_row.operator("blendpro.close_popup", text="Close", icon='X')

class BLENDPRO_OT_copy_code(Operator):
    """Copy code to clipboard"""
    bl_idname = "blendpro.copy_code"
    bl_label = "Copy Code"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        # Get the last AI response that contains code
        chat_history = context.scene.blendpro_chat_history
        for message in reversed(chat_history):
            if message.type == 'assistant' and 'import' in str(message.content):
                # Copy to clipboard (simplified - would need proper clipboard handling)
                context.window_manager.clipboard = str(message.content)
                self.report({'INFO'}, "Code copied to clipboard")
                return {'FINISHED'}
        
        self.report({'WARNING'}, "No code found to copy")
        return {'CANCELLED'}

class BLENDPRO_OT_close_popup(Operator):
    """Close popup"""
    bl_idname = "blendpro.close_popup"
    bl_label = "Close"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        return {'FINISHED'}

# Convenience function to show response popup
def show_response_popup(response_text: str, response_type: str = "answer", plan_id: str = ""):
    """Show AI response in popup window"""
    bpy.ops.blendpro.show_response(
        'INVOKE_DEFAULT',
        response_text=response_text,
        response_type=response_type,
        plan_id=plan_id
    )

def register():
    bpy.utils.register_class(BLENDPRO_OT_show_response)
    bpy.utils.register_class(BLENDPRO_OT_copy_code)
    bpy.utils.register_class(BLENDPRO_OT_close_popup)

def unregister():
    bpy.utils.unregister_class(BLENDPRO_OT_close_popup)
    bpy.utils.unregister_class(BLENDPRO_OT_copy_code)
    bpy.utils.unregister_class(BLENDPRO_OT_show_response)
