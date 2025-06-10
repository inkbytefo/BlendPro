import bpy
from openai import OpenAI
import re
import os
import sys
import json
import mathutils


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
    
    # New UI feature properties
    bpy.types.Scene.gpt4_show_scene_preview = bpy.props.BoolProperty(
        name="Show Scene Preview",
        description="Display current scene context information",
        default=True,
    )
    bpy.types.Scene.gpt4_show_intent_analysis = bpy.props.BoolProperty(
        name="Show Intent Analysis",
        description="Display intent analysis feedback",
        default=True,
    )
    bpy.types.Scene.gpt4_use_smart_prompts = bpy.props.BoolProperty(
        name="Use Smart Prompts",
        description="Enable smart prompt engineering system",
        default=True,
    )
    bpy.types.Scene.gpt4_show_suggestions = bpy.props.BoolProperty(
        name="Show Command Suggestions",
        description="Display command suggestions while typing",
        default=True,
    )
    bpy.types.Scene.gpt4_last_intent_analysis = bpy.props.StringProperty(
        name="Last Intent Analysis",
        description="Store last intent analysis result",
        default="",
    )
    bpy.types.Scene.gpt4_last_prompt_quality = bpy.props.FloatProperty(
        name="Last Prompt Quality",
        description="Quality score of the last generated prompt",
        default=0.0,
        min=0.0,
        max=10.0,
    )
    bpy.types.Scene.gpt4_progress = bpy.props.FloatProperty(
        name="Progress",
        description="Processing progress indicator",
        default=0.0,
        min=0.0,
        max=100.0,
        subtype='PERCENTAGE',
    )
    
    bpy.types.PropertyGroup.type = bpy.props.StringProperty()
    bpy.types.PropertyGroup.content = bpy.props.StringProperty()

def clear_props():
    del bpy.types.Scene.gpt4_chat_history
    del bpy.types.Scene.gpt4_chat_input
    del bpy.types.Scene.gpt4_button_pressed
    del bpy.types.Scene.gpt4_show_scene_preview
    del bpy.types.Scene.gpt4_show_intent_analysis
    del bpy.types.Scene.gpt4_use_smart_prompts
    del bpy.types.Scene.gpt4_show_suggestions
    del bpy.types.Scene.gpt4_last_intent_analysis
    del bpy.types.Scene.gpt4_last_prompt_quality
    del bpy.types.Scene.gpt4_progress

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
    # Store current area count to identify new area
    initial_area_count = len(context.screen.areas)
    
    # Set the current area as active
    context.window.screen = context.screen
    
    # Split the area (Blender 4.4+ doesn't need context override)
    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
    
    # Find the new area (should be the last one added)
    if len(context.screen.areas) > initial_area_count:
        new_area = context.screen.areas[-1]
        new_area.type = 'TEXT_EDITOR'
        return new_area
    else:
        # Fallback: return the current area if split failed
        return context.area


# Scene Context API Functions
def get_scene_context():
    """Analyze current Blender scene and return structured context data"""
    scene_data = {
        "scene_info": get_scene_info(),
        "objects": get_objects_info(),
        "materials": get_materials_info(),
        "lights": get_lights_info(),
        "cameras": get_cameras_info(),
        "world_settings": get_world_settings()
    }
    return scene_data

def get_scene_info():
    """Get basic scene information"""
    scene = bpy.context.scene
    return {
        "name": scene.name,
        "frame_current": scene.frame_current,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "render_engine": scene.render.engine,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "total_objects": len(bpy.data.objects)
    }

def get_objects_info():
    """Get information about all objects in the scene"""
    objects_data = []
    
    for obj in bpy.data.objects:
        if obj.name in bpy.context.scene.objects:
            obj_data = {
                "name": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "scale": list(obj.scale),
                "visible": not obj.hide_viewport,
                "selected": obj.select_get() if hasattr(obj, 'select_get') else False
            }
            
            # Add mesh-specific data
            if obj.type == 'MESH' and obj.data:
                obj_data["mesh_info"] = {
                    "vertices_count": len(obj.data.vertices),
                    "faces_count": len(obj.data.polygons),
                    "materials_count": len(obj.data.materials)
                }
            
            # Add modifier information
            if obj.modifiers:
                obj_data["modifiers"] = [{
                    "name": mod.name,
                    "type": mod.type
                } for mod in obj.modifiers]
            
            objects_data.append(obj_data)
    
    return objects_data

