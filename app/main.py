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


# =========================================================
# REQUEST MODEL
# =========================================================

from typing import List
from pydantic import Field

class Request(BaseModel):
    prompt: str
    authoritative_tests: List[str] = Field(default_factory=list)


# =========================================================
# HOME ROUTE
# =========================================================

@app.get("/")
def home():

    return {
        "message": "AI Code Generator Running 🚀"
    }


# =========================================================
# MAIN GENERATION ROUTE
# =========================================================

import time
import uuid

def record_strategy_outcomes(feedback_record):
    """Update strategy policy using the fully verified outcomes (pass or fail)."""
    for att in feedback_record["attempts"]:
        strat = att.get("strategy")
        if not strat:
            continue
            
        strategy_id = strat["selected_strategy"]
        error_type = att.get("error_type", "Unknown")
        attempt_num = att.get("attempt_number", 1)
        
        # Determine if THIS strategy step was successful
        # It's successful if this attempt produced code that fixed the problem (i.e. no next attempt)
        this_attempt_succeeded = (att.get("execution_status") == "success" and att.get("test_results", {}).get("success", False))
        
        # Did it time out or have a security violation?
        sec_viol = "SecurityViolation" in att.get("error_type", "")
        t_out = "TimeoutError" in att.get("error_type", "")
        
        strategy_selector.record_outcome(
            strategy_id=strategy_id,
            error_type=error_type,
            task=feedback_record["task"],
            attempt_number=attempt_num,
            success=this_attempt_succeeded,
            tests_passed=this_attempt_succeeded,
            execution_passed=(att.get("execution_status") == "success"),
            duration_ms=feedback_record.get("execution", {}).get("duration_ms", 500),
            feedback_id=feedback_record["feedback_id"],
            security_violation=sec_viol,
            timeout=t_out
        )

@app.post("/generate")
def generate(req: Request):

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

    # =====================================================
    # STEP 1: INITIAL CODE GENERATION
    # =====================================================

    current_code = generate_code(req.prompt)
    feedback_record["initial_code"] = current_code

    # =====================================================
    # STEP 2: EMPTY GENERATION CHECK
    # =====================================================

    if not current_code or not current_code.strip():
        feedback_record["execution_time"] = time.time() - start_time
        save_feedback(feedback_record)
        return {
            "success": False,
            "message": "Model returned empty code"
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
            fixed_code = fix_code(current_code, error, memory_context, strategy_prompt=strat_prompt)
            attempt_record["repair_applied"] = fixed_code
            current_code = fixed_code
            feedback_record["total_repairs"] += 1
            # Difficulty-Aware Compute Allocation
            if config.get("DIFFICULTY_ALLOCATION_ENABLED"):
                budget = diff_info.get("recommended_attempts", MAX_RETRIES)
            else:
                budget = MAX_RETRIES
                
            if attempt + 1 >= budget:
                print(f"\nRepair budget exhausted ({budget} attempts).")
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
                for i, att in enumerate(feedback_record["attempts"]):
                    if att["error_message"] and att["repair_applied"]:
                        # Do not store security failures as successful repair memories
                        if "SecurityViolation" in att["error_type"]:
                            continue
                            
                        added = repair_memory.add_repair_experience(
                            task=req.prompt,
                            error_type=att["error_type"],
                            error_message=att["error_message"],
                            broken_code=att["code"],
                            successful_fix=att["repair_applied"],
                            tests=att["tests_generated"],
                            verification=feedback_record["verification"],
                            repair_attempts=1
                        )
                        if added:
                            memories_added = True
                            
                if config.get("LORA_ENABLED") and memories_added:
                    # Trigger training worker asynchronously (non-blocking)
                    import subprocess
                    import sys
                    # Popen without wait allows FastAPI to return immediately
                    subprocess.Popen([sys.executable, "train_worker.py"], creationflags=subprocess.CREATE_NEW_CONSOLE | getattr(subprocess, 'DETACHED_PROCESS', 8))
            
            record_strategy_outcomes(feedback_record)
            save_feedback(feedback_record)

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
        fixed_code = fix_code(current_code, error, memory_context, strategy_prompt=strat_prompt)
        attempt_record["repair_applied"] = fixed_code
        current_code = fixed_code
        feedback_record["total_repairs"] += 1
        
        # Difficulty-Aware Compute Allocation
        if config.get("DIFFICULTY_ALLOCATION_ENABLED"):
            budget = diff_info.get("recommended_attempts", MAX_RETRIES)
        else:
            budget = MAX_RETRIES
            
        if attempt + 1 >= budget:
            print(f"\nRepair budget exhausted ({budget} attempts).")
            break

    # =====================================================
    # MAX RETRIES EXCEEDED
    # =====================================================

    feedback_record["final_code"] = current_code
    feedback_record["final_status"] = "failure"
    feedback_record["execution_time"] = time.time() - start_time
    
    record_strategy_outcomes(feedback_record)
    save_feedback(feedback_record)

    return {
        "success": False,
        "message": "Maximum retry attempts exceeded",
        "final_code": current_code,
        "history": attempt_history,
        "feedback_record": feedback_record
    }