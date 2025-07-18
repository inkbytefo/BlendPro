"""
Code Executor for BlendPro: AI Co-Pilot
Safe execution of generated Python code in Blender
"""

import sys
import traceback
import time
from typing import Dict, Any, Optional, List, Callable
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import bpy

from ..config.settings import get_settings
from .backup_manager import get_backup_manager
from .logger import get_logger, log_code_execution, log_error_with_context
from .input_validator import get_input_validator, ValidationSeverity

class CodeExecutionError(Exception):
    """Custom exception for code execution errors"""

    def __init__(self, message: str, code: Optional[str] = None, line_number: Optional[int] = None, error_type: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.line_number = line_number
        self.error_type = error_type

    def __str__(self) -> str:
        if self.line_number and self.error_type:
            return f"Code Execution Error [{self.error_type}] at line {self.line_number}: {self.message}"
        elif self.error_type:
            return f"Code Execution Error [{self.error_type}]: {self.message}"
        return f"Code Execution Error: {self.message}"

class CodeExecutor:
    """Handles safe execution of generated Python code"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("BlendPro.CodeExec")
        self.backup_manager = get_backup_manager()
        self.input_validator = get_input_validator()
        self._execution_history: List[Dict[str, Any]] = []
        self._max_history = 50
    
    def _validate_code(self, code: str) -> Dict[str, Any]:
        """Validate code for safety before execution"""
        validation_result = {
            "is_safe": True,
            "warnings": [],
            "errors": []
        }
        
        # Check for potentially dangerous operations
        dangerous_patterns = [
            ("import subprocess", "Subprocess operations not allowed"),
            ("import os", "OS operations should be limited"),
            ("exec(", "Dynamic code execution not recommended"),
            ("eval(", "Dynamic evaluation not recommended"),
            ("__import__", "Dynamic imports not allowed"),
            ("open(", "File operations should be reviewed"),
            ("file(", "File operations should be reviewed"),
            ("input(", "User input operations not allowed"),
            ("raw_input(", "User input operations not allowed"),
        ]
        
        for pattern, warning in dangerous_patterns:
            if pattern in code:
                validation_result["warnings"].append(warning)
        
        # Check for syntax errors
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            validation_result["is_safe"] = False
            validation_result["errors"].append(f"Syntax error: {e}")
        
        # Check for required Blender imports
        if "bpy." in code and "import bpy" not in code:
            validation_result["warnings"].append("Code uses bpy but doesn't import it")
        
        return validation_result
    
    def _create_safe_namespace(self) -> Dict[str, Any]:
        """Create a safe namespace for code execution"""
        # Start with a minimal namespace
        safe_namespace = {
            '__builtins__': {
                # Allow basic built-ins
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'print': print,
                'abs': abs,
                'min': min,
                'max': max,
                'sum': sum,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
            }
        }
        
        # Add commonly used modules
        import math
        import random
        import mathutils
        
        safe_namespace.update({
            'bpy': bpy,
            'math': math,
            'random': random,
            'mathutils': mathutils,
        })
        
        # Add bmesh if available
        try:
            import bmesh
            safe_namespace['bmesh'] = bmesh
        except ImportError:
            pass
        
        return safe_namespace
    
    def execute_code(self, code: str, show_preview: bool = True) -> Dict[str, Any]:
        """Execute Python code with safety checks and error handling"""
        execution_start = time.time()
        
        # Validate code first with enhanced validation
        validation = self._validate_code(code)
        enhanced_validation = self.input_validator.validate_code_safety(code)

        if not validation["is_safe"] or not enhanced_validation.is_valid:
            error_details = validation["errors"] + (enhanced_validation.issues or [])
            self.logger.error("Code validation failed",
                            validation_errors=validation["errors"],
                            enhanced_errors=enhanced_validation.issues,
                            code_length=len(code))
            return {
                "success": False,
                "error": "Code validation failed",
                "details": error_details,
                "warnings": validation["warnings"]
            }

        # Log validation warnings
        if validation["warnings"] or enhanced_validation.severity == ValidationSeverity.WARNING:
            all_warnings = validation["warnings"] + (enhanced_validation.issues or [])
            self.logger.warning("Code validation warnings", warnings=all_warnings)
        
        # Create backup before execution if enabled
        backup_path = None
        if self.settings.enable_auto_backup:
            try:
                backup_path = self.backup_manager.create_backup(force=True)
            except Exception as e:
                print(f"Warning: Failed to create backup before code execution: {e}")
        
        # Capture output
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        execution_result = {
            "success": False,
            "output": "",
            "error": "",
            "warnings": validation["warnings"],
            "execution_time": 0,
            "backup_created": backup_path is not None,
            "backup_path": backup_path
        }
        
        try:
            # Create safe execution namespace
            namespace = self._create_safe_namespace()
            
            # Execute code with output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, namespace)
            
            # Capture results
            execution_result.update({
                "success": True,
                "output": stdout_capture.getvalue(),
                "error": stderr_capture.getvalue(),
                "execution_time": time.time() - execution_start
            })
            
        except Exception as e:
            # Capture execution error
            error_traceback = traceback.format_exc()
            execution_result.update({
                "success": False,
                "error": str(e),
                "traceback": error_traceback,
                "execution_time": time.time() - execution_start
            })
        
        # Log execution result
        execution_time = execution_result["execution_time"]
        success = execution_result["success"]
        log_code_execution(len(code), execution_time, success)

        if not success:
            log_error_with_context(
                Exception(execution_result.get("error", "Unknown error")),
                {"code_length": len(code), "execution_time": execution_time},
                "code execution"
            )

        # Add to execution history
        self._add_to_history(code, execution_result)

        return execution_result
    
    def _add_to_history(self, code: str, result: Dict[str, Any]) -> None:
        """Add execution to history"""
        history_entry = {
            "timestamp": time.time(),
            "code": code,
            "success": result["success"],
            "execution_time": result["execution_time"],
            "error": result.get("error", ""),
            "backup_path": result.get("backup_path")
        }
        
        self._execution_history.append(history_entry)
        
        # Limit history size
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution history"""
        return self._execution_history[-limit:] if self._execution_history else []
    
    def get_last_execution(self) -> Optional[Dict[str, Any]]:
        """Get the last execution result"""
        return self._execution_history[-1] if self._execution_history else None
    
    def undo_last_execution(self) -> bool:
        """Undo the last code execution by restoring backup"""
        last_execution = self.get_last_execution()
        
        if not last_execution or not last_execution.get("backup_path"):
            return False
        
        try:
            return self.backup_manager.restore_backup(last_execution["backup_path"])
        except Exception as e:
            print(f"Failed to undo last execution: {e}")
            return False
    
    def clear_history(self) -> None:
        """Clear execution history"""
        self._execution_history.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self._execution_history:
            return {"total_executions": 0}
        
        successful = sum(1 for entry in self._execution_history if entry["success"])
        failed = len(self._execution_history) - successful
        avg_time = sum(entry["execution_time"] for entry in self._execution_history) / len(self._execution_history)
        
        return {
            "total_executions": len(self._execution_history),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(self._execution_history) * 100,
            "average_execution_time": avg_time,
            "last_execution_time": self._execution_history[-1]["timestamp"] if self._execution_history else None
        }

# Global code executor instance
_code_executor: Optional[CodeExecutor] = None

def get_code_executor() -> CodeExecutor:
    """Get global code executor instance"""
    global _code_executor
    if _code_executor is None:
        _code_executor = CodeExecutor()
    return _code_executor

def execute_code(code: str, show_preview: bool = True) -> Dict[str, Any]:
    """Convenience function to execute code"""
    return get_code_executor().execute_code(code, show_preview=show_preview)
