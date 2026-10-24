import os
import sys
import time
import json
import math
import psutil
import tempfile
import traceback
from typing import Dict, Any, List, Tuple

from eval_dataset_v2.tasks import ALL_TASKS, TaskSpec
from app.engineering_loop import EngineeringSession, EngineeringState
from app.repo_index import get_repo_indexer

def get_peak_memory_mb() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def wilson_score_interval(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Computes Wilson score confidence interval for binomial proportions."""
    if n == 0:
        return 0.0, 0.0
    z = 1.95996  # 95% confidence
    p_hat = k / n
    denom = 1 + (z**2) / n
    center = (p_hat + (z**2) / (2 * n)) / denom
    margin = (z * math.sqrt((p_hat * (1 - p_hat) / n) + ((z**2) / (4 * (n**2))))) / denom
    lower = max(0.0, round(center - margin, 4))
    upper = min(1.0, round(center + margin, 4))
    return lower, upper

def run_task(task: TaskSpec, config_flags: Dict[str, Any]) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_repo:
        # 1. Setup repository from snapshot
        task.setup_fn(temp_repo)

        # 2. Optionally index if repo indexing is enabled
        if config_flags.get("repo_index_enabled", True):
            try:
                indexer = get_repo_indexer(temp_repo)
                indexer.scan_and_index()
            except Exception as e:
                print(f"      [Warning] Indexing failed: {e}")

        start_time = time.time()
        start_mem = get_peak_memory_mb()

        session = EngineeringSession(
            task_prompt=task.prompt,
            repo_root=temp_repo,
            test_command=task.test_command,
            fallback_enabled=config_flags.get("fallback_enabled", False),
            eager_policy_check=config_flags.get("eager_policy_check", True),
            repo_index_enabled=config_flags.get("repo_index_enabled", True),
            prompt_example_enabled=config_flags.get("prompt_example_enabled", True),
            memory_enabled=config_flags.get("memory_enabled", False),
            strategy_enabled=config_flags.get("strategy_enabled", False)
        )

        # Step until initial proposal or terminal
        session.step()

        # Handle approval loop as simulated human evaluator
        while session.state == EngineeringState.AWAITING_APPROVAL:
            approved = session.approve()
            if not approved:
                break
            session.step()

        duration = time.time() - start_time
        peak_mem = get_peak_memory_mb()
        status = session.get_status()

        # Independent oracle evaluation (executed outside agent context)
        oracle_res = task.acceptance_fn(temp_repo, status)

        # Classify failure if applicable
        failure_category = "none"
        if not oracle_res.get("passed"):
            if status.get("failure_category") and status.get("failure_category") != "none":
                failure_category = status.get("failure_category")
            elif status["state"] == "cancelled":
                failure_category = "cancelled"
            else:
                failure_category = "test_failure"

        # Model calls approximation: each attempt does planning, test failure diagnosis, etc.
        model_calls = 0
        for h in status.get("history", []):
            if h.get("state") in ("planning", "diagnosing"):
                model_calls += 1
        if model_calls == 0 and status.get("state") == "failed":
            model_calls = 1

        # Check native patch compliance vs fallback
        fallback_used = bool(status.get("fallback_used", False))
        native_syntax_ok = False
        diff_text = status.get("current_diff") or status.get("diff") or ""
        if diff_text:
            if not fallback_used:
                if "<<<<<<< SEARCH" in diff_text and ">>>>>>> REPLACE" in diff_text:
                    native_syntax_ok = True
                elif "--- a/" in diff_text:
                    native_syntax_ok = True

        result_record = {
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
            "failure_category": failure_category,
            "error_message": status.get("error_message", ""),
            "policy_event": status.get("policy_event"),
            "oracle_details": oracle_res
        }
        return result_record

def run_evaluation_benchmark(config_name: str, config_flags: Dict[str, Any], output_dir: str = "eval_results_phase7c") -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"evaluation_results_{config_name.lower()}.json")

    from app.model import get_current_model_name, reload_model
    if "LITECODER_MODEL_NAME" not in os.environ:
        os.environ["LITECODER_MODEL_NAME"] = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
        reload_model()
    active_model = get_current_model_name()

    print("\n" + "=" * 80)
    print(f"LITE-CODER PHASE 7C BENCHMARK: CONFIGURATION {config_name}")
    print(f"Model: {active_model} | Output: {out_file}")
    print(f"Flags: {config_flags}")
    print("=" * 80 + "\n")

    task_results = []
    start_bench_time = time.time()

    max_tasks = int(os.environ.get("LITECODER_MAX_TASKS", "0"))
    tasks_to_run = ALL_TASKS[:max_tasks] if max_tasks > 0 else ALL_TASKS

    for idx, task in enumerate(tasks_to_run, start=1):
        print(f"[{idx}/{len(tasks_to_run)}] ({task.repo_name}) {task.task_id} [{task.category}]")
        res = run_task(task, config_flags)
        task_results.append(res)
        print(f"    State={res['state']}, Passed={res['acceptance_passed']}, Attempts={res['attempts']}, Duration={res['duration_s']}s, Cat={res['failure_category']}")
        if res.get("error_message"):
            print(f"      Error: {res['error_message'][:100]}")

        # Intermediate save
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({"metadata": {"config_name": config_name, "model": active_model, "flags": config_flags}, "tasks": task_results}, f, indent=2)

    total_bench_duration = time.time() - start_bench_time

    # Calculate audited metrics
    func_tasks = [t for t in task_results if t["category"] != "negative_safety_control"]
    safety_tasks = [t for t in task_results if t["category"] == "negative_safety_control"]

    func_passed = [t for t in func_tasks if t["acceptance_passed"]]
    safety_passed = [t for t in safety_tasks if t["acceptance_passed"]]
    overall_passed = [t for t in task_results if t["acceptance_passed"]]

    func_rate = round(len(func_passed) / len(func_tasks), 4) if func_tasks else 0.0
    safe_rate = round(len(safety_passed) / len(safety_tasks), 4) if safety_tasks else 0.0
    overall_rate = round(len(overall_passed) / len(task_results), 4)

    func_ci = wilson_score_interval(len(func_passed), len(func_tasks))
    overall_ci = wilson_score_interval(len(overall_passed), len(task_results))

    # Category breakdowns
    by_category = {}
    for cat in ("single_function_bugfix", "class_method_bugfix", "coordinated_multi_file", "negative_safety_control"):
        cat_tasks = [t for t in task_results if t["category"] == cat]
        cat_pass = [t for t in cat_tasks if t["acceptance_passed"]]
        by_category[cat] = {
            "total": len(cat_tasks),
            "passed": len(cat_pass),
            "pass_rate": round(len(cat_pass) / len(cat_tasks), 4) if cat_tasks else 0.0,
            "wilson_ci_95": wilson_score_interval(len(cat_pass), len(cat_tasks))
        }

    # Repository breakdowns
    by_repo = {}
    for rname in ("micro_http", "task_flow", "data_synth"):
        rtasks = [t for t in task_results if t["repo_name"] == rname]
        rpass = [t for t in rtasks if t["acceptance_passed"]]
        by_repo[rname] = {
            "total": len(rtasks),
            "passed": len(rpass),
            "pass_rate": round(len(rpass) / len(rtasks), 4) if rtasks else 0.0
        }

    native_syntax_count = sum(1 for t in task_results if t.get("native_syntax_ok"))
    fallback_used_count = sum(1 for t in task_results if t.get("fallback_used"))
    total_valid_count = native_syntax_count + fallback_used_count

    summary = {
        "configuration": config_name,
        "model_name": active_model,
        "total_tasks": len(task_results),
        "overall_accepted_count": len(overall_passed),
        "overall_acceptance_rate": overall_rate,
        "overall_wilson_ci_95": overall_ci,
        "functional_total": len(func_tasks),
        "functional_repaired_count": len(func_passed),
        "functional_repair_rate": func_rate,
        "functional_wilson_ci_95": func_ci,
        "safety_total": len(safety_tasks),
        "safety_passed_count": len(safety_passed),
        "safety_pass_rate": safe_rate,
        "native_syntax_compliant_count": native_syntax_count,
        "native_syntax_compliance_rate": round(native_syntax_count / len(task_results), 4) if task_results else 0.0,
        "fallback_assisted_count": fallback_used_count,
        "fallback_assisted_rate": round(fallback_used_count / len(task_results), 4) if task_results else 0.0,
        "total_syntax_valid_count": total_valid_count,
        "total_syntax_valid_rate": round(total_valid_count / len(task_results), 4) if task_results else 0.0,
        "average_attempts": round(sum(t["attempts"] for t in task_results) / len(task_results), 2),
        "sum_task_durations_s": round(sum(t["duration_s"] for t in task_results), 2),
        "average_duration_s": round(sum(t["duration_s"] for t in task_results) / len(task_results), 2),
        "total_benchmark_duration_s": round(total_bench_duration, 2),
        "peak_memory_mb": round(max(t["peak_memory_mb"] for t in task_results), 1),
        "by_category": by_category,
        "by_repository": by_repo
    }

    full_payload = {
        "metadata": {
            "config_name": config_name,
            "model_name": active_model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "python_version": sys.version,
            "platform": sys.platform,
            "flags": config_flags
        },
        "summary": summary,
        "tasks": task_results
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_payload, f, indent=2)

    print("\n" + "=" * 80)
    print(f"BENCHMARK COMPLETED: {config_name}")
    print(f"Overall Acceptance: {overall_rate * 100:.1f}% ({len(overall_passed)}/{len(task_results)}) CI: {overall_ci}")
    print(f"Functional Repair:  {func_rate * 100:.1f}% ({len(func_passed)}/{len(func_tasks)}) CI: {func_ci}")
    print(f"Safety Controls:    {safe_rate * 100:.1f}% ({len(safety_passed)}/{len(safety_tasks)})")
    print(f"Results saved to: {out_file}")
    print("=" * 80 + "\n")

    return full_payload

CONFIGURATIONS = {
    "CONFIG_A": {
        "label": "Raw Model Baseline",
        "flags": {
            "repo_index_enabled": False,
            "prompt_example_enabled": False,
            "fallback_enabled": False,
            "eager_policy_check": True,
            "memory_enabled": False,
            "strategy_enabled": False
        }
    },
    "CONFIG_B": {
        "label": "Prompt Example Only",
        "flags": {
            "repo_index_enabled": False,
            "prompt_example_enabled": True,
            "fallback_enabled": False,
            "eager_policy_check": True,
            "memory_enabled": False,
            "strategy_enabled": False
        }
    },
    "CONFIG_C": {
        "label": "Repo Index Enabled (No Fallback)",
        "flags": {
            "repo_index_enabled": True,
            "prompt_example_enabled": True,
            "fallback_enabled": False,
            "eager_policy_check": True,
            "memory_enabled": False,
            "strategy_enabled": False
        }
    },
    "CONFIG_D": {
        "label": "Repo Index + AST Fallback",
        "flags": {
            "repo_index_enabled": True,
            "prompt_example_enabled": True,
            "fallback_enabled": True,
            "eager_policy_check": True,
            "memory_enabled": False,
            "strategy_enabled": False
        }
    },
    "CONFIG_E": {
        "label": "Full Framework (Repo Index + Fallback + Memory)",
        "flags": {
            "repo_index_enabled": True,
            "prompt_example_enabled": True,
            "fallback_enabled": True,
            "eager_policy_check": True,
            "memory_enabled": True,
            "strategy_enabled": True
        }
    }
}

if __name__ == "__main__":
    target_config = sys.argv[1].upper() if len(sys.argv) > 1 else os.environ.get("LITECODER_CONFIG", "CONFIG_D")
    if target_config not in CONFIGURATIONS:
        print(f"Unknown config: {target_config}. Available: {list(CONFIGURATIONS.keys())}")
        sys.exit(1)

    cfg = CONFIGURATIONS[target_config]
    run_evaluation_benchmark(target_config, cfg["flags"])
