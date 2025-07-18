"""
Proactive Suggestions for BlendPro: AI Co-Pilot
Generates intelligent suggestions based on user workflow and scene state
"""

import time
import json
from typing import Dict, List, Any, Optional, Set
from collections import deque
from dataclasses import dataclass
from enum import Enum

from ..config.settings import get_settings
from ..config.prompts import get_system_prompt, PromptType
from ..utils.api_client import get_api_client, APIRequest
from ..vision.scene_analyzer import get_scene_analyzer
from ..core.conversation_memory import get_conversation_memory

class SuggestionType(Enum):
    """Types of proactive suggestions"""
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    SCENE_IMPROVEMENT = "scene_improvement"
    LEARNING_TIP = "learning_tip"
    PERFORMANCE_TIP = "performance_tip"
    CREATIVE_IDEA = "creative_idea"
    BEST_PRACTICE = "best_practice"

@dataclass
class ProactiveSuggestion:
    """Represents a proactive suggestion"""
    suggestion_type: SuggestionType
    title: str
    description: str
    priority: int  # 1-10, higher is more important
    context: Dict[str, Any]
    actionable: bool
    action_code: Optional[str] = None
    learn_more_url: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

class ProactiveSuggestions:
    """Generates and manages proactive suggestions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_client = get_api_client()
        self.scene_analyzer = get_scene_analyzer()
        self.conversation_memory = get_conversation_memory()
        
        self._suggestion_history: deque = deque(maxlen=100)
        self._active_suggestions: deque = deque(maxlen=self.settings.max_suggestions)
        self._user_patterns: Dict[str, Any] = {}
        self._dismissed_suggestions: Set[str] = set()
        
        # Suggestion generators
        self._suggestion_generators = [
            self._generate_workflow_suggestions,
            self._generate_scene_improvement_suggestions,
            self._generate_learning_suggestions,
            self._generate_performance_suggestions,
            self._generate_creative_suggestions
        ]
    
    def generate_suggestions(self, context, trigger_event: str = "periodic") -> List[ProactiveSuggestion]:
        """Generate proactive suggestions based on current context"""
        
        if not self.settings.enable_proactive_suggestions:
            return []
        
        try:
            # Get scene data
            scene_data = self.scene_analyzer.analyze_scene(context)
            
            if scene_data.get("error"):
                return []
            
            # Update user patterns
            self._update_user_patterns(scene_data, trigger_event)
            
            # Generate suggestions from all generators
            all_suggestions = []
            
            for generator in self._suggestion_generators:
                try:
                    suggestions = generator(scene_data, context, trigger_event)
                    all_suggestions.extend(suggestions)
                except Exception as e:
                    print(f"Suggestion generator error: {e}")
                    continue
            
            # Filter and prioritize suggestions
            filtered_suggestions = self._filter_and_prioritize(all_suggestions)
            
            # Add to active suggestions
            for suggestion in filtered_suggestions:
                self._active_suggestions.append(suggestion)
                self._suggestion_history.append(suggestion)
            
            return filtered_suggestions
            
        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return []
    
    def _generate_workflow_suggestions(
        self, 
        scene_data: Dict[str, Any], 
        context, 
        trigger_event: str
    ) -> List[ProactiveSuggestion]:
        """Generate workflow optimization suggestions"""
        
        suggestions = []
        
        # Check for repetitive actions
        conversation_stats = self.conversation_memory.get_memory_stats()
        most_mentioned = conversation_stats.get("most_mentioned_entities", [])
        
        if len(most_mentioned) > 0:
            top_entity = most_mentioned[0]
            if top_entity[1] > 3:  # Mentioned more than 3 times
                suggestions.append(ProactiveSuggestion(
                    suggestion_type=SuggestionType.WORKFLOW_OPTIMIZATION,
                    title=f"Frequent work with {top_entity[0]}",
                    description=f"You've been working with '{top_entity[0]}' frequently. Consider creating a custom action or using collections for better organization.",
                    priority=6,
                    context={"entity": top_entity[0], "mentions": top_entity[1]},
                    actionable=True,
                    action_code=f"""