def get_materials_info():
    """Get information about all materials in the scene"""
    materials_data = []
    
    for material in bpy.data.materials:
        if material.users > 0:  # Only include materials that are actually used
            mat_data = {
                "name": material.name,
                "use_nodes": material.use_nodes,
                "users": material.users
            }
            
            # Add basic material properties
            if hasattr(material, 'diffuse_color'):
                mat_data["diffuse_color"] = list(material.diffuse_color)
            
            # Add node information if using nodes
            if material.use_nodes and material.node_tree:
                nodes_info = []
                for node in material.node_tree.nodes:
                    node_info = {
                        "name": node.name,
                        "type": node.type,
                        "location": list(node.location)
                    }
                    nodes_info.append(node_info)
                mat_data["nodes"] = nodes_info
            
            materials_data.append(mat_data)
    
    return materials_data

def get_lights_info():
    """Get information about all lights in the scene"""
    lights_data = []
    
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT' and obj.name in bpy.context.scene.objects:
            light_data = {
                "name": obj.name,
                "type": obj.data.type,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "energy": obj.data.energy,
                "color": list(obj.data.color),
                "visible": not obj.hide_viewport
            }
            
            # Add light-specific properties
            if obj.data.type == 'SUN':
                light_data["angle"] = obj.data.angle
            elif obj.data.type in ['POINT', 'SPOT']:
                light_data["shadow_soft_size"] = obj.data.shadow_soft_size
                if obj.data.type == 'SPOT':
                    light_data["spot_size"] = obj.data.spot_size
                    light_data["spot_blend"] = obj.data.spot_blend
            
            lights_data.append(light_data)
    
    return lights_data

def get_cameras_info():
    """Get information about all cameras in the scene"""
    cameras_data = []
    
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA' and obj.name in bpy.context.scene.objects:
            camera_data = {
                "name": obj.name,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "lens": obj.data.lens,
                "sensor_width": obj.data.sensor_width,
                "clip_start": obj.data.clip_start,
                "clip_end": obj.data.clip_end,
                "is_active": obj == bpy.context.scene.camera
            }
            cameras_data.append(camera_data)
    
    return cameras_data

def get_world_settings():
    """Get world/environment settings"""
    world = bpy.context.scene.world
    world_data = {
        "name": world.name if world else "No World",
        "use_nodes": world.use_nodes if world else False
    }
    
    if world and world.use_nodes and world.node_tree:
        # Get background color/HDRI info
        for node in world.node_tree.nodes:
            if node.type == 'BACKGROUND':
                if len(node.inputs) > 0 and hasattr(node.inputs[0], 'default_value'):
                    world_data["background_color"] = list(node.inputs[0].default_value[:3])
                if len(node.inputs) > 1:
                    world_data["background_strength"] = node.inputs[1].default_value
                break
    
    return world_data

