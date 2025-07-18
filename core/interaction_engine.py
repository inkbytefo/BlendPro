"""
Interaction Engine for BlendPro: AI Co-Pilot
Main orchestrator for AI interactions and task processing
"""

import json
import threading
from typing import Dict, Any, Optional, List
import bpy

from ..config.settings import get_settings
from ..config.prompts import get_system_prompt, PromptType
from ..utils.api_client import get_api_client, APIRequest
from ..utils.logger import get_logger
from ..utils.code_executor import get_code_executor
from ..utils.backup_manager import get_backup_manager
from ..utils.file_manager import get_file_manager
from ..utils.input_validator import get_input_validator, ValidationSeverity

from .task_classifier import get_task_classifier, TaskType
from .clarification_system import get_clarification_system
from .multi_step_planner import get_multi_step_planner
from .conversation_memory import get_conversation_memory

class InteractionEngine:
    """Main engine for processing user interactions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("BlendPro.Engine")
        self.api_client = get_api_client()
        self.code_executor = get_code_executor()
        self.backup_manager = get_backup_manager()
        self.file_manager = get_file_manager()
        
        self.task_classifier = get_task_classifier()
        self.clarification_system = get_clarification_system()
        self.multi_step_planner = get_multi_step_planner()
        self.conversation_memory = get_conversation_memory()
        self.input_validator = get_input_validator()

        self._processing = False
        self._current_session_id = None
    
    def process_user_input(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Main entry point for processing user input"""

        if self._processing:
            return {"error": "Already processing a request. Please wait..."}

        # Validate user input first
        validation_result = self.input_validator.validate_user_input(user_input)
        if not validation_result.is_valid:
            self.logger.warning("Invalid user input",
                              message=validation_result.message,
                              severity=validation_result.severity.value)
            return {"error": f"Invalid input: {validation_result.message}"}

        # Use sanitized input if available
        if validation_result.sanitized_input:
            user_input = validation_result.sanitized_input

        # Log validation warnings
        if validation_result.severity == ValidationSeverity.WARNING:
            self.logger.warning("Input validation warning",
                              validation_message=validation_result.message,
                              issues=validation_result.issues)

        self._processing = True

        try:
            # Get scene context if not provided
            if context is None:
                context = self._get_scene_context()
            
            # Resolve pronouns and vague references
            resolved_input = self.conversation_memory.resolve_pronouns(user_input, context)
            
            # Classify the task
            classification = self.task_classifier.classify(resolved_input, context)
            
            # Route based on classification
            if classification.task_type == TaskType.QUESTION:
                result = self._handle_question(resolved_input, context, classification)
            elif classification.task_type == TaskType.CLARIFICATION_NEEDED:
                result = self._handle_clarification_needed(resolved_input, context, classification)
            else:  # TaskType.TASK
                result = self._handle_task(resolved_input, context, classification)
            
            # Add to conversation memory
            self.conversation_memory.add_turn(
                user_input=user_input,
                assistant_response=result.get("content", ""),
                turn_type=result.get("type", "normal"),
                context=context
            )
            
            return result
            
        except Exception as e:
            return {"error": f"Processing error: {str(e)}"}
        finally:
            self._processing = False
    
    def _handle_question(
        self, 
        user_input: str, 
        context: Dict[str, Any],
        classification
    ) -> Dict[str, Any]:
        """Handle question-type inputs"""
        
        # Build context-aware prompt
        system_prompt = get_system_prompt(PromptType.MAIN_ASSISTANT)
        
        # Add conversation context
        conversation_context = self.conversation_memory.build_context_summary()
        
        # Add scene context
        scene_summary = self._build_scene_summary(context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
Context Information:
{conversation_context}

Scene Information:
{scene_summary}

User Question: {user_input}

Please provide a helpful answer based on the current scene and conversation context.
"""}
        ]
        
        # Get API config for general tasks
        api_config = self.settings.get_api_config("general")

        request = APIRequest(
            messages=messages,
            model=api_config["model"],
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens
        )
        
        response = self.api_client.make_request(request)
        
        if response.error:
            return {"error": response.error, "type": "question"}
        
        return {
            "content": response.content,
            "type": "question",
            "classification": classification.task_type.value
        }
    
    def _handle_clarification_needed(
        self, 
        user_input: str, 
        context: Dict[str, Any],
        classification
    ) -> Dict[str, Any]:
        """Handle inputs that need clarification"""
        
        clarification_response = self.clarification_system.generate_clarification(
            user_input=user_input,
            ambiguity_reason=classification.reasoning,
            scene_context=context
        )
        
        return {
            "content": clarification_response.question,
            "type": "clarification",
            "is_question": True,
            "question": clarification_response.question,
            "classification": classification.task_type.value
        }
    
    def _handle_task(
        self, 
        user_input: str, 
        context: Dict[str, Any],
        classification
    ) -> Dict[str, Any]:
        """Handle task-type inputs"""
        
        # Check if this should be a multi-step task
        if (self.settings.enable_multi_step_planning and 
            self.multi_step_planner.should_use_multi_step(user_input, context)):
            
            return self._handle_multi_step_task(user_input, context)
        else:
            return self._handle_single_step_task(user_input, context)
    
    def _handle_single_step_task(
        self, 
        user_input: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle single-step tasks"""
        
        # Generate code directly
        system_prompt = get_system_prompt(
            PromptType.CODE_GENERATOR,
            task_description=user_input,
            scene_context=json.dumps(context, indent=2),
            requirements="Generate safe, efficient Python code for Blender"
        )
        
        # Add conversation context
        conversation_context = self.conversation_memory.build_context_summary()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
Conversation Context:
{conversation_context}

Task: {user_input}

Generate Python code to accomplish this task.
"""}
        ]
        
        # Get appropriate model for code generation
        api_config = self.settings.get_api_config("code")

        request = APIRequest(
            messages=messages,
            model=api_config["model"],
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens
        )
        
        response = self.api_client.make_request(request)
        
        if response.error:
            return {"error": response.error, "type": "task"}
        
        # Extract code from response
        code = self._extract_code_from_response(response.content)
        
        return {
            "content": code,
            "code": code,
            "type": "task",
            "is_single_step": True
        }
    
    def _handle_multi_step_task(
        self, 
        user_input: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle multi-step tasks"""
        
        # Create execution plan
        plan = self.multi_step_planner.create_plan(user_input, context)
        
        # Generate plan preview
        plan_preview = self.multi_step_planner.generate_plan_preview(plan)
        
        # Store plan for later execution
        import uuid
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        self.multi_step_planner.store_plan(plan, plan_id)

        from ..utils.logger import get_logger
        logger = get_logger("BlendPro.PlanCreation")
        logger.debug(f"Created and stored plan with ID: {plan_id}")
        
        return {
            "content": plan_preview,
            "type": "plan_preview",
            "is_plan_preview": True,
            "plan_preview": plan_preview,
            "steps": [
                {
                    "step_number": step.step_number,
                    "description": step.description,
                    "action_type": step.action_type.value,
                    "expected_outcome": step.expected_outcome
                }
                for step in plan.steps
            ],
            "plan_id": plan_id
        }
    
    def execute_plan(self, plan_id: str, context: Optional[Dict[str, Any]] = None, step_number: Optional[int] = None) -> Dict[str, Any]:
        """Execute a stored plan - either all steps or a specific step"""

        from ..utils.logger import get_logger
        logger = get_logger("BlendPro.PlanExecution")

        logger.debug(f"Attempting to execute plan with ID: {plan_id}, step: {step_number}")

        plan = self.multi_step_planner.get_plan(plan_id)
        if not plan:
            logger.error(f"Plan not found for ID: {plan_id}")
            # List available plans for debugging
            available_plans = list(self.multi_step_planner._active_plans.keys())
            logger.debug(f"Available plans: {available_plans}")
            return {"error": f"Plan not found (ID: {plan_id}). Available plans: {available_plans}"}

        logger.info(f"Found plan with {len(plan.steps)} steps")

        if context is None:
            context = self._get_scene_context()

        # If step_number is specified, execute only that step
        if step_number is not None:
            return self._execute_single_step(plan, step_number, context)

        # Otherwise, execute first step only (for multi-step workflow)
        return self._execute_single_step(plan, 1, context)

    def _execute_single_step(self, plan, step_number: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step of a plan"""

        from ..utils.logger import get_logger
        logger = get_logger("BlendPro.StepExecution")

        if step_number < 1 or step_number > len(plan.steps):
            return {"error": f"Invalid step number: {step_number}"}

        step = plan.steps[step_number - 1]
        logger.debug(f"Executing step {step.step_number}: {step.description}")

        step_result = self.multi_step_planner.execute_plan_step(
            plan, step.step_number, context
        )

        if step_result["success"]:
            logger.debug(f"Step {step.step_number} completed successfully")

            # Check if there are more steps
            has_next_step = step_number < len(plan.steps)
            next_step_info = None

            if has_next_step:
                next_step = plan.steps[step_number]  # step_number is 1-based, array is 0-based
                next_step_info = {
                    "step_number": next_step.step_number,
                    "description": next_step.description,
                    "expected_outcome": next_step.expected_outcome
                }

            return {
                "content": step_result["code"],
                "code": step_result["code"],
                "type": "multi_step_task",
                "is_multi_step": True,
                "current_step": step_number,
                "total_steps": len(plan.steps),
                "step_description": step.description,
                "step_outcome": step.expected_outcome,
                "has_next_step": has_next_step,
                "next_step": next_step_info,
                "plan_id": plan.plan_id,
                "plan_summary": plan.plan_summary
            }
        else:
            logger.error(f"Step {step.step_number} failed: {step_result['error']}")
            return {"error": f"Step {step.step_number} failed: {step_result['error']}"}

    def execute_plan_legacy(self, plan_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute all steps of a plan at once (legacy behavior)"""

        from ..utils.logger import get_logger
        logger = get_logger("BlendPro.PlanExecution")

        logger.debug(f"Attempting to execute plan with ID: {plan_id}")

        plan = self.multi_step_planner.get_plan(plan_id)
        if not plan:
            logger.error(f"Plan not found for ID: {plan_id}")
            # List available plans for debugging
            available_plans = list(self.multi_step_planner._active_plans.keys())
            logger.debug(f"Available plans: {available_plans}")
            return {"error": f"Plan not found (ID: {plan_id}). Available plans: {available_plans}"}

        logger.info(f"Found plan with {len(plan.steps)} steps")

        if context is None:
            context = self._get_scene_context()

        # Execute all steps and combine code
        combined_code = []
        execution_results = []

        for step in plan.steps:
            logger.debug(f"Executing step {step.step_number}: {step.description}")
            step_result = self.multi_step_planner.execute_plan_step(
                plan, step.step_number, context
            )

            if step_result["success"]:
                combined_code.append(f"# Step {step.step_number}: {step.description}")
                combined_code.append(step_result["code"])
                combined_code.append("")  # Empty line between steps
                execution_results.append(step_result)
                logger.debug(f"Step {step.step_number} completed successfully")
            else:
                logger.error(f"Step {step.step_number} failed: {step_result['error']}")
                return {"error": f"Step {step.step_number} failed: {step_result['error']}"}

        final_code = "\n".join(combined_code)
        logger.info(f"Plan execution completed successfully. Generated {len(final_code)} characters of code")

        return {
            "content": final_code,
            "code": final_code,
            "type": "multi_step_task",
            "is_multi_step": True,
            "steps": execution_results,
            "plan_summary": plan.plan_summary
        }
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from AI response"""
        import re
        
        # Look for code blocks
        code_pattern = r'```(?:python)?\s*(.*?)```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks found, return the whole response
        return response.strip()
    
    def _get_scene_context(self) -> Dict[str, Any]:
        """Get current scene context"""
        try:
            # Import vision system if available
            from ..vision.scene_analyzer import get_scene_analyzer
            scene_analyzer = get_scene_analyzer()
            return scene_analyzer.analyze_scene(bpy.context)
        except ImportError:
            # Fallback to basic scene info
            return self._get_basic_scene_info()
    
    def _get_basic_scene_info(self) -> Dict[str, Any]:
        """Get basic scene information without vision system"""
        scene = bpy.context.scene
        
        objects = []
        for obj in scene.objects:
            objects.append({
                "name": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "selected": obj.select_get()
            })
        
        return {
            "objects": objects,
            "active_object": scene.objects.active.name if scene.objects.active else None,
            "frame_current": scene.frame_current,
            "render_engine": scene.render.engine
        }
    
    def _build_scene_summary(self, context: Dict[str, Any]) -> str:
        """Build a human-readable scene summary"""
        objects = context.get("objects", [])
        active_object = context.get("active_object")
        
        summary_parts = []
        
        if objects:
            summary_parts.append(f"Scene contains {len(objects)} objects:")
            for obj in objects[:10]:  # Limit to first 10 objects
                status = " (selected)" if obj.get("selected") else ""
                summary_parts.append(f"- {obj['name']} ({obj['type']}){status}")
            
            if len(objects) > 10:
                summary_parts.append(f"... and {len(objects) - 10} more objects")
        
        if active_object:
            summary_parts.append(f"Active object: {active_object}")
        
        return "\n".join(summary_parts) if summary_parts else "Empty scene"

# Blender Operator for sending messages
class BLENDPRO_OT_SendMessage(bpy.types.Operator):
    """Send message to BlendPro AI Co-Pilot"""
    bl_idname = "blendpro.send_message"
    bl_label = "Send Message"
    bl_options = {'REGISTER', 'UNDO'}

    # Background processing variables
    _timer = None
    _thread = None
    _result = None
    _error = None
    _processing = False

    def execute(self, context):
        """Execute the send message operation"""
        if self._processing:
            self.report({'WARNING'}, "Already processing a request. Please wait...")
            return {'CANCELLED'}

        # Get user input
        user_input = context.scene.blendpro_chat_input
        if not user_input.strip():
            self.report({'ERROR'}, "Please enter a message.")
            return {'CANCELLED'}

        # Add user message to chat history
        message = context.scene.blendpro_chat_history.add()
        message.type = 'user'
        message.content = user_input

        # Save chat history
        file_manager = get_file_manager()
        file_manager.save_chat_history(context.scene.blendpro_chat_history)

        # Clear input field
        context.scene.blendpro_chat_input = ""

        # Set processing state
        context.scene.blendpro_button_pressed = True
        self._processing = True
        self._result = None
        self._error = None

        # Extract context data before passing to thread
        context_data = {
            'scene_name': context.scene.name,
            'active_object': context.active_object.name if context.active_object else None,
            'selected_objects': [obj.name for obj in context.selected_objects],
            'mode': context.mode,
            'frame_current': context.scene.frame_current
        }

        # Start background processing
        self._thread = threading.Thread(
            target=self._background_process,
            args=(user_input, context_data)
        )
        self._thread.daemon = True
        self._thread.start()

        # Start timer for modal operation
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def _background_process(self, user_input: str, context_data: dict):
        """Background thread function for processing"""
        try:
            engine = get_interaction_engine()
            # Context'i parametre olarak geç, thread içinde bpy.context kullanma
            result = engine.process_user_input(user_input, context_data)
            self._result = result
        except Exception as e:
            self._error = f"Processing error: {str(e)}"

    def modal(self, context, event):
        """Modal handler for background processing"""
        if event.type == 'TIMER':
            # Check if thread is still alive
            if self._thread and self._thread.is_alive():
                return {'PASS_THROUGH'}

            # Thread completed, cleanup
            self._cleanup_modal(context)

            # Handle errors
            if self._error:
                # Show error in popup
                try:
                    bpy.ops.blendpro.show_response(
                        'INVOKE_DEFAULT',
                        response_text=self._error,
                        response_type="error"
                    )
                except Exception as e:
                    print(f"Error showing error popup: {e}")

                self.report({'ERROR'}, self._error)
                return {'CANCELLED'}

            if not self._result:
                self.report({'ERROR'}, "No response received")
                return {'CANCELLED'}

            # Process result based on type
            return self._process_result(context, self._result)

        return {'PASS_THROUGH'}

    def _cleanup_modal(self, context):
        """Clean up modal operation resources"""
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None

        context.scene.blendpro_button_pressed = False
        self._processing = False

    def _process_result(self, context, result: Dict[str, Any]):
        """Process the result from interaction engine"""

        # Handle errors
        if result.get('error'):
            self.report({'ERROR'}, result['error'])
            return {'CANCELLED'}

        # Add assistant response to chat history
        message = context.scene.blendpro_chat_history.add()
        message.type = 'assistant'
        message.content = result.get('content', '')

        # Save chat history immediately
        file_manager = get_file_manager()
        file_manager.save_chat_history(context.scene.blendpro_chat_history)

        # Handle different result types
        result_type = result.get('type', 'normal')

        if result_type == 'question':
            # Show response in popup
            response_content = result.get('content', 'No response content')
            try:
                bpy.ops.blendpro.show_response(
                    'INVOKE_DEFAULT',
                    response_text=response_content,
                    response_type="answer"
                )
            except Exception as e:
                print(f"Error showing popup: {e}")
            self.report({'INFO'}, "Question answered")

        elif result_type == 'clarification':
            # Mark as needing clarification
            self.report({'INFO'}, "Please provide clarification")

        elif result_type == 'plan_preview':
            # Mark as interactive plan message
            message.is_interactive = True

            # Store plan data
            steps_data = result.get('steps', [])
            message.plan_data = json.dumps(steps_data)

            from ..utils.logger import get_logger
            logger = get_logger("BlendPro.PlanMessage")
            logger.debug(f"Plan data stored: {len(steps_data)} steps")
            logger.debug(f"Plan data JSON length: {len(message.plan_data)}")

            # Store plan_id for later execution
            if 'plan_id' in result:
                message.plan_id = result['plan_id']
                logger.debug(f"Plan ID stored in message: {result['plan_id']}")
                logger.debug(f"Message plan_id type: {type(message.plan_id)}")
                logger.debug(f"Message plan_id value: {message.plan_id}")
            else:
                logger.warning("No plan_id found in result")
                logger.debug(f"Result keys: {list(result.keys())}")

            # Show plan in popup
            steps = result.get('steps', [])
            plan_text = "Multi-Step Plan:\n\n"
            for i, step in enumerate(steps, 1):
                plan_text += f"{i}. {step.get('description', 'No description')}\n"

            try:
                bpy.ops.blendpro.show_response(
                    'INVOKE_DEFAULT',
                    response_text=plan_text,
                    response_type="plan",
                    plan_id=result.get('plan_id', '')
                )
            except Exception as e:
                print(f"Error showing plan popup: {e}")

            # Force UI refresh to show the plan
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'UI':
                            region.tag_redraw()

            self.report({'INFO'}, f"Plan created. Please review and approve.")

        elif result_type == 'multi_step_task':
            # Handle multi-step task result (step-by-step execution)
            code = result.get('code', '')
            if code:
                # Check if this is a step result with next step info
                if result.get('has_next_step'):
                    # Show step result with next step option
                    try:
                        step_title = f"Step {result.get('current_step', 1)}: {result.get('step_description', 'Code Generated')}"
                        next_step = result.get('next_step', {})

                        bpy.ops.blendpro.show_step_result(
                            'INVOKE_DEFAULT',
                            code=code,
                            step_title=step_title,
                            plan_id=result.get('plan_id', ''),
                            current_step=result.get('current_step', 1),
                            total_steps=result.get('total_steps', 1),
                            has_next_step=True,
                            next_step_number=result.get('current_step', 1) + 1,
                            next_step_description=next_step.get('description', 'Continue')
                        )
                    except Exception as e:
                        print(f"Error showing step result popup: {e}")
                        # Fallback to regular code preview
                        bpy.ops.blendpro.code_preview('INVOKE_DEFAULT', code=code)
                else:
                    # Final step - show regular code preview
                    try:
                        step_title = f"Final Step: {result.get('step_description', 'Plan Completed')}"
                        bpy.ops.blendpro.show_response(
                            'INVOKE_DEFAULT',
                            response_text=f"{step_title}\n\n{code}",
                            response_type="code"
                        )
                    except Exception as e:
                        print(f"Error showing final step popup: {e}")
                        bpy.ops.blendpro.code_preview('INVOKE_DEFAULT', code=code)

                self.report({'INFO'}, f"Step {result.get('current_step', 1)} completed. Please review and execute.")
            else:
                self.report({'ERROR'}, "No code generated for step")
                return {'CANCELLED'}

        elif result_type == 'task':
            # Handle regular single task
            code = result.get('code', '')
            if code:
                # Show code in popup
                try:
                    bpy.ops.blendpro.show_response(
                        'INVOKE_DEFAULT',
                        response_text=f"Generated Code:\n\n{code}",
                        response_type="code"
                    )
                except Exception as e:
                    print(f"Error showing code popup: {e}")
                    # Fallback to old method
                    bpy.ops.blendpro.code_preview('INVOKE_DEFAULT', code=code)

                self.report({'INFO'}, "Code generated. Please review and execute.")
            else:
                self.report({'ERROR'}, "No code generated")
                return {'CANCELLED'}

        # Save chat history
        file_manager = get_file_manager()
        file_manager.save_chat_history(context.scene.blendpro_chat_history)

        return {'FINISHED'}

# Plan execution operators
class BLENDPRO_OT_ApprovePlan(bpy.types.Operator):
    """Execute approved plan step by step"""
    bl_idname = "blendpro.approve_plan"
    bl_label = "Execute Plan"
    bl_options = {'REGISTER'}

    plan_steps_json: bpy.props.StringProperty()
    plan_id: bpy.props.StringProperty()
    step_number: bpy.props.IntProperty(default=1)

    def execute(self, context):
        try:
            from ..utils.logger import get_logger
            logger = get_logger("BlendPro.PlanExecution")

            # Debug logging
            logger.debug(f"Plan execution started")
            logger.debug(f"  - plan_id type: {type(self.plan_id)}")
            logger.debug(f"  - plan_id value: {self.plan_id}")
            logger.debug(f"  - step_number: {self.step_number}")
            logger.debug(f"  - has_steps_json: {bool(self.plan_steps_json)}")

            # Plan ID must be provided by UI - no fallback ID generation
            if not self.plan_id or not str(self.plan_id).strip():
                logger.error("Plan execution failed: No plan_id provided to the operator.")
                self.report({'ERROR'}, "Plan ID is missing. Cannot execute.")
                return {'CANCELLED'}

            # Convert Blender property to string
            plan_id_string = str(self.plan_id).strip()
            logger.debug(f"Using provided plan_id: '{plan_id_string}'")

            # Execute plan - check if this is initial approval or step continuation
            engine = get_interaction_engine()

            # If step_number is 1 and we have plan_steps_json, this is initial plan approval from popup
            # In this case, use legacy execution (all steps at once) for backward compatibility
            # If step_number > 1, this is step continuation from UI buttons
            if self.step_number == 1 and self.plan_steps_json:
                # Initial plan approval from popup - use legacy execution
                logger.debug(f"Initial plan approval from popup - using legacy execution with ID: {plan_id_string}")
                result = engine.execute_plan_legacy(plan_id_string)
            else:
                # Step continuation or explicit step execution
                logger.debug(f"Executing plan step {self.step_number} with ID: {plan_id_string}")
                result = engine.execute_plan(plan_id_string, step_number=self.step_number)

            if result.get('error'):
                logger.error(f"Plan execution failed: {result['error']}")
                self.report({'ERROR'}, f"Plan execution failed: {result['error']}")
                return {'CANCELLED'}

            # Add execution result to chat history
            message = context.scene.blendpro_chat_history.add()
            message.type = 'assistant'

            # Check if this is legacy execution (all steps) or step-by-step
            if result.get('is_multi_step') and 'current_step' in result:
                # Step-by-step execution result
                step_info = f"Step {result.get('current_step', self.step_number)}/{result.get('total_steps', '?')}: {result.get('step_description', 'Unknown step')}"
                message.content = f"{step_info}\n\n{result.get('code', '')}"

                # Mark as multi-step result if there are more steps
                if result.get('has_next_step'):
                    message.is_interactive = True
                    message.interaction_type = "next_step"
                    message.plan_id = plan_id_string
                    message.next_step_number = result.get('current_step', self.step_number) + 1
                    message.next_step_info = json.dumps(result.get('next_step', {}))

                # Show code preview with step information
                code = result.get('code', '')
                if code:
                    step_title = f"Step {result.get('current_step', self.step_number)}: {result.get('step_description', 'Code Generated')}"

                    # Show code with next step option if available
                    if result.get('has_next_step'):
                        next_step = result.get('next_step', {})

                        bpy.ops.blendpro.show_step_result(
                            'INVOKE_DEFAULT',
                            code=code,
                            step_title=step_title,
                            plan_id=plan_id_string,
                            current_step=result.get('current_step', self.step_number),
                            total_steps=result.get('total_steps', 1),
                            has_next_step=True,
                            next_step_number=result.get('current_step', self.step_number) + 1,
                            next_step_description=next_step.get('description', 'Continue')
                        )
                    else:
                        # Final step - just show code preview
                        bpy.ops.blendpro.code_preview('INVOKE_DEFAULT', code=code)

                    logger.info(f"Step {self.step_number} executed successfully")
                    self.report({'INFO'}, f"Step {self.step_number} executed successfully")
                else:
                    logger.warning("Step executed but no code was generated")
                    self.report({'WARNING'}, "Step executed but no code was generated")
            else:
                # Legacy execution result (all steps at once)
                message.content = f"Multi-step plan executed:\n{result.get('code', '')}"

                # Show code preview
                code = result.get('code', '')
                if code:
                    bpy.ops.blendpro.code_preview('INVOKE_DEFAULT', code=code)
                    logger.info("Plan executed successfully")
                    self.report({'INFO'}, "Plan executed successfully")
                else:
                    logger.warning("Plan executed but no code was generated")
                    self.report({'WARNING'}, "Plan executed but no code was generated")

            return {'FINISHED'}

        except Exception as e:
            logger.exception(f"Plan execution error: {str(e)}")
            self.report({'ERROR'}, f"Plan execution error: {str(e)}")
            return {'CANCELLED'}

class BLENDPRO_OT_ShowStepResult(bpy.types.Operator):
    """Show step execution result with next step option"""
    bl_idname = "blendpro.show_step_result"
    bl_label = "Step Result"
    bl_options = {'REGISTER'}

    code: bpy.props.StringProperty()
    step_title: bpy.props.StringProperty()
    plan_id: bpy.props.StringProperty()
    current_step: bpy.props.IntProperty()
    total_steps: bpy.props.IntProperty()
    has_next_step: bpy.props.BoolProperty()
    next_step_number: bpy.props.IntProperty()
    next_step_description: bpy.props.StringProperty()

    def execute(self, context):
        return context.window_manager.invoke_props_dialog(self, width=600)

    def draw(self, context):
        layout = self.layout

        # Step title
        title_row = layout.row()
        title_row.label(text=self.step_title, icon='CHECKMARK')

        # Progress indicator
        progress_row = layout.row()
        progress_row.label(text=f"Progress: {self.current_step}/{self.total_steps} steps completed")

        # Code preview
        if self.code:
            code_box = layout.box()
            code_box.label(text="Generated Code:", icon='SCRIPT')

            # Show first few lines of code
            code_lines = self.code.split('\n')[:10]  # Show first 10 lines
            for line in code_lines:
                if line.strip():
                    code_box.label(text=line)

            if len(self.code.split('\n')) > 10:
                code_box.label(text="... (click Execute to see full code)")

        # Action buttons
        button_row = layout.row(align=True)
        button_row.scale_y = 1.2

        # Execute current step code
        exec_op = button_row.operator("blendpro.execute_code", text="Execute Code", icon='PLAY')
        exec_op.code = self.code

        # Next step button (if available)
        if self.has_next_step:
            next_op = button_row.operator("blendpro.approve_plan", text=f"Next Step", icon='FORWARD')
            next_op.plan_id = self.plan_id
            next_op.step_number = self.next_step_number

            # Show next step info
            if self.next_step_description:
                next_info_row = layout.row()
                next_info_row.label(text=f"Next: {self.next_step_description}", icon='INFO')
        else:
            # Plan completed
            completion_row = layout.row()
            completion_row.label(text="✓ Plan completed successfully!", icon='CHECKMARK')

class BLENDPRO_OT_RejectPlan(bpy.types.Operator):
    """Reject plan and use single-step approach"""
    bl_idname = "blendpro.reject_plan"
    bl_label = "Reject Plan"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Add rejection message to chat history
        message = context.scene.blendpro_chat_history.add()
        message.type = 'user'
        message.content = "(Plan rejected - using single-step approach)"

        # Save chat history
        file_manager = get_file_manager()
        file_manager.save_chat_history(context.scene.blendpro_chat_history)

        self.report({'INFO'}, "Plan rejected. Please enter your request again for single-step processing.")
        return {'FINISHED'}

# Global interaction engine instance
_interaction_engine: Optional[InteractionEngine] = None

def get_interaction_engine() -> InteractionEngine:
    """Get global interaction engine instance"""
    global _interaction_engine
    if _interaction_engine is None:
        _interaction_engine = InteractionEngine()
    return _interaction_engine

def register():
    """Register Blender classes"""
    bpy.utils.register_class(BLENDPRO_OT_SendMessage)
    bpy.utils.register_class(BLENDPRO_OT_ApprovePlan)
    bpy.utils.register_class(BLENDPRO_OT_ShowStepResult)
    bpy.utils.register_class(BLENDPRO_OT_RejectPlan)

def unregister():
    """Unregister Blender classes"""
    bpy.utils.unregister_class(BLENDPRO_OT_RejectPlan)
    bpy.utils.unregister_class(BLENDPRO_OT_ShowStepResult)
    bpy.utils.unregister_class(BLENDPRO_OT_ApprovePlan)
    bpy.utils.unregister_class(BLENDPRO_OT_SendMessage)