# Create collection for {top_entity[0]} workflow
import bpy
collection = bpy.data.collections.new("{top_entity[0]}_Workflow")
bpy.context.scene.collection.children.link(collection)
"""
                ))
        
        # Check for unorganized scene
        objects = scene_data.get("objects", [])
        collections = scene_data.get("collections", [])
        
        if len(objects) > 10 and len(collections) <= 1:
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.WORKFLOW_OPTIMIZATION,
                title="Scene Organization",
                description=f"Your scene has {len(objects)} objects but minimal organization. Consider using collections to group related objects.",
                priority=7,
                context={"object_count": len(objects), "collection_count": len(collections)},
                actionable=True,
                action_code="""
import bpy

# Create basic collections
collections_to_create = ["Geometry", "Lights", "Cameras", "Helpers"]

for coll_name in collections_to_create:
    if coll_name not in bpy.data.collections:
        collection = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(collection)

# Auto-organize objects by type
for obj in bpy.context.scene.objects:
    target_collection = None
    
    if obj.type == 'MESH':
        target_collection = bpy.data.collections.get("Geometry")
    elif obj.type == 'LIGHT':
        target_collection = bpy.data.collections.get("Lights")
    elif obj.type == 'CAMERA':
        target_collection = bpy.data.collections.get("Cameras")
    else:
        target_collection = bpy.data.collections.get("Helpers")
    
    if target_collection and obj.name not in target_collection.objects:
        target_collection.objects.link(obj)
        bpy.context.scene.collection.objects.unlink(obj)
"""
            ))
        
        return suggestions
    
    def _generate_scene_improvement_suggestions(
        self, 
        scene_data: Dict[str, Any], 
        context, 
        trigger_event: str
    ) -> List[ProactiveSuggestion]:
        """Generate scene improvement suggestions"""
        
        suggestions = []
        
        # Check lighting setup
        lights = scene_data.get("lights", [])
        
        if len(lights) == 0:
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.SCENE_IMPROVEMENT,
                title="Add Lighting",
                description="Your scene has no lights. Adding proper lighting will dramatically improve the visual quality.",
                priority=8,
                context={"light_count": 0},
                actionable=True,
                action_code="""
import bpy

# Add a three-point lighting setup
# Key light
bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
key_light = bpy.context.active_object
key_light.name = "Key_Light"
key_light.data.energy = 3.0

# Fill light
bpy.ops.object.light_add(type='AREA', location=(-3, -3, 4))
fill_light = bpy.context.active_object
fill_light.name = "Fill_Light"
fill_light.data.energy = 1.5
fill_light.data.size = 2.0

# Rim light
bpy.ops.object.light_add(type='SPOT', location=(0, 5, 6))
rim_light = bpy.context.active_object
rim_light.name = "Rim_Light"
rim_light.data.energy = 2.0
rim_light.data.spot_size = 1.2
"""
            ))
        
        elif len(lights) == 1 and lights[0].get("light_type") == "SUN":
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.SCENE_IMPROVEMENT,
                title="Enhance Lighting Setup",
                description="You have basic lighting. Consider adding fill and rim lights for more professional results.",
                priority=6,
                context={"current_lights": lights},
                actionable=True,
                action_code="""
import bpy

# Add fill light to complement existing sun light
bpy.ops.object.light_add(type='AREA', location=(-3, -3, 4))
fill_light = bpy.context.active_object
fill_light.name = "Fill_Light"
fill_light.data.energy = 1.0
fill_light.data.size = 3.0
"""
            ))
        
        # Check materials
        objects_without_materials = [
            obj for obj in scene_data.get("objects", [])
            if obj["type"] == "MESH" and obj.get("material_slots", 0) == 0
        ]
        
        if len(objects_without_materials) > 0:
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.SCENE_IMPROVEMENT,
                title="Add Materials",
                description=f"{len(objects_without_materials)} objects don't have materials. Materials greatly improve visual appeal.",
                priority=7,
                context={"objects_without_materials": len(objects_without_materials)},
                actionable=True,
                action_code=f"""
