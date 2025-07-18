"""
Interactive Messages for BlendPro: AI Co-Pilot
Handles interactive message types like plan approvals and code previews
"""

import bpy
import json
from typing import Dict, Any, Optional, List

from ..config.settings import get_settings
from ..utils.code_executor import get_code_executor

class InteractiveMessages:
    """Manages interactive message functionality"""
    
    def __init__(self):
        self.settings = get_settings()
        self.code_executor = get_code_executor()
    
    def create_plan_message(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an interactive plan message"""
        
        steps = plan_data.get("steps", [])
        plan_summary = plan_data.get("plan_summary", "Multi-step plan")
        
        # Create formatted message content
        content_parts = [
            f"📋 **{plan_summary}**\n",
            f"⏱️ **Estimated Time**: {plan_data.get('total_estimated_time', 0) // 60} minutes",
            f"📊 **Complexity**: {'●' * int(plan_data.get('complexity_score', 0.5) * 5)}{'○' * (5 - int(plan_data.get('complexity_score', 0.5) * 5))}\n",
            "**Steps:**"
        ]
        
        for i, step in enumerate(steps, 1):
            content_parts.append(f"{i}. **{step.get('description', 'Step')}**")
            content_parts.append(f"   - Expected: {step.get('expected_outcome', 'Outcome')}")
            
            if step.get('prerequisites'):
                content_parts.append(f"   - Requires: {', '.join(step['prerequisites'])}")
            
            if step.get('potential_issues'):
                content_parts.append(f"   - Watch for: {', '.join(step['potential_issues'])}")
            
            content_parts.append("")
        
        content_parts.append("**Please review and approve this plan to proceed.**")
        
        return {
            "content": "\n".join(content_parts),
            "is_interactive": True,
            "plan_data": json.dumps(steps),
            "interaction_type": "plan_approval"
        }
    
    def create_code_preview_message(self, code: str, description: str = "") -> Dict[str, Any]:
        """Create an interactive code preview message"""
        
        # Format code for display
        code_lines = code.split('\n')
        preview_lines = code_lines[:10]  # Show first 10 lines
        
        content_parts = [
            f"🐍 **Generated Code**" + (f": {description}" if description else ""),
            "",
            "```python"
        ]
        
        content_parts.extend(preview_lines)
        
        if len(code_lines) > 10:
            content_parts.append(f"... ({len(code_lines) - 10} more lines)")
        
        content_parts.extend([
            "```",
            "",
            "**Review the code and click Execute to run it.**"
        ])
        
        return {
            "content": "\n".join(content_parts),
            "is_interactive": True,
            "code_data": code,
            "interaction_type": "code_preview"
        }

class BLENDPRO_PT_InteractivePanel(bpy.types.Panel):
    """Panel for interactive message controls"""
    bl_label = "Interactive Messages"
    bl_idname = "BLENDPRO_PT_interactive_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlendPro"
    bl_parent_id = "BLENDPRO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw interactive panel content"""
        layout = self.layout
        
        # Find interactive messages in chat history
        interactive_messages = self._get_interactive_messages(context)
        
        if not interactive_messages:
            layout.label(text="No interactive messages", icon='INFO')
            return
        
        # Show interactive messages
        for msg_data in interactive_messages:
            self._draw_interactive_message(layout, msg_data)
    
    def _get_interactive_messages(self, context) -> List[Dict[str, Any]]:
        """Get interactive messages from chat history"""
        
        interactive_messages = []
        chat_history = context.scene.blendpro_chat_history
        
        for i, message in enumerate(chat_history):
            if hasattr(message, 'is_interactive') and message.is_interactive:
                msg_data = {
                    "index": i,
                    "content": message.content,
                    "plan_data": getattr(message, 'plan_data', ""),
                    "code_data": getattr(message, 'code_data', ""),
                    "interaction_type": getattr(message, 'interaction_type', "unknown")
                }
                interactive_messages.append(msg_data)
        
        return interactive_messages[-3:]  # Show last 3 interactive messages
    
    def _draw_interactive_message(self, layout, msg_data: Dict[str, Any]):
        """Draw individual interactive message"""
        
        box = layout.box()
        interaction_type = msg_data.get("interaction_type", "unknown")
        
        # Message header
        header_row = box.row()
        
        if interaction_type == "plan_approval":
            header_row.label(text="Plan Approval Required", icon='CHECKMARK')
            self._draw_plan_approval(box, msg_data)
            
        elif interaction_type == "code_preview":
            header_row.label(text="Code Preview", icon='SCRIPT')
            self._draw_code_preview(box, msg_data)
            
        else:
            header_row.label(text="Interactive Message", icon='QUESTION')
            
            # Generic interactive options
            action_row = box.row()
            action_row.label(text="Interactive options available")
    
    def _draw_plan_approval(self, layout, msg_data: Dict[str, Any]):
        """Draw plan approval interface"""

        plan_data = msg_data.get("plan_data", "")
        plan_id = msg_data.get("plan_id", "")

        if not plan_data:
            layout.label(text="No plan data available", icon='ERROR')
            return

        try:
            plan_data_str = str(plan_data).strip() if plan_data else ""

            # Comprehensive validation of plan_data before JSON parsing
            if (not plan_data_str or
                plan_data_str == "" or
                plan_data_str in ["None", "null", "undefined"] or
                plan_data_str.startswith("<") or
                "PropertyDeferred" in plan_data_str or
                len(plan_data_str) < 2):  # Minimum valid JSON is "{}" or "[]"
                layout.label(text="No valid plan data", icon='ERROR')
                return

            # Safe JSON parsing with error handling
            try:
                steps = json.loads(plan_data_str)
            except (json.JSONDecodeError, ValueError, TypeError) as json_error:
                print(f"JSON parsing error in interactive_messages plan_data: {json_error}")
                layout.label(text="Invalid plan data format", icon='ERROR')
                return

            # Plan summary
            summary_row = layout.row()
            summary_row.label(text=f"Steps: {len(steps)}", icon='LIST')

            # Action buttons
            action_row = layout.row(align=True)
            action_row.scale_y = 1.2

            # Execute plan button
            approve_op = action_row.operator("blendpro.approve_plan", text="Execute Plan", icon='CHECKMARK')
            approve_op.plan_steps_json = plan_data_str

            # Set plan ID - must be available
            if plan_id:
                approve_op.plan_id = str(plan_id)
            else:
                # Skip if no plan_id available - operator will handle the error
                print("Warning: No plan_id available for plan execution")
                return

            # Reject plan button
            action_row.operator("blendpro.reject_plan", text="Reject", icon='CANCEL')
            
            # Show individual steps
            if len(steps) <= 5:  # Only show details for small plans
                steps_box = layout.box()
                steps_box.label(text="Plan Steps:", icon='SEQUENCE')
                
                for i, step in enumerate(steps, 1):
                    step_row = steps_box.row()
                    step_row.label(text=f"{i}. {step.get('description', 'Step')[:40]}...")
            
        except json.JSONDecodeError:
            layout.label(text="Invalid plan data", icon='ERROR')
    
    def _draw_code_preview(self, layout, msg_data: Dict[str, Any]):
        """Draw code preview interface"""
        
        code_data = msg_data.get("code_data", "")
        
        if not code_data:
            layout.label(text="No code data available", icon='ERROR')
            return
        
        # Code info
        code_lines = code_data.split('\n')
        info_row = layout.row()
        info_row.label(text=f"Lines: {len(code_lines)}", icon='TEXT')
        
        # Action buttons
        action_row = layout.row(align=True)
        action_row.scale_y = 1.2
        
        # Execute code button
        execute_op = action_row.operator("blendpro.execute_code", text="Execute", icon='PLAY')
        execute_op.code = code_data
        
        # Preview code button
        preview_op = action_row.operator("blendpro.code_preview", text="Preview", icon='ZOOM_IN')
        preview_op.code = code_data

# Code preview and execution operators
class BLENDPRO_OT_CodePreview(bpy.types.Operator):
    """Preview code in a popup"""
    bl_idname = "blendpro.code_preview"
    bl_label = "Code Preview"
    bl_options = {'REGISTER'}
    
    code: bpy.props.StringProperty()
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=600)
    
    def draw(self, context):
        """Draw code preview dialog"""
        layout = self.layout
        
        # Code display
        box = layout.box()
        box.label(text="Generated Code:", icon='SCRIPT')
        
        # Show code lines
        code_lines = self.code.split('\n')
        
        for line in code_lines[:20]:  # Show first 20 lines
            if line.strip():
                row = box.row()
                row.label(text=line[:80])  # Truncate long lines
        
        if len(code_lines) > 20:
            box.label(text=f"... ({len(code_lines) - 20} more lines)")
        
        # Action buttons
        action_row = layout.row(align=True)
        action_row.scale_y = 1.2
        
        execute_op = action_row.operator("blendpro.execute_code", text="Execute Code", icon='PLAY')
        execute_op.code = self.code
        
        action_row.operator("blendpro.copy_code", text="Copy to Clipboard", icon='COPYDOWN')
    
    def execute(self, context):
        return {'FINISHED'}

