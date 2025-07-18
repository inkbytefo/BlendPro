"""
Clarification System for BlendPro: AI Co-Pilot
Handles ambiguous user requests by asking clarifying questions
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..config.prompts import get_system_prompt, PromptType
from ..utils.api_client import get_api_client, APIRequest

@dataclass
class ClarificationRequest:
    """Represents a request for clarification"""
    original_input: str
    ambiguity_reason: str
    scene_context: Dict[str, Any]
    suggested_questions: List[str]
    default_assumptions: Dict[str, Any]

@dataclass
class ClarificationResponse:
    """Response from clarification system"""
    question: str
    context_provided: str
    suggested_defaults: Dict[str, Any]
    confidence: float

class ClarificationSystem:
    """Generates clarifying questions for ambiguous user requests"""
    
    def __init__(self):
        self.api_client = get_api_client()
        self._active_clarifications: Dict[str, ClarificationRequest] = {}
    
    def generate_clarification(
        self, 
        user_input: str, 
        ambiguity_reason: str,
        scene_context: Optional[Dict[str, Any]] = None
    ) -> ClarificationResponse:
        """Generate a clarifying question for ambiguous input"""
        
        try:
            # Prepare scene context
            context = scene_context or {}
            
            # Get clarification prompt
            system_prompt = get_system_prompt(
                PromptType.CLARIFICATION,
                scene_context=json.dumps(context, indent=2),
                user_request=user_input,
                ambiguity_reason=ambiguity_reason
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate a clarifying question for: '{user_input}'"}
            ]
            
            request = APIRequest(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=200
            )
            
            response = self.api_client.make_request(request)
            
            if response.error:
                return self._generate_fallback_clarification(user_input, ambiguity_reason, context)
            
            # Store the clarification request
            clarification_id = self._generate_clarification_id(user_input)
            self._active_clarifications[clarification_id] = ClarificationRequest(
                original_input=user_input,
                ambiguity_reason=ambiguity_reason,
                scene_context=context,
                suggested_questions=[response.content],
                default_assumptions={}
            )
            
            return ClarificationResponse(
                question=response.content,
                context_provided=json.dumps(context, indent=2),
                suggested_defaults={},
                confidence=0.8
            )
            
        except Exception as e:
            print(f"Error generating clarification: {e}")
            return self._generate_fallback_clarification(user_input, ambiguity_reason, scene_context or {})
    
    def _generate_fallback_clarification(
        self, 
        user_input: str, 
        ambiguity_reason: str, 
        context: Dict[str, Any]
    ) -> ClarificationResponse:
        """Generate fallback clarification using templates"""
        
        user_input_lower = user_input.lower()
        
        # Common clarification patterns
        if "this" in user_input_lower or "that" in user_input_lower or "it" in user_input_lower:
            # Object reference ambiguity
            objects_in_scene = context.get("objects", [])
            selected_objects = [obj for obj in objects_in_scene if obj.get("selected", False)]
            
            if selected_objects:
                question = f"I see you have {len(selected_objects)} object(s) selected. Are you referring to the selected object(s), or would you like me to list all objects in the scene so you can specify which one?"
            else:
                question = "I need to know which object you're referring to. Would you like me to list the objects in your scene so you can specify which one?"
        
        elif "bigger" in user_input_lower or "smaller" in user_input_lower:
            # Size ambiguity
            question = "I'd be happy to help with resizing! Could you please specify:\n1. Which object should be resized?\n2. How much bigger/smaller? (e.g., '2x larger', 'scale by 0.5', 'make it 3 units wide')"
        
        elif "color" in user_input_lower or "red" in user_input_lower or "blue" in user_input_lower:
            # Color/material ambiguity
            question = "I can help with coloring! Please clarify:\n1. Which object should be colored?\n2. Should I create a new material or modify an existing one?"
        
        elif "move" in user_input_lower:
            # Movement ambiguity
            question = "I can help with moving objects! Please specify:\n1. Which object should be moved?\n2. Where should it be moved to? (e.g., 'to position (1,2,3)', 'up by 2 units', 'next to the cube')"
        
        else:
            # Generic ambiguity
            question = f"I need more information to help you with '{user_input}'. Could you please provide more specific details about what you'd like me to do?"
        
        return ClarificationResponse(
            question=question,
            context_provided=json.dumps(context, indent=2),
            suggested_defaults={},
            confidence=0.6
        )
    
    def resolve_clarification(
        self, 
        clarification_id: str, 
        user_response: str
    ) -> Optional[str]:
        """Resolve a clarification with user's response"""
        
        if clarification_id not in self._active_clarifications:
            return None
        
        clarification = self._active_clarifications[clarification_id]
        
        # Combine original input with clarification response
        resolved_input = f"{clarification.original_input}\n\nClarification: {user_response}"
        
        # Remove from active clarifications
        del self._active_clarifications[clarification_id]
        
        return resolved_input
    
    def _generate_clarification_id(self, user_input: str) -> str:
        """Generate unique ID for clarification"""
        import hashlib
        import time
        
        id_string = f"{user_input}_{time.time()}"
        return hashlib.md5(id_string.encode()).hexdigest()[:8]
    
    def get_common_ambiguities(self, user_input: str, context: Dict[str, Any]) -> List[str]:
        """Identify common ambiguities in user input"""
        ambiguities = []
        user_input_lower = user_input.lower()
        
        # Vague object references
        vague_refs = ["this", "that", "it", "them", "these", "those"]
        if any(ref in user_input_lower for ref in vague_refs):
            ambiguities.append("Vague object reference")
        
        # Missing parameters
        if any(word in user_input_lower for word in ["bigger", "smaller", "more", "less"]) and not any(num in user_input for num in "0123456789"):
            ambiguities.append("Missing size specification")
        
        # Color without object
        color_words = ["red", "blue", "green", "yellow", "color", "material"]
        if any(color in user_input_lower for color in color_words) and not any(ref in user_input_lower for ref in vague_refs):
            objects_mentioned = self._extract_object_names(user_input, context)
            if not objects_mentioned:
                ambiguities.append("Color specified without target object")
        
        # Movement without destination
        if "move" in user_input_lower and not any(prep in user_input_lower for prep in ["to", "by", "up", "down", "left", "right"]):
            ambiguities.append("Movement without destination")
        
        return ambiguities
    
    def _extract_object_names(self, user_input: str, context: Dict[str, Any]) -> List[str]:
        """Extract potential object names from user input"""
        objects_in_scene = [obj.get("name", "") for obj in context.get("objects", [])]
        mentioned_objects = []
        
        user_input_lower = user_input.lower()
        for obj_name in objects_in_scene:
            if obj_name.lower() in user_input_lower:
                mentioned_objects.append(obj_name)
        
        return mentioned_objects
    
    def clear_active_clarifications(self) -> None:
        """Clear all active clarifications"""
        self._active_clarifications.clear()
    
    def get_active_clarifications(self) -> Dict[str, ClarificationRequest]:
        """Get all active clarifications"""
        return self._active_clarifications.copy()

# Global clarification system instance
_clarification_system: Optional[ClarificationSystem] = None

def get_clarification_system() -> ClarificationSystem:
    """Get global clarification system instance"""
    global _clarification_system
    if _clarification_system is None:
        _clarification_system = ClarificationSystem()
    return _clarification_system