import bpy

# Create a set of basic materials
material_configs = [
    {{"name": "Plastic_Red", "color": (0.8, 0.2, 0.2, 1.0), "roughness": 0.3, "metallic": 0.0}},
    {{"name": "Metal_Steel", "color": (0.7, 0.7, 0.8, 1.0), "roughness": 0.2, "metallic": 1.0}},
    {{"name": "Wood_Oak", "color": (0.6, 0.4, 0.2, 1.0), "roughness": 0.8, "metallic": 0.0}},
    {{"name": "Ceramic_White", "color": (0.9, 0.9, 0.9, 1.0), "roughness": 0.1, "metallic": 0.0}}
]

# Create materials
created_materials = []
for config in material_configs:
    if config["name"] not in bpy.data.materials:
        mat = bpy.data.materials.new(name=config["name"])
        mat.use_nodes = True
        
        # Set up basic principled BSDF
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = config["color"]
            bsdf.inputs["Roughness"].default_value = config["roughness"]
            bsdf.inputs["Metallic"].default_value = config["metallic"]
        
        created_materials.append(mat)

# Assign materials to objects without them
objects_without_materials = {[obj["name"] for obj in objects_without_materials]}
for i, obj_name in enumerate(objects_without_materials):
    obj = bpy.data.objects.get(obj_name)
    if obj and obj.type == 'MESH':
        mat = created_materials[i % len(created_materials)]
        if len(obj.material_slots) == 0:
            obj.data.materials.append(mat)
        else:
            obj.material_slots[0].material = mat
"""
            ))
        
        return suggestions
    
    def _generate_learning_suggestions(
        self, 
        scene_data: Dict[str, Any], 
        context, 
        trigger_event: str
    ) -> List[ProactiveSuggestion]:
        """Generate learning tips and educational suggestions"""
        
        suggestions = []
        
        # Check user's apparent skill level based on scene complexity
        objects = scene_data.get("objects", [])
        materials = scene_data.get("materials", [])
        modifiers_used = sum(len(obj.get("modifiers", [])) for obj in objects)
        
        # Beginner tips
        if len(objects) < 5 and len(materials) < 2 and modifiers_used == 0:
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.LEARNING_TIP,
                title="Learn About Modifiers",
                description="Modifiers are powerful tools that can transform your objects non-destructively. Try adding a Subdivision Surface modifier to smooth your geometry.",
                priority=4,
                context={"skill_level": "beginner"},
                actionable=True,
                action_code="""
import bpy

# Add subdivision surface to selected object
if bpy.context.active_object and bpy.context.active_object.type == 'MESH':
    obj = bpy.context.active_object
    
    # Check if subdivision surface already exists
    if "Subdivision Surface" not in [mod.name for mod in obj.modifiers]:
        mod = obj.modifiers.new('Subdivision Surface', 'SUBSURF')
        mod.levels = 2
        print(f"Added Subdivision Surface modifier to {obj.name}")
else:
    print("Please select a mesh object first")
""",
                learn_more_url="https://docs.blender.org/manual/en/latest/modeling/modifiers/"
            ))
        
        # Intermediate tips
        elif len(objects) >= 5 and modifiers_used > 0:
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.LEARNING_TIP,
                title="Explore Node-Based Materials",
                description="You're using modifiers well! Next, try creating complex materials using the Shader Editor's node system for more realistic results.",
                priority=5,
                context={"skill_level": "intermediate"},
                actionable=False,
                learn_more_url="https://docs.blender.org/manual/en/latest/render/shader_nodes/"
            ))
        
        return suggestions

    def _generate_performance_suggestions(
        self,
        scene_data: Dict[str, Any],
        context,
        trigger_event: str
    ) -> List[ProactiveSuggestion]:
        """Generate performance optimization suggestions"""

        suggestions = []

        # Check for high-poly objects
        high_poly_objects = []
        for obj in scene_data.get("objects", []):
            if obj["type"] == "MESH" and obj.get("vertices", 0) > 50000:
                high_poly_objects.append(obj["name"])

        if high_poly_objects:
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.PERFORMANCE_TIP,
                title="Optimize High-Poly Objects",
                description=f"Found {len(high_poly_objects)} high-polygon objects that might slow down your workflow.",
                priority=6,
                context={"high_poly_objects": high_poly_objects},
                actionable=True,
                action_code=f"""
