"""
Scene Analyzer for BlendPro: AI Co-Pilot
Comprehensive Blender scene analysis and data extraction
"""

import bpy
import bmesh
import mathutils
from typing import Dict, List, Any, Optional, Tuple
import time

from ..config.settings import get_settings

class SceneAnalyzer:
    """Analyzes Blender scenes and extracts comprehensive data"""
    
    def __init__(self):
        self.settings = get_settings()
        self._cache = {}
        self._cache_timeout = 5.0  # seconds
    
    def analyze_scene(self, context, use_cache: bool = True) -> Dict[str, Any]:
        """Perform comprehensive scene analysis"""
        
        cache_key = "full_scene_analysis"
        
        # Check cache if enabled
        if use_cache and self.settings.enable_caching:
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
        
        try:
            analysis_start = time.time()
            
            scene_data = {
                "metadata": self._extract_scene_metadata(context),
                "objects": self._extract_object_data(context),
                "materials": self._extract_material_data(context),
                "lights": self._extract_lighting_data(context),
                "cameras": self._extract_camera_data(context),
                "world": self._extract_world_data(context),
                "render_settings": self._extract_render_settings(context),
                "viewport_info": self._extract_viewport_info(context),
                "hierarchy": self._extract_object_hierarchy(context),
                "collections": self._extract_collection_data(context),
                "analysis_time": time.time() - analysis_start
            }
            
            # Cache result
            if use_cache and self.settings.enable_caching:
                self._cache_result(cache_key, scene_data)
            
            return scene_data
            
        except Exception as e:
            return {"error": f"Scene analysis failed: {str(e)}"}
    
    def _extract_scene_metadata(self, context) -> Dict[str, Any]:
        """Extract basic scene metadata"""
        scene = context.scene
        
        return {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "render_engine": scene.render.engine,
            "unit_system": scene.unit_settings.system,
            "unit_scale": scene.unit_settings.scale_length,
            "gravity": list(scene.gravity) if hasattr(scene, 'gravity') else [0, 0, -9.81]
        }
    
    def _extract_object_data(self, context) -> List[Dict[str, Any]]:
        """Extract detailed object information"""
        objects = []
        
        for obj in context.scene.objects:
            try:
                # Safely get active object to avoid context errors
                active_object = getattr(context, 'active_object', None)

                obj_data = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": list(obj.location),
                    "rotation_euler": list(obj.rotation_euler),
                    "scale": list(obj.scale),
                    "dimensions": list(obj.dimensions),
                    "visible": obj.visible_get(),
                    "selected": obj.select_get(),
                    "active": obj == active_object if active_object else False,
                    "parent": obj.parent.name if obj.parent else None,
                    "children": [child.name for child in obj.children],
                    "material_slots": len(obj.material_slots),
                    "modifiers": [mod.name for mod in obj.modifiers],
                    "constraints": [con.name for con in obj.constraints]
                }
                
                # Add type-specific data
                if obj.type == 'MESH':
                    obj_data.update(self._extract_mesh_data(obj))
                elif obj.type == 'LIGHT':
                    obj_data.update(self._extract_light_specific_data(obj))
                elif obj.type == 'CAMERA':
                    obj_data.update(self._extract_camera_specific_data(obj))
                
                objects.append(obj_data)
                
            except Exception as e:
                print(f"Error extracting data for object {obj.name}: {e}")
                continue
        
        return objects
    
    def _extract_mesh_data(self, obj) -> Dict[str, Any]:
        """Extract mesh-specific data"""
        if not obj.data:
            return {}
        
        mesh = obj.data
        
        # Get basic mesh stats
        mesh_data = {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "faces": len(mesh.polygons),
            "materials": [mat.name if mat else None for mat in obj.data.materials],
            "uv_layers": len(mesh.uv_layers),
            "vertex_colors": len(mesh.vertex_colors)
        }
        
        # Check for common issues
        issues = []
        
        # Check for non-manifold geometry (simplified check)
        if len(mesh.vertices) > 0:
            bm = None
            try:
                # Create bmesh for analysis
                bm = bmesh.new()
                bm.from_mesh(mesh)

                # Check for non-manifold
                non_manifold = [v for v in bm.verts if not v.is_manifold]
                if non_manifold:
                    issues.append(f"Non-manifold vertices: {len(non_manifold)}")

                # Check for loose geometry
                loose_verts = [v for v in bm.verts if not v.link_edges]
                if loose_verts:
                    issues.append(f"Loose vertices: {len(loose_verts)}")

            except Exception as e:
                print(f"bmesh analysis failed: {e}")
            finally:
                if bm:
                    bm.free()
        
        mesh_data["issues"] = issues
        return mesh_data
    
    def _extract_material_data(self, context) -> List[Dict[str, Any]]:
        """Extract material information"""
        materials = []
        
        for mat in bpy.data.materials:
            if mat.users > 0:  # Only include used materials
                mat_data = {
                    "name": mat.name,
                    "use_nodes": mat.use_nodes,
                    "users": mat.users,
                    "diffuse_color": list(mat.diffuse_color) if hasattr(mat, 'diffuse_color') else None,
                    "metallic": getattr(mat, 'metallic', 0.0),
                    "roughness": getattr(mat, 'roughness', 0.5),
                    "alpha": mat.diffuse_color[3] if hasattr(mat, 'diffuse_color') and len(mat.diffuse_color) > 3 else 1.0
                }
                
                # Node information if using nodes
                if mat.use_nodes and mat.node_tree:
                    nodes = []
                    for node in mat.node_tree.nodes:
                        nodes.append({
                            "name": node.name,
                            "type": node.type,
                            "location": list(node.location)
                        })
                    mat_data["nodes"] = nodes
                
                materials.append(mat_data)
        
        return materials
    
    def _extract_lighting_data(self, context) -> List[Dict[str, Any]]:
        """Extract lighting information"""
        lights = []
        
        for obj in context.scene.objects:
            if obj.type == 'LIGHT':
                light_data = {
                    "name": obj.name,
                    "location": list(obj.location),
                    "rotation": list(obj.rotation_euler),
                    "light_type": obj.data.type,
                    "energy": obj.data.energy,
                    "color": list(obj.data.color),
                    "visible": obj.visible_get()
                }
                
                # Type-specific properties
                if obj.data.type == 'SUN':
                    light_data["angle"] = obj.data.angle
                elif obj.data.type == 'SPOT':
                    light_data["spot_size"] = obj.data.spot_size
                    light_data["spot_blend"] = obj.data.spot_blend
                elif obj.data.type == 'AREA':
                    light_data["size"] = obj.data.size
                elif obj.data.type == 'POINT':
                    # Point lights don't have a size property in Blender 4.4+
                    light_data["shadow_soft_size"] = getattr(obj.data, 'shadow_soft_size', 0.25)
                
                lights.append(light_data)
        
        return lights
    
    def _extract_camera_data(self, context) -> List[Dict[str, Any]]:
        """Extract camera information"""
        cameras = []
        
        for obj in context.scene.objects:
            if obj.type == 'CAMERA':
                cam_data = {
                    "name": obj.name,
                    "location": list(obj.location),
                    "rotation": list(obj.rotation_euler),
                    "lens": obj.data.lens,
                    "sensor_width": obj.data.sensor_width,
                    "sensor_height": obj.data.sensor_height,
                    "clip_start": obj.data.clip_start,
                    "clip_end": obj.data.clip_end,
                    "type": obj.data.type,
                    "is_active": obj == context.scene.camera
                }
                cameras.append(cam_data)
        
        return cameras
    
    def _extract_world_data(self, context) -> Dict[str, Any]:
        """Extract world/environment data"""
        world = context.scene.world
        
        if not world:
            return {}
        
        world_data = {
            "name": world.name,
            "use_nodes": world.use_nodes,
            "color": list(world.color) if hasattr(world, 'color') else [0.05, 0.05, 0.05]
        }
        
        # Node information if using nodes
        if world.use_nodes and world.node_tree:
            nodes = []
            for node in world.node_tree.nodes:
                nodes.append({
                    "name": node.name,
                    "type": node.type
                })
            world_data["nodes"] = nodes
        
        return world_data
    
    def _extract_render_settings(self, context) -> Dict[str, Any]:
        """Extract render settings"""
        render = context.scene.render
        
        return {
            "engine": render.engine,
            "resolution_x": render.resolution_x,
            "resolution_y": render.resolution_y,
            "resolution_percentage": render.resolution_percentage,
            "frame_map_old": render.frame_map_old,
            "frame_map_new": render.frame_map_new,
            "fps": render.fps,
            "filepath": render.filepath
        }
    
    def _extract_viewport_info(self, context) -> Dict[str, Any]:
        """Extract viewport information"""
        try:
            area = context.area
            space = context.space_data
            
            if area and area.type == 'VIEW_3D' and space:
                return {
                    "viewport_shade": space.shading.type,
                    "show_overlays": space.overlay.show_overlays,
                    "show_wireframes": space.overlay.show_wireframes,
                    "clip_start": space.clip_start,
                    "clip_end": space.clip_end,
                    "lens": space.lens
                }
        except:
            pass
        
        return {}
    
    def _extract_object_hierarchy(self, context) -> Dict[str, Any]:
        """Extract object hierarchy information"""
        hierarchy = {
            "root_objects": [],
            "parent_child_relationships": {}
        }
        
        for obj in context.scene.objects:
            if not obj.parent:
                hierarchy["root_objects"].append(obj.name)
            
            if obj.children:
                hierarchy["parent_child_relationships"][obj.name] = [child.name for child in obj.children]
        
        return hierarchy
    
    def _extract_collection_data(self, context) -> List[Dict[str, Any]]:
        """Extract collection information"""
        collections = []
        
        for collection in bpy.data.collections:
            if collection.users > 0:
                coll_data = {
                    "name": collection.name,
                    "objects": [obj.name for obj in collection.objects],
                    "children": [child.name for child in collection.children],
                    "hide_viewport": collection.hide_viewport,
                    "hide_render": collection.hide_render
                }
                collections.append(coll_data)
        
        return collections
    
    def _extract_light_specific_data(self, obj) -> Dict[str, Any]:
        """Extract light-specific data"""
        return {
            "light_type": obj.data.type,
            "energy": obj.data.energy,
            "color": list(obj.data.color)
        }
    
    def _extract_camera_specific_data(self, obj) -> Dict[str, Any]:
        """Extract camera-specific data"""
        return {
            "lens": obj.data.lens,
            "sensor_width": obj.data.sensor_width,
            "is_active_camera": obj == bpy.context.scene.camera
        }
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if valid"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_timeout:
                return cached_data
        return None
    
    def _cache_result(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Cache analysis result"""
        self._cache[cache_key] = (data, time.time())
    
    def clear_cache(self) -> None:
        """Clear analysis cache"""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cached_analyses": len(self._cache),
            "cache_timeout": self._cache_timeout
        }

# Global scene analyzer instance
_scene_analyzer: Optional[SceneAnalyzer] = None

def get_scene_analyzer() -> SceneAnalyzer:
    """Get global scene analyzer instance"""
    global _scene_analyzer
    if _scene_analyzer is None:
        _scene_analyzer = SceneAnalyzer()
    return _scene_analyzer
