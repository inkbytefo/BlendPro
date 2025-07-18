"""
BlendPro Settings Management
Centralized configuration for all BlendPro components
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class BlendProSettings:
    """Central configuration class for BlendPro"""
    
    # API Configuration
    api_key: str = ""
    base_url: str = ""
    use_custom_model: bool = False
    custom_model: str = ""
    
    # AI Parameters
    temperature: float = 0.7
    max_tokens: int = 1500
    top_p: float = 1.0
    
    # Vision System
    vision_api_key: str = ""
    vision_base_url: str = ""
    use_custom_vision_model: bool = False
    custom_vision_model: str = ""
    enable_vision_context: bool = True
    auto_vision_keywords: str = "scene,current,visible,see,look,analyze,what,this,these,objects"
    
    # Scene Monitoring
    enable_scene_monitoring: bool = True
    monitoring_interval: float = 2.0
    analysis_cooldown: float = 10.0
    max_suggestions: int = 10
    
    # Interaction Engine
    enable_task_classification: bool = True
    enable_clarification_system: bool = True
    enable_multi_step_planning: bool = True
    conversation_memory_size: int = 50
    
    # Workflow
    enable_proactive_suggestions: bool = True
    enable_auto_fix: bool = True
    max_action_library_size: int = 100
    
    # UI Configuration
    chat_history_size: int = 100
    enable_interactive_messages: bool = True
    show_code_preview: bool = True
    
    # Performance
    enable_caching: bool = True
    cache_timeout: int = 300  # 5 minutes
    max_concurrent_requests: int = 3
    
    # Backup System
    enable_auto_backup: bool = True
    max_backups: int = 10
    backup_interval: int = 60  # seconds

    # Model Configuration
    default_models: Dict[str, str] = field(default_factory=lambda: {
        "general": "gpt-4o-mini",
        "classification": "gpt-4o-mini",
        "planning": "gpt-4",
        "code_generation": "gpt-4",
        "vision": "gpt-4o-mini"
    })

    # Timeout Settings
    api_timeout: float = 30.0
    code_execution_timeout: float = 60.0
    planning_timeout: float = 45.0

    # Validation Settings
    max_input_length: int = 5000
    max_code_length: int = 10000
    enable_code_validation: bool = True
    enable_input_sanitization: bool = True
    
    def __post_init__(self):
        """Initialize settings from environment variables if not set"""
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.base_url:
            self.base_url = os.getenv("OPENAI_BASE_URL", "")
        if not self.vision_api_key:
            self.vision_api_key = self.api_key  # Use main API key as fallback
        if not self.vision_base_url:
            self.vision_base_url = self.base_url  # Use main base URL as fallback
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlendProSettings':
        """Create settings from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def update(self, **kwargs) -> None:
        """Update settings with new values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_api_config(self, task_type: str = "general") -> Dict[str, str]:
        """Get API configuration for AI model based on task type"""
        from .models import get_default_model_for_task

        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": get_default_model_for_task(task_type)
        }

    def get_vision_api_config(self) -> Dict[str, str]:
        """Get API configuration for vision model"""
        from .models import get_vision_model

        return {
            "api_key": self.vision_api_key or self.api_key,
            "base_url": self.vision_base_url or self.base_url,
            "model": get_vision_model()
        }

    def get_classification_api_config(self) -> Dict[str, str]:
        """Get API configuration for task classification"""
        from .models import get_classification_model

        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": get_classification_model()
        }

    def get_test_api_config(self, use_vision: bool = False) -> Dict[str, str]:
        """Get API configuration for testing"""
        from .models import get_test_model

        return {
            "api_key": self.vision_api_key if use_vision else self.api_key,
            "base_url": self.vision_base_url if use_vision else self.base_url,
            "model": get_test_model(use_vision)
        }

# Global settings instance
_settings: Optional[BlendProSettings] = None

def get_settings() -> BlendProSettings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = BlendProSettings()
    return _settings

def update_settings(**kwargs) -> None:
    """Update global settings"""
    settings = get_settings()
    settings.update(**kwargs)

def reset_settings() -> None:
    """Reset settings to defaults"""
    global _settings
    _settings = BlendProSettings()

def sync_from_preferences(preferences) -> None:
    """Sync settings from Blender addon preferences"""
    settings = get_settings()

    # Update settings with preference values
    settings.update(
        api_key=getattr(preferences, 'api_key', ''),
        base_url=getattr(preferences, 'custom_api_url', ''),
        use_custom_model=getattr(preferences, 'use_custom_model', False),
        custom_model=getattr(preferences, 'custom_model', 'gpt-4o-mini'),
        vision_api_key=getattr(preferences, 'vision_api_key', '') or getattr(preferences, 'api_key', ''),
        vision_base_url=getattr(preferences, 'vision_api_url', '') or getattr(preferences, 'custom_api_url', ''),
        temperature=getattr(preferences, 'temperature', 0.7),
        max_tokens=getattr(preferences, 'max_tokens', 1500),
        enable_vision_context=getattr(preferences, 'enable_vision_context', True),
        enable_multi_step_planning=getattr(preferences, 'enable_multi_step_planning', True),
        enable_proactive_suggestions=getattr(preferences, 'enable_proactive_suggestions', True),
        enable_scene_monitoring=getattr(preferences, 'enable_scene_monitoring', True),
        enable_auto_backup=getattr(preferences, 'enable_auto_backup', True),
        enable_caching=getattr(preferences, 'enable_caching', True),
        monitoring_interval=getattr(preferences, 'monitoring_interval', 2.0),
        max_concurrent_requests=getattr(preferences, 'max_concurrent_requests', 3),
        max_suggestions=getattr(preferences, 'max_suggestions', 5),
        backup_interval=getattr(preferences, 'backup_interval', 300),
        max_backups=getattr(preferences, 'max_backups', 10),
        analysis_cooldown=getattr(preferences, 'analysis_cooldown', 1.0)
    )
