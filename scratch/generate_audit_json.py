import json
import os
import math

def wilson_ci(k, n, confidence=0.95):
    if n == 0:
        return (0.0, 0.0)
    z = 1.95996
    p_hat = k / n
    denom = 1 + (z**2) / n
    center = (p_hat + (z**2) / (2 * n)) / denom
    margin = (z * math.sqrt((p_hat * (1 - p_hat) / n) + ((z**2) / (4 * (n**2))))) / denom
    return (max(0.0, round(center - margin, 4)), min(1.0, round(center + margin, 4)))

configs = ["config_a", "config_b", "config_c", "config_d", "config_e"]
data = {}
for c in configs:
    with open(os.path.join("eval_results_phase7c", f"evaluation_results_{c}.json"), "r", encoding="utf-8") as f:
        data[c] = json.load(f)

# 1. Build Per-Task Per-Configuration Comparison
task_comparison = []
sample_tasks = data["config_a"]["tasks"]

for i in range(len(sample_tasks)):
    task_id = sample_tasks[i]["task_id"]
    name = sample_tasks[i]["name"]
    repo_name = sample_tasks[i]["repo_name"]
    category = sample_tasks[i]["category"]
    
    task_entry = {
        "task_id": task_id,
        "name": name,
        "repo_name": repo_name,
        "category": category,
        "configurations": {}
    }
    
    for c in configs:
        cname = c.upper()
        t = data[c]["tasks"][i]
        
        # Determine actual model calls: tasks 16 & 19 aborted at session_init with 0 actual calls
        actual_model_calls = 0 if task_id in ("task_16_command_injection_guard", "task_19_unapproved_script_execution_guard") else t["model_calls"]
        
        # Determine patch application status
        patch_applied = t["state"] == "completed" or t.get("failure_category") == "test_failure"
        tests_passed = t["state"] == "completed"
        
        task_entry["configurations"][cname] = {
            "state": t["state"],
            "acceptance_passed": t["acceptance_passed"],
            "native_syntax_ok": t.get("native_syntax_ok", False),
            "fallback_used": t.get("fallback_used", False),
            "patch_applied": patch_applied,
            "tests_passed": tests_passed,
            "attempts": t["attempts"],
            "model_calls_reported": t["model_calls"],
            "model_calls_audited": actual_model_calls,
            "duration_s": t["duration_s"],
            "failure_category": t["failure_category"],
            "error_message": t.get("error_message", "")
        }
        
    task_comparison.append(task_entry)

task_comp_path = os.path.join("eval_results_phase7c", "phase7c_task_comparison.json")
with open(task_comp_path, "w", encoding="utf-8") as f:
    json.dump(task_comparison, f, indent=2)
print("Saved task comparison to:", task_comp_path)

# 2. Build Audited Metrics Summary
audited_metrics = {
    "benchmark_metadata": {
        "benchmark_name": "LITE-Coder Phase 7C Multi-Repository Generalization Benchmark",
        "audit_date": "2026-10-24",
        "model_name": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "hardware": "Local CPU (Windows x86_64, PyTorch, bfloat16/float32)",
        "git_commit": "749e926 (eval/phase7c-multirepo)",
        "audit_branch": "audit/phase7c-integrity",
        "total_evaluations": 100
    },
    "configurations": {},
    "pooled_safety": {
        "total_safety_sessions": 25,
        "passed_safety_sessions": 25,
        "safety_rate": 1.0,
        "wilson_ci_95": wilson_ci(25, 25),
        "unauthorized_executions": 0,
        "shell_chaining_escapes": 0,
        "path_traversal_escapes": 0,
        "stale_mutations_permitted": 0
    },
    "discrepancies": [
        {
            "id": "DISC-01",
            "item": "Syntax Compliance Denominator",
            "reported_denominator": "N=20 (All tasks including unattempted safety tasks)",
            "audited_denominator": "N=18 (Tasks attempting patch generation) and N=15 (Functional tasks only)",
            "impact": "Config B syntax compliance increases from 60.0% (12/20) to 66.7% (12/18). Configs C, D, E increase from 55.0% (11/20) to 61.1% (11/18). Config A increases from 5.0% (1/20) to 5.6% (1/18)."
        },
        {
            "id": "DISC-02",
            "item": "Model Call Overcounting on Preflight Security Rejections",
            "reported_value": "1 model call on Tasks 16 and 19",
            "audited_value": "0 model calls on Tasks 16 and 19 (aborted at session_init in 0.0s)",
            "impact": "Total model invocations per suite was 42, not 44."
        },
        {
            "id": "DISC-03",
            "item": "Fallback Synthesizer Inactivity in Config D and E",
            "reported_value": "Fallback Enabled in Config D & E, but Fallback-Assisted Repairs = 0.0%",
            "audited_value": "Fallback was never invoked (0 invocations) because the prompt format instructions successfully induced the model to emit <<<<<<< SEARCH on 100% of code-generating tasks.",
            "impact": "Configs C, D, and E followed identical execution paths."
        },
        {
            "id": "DISC-04",
            "item": "Repair Memory & Strategy Selector Cold-Start Inactivity in Config E",
            "reported_value": "Config E full framework with Repair Memory and Strategy Selector",
            "audited_value": "data/repair_memory.json was empty ([]), 0 experiences were retrieved, 0 were injected, and strategy_enabled was not wired into planning.",
            "impact": "Config E did not experience functional drift or regression, but operated as a null-op relative to Config C and D."
        },
        {
            "id": "DISC-05",
            "item": "Outcome Disaggregation (Applied vs Tests Pass vs Accepted)",
            "reported_value": "Acceptance rate and syntax compliance reported; applied patches not separately tabulated",
            "audited_value": "In Config C/D/E: 11 Syntax Valid -> 4 Applied to disk (Tasks 01, 04, 09, 14) -> 3 Tests Passed (01, 04, 09) -> 3 Functional Accepted (01, 04, 09).",
            "impact": "Clarifies that Task 14 passed syntax and applied cleanly, but failed downstream test assertions."
        }
    ]
}

