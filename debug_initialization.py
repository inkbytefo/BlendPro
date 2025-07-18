"""
Debug script for BlendPro initialization issues
Run this in Blender's Text Editor to diagnose AI configuration problems
"""

import bpy
import sys
import traceback
from pathlib import Path

def debug_blendpro_initialization():
    """Debug BlendPro initialization step by step"""
    
    print("=" * 60)
    print("BlendPro AI Configuration Debug")
    print("=" * 60)
    
    # Step 1: Check if addon is enabled
    addon_name = "BlendProV2"
    if addon_name in bpy.context.preferences.addons:
        print(f"✓ {addon_name} addon is enabled")
        addon = bpy.context.preferences.addons[addon_name]
        prefs = addon.preferences
        print(f"✓ Addon preferences accessible")
    else:
        print(f"✗ {addon_name} addon is not enabled")
        return False
    
    # Step 2: Check lib directory and dependencies
    try:
        addon_dir = Path(__file__).parent
        lib_dir = addon_dir / "lib"
        
        if lib_dir.exists():
            lib_path_str = str(lib_dir)
            if lib_path_str not in sys.path:
                sys.path.insert(0, lib_path_str)
                print(f"✓ Added lib directory: {lib_path_str}")
            else:
                print(f"✓ Lib directory already in path: {lib_path_str}")
        else:
            print(f"✗ Lib directory not found: {lib_dir}")
            return False
            
        # Test critical imports
        import openai
        print(f"✓ OpenAI library: {openai.__version__}")
        
    except Exception as e:
        print(f"✗ Dependency import failed: {e}")
        traceback.print_exc()
        return False
    
    # Step 3: Check BlendPro modules
    try:
        from BlendProV2.config.settings import get_settings
        settings = get_settings()
        print("✓ Settings module loaded")
        
        from BlendProV2.utils.api_client import get_api_client
        print("✓ API client module loaded")
        
    except Exception as e:
        print(f"✗ BlendPro module import failed: {e}")
        traceback.print_exc()
        return False
    
    # Step 4: Check API configuration
    try:
        print("\n--- API Configuration Check ---")
        
        # Check preferences
        api_key = getattr(prefs, 'api_key', '')
        custom_api_url = getattr(prefs, 'custom_api_url', '')
        
        print(f"API Key set: {'Yes' if api_key else 'No'}")
        print(f"API Key length: {len(api_key) if api_key else 0}")
        print(f"Custom API URL: {custom_api_url if custom_api_url else 'Default (OpenAI)'}")
        
        if not api_key:
            print("✗ No API key configured in preferences")
            print("  → Go to Edit > Preferences > Add-ons > BlendPro")
            print("  → Enter your OpenAI API key")
            return False
        else:
            print("✓ API key is configured")
            
    except Exception as e:
        print(f"✗ API configuration check failed: {e}")
        traceback.print_exc()
        return False
    
    # Step 5: Test API client initialization
    try:
        print("\n--- API Client Initialization ---")
        
        # Update settings with preferences
        settings.update(
            api_key=api_key,
            base_url=custom_api_url,
            temperature=getattr(prefs, 'temperature', 0.7),
            max_tokens=getattr(prefs, 'max_tokens', 1500)
        )
        
        print("✓ Settings updated with preferences")
        
        # Try to get API client
        api_client = get_api_client()
        print("✓ API client instance created")
        
        # Test API configuration
        api_config = settings.get_api_config()
        print(f"✓ API config retrieved: model={api_config.get('model', 'unknown')}")
        
    except Exception as e:
        print(f"✗ API client initialization failed: {e}")
        traceback.print_exc()
        return False
    
    # Step 6: Test simple API call (optional)
    try:
        print("\n--- API Connection Test ---")
        print("Testing connection to OpenAI API...")
        
        from BlendProV2.utils.api_client import APIRequest
        
        # Get test model from settings
        from BlendProV2.config.models import get_test_model
        test_model = get_test_model()

        test_request = APIRequest(
            messages=[{"role": "user", "content": "Hello, this is a test. Please respond with 'API connection successful'."}],
            model=test_model,
            temperature=0.1,
            max_tokens=50
        )
        
        response = api_client.make_request(test_request)
        
        if response.error:
            print(f"✗ API test failed: {response.error}")
            return False
        else:
            print(f"✓ API test successful: {response.content[:100]}...")
            
    except Exception as e:
        print(f"✗ API connection test failed: {e}")
        traceback.print_exc()
        print("  → This might be due to invalid API key or network issues")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All checks passed! BlendPro AI is properly initialized.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    debug_blendpro_initialization()
