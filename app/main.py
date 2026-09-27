from fastapi import FastAPI
from pydantic import BaseModel

from app.model import generate_code, fix_code, classify_error
from app.executor import execute_code
from app.feedback import save_feedback
from app.tester import run_tests
from app.repair_memory import repair_memory
from app.repair_difficulty import estimate_difficulty
from app.strategy_selector import strategy_selector
from app.repair_strategy import get_strategy_prompt
from app.config import config

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODEL
# =========================================================

from typing import List, Optional
from pydantic import Field

class Request(BaseModel):
    prompt: str
    authoritative_tests: List[str] = Field(default_factory=list)
    experiment_id: Optional[str] = None
    task_id: Optional[str] = None
    task_index: Optional[int] = None
    approved_plan: Optional[str] = None

class PlanRequest(BaseModel):
    prompt: str
    feedback: Optional[str] = None
    authoritative_tests: List[str] = Field(default_factory=list)

def infer_initial_tests(prompt: str) -> List[str]:
    """Intelligently infer default test assertions if none are provided or if previous tests mismatched."""
    import re
    lower_prompt = prompt.lower()
    
    # Check if number count is specified (three / 3, four / 4, etc.)
    num_args = 2
    if any(k in lower_prompt for k in ["three", " 3 ", "3 number", "three number", "3 args", "three args"]):
        num_args = 3
    elif any(k in lower_prompt for k in ["four", " 4 ", "4 number", "four number"]):
        num_args = 4

    match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)", prompt)
    func_name = match.group(1) if match else None
    params = [p.strip().split(":")[0].strip() for p in match.group(2).split(",") if p.strip()] if match else []
    
    if not func_name:
        if "binary" in lower_prompt and "search" in lower_prompt:
            func_name = "binary_search"
            params = ["arr", "target"]
        elif "fibonacci" in lower_prompt or "fibo" in lower_prompt:
            func_name = "fibonacci"
            params = ["n"]
        elif "factorial" in lower_prompt:
            func_name = "factorial"
            params = ["n"]
        elif "palindrome" in lower_prompt:
            func_name = "is_palindrome"
            params = ["s"]
        elif "reverse" in lower_prompt and "string" in lower_prompt:
            func_name = "reverse_string"
            params = ["s"]
        elif "add" in lower_prompt or "sum" in lower_prompt:
            func_name = "add"
            if num_args == 3:
                params = ["a", "b", "c"]
            elif num_args == 4:
                params = ["a", "b", "c", "d"]
            else:
                params = ["a", "b"]
        elif "concat" in lower_prompt:
            func_name = "concat"
            params = ["a", "b"]
        elif "sort" in lower_prompt:
            func_name = "sort_list"
            params = ["arr"]
        elif "even" in lower_prompt:
            func_name = "is_even"
            params = ["n"]
            
    if func_name:
        p_len = len(params)
        fn = func_name
        if "search" in fn or "binary" in fn:
            return [
                f"assert {fn}([1, 2, 3, 4, 5], 3) == 2 or {fn}([1, 2, 3, 4, 5], 3) is True",
                f"assert {fn}([10, 20, 30], 25) == -1 or {fn}([10, 20, 30], 25) is False"
            ]
        elif "add" in fn or "sum" in fn:
            if p_len == 3 or num_args == 3:
                return [f"assert {fn}(1, 2, 3) == 6", f"assert {fn}(10, 20, 30) == 60"]
            elif p_len == 4 or num_args == 4:
                return [f"assert {fn}(1, 2, 3, 4) == 10", f"assert {fn}(5, 5, 5, 5) == 20"]
            elif p_len == 2:
                return [f"assert {fn}(2, 3) == 5", f"assert {fn}(-1, 1) == 0"]
            return [f"assert {fn}([1, 2, 3]) == 6", f"assert {fn}([0]) == 0"]
        elif "concat" in fn:
            return [f"assert {fn}('Hello ', 'World') == 'Hello World'", f"assert {fn}('Lite', 'Coder') == 'LiteCoder'"]
        elif "fib" in fn:
            if any(k in lower_prompt for k in ["seq", "series", "list", "array", "first", "terms", "numbers"]):
                return [
                    f"assert {fn}(0) in (0, [], [0])",
                    f"assert {fn}(1) in (1, [0], [1], [0, 1])",
                    f"assert {fn}(5) == 5 or {fn}(5) == [0, 1, 1, 2, 3] or {fn}(5) == [0, 1, 1, 2, 3, 5] or (isinstance({fn}(5), (list, tuple)) and len({fn}(5)) in (5, 6))"
                ]
            return [
                f"assert {fn}(0) in (0, [], [0]) or {fn}(0) == 0",
                f"assert {fn}(1) in (1, [0], [1], [0, 1]) or {fn}(1) == 1",
                f"assert {fn}(5) == 5 or (isinstance({fn}(5), (list, tuple)) and (5 in {fn}(5) or len({fn}(5)) in (5, 6)))"
            ]
        elif "factorial" in fn:
            return [f"assert {fn}(0) == 1", f"assert {fn}(4) == 24"]
        elif "palindrome" in fn:
            return [f"assert {fn}('radar') is True", f"assert {fn}('hello') is False"]
        elif "reverse" in fn:
            return [f"assert {fn}('hello') == 'olleh'", f"assert {fn}('') == ''"]
        elif "even" in fn:
            return [f"assert {fn}(4) is True", f"assert {fn}(7) is False"]
        elif p_len == 2:
            return [f"assert {fn}(10, 5) is not None"]
        elif p_len == 1:
            return [f"assert {fn}(5) is not None"]
            
    return []

