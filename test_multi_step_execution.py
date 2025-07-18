"""
Test script for multi-step execution feature
Tests the new step-by-step plan execution system
"""

import bpy
import json
from core.interaction_engine import get_interaction_engine
from core.multi_step_planner import get_multi_step_planner
from utils.logger import get_logger, setup_logging

def test_multi_step_execution():
    """Test the new multi-step execution system"""
    
    # Setup logging
    setup_logging("DEBUG")
    logger = get_logger("BlendPro.MultiStepTest")
    
    logger.info("=== Testing Multi-Step Execution ===")
    
    # Get engine and planner
    engine = get_interaction_engine()
    planner = get_multi_step_planner()
    
    # Create a test plan
    test_task = "Create a cube, scale it to 2x, move it up by 3 units, and add a material"
    logger.info(f"Creating plan for task: {test_task}")
    
    try:
        # Create plan
        plan = planner.create_plan(test_task)
        logger.info(f"Plan created with {len(plan.steps)} steps")
        
        # Store plan
        import uuid
        plan_id = f"test_plan_{uuid.uuid4().hex[:8]}"
        planner.store_plan(plan, plan_id)
        logger.info(f"Plan stored with ID: {plan_id}")
        
        # Test step-by-step execution
        for step_num in range(1, len(plan.steps) + 1):
            logger.info(f"\n--- Testing Step {step_num} ---")
            
            # Execute single step
            result = engine.execute_plan(plan_id, step_number=step_num)
            
            if result.get('error'):
                logger.error(f"Step {step_num} failed: {result['error']}")
                return False
            
            # Check result structure
            logger.info(f"Step {step_num} result:")
            logger.info(f"  - Current step: {result.get('current_step')}")
            logger.info(f"  - Total steps: {result.get('total_steps')}")
            logger.info(f"  - Has next step: {result.get('has_next_step')}")
            logger.info(f"  - Step description: {result.get('step_description')}")
            logger.info(f"  - Code length: {len(result.get('code', ''))}")
            
            if result.get('has_next_step'):
                next_step = result.get('next_step', {})
                logger.info(f"  - Next step: {next_step.get('description', 'Unknown')}")
            else:
                logger.info("  - This is the final step")
        
        logger.info("\n✓ Multi-step execution test completed successfully")
        return True
        
    except Exception as e:
        logger.exception(f"Multi-step execution test failed: {str(e)}")
        return False

def test_ui_integration():
    """Test UI integration for multi-step execution"""
    
    logger = get_logger("BlendPro.UITest")
    logger.info("=== Testing UI Integration ===")
    
    try:
        # Create a test message with next step info
        if hasattr(bpy.context.scene, 'blendpro_chat_history'):
            test_message = bpy.context.scene.blendpro_chat_history.add()
            test_message.type = 'assistant'
            test_message.content = 'Step 1 completed: Cube created'
            test_message.is_interactive = True
            test_message.interaction_type = "next_step"
            test_message.plan_id = "test_plan_123"
            test_message.next_step_number = 2
            test_message.next_step_info = json.dumps({
                "description": "Scale cube to 2x size",
                "expected_outcome": "Cube will be scaled to double size"
            })
            
            logger.info("✓ Test message created successfully")
            logger.info(f"  - Interaction type: {test_message.interaction_type}")
            logger.info(f"  - Next step number: {test_message.next_step_number}")
            logger.info(f"  - Next step info: {test_message.next_step_info}")
            
            return True
        else:
            logger.error("Chat history not available")
            return False
            
    except Exception as e:
        logger.exception(f"UI integration test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all multi-step execution tests"""
    
    print("BlendPro Multi-Step Execution Tests")
    print("=" * 40)
    
    tests = [
        ("Multi-Step Execution", test_multi_step_execution),
        ("UI Integration", test_ui_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"✓ {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"✗ {test_name}: ERROR - {str(e)}")
    
    # Summary
    print(f"\n{'='*40}")
    print("Test Results Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed. Check the logs for details.")

if __name__ == "__main__":
    run_all_tests()