import bpy

# Add decimate modifiers to high-poly objects
high_poly_objects = {high_poly_objects}

for obj_name in high_poly_objects:
    obj = bpy.data.objects.get(obj_name)
    if obj and obj.type == 'MESH':
        # Check if decimate modifier already exists
        if "Decimate_Optimize" not in [mod.name for mod in obj.modifiers]:
            mod = obj.modifiers.new('Decimate_Optimize', 'DECIMATE')
            mod.ratio = 0.5  # Reduce by 50%
            mod.use_collapse_triangulate = True
            print(f"Added decimate modifier to {{obj_name}}")
"""
            ))

        # Check viewport performance
        total_objects = len(scene_data.get("objects", []))
        if total_objects > 500:
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.PERFORMANCE_TIP,
                title="Scene Complexity Warning",
                description=f"Your scene has {total_objects} objects. Consider using instancing or collections to improve viewport performance.",
                priority=7,
                context={"object_count": total_objects},
                actionable=False,
                learn_more_url="https://docs.blender.org/manual/en/latest/scene_layout/object/editing/duplicate.html"
            ))

        return suggestions

    def _generate_creative_suggestions(
        self,
        scene_data: Dict[str, Any],
        context,
        trigger_event: str
    ) -> List[ProactiveSuggestion]:
        """Generate creative ideas and inspiration"""

        suggestions = []

        # Analyze scene content for creative suggestions
        objects = scene_data.get("objects", [])
        object_types = [obj["type"] for obj in objects]

        # Suggest adding variety
        if object_types.count("MESH") > 5 and "LIGHT" not in object_types:
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.CREATIVE_IDEA,
                title="Dramatic Lighting",
                description="Your scene has good geometry. Try adding colored lights or volumetric lighting for dramatic effect.",
                priority=4,
                context={"scene_content": "geometry_heavy"},
                actionable=True,
                action_code="""
import bpy

# Add colored volumetric lighting
bpy.ops.object.light_add(type='SPOT', location=(0, 0, 5))
light = bpy.context.active_object
light.name = "Volumetric_Spot"

# Set up volumetric properties
light.data.energy = 5.0
light.data.color = (0.3, 0.7, 1.0)  # Blue tint
light.data.spot_size = 1.5
light.data.show_cone = True

# Enable volumetrics in world settings
world = bpy.context.scene.world
if world:
    world.use_nodes = True
    nodes = world.node_tree.nodes

    # Add volume scatter node
    volume_scatter = nodes.new(type='ShaderNodeVolumeScatter')
    volume_scatter.inputs['Density'].default_value = 0.1

    # Connect to world output
    world_output = nodes.get('World Output')
    if world_output:
        world.node_tree.links.new(volume_scatter.outputs['Volume'], world_output.inputs['Volume'])
