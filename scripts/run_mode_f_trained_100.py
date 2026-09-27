#!/usr/bin/env python3
"""
scripts/run_mode_f_trained_100.py
=================================
Execution wrapper for LITE-CODER 100-Task MODE-F Trained Benchmark Run.

This script executes the complete 100-task benchmark in MODE-F
(Full LITE-CODER: Memory ON + Adaptive Strategy Learning ON + Active LoRA Continual Training ON):
- Dataset: data/benchmark/v1.0/dataset.json (100 tasks, SHA256: 2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620)
- Mode: MODE_F
- Base Model: Qwen/Qwen2.5-Coder-1.5B (Active LoRA adapter online updates)
- Output directory: experiments/LITE_CODER_100TASK_MODE_F_TRAINED/
"""

import sys
import os
import time
import json
import hashlib

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import benchmark.runner as runner_mod
from benchmark.metrics import calculate_metrics

EXPERIMENT_ID = "LITE_CODER_100TASK_MODE_F_TRAINED"
MODE = "MODE_F"
DATASET_PATH = "data/benchmark/v1.0/dataset.json"
EXPECTED_DATASET_SHA256 = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"

def main():
    print("=" * 65)
    print("LITE-CODER: FULL 100-TASK MODE-F TRAINED BENCHMARK RUN")
    print(f"Experiment ID: {EXPERIMENT_ID}")
    print(f"Mode:          {MODE}")
    print(f"Dataset:       {DATASET_PATH}")
    print("=" * 65)

    # 1. Dataset verification
    abs_ds_path = os.path.join(PROJECT_ROOT, DATASET_PATH)
    if not os.path.exists(abs_ds_path):
        raise FileNotFoundError(f"Dataset not found at {abs_ds_path}")

    with open(abs_ds_path, "rb") as f:
        ds_hash = hashlib.sha256(f.read()).hexdigest()

    print(f"[INFO] Dataset SHA256: {ds_hash}")
    if ds_hash.lower() != EXPECTED_DATASET_SHA256.lower():
        raise ValueError(f"Dataset SHA256 mismatch! Expected {EXPECTED_DATASET_SHA256}, got {ds_hash}")

    with open(abs_ds_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    print(f"[INFO] Total tasks: {len(tasks)}")
    if len(tasks) != 100:
        raise ValueError(f"Expected 100 tasks, but found {len(tasks)}")

    # 2. Output directory check
    exp_dir = os.path.join(PROJECT_ROOT, "experiments", EXPERIMENT_ID)
    if os.path.exists(exp_dir):
        print(f"[WARNING] Experiment directory already exists: {exp_dir}")
        print("          Existing files will be inspected/resumed as per runner protocol.")

    # 3. Execute benchmark
    start_time = time.time()
    results = runner_mod.run_benchmark(
        experiment_id=EXPERIMENT_ID,
        mode=MODE,
        size=len(tasks),
        dataset_path=DATASET_PATH
    )
    total_time = time.time() - start_time

    # 4. Metrics calculation
    metrics = calculate_metrics(results, len(tasks))
    metrics["total_runtime_seconds"] = round(total_time, 2)
    metrics["experiment_id"] = EXPERIMENT_ID
    metrics["mode"] = MODE

    # Copy training history directly to experiment directory if exists
    training_hist_src = "models/adapters/training_history.json"
    if os.path.exists(training_hist_src):
        import shutil
        shutil.copy2(training_hist_src, os.path.join(exp_dir, "training_history.json"))

    metrics_path = os.path.join(exp_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)

    print("\n" + "=" * 65)
    print("100-TASK MODE-F TRAINED RUN COMPLETE")
    print(f"Total tasks processed: {metrics.get('completed_tasks')}")
    print(f"Successes:              {metrics.get('successful_repairs')}")
    print(f"Model failures:         {metrics.get('repair_failures')}")
    print(f"Infrastructure errors:  {metrics.get('infrastructure_errors')}")
    print(f"Success rate:           {metrics.get('success_rate', 0)*100:.2f}%")
    print(f"Total runtime:          {total_time:.1f}s")
    print(f"Complete run:           {metrics.get('is_complete_run')}")
    print(f"Results directory:      experiments/{EXPERIMENT_ID}/")
    print("=" * 65)

if __name__ == "__main__":
    main()
