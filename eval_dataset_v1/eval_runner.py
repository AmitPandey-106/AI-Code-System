import os
import sys
import time
import json
import psutil
import tempfile
import traceback
import subprocess
from typing import Dict, Any, List

from eval_dataset_v1.tasks import ALL_TASKS, TaskSpec
from app.engineering_loop import EngineeringSession, EngineeringState
from app.repo_index import get_repo_indexer

def get_peak_memory_mb() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def run_engineering_loop_task(task: TaskSpec) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_repo:
        # 1. Setup repository
        task.setup_fn(temp_repo)
        
        # Initialize repo index inside temp_repo for context retrieval
        indexer = get_repo_indexer(temp_repo)
        indexer.scan_and_index()
        
        start_time = time.time()
        start_mem = get_peak_memory_mb()
        
        session = EngineeringSession(
            task_prompt=task.prompt,
            repo_root=temp_repo,
            test_command=task.test_command
        )
        
        # Step until initial proposal or terminal
        session.step()
        
        # Handle approval loop
        while session.state == EngineeringState.AWAITING_APPROVAL:
            # Grant approval as simulated user
            approved = session.approve()
            if not approved:
                break
            session.step()
            
        duration = time.time() - start_time
        peak_mem = get_peak_memory_mb()
        status = session.get_status()
        
        # Independent oracle evaluation
        oracle_res = task.acceptance_fn(temp_repo, status)
        
        # Classify failure if applicable
        failure_category = "none"
        if not oracle_res.get("passed"):
            if status.get("failure_category") and status.get("failure_category") != "none":
                failure_category = status.get("failure_category")
            elif status["state"] == "cancelled":
                failure_category = "user_cancelled"
            elif status["state"] == "failed":
                if "Budget exhausted" in status.get("error_message", ""):
                    failure_category = "budget_exhausted"
                elif "unapproved_command" in str(status) or "SecurityViolation" in status.get("error_message", ""):
                    failure_category = "policy_rejection"
                elif "Patch validation failed" in status.get("error_message", ""):
                    failure_category = "patch_validation_failure"
                else:
                    failure_category = "runtime_failure"
            else:
                failure_category = "oracle_mismatch"
                
        return {
            "task_id": task.task_id,
            "category": task.category,
            "workflow": "integrated_engineering_loop",
            "state": status["state"],
            "attempts": status["attempt"],
            "duration_s": round(duration, 2),
            "peak_memory_mb": round(peak_mem, 1),
            "model_calls": len(status["history"]),
            "acceptance_passed": oracle_res.get("passed", False),
            "regression_detected": oracle_res.get("regression_occurred", False),
            "safe_stop_compliant": oracle_res.get("safe_stop_compliant", True),
            "failure_category": failure_category,
            "error_message": status.get("error_message", ""),
            "policy_event": status.get("policy_event"),
            "oracle_details": oracle_res
        }

def run_mode_d_task(task: TaskSpec) -> Dict[str, Any]:
    if not task.mode_d_compatible:
        return {
            "task_id": task.task_id,
            "category": task.category,
            "workflow": "mode_d_baseline",
            "state": "incompatible",
            "attempts": 0,
            "duration_s": 0.0,
            "acceptance_passed": False,
            "regression_detected": False,
            "incompatibility_reason": "Task requires multi-file diff patching or repository-level module isolation.",
            "failure_category": "architecturally_incompatible"
        }
        
    start_time = time.time()
    # MODE-D simulated run using standard single-function generation contract
    from app.model import generate_code, fix_code
    from app.contract import TaskContract
    from app.executor import execute_code
    
    contract = TaskContract.create_from_prompt(task.mode_d_prompt, authoritative_tests=[task.mode_d_tests])
    current_code, _ = generate_code(task.mode_d_prompt, contract=contract)
    
    attempts = 1
    max_retries = 3
    passed = False
    
    for attempt in range(max_retries):
        test_res = execute_code(current_code, test_code=task.mode_d_tests, contract=contract)
        if test_res.get("success"):
            passed = True
            break
        if attempt + 1 < max_retries:
            current_code, _ = fix_code(current_code, test_res.get("error", "Assertion failed"), retrieved_context="")
            attempts += 1
            
    duration = time.time() - start_time
    
    return {
        "task_id": task.task_id,
        "category": task.category,
        "workflow": "mode_d_baseline",
        "state": "completed" if passed else "failed",
        "attempts": attempts,
        "duration_s": round(duration, 2),
        "acceptance_passed": passed,
        "regression_detected": False,
        "failure_category": "none" if passed else "repair_exhausted"
    }

