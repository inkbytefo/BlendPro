"""
Task Classifier for BlendPro: AI Co-Pilot
Classifies user input into tasks, questions, or clarification needs
"""

import json
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

from ..config.prompts import get_system_prompt, PromptType
from ..config.settings import get_settings
from ..utils.api_client import get_api_client, APIRequest

class TaskType(Enum):
    """Types of user tasks"""
    QUESTION = "QUESTION"
    TASK = "TASK"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"

@dataclass
class ClassificationResult:
    """Result of task classification"""
    task_type: TaskType
    confidence: float
    reasoning: str
    keywords_found: List[str]
    missing_info: List[str]
    raw_response: Dict[str, Any]

class TaskClassifier:
    """Classifies user input to determine appropriate response mode"""
    
    def __init__(self):
        self.api_client = get_api_client()
        self.settings = get_settings()
        self._classification_cache: Dict[str, ClassificationResult] = {}
    
    def classify(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """Classify user input into task type"""
        
        # Check cache first
        cache_key = self._generate_cache_key(user_input, context)
        if cache_key in self._classification_cache:
            return self._classification_cache[cache_key]
        
        try:
            # Prepare the classification request
            system_prompt = get_system_prompt(PromptType.TASK_CLASSIFIER)
            
            # Add context information if available
            context_info = ""
            if context:
                context_info = f"\nScene context: {json.dumps(context, indent=2)}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Classify this user input: '{user_input}'{context_info}"}
            ]
            
            # Get classification API config
            api_config = self.settings.get_classification_api_config()

            request = APIRequest(
                messages=messages,
                model=api_config["model"],  # Use configured model for classification
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=300
            )
            
            response = self.api_client.make_request(request)
            
            if response.error:
                # Fallback to simple keyword-based classification
                return self._fallback_classification(user_input)
            
            # Parse the JSON response
            try:
                classification_data = json.loads(response.content)
                
                result = ClassificationResult(
                    task_type=TaskType(classification_data.get("classification", "TASK")),
                    confidence=float(classification_data.get("confidence", 0.5)),
                    reasoning=classification_data.get("reasoning", ""),
                    keywords_found=classification_data.get("keywords_found", []),
                    missing_info=classification_data.get("missing_info", []),
                    raw_response=classification_data
                )
                
                # Cache the result
                self._classification_cache[cache_key] = result
                return result
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error parsing classification response: {e}")
                return self._fallback_classification(user_input)
                
        except Exception as e:
            print(f"Error in task classification: {e}")
            return self._fallback_classification(user_input)
    
    def _fallback_classification(self, user_input: str) -> ClassificationResult:
        """Fallback classification using simple keyword matching"""
        user_input_lower = user_input.lower()
        
        # Question keywords
        question_keywords = [
            "what", "how", "why", "which", "where", "when", "who",
            "explain", "tell me", "show me", "describe", "list",
            "is", "are", "can", "could", "would", "should", "do"
        ]
        
        # Task keywords
        task_keywords = [
            "create", "make", "add", "delete", "remove", "move", "scale",
            "rotate", "generate", "build", "place", "set", "change",
            "modify", "update", "apply", "render", "export", "import"
        ]
        
        # Clarification keywords (vague references)
        clarification_keywords = [
            "this", "that", "it", "them", "these", "those",
            "bigger", "smaller", "better", "different"
        ]
        
        # Count keyword matches
        question_score = sum(1 for keyword in question_keywords if keyword in user_input_lower)
        task_score = sum(1 for keyword in task_keywords if keyword in user_input_lower)
        clarification_score = sum(1 for keyword in clarification_keywords if keyword in user_input_lower)
        
        # Determine classification
        if clarification_score > 0 and (question_score + task_score) == 0:
            task_type = TaskType.CLARIFICATION_NEEDED
            confidence = 0.7
            reasoning = "Contains vague references that need clarification"
            missing_info = ["Specific object or parameter references"]
        elif question_score > task_score:
            task_type = TaskType.QUESTION
            confidence = 0.8 if question_score > 1 else 0.6
            reasoning = "Contains question keywords"
        else:
            task_type = TaskType.TASK
            confidence = 0.8 if task_score > 0 else 0.5
            reasoning = "Contains task keywords or appears to be a command"
        
        return ClassificationResult(
            task_type=task_type,
            confidence=confidence,
            reasoning=reasoning,
            keywords_found=[],
            missing_info=missing_info if task_type == TaskType.CLARIFICATION_NEEDED else [],
            raw_response={}
        )
    
    def _generate_cache_key(self, user_input: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for classification"""
        import hashlib
        
        cache_data = {
            "input": user_input,
            "context": context or {}
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def is_question(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Quick check if input is a question"""
        result = self.classify(user_input, context)
        return result.task_type == TaskType.QUESTION
    
    def is_task(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Quick check if input is a task"""
        result = self.classify(user_input, context)
        return result.task_type == TaskType.TASK
    
    def needs_clarification(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Quick check if input needs clarification"""
        result = self.classify(user_input, context)
        return result.task_type == TaskType.CLARIFICATION_NEEDED
    
    def clear_cache(self) -> None:
        """Clear the classification cache"""
        self._classification_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "cached_classifications": len(self._classification_cache)
        }

# Global task classifier instance
_task_classifier: Optional[TaskClassifier] = None

def get_task_classifier() -> TaskClassifier:
    """Get global task classifier instance"""
    global _task_classifier
    if _task_classifier is None:
        _task_classifier = TaskClassifier()
    return _task_classifier
