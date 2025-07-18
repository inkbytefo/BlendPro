"""
Debug script for plan execution issues
This script helps diagnose the "plan.data" error in BlendPro
"""

import bpy
import json
from core.interaction_engine import get_interaction_engine
from core.multi_step_planner import get_multi_step_planner
from utils.logger import get_logger, setup_logging

def debug_plan_system():
    """Debug the plan execution system"""
    
    # Setup logging
    setup_logging("DEBUG")
    logger = get_logger("BlendPro.Debug")
    
    logger.info("Starting plan system debug...")
    
    # Get engine and planner
    engine = get_interaction_engine()
    planner = get_multi_step_planner()
    
    # Test plan creation
    test_task = "Create a cube and move it up by 2 units"
    logger.info(f"Creating plan for task: {test_task}")
    
    try:
        plan = planner.create_plan(test_task)
        logger.info(f"Plan created successfully with {len(plan.steps)} steps")
        
        # Generate plan ID and store
        import time
        plan_id = f"plan_{int(time.time())}"
        planner.store_plan(plan, plan_id)
        logger.info(f"Plan stored with ID: {plan_id}")
        
        # Check if plan can be retrieved
        retrieved_plan = planner.get_plan(plan_id)
        if retrieved_plan:
            logger.info("Plan retrieved successfully")
        else:
            logger.error("Failed to retrieve stored plan")
            return False
        
        # List all active plans
        active_plans = list(planner._active_plans.keys())
        logger.info(f"Active plans: {active_plans}")
        
        # Test plan execution
        logger.info("Testing plan execution...")
        result = engine.execute_plan(plan_id)
        
        if result.get('error'):
            logger.error(f"Plan execution failed: {result['error']}")
            return False
        else:
            logger.info("Plan execution successful")
            logger.info(f"Generated code length: {len(result.get('code', ''))}")
            return True
            
    except Exception as e:
        logger.exception(f"Error during plan debug: {str(e)}")
        return False

def debug_ui_plan_data():
    """Debug UI plan data handling"""
    
    logger = get_logger("BlendPro.UIDebug")
    
    # Check chat history for plan messages
    if hasattr(bpy.context.scene, 'blendpro_chat_history'):
        chat_history = bpy.context.scene.blendpro_chat_history
        logger.info(f"Found {len(chat_history)} messages in chat history")
        
        plan_messages = []
        for i, message in enumerate(chat_history):
            if hasattr(message, 'is_interactive') and message.is_interactive:
                plan_messages.append(i)
                logger.info(f"Message {i}: Interactive message found")
                
                if hasattr(message, 'plan_data'):
                    try:
                        plan_data = json.loads(message.plan_data)
                        logger.info(f"  - Plan data: {len(plan_data)} steps")
                    except json.JSONDecodeError as e:
                        logger.error(f"  - Invalid plan data: {e}")
                
                if hasattr(message, 'plan_id'):
                    logger.info(f"  - Plan ID: {message.plan_id}")
                else:
                    logger.warning("  - No plan ID found")
        
        logger.info(f"Found {len(plan_messages)} plan messages")
        return len(plan_messages) > 0
    else:
        logger.error("No chat history found")
        return False

