"""
Quick test script to verify plan execution fix
"""

import bpy
import json
from core.interaction_engine import get_interaction_engine, BLENDPRO_OT_ApprovePlan
from core.multi_step_planner import get_multi_step_planner
from utils.logger import get_logger, setup_logging

def test_plan_id_conversion():
    """Test plan ID conversion from Blender property to string"""
    
    setup_logging("DEBUG")
    logger = get_logger("BlendPro.PlanIDTest")
    
    print("=== Testing Plan ID Conversion ===")
    
    # Create a test operator instance
    op = BLENDPRO_OT_ApprovePlan()
    
    # Set properties as they would be set by UI
    test_plan_id = "plan_6d765ac7"  # This is the available plan from the error
    test_steps = [{"step_number": 1, "description": "Test step"}]
    
    op.plan_id = test_plan_id
    op.plan_steps_json = json.dumps(test_steps)
    
    print(f"Original plan_id: {op.plan_id}")
    print(f"Type of plan_id: {type(op.plan_id)}")
    
    # Test string conversion
    plan_id_str = str(op.plan_id)
    plan_steps_str = str(op.plan_steps_json)
    
    print(f"Converted plan_id: '{plan_id_str}'")
    print(f"Type of converted plan_id: {type(plan_id_str)}")
    print(f"Plan steps length: {len(plan_steps_str)}")
    
    # Check if the plan exists in the planner
    planner = get_multi_step_planner()
    available_plans = list(planner._active_plans.keys())
    print(f"Available plans: {available_plans}")
    
    if plan_id_str in available_plans:
        print("✓ Plan ID found in available plans")
        return True
    else:
        print("✗ Plan ID not found in available plans")
        return False

def create_test_plan():
    """Create a test plan to work with"""
    
    print("=== Creating Test Plan ===")
    
    engine = get_interaction_engine()
    planner = get_multi_step_planner()
    
    # Create a simple plan
    test_task = "Create a cube and move it up by 2 units"
    plan = planner.create_plan(test_task)
    
    # Store the plan with a known ID
    import uuid
    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
    planner.store_plan(plan, plan_id)
    
    print(f"Created plan with ID: {plan_id}")
    print(f"Plan has {len(plan.steps)} steps")
    
    return plan_id

def test_full_execution():
    """Test the full plan execution process"""
    
    print("=== Testing Full Plan Execution ===")
    
    # Create a test plan
    plan_id = create_test_plan()
    
    # Create operator and set properties
    op = BLENDPRO_OT_ApprovePlan()
    op.plan_id = plan_id
    op.plan_steps_json = json.dumps([{"step_number": 1, "description": "Test"}])
    
    # Test the conversion that happens in execute method
    converted_plan_id = str(op.plan_id)
    print(f"Original plan_id: {plan_id}")
    print(f"Converted plan_id: {converted_plan_id}")
    print(f"IDs match: {plan_id == converted_plan_id}")
    
    # Test plan retrieval
    engine = get_interaction_engine()
    result = engine.execute_plan(converted_plan_id)
    
    if result.get('error'):
        print(f"✗ Plan execution failed: {result['error']}")
        return False
    else:
        print("✓ Plan execution successful")
        print(f"Generated code length: {len(result.get('code', ''))}")
        return True

if __name__ == "__main__":
    print("=== BlendPro Plan Fix Test ===")
    
    try:
        # Test 1: Plan ID conversion
        print("\n1. Testing plan ID conversion...")
        if test_plan_id_conversion():
            print("✓ Plan ID conversion working")
        else:
            print("✗ Plan ID conversion failed")
        
        # Test 2: Full execution
        print("\n2. Testing full execution...")
        if test_full_execution():
            print("✓ Full execution working")
        else:
            print("✗ Full execution failed")
            
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Test Complete ===")
