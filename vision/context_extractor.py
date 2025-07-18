"""
Context Extractor for BlendPro: AI Co-Pilot
Extracts relevant context based on user focus and intent
"""

import bpy
from typing import Dict, List, Any, Optional, Set
import re

from ..config.settings import get_settings
from .scene_analyzer import get_scene_analyzer

class ContextExtractor:
    """Extracts context-sensitive scene information based on user focus"""
    
    def __init__(self):
        self.settings = get_settings()
        self.scene_analyzer = get_scene_analyzer()
    
    def extract_context(
        self, 
        user_input: str, 
        context_type: str = "auto",
        full_scene_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract relevant context based on user input and focus"""
        
        # Get full scene data if not provided
        if full_scene_data is None:
            full_scene_data = self.scene_analyzer.analyze_scene(bpy.context)
        
        # Determine context type if auto
        if context_type == "auto":
            context_type = self._determine_context_type(user_input, full_scene_data)
        
        # Extract context based on type
        if context_type == "selected":
            return self._extract_selected_context(full_scene_data)
        elif context_type == "visible":
            return self._extract_visible_context(full_scene_data)
        elif context_type == "mentioned":
            return self._extract_mentioned_context(user_input, full_scene_data)
        elif context_type == "active":
            return self._extract_active_context(full_scene_data)
        elif context_type == "materials":
            return self._extract_materials_context(full_scene_data)
        elif context_type == "lighting":
            return self._extract_lighting_context(full_scene_data)
        elif context_type == "cameras":
            return self._extract_cameras_context(full_scene_data)
        else:  # "full" or unknown
            return full_scene_data
    
    def _determine_context_type(self, user_input: str, scene_data: Dict[str, Any]) -> str:
        """Automatically determine the most relevant context type"""
        
        user_input_lower = user_input.lower()
        
        # Check for specific context keywords
        if any(word in user_input_lower for word in ["selected", "selection", "chosen"]):
            return "selected"
        
        if any(word in user_input_lower for word in ["visible", "see", "shown", "displayed"]):
            return "visible"
        
        if any(word in user_input_lower for word in ["active", "current"]):
            return "active"
        
        if any(word in user_input_lower for word in ["material", "shader", "texture", "color"]):
            return "materials"
        
        if any(word in user_input_lower for word in ["light", "lighting", "lamp", "illumination"]):
            return "lighting"
        
        if any(word in user_input_lower for word in ["camera", "view", "render"]):
            return "cameras"
        
        # Check if specific objects are mentioned
        mentioned_objects = self._find_mentioned_objects(user_input, scene_data)
        if mentioned_objects:
            return "mentioned"
        
        # Check if user has objects selected
        selected_objects = [obj for obj in scene_data.get("objects", []) if obj.get("selected", False)]
        if selected_objects:
            return "selected"
        
        # Default to visible objects if scene is complex
        total_objects = len(scene_data.get("objects", []))
        if total_objects > 20:
            return "visible"
        
        return "full"
    
    def _extract_selected_context(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context for selected objects only"""
        
        selected_objects = [obj for obj in scene_data.get("objects", []) if obj.get("selected", False)]
        
        if not selected_objects:
            # No selection, return minimal context
            return {
                "context_type": "selected",
                "message": "No objects selected",
                "objects": [],
                "materials": [],
                "summary": "No objects are currently selected in the scene."
            }
        
        # Get materials used by selected objects
        selected_materials = set()
        for obj in selected_objects:
            if obj.get("materials"):
                selected_materials.update(obj["materials"])
        
        relevant_materials = [
            mat for mat in scene_data.get("materials", [])
            if mat["name"] in selected_materials
        ]
        
        return {
            "context_type": "selected",
            "objects": selected_objects,
            "materials": relevant_materials,
            "active_object": scene_data.get("metadata", {}).get("active_object"),
            "summary": f"{len(selected_objects)} object(s) selected: {', '.join([obj['name'] for obj in selected_objects])}"
        }
    
    def _extract_visible_context(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context for visible objects only"""
        
        visible_objects = [obj for obj in scene_data.get("objects", []) if obj.get("visible", True)]
        
        # Get materials used by visible objects
        visible_materials = set()
        for obj in visible_objects:
            if obj.get("materials"):
                visible_materials.update(obj["materials"])
        
        relevant_materials = [
            mat for mat in scene_data.get("materials", [])
            if mat["name"] in visible_materials
        ]
        
        return {
            "context_type": "visible",
            "objects": visible_objects,
            "materials": relevant_materials,
            "lights": scene_data.get("lights", []),
            "cameras": scene_data.get("cameras", []),
            "summary": f"{len(visible_objects)} visible object(s) in scene"
        }
    
    def _extract_mentioned_context(self, user_input: str, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context for objects mentioned in user input"""
        
        mentioned_objects = self._find_mentioned_objects(user_input, scene_data)
        mentioned_materials = self._find_mentioned_materials(user_input, scene_data)
        
        # Get full object data for mentioned objects
        relevant_objects = [
            obj for obj in scene_data.get("objects", [])
            if obj["name"] in mentioned_objects
        ]
        
        # Get full material data for mentioned materials
        relevant_materials = [
            mat for mat in scene_data.get("materials", [])
            if mat["name"] in mentioned_materials
        ]
        
        return {
            "context_type": "mentioned",
            "objects": relevant_objects,
            "materials": relevant_materials,
            "mentioned_object_names": list(mentioned_objects),
            "mentioned_material_names": list(mentioned_materials),
            "summary": f"Mentioned: {len(mentioned_objects)} object(s), {len(mentioned_materials)} material(s)"
        }
    
    def _extract_active_context(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context for active object and related elements"""
        
        active_object_name = None
        active_object = None
        
        # Find active object
        for obj in scene_data.get("objects", []):
            if obj.get("active", False):
                active_object = obj
                active_object_name = obj["name"]
                break
        
        if not active_object:
            return {
                "context_type": "active",
                "message": "No active object",
                "objects": [],
                "summary": "No object is currently active in the scene."
            }
        
        # Get materials used by active object
        active_materials = []
        if active_object.get("materials"):
            active_materials = [
                mat for mat in scene_data.get("materials", [])
                if mat["name"] in active_object["materials"]
            ]
        
        return {
            "context_type": "active",
            "active_object": active_object,
            "objects": [active_object],
            "materials": active_materials,
            "summary": f"Active object: {active_object_name}"
        }
    
    def _extract_materials_context(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract materials-focused context"""
        
        materials = scene_data.get("materials", [])
        
        # Get objects that use materials
        objects_with_materials = [
            obj for obj in scene_data.get("objects", [])
            if obj.get("materials") and len(obj["materials"]) > 0
        ]
        
        return {
            "context_type": "materials",
            "materials": materials,
            "objects": objects_with_materials,
            "summary": f"{len(materials)} material(s) in scene, {len(objects_with_materials)} object(s) with materials"
        }
    
    def _extract_lighting_context(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract lighting-focused context"""
        
        lights = scene_data.get("lights", [])
        world_data = scene_data.get("world", {})
        
        return {
            "context_type": "lighting",
            "lights": lights,
            "world": world_data,
            "summary": f"{len(lights)} light(s) in scene"
        }
    
    def _extract_cameras_context(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract camera-focused context"""
        
        cameras = scene_data.get("cameras", [])
        active_camera = None
        
        for cam in cameras:
            if cam.get("is_active", False):
                active_camera = cam
                break
        
        return {
            "context_type": "cameras",
            "cameras": cameras,
            "active_camera": active_camera,
            "render_settings": scene_data.get("render_settings", {}),
            "summary": f"{len(cameras)} camera(s) in scene" + (f", active: {active_camera['name']}" if active_camera else "")
        }
    
    def _find_mentioned_objects(self, user_input: str, scene_data: Dict[str, Any]) -> Set[str]:
        """Find object names mentioned in user input"""
        
        mentioned = set()
        user_input_lower = user_input.lower()
        
        for obj in scene_data.get("objects", []):
            obj_name = obj["name"].lower()
            
            # Direct name match
            if obj_name in user_input_lower:
                mentioned.add(obj["name"])
                continue
            
            # Type-based matching
            obj_type = obj["type"].lower()
            if obj_type in user_input_lower:
                # Check if it's a specific reference like "the cube" or "cube.001"
                type_pattern = rf'\b{re.escape(obj_type)}\b'
                if re.search(type_pattern, user_input_lower):
                    mentioned.add(obj["name"])
        
        return mentioned
    
    def _find_mentioned_materials(self, user_input: str, scene_data: Dict[str, Any]) -> Set[str]:
        """Find material names mentioned in user input"""
        
        mentioned = set()
        user_input_lower = user_input.lower()
        
        for mat in scene_data.get("materials", []):
            mat_name = mat["name"].lower()
            
            # Direct name match
            if mat_name in user_input_lower:
                mentioned.add(mat["name"])
        
        return mentioned
    
    def get_context_summary(self, context_data: Dict[str, Any]) -> str:
        """Generate a human-readable summary of the context"""
        
        context_type = context_data.get("context_type", "unknown")
        
        if "summary" in context_data:
            return f"Context ({context_type}): {context_data['summary']}"
        
        # Generate summary based on context type
        objects_count = len(context_data.get("objects", []))
        materials_count = len(context_data.get("materials", []))
        
        summary_parts = [f"Context type: {context_type}"]
        
        if objects_count > 0:
            summary_parts.append(f"{objects_count} object(s)")
        
        if materials_count > 0:
            summary_parts.append(f"{materials_count} material(s)")
        
        return ", ".join(summary_parts)
    
    def filter_context_for_task(self, context_data: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """Filter context data based on task requirements"""
        
        if task_type == "modeling":
            # Focus on objects and their geometry
            return {
                "objects": context_data.get("objects", []),
                "hierarchy": context_data.get("hierarchy", {}),
                "collections": context_data.get("collections", [])
            }
        
        elif task_type == "materials":
            # Focus on materials and objects that use them
            return {
                "materials": context_data.get("materials", []),
                "objects": [obj for obj in context_data.get("objects", []) if obj.get("materials")]
            }
        
        elif task_type == "lighting":
            # Focus on lights and world settings
            return {
                "lights": context_data.get("lights", []),
                "world": context_data.get("world", {}),
                "cameras": context_data.get("cameras", [])
            }
        
        elif task_type == "animation":
            # Focus on objects with animation data
            return {
                "objects": context_data.get("objects", []),
                "metadata": context_data.get("metadata", {}),
                "hierarchy": context_data.get("hierarchy", {})
            }
        
        else:
            # Return full context for unknown task types
            return context_data

# Global context extractor instance
_context_extractor: Optional[ContextExtractor] = None

def get_context_extractor() -> ContextExtractor:
    """Get global context extractor instance"""
    global _context_extractor
    if _context_extractor is None:
        _context_extractor = ContextExtractor()
    return _context_extractor