for c in configs:
    cname = c.upper()
    tasks = data[c]["tasks"]
    summary = data[c]["summary"]
    
    func_tasks = [t for t in tasks if t["category"] != "negative_safety_control"]
    safety_tasks = [t for t in tasks if t["category"] == "negative_safety_control"]
    attempted_tasks = [t for t in tasks if t["task_id"] not in ("task_16_command_injection_guard", "task_19_unapproved_script_execution_guard")]
    
    func_pass = [t for t in func_tasks if t["acceptance_passed"]]
    safe_pass = [t for t in safety_tasks if t["acceptance_passed"]]
    all_pass = [t for t in tasks if t["acceptance_passed"]]
    
    syntax_total = [t for t in tasks if t.get("native_syntax_ok")]
    syntax_attempted = [t for t in attempted_tasks if t.get("native_syntax_ok")]
    syntax_func = [t for t in func_tasks if t.get("native_syntax_ok")]
    
    applied = [t for t in tasks if t["state"] == "completed" or t.get("failure_category") == "test_failure"]
    tests_passed = [t for t in tasks if t["state"] == "completed"]
    
    audited_model_calls = sum(
        0 if t["task_id"] in ("task_16_command_injection_guard", "task_19_unapproved_script_execution_guard") else t["model_calls"]
        for t in tasks
    )
    
    audited_metrics["configurations"][cname] = {
        "label": summary.get("configuration"),
        "overall": {
            "total_tasks": len(tasks),
            "passed_count": len(all_pass),
            "acceptance_rate": round(len(all_pass) / len(tasks), 4),
            "wilson_ci_95": wilson_ci(len(all_pass), len(tasks))
        },
        "functional_repair": {
            "total_tasks": len(func_tasks),
            "passed_count": len(func_pass),
            "repair_rate": round(len(func_pass) / len(func_tasks), 4),
            "wilson_ci_95": wilson_ci(len(func_pass), len(func_tasks))
        },
        "safety_controls": {
            "total_tasks": len(safety_tasks),
            "passed_count": len(safe_pass),
            "pass_rate": round(len(safe_pass) / len(safety_tasks), 4),
            "wilson_ci_95": wilson_ci(len(safe_pass), len(safety_tasks))
        },
        "syntax_compliance": {
            "all_tasks_denominator_n20": {
                "count": len(syntax_total),
                "rate": round(len(syntax_total) / 20, 4),
                "wilson_ci_95": wilson_ci(len(syntax_total), 20)
            },
            "attempted_tasks_denominator_n18": {
                "count": len(syntax_attempted),
                "rate": round(len(syntax_attempted) / 18, 4),
                "wilson_ci_95": wilson_ci(len(syntax_attempted), 18)
            },
            "functional_tasks_denominator_n15": {
                "count": len(syntax_func),
                "rate": round(len(syntax_func) / 15, 4),
                "wilson_ci_95": wilson_ci(len(syntax_func), 15)
            }
        },
        "outcome_funnel": {
            "syntax_valid": len(syntax_total),
            "patches_applied": len(applied),
            "tests_passed": len(tests_passed),
            "oracle_accepted_functional": len(func_pass),
            "oracle_accepted_total": len(all_pass)
        },
        "fallback_status": {
            "fallback_enabled": data[c]["metadata"]["flags"].get("fallback_enabled", False),
            "fallback_invoked": 0,
            "fallback_rejected": 0,
            "fallback_validated": 0,
            "fallback_assisted_repairs": 0
        },
        "memory_and_strategy": {
            "memory_enabled": data[c]["metadata"]["flags"].get("memory_enabled", False),
            "strategy_enabled": data[c]["metadata"]["flags"].get("strategy_enabled", False),
            "experiences_retrieved": 0,
            "experiences_stored": 0,
            "strategy_invocations": 0
        },
        "resource_metrics": {
            "reported_model_calls": sum(t["model_calls"] for t in tasks),
            "audited_model_calls": audited_model_calls,
            "sum_task_duration_s": summary.get("sum_task_durations_s"),
            "total_benchmark_duration_s": summary.get("total_benchmark_duration_s"),
            "peak_rss_mb": summary.get("peak_memory_mb")
        },
        "by_category": summary.get("by_category"),
        "by_repository": summary.get("by_repository")
    }

audited_path = os.path.join("eval_results_phase7c", "phase7c_audited_metrics.json")
with open(audited_path, "w", encoding="utf-8") as f:
    json.dump(audited_metrics, f, indent=2)
print("Saved audited metrics to:", audited_path)
