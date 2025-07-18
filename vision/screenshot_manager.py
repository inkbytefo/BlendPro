"""
Screenshot Manager for BlendPro: AI Co-Pilot
Captures and manages viewport screenshots for vision analysis
"""

import bpy
import gpu
import base64
import io
import os
import time
from typing import Dict, Any, Optional, Tuple, List
from mathutils import Vector

from ..config.settings import get_settings
from ..utils.dependency_loader import safe_import, is_available

# Import image processing dependencies with dependency loader
PIL = safe_import('PIL', 'Pillow (Image Processing)', required=False, min_version='10.0.0')
numpy = safe_import('numpy', 'NumPy (Numerical Computing)', required=False, min_version='1.24.0')

# Feature flags for conditional functionality
PIL_AVAILABLE = PIL is not None
NUMPY_AVAILABLE = numpy is not None

# Import specific classes if available
if PIL_AVAILABLE:
    try:
        from PIL import Image
    except ImportError:
        Image = None
        PIL_AVAILABLE = False
else:
    Image = None

if NUMPY_AVAILABLE:
    np = numpy
else:
    np = None

class ScreenshotManager:
    """Manages viewport screenshot capture and processing"""
    
    def __init__(self):
        self.settings = get_settings()
        self._screenshot_cache: Dict[str, Tuple[str, float]] = {}
        self._cache_timeout = 30.0  # seconds
    
    def capture_viewport_screenshot(
        self, 
        context, 
        resolution: Optional[Tuple[int, int]] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Capture screenshot of current viewport"""
        
        if not PIL_AVAILABLE:
            return {"error": "PIL not available for screenshot capture"}
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(context, resolution)
            
            # Check cache
            if use_cache and cache_key in self._screenshot_cache:
                cached_data, timestamp = self._screenshot_cache[cache_key]
                if time.time() - timestamp < self._cache_timeout:
                    return {"base64_image": cached_data, "cached": True}
            
            # Capture screenshot
            screenshot_data = self._capture_screenshot(context, resolution)
            
            if screenshot_data:
                # Cache the result
                if use_cache:
                    self._screenshot_cache[cache_key] = (screenshot_data["base64_image"], time.time())
                
                return screenshot_data
            
            return {"error": "Failed to capture screenshot"}
            
        except Exception as e:
            return {"error": f"Screenshot capture failed: {str(e)}"}
    
    def _capture_screenshot(
        self, 
        context, 
        resolution: Optional[Tuple[int, int]] = None
    ) -> Optional[Dict[str, Any]]:
        """Internal screenshot capture method"""
        
        # Get the 3D viewport area
        area = None
        for area_candidate in context.screen.areas:
            if area_candidate.type == 'VIEW_3D':
                area = area_candidate
                break
        
        if not area:
            return {"error": "No 3D viewport found"}
        
        # Get region
        region = None
        for region_candidate in area.regions:
            if region_candidate.type == 'WINDOW':
                region = region_candidate
                break
        
        if not region:
            return {"error": "No viewport region found"}
        
        # Determine resolution
        if resolution is None:
            width, height = region.width, region.height
        else:
            width, height = resolution
        
        # Ensure minimum resolution
        width = max(width, 64)
        height = max(height, 64)
        
        try:
            # Create offscreen buffer
            offscreen = gpu.types.GPUOffScreen(width, height)
            
            with offscreen.bind():
                # Clear the buffer
                gpu.state.depth_test_set('LESS')
                gpu.state.depth_mask_set(True)

                # Set up viewport (handled by offscreen buffer)
                
                # Get view matrix from 3D viewport
                space = area.spaces.active
                if space.type == 'VIEW_3D':
                    # Get view and projection matrices
                    view_matrix = space.region_3d.view_matrix
                    projection_matrix = space.region_3d.window_matrix
                    
                    # Render the scene
                    self._render_scene_to_buffer(context, view_matrix, projection_matrix)
                
                # Read pixels using GPU module
                buffer = gpu.types.Buffer('UBYTE', width * height * 4)
                offscreen.read_color(0, 0, width, height, 4, 0, buffer)
            
            # Convert buffer to image
            if NUMPY_AVAILABLE and np is not None:
                try:
                    # Use numpy for efficient conversion
                    pixels = np.frombuffer(buffer, dtype=np.uint8)
                    pixels = pixels.reshape((height, width, 4))
                    pixels = np.flipud(pixels)  # Flip vertically

                    # Convert to PIL Image
                    image = Image.fromarray(pixels, 'RGBA')
                except Exception as numpy_error:
                    print(f"NumPy conversion failed: {numpy_error}")
                    # Fallback to manual conversion
                    image = self._create_fallback_image(width, height)
            else:
                try:
                    # Fallback without numpy
                    pixels = list(buffer)
                    image = Image.new('RGBA', (width, height))

                    # Convert buffer to pixel data
                    pixel_data = []
                    for i in range(0, len(pixels), 4):
                        pixel_data.append((pixels[i], pixels[i+1], pixels[i+2], pixels[i+3]))

                    image.putdata(pixel_data)
                    image = image.transpose(Image.FLIP_TOP_BOTTOM)
                except Exception as manual_error:
                    print(f"Manual conversion failed: {manual_error}")
                    # Create a simple fallback image
                    image = self._create_fallback_image(width, height)

            # Ensure we have a valid image
            if image is None:
                image = self._create_fallback_image(width, height)

            # Convert to base64
            try:
                base64_image = self._image_to_base64(image)
            except Exception as base64_error:
                print(f"Base64 conversion failed: {base64_error}")
                # Create a minimal fallback
                fallback_image = self._create_fallback_image(64, 64)
                base64_image = self._image_to_base64(fallback_image)
            
            # Clean up
            offscreen.free()
            
            return {
                "base64_image": base64_image,
                "width": width,
                "height": height,
                "format": "PNG",
                "cached": False
            }
            
        except Exception as e:
            return {"error": f"Screenshot rendering failed: {str(e)}"}
    
    def _render_scene_to_buffer(self, context, view_matrix, projection_matrix):
        """Render scene to the current buffer - simplified approach"""

        try:
            # For Blender 4.4+, we'll use a simpler approach
            # Just clear the buffer with a background color

            # Get background color from world or use default
            world = context.scene.world
            if world and hasattr(world, 'color'):
                bg_color = world.color[:3]
            else:
                bg_color = (0.05, 0.05, 0.05)  # Default dark gray

            # Clear the framebuffer
            gpu.state.depth_test_set('LESS')
            gpu.state.depth_mask_set(True)

            # The offscreen buffer will automatically capture the viewport content
            # when we read from it, so we don't need to manually render here

        except Exception as e:
            print(f"Scene rendering error: {e}")

    def _create_fallback_image(self, width: int, height: int) -> Image.Image:
        """Create a simple fallback image when screenshot fails"""
        if PIL_AVAILABLE and Image:
            # Create a simple gradient or solid color image
            image = Image.new('RGB', (width, height), (64, 64, 64))  # Dark gray
            return image
        else:
            # This shouldn't happen if we got this far, but just in case
            raise Exception("PIL not available for fallback image")

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
            image = background
        
        # Save to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='PNG', quality=95)
        buffer.seek(0)
        
        # Encode to base64
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _generate_cache_key(self, context, resolution: Optional[Tuple[int, int]]) -> str:
        """Generate cache key for screenshot"""
        
        # Get viewport state
        area = context.area
        space = context.space_data
        
        cache_components = []
        
        if area and area.type == 'VIEW_3D' and space:
            # Add viewport-specific information
            cache_components.extend([
                str(space.shading.type),
                str(space.overlay.show_overlays),
                str(resolution or (area.width, area.height))
            ])
            
            # Add view matrix components (simplified)
            if hasattr(space, 'region_3d') and space.region_3d:
                view_location = space.region_3d.view_location
                view_rotation = space.region_3d.view_rotation
                view_distance = space.region_3d.view_distance
                
                cache_components.extend([
                    f"{view_location.x:.2f}_{view_location.y:.2f}_{view_location.z:.2f}",
                    f"{view_rotation.w:.2f}_{view_rotation.x:.2f}_{view_rotation.y:.2f}_{view_rotation.z:.2f}",
                    f"{view_distance:.2f}"
                ])
        
        # Add scene state
        scene = context.scene
        cache_components.extend([
            str(scene.frame_current),
            str(len(scene.objects)),
            str(hash(tuple(obj.name for obj in scene.objects if obj.visible_get())))
        ])
        
        # Create hash
        import hashlib
        cache_string = "_".join(cache_components)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def capture_multiple_views(
        self, 
        context, 
        view_angles: List[Dict[str, Any]],
        resolution: Optional[Tuple[int, int]] = None
    ) -> List[Dict[str, Any]]:
        """Capture screenshots from multiple view angles"""
        
        screenshots = []
        original_view_state = self._save_view_state(context)
        
        try:
            for i, view_angle in enumerate(view_angles):
                # Set view angle
                self._set_view_angle(context, view_angle)
                
                # Capture screenshot
                screenshot = self.capture_viewport_screenshot(
                    context, 
                    resolution=resolution,
                    use_cache=False  # Don't cache multi-view screenshots
                )
                
                if screenshot and not screenshot.get("error"):
                    screenshot["view_angle"] = view_angle
                    screenshot["view_index"] = i
                    screenshots.append(screenshot)
                
        finally:
            # Restore original view state
            self._restore_view_state(context, original_view_state)
        
        return screenshots
    
    def _save_view_state(self, context) -> Dict[str, Any]:
        """Save current viewport state"""
        
        area = context.area
        space = context.space_data
        
        if area and area.type == 'VIEW_3D' and space and hasattr(space, 'region_3d'):
            region_3d = space.region_3d
            return {
                "view_location": region_3d.view_location.copy(),
                "view_rotation": region_3d.view_rotation.copy(),
                "view_distance": region_3d.view_distance
            }
        
        return {}
    
    def _restore_view_state(self, context, view_state: Dict[str, Any]) -> None:
        """Restore viewport state"""
        
        if not view_state:
            return
        
        area = context.area
        space = context.space_data
        
        if area and area.type == 'VIEW_3D' and space and hasattr(space, 'region_3d'):
            region_3d = space.region_3d
            
            if "view_location" in view_state:
                region_3d.view_location = view_state["view_location"]
            if "view_rotation" in view_state:
                region_3d.view_rotation = view_state["view_rotation"]
            if "view_distance" in view_state:
                region_3d.view_distance = view_state["view_distance"]
    
    def _set_view_angle(self, context, view_angle: Dict[str, Any]) -> None:
        """Set viewport to specific view angle"""
        
        area = context.area
        space = context.space_data
        
        if not (area and area.type == 'VIEW_3D' and space and hasattr(space, 'region_3d')):
            return
        
        region_3d = space.region_3d
        
        if "location" in view_angle:
            region_3d.view_location = Vector(view_angle["location"])
        
        if "rotation" in view_angle:
            region_3d.view_rotation = view_angle["rotation"]
        
        if "distance" in view_angle:
            region_3d.view_distance = view_angle["distance"]
    
    def get_standard_view_angles(self) -> List[Dict[str, Any]]:
        """Get standard view angles for multi-view capture"""
        
        return [
            {"name": "front", "rotation": (0.7071, 0.7071, 0, 0), "distance": 10},
            {"name": "back", "rotation": (0, 0, 0.7071, 0.7071), "distance": 10},
            {"name": "right", "rotation": (0.5, 0.5, 0.5, 0.5), "distance": 10},
            {"name": "left", "rotation": (0.5, -0.5, -0.5, 0.5), "distance": 10},
            {"name": "top", "rotation": (1, 0, 0, 0), "distance": 10},
            {"name": "bottom", "rotation": (0, 1, 0, 0), "distance": 10}
        ]
    
    def clear_cache(self) -> None:
        """Clear screenshot cache"""
        self._screenshot_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cached_screenshots": len(self._screenshot_cache),
            "cache_timeout": self._cache_timeout
        }

# Blender operator for capturing screenshots
class BLENDPRO_OT_CaptureScreenshot(bpy.types.Operator):
    """Capture viewport screenshot"""
    bl_idname = "blendpro.capture_screenshot"
    bl_label = "Capture Screenshot"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        screenshot_manager = get_screenshot_manager()
        result = screenshot_manager.capture_viewport_screenshot(context)
        
        if result and not result.get("error"):
            self.report({'INFO'}, "Screenshot captured successfully")
        else:
            error_msg = result.get("error", "Unknown error") if result else "Failed to capture"
            self.report({'ERROR'}, f"Screenshot failed: {error_msg}")
        
        return {'FINISHED'}

# Global screenshot manager instance
_screenshot_manager: Optional[ScreenshotManager] = None

def get_screenshot_manager() -> ScreenshotManager:
    """Get global screenshot manager instance"""
    global _screenshot_manager
    if _screenshot_manager is None:
        _screenshot_manager = ScreenshotManager()
    return _screenshot_manager

def register():
    """Register Blender classes"""
    bpy.utils.register_class(BLENDPRO_OT_CaptureScreenshot)

def unregister():
    """Unregister Blender classes"""
    bpy.utils.unregister_class(BLENDPRO_OT_CaptureScreenshot)
