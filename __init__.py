import sys
import os
import bpy
import bpy.props
import re

# Add the 'libs' folder to the Python path
libs_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib")
if libs_path not in sys.path:
    sys.path.append(libs_path)

from openai import OpenAI

from .utilities import *
bl_info = {
    "name": "GPT-4 Blender Assistant",
    "blender": (2, 82, 0),
    "category": "Object",
    "author": "Aarya (@gd3kr)",
    "version": (2, 0, 0),
    "location": "3D View > UI > GPT-4 Blender Assistant",
    "description": "Generate Blender Python code using OpenAI's GPT-4 to perform various tasks.",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
}

system_prompt = """You are an assistant made for the purposes of helping the user with Blender, the 3D software. 
- Respond with your answers in markdown (```). 
- Preferably import entire modules instead of bits. 
- Do not perform destructive operations on the meshes. 
- Do not use cap_ends. Do not do more than what is asked (setting up render settings, adding cameras, etc)
- Do not respond with anything that is not Python code.

Example:

user: create 10 cubes in random locations from -10 to 10
assistant:
```
import bpy
import random
bpy.ops.mesh.primitive_cube_add()

#how many cubes you want to add
count = 10

for c in range(0,count):
    x = random.randint(-10,10)
    y = random.randint(-10,10)
    z = random.randint(-10,10)
    bpy.ops.mesh.primitive_cube_add(location=(x,y,z))
```"""



class GPT4_OT_DeleteMessage(bpy.types.Operator):
    bl_idname = "gpt4.delete_message"
    bl_label = "Delete Message"
    bl_options = {'REGISTER', 'UNDO'}

    message_index: bpy.props.IntProperty()

    def execute(self, context):
        context.scene.gpt4_chat_history.remove(self.message_index)
        return {'FINISHED'}

class GPT4_OT_ApplySuggestion(bpy.types.Operator):
    bl_idname = "gpt4.apply_suggestion"
    bl_label = "Apply Suggestion"
    bl_options = {'REGISTER', 'UNDO'}

    suggestion_text: bpy.props.StringProperty()

    def execute(self, context):
        context.scene.gpt4_chat_input = self.suggestion_text
        return {'FINISHED'}

class GPT4_OT_RefreshSceneContext(bpy.types.Operator):
    bl_idname = "gpt4.refresh_scene_context"
    bl_label = "Refresh Scene Context"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Force refresh of scene context
        scene_summary = get_scene_summary()
        self.report({'INFO'}, f"Scene context refreshed: {scene_summary.get('total_objects', 0)} objects found")
        return {'FINISHED'}

class GPT4_OT_ShowCode(bpy.types.Operator):
    bl_idname = "gpt4.show_code"
    bl_label = "Show Code"
    bl_options = {'REGISTER', 'UNDO'}

    code: bpy.props.StringProperty(
        name="Code",
        description="The generated code",
        default="",
    )

    def execute(self, context):
        text_name = "GPT4_Generated_Code.py"
        text = bpy.data.texts.get(text_name)
        if text is None:
            text = bpy.data.texts.new(text_name)

        text.clear()
        text.write(self.code)

        text_editor_area = None
        for area in context.screen.areas:
            if area.type == 'TEXT_EDITOR':
                text_editor_area = area
                break

        if text_editor_area is None:
            text_editor_area = split_area_to_text_editor(context)
        
        text_editor_area.spaces.active.text = text

        return {'FINISHED'}

