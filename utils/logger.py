"""
Centralized Logging System for BlendPro: AI Co-Pilot
Provides structured logging with different levels and formatters
"""

import logging
import sys
import os
from typing import Optional, Dict, Any
from pathlib import Path
import bpy

# Try to import colorlog for colored console output
try:
    from colorlog import ColoredFormatter
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False

class BlendProLogger:
    """Centralized logger for BlendPro with multiple output handlers"""
    
    def __init__(self, name: str = "BlendPro"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers for console and file output"""
        
        # Console handler with colors if available
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        if COLORLOG_AVAILABLE:
            console_formatter = ColoredFormatter(
                '%(log_color)s[%(asctime)s] %(name)s - %(levelname)s: %(message)s',
                datefmt='%H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            console_formatter = logging.Formatter(
                '[%(asctime)s] %(name)s - %(levelname)s: %(message)s',
                datefmt='%H:%M:%S'
            )
        
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for persistent logging
        try:
            log_dir = self._get_log_directory()
            if log_dir:
                log_file = log_dir / "blendpro.log"
                file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                
                file_formatter = logging.Formatter(
                    '[%(asctime)s] %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
                
                self.logger.debug(f"File logging enabled: {log_file}")
        except Exception as e:
            self.logger.warning(f"Could not setup file logging: {e}")
    
    def _get_log_directory(self) -> Optional[Path]:
        """Get appropriate directory for log files"""
        try:
            # Try to use Blender's user config directory
            if hasattr(bpy.utils, 'user_resource'):
                config_dir = Path(bpy.utils.user_resource('CONFIG'))
                log_dir = config_dir / "blendpro" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                return log_dir
        except Exception:
            pass
        
        try:
            # Fallback to temp directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "blendpro" / "logs"
            temp_dir.mkdir(parents=True, exist_ok=True)
            return temp_dir
        except Exception:
            pass
        
        return None
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(self._format_message(message, **kwargs))
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(self._format_message(message, **kwargs))
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format log message with additional context"""
        if kwargs:
            context_parts = []
            for key, value in kwargs.items():
                if isinstance(value, dict):
                    context_parts.append(f"{key}={len(value)} items")
                elif isinstance(value, (list, tuple)):
                    context_parts.append(f"{key}={len(value)} items")
                else:
                    context_parts.append(f"{key}={value}")
            
            if context_parts:
                return f"{message} [{', '.join(context_parts)}]"
        
        return message
    
    def set_level(self, level: str):
        """Set logging level"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            self.logger.setLevel(level_map[level.upper()])
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    handler.setLevel(level_map[level.upper()])

# Global logger instances
_loggers: Dict[str, BlendProLogger] = {}

def get_logger(name: str = "BlendPro") -> BlendProLogger:
    """Get or create a logger instance"""
    if name not in _loggers:
        _loggers[name] = BlendProLogger(name)
    return _loggers[name]

def setup_logging(level: str = "INFO"):
    """Setup global logging configuration"""
    logger = get_logger()
    logger.set_level(level)
    logger.info("BlendPro logging system initialized", level=level)

# Convenience functions for common logging operations
def log_api_request(endpoint: str, model: str, tokens: int, duration: float):
    """Log API request details"""
    logger = get_logger("BlendPro.API")
    logger.info(f"API request completed", 
                endpoint=endpoint, 
                model=model, 
                tokens=tokens, 
                duration_ms=round(duration * 1000, 2))

def log_code_execution(code_length: int, execution_time: float, success: bool):
    """Log code execution details"""
    logger = get_logger("BlendPro.CodeExec")
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"Code execution {status}", 
                code_length=code_length, 
                execution_time_ms=round(execution_time * 1000, 2))

def log_scene_analysis(object_count: int, analysis_time: float):
    """Log scene analysis details"""
    logger = get_logger("BlendPro.Scene")
    logger.info("Scene analysis completed", 
                object_count=object_count, 
                analysis_time_ms=round(analysis_time * 1000, 2))

def log_error_with_context(error: Exception, context: Dict[str, Any], operation: str):
    """Log error with detailed context"""
    logger = get_logger("BlendPro.Error")
    logger.error(f"Error during {operation}: {str(error)}", 
                 error_type=type(error).__name__, 
                 **context)

# Module-level convenience functions
debug = lambda msg, **kwargs: get_logger().debug(msg, **kwargs)
info = lambda msg, **kwargs: get_logger().info(msg, **kwargs)
warning = lambda msg, **kwargs: get_logger().warning(msg, **kwargs)
error = lambda msg, **kwargs: get_logger().error(msg, **kwargs)
critical = lambda msg, **kwargs: get_logger().critical(msg, **kwargs)
exception = lambda msg, **kwargs: get_logger().exception(msg, **kwargs)
