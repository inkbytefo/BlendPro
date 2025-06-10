import bpy
from openai import OpenAI
import re
import os
import sys


def get_api_key(context, addon_name):
    preferences = context.preferences
    addon_prefs = preferences.addons[addon_name].preferences
    return addon_prefs.api_key


def get_model_items(self, context):
    """Dynamic model list based on addon preferences"""
    addon_prefs = context.preferences.addons[__name__.split('.')[0]].preferences
    
    # Default models
    items = [
        ("gpt-4", "GPT-4 (powerful, expensive)", "Use GPT-4"),
        ("gpt-3.5-turbo", "GPT-3.5 Turbo (less powerful, cheaper)", "Use GPT-3.5 Turbo"),
        ("gpt-4-turbo", "GPT-4 Turbo (latest, fast)", "Use GPT-4 Turbo"),
        ("gpt-4o", "GPT-4o (optimized)", "Use GPT-4o"),
    ]
    
    # Add custom model if specified in preferences
    if addon_prefs.custom_model and addon_prefs.custom_model.strip():
        custom_model = addon_prefs.custom_model.strip()
        # Check if custom model is not already in the list
        if not any(item[0] == custom_model for item in items):
            items.append((custom_model, f"Custom: {custom_model}", f"Use custom model: {custom_model}"))
    
    return items

def init_props():
    bpy.types.Scene.gpt4_chat_history = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.gpt4_model = bpy.props.EnumProperty(
        name="GPT Model",
        description="Select the GPT model to use",
        items=get_model_items,
        default=0,  # Use index instead of string for dynamic enum
    )
    bpy.types.Scene.gpt4_chat_input = bpy.props.StringProperty(
        name="Message",
        description="Enter your message",
        default="",
    )
    bpy.types.Scene.gpt4_button_pressed = bpy.props.BoolProperty(default=False)
    bpy.types.PropertyGroup.type = bpy.props.StringProperty()
    bpy.types.PropertyGroup.content = bpy.props.StringProperty()

def clear_props():
    del bpy.types.Scene.gpt4_chat_history
    del bpy.types.Scene.gpt4_chat_input
    del bpy.types.Scene.gpt4_button_pressed

def generate_blender_code(prompt, chat_history, context, system_prompt, api_key):
    # Get addon preferences for custom settings
    addon_prefs = context.preferences.addons[__name__.split('.')[0]].preferences
    
    # Create OpenAI client with custom base URL if specified
    client_kwargs = {"api_key": api_key}
    if addon_prefs.custom_base_url and addon_prefs.custom_base_url.strip():
        client_kwargs["base_url"] = addon_prefs.custom_base_url.strip()
    
    client = OpenAI(**client_kwargs)
    
    messages = [{"role": "system", "content": system_prompt}]
    for message in chat_history[-10:]:
        if message.type == "assistant":
            messages.append({"role": "assistant", "content": "```\n" + message.content + "\n```"})
        else:
            messages.append({"role": message.type.lower(), "content": message.content})

    # Add the current user message
    messages.append({"role": "user", "content": "Can you please write Blender code for me that accomplishes the following task: " + prompt + "? \n. Do not respond with anything that is not Python code. Do not provide explanations"})

    try:
        response = client.chat.completions.create(
            model=context.scene.gpt4_model,
            messages=messages,
            stream=True,
            max_tokens=1500,
        )

        completion_text = ''
        # iterate through the stream of events
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                event_text = chunk.choices[0].delta.content
                completion_text += event_text  # append the text
                print(completion_text, flush=True, end='\r')
        
        # Extract code from markdown code blocks
        code_matches = re.findall(r'```(?:python)?\s*(.*?)```', completion_text, re.DOTALL)
        if code_matches:
            completion_text = code_matches[0].strip()
        else:
            # If no code blocks found, return the raw text
            completion_text = completion_text.strip()
        
        return completion_text
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return None

def split_area_to_text_editor(context):
    area = context.area
    for region in area.regions:
        if region.type == 'WINDOW':
            override = context.copy()
            override['area'] = area
            override['region'] = region
            bpy.ops.screen.area_split(context=override, direction='VERTICAL', factor=0.5)
            break

    new_area = context.screen.areas[-1]
    new_area.type = 'TEXT_EDITOR'
    return new_area