class GPT4_PT_Panel(bpy.types.Panel):
    bl_label = "GPT-4 Blender Assistant"
    bl_idname = "GPT4_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GPT-4 Assistant'

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        # Scene Context Preview Section
        if context.scene.gpt4_show_scene_preview:
            row = column.row()
            row.label(text="Scene Context:", icon="SCENE_DATA")
            row.operator("gpt4.refresh_scene_context", text="", icon="FILE_REFRESH")
            preview_box = column.box()
            scene_summary = get_scene_summary()
            if scene_summary:
                preview_box.label(text=f"Objects: {scene_summary.get('total_objects', 0)}")
                preview_box.label(text=f"Lights: {scene_summary.get('total_lights', 0)}")
                preview_box.label(text=f"Cameras: {scene_summary.get('total_cameras', 0)}")
                if scene_summary.get('selected_objects'):
                    preview_box.label(text=f"Selected: {', '.join(scene_summary['selected_objects'][:3])}")
                if scene_summary.get('active_object'):
                    preview_box.label(text=f"Active: {scene_summary['active_object']}")
            column.separator()

        # Smart Features Toggle Section
        column.label(text="Smart Features:", icon="SETTINGS")
        features_box = column.box()
        features_box.prop(context.scene, "gpt4_show_scene_preview", text="Scene Preview")
        features_box.prop(context.scene, "gpt4_show_intent_analysis", text="Intent Analysis")
        features_box.prop(context.scene, "gpt4_use_smart_prompts", text="Smart Prompts")
        features_box.prop(context.scene, "gpt4_show_suggestions", text="Command Suggestions")
        column.separator()

        # Intent Analysis Feedback Section
        if context.scene.gpt4_show_intent_analysis and context.scene.gpt4_last_intent_analysis:
            column.label(text="Intent Analysis:", icon="VIEWZOOM")
            intent_box = column.box()
            analysis_str = context.scene.gpt4_last_intent_analysis
            try:
                analysis = eval(analysis_str) if analysis_str else {}
                if isinstance(analysis, dict):
                    intent_box.label(text=f"Intent: {analysis.get('intent', 'Unknown')}")
                    intent_box.label(text=f"Confidence: {analysis.get('confidence', 0):.1f}%")
                    if analysis.get('parameters'):
                        intent_box.label(text="Parameters:")
                        for key, value in list(analysis['parameters'].items())[:3]:
                            intent_box.label(text=f"  {key}: {value}")
                else:
                    intent_box.label(text="Analysis data not available")
            except:
                intent_box.label(text="Analysis data not available")
            column.separator()

        # Command Suggestions Section
        if context.scene.gpt4_show_suggestions and context.scene.gpt4_chat_input:
            suggestions = get_intent_suggestions(context.scene.gpt4_chat_input)
            if suggestions:
                column.label(text="Suggestions:", icon="LIGHTBULB")
                suggestions_box = column.box()
                for suggestion in suggestions[:3]:
                    row = suggestions_box.row()
                    op = row.operator("gpt4.apply_suggestion", text=suggestion)
                    op.suggestion_text = suggestion
                column.separator()

        column.label(text="Chat history:")
        box = column.box()
        for index, message in enumerate(context.scene.gpt4_chat_history):
            if message.type == 'assistant':
                row = box.row()
                row.label(text="Assistant: ")
                show_code_op = row.operator("gpt4.show_code", text="Show Code")
                show_code_op.code = message.content
                delete_message_op = row.operator("gpt4.delete_message", text="", icon="TRASH", emboss=False)
                delete_message_op.message_index = index
            else:
                row = box.row()
                row.label(text=f"User: {message.content}")
                delete_message_op = row.operator("gpt4.delete_message", text="", icon="TRASH", emboss=False)
                delete_message_op.message_index = index

        column.separator()
        
        column.label(text="GPT Model:")
        column.prop(context.scene, "gpt4_model", text="")

        column.label(text="Enter your message:")
        column.prop(context.scene, "gpt4_chat_input", text="")
        
        # Progress indicator and quality score
        if context.scene.gpt4_button_pressed:
            column.label(text="Processing...", icon="TIME")
            if hasattr(context.scene, 'gpt4_progress'):
                column.prop(context.scene, "gpt4_progress", text="Progress", slider=True)
        
        if hasattr(context.scene, 'gpt4_last_prompt_quality') and context.scene.gpt4_last_prompt_quality > 0:
            quality_text = f"Last Prompt Quality: {context.scene.gpt4_last_prompt_quality:.1f}/10"
            column.label(text=quality_text, icon="CHECKMARK" if context.scene.gpt4_last_prompt_quality >= 7 else "ERROR")
        
        button_label = "Please wait...(this might take some time)" if context.scene.gpt4_button_pressed else "Execute"
        row = column.row(align=True)
        row.operator("gpt4.send_message", text=button_label)
        row.operator("gpt4.clear_chat", text="Clear Chat")

        column.separator()

class GPT4_OT_ClearChat(bpy.types.Operator):
    bl_idname = "gpt4.clear_chat"
    bl_label = "Clear Chat"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.gpt4_chat_history.clear()
        return {'FINISHED'}