class BLENDPRO_OT_ExecuteCode(bpy.types.Operator):
    """Execute provided code"""
    bl_idname = "blendpro.execute_code"
    bl_label = "Execute Code"
    bl_options = {'REGISTER', 'UNDO'}
    
    code: bpy.props.StringProperty()
    
    def execute(self, context):
        if not self.code:
            self.report({'ERROR'}, "No code provided")
            return {'CANCELLED'}
        
        # Execute code using code executor
        code_executor = get_code_executor()
        result = code_executor.execute_code(self.code)
        
        if result["success"]:
            self.report({'INFO'}, "Code executed successfully")
            
            # Print output to console if available
            if result.get("output"):
                print("Code execution output:")
                print(result["output"])
        else:
            error_msg = result.get("error", "Unknown error")
            self.report({'ERROR'}, f"Code execution failed: {error_msg}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class BLENDPRO_OT_CopyCode(bpy.types.Operator):
    """Copy code to clipboard"""
    bl_idname = "blendpro.copy_code"
    bl_label = "Copy Code"
    bl_options = {'REGISTER'}
    
    code: bpy.props.StringProperty()
    
    def execute(self, context):
        if not self.code:
            self.report({'ERROR'}, "No code to copy")
            return {'CANCELLED'}
        
        # Copy to clipboard
        context.window_manager.clipboard = self.code
        self.report({'INFO'}, "Code copied to clipboard")
        
        return {'FINISHED'}

def register():
    """Register Blender classes"""
    bpy.utils.register_class(BLENDPRO_PT_InteractivePanel)
    bpy.utils.register_class(BLENDPRO_OT_CodePreview)
    bpy.utils.register_class(BLENDPRO_OT_ExecuteCode)
    bpy.utils.register_class(BLENDPRO_OT_CopyCode)

def unregister():
    """Unregister Blender classes"""
    bpy.utils.unregister_class(BLENDPRO_OT_CopyCode)
    bpy.utils.unregister_class(BLENDPRO_OT_ExecuteCode)
    bpy.utils.unregister_class(BLENDPRO_OT_CodePreview)
    bpy.utils.unregister_class(BLENDPRO_PT_InteractivePanel)
