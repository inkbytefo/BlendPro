"""
Multi-Modal Vision for BlendPro: AI Co-Pilot
Combines visual and textual analysis for comprehensive scene understanding
"""

import json
from typing import Dict, List, Any, Optional
import bpy

from ..config.settings import get_settings
from ..config.prompts import get_system_prompt, PromptType
from ..utils.api_client import get_api_client, APIRequest
from .scene_analyzer import get_scene_analyzer
from .context_extractor import get_context_extractor
from .screenshot_manager import get_screenshot_manager

class MultiModalVision:
    """Combines visual and textual scene analysis"""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_client = get_api_client()
        self.scene_analyzer = get_scene_analyzer()
        self.context_extractor = get_context_extractor()
        self.screenshot_manager = get_screenshot_manager()
    
    def analyze_scene_with_vision(
        self, 
        context, 
        user_query: Optional[str] = None,
        focus_type: str = "auto"
    ) -> Dict[str, Any]:
        """Perform comprehensive scene analysis using both vision and data"""
        
        try:
            # Get scene data
            scene_data = self.scene_analyzer.analyze_scene(context)
            
            # Extract relevant context
            context_data = self.context_extractor.extract_context(
                user_query or "analyze scene", 
                focus_type, 
                scene_data
            )
            
            # Capture screenshot if vision is enabled
            screenshot_data = None
            if self.settings.enable_vision_context:
                screenshot_data = self.screenshot_manager.capture_viewport_screenshot(context)
            
            # Perform vision analysis
            vision_analysis = self._perform_vision_analysis(
                context_data, 
                screenshot_data, 
                user_query
            )
            
            return {
                "scene_data": context_data,
                "screenshot": screenshot_data,
                "vision_analysis": vision_analysis,
                "analysis_type": "multi_modal"
            }
            
        except Exception as e:
            return {"error": f"Multi-modal analysis failed: {str(e)}"}
    
    def _perform_vision_analysis(
        self, 
        scene_data: Dict[str, Any], 
        screenshot_data: Optional[Dict[str, Any]],
        user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform AI-powered vision analysis"""
        
        try:
            # Prepare the analysis prompt
            system_prompt = get_system_prompt(
                PromptType.VISION_ANALYZER,
                scene_data=json.dumps(scene_data, indent=2),
                visual_context="Screenshot provided" if screenshot_data else "No screenshot available",
                analysis_focus=user_query or "General scene analysis"
            )
            
            # Build the message content
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add user query if provided
            if user_query:
                messages.append({
                    "role": "user", 
                    "content": f"Analyze the scene with focus on: {user_query}"
                })
            else:
                messages.append({
                    "role": "user",
                    "content": "Provide a comprehensive analysis of this Blender scene."
                })
            
            # Add screenshot if available
            if screenshot_data and not screenshot_data.get("error"):
                # For vision-capable models, add the image
                if self._is_vision_model_available():
                    messages[-1]["content"] = [
                        {"type": "text", "text": messages[-1]["content"]},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_data['base64_image']}"
                            }
                        }
                    ]
            
            # Make API request
            request = APIRequest(
                messages=messages,
                model=self._get_vision_model(),
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=1000
            )
            
            response = self.api_client.make_request(request, use_vision=True)
            
            if response.error:
                return {"error": response.error, "fallback_used": False}
            
            return {
                "analysis": response.content,
                "model_used": request.model,
                "has_visual_input": screenshot_data is not None and not screenshot_data.get("error"),
                "fallback_used": False
            }
            
        except Exception as e:
            # Fallback to text-only analysis
            return self._fallback_text_analysis(scene_data, user_query, str(e))
    
    def _fallback_text_analysis(
        self, 
        scene_data: Dict[str, Any], 
        user_query: Optional[str],
        error_reason: str
    ) -> Dict[str, Any]:
        """Fallback to text-only analysis when vision fails"""
        
        try:
            # Use text-only model for analysis
            system_prompt = get_system_prompt(PromptType.VISION_ANALYZER)
            
            # Create detailed text description of scene
            scene_description = self._create_scene_description(scene_data)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
Scene Description:
{scene_description}

Analysis Request: {user_query or 'General scene analysis'}

Please analyze this Blender scene based on the provided data.
"""}
            ]
            
            request = APIRequest(
                messages=messages,
                model=self.settings.custom_model if self.settings.use_custom_model else "gpt-4",
                temperature=0.3,
                max_tokens=800
            )
            
            response = self.api_client.make_request(request)
            
            return {
                "analysis": response.content if not response.error else "Analysis failed",
                "model_used": request.model,
                "has_visual_input": False,
                "fallback_used": True,
                "fallback_reason": error_reason
            }
            
        except Exception as e:
            return {
                "error": f"Both vision and fallback analysis failed: {str(e)}",
                "fallback_used": True
            }
    
    def _create_scene_description(self, scene_data: Dict[str, Any]) -> str:
        """Create detailed text description of scene data"""
        
        description_parts = []
        
        # Objects
        objects = scene_data.get("objects", [])
        if objects:
            description_parts.append(f"Scene contains {len(objects)} objects:")
            for obj in objects[:10]:  # Limit to first 10 objects
                obj_desc = f"- {obj['name']} ({obj['type']})"
                if obj.get("selected"):
                    obj_desc += " [SELECTED]"
                if obj.get("active"):
                    obj_desc += " [ACTIVE]"
                description_parts.append(obj_desc)
            
            if len(objects) > 10:
                description_parts.append(f"... and {len(objects) - 10} more objects")
        
        # Materials
        materials = scene_data.get("materials", [])
        if materials:
            description_parts.append(f"\nMaterials ({len(materials)}):")
            for mat in materials[:5]:  # Limit to first 5 materials
                description_parts.append(f"- {mat['name']} (users: {mat.get('users', 0)})")
        
        # Lights
        lights = scene_data.get("lights", [])
        if lights:
            description_parts.append(f"\nLighting ({len(lights)} lights):")
            for light in lights:
                description_parts.append(f"- {light['name']} ({light['light_type']}, energy: {light['energy']})")
        
        # Cameras
        cameras = scene_data.get("cameras", [])
        if cameras:
            description_parts.append(f"\nCameras ({len(cameras)}):")
            for cam in cameras:
                cam_desc = f"- {cam['name']} (lens: {cam['lens']}mm)"
                if cam.get("is_active"):
                    cam_desc += " [ACTIVE]"
                description_parts.append(cam_desc)
        
        # Context type
        context_type = scene_data.get("context_type")
        if context_type:
            description_parts.insert(0, f"Context focus: {context_type}")
        
        return "\n".join(description_parts)
    
    def _is_vision_model_available(self) -> bool:
        """Check if a vision-capable model is configured"""
        
        vision_config = self.settings.get_vision_api_config()
        model = vision_config.get("model", "")
        
        # Check if model supports vision
        vision_models = [
            "gpt-4-vision-preview", "gpt-4o", "gpt-4o-mini",
            "claude-3-5-sonnet", "claude-3-opus", "claude-3-sonnet", "claude-3-haiku"
        ]
        
        return any(vm in model for vm in vision_models)
    
    def _get_vision_model(self) -> str:
        """Get the configured vision model"""
        
        vision_config = self.settings.get_vision_api_config()
        return vision_config.get("model", "gpt-4-vision-preview")
    
    def analyze_spatial_relationships(
        self, 
        context, 
        objects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze spatial relationships between objects"""
        
        try:
            # Get scene data
            scene_data = self.scene_analyzer.analyze_scene(context)
            
            # Filter objects if specified
            if objects:
                filtered_objects = [
                    obj for obj in scene_data.get("objects", [])
                    if obj["name"] in objects
                ]
            else:
                filtered_objects = scene_data.get("objects", [])
            
            # Analyze relationships
            relationships = []
            
            for i, obj1 in enumerate(filtered_objects):
                for obj2 in filtered_objects[i+1:]:
                    relationship = self._calculate_spatial_relationship(obj1, obj2)
                    if relationship:
                        relationships.append(relationship)
            
            return {
                "relationships": relationships,
                "analyzed_objects": len(filtered_objects),
                "total_relationships": len(relationships)
            }
            
        except Exception as e:
            return {"error": f"Spatial analysis failed: {str(e)}"}
    
    def _calculate_spatial_relationship(self, obj1: Dict[str, Any], obj2: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate spatial relationship between two objects"""
        
        try:
            from mathutils import Vector
            
            pos1 = Vector(obj1["location"])
            pos2 = Vector(obj2["location"])
            
            distance = (pos1 - pos2).length
            direction = (pos2 - pos1).normalized()
            
            # Determine relative position
            relative_pos = "near"
            if distance > 5.0:
                relative_pos = "far"
            elif distance > 2.0:
                relative_pos = "medium"
            
            # Determine direction
            if abs(direction.z) > 0.7:
                spatial_dir = "above" if direction.z > 0 else "below"
            elif abs(direction.x) > abs(direction.y):
                spatial_dir = "right" if direction.x > 0 else "left"
            else:
                spatial_dir = "front" if direction.y > 0 else "back"
            
            return {
                "object1": obj1["name"],
                "object2": obj2["name"],
                "distance": round(distance, 2),
                "relative_position": relative_pos,
                "direction": spatial_dir,
                "relationship": f"{obj1['name']} is {relative_pos} and to the {spatial_dir} of {obj2['name']}"
            }
            
        except Exception:
            return None
    
    def get_vision_capabilities(self) -> Dict[str, Any]:
        """Get information about available vision capabilities"""
        
        return {
            "vision_model_available": self._is_vision_model_available(),
            "screenshot_available": self.screenshot_manager is not None,
            "scene_analysis_available": True,
            "spatial_analysis_available": True,
            "multi_view_available": True,
            "configured_vision_model": self._get_vision_model(),
            "vision_context_enabled": self.settings.enable_vision_context
        }

# Global multi-modal vision instance
_multi_modal_vision: Optional[MultiModalVision] = None

def get_multi_modal_vision() -> MultiModalVision:
    """Get global multi-modal vision instance"""
    global _multi_modal_vision
    if _multi_modal_vision is None:
        _multi_modal_vision = MultiModalVision()
    return _multi_modal_vision