class GPT4_OT_Execute(bpy.types.Operator):
    bl_idname = "gpt4.send_message"
    bl_label = "Send Message"
    bl_options = {'REGISTER', 'UNDO'}

    natural_language_input: bpy.props.StringProperty(
        name="Command",
        description="Enter the natural language command",
        default="",
    )

    def execute(self, context):
        api_key = get_api_key(context, __name__)
        # if null then set to env key
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            self.report({'ERROR'}, "No OpenAI API key detected. Please set the API key in the addon preferences or OPENAI_API_KEY environment variable.")
            return {'CANCELLED'}

        context.scene.gpt4_button_pressed = True
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        
        user_input = context.scene.gpt4_chat_input
        
        # Perform intent analysis if enabled
        if context.scene.gpt4_show_intent_analysis:
            intent_analysis = analyze_user_intent(user_input)
            context.scene.gpt4_last_intent_analysis = str(intent_analysis)  # Store as string for Blender property
        
        # Use smart prompts if enabled, otherwise use traditional method
        if context.scene.gpt4_use_smart_prompts:
            blender_code = generate_blender_code_with_context(
                user_input, 
                context, 
                context.scene.gpt4_chat_history, 
                "",  # system_prompt
                api_key
            )
            
            # Calculate and store prompt quality score
            if hasattr(context.scene, 'gpt4_last_intent_analysis'):
                try:
                    analysis = eval(context.scene.gpt4_last_intent_analysis)
                    quality_score = get_prompt_quality_score(user_input, analysis, get_scene_summary())
                    context.scene.gpt4_last_prompt_quality = quality_score
                except:
                    context.scene.gpt4_last_prompt_quality = 5.0
        else:
            blender_code = generate_blender_code(user_input, context.scene.gpt4_chat_history, context, system_prompt, api_key)

        message = context.scene.gpt4_chat_history.add()
        message.type = 'user'
        message.content = user_input

        # Clear the chat input field
        context.scene.gpt4_chat_input = ""

    
        if blender_code:
            message = context.scene.gpt4_chat_history.add()
            message.type = 'assistant'
            message.content = blender_code

            global_namespace = globals().copy()
        else:
            self.report({'ERROR'}, "Failed to generate code. Please check your API key and try again.")
            context.scene.gpt4_button_pressed = False
            return {'CANCELLED'}
    
        try:
            exec(blender_code, global_namespace)
        except SyntaxError as e:
            self.report({'ERROR'}, f"Syntax error in generated code: {e}")
            context.scene.gpt4_button_pressed = False
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error executing generated code: {e}")
            context.scene.gpt4_button_pressed = False
            return {'CANCELLED'}

        

        context.scene.gpt4_button_pressed = False
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(GPT4_OT_Execute.bl_idname)

class GPT4AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    api_key: bpy.props.StringProperty(
        name="API Key",
        description="Enter your OpenAI API Key",
        default="",
        subtype="PASSWORD",
    )
    
    custom_base_url: bpy.props.StringProperty(
        name="Custom Base URL",
        description="Custom OpenAI-compatible API base URL (leave empty for default OpenAI)",
        default="",
    )
    
    custom_model: bpy.props.StringProperty(
        name="Model Name",
        description="Model name to use (e.g., gpt-4, gpt-3.5-turbo, or custom model)",
        default="gpt-4",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.prop(self, "custom_base_url")
        layout.prop(self, "custom_model")

def register():
    bpy.utils.register_class(GPT4AddonPreferences)
    bpy.utils.register_class(GPT4_OT_Execute)
    bpy.utils.register_class(GPT4_PT_Panel)
    bpy.utils.register_class(GPT4_OT_ClearChat)
    bpy.utils.register_class(GPT4_OT_ShowCode)
    bpy.utils.register_class(GPT4_OT_DeleteMessage)
    bpy.utils.register_class(GPT4_OT_ApplySuggestion)
    bpy.utils.register_class(GPT4_OT_RefreshSceneContext)


    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
    init_props()


def unregister():
    bpy.utils.unregister_class(GPT4AddonPreferences)
    bpy.utils.unregister_class(GPT4_OT_Execute)
    bpy.utils.unregister_class(GPT4_PT_Panel)
    bpy.utils.unregister_class(GPT4_OT_ClearChat)
    bpy.utils.unregister_class(GPT4_OT_ShowCode)
    bpy.utils.unregister_class(GPT4_OT_DeleteMessage)
    bpy.utils.unregister_class(GPT4_OT_ApplySuggestion)
    bpy.utils.unregister_class(GPT4_OT_RefreshSceneContext)

    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    clear_props()


if __name__ == "__main__":
    register()
