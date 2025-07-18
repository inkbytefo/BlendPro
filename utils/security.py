"""
Security Manager for BlendPro: AI Co-Pilot
Provides comprehensive security validation and protection
"""

import re
import hashlib
import secrets
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .logger import get_logger

class SecurityLevel(Enum):
    """Security threat levels"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityResult:
    """Result of security analysis"""
    is_safe: bool
    level: SecurityLevel
    threats: List[str]
    recommendations: List[str]
    sanitized_content: Optional[str] = None

class SecurityManager:
    """Comprehensive security management system"""
    
    def __init__(self):
        self.logger = get_logger("BlendPro.Security")
        
        # Rate limiting storage
        self._rate_limits: Dict[str, List[float]] = {}
        self._blocked_ips: Set[str] = set()
        
        # Security patterns
        self.dangerous_patterns = {
            # Code injection patterns
            'code_injection': [
                r'exec\s*\(',
                r'eval\s*\(',
                r'__import__\s*\(',
                r'compile\s*\(',
                r'globals\s*\(\)',
                r'locals\s*\(\)'
            ],
            
            # File system access
            'file_access': [
                r'open\s*\(',
                r'file\s*\(',
                r'\.read\s*\(',
                r'\.write\s*\(',
                r'os\.system',
                r'subprocess\.',
                r'shutil\.'
            ],
            
            # Network access
            'network_access': [
                r'urllib\.',
                r'requests\.',
                r'socket\.',
                r'http\.',
                r'ftp\.',
                r'smtp\.'
            ],
            
            # System access
            'system_access': [
                r'os\.environ',
                r'sys\.exit',
                r'sys\.path',
                r'importlib\.',
                r'__builtins__'
            ]
        }
        
        # Suspicious keywords
        self.suspicious_keywords = {
            'password', 'secret', 'token', 'key', 'auth', 'credential',
            'admin', 'root', 'sudo', 'chmod', 'chown', 'rm -rf',
            'format c:', 'del /f', 'rmdir /s'
        }
        
        # Safe Blender operations
        self.safe_blender_operations = {
            'bpy.ops.mesh', 'bpy.ops.object', 'bpy.ops.material',
            'bpy.ops.scene', 'bpy.ops.render', 'bpy.context',
            'bpy.data', 'bmesh', 'mathutils'
        }
    
    def validate_code_safety(self, code: str) -> SecurityResult:
        """Comprehensive code safety validation"""
        threats = []
        recommendations = []
        
        if not code or not code.strip():
            return SecurityResult(
                is_safe=True,
                level=SecurityLevel.SAFE,
                threats=[],
                recommendations=[]
            )
        
        # Check for dangerous patterns
        for category, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    threats.append(f"Dangerous {category} pattern detected: {pattern}")
        
        # Check for suspicious keywords
        code_lower = code.lower()
        for keyword in self.suspicious_keywords:
            if keyword in code_lower:
                threats.append(f"Suspicious keyword detected: {keyword}")
        
        # Check for obfuscation attempts
        if self._detect_obfuscation(code):
            threats.append("Potential code obfuscation detected")
        
        # Check for excessive complexity
        complexity_score = self._calculate_complexity(code)
        if complexity_score > 100:
            threats.append(f"High code complexity detected: {complexity_score}")
            recommendations.append("Consider breaking down complex operations")
        
        # Determine security level
        level = self._determine_security_level(threats)
        is_safe = level in [SecurityLevel.SAFE, SecurityLevel.LOW]
        
        # Generate recommendations
        if threats:
            recommendations.extend([
                "Review code for security implications",
                "Ensure code only performs intended Blender operations",
                "Consider using safer alternatives"
            ])
        
        return SecurityResult(
            is_safe=is_safe,
            level=level,
            threats=threats,
            recommendations=recommendations,
            sanitized_content=self._sanitize_code(code) if not is_safe else None
        )
    
    def validate_api_key_security(self, api_key: str) -> SecurityResult:
        """Validate API key security"""
        threats = []
        recommendations = []
        
        if not api_key:
            return SecurityResult(
                is_safe=False,
                level=SecurityLevel.HIGH,
                threats=["Empty API key"],
                recommendations=["Provide a valid API key"]
            )
        
        # Check for common weak patterns
        if len(api_key) < 20:
            threats.append("API key appears too short")
        
        if api_key.lower() in ['test', 'demo', 'example', 'placeholder']:
            threats.append("API key appears to be a placeholder")
        
        # Check for proper format
        if not re.match(r'^[a-zA-Z0-9\-_]+$', api_key):
            threats.append("API key contains invalid characters")
        
        # Check for exposure in logs
        if self._check_key_exposure_risk(api_key):
            threats.append("API key may be at risk of exposure")
            recommendations.append("Ensure API key is not logged or displayed")
        
        level = self._determine_security_level(threats)
        is_safe = level in [SecurityLevel.SAFE, SecurityLevel.LOW]
        
        return SecurityResult(
            is_safe=is_safe,
            level=level,
            threats=threats,
            recommendations=recommendations
        )
    
    def check_rate_limiting(self, identifier: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """Check if request should be rate limited"""
        current_time = time.time()
        
        # Clean old entries
        if identifier in self._rate_limits:
            self._rate_limits[identifier] = [
                timestamp for timestamp in self._rate_limits[identifier]
                if current_time - timestamp < window_seconds
            ]
        else:
            self._rate_limits[identifier] = []
        
        # Check if limit exceeded
        if len(self._rate_limits[identifier]) >= max_requests:
            self.logger.warning("Rate limit exceeded", identifier=identifier)
            return True
        
        # Add current request
        self._rate_limits[identifier].append(current_time)
        return False
    
    def sanitize_user_input(self, user_input: str) -> str:
        """Sanitize user input for safe processing"""
        if not user_input:
            return ""
        
        # Remove potential script tags
        sanitized = re.sub(r'<script.*?</script>', '', user_input, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove potential SQL injection patterns
        sanitized = re.sub(r'[\'";].*?[\'";]', '', sanitized)
        sanitized = re.sub(r'--.*$', '', sanitized, flags=re.MULTILINE)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit length
        if len(sanitized) > 5000:
            sanitized = sanitized[:5000] + "..."
        
        return sanitized
    
    def _detect_obfuscation(self, code: str) -> bool:
        """Detect potential code obfuscation"""
        # Check for excessive string concatenation
        if code.count('+') > 20 and code.count('"') > 10:
            return True
        
        # Check for base64-like patterns
        if re.search(r'[A-Za-z0-9+/]{20,}={0,2}', code):
            return True
        
        # Check for hex encoding
        if re.search(r'\\x[0-9a-fA-F]{2}', code):
            return True
        
        # Check for excessive escape sequences
        if code.count('\\') > len(code) * 0.1:
            return True
        
        return False
    
    def _calculate_complexity(self, code: str) -> int:
        """Calculate code complexity score"""
        complexity = 0
        
        # Count control structures
        complexity += len(re.findall(r'\b(if|for|while|try|except|with)\b', code))
        
        # Count function definitions
        complexity += len(re.findall(r'\bdef\s+\w+', code))
        
        # Count nested structures
        complexity += code.count('{') + code.count('[') + code.count('(')
        
        # Count lines
        complexity += len(code.split('\n'))
        
        return complexity
    
    def _determine_security_level(self, threats: List[str]) -> SecurityLevel:
        """Determine security level based on threats"""
        if not threats:
            return SecurityLevel.SAFE
        
        critical_keywords = ['exec', 'eval', 'system', 'subprocess']
        high_keywords = ['import', 'file', 'network']
        
        for threat in threats:
            threat_lower = threat.lower()
            if any(keyword in threat_lower for keyword in critical_keywords):
                return SecurityLevel.CRITICAL
            elif any(keyword in threat_lower for keyword in high_keywords):
                return SecurityLevel.HIGH
        
        if len(threats) > 3:
            return SecurityLevel.MEDIUM
        else:
            return SecurityLevel.LOW
    
    def _sanitize_code(self, code: str) -> str:
        """Sanitize dangerous code"""
        sanitized = code
        
        # Remove dangerous function calls
        for category, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                sanitized = re.sub(pattern, f'# {pattern} removed for security', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def _check_key_exposure_risk(self, api_key: str) -> bool:
        """Check if API key has exposure risk"""
        # Check if key appears to be in a common format that might be logged
        if api_key.startswith('sk-') and len(api_key) > 40:
            return False  # Proper OpenAI format
        
        # Check for test/demo patterns
        test_patterns = ['test', 'demo', 'example', '123', 'abc']
        return any(pattern in api_key.lower() for pattern in test_patterns)

# Global security manager instance
_security_manager: Optional[SecurityManager] = None

def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager

# Convenience functions
def validate_code_safety(code: str) -> SecurityResult:
    """Validate code safety"""
    return get_security_manager().validate_code_safety(code)

def validate_api_key_security(api_key: str) -> SecurityResult:
    """Validate API key security"""
    return get_security_manager().validate_api_key_security(api_key)

def sanitize_user_input(user_input: str) -> str:
    """Sanitize user input"""
    return get_security_manager().sanitize_user_input(user_input)

def check_rate_limiting(identifier: str, max_requests: int = 60) -> bool:
    """Check rate limiting"""
    return get_security_manager().check_rate_limiting(identifier, max_requests)