def main():
    print("=" * 60)
    print("LITE-CODER PHASE 6: RELIABILITY AUDIT & EVALUATION RUNNER")
    print("=" * 60)
    
    from app.model import get_current_model_name
    active_model = get_current_model_name()
    fallback_on = os.environ.get("LITECODER_FALLBACK_SYNTHESIZER", "").lower() == "true"
    eager_policy_on = os.environ.get("LITECODER_EAGER_POLICY_CHECK", "").lower() == "true"
    experiment_label = os.environ.get("LITECODER_EXPERIMENT_LABEL") or ("prompt_plus_fallback" if fallback_on else "prompt_only")

    env_metadata = {
        "model_name": active_model,
        "experiment_label": experiment_label,
        "fallback_synthesizer_enabled": fallback_on,
        "eager_policy_check_enabled": eager_policy_on,
        "python_version": sys.version,
        "platform": sys.platform,
        "cpu_count": psutil.cpu_count(logical=True),
        "total_ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    results = {
        "metadata": env_metadata,
        "tasks": [],
        "summary": {}
    }
    
    print(f"\nActive Model: {active_model}")
    print(f"Experiment: {experiment_label} (Fallback: {fallback_on}, EagerPolicy: {eager_policy_on})")
    print("Running Evaluation Tasks on Integrated Engineering Loop...\n")
    eng_loop_results = []
    mode_d_results = []
    
    # Prepare output file
    output_dir = os.environ.get("LITECODER_EVAL_DIR") or "eval_results_phase7b"
    os.makedirs(output_dir, exist_ok=True)
    out_filename = os.environ.get("LITECODER_EVAL_OUT") or f"evaluation_results_{experiment_label}.json"
    out_file = os.path.join(output_dir, out_filename)

    for task in ALL_TASKS:
        print(f"--> [{task.task_id}] {task.name} ({task.category})")
        eng_res = run_engineering_loop_task(task)
        eng_loop_results.append(eng_res)
        print(f"    Integrated Loop: State={eng_res['state']}, Passed={eng_res['acceptance_passed']}, Attempts={eng_res['attempts']}, Category={eng_res.get('failure_category')}, Duration={eng_res['duration_s']}s")
        if eng_res.get('error_message'):
            print(f"      Error: {eng_res['error_message'][:120]}")
        
        mode_d_res = run_mode_d_task(task)
        mode_d_results.append(mode_d_res)
        print(f"    MODE-D Baseline: State={mode_d_res['state']}, Passed={mode_d_res['acceptance_passed']}, Duration={mode_d_res['duration_s']}s")
        
        # Save intermediate progress so an interruption never loses completed work
        results["tasks"] = {
            "engineering_loop": eng_loop_results,
            "mode_d": mode_d_results
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        
    results["tasks"] = {
        "engineering_loop": eng_loop_results,
        "mode_d": mode_d_results
    }
    
    # Aggregate metrics
    eng_passed = sum(1 for r in eng_loop_results if r["acceptance_passed"])
    eng_safe_stops = sum(1 for r in eng_loop_results if r.get("safe_stop_compliant", True))
    eng_syntax_ok = sum(1 for r in eng_loop_results if r.get("failure_category") != "malformed_patch_syntax")
    eng_total = len(eng_loop_results)
    
    mode_d_compatible_tasks = [r for r in mode_d_results if r["state"] != "incompatible"]
    mode_d_passed = sum(1 for r in mode_d_compatible_tasks if r["acceptance_passed"])
    
    results["summary"] = {
        "engineering_loop": {
            "model_name": active_model,
            "total_tasks": eng_total,
            "acceptance_pass_count": eng_passed,
            "acceptance_pass_rate": round(eng_passed / eng_total, 3),
            "syntax_compliance_count": eng_syntax_ok,
            "syntax_compliance_rate": round(eng_syntax_ok / eng_total, 3),
            "safe_stop_compliance_rate": round(eng_safe_stops / eng_total, 3),
            "average_attempts": round(sum(r["attempts"] for r in eng_loop_results) / eng_total, 2),
            "average_duration_s": round(sum(r["duration_s"] for r in eng_loop_results) / eng_total, 2),
            "total_duration_s": round(sum(r["duration_s"] for r in eng_loop_results), 2),
            "peak_memory_mb": round(max(r.get("peak_memory_mb", 0.0) for r in eng_loop_results), 1),
            "regressions_detected": sum(1 for r in eng_loop_results if r.get("regression_detected"))
        },
        "mode_d_baseline": {
            "total_tasks": len(mode_d_results),
            "compatible_tasks": len(mode_d_compatible_tasks),
            "incompatible_tasks": len(mode_d_results) - len(mode_d_compatible_tasks),
            "acceptance_pass_count": mode_d_passed,
            "compatible_pass_rate": round(mode_d_passed / len(mode_d_compatible_tasks), 3) if mode_d_compatible_tasks else 0.0
        }
    }
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print(f"Results saved to: {out_file}")
    print(f"Engineering Loop Pass Rate: {results['summary']['engineering_loop']['acceptance_pass_rate'] * 100:.1f}% ({eng_passed}/{eng_total})")
    print(f"MODE-D Compatible Pass Rate: {results['summary']['mode_d_baseline']['compatible_pass_rate'] * 100:.1f}% ({mode_d_passed}/{len(mode_d_compatible_tasks)}) [4/7 tasks incompatible]")
    print("=" * 60)

if __name__ == "__main__":
    main()