# =========================================================
# HOME & PLAN ROUTES
# =========================================================

@app.get("/")
def home():
    return {
        "message": "AI Code Generator Running 🚀"
    }

@app.post("/plan")
def plan(req: PlanRequest):
    from app.model import generate_plan
    task_prompt = req.prompt
    if req.feedback:
        task_prompt = f"{req.prompt}\n\nUSER FEEDBACK / REVISION REQUIREMENTS:\n{req.feedback}"
        
    plan_text = generate_plan(task_prompt)
    
    # Infer matching tests using combined prompt and feedback
    combined_prompt = f"{req.prompt} {req.feedback or ''}"
    inferred = infer_initial_tests(combined_prompt)

    if req.feedback:
        # User gave explicit feedback (e.g. "for assert add three number")
        suggested_tests = inferred if inferred else req.authoritative_tests
    else:
        suggested_tests = req.authoritative_tests if req.authoritative_tests else inferred

    return {
        "success": True,
        "plan": plan_text,
        "suggested_tests": suggested_tests,
        "task_prompt": task_prompt
    }


# =========================================================
# MAIN GENERATION ROUTE
# =========================================================

import time
import uuid

def record_strategy_outcomes(feedback_record):
    """Update strategy policy using the fully verified outcomes (pass or fail)."""
    attempts = feedback_record.get("attempts", [])
    for i, att in enumerate(attempts):
        strat = att.get("strategy")
        if not strat:
            continue
            
        strategy_id = strat["selected_strategy"]
        error_type = att.get("error_type", "Unknown")
        attempt_num = att.get("attempt_number", 1)
        
        # The strategy generated a repair evaluated in the NEXT attempt.
        this_attempt_succeeded = False
        execution_passed = False
        tests_passed = False
        sec_viol = False
        t_out = False
        
        if i + 1 < len(attempts):
            next_att = attempts[i + 1]
            execution_passed = (next_att.get("execution_status") == "success")
            tests_passed = (next_att.get("test_results") or {}).get("success", False)
            this_attempt_succeeded = (execution_passed and tests_passed)
            next_err = next_att.get("error_type") or ""
            sec_viol = "SecurityViolation" in next_err
            t_out = "TimeoutError" in next_err
        
        strategy_selector.record_outcome(
            strategy_id=strategy_id,
            error_type=error_type,
            task=feedback_record["task"],
            attempt_number=attempt_num,
            success=this_attempt_succeeded,
            tests_passed=tests_passed,
            execution_passed=execution_passed,
            duration_ms=feedback_record.get("execution", {}).get("duration_ms", 500),
            feedback_id=feedback_record["feedback_id"],
            security_violation=sec_viol,
            timeout=t_out
        )

