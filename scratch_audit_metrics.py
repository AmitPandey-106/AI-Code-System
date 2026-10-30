import json
import os
import sys

def audit_configs():
    files = {
        "Config A": "eval_results_phase6/evaluation_results_instruct.json",
        "Config B": "eval_results_phase7b/evaluation_results_prompt_only.json",
        "Config C": "eval_results_phase7b/evaluation_results_prompt_plus_fallback.json"
    }

    data = {}
    for name, path in files.items():
        with open(path, "r", encoding="utf-8") as f:
            data[name] = json.load(f)

    print("=" * 80)
    print("PHASE 7B EVIDENCE AUDIT: RAW DATA METRICS RECALCULATION")
    print("=" * 80)

    functional_task_ids = {
        "repo_task_01_cross_file_symbol",
        "repo_task_02_single_file_bugfix",
        "repo_task_03_multi_file_changes",
        "repo_task_04_regression_sensitive",
        "repo_task_05_initially_failing_tests"
    }
    safety_task_ids = {
        "repo_task_06_unapproved_command_stop",
        "repo_task_07_unsatisfiable_safety_stop"
    }

    recalculated = {}

    for name, root in data.items():
        print(f"\n--- {name} ({files[name]}) ---")
        meta = root.get("metadata", {})
        print(f"Model: {meta.get('model_name')}")
        print(f"Timestamp: {meta.get('timestamp')}")
        print(f"Fallback: {meta.get('fallback_synthesizer_enabled')}, EagerPolicy: {meta.get('eager_policy_check_enabled')}")

        tasks = root["tasks"]["engineering_loop"]
        summary = root.get("summary", {}).get("engineering_loop", {})

        print(f"\nTotal tasks in JSON: {len(tasks)}")
        
        # Recalculate metrics
        total_tasks = len(tasks)
        func_tasks = [t for t in tasks if t["task_id"] in functional_task_ids]
        safe_tasks = [t for t in tasks if t["task_id"] in safety_task_ids]

        func_passed = [t for t in func_tasks if t["acceptance_passed"]]
        safe_passed = [t for t in safe_tasks if t["acceptance_passed"]]
        overall_passed = [t for t in tasks if t["acceptance_passed"]]

        safe_stop_compliant = [t for t in tasks if t.get("safe_stop_compliant", True)]
        
        # Syntax compliance
        # Definition 1 (eval_runner script logic): failure_category != 'malformed_patch_syntax'
        eval_runner_syntax_ok = [t for t in tasks if t.get("failure_category") != "malformed_patch_syntax"]
        # Definition 2 (strict patch generated & applied successfully)
        # Note: task 06 never produces a patch (eager stop or security stop), task 07 produces test failures
        strictly_applied_patches = [t for t in tasks if t["state"] == "completed"]

        regressions = [t for t in tasks if t.get("regression_detected", False)]

        attempts_list = [t["attempts"] for t in tasks]
        durations_list = [t["duration_s"] for t in tasks]
        peak_mems = [t.get("peak_memory_mb", 0.0) for t in tasks]

        avg_attempts = sum(attempts_list) / total_tasks
        sum_durations = sum(durations_list)
        avg_duration = sum_durations / total_tasks
        max_peak_mem = max(peak_mems)

        recalculated[name] = {
            "metadata": meta,
            "total_tasks": total_tasks,
            "overall_accepted": len(overall_passed),
            "overall_acceptance_rate": round(len(overall_passed) / total_tasks, 4),
            "functional_total": len(func_tasks),
            "functional_passed": len(func_passed),
            "functional_repair_rate": round(len(func_passed) / len(func_tasks), 4),
            "safety_total": len(safe_tasks),
            "safety_passed": len(safe_passed),
            "safety_pass_rate": round(len(safe_passed) / len(safe_tasks), 4),
            "safe_stop_compliant_count": len(safe_stop_compliant),
            "safe_stop_compliance_rate": round(len(safe_stop_compliant) / total_tasks, 4),
            "eval_runner_syntax_ok_count": len(eval_runner_syntax_ok),
            "eval_runner_syntax_ok_rate": round(len(eval_runner_syntax_ok) / total_tasks, 4),
            "strictly_applied_patches_count": len(strictly_applied_patches),
            "strictly_applied_patches_rate": round(len(strictly_applied_patches) / total_tasks, 4),
            "regressions_detected": len(regressions),
            "average_attempts": round(avg_attempts, 2),
            "sum_task_durations_s": round(sum_durations, 2),
            "average_duration_s": round(avg_duration, 2),
            "reported_total_duration_s": summary.get("total_duration_s"),
            "reported_average_duration_s": summary.get("average_duration_s"),
            "reported_acceptance_rate": summary.get("acceptance_pass_rate"),
            "reported_syntax_rate": summary.get("syntax_compliance_rate"),
            "peak_memory_mb": round(max_peak_mem, 1)
        }

        print("Task breakdown:")
        for t in tasks:
            print(f"  [{t['task_id']}] state={t['state']}, passed={t['acceptance_passed']}, attempts={t['attempts']}, duration={t['duration_s']}s, category={t.get('failure_category')}")
            if t.get("policy_event"):
                print(f"    policy_event={t['policy_event']['stage']}:{t['policy_event']['status']}")

    print("\n" + "=" * 80)
    print("COMPARATIVE RECALCULATION TABLE")
    print("=" * 80)
    print(f"{'Metric':<35} | {'Config A':<15} | {'Config B':<15} | {'Config C':<15}")
    print("-" * 86)
    keys = [
        ("Total Tasks", "total_tasks"),
        ("Overall Accepted (7 tasks)", "overall_accepted"),
        ("Overall Acceptance Rate", "overall_acceptance_rate"),
        ("Functional Repaired (5 tasks)", "functional_passed"),
        ("Functional Repair Rate (N=5)", "functional_repair_rate"),
        ("Safety Stops Passed (N=2)", "safety_passed"),
        ("Safety Stop Rate (N=2)", "safety_pass_rate"),
        ("Safe Stop Compliant (N=7)", "safe_stop_compliant_count"),
        ("Syntax OK (eval_runner def)", "eval_runner_syntax_ok_count"),
        ("Syntax OK Rate (eval_runner)", "eval_runner_syntax_ok_rate"),
        ("Strictly Applied Patches", "strictly_applied_patches_count"),
        ("Strictly Applied Patch Rate", "strictly_applied_patches_rate"),
        ("Average Attempts", "average_attempts"),
        ("Sum Task Durations (s)", "sum_task_durations_s"),
        ("Average Task Duration (s)", "average_duration_s"),
        ("Peak Resident RAM (MB)", "peak_memory_mb"),
        ("Regressions Detected", "regressions_detected")
    ]
    for label, k in keys:
        va = recalculated["Config A"][k]
        vb = recalculated["Config B"][k]
        vc = recalculated["Config C"][k]
        print(f"{label:<35} | {str(va):<15} | {str(vb):<15} | {str(vc):<15}")

    # Output detailed task comparison
    print("\n" + "=" * 80)
    print("TASK DURATION COMPARISON (A vs B vs C)")
    print("=" * 80)
    print(f"{'Task ID':<35} | {'Config A (s)':<12} | {'Config B (s)':<12} | {'Config C (s)':<12}")
    print("-" * 80)
    for i in range(len(data["Config A"]["tasks"]["engineering_loop"])):
        ta = data["Config A"]["tasks"]["engineering_loop"][i]
        tb = data["Config B"]["tasks"]["engineering_loop"][i]
        tc = data["Config C"]["tasks"]["engineering_loop"][i]
        print(f"{ta['task_id']:<35} | {ta['duration_s']:<12.2f} | {tb['duration_s']:<12.2f} | {tc['duration_s']:<12.2f}")

    # Write recalculations to json
    with open("eval_results_phase7b/phase7b_audited_metrics.json", "w", encoding="utf-8") as f:
        json.dump(recalculated, f, indent=2)
    print("\nWrote audited metrics to eval_results_phase7b/phase7b_audited_metrics.json")

if __name__ == "__main__":
    audit_configs()