def test_plan_approval_operator():
    """Test the plan approval operator directly"""

    logger = get_logger("BlendPro.OperatorTest")

    # Create a test plan
    test_steps = [
        {
            "step_number": 1,
            "description": "Create a cube",
            "action_type": "create",
            "expected_outcome": "Cube created in scene"
        }
    ]

    plan_steps_json = json.dumps(test_steps)
    plan_id = f"test_plan_{int(time.time())}"

    logger.info(f"Testing with plan_id: {plan_id}")
    logger.info(f"Plan steps JSON: {plan_steps_json}")

    # Test the operator properties
    try:
        # This simulates what happens when the operator is called
        from core.interaction_engine import BLENDPRO_OT_ApprovePlan

        # Create operator instance (this is just for testing)
        op = BLENDPRO_OT_ApprovePlan()
        op.plan_steps_json = plan_steps_json
        op.plan_id = plan_id

        logger.info("Operator properties set successfully")
        logger.info(f"  - plan_steps_json length: {len(op.plan_steps_json)}")
        logger.info(f"  - plan_id: {op.plan_id}")

        # Test string conversion (this is what happens in execute method)
        plan_id_str = str(op.plan_id)
        plan_steps_str = str(op.plan_steps_json)

        logger.info("String conversion test:")
        logger.info(f"  - plan_id_str: {plan_id_str}")
        logger.info(f"  - plan_steps_str length: {len(plan_steps_str)}")

        # Test JSON parsing
        parsed_steps = json.loads(plan_steps_str)
        logger.info(f"  - parsed steps: {len(parsed_steps)} steps")

        return True

    except Exception as e:
        logger.exception(f"Error testing operator: {str(e)}")
        return False

def test_json_serialization():
    """Test JSON serialization of plan data"""

    logger = get_logger("BlendPro.JSONTest")

    # Test plan data serialization
    test_plan_data = [
        {
            "step_number": 1,
            "description": "Create a cube",
            "action_type": "create",
            "expected_outcome": "Cube created in scene"
        }
    ]

    try:
        # Test JSON serialization
        json_str = json.dumps(test_plan_data)
        logger.info(f"JSON serialization successful: {len(json_str)} characters")

        # Test JSON deserialization
        parsed_data = json.loads(json_str)
        logger.info(f"JSON deserialization successful: {len(parsed_data)} steps")

        return True

    except Exception as e:
        logger.exception(f"JSON serialization test failed: {str(e)}")
        return False

def test_property_conversion():
    """Test Blender property to string conversion"""

    logger = get_logger("BlendPro.PropertyTest")

    try:
        # Create a test message
        if hasattr(bpy.context.scene, 'blendpro_chat_history'):
            test_message = bpy.context.scene.blendpro_chat_history.add()
            test_message.type = 'assistant'
            test_message.content = 'Test message'
            test_message.is_interactive = True
            test_message.plan_data = json.dumps([{"test": "data"}])
            test_message.plan_id = "test_plan_123"

            # Test string conversion
            plan_data_str = str(test_message.plan_data)
            plan_id_str = str(test_message.plan_id)

            logger.info(f"Property conversion successful")
            logger.info(f"  - plan_data: {len(plan_data_str)} characters")
            logger.info(f"  - plan_id: {plan_id_str}")

            # Test JSON parsing
            parsed_plan = json.loads(plan_data_str)
            logger.info(f"  - parsed plan: {parsed_plan}")

            # Clean up
            bpy.context.scene.blendpro_chat_history.remove(len(bpy.context.scene.blendpro_chat_history) - 1)

            return True
        else:
            logger.error("No chat history property found")
            return False

    except Exception as e:
        logger.exception(f"Property conversion test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== BlendPro Plan System Debug ===")

    print("\n1. Testing JSON serialization...")
    if test_json_serialization():
        print("✓ JSON serialization working correctly")
    else:
        print("✗ JSON serialization has issues")

    print("\n2. Testing property conversion...")
    if test_property_conversion():
        print("✓ Property conversion working correctly")
    else:
        print("✗ Property conversion has issues")

    print("\n3. Testing plan system...")
    if debug_plan_system():
        print("✓ Plan system working correctly")
    else:
        print("✗ Plan system has issues")

    print("\n4. Testing UI plan data...")
    if debug_ui_plan_data():
        print("✓ UI plan data found")
    else:
        print("✗ No UI plan data found")

    print("\n5. Testing plan approval operator...")
    if test_plan_approval_operator():
        print("✓ Plan approval operator working")
    else:
        print("✗ Plan approval operator has issues")

    print("\n=== Debug Complete ===")
