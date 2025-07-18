"""
API Client for BlendPro: AI Co-Pilot
Centralized API communication with OpenAI and other providers
"""

import json
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from ..config.settings import get_settings
from ..config.models import get_model_config
from .dependency_loader import require_package, DependencyError
from .logger import get_logger, log_api_request, log_error_with_context

# Import OpenAI with dependency management
try:
    openai_module = require_package('openai', 'OpenAI API Client', min_version='1.0.0')
    OpenAI = openai_module.OpenAI
except DependencyError as e:
    raise ImportError(f"BlendPro requires OpenAI library: {e}") from e

class APIError(Exception):
    """Custom exception for API-related errors"""

    def __init__(self, message: str, error_code: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

    def __str__(self) -> str:
        if self.error_code:
            return f"API Error [{self.error_code}]: {self.message}"
        return f"API Error: {self.message}"

@dataclass
class APIRequest:
    """Represents an API request"""
    messages: List[Dict[str, Any]]
    model: str
    temperature: float = 0.7
    max_tokens: int = 1500
    top_p: float = 1.0
    stream: bool = False
    timeout: int = 60

@dataclass 
class APIResponse:
    """Represents an API response"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    error: Optional[str] = None

class APIClient:
    """Centralized API client for all AI model interactions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("BlendPro.API")
        self._clients: Dict[str, OpenAI] = {}
        self._request_cache: Dict[str, APIResponse] = {}
        self._rate_limiter = threading.Semaphore(self.settings.max_concurrent_requests)

        # Verify OpenAI dependency is available
        if not OpenAI:
            raise APIError("OpenAI library is not available. Please install it to use BlendPro.")
    
    def _get_client(self, api_key: str, base_url: str) -> OpenAI:
        """Get or create OpenAI client for given configuration"""
        client_key = f"{api_key[:10]}_{base_url}"
        
        if client_key not in self._clients:
            self._clients[client_key] = OpenAI(
                api_key=api_key,
                base_url=base_url if base_url else None
            )
        
        return self._clients[client_key]
    
    def _generate_cache_key(self, request: APIRequest) -> str:
        """Generate cache key for request"""
        if not self.settings.enable_caching:
            return ""
        
        # Create hash of request parameters
        import hashlib
        request_str = json.dumps({
            "messages": request.messages,
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p
        }, sort_keys=True)
        
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid"""
        if not cache_key or cache_key not in self._request_cache:
            return False
        
        # Simple time-based cache validation
        # In a real implementation, you'd store timestamps
        return True  # Simplified for now
    
    def make_request(self, request: APIRequest, use_vision: bool = False) -> APIResponse:
        """Make API request with error handling and caching"""
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        if cache_key and self._is_cache_valid(cache_key):
            return self._request_cache[cache_key]
        
        # Rate limiting
        with self._rate_limiter:
            try:
                # Get appropriate API configuration
                if use_vision:
                    api_config = self.settings.get_vision_api_config()
                else:
                    api_config = self.settings.get_api_config()
                
                # Validate configuration
                if not api_config["api_key"]:
                    raise APIError("No API key configured")
                
                # Get client
                client = self._get_client(api_config["api_key"], api_config["base_url"])
                
                # Use model from request or fallback to config
                model = request.model or api_config["model"]

                start_time = time.time()
                self.logger.debug("Making API request",
                                model=model,
                                message_count=len(request.messages),
                                temperature=request.temperature,
                                max_tokens=request.max_tokens)

                # Make the request
                response = client.chat.completions.create(
                    model=model,
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_p=request.top_p,
                    stream=request.stream,
                    timeout=request.timeout
                )
                
                # Process response
                if request.stream:
                    # Handle streaming response
                    content = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            content += chunk.choices[0].delta.content
                    
                    api_response = APIResponse(
                        content=content,
                        model=model,
                        usage={"total_tokens": 0},  # Streaming doesn't provide usage
                        finish_reason="stop"
                    )
                else:
                    # Handle regular response
                    api_response = APIResponse(
                        content=response.choices[0].message.content,
                        model=response.model,
                        usage=response.usage.model_dump() if response.usage else {},
                        finish_reason=response.choices[0].finish_reason
                    )
                
                # Log successful request
                duration = time.time() - start_time
                tokens_used = api_response.usage.get("total_tokens", 0)
                log_api_request("chat/completions", model, tokens_used, duration)

                # Cache successful response
                if cache_key:
                    self._request_cache[cache_key] = api_response

                return api_response
                
            except Exception as e:
                error_msg = str(e)

                # Log the error with context
                log_error_with_context(e, {
                    "model": model,
                    "message_count": len(request.messages),
                    "use_vision": use_vision
                }, "API request")

                # Categorize common errors
                if "timeout" in error_msg.lower():
                    error_msg = "Request timed out. Please try again."
                elif "rate limit" in error_msg.lower():
                    error_msg = "API rate limit exceeded. Please wait and try again."
                elif "connection" in error_msg.lower():
                    error_msg = "Connection error. Please check your internet connection."
                elif "authentication" in error_msg.lower():
                    error_msg = "Authentication failed. Please check your API key."
                elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                    error_msg = f"Model '{model}' not found. Please check your model configuration."

                return APIResponse(
                    content="",
                    model=model,
                    usage={},
                    finish_reason="error",
                    error=error_msg
                )
    
    def test_connection(self, model: str = None, use_vision: bool = False) -> Dict[str, Any]:
        """Test API connection with a simple request"""
        try:
            # Get test API config if no model specified
            if not model:
                test_config = self.settings.get_test_api_config(use_vision)
                model = test_config["model"]

            test_request = APIRequest(
                messages=[{"role": "user", "content": "Hello, please respond with 'Connection successful!'"}],
                model=model,
                max_tokens=50,
                timeout=10
            )
            
            response = self.make_request(test_request, use_vision=use_vision)
            
            if response.error:
                return {"success": False, "error": response.error}
            
            return {
                "success": True,
                "content": response.content,
                "model": response.model,
                "usage": response.usage
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def clear_cache(self) -> None:
        """Clear the request cache"""
        self._request_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "cached_requests": len(self._request_cache),
            "cache_enabled": self.settings.enable_caching
        }

# Global API client instance
_api_client: Optional[APIClient] = None

def get_api_client() -> APIClient:
    """Get global API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client
