"""
benchmark/run_experiment.py
============================
Clean CLI entry point for running LITE-CODER benchmark experiments.

Enforces:
- Pre-run manifest creation
- Dataset SHA256 verification
- New experiment IDs only (no overwriting)
- Post-run forensic audit

Usage:
    python -m benchmark.run_experiment \\
        --mode MODE_A \\
        --experiment-id LITE_CODER_100TASK_MODE_A_V2 \\
        --dataset data/benchmark/v1.0/dataset.json \\
        [--size 5]
"""

import os
import sys
import json
import time
import argparse
import hashlib

# =========================================================
# KNOWN FROZEN DATASET HASHES
# The SHA256 of data/benchmark/v1.0/dataset.json as validated
# against the original 100-task experiment backup.
#
# NOTE: The backup's recorded SHA256 was 7f7ff7305431... (Colab version).
# The local copy at data/benchmark/v1.0/dataset.json has SHA256 2bd5075...
# These differ — the local file may have been modified after the original run.
# A new clean baseline will be tied to the LOCAL file's hash.
# =========================================================

KNOWN_DATASET_HASHES = {
    "7f7ff7305431cc66e8ee327a3c209b788d84818a9651789d70a56653376c47f6": "original_colab_100task",
    "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620": "local_100task_v1.0",
}


def get_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="LITE-CODER clean experiment runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", required=True,
                        choices=["MODE_A", "MODE_B", "MODE_C", "MODE_D", "MODE_E", "MODE_F"],
                        help="Ablation mode")
    parser.add_argument("--experiment-id", required=True,
                        help="Unique experiment ID. Must not already exist.")
    parser.add_argument("--dataset", default="data/benchmark/v1.0/dataset.json",
                        help="Dataset path")
    parser.add_argument("--size", type=int, default=None,
                        help="Number of tasks (None = all)")
    parser.add_argument("--no-audit", action="store_true",
                        help="Skip post-run forensic audit")
    parser.add_argument("--audit-output", default=None,
                        help="Output dir for forensic audit (defaults to experiment dir)")
    args = parser.parse_args()

    experiment_id = args.experiment_id
    experiment_dir = f"experiments/{experiment_id}"

    # ---- Guard: refuse to overwrite existing experiments ----
    if os.path.exists(experiment_dir):
        print(f"\nERROR: Experiment directory already exists: {experiment_dir}")
        print("       Create a new experiment ID for each run.")
        sys.exit(1)

    # ---- Verify dataset ----
    if not os.path.exists(args.dataset):
        print(f"\nERROR: Dataset not found: {args.dataset}")
        sys.exit(1)

    dataset_hash = get_sha256(args.dataset)
    print(f"\n[INFO] Dataset: {args.dataset}")
    print(f"[INFO] Dataset SHA256: {dataset_hash}")

    known_name = KNOWN_DATASET_HASHES.get(dataset_hash)
    if known_name:
        print(f"[INFO] Known dataset version: {known_name}")
    else:
        print(f"[WARNING] Dataset hash is not in the known-hash registry.")
        print(f"          This is acceptable for new experiments, but confirm intentional.")

    import json
    with open(args.dataset, "r") as f:
        tasks = json.load(f)
    print(f"[INFO] Total tasks in dataset: {len(tasks)}")

    size_str = str(args.size) if args.size else "ALL"
    print(f"\n{'='*60}")
    print(f"  EXPERIMENT: {experiment_id}")
    print(f"  MODE:       {args.mode}")
    print(f"  DATASET:    {args.dataset} ({len(tasks)} tasks, SHA256: {dataset_hash[:12]}...)")
    print(f"  TASK SIZE:  {size_str}")
    print(f"  SEED:       42 (fixed by ablation mode)")
    print(f"{'='*60}\n")

    # ---- Run benchmark ----
    from benchmark.runner import run_benchmark
    from benchmark.metrics import calculate_metrics

    start_time = time.time()
    results = run_benchmark(
        experiment_id=experiment_id,
        mode=args.mode,
        size=args.size,
        dataset_path=args.dataset
    )
    total_time = time.time() - start_time

    # ---- Compute and save metrics ----
    dataset_size = args.size if args.size else len(tasks)
    metrics = calculate_metrics(results, dataset_size)
    metrics["total_runtime_seconds"] = round(total_time, 2)
    metrics["experiment_id"] = experiment_id
    metrics["mode"] = args.mode

    metrics_path = f"{experiment_dir}/metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT COMPLETE: {experiment_id}")
    print(f"  Total tasks     : {metrics['completed_tasks']}")
    print(f"  Successes       : {metrics['successful_repairs']}")
    print(f"  Model failures  : {metrics['repair_failures']}")
    print(f"  Infra errors    : {metrics['infrastructure_errors']}")
    print(f"  Success rate    : {metrics['success_rate']*100:.2f}%")
    print(f"  Total runtime   : {total_time:.1f}s")
    print(f"  Is complete run : {metrics['is_complete_run']}")
    print(f"  All resolved    : {metrics['infrastructure_errors'] == 0 and metrics['completed_tasks'] == dataset_size}")
    print(f"{'='*60}\n")

    # ---- Post-run forensic audit ----
    if not args.no_audit:
        print("[INFO] Running post-experiment forensic audit...")
        try:
            sys.path.insert(0, os.path.abspath("."))
            from research.audit.forensic_audit import run_audit
            audit_output = args.audit_output or experiment_dir
            run_audit(experiment_dir, dataset_path=args.dataset, output_dir=audit_output)
        except Exception as e:
            print(f"[WARNING] Forensic audit failed: {e}")
            print("          Run manually: python research/audit/forensic_audit.py " + experiment_dir)

    print(f"\n[DONE] Results in: {experiment_dir}")
    print(f"[DONE] Command to audit: python research/audit/forensic_audit.py {experiment_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
