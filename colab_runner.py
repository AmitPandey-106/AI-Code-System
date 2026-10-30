"""
colab_runner.py
===============
One-shot Google Colab GPU Benchmark Runner for LITE-Coder Q1 Journal Evaluation.
Runs all 100 tasks across:
- Mode 1: Zero-Shot (pass@1)
- Mode 2: Naive Iterative Repair (Raw traceback feedback)
- Mode 3: LITE-Coder Full Architecture (Contract + AST shield + isolated runner)
- Mode 4: Negative Controls (Adversarial oracle defense)

Optimized for NVIDIA T4 / V100 / A100 GPU (fp16).
Outputs:
- experiments/q1_results/q1_results_master.json
- experiments/q1_results/Q1_EVALUATION_REPORT.md
- Automatically packages q1_results.zip for 1-click download in Colab!
"""

import sys
import os
import time
import json
import zipfile
from typing import Dict, Any, List, Optional

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch
from benchmarks.q1_benchmark.runner import (
    evaluate_zero_shot,
    evaluate_naive_repair,
    evaluate_lite_coder,
    evaluate_negative_controls,
    generate_q1_markdown_report
)
from benchmarks.q1_benchmark.tasks import EVALUATION_TASKS, NEGATIVE_CONTROLS
from app.model import get_model


def run_colab_evaluation(output_dir: str = "experiments/q1_results"):
    print("=" * 75)
    print("  LITE-CODER: Q1 JOURNAL BENCHMARK EVALUATION (100 TASKS)")
    print(f"  CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"  VRAM: {round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)} GB")
    else:
        print("  Running on CPU (GPU recommended for maximum speed)")
    print("=" * 75)

    os.makedirs(output_dir, exist_ok=True)
    results_path = os.path.join(output_dir, "q1_results_master.json")
    report_path = os.path.join(output_dir, "Q1_EVALUATION_REPORT.md")

    # Warm-up model on GPU
    print("\n[+] Loading model into GPU memory (float16)...")
    model, tokenizer = get_model()
    print("[+] Model loaded successfully!\n")

    eval_tasks = EVALUATION_TASKS
    total_eval = len(eval_tasks)

    task_results = []
    domain_stats: Dict[str, Dict[str, Any]] = {}

    start_time = time.time()

    for idx, task in enumerate(eval_tasks, 1):
        t_id = task["task_id"]
        t_name = task["task_name"]
        dom = task["domain"]

        if dom not in domain_stats:
            domain_stats[dom] = {"count": 0, "zero_shot": 0, "naive": 0, "lite_coder": 0, "ast_caught": 0}
        domain_stats[dom]["count"] += 1

        t_start = time.time()

        # Mode 1: Zero-Shot
        z_res = evaluate_zero_shot(task)
        if z_res["passed"]: domain_stats[dom]["zero_shot"] += 1

        # Mode 2: Naive Iterative Repair
        n_res = evaluate_naive_repair(task, max_attempts=3)
        if n_res["passed"]: domain_stats[dom]["naive"] += 1

        # Mode 3: LITE-Coder Full Architecture
        l_res = evaluate_lite_coder(task, max_attempts=3)
        if l_res["passed"]: domain_stats[dom]["lite_coder"] += 1
        domain_stats[dom]["ast_caught"] += l_res["ast_violations_caught"]

        elapsed_task = round(time.time() - t_start, 1)

        print(f"[{idx:02d}/{total_eval}] {t_id:<12} [{t_name:<28}] ({elapsed_task}s) | "
              f"Zero-Shot: {'PASS' if z_res['passed'] else 'FAIL'} | "
              f"Naive: {'PASS' if n_res['passed'] else 'FAIL'} (att: {n_res['attempts']}) | "
              f"LITE-Coder: {'PASS' if l_res['passed'] else 'FAIL'} (att: {l_res['attempts']}, AST: {l_res['ast_violations_caught']})")

        task_results.append({
            "task_id": t_id,
            "task_name": t_name,
            "domain": dom,
            "difficulty": task.get("difficulty", "MEDIUM"),
            "zero_shot": z_res,
            "naive_repair": n_res,
            "lite_coder": l_res
        })

        # Save checkpoint every 5 tasks
        if idx % 5 == 0 or idx == total_eval:
            with open(os.path.join(output_dir, "checkpoint.json"), "w", encoding="utf-8") as f:
                json.dump({"completed": idx, "results": task_results}, f, indent=2)

    # Mode 4: Negative Controls
    print("\n" + "=" * 70)
    print("RUNNING MODE 4: ADVERSARIAL ORACLE DEFENSE (NEGATIVE CONTROLS)")
    print("=" * 70)
    neg_results = evaluate_negative_controls()
    isolated_count = sum(1 for r in neg_results if r["isolated_successfully"])
    print(f"\n[+] Negative Controls: {isolated_count}/{len(neg_results)} Adversarial Oracles Successfully Isolated.")

    total_time = round(time.time() - start_time, 2)

    summary_stats = {
        "total_eval_tasks": total_eval,
        "zero_shot_passed": sum(1 for r in task_results if r["zero_shot"]["passed"]),
        "naive_passed": sum(1 for r in task_results if r["naive_repair"]["passed"]),
        "lite_coder_passed": sum(1 for r in task_results if r["lite_coder"]["passed"]),
        "total_ast_violations_caught": sum(r["lite_coder"]["ast_violations_caught"] for r in task_results),
        "execution_time_seconds": total_time
    }

    neg_stats = {
        "total_negative_controls": len(neg_results),
        "isolated_count": isolated_count,
        "controls": neg_results
    }

    master_payload = {
        "metadata": {
            "title": "LITE-Coder Q1 Benchmark Evaluation",
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tasks": total_eval + len(neg_results),
            "total_duration_minutes": round(total_time / 60, 2)
        },
        "summary": summary_stats,
        "negative_controls_summary": neg_stats,
        "domain_breakdown": domain_stats,
        "task_results": task_results
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(master_payload, f, indent=2)

    generate_q1_markdown_report(summary_stats, domain_stats, neg_stats, report_path)

    # Package output files into q1_results.zip
    zip_path = "q1_results.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, ".")
                zipf.write(full_p, rel_p)

    print("\n" + "=" * 75)
    print(f"  [SUCCESS] 100-Task Q1 Benchmark Evaluation Completed in {round(total_time/60, 1)} minutes!")
    print(f"  [+] Master Results: {results_path}")
    print(f"  [+] LaTeX & Markdown Report: {report_path}")
    print(f"  [+] Downloadable Bundle: {zip_path}")
    print("=" * 75)


if __name__ == "__main__":
    run_colab_evaluation()
