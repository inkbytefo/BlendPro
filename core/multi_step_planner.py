"""
Multi-Step Planner for BlendPro: AI Co-Pilot
Breaks down complex tasks into manageable steps
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..config.prompts import get_system_prompt, PromptType
from ..config.settings import get_settings
from ..utils.api_client import get_api_client, APIRequest
from ..utils.logger import get_logger

class ActionType(Enum):
    """Types of actions in a plan step"""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    ANALYZE = "analyze"
    VERIFY = "verify"

@dataclass
class PlanStep:
    """Represents a single step in a multi-step plan"""
    step_number: int
    description: str
    action_type: ActionType
    expected_outcome: str
    prerequisites: List[str]
    potential_issues: List[str]
    code_template: Optional[str] = None
    estimated_time: Optional[int] = None  # in seconds

@dataclass
class ExecutionPlan:
    """Represents a complete execution plan"""
    task_analysis: str
    estimated_steps: int
    steps: List[PlanStep]
    plan_summary: str
    total_estimated_time: int
    complexity_score: float  # 0-1, where 1 is most complex

class MultiStepPlanner:
    """Plans and manages multi-step task execution"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("BlendPro.Planner")
        self.api_client = get_api_client()
        self._active_plans: Dict[str, ExecutionPlan] = {}
        self._execution_history: List[Dict[str, Any]] = []
    
    def create_plan(
        self, 
        user_task: str, 
        scene_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """Create a multi-step plan for a complex task"""
        
        try:
            # Prepare context
            context = scene_context or {}
            
            # Get planning prompt
            system_prompt = get_system_prompt(
                PromptType.MULTI_STEP_PLANNER,
                user_task=user_task,
                scene_context=json.dumps(context, indent=2)
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a step-by-step plan for: {user_task}"}
            ]
            
            # Get appropriate model for planning
            api_config = self.settings.get_api_config("code")

            request = APIRequest(
                messages=messages,
                model=api_config["model"],
                temperature=0.3,
                max_tokens=1500
            )
            
            response = self.api_client.make_request(request)
            
            if response.error:
                return self._create_fallback_plan(user_task, context)
            
            # Parse the JSON response
            try:
                plan_data = json.loads(response.content)
                return self._parse_plan_response(plan_data, user_task)
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing plan response: {e}")
                return self._create_fallback_plan(user_task, context)
                
        except Exception as e:
            print(f"Error creating plan: {e}")
            return self._create_fallback_plan(user_task, context)
    
    def _parse_plan_response(self, plan_data: Dict[str, Any], user_task: str) -> ExecutionPlan:
        """Parse AI response into ExecutionPlan"""
        
        steps = []
        for step_data in plan_data.get("steps", []):
            try:
                step = PlanStep(
                    step_number=step_data.get("step_number", 1),
                    description=step_data.get("description", ""),
                    action_type=ActionType(step_data.get("action_type", "create")),
                    expected_outcome=step_data.get("expected_outcome", ""),
                    prerequisites=step_data.get("prerequisites", []),
                    potential_issues=step_data.get("potential_issues", []),
                    estimated_time=step_data.get("estimated_time", 30)
                )
                steps.append(step)
            except (ValueError, KeyError) as e:
                print(f"Error parsing step: {e}")
                continue
        
        total_time = sum(step.estimated_time or 30 for step in steps)
        complexity_score = min(len(steps) / 10.0, 1.0)  # Simple complexity calculation
        
        return ExecutionPlan(
            task_analysis=plan_data.get("task_analysis", f"Analysis for: {user_task}"),
            estimated_steps=len(steps),
            steps=steps,
            plan_summary=plan_data.get("plan_summary", f"Plan for: {user_task}"),
            total_estimated_time=total_time,
            complexity_score=complexity_score
        )
    
    def _create_fallback_plan(self, user_task: str, context: Dict[str, Any]) -> ExecutionPlan:
        """Create a simple fallback plan when AI planning fails"""
        
        # Simple task breakdown based on keywords
        user_task_lower = user_task.lower()
        steps = []
        
        if "create" in user_task_lower or "make" in user_task_lower:
            steps.append(PlanStep(
                step_number=1,
                description=f"Create the requested object/structure",
                action_type=ActionType.CREATE,
                expected_outcome="Object created in scene",
                prerequisites=[],
                potential_issues=["Object might overlap with existing objects"]
            ))
        
        if "material" in user_task_lower or "color" in user_task_lower:
            steps.append(PlanStep(
                step_number=len(steps) + 1,
                description="Apply materials and colors",
                action_type=ActionType.MODIFY,
                expected_outcome="Objects have proper materials",
                prerequisites=["Objects must exist"],
                potential_issues=["Material nodes might be complex"]
            ))
        
        if "light" in user_task_lower:
            steps.append(PlanStep(
                step_number=len(steps) + 1,
                description="Set up lighting",
                action_type=ActionType.CREATE,
                expected_outcome="Scene is properly lit",
                prerequisites=["Objects must exist"],
                potential_issues=["Lighting might be too bright or too dark"]
            ))
        
        # Default step if no specific keywords found
        if not steps:
            steps.append(PlanStep(
                step_number=1,
                description=f"Execute task: {user_task}",
                action_type=ActionType.CREATE,
                expected_outcome="Task completed",
                prerequisites=[],
                potential_issues=["Task might be complex"]
            ))
        
        return ExecutionPlan(
            task_analysis=f"Simple breakdown of: {user_task}",
            estimated_steps=len(steps),
            steps=steps,
            plan_summary=f"Fallback plan for: {user_task}",
            total_estimated_time=len(steps) * 60,  # 1 minute per step
            complexity_score=0.5
        )
    
    def should_use_multi_step(self, user_task: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if a task should use multi-step planning"""
        
        user_task_lower = user_task.lower()
        
        # Keywords that suggest complexity
        complex_keywords = [
            "room", "house", "building", "scene", "environment",
            "multiple", "several", "many", "all", "entire",
            "complete", "full", "detailed", "complex",
            "and", "then", "after", "before", "with"
        ]
        
        # Count complex indicators
        complexity_score = sum(1 for keyword in complex_keywords if keyword in user_task_lower)
        
        # Check for multiple actions
        action_words = ["create", "make", "add", "place", "set", "apply", "render"]
        action_count = sum(1 for action in action_words if action in user_task_lower)
        
        # Check sentence length (longer sentences often indicate complexity)
        word_count = len(user_task.split())
        
        # Decision logic
        return (
            complexity_score >= 2 or
            action_count >= 2 or
            word_count >= 15 or
            " and " in user_task_lower
        )
    
    def store_plan(self, plan: ExecutionPlan, plan_id: str) -> None:
        """Store a plan for later execution"""
        self._active_plans[plan_id] = plan
    
    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Retrieve a stored plan"""
        return self._active_plans.get(plan_id)
    
    def execute_plan_step(
        self, 
        plan: ExecutionPlan, 
        step_number: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a specific step of a plan"""
        
        if step_number < 1 or step_number > len(plan.steps):
            return {"success": False, "error": "Invalid step number"}
        
        step = plan.steps[step_number - 1]
        
        # Check prerequisites
        for prerequisite in step.prerequisites:
            # In a full implementation, you'd check if prerequisites are met
            pass
        
        # Generate code for this step
        from ..config.prompts import get_system_prompt, PromptType
        
        code_prompt = get_system_prompt(
            PromptType.CODE_GENERATOR,
            task_description=step.description,
            scene_context=json.dumps(context or {}, indent=2),
            requirements=f"Expected outcome: {step.expected_outcome}"
        )
        
        messages = [
            {"role": "system", "content": code_prompt},
            {"role": "user", "content": f"Generate code for step {step_number}: {step.description}"}
        ]
        
        # Get appropriate model for code generation
        api_config = self.settings.get_api_config("code")

        request = APIRequest(
            messages=messages,
            model=api_config["model"],
            temperature=0.3,
            max_tokens=800
        )
        
        response = self.api_client.make_request(request)
        
        if response.error:
            return {"success": False, "error": response.error}
        
        return {
            "success": True,
            "code": response.content,
            "step": step,
            "step_number": step_number
        }
    
    def generate_plan_preview(self, plan: ExecutionPlan) -> str:
        """Generate a human-readable preview of the plan"""

        preview = f"📋 Plan Summary: {plan.plan_summary}\n\n"
        preview += f"🔍 Analysis: {plan.task_analysis}\n\n"
        preview += f"⏱️ Estimated Time: {plan.total_estimated_time // 60} minutes\n"
        preview += f"📊 Complexity: {'●' * int(plan.complexity_score * 5)}{'○' * (5 - int(plan.complexity_score * 5))}\n\n"
        preview += "Steps:\n"

        for step in plan.steps:
            preview += f"{step.step_number}. {step.description}\n"
            preview += f"   - Expected: {step.expected_outcome}\n"
            if step.prerequisites:
                preview += f"   - Requires: {', '.join(step.prerequisites)}\n"
            if step.potential_issues:
                preview += f"   - Watch for: {', '.join(step.potential_issues)}\n"
            preview += "\n"

        preview += "Please review and approve this plan to proceed."

        return preview
    
    def clear_active_plans(self) -> None:
        """Clear all active plans"""
        self._active_plans.clear()
    
    def get_plan_stats(self) -> Dict[str, Any]:
        """Get planning statistics"""
        return {
            "active_plans": len(self._active_plans),
            "total_executions": len(self._execution_history)
        }

# Global multi-step planner instance
_multi_step_planner: Optional[MultiStepPlanner] = None

def get_multi_step_planner() -> MultiStepPlanner:
    """Get global multi-step planner instance"""
    global _multi_step_planner
    if _multi_step_planner is None:
        _multi_step_planner = MultiStepPlanner()
    return _multi_step_planner