def get_scene_context_json():
    """Get scene context as JSON string"""
    try:
        context_data = get_scene_context()
        return json.dumps(context_data, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to get scene context: {str(e)}"})

def get_scene_summary():
    """Get a structured summary of the scene for UI display"""
    try:
        context = get_scene_context()
        
        # Get selected and active objects
        selected_objects = []
        active_object = None
        
        for obj in bpy.data.objects:
            if obj.name in bpy.context.scene.objects:
                if hasattr(obj, 'select_get') and obj.select_get():
                    selected_objects.append(obj.name)
                if bpy.context.active_object and obj == bpy.context.active_object:
                    active_object = obj.name
        
        summary = {
            "scene_name": context['scene_info']['name'],
            "total_objects": len(context['objects']),
            "total_lights": len(context['lights']),
            "total_cameras": len(context['cameras']),
            "total_materials": len(context['materials']),
            "render_engine": context['scene_info']['render_engine'],
            "selected_objects": selected_objects,
            "active_object": active_object,
            "object_types": {}
        }
        
        # Object types breakdown
        for obj in context['objects']:
            obj_type = obj['type']
            summary["object_types"][obj_type] = summary["object_types"].get(obj_type, 0) + 1
        
        return summary
    except Exception as e:
        return {
            "error": f"Error generating scene summary: {str(e)}",
            "total_objects": 0,
            "total_lights": 0,
            "total_cameras": 0,
            "total_materials": 0,
            "selected_objects": [],
            "active_object": None
        }


# Natural Language Processing Functions
def analyze_user_intent(user_input):
    """Analyze user input and determine the intent and parameters"""
    user_input = user_input.lower().strip()
    
    intent_patterns = {
        'create_object': {
            'keywords': ['create', 'add', 'make', 'generate', 'spawn'],
            'objects': ['cube', 'sphere', 'cylinder', 'plane', 'monkey', 'torus', 'cone'],
            'modifiers': ['subdivision', 'mirror', 'array', 'bevel', 'solidify']
        },
        'modify_object': {
            'keywords': ['move', 'rotate', 'scale', 'resize', 'transform', 'change'],
            'properties': ['location', 'position', 'rotation', 'scale', 'size']
        },
        'delete_object': {
            'keywords': ['delete', 'remove', 'destroy', 'clear']
        },
        'material_operation': {
            'keywords': ['material', 'texture', 'color', 'shader'],
            'actions': ['apply', 'create', 'change', 'set']
        },
        'lighting_operation': {
            'keywords': ['light', 'lighting', 'illuminate', 'brightness'],
            'types': ['sun', 'point', 'spot', 'area']
        },
        'camera_operation': {
            'keywords': ['camera', 'view', 'angle', 'focus'],
            'actions': ['move', 'rotate', 'focus', 'set']
        },
        'render_operation': {
            'keywords': ['render', 'output', 'export'],
            'formats': ['png', 'jpg', 'exr', 'blend']
        },
        'scene_query': {
            'keywords': ['what', 'how many', 'list', 'show', 'tell me', 'describe']
        }
    }
    
    detected_intent = 'unknown'
    confidence = 0.0
    parameters = {}
    
    # Analyze intent
    for intent, patterns in intent_patterns.items():
        keyword_matches = sum(1 for keyword in patterns['keywords'] if keyword in user_input)
        if keyword_matches > 0:
            current_confidence = keyword_matches / len(patterns['keywords'])
            if current_confidence > confidence:
                confidence = current_confidence
                detected_intent = intent
                
                # Extract specific parameters based on intent
                if intent == 'create_object':
                    for obj_type in patterns['objects']:
                        if obj_type in user_input:
                            parameters['object_type'] = obj_type
                            break
                    for modifier in patterns.get('modifiers', []):
                        if modifier in user_input:
                            parameters['modifier'] = modifier
                            break
                            
                elif intent == 'modify_object':
                    # Extract object name and property
                    words = user_input.split()
                    for i, word in enumerate(words):
                        if word in patterns['keywords'] and i + 1 < len(words):
                            parameters['target_object'] = words[i + 1]
                            break
                    for prop in patterns['properties']:
                        if prop in user_input:
                            parameters['property'] = prop
                            break
                            
                elif intent == 'material_operation':
                    for action in patterns['actions']:
                        if action in user_input:
                            parameters['action'] = action
                            break
                    # Extract color if mentioned
                    colors = ['red', 'green', 'blue', 'yellow', 'white', 'black', 'gray', 'orange', 'purple']
                    for color in colors:
                        if color in user_input:
                            parameters['color'] = color
                            break
                            
                elif intent == 'lighting_operation':
                    for light_type in patterns['types']:
                        if light_type in user_input:
                            parameters['light_type'] = light_type
                            break
    
    # Extract numerical values
    import re
    numbers = re.findall(r'\d+(?:\.\d+)?', user_input)
    if numbers:
        parameters['values'] = [float(num) for num in numbers]
    
    return {
        'intent': detected_intent,
        'confidence': confidence,
        'parameters': parameters,
        'original_input': user_input
    }

def generate_blender_code_with_context(user_input, context, chat_history, system_prompt, api_key):
    """Generate Blender code using scene context and natural language processing"""
    # Analyze user intent
    intent_analysis = analyze_user_intent(user_input)
    
    # Get scene context
    scene_context = get_scene_context()
    scene_summary = get_scene_summary()
    
    # Create enhanced prompt with context
    enhanced_prompt = create_context_aware_prompt(
        user_input, 
        intent_analysis, 
        scene_context, 
        scene_summary
    )
    
    # Get addon preferences for custom settings
    addon_prefs = bpy.context.preferences.addons[__name__.split('.')[0]].preferences
    
    # Create OpenAI client with custom base URL if specified
    client_kwargs = {"api_key": api_key}
    if addon_prefs.custom_base_url and addon_prefs.custom_base_url.strip():
        client_kwargs["base_url"] = addon_prefs.custom_base_url.strip()
    
    client = OpenAI(**client_kwargs)
    
    # Prepare messages with enhanced context
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add scene context to system message
    context_message = f"""Current Blender Scene Context:
{scene_summary}

User Intent Analysis:
- Intent: {intent_analysis['intent']}
- Confidence: {intent_analysis['confidence']:.2f}
- Parameters: {intent_analysis['parameters']}

Please generate Blender Python code that takes into account the current scene state and the user's intent."""
    
    messages.append({"role": "system", "content": context_message})
    
    # Add chat history
    for message in chat_history[-8:]:  # Reduced to make room for context
        if message.type == "assistant":
            messages.append({"role": "assistant", "content": "```\n" + message.content + "\n```"})
        else:
            messages.append({"role": message.type.lower(), "content": message.content})
    
    # Add the enhanced user message
    messages.append({"role": "user", "content": enhanced_prompt})
    
    try:
        response = client.chat.completions.create(
            model=bpy.context.scene.gpt4_model,
            messages=messages,
            stream=True,
            max_tokens=1500,
        )
        
        completion_text = ''
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                event_text = chunk.choices[0].delta.content
                completion_text += event_text
                print(completion_text, flush=True, end='\r')
        
        # Extract code from markdown code blocks
        code_matches = re.findall(r'```(?:python)?\s*(.*?)```', completion_text, re.DOTALL)
        if code_matches:
            completion_text = code_matches[0].strip()
        else:
            completion_text = completion_text.strip()
        
        return completion_text
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return None

def create_context_aware_prompt(user_input, intent_analysis, scene_context, scene_summary):
    """Create an enhanced prompt that includes scene context and intent analysis"""
    
    base_prompt = f"Can you please write Blender code for me that accomplishes the following task: {user_input}?"
    
    # Add context-specific instructions based on intent
    if intent_analysis['intent'] == 'create_object':
        if 'object_type' in intent_analysis['parameters']:
            obj_type = intent_analysis['parameters']['object_type']
            base_prompt += f"\n\nSpecific requirements:\n- Create a {obj_type} object"
            if 'modifier' in intent_analysis['parameters']:
                modifier = intent_analysis['parameters']['modifier']
                base_prompt += f"\n- Apply {modifier} modifier"
    
    elif intent_analysis['intent'] == 'modify_object':
        if scene_context['objects']:
            base_prompt += "\n\nAvailable objects in scene:"
            for obj in scene_context['objects'][:5]:  # Limit to first 5 objects
                base_prompt += f"\n- {obj['name']} ({obj['type']}) at {obj['location']}"
        
        if 'target_object' in intent_analysis['parameters']:
            target = intent_analysis['parameters']['target_object']
            base_prompt += f"\n\nTarget object: {target}"
    
    elif intent_analysis['intent'] == 'material_operation':
        if scene_context['materials']:
            base_prompt += "\n\nExisting materials:"
            for mat in scene_context['materials'][:3]:
                base_prompt += f"\n- {mat['name']}"
    
    elif intent_analysis['intent'] == 'lighting_operation':
        if scene_context['lights']:
            base_prompt += "\n\nCurrent lights:"
            for light in scene_context['lights']:
                base_prompt += f"\n- {light['name']} ({light['type']}) - Energy: {light['energy']}"
    
    elif intent_analysis['intent'] == 'scene_query':
        base_prompt = f"Based on the current scene, please answer: {user_input}\n\nScene Information:\n{scene_summary}"
        return base_prompt
    
    # Add numerical values if detected
    if 'values' in intent_analysis['parameters'] and intent_analysis['parameters']['values']:
        values = intent_analysis['parameters']['values']
        base_prompt += f"\n\nNumerical values to use: {values}"
    
    base_prompt += "\n\nDo not respond with anything that is not Python code. Do not provide explanations."
    
    return base_prompt

def get_intent_suggestions(partial_input):
    """Get suggestions based on partial user input"""
    suggestions = []
    partial_input = partial_input.lower()
    
    common_commands = [
        "Create a cube",
        "Add a sphere",
        "Delete selected objects",
        "Move the cube to (0, 0, 2)",
        "Scale the object by 2",
        "Add a red material",
        "Create a sun light",
        "Rotate the camera",
        "What objects are in the scene?",
        "How many lights do I have?"
    ]
    
    for command in common_commands:
        if partial_input in command.lower() or command.lower().startswith(partial_input):
            suggestions.append(command)
    
    return suggestions[:5]  # Return top 5 suggestions


# Smart Prompt Engineering System
def get_prompt_templates():
    """Get predefined prompt templates for different intent types"""
    templates = {
        'create_object': {
            'base': "Create a {object_type} in Blender at position {position}.",
            'with_modifier': "Create a {object_type} in Blender at position {position} and apply a {modifier} modifier.",
            'with_material': "Create a {object_type} in Blender at position {position} with a {color} material.",
            'complex': "Create a {object_type} in Blender at position {position}, apply {modifier} modifier, and add {color} material."
        },
        'modify_object': {
            'transform': "Modify the {target_object} by changing its {property} to {values}.",
            'material': "Change the material of {target_object} to {color}.",
            'modifier': "Apply {modifier} modifier to {target_object}.",
            'complex': "Transform {target_object}: set {property} to {values} and apply {modifier}."
        },
        'delete_object': {
            'simple': "Delete the {target_object} from the scene.",
            'multiple': "Delete all {object_type} objects from the scene.",
            'conditional': "Delete {target_object} if it exists in the scene."
        },
        'material_operation': {
            'create': "Create a new {color} material named {material_name}.",
            'apply': "Apply {material_name} material to {target_object}.",
            'modify': "Modify {material_name} material to be {color} with {properties}."
        },
        'lighting_operation': {
            'create': "Add a {light_type} light at position {position} with energy {energy}.",
            'modify': "Change {light_name} light energy to {energy} and color to {color}.",
            'setup': "Set up a {lighting_setup} lighting configuration."
        },
        'camera_operation': {
            'position': "Move the camera to position {position} and look at {target}.",
            'settings': "Set camera {property} to {value}.",
            'animation': "Animate camera from {start_pos} to {end_pos}."
        },
        'render_operation': {
            'simple': "Render the scene and save as {filename}.{format}.",
            'settings': "Set render resolution to {width}x{height} and render as {format}.",
            'animation': "Render animation from frame {start} to {end}."
        },
        'scene_query': {
            'count': "Count the number of {object_type} objects in the scene.",
            'list': "List all {object_type} objects with their properties.",
            'analyze': "Analyze the current scene and provide a detailed report."
        }
    }
    return templates

def select_optimal_template(intent_analysis, scene_context):
    """Select the most appropriate template based on intent and available parameters"""
    templates = get_prompt_templates()
    intent = intent_analysis['intent']
    parameters = intent_analysis['parameters']
    
    if intent not in templates:
        return None
    
    intent_templates = templates[intent]
    
    # Score templates based on available parameters
    template_scores = {}
    
    for template_name, template in intent_templates.items():
        score = 0
        required_params = re.findall(r'\{(\w+)\}', template)
        
        for param in required_params:
            if param in parameters:
                score += 1
            elif param == 'position' and 'values' in parameters:
                score += 0.8  # Partial match for position
            elif param == 'target_object' and scene_context['objects']:
                score += 0.6  # Can infer from scene
        
        # Penalty for missing critical parameters
        missing_critical = len([p for p in required_params if p not in parameters and p not in ['position', 'target_object']])
        score -= missing_critical * 0.5
        
        template_scores[template_name] = score
    
    # Select template with highest score
    if template_scores:
        best_template = max(template_scores.items(), key=lambda x: x[1])
        if best_template[1] > 0:  # Only return if score is positive
            return intent_templates[best_template[0]]
    
    # Fallback to simple template
    return intent_templates.get('simple', intent_templates.get('base', None))

def fill_template_parameters(template, intent_analysis, scene_context):
    """Fill template with actual parameters from intent analysis and scene context"""
    if not template:
        return None
    
    parameters = intent_analysis['parameters'].copy()
    
    # Add default values for common parameters
    if 'position' not in parameters:
        if 'values' in parameters and len(parameters['values']) >= 3:
            parameters['position'] = f"({parameters['values'][0]}, {parameters['values'][1]}, {parameters['values'][2]})"
        else:
            parameters['position'] = "(0, 0, 0)"
    
    if 'target_object' not in parameters and scene_context['objects']:
        # Use the first object as default target
        parameters['target_object'] = scene_context['objects'][0]['name']
    
    if 'color' not in parameters:
        parameters['color'] = 'white'
    
    if 'energy' not in parameters:
        parameters['energy'] = '10'
    
    if 'material_name' not in parameters:
        parameters['material_name'] = f"{parameters.get('color', 'default')}_material"
    
    # Fill template
    try:
        filled_template = template.format(**parameters)
        return filled_template
    except KeyError as e:
        # Handle missing parameters gracefully
        return template.replace('{' + str(e).strip("'") + '}', '[PARAMETER_MISSING]')

def optimize_prompt_for_context(base_prompt, scene_context, intent_analysis):
    """Optimize prompt based on scene complexity and context"""
    optimized_prompt = base_prompt
    
    # Add scene complexity awareness
    object_count = len(scene_context['objects'])
    
    if object_count > 10:
        optimized_prompt += "\n\nNote: Scene has many objects. Be specific about target objects."
    elif object_count == 0:
        optimized_prompt += "\n\nNote: Scene is empty. Create objects as needed."
    
    # Add performance considerations
    if intent_analysis['intent'] in ['create_object', 'modify_object']:
        optimized_prompt += "\n\nEnsure efficient code execution and proper error handling."
    
    # Add context-specific instructions
    if scene_context['materials'] and intent_analysis['intent'] == 'material_operation':
        optimized_prompt += f"\n\nExisting materials: {[mat['name'] for mat in scene_context['materials'][:3]]}"
    
    if scene_context['lights'] and intent_analysis['intent'] == 'lighting_operation':
        optimized_prompt += f"\n\nCurrent lights: {[light['name'] for light in scene_context['lights']]}"
    
    return optimized_prompt

def generate_smart_prompt(user_input, scene_context=None, chat_history=None):
    """Generate an optimized prompt using template-based approach and context awareness"""
    # Get scene context if not provided
    if scene_context is None:
        scene_context = get_scene_context()
    
    # Analyze user intent
    intent_analysis = analyze_user_intent(user_input)
    
    # Try template-based approach first
    template = select_optimal_template(intent_analysis, scene_context)
    
    if template and intent_analysis['confidence'] > 0.3:
        # Use template-based generation
        base_prompt = fill_template_parameters(template, intent_analysis, scene_context)
        if base_prompt and '[PARAMETER_MISSING]' not in base_prompt:
            # Template was successfully filled
            optimized_prompt = optimize_prompt_for_context(base_prompt, scene_context, intent_analysis)
            return {
                'prompt': optimized_prompt,
                'method': 'template',
                'confidence': intent_analysis['confidence'],
                'intent': intent_analysis['intent']
            }
    
    # Fallback to context-aware approach
    fallback_prompt = create_context_aware_prompt(user_input, intent_analysis, scene_context, get_scene_summary())
    optimized_prompt = optimize_prompt_for_context(fallback_prompt, scene_context, intent_analysis)
    
    return {
        'prompt': optimized_prompt,
        'method': 'context_aware',
        'confidence': intent_analysis['confidence'],
        'intent': intent_analysis['intent']
    }

def get_prompt_quality_score(prompt_result, scene_context):
    """Calculate a quality score for the generated prompt"""
    score = 0
    
    # Base score from confidence
    score += prompt_result['confidence'] * 50
    
    # Method bonus
    if prompt_result['method'] == 'template':
        score += 30
    elif prompt_result['method'] == 'context_aware':
        score += 20
    
    # Intent clarity bonus
    if prompt_result['intent'] != 'unknown':
        score += 20
    
    # Context utilization bonus
    prompt_text = prompt_result['prompt'].lower()
    if 'scene' in prompt_text or 'object' in prompt_text:
        score += 10
    
    return min(score, 100)  # Cap at 100