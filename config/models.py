"""
AI Model Configuration for BlendPro
Defines available models and their capabilities
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ModelCapability(Enum):
    """Model capabilities enumeration"""
    TEXT_GENERATION = "text_generation"
    VISION = "vision"
    CODE_GENERATION = "code_generation"
    FUNCTION_CALLING = "function_calling"
    LONG_CONTEXT = "long_context"

@dataclass
class ModelConfig:
    """Configuration for an AI model"""
    name: str
    display_name: str
    provider: str
    capabilities: List[ModelCapability]
    max_tokens: int
    context_window: int
    cost_per_1k_tokens: float
    recommended_temperature: float = 0.7
    supports_streaming: bool = True
    
    def has_capability(self, capability: ModelCapability) -> bool:
        """Check if model has specific capability"""
        return capability in self.capabilities
    
    def is_vision_capable(self) -> bool:
        """Check if model supports vision"""
        return self.has_capability(ModelCapability.VISION)
    
    def is_code_capable(self) -> bool:
        """Check if model is good for code generation"""
        return self.has_capability(ModelCapability.CODE_GENERATION)

# Predefined model configurations
AVAILABLE_MODELS: Dict[str, ModelConfig] = {
    # OpenAI Models
    "gpt-4": ModelConfig(
        name="gpt-4",
        display_name="GPT-4",
        provider="openai",
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.FUNCTION_CALLING
        ],
        max_tokens=4096,
        context_window=8192,
        cost_per_1k_tokens=0.03,
        recommended_temperature=0.7
    ),
    
    "gpt-4-turbo": ModelConfig(
        name="gpt-4-turbo",
        display_name="GPT-4 Turbo",
        provider="openai",
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.LONG_CONTEXT
        ],
        max_tokens=4096,
        context_window=128000,
        cost_per_1k_tokens=0.01,
        recommended_temperature=0.7
    ),
    
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        display_name="GPT-4o",
        provider="openai",
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.VISION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.LONG_CONTEXT
        ],
        max_tokens=4096,
        context_window=128000,
        cost_per_1k_tokens=0.005,
        recommended_temperature=0.7
    ),
    
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        display_name="GPT-4o Mini",
        provider="openai",
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.VISION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.FUNCTION_CALLING
        ],
        max_tokens=16384,
        context_window=128000,
        cost_per_1k_tokens=0.00015,
        recommended_temperature=0.7
    ),
    
    "gpt-4-vision-preview": ModelConfig(
        name="gpt-4-vision-preview",
        display_name="GPT-4 Vision Preview",
        provider="openai",
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.VISION,
            ModelCapability.CODE_GENERATION
        ],
        max_tokens=4096,
        context_window=128000,
        cost_per_1k_tokens=0.01,
        recommended_temperature=0.7
    ),
    
    # Claude Models
    "claude-3-5-sonnet-20241022": ModelConfig(
        name="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        provider="anthropic",
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.VISION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.LONG_CONTEXT
        ],
        max_tokens=8192,
        context_window=200000,
        cost_per_1k_tokens=0.003,
        recommended_temperature=0.7
    ),
    
    "claude-3-opus-20240229": ModelConfig(
        name="claude-3-opus-20240229",
        display_name="Claude 3 Opus",
        provider="anthropic",
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.VISION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.LONG_CONTEXT
        ],
        max_tokens=4096,
        context_window=200000,
        cost_per_1k_tokens=0.015,
        recommended_temperature=0.7
    )
}

def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get configuration for a specific model"""
    return AVAILABLE_MODELS.get(model_name)

def get_models_by_capability(capability: ModelCapability) -> List[ModelConfig]:
    """Get all models that have a specific capability"""
    return [
        config for config in AVAILABLE_MODELS.values()
        if config.has_capability(capability)
    ]

def get_vision_models() -> List[ModelConfig]:
    """Get all models that support vision"""
    return get_models_by_capability(ModelCapability.VISION)

def get_code_models() -> List[ModelConfig]:
    """Get all models that are good for code generation"""
    return get_models_by_capability(ModelCapability.CODE_GENERATION)

def get_model_choices() -> List[tuple]:
    """Get model choices for Blender enum property"""
    return [
        (name, config.display_name, f"Use {config.display_name}")
        for name, config in AVAILABLE_MODELS.items()
    ]

def get_vision_model_choices() -> List[tuple]:
    """Get vision model choices for Blender enum property"""
    return [
        (name, config.display_name, f"Use {config.display_name} for vision")
        for name, config in AVAILABLE_MODELS.items()
        if config.is_vision_capable()
    ]

def get_default_model_for_task(task_type: str = "general") -> str:
    """Get default model based on task type and user preferences"""
    from .settings import get_settings

    settings = get_settings()

    # If user has custom model enabled, use it
    if settings.use_custom_model and settings.custom_model:
        return settings.custom_model

    # Task-specific model selection using settings
    default_models = getattr(settings, 'default_models', {
        "general": "gpt-4o-mini",
        "classification": "gpt-4o-mini",
        "planning": "gpt-4",
        "code_generation": "gpt-4",
        "vision": "gpt-4o-mini"
    })

    if task_type == "classification":
        return default_models.get("classification", "gpt-4o-mini")
    elif task_type == "vision":
        # Use custom vision model if configured
        if settings.use_custom_vision_model and settings.custom_vision_model:
            return settings.custom_vision_model
        return default_models.get("vision", "gpt-4o-mini")
    elif task_type == "code":
        return default_models.get("code_generation", "gpt-4")
    elif task_type == "planning":
        return default_models.get("planning", "gpt-4")
    elif task_type == "general":
        return default_models.get("general", "gpt-4o-mini")
    else:
        # Fallback to general model
        return default_models.get("general", "gpt-4o-mini")

def get_model_for_capability(capability: ModelCapability, prefer_fast: bool = False) -> str:
    """Get best model for specific capability"""
    from .settings import get_settings

    settings = get_settings()

    # If user has custom model and it supports the capability, use it
    if settings.use_custom_model and settings.custom_model:
        model_config = get_model_config(settings.custom_model)
        if model_config and model_config.has_capability(capability):
            return settings.custom_model

    # Get models with the capability
    capable_models = get_models_by_capability(capability)

    if not capable_models:
        # Fallback to default
        return get_default_model_for_task("general")

    if prefer_fast:
        # Sort by cost (lower cost = faster/cheaper model)
        capable_models.sort(key=lambda m: m.cost_per_1k_tokens)
    else:
        # Sort by capability and context window (better models first)
        capable_models.sort(key=lambda m: (len(m.capabilities), m.context_window), reverse=True)

    return capable_models[0].name

def get_classification_model() -> str:
    """Get model optimized for task classification"""
    return get_default_model_for_task("classification")

def get_vision_model() -> str:
    """Get model optimized for vision tasks"""
    return get_default_model_for_task("vision")

def get_code_model() -> str:
    """Get model optimized for code generation"""
    return get_default_model_for_task("code")

def get_test_model(use_vision: bool = False) -> str:
    """Get model for testing connections"""
    if use_vision:
        return get_vision_model()
    else:
        return get_default_model_for_task("general")
