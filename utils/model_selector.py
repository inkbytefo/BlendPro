"""
Model Selection Utilities for BlendPro
Provides intelligent model selection based on task requirements and user preferences
"""

from typing import Optional, Dict, Any
from ..config.models import (
    get_default_model_for_task,
    get_model_for_capability,
    get_classification_model,
    get_vision_model,
    get_code_model,
    get_test_model,
    ModelCapability,
    get_model_config
)
from ..config.settings import get_settings


class ModelSelector:
    """Intelligent model selector for different tasks"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def select_for_task(self, task_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Select best model for a specific task type"""
        
        # Check if user has forced a specific model
        if self.settings.use_custom_model and self.settings.custom_model:
            model_config = get_model_config(self.settings.custom_model)
            if model_config:
                # Verify the model can handle the task
                if self._can_handle_task(model_config, task_type):
                    return self.settings.custom_model
        
        # Task-specific selection
        if task_type == "classification":
            return get_classification_model()
        elif task_type == "vision":
            return get_vision_model()
        elif task_type == "code":
            return get_code_model()
        elif task_type == "question":
            return get_default_model_for_task("general")
        elif task_type == "task":
            # For tasks, prefer code-capable models
            return get_model_for_capability(ModelCapability.CODE_GENERATION, prefer_fast=False)
        elif task_type == "test":
            return get_test_model()
        else:
            return get_default_model_for_task("general")
    
    def select_for_capability(self, capability: ModelCapability, prefer_fast: bool = False) -> str:
        """Select model based on required capability"""
        return get_model_for_capability(capability, prefer_fast)
    
    def select_for_context(self, context: Dict[str, Any]) -> str:
        """Select model based on context information"""
        
        # Check if vision is needed
        if self._needs_vision(context):
            return get_vision_model()
        
        # Check if code generation is needed
        if self._needs_code_generation(context):
            return get_code_model()
        
        # Default to general model
        return get_default_model_for_task("general")
    
    def _can_handle_task(self, model_config, task_type: str) -> bool:
        """Check if a model can handle a specific task type"""
        
        if task_type == "vision":
            return model_config.is_vision_capable()
        elif task_type == "code":
            return model_config.is_code_capable()
        elif task_type in ["classification", "question", "task", "general"]:
            return ModelCapability.TEXT_GENERATION in model_config.capabilities
        
        return True  # Most models can handle basic tasks
    
    def _needs_vision(self, context: Dict[str, Any]) -> bool:
        """Determine if vision capability is needed based on context"""
        
        # Check for vision keywords in user input
        user_input = context.get("user_input", "").lower()
        vision_keywords = [
            "see", "look", "view", "image", "picture", "visual", "scene",
            "current", "visible", "analyze", "what", "this", "these"
        ]
        
        return any(keyword in user_input for keyword in vision_keywords)
    
    def _needs_code_generation(self, context: Dict[str, Any]) -> bool:
        """Determine if code generation capability is needed"""
        
        user_input = context.get("user_input", "").lower()
        code_keywords = [
            "create", "generate", "build", "make", "add", "script",
            "python", "code", "function", "class", "method"
        ]
        
        return any(keyword in user_input for keyword in code_keywords)
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        model_config = get_model_config(model_name)
        if not model_config:
            return None
        
        return {
            "name": model_config.name,
            "display_name": model_config.display_name,
            "provider": model_config.provider,
            "capabilities": [cap.value for cap in model_config.capabilities],
            "max_tokens": model_config.max_tokens,
            "context_window": model_config.context_window,
            "cost_per_1k_tokens": model_config.cost_per_1k_tokens,
            "recommended_temperature": model_config.recommended_temperature,
            "supports_streaming": model_config.supports_streaming
        }


# Global model selector instance
_model_selector: Optional[ModelSelector] = None

def get_model_selector() -> ModelSelector:
    """Get global model selector instance"""
    global _model_selector
    if _model_selector is None:
        _model_selector = ModelSelector()
    return _model_selector

def select_model_for_task(task_type: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Convenience function to select model for task"""
    selector = get_model_selector()
    return selector.select_for_task(task_type, context)

def select_model_for_capability(capability: ModelCapability, prefer_fast: bool = False) -> str:
    """Convenience function to select model for capability"""
    selector = get_model_selector()
    return selector.select_for_capability(capability, prefer_fast)
