"""
Conversation Memory for BlendPro: AI Co-Pilot
Manages conversation context and entity tracking
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import deque
import re

@dataclass
class Entity:
    """Represents an entity (object, material, etc.) in conversation"""
    name: str
    entity_type: str  # 'object', 'material', 'light', etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    last_mentioned: float = field(default_factory=time.time)
    mention_count: int = 0
    aliases: List[str] = field(default_factory=list)

@dataclass
class ConversationTurn:
    """Represents a single turn in conversation"""
    timestamp: float
    user_input: str
    assistant_response: str
    entities_mentioned: List[str] = field(default_factory=list)
    context_used: Dict[str, Any] = field(default_factory=dict)
    turn_type: str = "normal"  # 'normal', 'clarification', 'plan_approval'

class ConversationMemory:
    """Manages conversation context and entity tracking"""
    
    def __init__(self, max_turns: int = 50):
        self.max_turns = max_turns
        self.conversation_history: deque = deque(maxlen=max_turns)
        self.entities: Dict[str, Entity] = {}
        self.current_focus: Optional[str] = None  # Currently focused entity
        self.session_start = time.time()
    
    def add_turn(
        self, 
        user_input: str, 
        assistant_response: str,
        turn_type: str = "normal",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a conversation turn to memory"""
        
        # Extract entities from user input
        mentioned_entities = self._extract_entities(user_input, context or {})
        
        # Create conversation turn
        turn = ConversationTurn(
            timestamp=time.time(),
            user_input=user_input,
            assistant_response=assistant_response,
            entities_mentioned=mentioned_entities,
            context_used=context or {},
            turn_type=turn_type
        )
        
        # Add to history
        self.conversation_history.append(turn)
        
        # Update entity mentions
        for entity_name in mentioned_entities:
            if entity_name in self.entities:
                self.entities[entity_name].last_mentioned = turn.timestamp
                self.entities[entity_name].mention_count += 1
    
    def _extract_entities(self, text: str, context: Dict[str, Any]) -> List[str]:
        """Extract entity names from text using context"""
        mentioned_entities = []
        text_lower = text.lower()
        
        # Get entities from scene context
        scene_objects = context.get("objects", [])
        materials = context.get("materials", [])
        lights = context.get("lights", [])
        
        # Check for object names
        for obj in scene_objects:
            obj_name = obj.get("name", "")
            if obj_name and obj_name.lower() in text_lower:
                mentioned_entities.append(obj_name)
                self._update_entity(obj_name, "object", obj)
        
        # Check for material names
        for mat in materials:
            mat_name = mat.get("name", "")
            if mat_name and mat_name.lower() in text_lower:
                mentioned_entities.append(mat_name)
                self._update_entity(mat_name, "material", mat)
        
        # Check for light names
        for light in lights:
            light_name = light.get("name", "")
            if light_name and light_name.lower() in text_lower:
                mentioned_entities.append(light_name)
                self._update_entity(light_name, "light", light)
        
        return mentioned_entities
    
    def _update_entity(self, name: str, entity_type: str, properties: Dict[str, Any]) -> None:
        """Update or create entity in memory"""
        if name in self.entities:
            # Update existing entity
            self.entities[name].properties.update(properties)
            self.entities[name].last_mentioned = time.time()
        else:
            # Create new entity
            self.entities[name] = Entity(
                name=name,
                entity_type=entity_type,
                properties=properties,
                last_mentioned=time.time(),
                mention_count=1
            )
    
    def resolve_pronouns(self, text: str, context: Dict[str, Any]) -> str:
        """Resolve pronouns and vague references in text"""
        
        # Common pronouns and their patterns
        pronoun_patterns = {
            r'\bit\b': self._resolve_it,
            r'\bthis\b': self._resolve_this,
            r'\bthat\b': self._resolve_that,
            r'\bthey\b': self._resolve_they,
            r'\bthem\b': self._resolve_them,
            r'\bthese\b': self._resolve_these,
            r'\bthose\b': self._resolve_those
        }
        
        resolved_text = text
        
        for pattern, resolver in pronoun_patterns.items():
            matches = re.finditer(pattern, resolved_text, re.IGNORECASE)
            for match in reversed(list(matches)):  # Process from end to start
                replacement = resolver(context)
                if replacement:
                    start, end = match.span()
                    resolved_text = resolved_text[:start] + replacement + resolved_text[end:]
        
        return resolved_text
    
    def _resolve_it(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'it' pronoun"""
        # Look for the most recently mentioned singular object
        recent_entities = self._get_recent_entities(entity_type="object", limit=1)
        if recent_entities:
            return recent_entities[0].name
        
        # Fallback to currently selected object
        selected_objects = self._get_selected_objects(context)
        if len(selected_objects) == 1:
            return selected_objects[0]
        
        return None
    
    def _resolve_this(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'this' reference"""
        # Similar to 'it' but with preference for current focus
        if self.current_focus and self.current_focus in self.entities:
            return self.current_focus
        
        return self._resolve_it(context)
    
    def _resolve_that(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'that' reference"""
        # Look for previously mentioned objects (not the most recent)
        recent_entities = self._get_recent_entities(entity_type="object", limit=3)
        if len(recent_entities) >= 2:
            return recent_entities[1].name  # Second most recent
        
        return self._resolve_it(context)
    
    def _resolve_they(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'they' pronoun"""
        # Look for multiple recently mentioned objects
        recent_entities = self._get_recent_entities(entity_type="object", limit=5)
        if len(recent_entities) >= 2:
            names = [entity.name for entity in recent_entities[:3]]
            return ", ".join(names)
        
        # Fallback to selected objects
        selected_objects = self._get_selected_objects(context)
        if len(selected_objects) > 1:
            return ", ".join(selected_objects)
        
        return None
    
    def _resolve_them(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'them' pronoun"""
        return self._resolve_they(context)
    
    def _resolve_these(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'these' reference"""
        # Similar to 'they' but with preference for current selection
        selected_objects = self._get_selected_objects(context)
        if len(selected_objects) > 1:
            return ", ".join(selected_objects)
        
        return self._resolve_they(context)
    
    def _resolve_those(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'those' reference"""
        # Look for previously mentioned groups
        return self._resolve_these(context)
    
    def _get_recent_entities(self, entity_type: Optional[str] = None, limit: int = 5) -> List[Entity]:
        """Get recently mentioned entities"""
        entities = list(self.entities.values())
        
        # Filter by type if specified
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        
        # Sort by last mentioned time
        entities.sort(key=lambda e: e.last_mentioned, reverse=True)
        
        return entities[:limit]
    
    def _get_selected_objects(self, context: Dict[str, Any]) -> List[str]:
        """Get currently selected objects from context"""
        objects = context.get("objects", [])
        return [obj.get("name", "") for obj in objects if obj.get("selected", False)]
    
    def get_conversation_context(self, turns_back: int = 5) -> List[ConversationTurn]:
        """Get recent conversation context"""
        return list(self.conversation_history)[-turns_back:]
    
    def get_entity_context(self, entity_name: str) -> Optional[Entity]:
        """Get context for a specific entity"""
        return self.entities.get(entity_name)
    
    def set_current_focus(self, entity_name: str) -> None:
        """Set the current focus entity"""
        if entity_name in self.entities:
            self.current_focus = entity_name
    
    def get_current_focus(self) -> Optional[Entity]:
        """Get the currently focused entity"""
        if self.current_focus and self.current_focus in self.entities:
            return self.entities[self.current_focus]
        return None
    
    def build_context_summary(self) -> str:
        """Build a summary of current conversation context"""
        summary_parts = []
        
        # Recent conversation
        recent_turns = self.get_conversation_context(3)
        if recent_turns:
            summary_parts.append("Recent conversation:")
            for turn in recent_turns[-2:]:  # Last 2 turns
                summary_parts.append(f"User: {turn.user_input[:100]}...")
                summary_parts.append(f"Assistant: {turn.assistant_response[:100]}...")
        
        # Current focus
        focus = self.get_current_focus()
        if focus:
            summary_parts.append(f"Current focus: {focus.name} ({focus.entity_type})")
        
        # Recently mentioned entities
        recent_entities = self._get_recent_entities(limit=3)
        if recent_entities:
            entity_names = [e.name for e in recent_entities]
            summary_parts.append(f"Recently mentioned: {', '.join(entity_names)}")
        
        return "\n".join(summary_parts)
    
    def clear_memory(self) -> None:
        """Clear conversation memory"""
        self.conversation_history.clear()
        self.entities.clear()
        self.current_focus = None
        self.session_start = time.time()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "conversation_turns": len(self.conversation_history),
            "tracked_entities": len(self.entities),
            "current_focus": self.current_focus,
            "session_duration": time.time() - self.session_start,
            "most_mentioned_entities": [
                (name, entity.mention_count) 
                for name, entity in sorted(
                    self.entities.items(), 
                    key=lambda x: x[1].mention_count, 
                    reverse=True
                )[:5]
            ]
        }

# Global conversation memory instance
_conversation_memory: Optional[ConversationMemory] = None

def get_conversation_memory() -> ConversationMemory:
    """Get global conversation memory instance"""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory
