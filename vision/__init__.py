"""
Vision module for BlendPro: AI Co-Pilot
Advanced scene analysis and visual understanding capabilities
"""

# Import with error handling to prevent circular imports
try:
    from .scene_analyzer import SceneAnalyzer, get_scene_analyzer
except ImportError as e:
    print(f"BlendPro Vision: Failed to import scene_analyzer: {e}")
    SceneAnalyzer = None
    get_scene_analyzer = None

try:
    from .context_extractor import ContextExtractor, get_context_extractor
except ImportError as e:
    print(f"BlendPro Vision: Failed to import context_extractor: {e}")
    ContextExtractor = None
    get_context_extractor = None

try:
    from .screenshot_manager import ScreenshotManager, get_screenshot_manager
except ImportError as e:
    print(f"BlendPro Vision: Failed to import screenshot_manager: {e}")
    ScreenshotManager = None
    get_screenshot_manager = None

try:
    from .multi_modal_vision import MultiModalVision, get_multi_modal_vision
except ImportError as e:
    print(f"BlendPro Vision: Failed to import multi_modal_vision: {e}")
    MultiModalVision = None
    get_multi_modal_vision = None

__all__ = [
    'SceneAnalyzer',
    'get_scene_analyzer',
    'ContextExtractor',
    'get_context_extractor',
    'ScreenshotManager',
    'get_screenshot_manager',
    'MultiModalVision',
    'get_multi_modal_vision'
]
