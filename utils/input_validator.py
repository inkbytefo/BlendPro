"""
Input Validation System for BlendPro: AI Co-Pilot
Provides comprehensive input validation and sanitization
"""

import re
import ast
import keyword
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .logger import get_logger

class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    sanitized_input: Optional[str] = None
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []

class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    def __init__(self):
        self.logger = get_logger("BlendPro.Validator")
        
        # Dangerous Python keywords and functions to block
        self.dangerous_keywords = {
            'exec', 'eval', 'compile', '__import__', 'open', 'file',
            'input', 'raw_input', 'reload', 'vars', 'globals', 'locals',
            'dir', 'hasattr', 'getattr', 'setattr', 'delattr'
        }
        
        # Dangerous modules to block in code
        self.dangerous_modules = {
            'os', 'sys', 'subprocess', 'shutil', 'pickle', 'marshal',
            'imp', 'importlib', 'socket', 'urllib', 'http', 'ftplib',
            'smtplib', 'telnetlib', 'webbrowser'
        }
        
        # Safe Blender modules
        self.safe_blender_modules = {
            'bpy', 'bmesh', 'mathutils', 'gpu', 'bl_ui', 'bgl'
        }
        
        # Maximum input lengths
        self.max_lengths = {
            'user_input': 5000,
            'api_key': 200,
            'model_name': 100,
            'file_path': 500
        }
    
    def validate_user_input(self, text: str) -> ValidationResult:
        """Validate user chat input"""
        if not text or not text.strip():
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Input cannot be empty",
                sanitized_input=""
            )
        
        # Check length
        if len(text) > self.max_lengths['user_input']:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Input too long. Maximum {self.max_lengths['user_input']} characters allowed.",
                sanitized_input=text[:self.max_lengths['user_input']]
            )
        
        # Check for potential injection attempts
        issues = []
        sanitized = text
        
        # Remove potential script tags
        if re.search(r'<script.*?</script>', text, re.IGNORECASE | re.DOTALL):
            issues.append("Removed potential script tags")
            sanitized = re.sub(r'<script.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Check for SQL injection patterns
        sql_patterns = [
            r'\b(union|select|insert|update|delete|drop|create|alter)\b',
            r'[\'";].*?[\'";]',
            r'--.*$'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append("Potential SQL injection pattern detected")
                break
        
        # Check for excessive special characters
        special_char_ratio = len(re.findall(r'[^\w\s]', text)) / len(text)
        if special_char_ratio > 0.3:
            issues.append("High ratio of special characters")
        
        severity = ValidationSeverity.WARNING if issues else ValidationSeverity.INFO
        
        return ValidationResult(
            is_valid=True,
            severity=severity,
            message="Input validated" if not issues else f"Input validated with warnings: {', '.join(issues)}",
            sanitized_input=sanitized.strip(),
            issues=issues
        )
    
    def validate_code_safety(self, code: str) -> ValidationResult:
        """Validate Python code for safety"""
        if not code or not code.strip():
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Code cannot be empty"
            )
        
        issues = []
        
        try:
            # Parse the code to check syntax
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Syntax error in code: {str(e)}"
            )
        
        # Check for dangerous keywords
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in self.dangerous_keywords:
                issues.append(f"Dangerous keyword detected: {node.id}")
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.dangerous_modules:
                        issues.append(f"Dangerous module import: {alias.name}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module in self.dangerous_modules:
                    issues.append(f"Dangerous module import: {node.module}")
        
        # Check for file operations
        file_operations = ['open', 'file', 'read', 'write', 'remove', 'delete']
        for op in file_operations:
            if re.search(rf'\b{op}\s*\(', code):
                issues.append(f"File operation detected: {op}")
        
        # Check for network operations
        network_patterns = [
            r'urllib', r'requests', r'socket', r'http', r'ftp'
        ]
        for pattern in network_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"Network operation detected: {pattern}")
        
        # Determine severity
        critical_issues = [issue for issue in issues if any(
            dangerous in issue.lower() for dangerous in ['exec', 'eval', 'import os', 'import sys']
        )]
        
        if critical_issues:
            severity = ValidationSeverity.CRITICAL
            is_valid = False
        elif issues:
            severity = ValidationSeverity.WARNING
            is_valid = True
        else:
            severity = ValidationSeverity.INFO
            is_valid = True
        
        return ValidationResult(
            is_valid=is_valid,
            severity=severity,
            message="Code safety validated" if not issues else f"Safety issues found: {', '.join(issues)}",
            issues=issues
        )
    
    def sanitize_code(self, code: str) -> str:
        """Sanitize code by removing dangerous elements"""
        if not code:
            return ""
        
        sanitized = code
        
        # Remove dangerous imports
        for module in self.dangerous_modules:
            sanitized = re.sub(rf'import\s+{module}.*?\n', '', sanitized)
            sanitized = re.sub(rf'from\s+{module}\s+import.*?\n', '', sanitized)
        
        # Remove dangerous function calls
        for keyword in self.dangerous_keywords:
            sanitized = re.sub(rf'\b{keyword}\s*\([^)]*\)', f'# {keyword} call removed', sanitized)
        
        return sanitized
    
    def validate_api_key(self, api_key: str) -> ValidationResult:
        """Validate API key format"""
        if not api_key or not api_key.strip():
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="API key cannot be empty"
            )
        
        api_key = api_key.strip()
        
        # Check length
        if len(api_key) > self.max_lengths['api_key']:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"API key too long. Maximum {self.max_lengths['api_key']} characters."
            )
        
        # Check for OpenAI API key format
        if api_key.startswith('sk-'):
            if len(api_key) < 20:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message="OpenAI API key appears to be too short"
                )
        
        # Check for suspicious characters
        if not re.match(r'^[a-zA-Z0-9\-_]+$', api_key):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="API key contains invalid characters"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="API key format validated",
            sanitized_input=api_key
        )
    
    def validate_file_path(self, file_path: str) -> ValidationResult:
        """Validate file path for safety"""
        if not file_path:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="File path cannot be empty"
            )
        
        issues = []
        
        # Check for path traversal attempts
        if '..' in file_path:
            issues.append("Path traversal attempt detected")
        
        # Check for absolute paths outside safe directories
        if file_path.startswith('/') or (len(file_path) > 1 and file_path[1] == ':'):
            issues.append("Absolute path detected")
        
        # Check for dangerous file extensions
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.sh', '.ps1', '.vbs']
        if any(file_path.lower().endswith(ext) for ext in dangerous_extensions):
            issues.append("Dangerous file extension detected")
        
        severity = ValidationSeverity.WARNING if issues else ValidationSeverity.INFO
        is_valid = len(issues) == 0 or all('Absolute path' not in issue for issue in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            severity=severity,
            message="File path validated" if not issues else f"Path issues: {', '.join(issues)}",
            issues=issues
        )

# Global validator instance
_input_validator: Optional[InputValidator] = None

def get_input_validator() -> InputValidator:
    """Get global input validator instance"""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator

# Convenience functions
def validate_user_input(text: str) -> ValidationResult:
    """Validate user input"""
    return get_input_validator().validate_user_input(text)

def validate_code_safety(code: str) -> ValidationResult:
    """Validate code safety"""
    return get_input_validator().validate_code_safety(code)

def sanitize_code(code: str) -> str:
    """Sanitize code"""
    return get_input_validator().sanitize_code(code)

def validate_api_key(api_key: str) -> ValidationResult:
    """Validate API key"""
    return get_input_validator().validate_api_key(api_key)
