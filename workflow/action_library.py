"""
Action Library for BlendPro: AI Co-Pilot
Parametric code snippets and user-defined actions
"""

import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..config.settings import get_settings
from ..utils.file_manager import get_file_manager
from ..utils.code_executor import get_code_executor

class ParameterType(Enum):
    """Types of parameters in actions"""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    OBJECT_NAME = "object_name"
    MATERIAL_NAME = "material_name"
    COLLECTION_NAME = "collection_name"
    VECTOR3 = "vector3"
    COLOR = "color"

@dataclass
class ActionParameter:
    """Represents a parameter in an action"""
    name: str
    param_type: ParameterType
    description: str
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[str]] = None  # For enum-like parameters

@dataclass
class UserAction:
    """Represents a user-defined action"""
    id: str
    name: str
    description: str
    code_template: str
    parameters: List[ActionParameter] = field(default_factory=list)
    category: str = "General"
    tags: List[str] = field(default_factory=list)
    created_time: float = field(default_factory=time.time)
    usage_count: int = 0
    last_used: float = 0.0
    author: str = "User"

class ActionLibrary:
    """Manages user-defined parametric actions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.file_manager = get_file_manager()
        self.code_executor = get_code_executor()
        
        self._actions: Dict[str, UserAction] = {}
        self._load_actions()
    
    def create_action_from_code(
        self, 
        name: str, 
        code: str, 
        description: str = "",
        category: str = "General"
    ) -> Optional[UserAction]:
        """Create a new action from code by extracting parameters"""
        
        try:
            # Generate unique ID
            action_id = self._generate_action_id(name)
            
            # Extract parameters from code
            parameters = self._extract_parameters_from_code(code)
            
            # Create parameter template
            code_template = self._create_code_template(code, parameters)
            
            # Create action
            action = UserAction(
                id=action_id,
                name=name,
                description=description or f"Custom action: {name}",
                code_template=code_template,
                parameters=parameters,
                category=category
            )
            
            # Store action
            self._actions[action_id] = action
            self._save_actions()
            
            return action
            
        except Exception as e:
            print(f"Error creating action: {e}")
            return None
    
    def _extract_parameters_from_code(self, code: str) -> List[ActionParameter]:
        """Extract parameters from code using pattern matching"""
        
        parameters = []
        
        # Common parameter patterns
        patterns = [
            # Numbers (integers and floats)
            (r'\b(\w+)\s*=\s*(\d+\.?\d*)\b', self._infer_number_type),
            # Strings
            (r'\b(\w+)\s*=\s*["\']([^"\']*)["\']', lambda x: ParameterType.STRING),
            # Booleans
            (r'\b(\w+)\s*=\s*(True|False)\b', lambda x: ParameterType.BOOLEAN),
            # Object references
            (r'bpy\.data\.objects\[["\']([^"\']*)["\']', lambda x: ParameterType.OBJECT_NAME),
            # Material references
            (r'bpy\.data\.materials\[["\']([^"\']*)["\']', lambda x: ParameterType.MATERIAL_NAME),
            # Location/rotation vectors
            (r'location\s*=\s*\(([^)]+)\)', lambda x: ParameterType.VECTOR3),
            (r'rotation_euler\s*=\s*\(([^)]+)\)', lambda x: ParameterType.VECTOR3),
            # Colors
            (r'color\s*=\s*\(([^)]+)\)', lambda x: ParameterType.COLOR),
        ]
        
        found_params = set()
        
        for pattern, type_inferrer in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            
            for match in matches:
                if len(match.groups()) >= 2:
                    param_name = match.group(1)
                    param_value = match.group(2)
                    
                    # Avoid duplicates
                    if param_name in found_params:
                        continue
                    
                    found_params.add(param_name)
                    
                    # Infer parameter type
                    param_type = type_inferrer(param_value)
                    
                    # Create parameter
                    parameter = ActionParameter(
                        name=param_name,
                        param_type=param_type,
                        description=f"Parameter: {param_name}",
                        default_value=self._parse_default_value(param_value, param_type)
                    )
                    
                    parameters.append(parameter)
        
        return parameters
    
    def _infer_number_type(self, value_str: str) -> ParameterType:
        """Infer if a number is integer or float"""
        if '.' in value_str:
            return ParameterType.FLOAT
        return ParameterType.INTEGER
    
    def _parse_default_value(self, value_str: str, param_type: ParameterType) -> Any:
        """Parse default value based on parameter type"""
        
        try:
            if param_type == ParameterType.INTEGER:
                return int(float(value_str))
            elif param_type == ParameterType.FLOAT:
                return float(value_str)
            elif param_type == ParameterType.BOOLEAN:
                return value_str == "True"
            elif param_type == ParameterType.VECTOR3:
                # Parse vector like "(1, 2, 3)"
                numbers = re.findall(r'-?\d+\.?\d*', value_str)
                return [float(n) for n in numbers[:3]]
            elif param_type == ParameterType.COLOR:
                # Parse color like "(1.0, 0.5, 0.2, 1.0)"
                numbers = re.findall(r'-?\d+\.?\d*', value_str)
                return [float(n) for n in numbers[:4]]
            else:
                return value_str
                
        except (ValueError, TypeError):
            return value_str
    
    def _create_code_template(self, code: str, parameters: List[ActionParameter]) -> str:
        """Create code template with parameter placeholders"""
        
        template = code
        
        for param in parameters:
            # Replace parameter values with placeholders
            if param.param_type == ParameterType.STRING:
                # Replace string literals
                pattern = rf'\b{re.escape(param.name)}\s*=\s*["\'][^"\']*["\']'
                replacement = f'{param.name} = "{{{param.name}}}"'
                template = re.sub(pattern, replacement, template)
            
            elif param.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                # Replace numeric values
                pattern = rf'\b{re.escape(param.name)}\s*=\s*\d+\.?\d*'
                replacement = f'{param.name} = {{{param.name}}}'
                template = re.sub(pattern, replacement, template)
            
            elif param.param_type == ParameterType.BOOLEAN:
                # Replace boolean values
                pattern = rf'\b{re.escape(param.name)}\s*=\s*(True|False)'
                replacement = f'{param.name} = {{{param.name}}}'
                template = re.sub(pattern, replacement, template)
            
            elif param.param_type == ParameterType.VECTOR3:
                # Replace vector values
                pattern = rf'{re.escape(param.name)}\s*=\s*\([^)]+\)'
                replacement = f'{param.name} = {{{param.name}}}'
                template = re.sub(pattern, replacement, template)
            
            elif param.param_type == ParameterType.COLOR:
                # Replace color values
                pattern = rf'color\s*=\s*\([^)]+\)'
                replacement = f'color = {{{param.name}}}'
                template = re.sub(pattern, replacement, template)
        
        return template
    
    def execute_action(self, action_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action with given parameters"""
        
        if action_id not in self._actions:
            return {"error": f"Action '{action_id}' not found"}
        
        action = self._actions[action_id]
        
        try:
            # Validate parameters
            validation_result = self._validate_parameters(action, parameters)
            if not validation_result["valid"]:
                return {"error": f"Parameter validation failed: {validation_result['error']}"}
            
            # Generate code from template
            code = self._generate_code_from_template(action, parameters)
            
            # Execute code
            execution_result = self.code_executor.execute_code(code)
            
            # Update usage statistics
            action.usage_count += 1
            action.last_used = time.time()
            self._save_actions()
            
            return {
                "success": execution_result["success"],
                "output": execution_result.get("output", ""),
                "error": execution_result.get("error", ""),
                "code": code,
                "action_name": action.name
            }
            
        except Exception as e:
            return {"error": f"Action execution failed: {str(e)}"}
    
    def _validate_parameters(self, action: UserAction, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters for an action"""
        
        for param in action.parameters:
            if param.name not in parameters:
                # Use default value if not provided
                parameters[param.name] = param.default_value
                continue
            
            value = parameters[param.name]
            
            # Type validation
            if param.param_type == ParameterType.INTEGER:
                if not isinstance(value, int):
                    try:
                        parameters[param.name] = int(value)
                    except (ValueError, TypeError):
                        return {"valid": False, "error": f"Parameter '{param.name}' must be an integer"}
            
            elif param.param_type == ParameterType.FLOAT:
                if not isinstance(value, (int, float)):
                    try:
                        parameters[param.name] = float(value)
                    except (ValueError, TypeError):
                        return {"valid": False, "error": f"Parameter '{param.name}' must be a number"}
            
            elif param.param_type == ParameterType.BOOLEAN:
                if not isinstance(value, bool):
                    if isinstance(value, str):
                        parameters[param.name] = value.lower() in ['true', '1', 'yes', 'on']
                    else:
                        parameters[param.name] = bool(value)
            
            elif param.param_type == ParameterType.VECTOR3:
                if not isinstance(value, (list, tuple)) or len(value) != 3:
                    return {"valid": False, "error": f"Parameter '{param.name}' must be a 3-element vector"}
                try:
                    parameters[param.name] = [float(x) for x in value]
                except (ValueError, TypeError):
                    return {"valid": False, "error": f"Parameter '{param.name}' must contain numeric values"}
            
            elif param.param_type == ParameterType.COLOR:
                if not isinstance(value, (list, tuple)) or len(value) not in [3, 4]:
                    return {"valid": False, "error": f"Parameter '{param.name}' must be a 3 or 4-element color"}
                try:
                    parameters[param.name] = [float(x) for x in value]
                    if len(parameters[param.name]) == 3:
                        parameters[param.name].append(1.0)  # Add alpha
                except (ValueError, TypeError):
                    return {"valid": False, "error": f"Parameter '{param.name}' must contain numeric values"}
            
            # Range validation
            if param.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                if param.min_value is not None and parameters[param.name] < param.min_value:
                    return {"valid": False, "error": f"Parameter '{param.name}' must be >= {param.min_value}"}
                if param.max_value is not None and parameters[param.name] > param.max_value:
                    return {"valid": False, "error": f"Parameter '{param.name}' must be <= {param.max_value}"}
        
        return {"valid": True}
    
    def _generate_code_from_template(self, action: UserAction, parameters: Dict[str, Any]) -> str:
        """Generate executable code from template and parameters"""
        
        code = action.code_template
        
        # Replace parameter placeholders
        for param_name, param_value in parameters.items():
            placeholder = f"{{{param_name}}}"
            
            if isinstance(param_value, str):
                replacement = f'"{param_value}"'
            elif isinstance(param_value, (list, tuple)):
                replacement = str(tuple(param_value))
            else:
                replacement = str(param_value)
            
            code = code.replace(placeholder, replacement)
        
        return code

    def get_action(self, action_id: str) -> Optional[UserAction]:
        """Get action by ID"""
        return self._actions.get(action_id)

    def get_all_actions(self) -> List[UserAction]:
        """Get all actions"""
        return list(self._actions.values())

    def get_actions_by_category(self, category: str) -> List[UserAction]:
        """Get actions by category"""
        return [action for action in self._actions.values() if action.category == category]

    def search_actions(self, query: str) -> List[UserAction]:
        """Search actions by name, description, or tags"""
        query_lower = query.lower()
        results = []

        for action in self._actions.values():
            if (query_lower in action.name.lower() or
                query_lower in action.description.lower() or
                any(query_lower in tag.lower() for tag in action.tags)):
                results.append(action)

        return results

    def delete_action(self, action_id: str) -> bool:
        """Delete an action"""
        if action_id in self._actions:
            del self._actions[action_id]
            self._save_actions()
            return True
        return False

    def update_action(
        self,
        action_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Update action metadata"""

        if action_id not in self._actions:
            return False

        action = self._actions[action_id]

        if name is not None:
            action.name = name
        if description is not None:
            action.description = description
        if category is not None:
            action.category = category
        if tags is not None:
            action.tags = tags

        self._save_actions()
        return True

    def get_action_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for action in self._actions.values():
            categories.add(action.category)
        return sorted(list(categories))

    def get_popular_actions(self, limit: int = 10) -> List[UserAction]:
        """Get most used actions"""
        actions = list(self._actions.values())
        actions.sort(key=lambda a: a.usage_count, reverse=True)
        return actions[:limit]

    def get_recent_actions(self, limit: int = 10) -> List[UserAction]:
        """Get recently used actions"""
        actions = [a for a in self._actions.values() if a.last_used > 0]
        actions.sort(key=lambda a: a.last_used, reverse=True)
        return actions[:limit]

    def export_actions(self, file_path: str, action_ids: Optional[List[str]] = None) -> bool:
        """Export actions to file"""

        try:
            if action_ids is None:
                actions_to_export = list(self._actions.values())
            else:
                actions_to_export = [self._actions[aid] for aid in action_ids if aid in self._actions]

            export_data = {
                "version": "1.0",
                "export_time": time.time(),
                "actions": [self._action_to_dict(action) for action in actions_to_export]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Export failed: {e}")
            return False

    def import_actions(self, file_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Import actions from file"""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            imported_count = 0
            skipped_count = 0
            errors = []

            for action_data in import_data.get("actions", []):
                try:
                    action = self._action_from_dict(action_data)

                    if action.id in self._actions and not overwrite:
                        skipped_count += 1
                        continue

                    self._actions[action.id] = action
                    imported_count += 1

                except Exception as e:
                    errors.append(f"Failed to import action: {e}")

            if imported_count > 0:
                self._save_actions()

            return {
                "success": True,
                "imported": imported_count,
                "skipped": skipped_count,
                "errors": errors
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_action_id(self, name: str) -> str:
        """Generate unique action ID"""
        import hashlib

        base_id = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
        timestamp = str(int(time.time()))

        # Create hash to ensure uniqueness
        hash_input = f"{base_id}_{timestamp}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]

        return f"{base_id}_{hash_suffix}"

    def _action_to_dict(self, action: UserAction) -> Dict[str, Any]:
        """Convert action to dictionary for serialization"""

        return {
            "id": action.id,
            "name": action.name,
            "description": action.description,
            "code_template": action.code_template,
            "parameters": [
                {
                    "name": param.name,
                    "type": param.param_type.value,
                    "description": param.description,
                    "default_value": param.default_value,
                    "min_value": param.min_value,
                    "max_value": param.max_value,
                    "options": param.options
                }
                for param in action.parameters
            ],
            "category": action.category,
            "tags": action.tags,
            "created_time": action.created_time,
            "usage_count": action.usage_count,
            "last_used": action.last_used,
            "author": action.author
        }

    def _action_from_dict(self, data: Dict[str, Any]) -> UserAction:
        """Create action from dictionary"""

        parameters = []
        for param_data in data.get("parameters", []):
            param = ActionParameter(
                name=param_data["name"],
                param_type=ParameterType(param_data["type"]),
                description=param_data["description"],
                default_value=param_data["default_value"],
                min_value=param_data.get("min_value"),
                max_value=param_data.get("max_value"),
                options=param_data.get("options")
            )
            parameters.append(param)

        return UserAction(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            code_template=data["code_template"],
            parameters=parameters,
            category=data.get("category", "General"),
            tags=data.get("tags", []),
            created_time=data.get("created_time", time.time()),
            usage_count=data.get("usage_count", 0),
            last_used=data.get("last_used", 0.0),
            author=data.get("author", "User")
        )

    def _get_actions_file_path(self) -> str:
        """Get path for actions storage file"""
        user_data_dir = self.file_manager.get_user_data_dir()
        return f"{user_data_dir}/blendpro_actions.json"

    def _save_actions(self) -> None:
        """Save actions to file"""

        try:
            file_path = self._get_actions_file_path()

            actions_data = {
                "version": "1.0",
                "last_updated": time.time(),
                "actions": [self._action_to_dict(action) for action in self._actions.values()]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(actions_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Failed to save actions: {e}")

    def _load_actions(self) -> None:
        """Load actions from file"""

        try:
            file_path = self._get_actions_file_path()

            if not self.file_manager.get_file_manager().get_user_data_dir():
                return

            import os
            if not os.path.exists(file_path):
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                actions_data = json.load(f)

            for action_data in actions_data.get("actions", []):
                try:
                    action = self._action_from_dict(action_data)
                    self._actions[action.id] = action
                except Exception as e:
                    print(f"Failed to load action: {e}")

        except Exception as e:
            print(f"Failed to load actions: {e}")

    def get_library_stats(self) -> Dict[str, Any]:
        """Get action library statistics"""

        total_actions = len(self._actions)
        total_usage = sum(action.usage_count for action in self._actions.values())
        categories = self.get_action_categories()

        return {
            "total_actions": total_actions,
            "total_usage": total_usage,
            "categories": len(categories),
            "category_list": categories,
            "most_used": self.get_popular_actions(5),
            "recently_used": self.get_recent_actions(5)
        }

# Global action library instance
_action_library: Optional[ActionLibrary] = None

def get_action_library() -> ActionLibrary:
    """Get global action library instance"""
    global _action_library
    if _action_library is None:
        _action_library = ActionLibrary()
    return _action_library