"""
            ))

        return suggestions

    def _filter_and_prioritize(self, suggestions: List[ProactiveSuggestion]) -> List[ProactiveSuggestion]:
        """Filter and prioritize suggestions"""

        # Remove dismissed suggestions
        filtered = [
            s for s in suggestions
            if self._get_suggestion_id(s) not in self._dismissed_suggestions
        ]

        # Remove duplicates
        seen_ids = set()
        unique_suggestions = []
        for suggestion in filtered:
            suggestion_id = self._get_suggestion_id(suggestion)
            if suggestion_id not in seen_ids:
                seen_ids.add(suggestion_id)
                unique_suggestions.append(suggestion)

        # Sort by priority (higher first)
        unique_suggestions.sort(key=lambda s: s.priority, reverse=True)

        # Limit to max suggestions
        return unique_suggestions[:self.settings.max_suggestions]

    def _get_suggestion_id(self, suggestion: ProactiveSuggestion) -> str:
        """Generate unique ID for suggestion"""
        import hashlib

        id_string = f"{suggestion.suggestion_type.value}_{suggestion.title}_{suggestion.description[:50]}"
        return hashlib.md5(id_string.encode()).hexdigest()[:8]

    def _update_user_patterns(self, scene_data: Dict[str, Any], trigger_event: str) -> None:
        """Update user behavior patterns"""

        current_time = time.time()

        # Track object types user works with
        object_types = [obj["type"] for obj in scene_data.get("objects", [])]

        if "preferred_object_types" not in self._user_patterns:
            self._user_patterns["preferred_object_types"] = {}

        for obj_type in object_types:
            if obj_type not in self._user_patterns["preferred_object_types"]:
                self._user_patterns["preferred_object_types"][obj_type] = 0
            self._user_patterns["preferred_object_types"][obj_type] += 1

        # Track session activity
        if "session_activity" not in self._user_patterns:
            self._user_patterns["session_activity"] = []

        self._user_patterns["session_activity"].append({
            "timestamp": current_time,
            "trigger": trigger_event,
            "object_count": len(scene_data.get("objects", [])),
            "material_count": len(scene_data.get("materials", []))
        })

        # Keep only recent activity (last 100 events)
        self._user_patterns["session_activity"] = self._user_patterns["session_activity"][-100:]

    def dismiss_suggestion(self, suggestion_id: str) -> None:
        """Dismiss a suggestion so it won't appear again"""
        self._dismissed_suggestions.add(suggestion_id)

    def get_active_suggestions(self) -> List[Dict[str, Any]]:
        """Get currently active suggestions"""

        return [self._suggestion_to_dict(s) for s in self._active_suggestions]

    def get_suggestion_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get suggestion history"""

        recent_suggestions = list(self._suggestion_history)[-limit:]
        return [self._suggestion_to_dict(s) for s in recent_suggestions]

    def _suggestion_to_dict(self, suggestion: ProactiveSuggestion) -> Dict[str, Any]:
        """Convert suggestion to dictionary"""

        return {
            "id": self._get_suggestion_id(suggestion),
            "type": suggestion.suggestion_type.value,
            "title": suggestion.title,
            "description": suggestion.description,
            "priority": suggestion.priority,
            "context": suggestion.context,
            "actionable": suggestion.actionable,
            "action_code": suggestion.action_code,
            "learn_more_url": suggestion.learn_more_url,
            "timestamp": suggestion.timestamp
        }

    def clear_suggestions(self) -> None:
        """Clear all active suggestions"""
        self._active_suggestions.clear()

    def get_user_patterns(self) -> Dict[str, Any]:
        """Get user behavior patterns"""
        return self._user_patterns.copy()

    def get_suggestion_stats(self) -> Dict[str, Any]:
        """Get suggestion system statistics"""

        return {
            "active_suggestions": len(self._active_suggestions),
            "total_generated": len(self._suggestion_history),
            "dismissed_count": len(self._dismissed_suggestions),
            "enabled": self.settings.enable_proactive_suggestions,
            "max_suggestions": self.settings.max_suggestions
        }

# Global proactive suggestions instance
_proactive_suggestions: Optional[ProactiveSuggestions] = None

def get_proactive_suggestions() -> ProactiveSuggestions:
    """Get global proactive suggestions instance"""
    global _proactive_suggestions
    if _proactive_suggestions is None:
        _proactive_suggestions = ProactiveSuggestions()
    return _proactive_suggestions
