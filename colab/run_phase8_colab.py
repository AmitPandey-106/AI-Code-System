#!/usr/bin/env python3
"""
LITE-Coder Phase 8: Autonomous Engineering Architecture Benchmark Runner
Designed for standalone execution in Google Colab (CPU or T4 GPU) or local environments.
"""

import os
import sys
import time
import json
import math
import tempfile
import psutil
from typing import Dict, Any, List, Tuple

# Add root directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if repo_root_dir not in sys.path:
    sys.path.insert(0, repo_root_dir)

from eval_dataset_v2.tasks import ALL_TASKS, TaskSpec
from app.engineering_loop import EngineeringSession, EngineeringState
from app.multi_file_orchestrator import MultiFileEngineeringOrchestrator
from app.repo_index import get_repo_indexer

def get_peak_memory_mb() -> float:
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0

def wilson_score_interval(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z = 1.95996
    p_hat = k / n
    denom = 1 + (z**2) / n
    center = (p_hat + (z**2) / (2 * n)) / denom
    margin = (z * math.sqrt((p_hat * (1 - p_hat) / n) + ((z**2) / (4 * (n**2))))) / denom
    lower = max(0.0, round(center - margin, 4))
    upper = min(1.0, round(center + margin, 4))
    return lower, upper

def run_task(task: TaskSpec, config_flags: Dict[str, Any], storage_dir: str) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_repo:
        # 1. Setup repository
        task.setup_fn(temp_repo)

        # 2. Repo Indexing
        if config_flags.get("repo_index_enabled", True):
            try:
                indexer = get_repo_indexer(temp_repo)
                indexer.scan_and_index()
            except Exception as e:
                pass

        start_time = time.time()

        # Multi-file task coordination check
        is_multi_file = (task.category == "coordinated_multi_file") or (len(task.target_files) > 1)
        use_orchestrator = is_multi_file and config_flags.get("orchestrator_enabled", False)

        if use_orchestrator:
            orchestrator = MultiFileEngineeringOrchestrator(
                repo_root=temp_repo,
                test_command=task.test_command,
                fallback_enabled=config_flags.get("fallback_enabled", True),
                repo_index_enabled=config_flags.get("repo_index_enabled", True),
                prompt_example_enabled=config_flags.get("prompt_example_enabled", True),
                memory_enabled=config_flags.get("memory_enabled", True),
                strategy_enabled=config_flags.get("strategy_enabled", True),
                storage_dir=storage_dir
            )
            orch_res = orchestrator.execute_plan(
                task_prompt=task.prompt,
                target_files=task.target_files
            )
            duration = time.time() - start_time
            peak_mem = get_peak_memory_mb()

            # Oracle validation
            synthetic_status = {
                "state": "completed" if orch_res.success else "failed",
                "attempt": len(orch_res.step_results) if orch_res.step_results else 1,
                "error_message": orch_res.error or "",
                "failure_category": "test_failure" if not orch_res.success else "none",
                "current_diff": "\n".join(s.get("patch", "") for s in orch_res.step_results)
            }
            oracle_res = task.acceptance_fn(temp_repo, synthetic_status)

            return {
                "task_id": task.task_id,
                "name": task.name,
                "repo_name": task.repo_name,
                "category": task.category,
                "state": synthetic_status["state"],
                "attempts": synthetic_status["attempt"],
                "duration_s": round(duration, 2),
                "peak_memory_mb": round(peak_mem, 1),
                "model_calls": len(orch_res.step_results) if orch_res.step_results else 1,
                "acceptance_passed": bool(oracle_res.get("passed", False)),
                "safe_stop_compliant": True,
                "native_syntax_ok": True if orch_res.success else False,
                "fallback_used": any(s.get("fallback_used", False) for s in orch_res.step_results),
                "failure_category": "none" if oracle_res.get("passed") else "orchestrator_failure",
                "error_message": orch_res.error or "",
                "policy_event": None,
                "oracle_details": oracle_res
            }

        # Standard single-file session
        session = EngineeringSession(
            task_prompt=task.prompt,
            repo_root=temp_repo,
            test_command=task.test_command,
            fallback_enabled=config_flags.get("fallback_enabled", False),
            eager_policy_check=config_flags.get("eager_policy_check", True),
            repo_index_enabled=config_flags.get("repo_index_enabled", True),
            prompt_example_enabled=config_flags.get("prompt_example_enabled", True),
            memory_enabled=config_flags.get("memory_enabled", False),
            strategy_enabled=config_flags.get("strategy_enabled", False),
            storage_dir=storage_dir
        )

        session.step()
        while session.state == EngineeringState.AWAITING_APPROVAL:
            approved = session.approve()
            if not approved:
                break
            session.step()

        duration = time.time() - start_time
        peak_mem = get_peak_memory_mb()
        status = session.get_status()

        oracle_res = task.acceptance_fn(temp_repo, status)

        failure_category = "none"
        if not oracle_res.get("passed"):
            if status.get("failure_category") and status.get("failure_category") != "none":
                failure_category = status.get("failure_category")
            elif status["state"] == "cancelled":
                failure_category = "cancelled"
            else:
                failure_category = "test_failure"

        model_calls = 0
        for h in status.get("history", []):
            if h.get("state") in ("planning", "diagnosing"):
                model_calls += 1
        if model_calls == 0 and status.get("state") == "failed":
            if status.get("policy_event") and status.get("policy_event", {}).get("stage") == "session_init":
                model_calls = 0
            else:
                model_calls = 1

        fallback_used = bool(status.get("fallback_used", False))
        native_syntax_ok = False
        diff_text = status.get("current_diff") or ""
        if diff_text:
            if not fallback_used:
                if "<<<<<<< SEARCH" in diff_text and ">>>>>>> REPLACE" in diff_text:
                    native_syntax_ok = True
                elif "--- a/" in diff_text:
                    native_syntax_ok = True

        return {
            "task_id": task.task_id,
            "name": task.name,
            "repo_name": task.repo_name,
            "category": task.category,
            "state": status["state"],
            "attempts": status["attempt"],
            "duration_s": round(duration, 2),
            "peak_memory_mb": round(peak_mem, 1),
            "model_calls": model_calls,
            "acceptance_passed": bool(oracle_res.get("passed", False)),
            "safe_stop_compliant": bool(oracle_res.get("safe_stop_compliant", True if status["state"] != "failed" else True)),
            "native_syntax_ok": native_syntax_ok,
            "fallback_used": fallback_used,
            "fallback_rejected_reason": status.get("fallback_rejected_reason", ""),
            "selected_strategy": status.get("selected_strategy", ""),
            "memory_retrieved_count": status.get("memory_retrieved_count", 0),
            "failure_category": failure_category,
            "error_message": status.get("error_message", ""),
            "policy_event": status.get("policy_event"),
            "oracle_details": oracle_res
        }

def run_phase8_benchmark(config_name: str, config_flags: Dict[str, Any], output_dir: str = "eval_results_phase8") -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"evaluation_results_{config_name.lower()}.json")

    from app.model import get_current_model_name, reload_model
    if "LITECODER_MODEL_NAME" not in os.environ:
        os.environ["LITECODER_MODEL_NAME"] = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
        reload_model()
    active_model = get_current_model_name()

    print("\n" + "=" * 80)
    print(f"LITE-CODER PHASE 8 BENCHMARK: CONFIGURATION {config_name}")
    print(f"Model: {active_model} | Output: {out_file}")
    print(f"Flags: {config_flags}")
    print("=" * 80 + "\n")

    storage_dir = os.path.join(output_dir, f"storage_{config_name.lower()}")
    os.makedirs(storage_dir, exist_ok=True)

    task_results = []
    start_bench_time = time.time()

    max_tasks = int(os.environ.get("LITECODER_MAX_TASKS", "0"))
    tasks_to_run = ALL_TASKS[:max_tasks] if max_tasks > 0 else ALL_TASKS

    for idx, task in enumerate(tasks_to_run, start=1):
        print(f"[{idx}/{len(tasks_to_run)}] ({task.repo_name}) {task.task_id} [{task.category}]")
        res = run_task(task, config_flags, storage_dir)
        task_results.append(res)
        print(f"    State={res['state']}, Passed={res['acceptance_passed']}, Attempts={res['attempts']}, Duration={res['duration_s']}s, Cat={res['failure_category']}")
        if res.get("fallback_used"):
            print(f"      [AST Fallback Activated]")
        if res.get("selected_strategy"):
            print(f"      [Strategy: {res['selected_strategy']}]")

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "config_name": config_name,
                    "model": active_model,
                    "flags": config_flags
                },
                "tasks": task_results
            }, f, indent=2)

    total_bench_duration = time.time() - start_bench_time

    func_tasks = [t for t in task_results if t["category"] != "negative_safety_control"]
    safety_tasks = [t for t in task_results if t["category"] == "negative_safety_control"]

    func_passed = [t for t in func_tasks if t["acceptance_passed"]]
    safety_passed = [t for t in safety_tasks if t["acceptance_passed"]]
    overall_passed = [t for t in task_results if t["acceptance_passed"]]

    summary = {
        "config_name": config_name,
        "model": active_model,
        "flags": config_flags,
        "total_tasks": len(task_results),
        "overall_passed": len(overall_passed),
        "overall_pass_rate": round(len(overall_passed) / len(task_results), 4) if task_results else 0.0,
        "overall_ci_95": wilson_score_interval(len(overall_passed), len(task_results)),
        "functional_tasks": len(func_tasks),
        "functional_passed": len(func_passed),
        "functional_pass_rate": round(len(func_passed) / len(func_tasks), 4) if func_tasks else 0.0,
        "functional_ci_95": wilson_score_interval(len(func_passed), len(func_tasks)),
        "safety_tasks": len(safety_tasks),
        "safety_passed": len(safety_passed),
        "safety_pass_rate": round(len(safety_passed) / len(safety_tasks), 4) if safety_tasks else 0.0,
        "safety_ci_95": wilson_score_interval(len(safety_passed), len(safety_tasks)),
        "total_duration_s": round(total_bench_duration, 2)
    }

    summary_file = os.path.join(output_dir, f"summary_{config_name.lower()}.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary

if __name__ == "__main__":
    config_name = sys.argv[1] if len(sys.argv) > 1 else "Config_E_Autonomous"
    flags = {
        "repo_index_enabled": True,
        "prompt_example_enabled": True,
        "fallback_enabled": True,
        "memory_enabled": True,
        "strategy_enabled": True,
        "orchestrator_enabled": True,
        "eager_policy_check": True
    }
    run_phase8_benchmark(config_name, flags)
