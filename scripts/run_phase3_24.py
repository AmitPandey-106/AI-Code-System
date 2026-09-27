#!/usr/bin/env python3
"""
scripts/run_phase3_24.py
========================
Execution wrapper for LITE-CODER Phase 3:
Targeted 24-Task MODE-A Rerun on Google Colab GPU.

This script runs ONLY the 24 tasks that were previously affected by the
TypeError bookkeeping bug in the original MODE-A benchmark run.
Evaluation semantics, generation parameters, and scoring logic are 100% identical
to the official benchmark runner.

Output directory: experiments/LITE_CODER_24TASK_POST_FIX_A_RERUN/
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import benchmark.runner as runner_mod
from benchmark.dataset import load_dataset

# Authoritative 24 tasks from original MODE-A forensic backup
TARGET_24_TASK_IDS = [
    "TASK_1E88EF5E", "TASK_FB475E1F", "TASK_527A01D3", "TASK_1AC7E084",
    "TASK_55A55247", "TASK_7C30D0A1", "TASK_761B7D7E", "TASK_96161F4B",
    "TASK_492A6DB5", "TASK_BC89315E", "TASK_435DA3AE", "TASK_E86381A6",
    "TASK_50B0F89F", "TASK_34E90ED9", "TASK_61DE3671", "TASK_61ECFD6A",
    "TASK_495776C1", "TASK_8FC95909", "TASK_71B9E063", "TASK_2A60D1B1",
    "TASK_64497C8C", "TASK_52F6CB07", "TASK_3CA90906", "TASK_0DB97680"
]

EXPERIMENT_ID = "LITE_CODER_24TASK_POST_FIX_A_RERUN"
MODE = "MODE_A"
DATASET_PATH = "data/benchmark/v1.0/dataset.json"

def main():
    print("=" * 65)
    print("LITE-CODER PHASE 3: 24-TASK TARGETED MODE-A RERUN")
    print(f"Experiment ID: {EXPERIMENT_ID}")
    print(f"Mode:          {MODE}")
    print(f"Dataset:       {DATASET_PATH}")
    print(f"Tasks:         {len(TARGET_24_TASK_IDS)} target tasks")
    print("=" * 65)

    # Filter load_dataset to only the target 24 tasks, preserving original order
    original_load = runner_mod.load_dataset

    def load_target_24(dataset_path=None):
        all_tasks = original_load(dataset_path if dataset_path else DATASET_PATH)
        task_map = {t.task_id: t for t in all_tasks}
        filtered = [task_map[tid] for tid in TARGET_24_TASK_IDS if tid in task_map]
        if len(filtered) != len(TARGET_24_TASK_IDS):
            missing = set(TARGET_24_TASK_IDS) - set(task_map.keys())
            raise RuntimeError(f"Could not find all 24 tasks in dataset. Missing: {missing}")
        return filtered

    runner_mod.load_dataset = load_target_24

    results = runner_mod.run_benchmark(
        experiment_id=EXPERIMENT_ID,
        mode=MODE,
        size=len(TARGET_24_TASK_IDS),
        dataset_path=DATASET_PATH
    )

    print("\n" + "=" * 65)
    print("PHASE 3 RERUN COMPLETE")
    print(f"Total tasks processed: {len(results)}")
    successes = sum(1 for r in results if r.success is True)
    infra_fails = sum(1 for r in results if r.status == "infrastructure_failure")
    model_fails = sum(1 for r in results if r.status == "model_failure")
    print(f"Model Successes:        {successes}/{len(results)}")
    print(f"Infrastructure Fails:   {infra_fails}/{len(results)}")
    print(f"Model Fails:            {model_fails}/{len(results)}")
    print(f"Results saved to:       experiments/{EXPERIMENT_ID}/")
    print("=" * 65)

if __name__ == "__main__":
    main()