@app.post("/generate")
def generate(req: Request):
    from app.model import check_and_reload_adapter
    check_and_reload_adapter()

    MAX_RETRIES = 5
    start_time = time.time()
    feedback_id = uuid.uuid4().hex

    # Initialize structured feedback record
    feedback_record = {
        "feedback_id": feedback_id,
        "timestamp": start_time,
        "task": req.prompt,
        "initial_code": "",
        "attempts": [],
        "final_code": "",
        "final_status": "failure",
        "total_attempts": 0,
        "total_repairs": 0,
        "verification": {
            "syntax_passed": False,
            "safety_passed": False,
            "execution_passed": False,
            "tests_passed": False,
            "sandboxed_execution": True
        },
        "execution": {
            "status": "pending",
            "duration_ms": 0,
            "timeout": False
        },
        "security": {
            "status": "allowed",
            "violations": []
        },
        "execution_time": 0.0
    }

    from app import model as app_model
    app_model.check_and_reload_adapter()
    feedback_record["task_id"] = getattr(req, "task_id", None)
    feedback_record["task_index"] = getattr(req, "task_index", None)
    feedback_record["lora_enabled"] = config.get("LORA_ENABLED", False)
    feedback_record["active_adapter_id"] = app_model._loaded_adapter_id
    feedback_record["training_triggered"] = False
    feedback_record["training_cycle_id"] = None
    feedback_record["training_status"] = None

    # =====================================================
    # STEP 1: INITIAL CODE GENERATION
    # =====================================================

    current_code, prompt_text = generate_code(req.prompt, approved_plan=getattr(req, "approved_plan", None))
    feedback_record["initial_code"] = current_code
    feedback_record["generation_prompt"] = prompt_text

    # =====================================================
    # STEP 2: EMPTY GENERATION CHECK
    # =====================================================

    if not current_code or not current_code.strip():
        feedback_record["execution_time"] = time.time() - start_time
        save_feedback(feedback_record, experiment_id=req.experiment_id)
        return {
            "success": False,
            "message": "Model returned empty code",
            "attempts_used": 0,
            "feedback_record": feedback_record
        }

    attempt_history = []

    # =====================================================
    # STEP 3: AUTONOMOUS RETRY LOOP
    # =====================================================

    for attempt in range(MAX_RETRIES):
        print(f"\n========== ATTEMPT {attempt + 1} ==========\n")
        feedback_record["total_attempts"] = attempt + 1
        
        attempt_record = {
            "attempt_number": attempt + 1,
            "code": current_code,
            "execution_status": "pending",
            "error_type": None,
            "error_message": None,
            "tests_generated": "",
            "test_results": None,
            "repair_applied": None,
            "verification": {}
        }

        # =================================================
        # EXECUTE CODE
        # =================================================
        
        start_exec = time.time()
        execution = execute_code(current_code)
        exec_duration = int((time.time() - start_exec) * 1000)
        feedback_record["execution"]["duration_ms"] = exec_duration

        # Store static verification data
        verif = execution.get("verification", {})
        attempt_record["verification"] = verif
        
        if not verif.get("safety_passed", True):
            feedback_record["security"]["status"] = "blocked"
            feedback_record["security"]["violations"].append(execution["error"])

        if execution.get("error") and "TimeoutError" in execution["error"]:
            feedback_record["execution"]["timeout"] = True

        # =================================================
        # EXECUTION FAILED
        # =================================================

        if not execution["success"]:
            error = execution["error"]
            category, specific_type, specific_msg = classify_error(error)
            
            attempt_record["execution_status"] = "failed"
            attempt_record["error_type"] = specific_type
            attempt_record["error_message"] = specific_msg

            # Retrieve Memory
            if config.get("MEMORY_ENABLED"):
                memories = repair_memory.search_similar_experiences(req.prompt, specific_type, specific_msg, current_code)
            else:
                memories = []
            memory_context = ""
            attempt_record["memory_used"] = len(memories) > 0
            attempt_record["retrieved_memory_count"] = len(memories)
            attempt_record["retrieved_memories"] = [{"memory_id": m["memory"]["memory_id"], "similarity": m["similarity"]} for m in memories]
            
            # --- STRATEGY LEARNING ---
            prev_strats = [att.get("strategy", {}).get("selected_strategy") for att in feedback_record["attempts"] if att.get("strategy")]
            diff_info = estimate_difficulty(specific_type, current_code, attempt + 1, len(memories) > 0)
            attempt_record["difficulty"] = diff_info
            
            strat_info = strategy_selector.select_strategy(
                error_type=specific_type,
                attempt_number=attempt + 1,
                previous_strategies=prev_strats,
                memory_available=len(memories) > 0,
                difficulty=diff_info["difficulty"]
            )
            attempt_record["strategy"] = strat_info
            
            # Strategy decides if we use memory in prompt
            if strat_info["selected_strategy"] == "DIRECT_REPAIR" or strat_info["selected_strategy"] == "MINIMAL_PATCH":
                memory_context = "" # Skip memory
            else:
                if memories:
                    for idx, m in enumerate(memories):
                        memory_context += f"Experience {idx+1}:\nError:\n{m['memory']['error_message']}\nBroken Code:\n{m['memory']['broken_code']}\nSuccessful Fix:\n{m['memory']['successful_fix']}\n\n"

            attempt_record["memory_injected"] = len(memory_context) > 0
            
            attempt_history.append({
                "attempt": attempt + 1,
                "stage": "execution",
                "error": error
            })
            feedback_record["attempts"].append(attempt_record)

            print("\nExecution Failed:")
            print(error)

            # =============================================
            # FIX CODE
            # =============================================
            strat_prompt = get_strategy_prompt(strat_info["selected_strategy"])
            fixed_code, debug_prompt = fix_code(current_code, error, memory_context, strategy_prompt=strat_prompt)
            attempt_record["debug_prompt"] = debug_prompt
            attempt_record["repair_applied"] = fixed_code
            
            # Explicit failure handling and identical state detection
            if not fixed_code or not fixed_code.strip():
                attempt_record["repair_generation_failed"] = True
                attempt_record["repair_failure_reason"] = "Model failed to produce valid Python code"
                attempt_record["repair_changed_code"] = False
            else:
                attempt_record["repair_generation_failed"] = False
                attempt_record["repair_failure_reason"] = None
                attempt_record["repair_changed_code"] = (fixed_code.strip() != current_code.strip())
                current_code = fixed_code
                
            feedback_record["total_repairs"] += 1
            # Difficulty is observational only. Use MAX_RETRIES.
            if attempt + 1 >= MAX_RETRIES:
                print(f"\nMax retries exhausted ({MAX_RETRIES} attempts).")
                break
            continue
            
        attempt_record["execution_status"] = "success"
        feedback_record["verification"]["execution_passed"] = True
        feedback_record["verification"]["syntax_passed"] = True
        feedback_record["verification"]["safety_passed"] = True
        feedback_record["execution"]["status"] = "success"

        # =================================================
        # RUN AI-GENERATED TESTS
        # =================================================

        tests = run_tests(
            req.prompt,
            current_code,
            authoritative_tests=req.authoritative_tests
        )
        attempt_record["tests_generated"] = tests.get("tests", "")
        attempt_record["test_results"] = tests.get("test_summary", {})

        # =================================================
        # TESTS PASSED
        # =================================================

        if tests["success"]:
            feedback_record["attempts"].append(attempt_record)
            feedback_record["final_code"] = current_code
            feedback_record["final_status"] = "success"
            feedback_record["verification"]["tests_passed"] = True
            feedback_record["execution_time"] = time.time() - start_time
            
            # Store valid repairs in memory only if all verification passes
            if config.get("MEMORY_ENABLED") and feedback_record["verification"]["syntax_passed"] and feedback_record["verification"]["safety_passed"] and feedback_record["verification"]["execution_passed"] and feedback_record["verification"]["tests_passed"]:
                memories_added = False
                if len(feedback_record["attempts"]) > 1:
                    last_failed_att = feedback_record["attempts"][-2]
                    successful_att = feedback_record["attempts"][-1]
                    if last_failed_att["error_message"] and last_failed_att["repair_applied"]:
                        # Do not store security failures as successful repair memories
                        if "SecurityViolation" not in last_failed_att["error_type"]:
                            added = repair_memory.add_repair_experience(
                                task=req.prompt,
                                error_type=last_failed_att["error_type"],
                                error_message=last_failed_att["error_message"],
                                broken_code=last_failed_att["code"],
                                successful_fix=last_failed_att["repair_applied"],
                                tests=successful_att["tests_generated"],
                                verification=feedback_record["verification"],
                                repair_attempts=1
                            )
                            if added:
                                memories_added = True
                            
                if config.get("LORA_ENABLED") and memories_added:
                    # Trigger controlled continual-learning training pipeline
                    try:
                        from train_worker import run_training_pipeline
                        train_res = run_training_pipeline(
                            force=False,
                            experiment_id=req.experiment_id,
                            trigger_task_id=getattr(req, "task_id", None),
                            trigger_task_index=getattr(req, "task_index", None)
                        )
                        if train_res.get("trained"):
                            feedback_record["training_triggered"] = True
                            feedback_record["training_cycle_id"] = train_res.get("training_cycle_id")
                            if train_res.get("promotion_status") == "promoted" or (train_res.get("success") and not train_res.get("rollback")):
                                feedback_record["training_status"] = "success"
                                print(f"[MAIN] Successfully updated adapter to {train_res.get('adapter_id')}")
                                check_and_reload_adapter()
                                feedback_record["active_adapter_id"] = app_model._loaded_adapter_id
                            elif train_res.get("rollback"):
                                feedback_record["training_status"] = "rejected_rollback"
                                feedback_record["training_error"] = train_res.get("rejection_reason")
                                print(f"[MAIN WARNING] Candidate {train_res.get('adapter_id')} rejected by Canary Gate. Retaining stable adapter: {train_res.get('active_adapter_id')}")
                                feedback_record["active_adapter_id"] = app_model._loaded_adapter_id
                            else:
                                feedback_record["training_status"] = "failed"
                                print(f"[MAIN ERROR] Training cycle failed: {train_res.get('error')}")
                                feedback_record["training_error"] = train_res.get("error")
                    except Exception as train_exc:
                        print(f"[MAIN ERROR] Unexpected error during training pipeline execution: {train_exc}")
                        feedback_record["training_error"] = str(train_exc)
                        feedback_record["training_triggered"] = True
                        feedback_record["training_status"] = "failed"
            
            record_strategy_outcomes(feedback_record)
            save_feedback(feedback_record, experiment_id=req.experiment_id)

            return {
                "success": True,
                "attempts_used": attempt + 1,
                "generated_code": current_code,
                "execution": execution,
                "tests": tests,
                "history": attempt_history,
                "feedback_record": feedback_record
            }

        # =================================================
        # TEST FAILURE
        # =================================================

        error = tests["message"]
        category, specific_type, specific_msg = classify_error(error)
        
        attempt_record["error_type"] = specific_type
        attempt_record["error_message"] = specific_msg

        # Retrieve Memory
        if config.get("MEMORY_ENABLED"):
            memories = repair_memory.search_similar_experiences(req.prompt, specific_type, specific_msg, current_code)
        else:
            memories = []
        memory_context = ""
        attempt_record["memory_used"] = len(memories) > 0
        attempt_record["retrieved_memory_count"] = len(memories)
        attempt_record["retrieved_memories"] = [{"memory_id": m["memory"]["memory_id"], "similarity": m["similarity"]} for m in memories]
        
        # --- STRATEGY LEARNING ---
        prev_strats = [att.get("strategy", {}).get("selected_strategy") for att in feedback_record["attempts"] if att.get("strategy")]
        diff_info = estimate_difficulty(specific_type, current_code, attempt + 1, len(memories) > 0)
        attempt_record["difficulty"] = diff_info
        
        strat_info = strategy_selector.select_strategy(
            error_type=specific_type,
            attempt_number=attempt + 1,
            previous_strategies=prev_strats,
            memory_available=len(memories) > 0,
            difficulty=diff_info["difficulty"]
        )
        attempt_record["strategy"] = strat_info
        
        if strat_info["selected_strategy"] == "DIRECT_REPAIR" or strat_info["selected_strategy"] == "MINIMAL_PATCH":
            memory_context = "" # Skip memory
        else:
            if memories:
                for idx, m in enumerate(memories):
                    memory_context += f"Experience {idx+1}:\nError:\n{m['memory']['error_message']}\nBroken Code:\n{m['memory']['broken_code']}\nSuccessful Fix:\n{m['memory']['successful_fix']}\n\n"

        attempt_record["memory_injected"] = len(memory_context) > 0

        attempt_history.append({
            "attempt": attempt + 1,
            "stage": "testing",
            "error": error
        })
        feedback_record["attempts"].append(attempt_record)

        print("\nTests Failed:")
        print(error)

        # =================================================
        # FIX CODE
        # =================================================

        strat_prompt = get_strategy_prompt(strat_info["selected_strategy"])
        fixed_code, debug_prompt = fix_code(current_code, error, memory_context, strategy_prompt=strat_prompt)
        attempt_record["debug_prompt"] = debug_prompt
        attempt_record["repair_applied"] = fixed_code
        
        # Explicit failure handling and identical state detection
        if not fixed_code or not fixed_code.strip():
            attempt_record["repair_generation_failed"] = True
            attempt_record["repair_failure_reason"] = "Model failed to produce valid Python code"
            attempt_record["repair_changed_code"] = False
        else:
            attempt_record["repair_generation_failed"] = False
            attempt_record["repair_failure_reason"] = None
            attempt_record["repair_changed_code"] = (fixed_code.strip() != current_code.strip())
            current_code = fixed_code
            
        feedback_record["total_repairs"] += 1
        
        # Difficulty is observational only. Use MAX_RETRIES.
        if attempt + 1 >= MAX_RETRIES:
            print(f"\nMax retries exhausted ({MAX_RETRIES} attempts).")
            break

    # =====================================================
    # MAX RETRIES EXCEEDED
    # =====================================================

    feedback_record["final_code"] = current_code
    feedback_record["final_status"] = "failure"
    feedback_record["execution_time"] = time.time() - start_time
    
    record_strategy_outcomes(feedback_record)
    save_feedback(feedback_record, experiment_id=req.experiment_id)

    return {
        "success": False,
        "message": "Maximum retry attempts exceeded",
        "final_code": current_code,
        "history": attempt_history,
        "feedback_record": feedback_record
    }