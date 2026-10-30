"""
benchmark/runner.py
====================
LITE-CODER experiment runner.

RESEARCH INTEGRITY RULES enforced here:
- Every task MUST produce a complete record regardless of outcome.
- Infrastructure exceptions MUST be distinguishable from model failures.
- Full traceback is captured and persisted on every exception.
- Atomic checkpoint writes prevent partial checkpoint corruption.
- Duplicate task IDs are rejected (FileExistsError on raw task files).
- Dataset SHA256 is verified on resume.
- New experiments MUST use new experiment IDs / directories.
"""

import os
import json
import time
import shutil
import hashlib
import platform
import traceback as tb_module
from typing import List, Optional
from benchmark.schemas import BenchmarkResult
from benchmark.dataset import load_dataset
from benchmark.ablation import apply_ablation_mode
from app.main import generate, Request
from app.config import config

STATE_FILES = [
    "data/repair_memory.json",
    "data/repair_memory_index.faiss",
    "data/strategy_stats.json"
]


# =========================================================
# UTILITIES
# =========================================================

def get_dataset_hash(dataset_path: str) -> str:
    if not os.path.exists(dataset_path):
        return ""
    with open(dataset_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def save_experiment_manifest(experiment_dir: str, mode: str, dataset_path: str, task_count: int, dataset_hash: str):
    import psutil
    import torch
    import transformers

    peft_version = None
    try:
        import peft
        peft_version = peft.__version__
    except ImportError:
        pass

    st_version = None
    try:
        import sentence_transformers
        st_version = sentence_transformers.__version__
    except ImportError:
        pass

    faiss_version = None
    try:
        import faiss
        faiss_version = faiss.__version__
    except ImportError:
        pass

    hw_info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "cpu": platform.processor(),
        "python": platform.python_version(),
        "pytorch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "peft_version": peft_version,
        "sentence_transformers_version": st_version,
        "faiss_version": faiss_version
    }

    manifest = {
        "experiment_id": os.path.basename(experiment_dir),
        "mode": mode,
        "dataset_path": dataset_path,
        "dataset_sha256": dataset_hash,
        "benchmark_size": task_count,
        "task_count": task_count,
        "benchmark_seed": config.get("BENCHMARK_SEED", 42),
        "deterministic_generation": config.get("DETERMINISTIC_GENERATION", False),
        "model_name": "Qwen/Qwen2.5-Coder-1.5B",
        "lora_enabled": config.get("LORA_ENABLED", False),
        "lora_buffer_size": config.get("LORA_BUFFER_SIZE", 4),
        "lora_epochs": config.get("LORA_EPOCHS", 3),
        "lora_learning_rate": config.get("LORA_LEARNING_RATE", 2e-4),
        "lora_rank": config.get("LORA_RANK", 8),
        "lora_alpha": config.get("LORA_ALPHA", 16),
        "memory_enabled": config.get("MEMORY_ENABLED", False),
        "strategy_learning_enabled": config.get("STRATEGY_LEARNING_ENABLED", False),
        "difficulty_allocation_enabled": config.get("DIFFICULTY_ALLOCATION_ENABLED", False),
        "max_retries": 5,
        "timestamp": time.time(),
        "hardware": hw_info,
        "full_config": config.config
    }

    os.makedirs(experiment_dir, exist_ok=True)
    with open(f"{experiment_dir}/experiment_manifest.json", "w") as f:
        json.dump(manifest, f, indent=4)


def snapshot_experiment_state(experiment_dir: str):
    snapshot_dir = os.path.join(experiment_dir, "state_snapshot")
    os.makedirs(snapshot_dir, exist_ok=True)
    for file_path in STATE_FILES:
        if os.path.exists(file_path):
            shutil.copy2(file_path, snapshot_dir)

    adapter_src = "models/adapters"
    adapter_dst = os.path.join(snapshot_dir, "adapters")
    if os.path.exists(adapter_src):
        if os.path.exists(adapter_dst):
            shutil.rmtree(adapter_dst)
        shutil.copytree(adapter_src, adapter_dst)


def restore_experiment_state(experiment_dir: str):
    snapshot_dir = os.path.join(experiment_dir, "state_snapshot")
    if not os.path.exists(snapshot_dir):
        raise RuntimeError(
            f"Checkpoint exists but state snapshot is missing at {snapshot_dir}. "
            "Exact resume cannot be guaranteed."
        )

    for file_path in STATE_FILES:
        basename = os.path.basename(file_path)
        snapshot_file = os.path.join(snapshot_dir, basename)
        if os.path.exists(snapshot_file):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            shutil.copy2(snapshot_file, file_path)

    adapter_src = os.path.join(snapshot_dir, "adapters")
    adapter_dst = "models/adapters"
    if os.path.exists(adapter_src):
        if os.path.exists(adapter_dst):
            shutil.rmtree(adapter_dst)
        shutil.copytree(adapter_src, adapter_dst)


def reset_state():
    """Safely clear memory, strategy, and adapter states for isolated experiments."""
    if os.path.exists("data/strategy_memory.json"):
        with open("data/strategy_memory.json", "w") as f:
            json.dump([], f)
    if os.path.exists("data/strategy_stats.json"):
        with open("data/strategy_stats.json", "w") as f:
            json.dump({}, f)

    from app.repair_memory import repair_memory
    from app.strategy_selector import strategy_selector

    repair_memory.index.reset()
    repair_memory.memories = []
    repair_memory._save()

    strategy_selector.reset()

    ACTIVE_ADAPTER_PATH = "models/adapters/active"
    if os.path.exists(ACTIVE_ADAPTER_PATH):
        shutil.rmtree(ACTIVE_ADAPTER_PATH)

    CANDIDATES_PATH = "models/adapters/candidates"
    if os.path.exists(CANDIDATES_PATH):
        shutil.rmtree(CANDIDATES_PATH)

    TRAINING_STATE_FILE = "models/adapters/training_state.json"
    if os.path.exists(TRAINING_STATE_FILE):
        os.remove(TRAINING_STATE_FILE)

    TRAINING_HISTORY_FILE = "models/adapters/training_history.json"
    if os.path.exists(TRAINING_HISTORY_FILE):
        os.remove(TRAINING_HISTORY_FILE)

    from app.model import reload_model
    reload_model()


# =========================================================
# ERROR DIAGNOSTIC BUILDER
# =========================================================

def build_error_diagnostic(exc: Exception, stage: str, task_id: str, experiment_id: str, elapsed_ms: int) -> dict:
    """
    Builds a complete, structured error diagnostic record from an exception.
    This is the authoritative record for any task that failed due to a
    runner/infrastructure exception rather than a model decision.
    
    Classification:
      error_category = "runner"        → exception inside the benchmark runner itself
      status         = "infrastructure_failure"
    """
    return {
        "error_category": "runner",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "error_stage": stage,
        "exception_class": type(exc).__qualname__,
        "traceback": tb_module.format_exc(),
        "task_id": task_id,
        "experiment_id": experiment_id,
        "elapsed_ms": elapsed_ms,
        "timestamp": time.time()
    }


# =========================================================
# MAIN BENCHMARK RUNNER
# =========================================================

def run_benchmark(experiment_id: str, mode: str, size: int = None, dataset_path: str = None) -> List[BenchmarkResult]:
    apply_ablation_mode(mode)
    reset_state()

    tasks = load_dataset(dataset_path) if dataset_path else load_dataset()
    if size is not None:
        tasks = tasks[:size]

    actual_dataset_path = dataset_path if dataset_path else "data/benchmark/dataset.json"
    dataset_hash = get_dataset_hash(actual_dataset_path)

    results = []
    experiment_dir = f"experiments/{experiment_id}"
    checkpoint_path = f"{experiment_dir}/checkpoint.json"
    manifest_path = f"{experiment_dir}/experiment_manifest.json"

    os.makedirs(experiment_dir, exist_ok=True)

    # ----------------------------------------------------------
    # RESUME FROM CHECKPOINT
    # ----------------------------------------------------------
    completed_task_ids = set()
    if os.path.exists(checkpoint_path):
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
                if manifest.get("dataset_sha256") and manifest.get("dataset_sha256") != dataset_hash:
                    raise ValueError(
                        f"Dataset identity mismatch: "
                        f"Expected {manifest.get('dataset_sha256')}, found {dataset_hash}"
                    )

        with open(checkpoint_path, "r") as f:
            saved_results = json.load(f)

        if saved_results:
            checkpoint_mode = saved_results[0].get("mode")
            if checkpoint_mode and checkpoint_mode != mode:
                raise ValueError(
                    f"Checkpoint mode mismatch: checkpoint was created with "
                    f"{checkpoint_mode} but resume requested {mode}"
                )

        restore_experiment_state(experiment_dir)

        from app.repair_memory import repair_memory
        from app.strategy_selector import strategy_selector
        repair_memory.initialize_memory()
        strategy_selector.stats = strategy_selector._load_stats()

        for r in saved_results:
            results.append(BenchmarkResult(**r))
            completed_task_ids.add(r["task_id"])
        print(f"Resumed {len(completed_task_ids)} tasks from checkpoint.")
    else:
        save_experiment_manifest(experiment_dir, mode, actual_dataset_path, len(tasks), dataset_hash)

    # ----------------------------------------------------------
    # TASK LOOP
    # ----------------------------------------------------------
    for idx, task in enumerate(tasks):
        if task.task_id in completed_task_ids:
            continue

        print(f"\n[{experiment_id} | {mode}] Running Task {idx+1}/{len(tasks)}: {task.task_id}")

        prompt = task.prompt
        if task.expected_tests:
            prompt += "\n\nEnsure it passes these tests:\n" + "\n".join(task.expected_tests)

        req = Request(
            prompt=prompt,
            authoritative_tests=task.expected_tests,
            experiment_id=experiment_id,
            task_id=task.task_id,
            task_index=idx + 1
        )

        # ---- Stage tracking ----
        current_stage = "pre_generate"
        start = time.time()

        # Defaults for the case of a clean success
        resp = {}
        attempts = None
        success = None
        error_type = None
        error_message = None
        error_stage = None
        error_traceback = None
        error_category = None
        status = "unresolved"
        strategy_history = []
        difficulty = {}
        memory_used = None
        verification_data = None
        feedback = {}
        error_diagnostic = None

        try:
            current_stage = "generation"
            resp = generate(req)
            elapsed_ms = int((time.time() - start) * 1000)
            feedback = resp.get("feedback_record", {})
            attempts = resp.get("attempts_used", feedback.get("total_attempts", 5))
            success = resp.get("success", False)

            # Derive status from outcome
            if success is True:
                status = "model_success"
            elif success is False:
                status = "model_failure"
            else:
                status = "unresolved"

            for att in feedback.get("attempts", []):
                if "strategy" in att:
                    strat = att["strategy"]
                    strat["success"] = att.get("execution_status") == "success"
                    strategy_history.append(strat)
                if "difficulty" in att and not difficulty:
                    difficulty = att["difficulty"]
                if "error_type" in att and att["error_type"]:
                    error_type = att["error_type"]
                if att.get("memory_used"):
                    memory_used = True

            verification_data = feedback.get("verification", {})

        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            # Capture the FULL exception context — this is the critical fix
            error_diagnostic = build_error_diagnostic(exc, current_stage, task.task_id, experiment_id, elapsed_ms)

            error_type = error_diagnostic["error_type"]
            error_message = error_diagnostic["error_message"]
            error_stage = error_diagnostic["error_stage"]
            error_traceback = error_diagnostic["traceback"]
            error_category = error_diagnostic["error_category"]
            status = "infrastructure_failure"
            success = None

            print(f"[RUNNER ERROR] Task {task.task_id} failed at stage '{current_stage}':")
            print(f"  Exception: {error_type}: {error_message}")
            print(f"  Full traceback captured in raw task record.")
            # Print the traceback to stdout for live debugging, but it is also persisted
            print(error_traceback)

        # ---- Assemble the BenchmarkResult ----
        res = BenchmarkResult(
            experiment_id=experiment_id,
            task_id=task.task_id,
            mode=mode,
            success=success,
            status=status,
            error_type=error_type,
            error_message=error_message,
            error_stage=error_stage,
            error_traceback=error_traceback,
            error_category=error_category,
            attempts=attempts,
            repair_effort=attempts,
            execution_time_ms=elapsed_ms,
            strategy_history=strategy_history,
            difficulty=difficulty,
            verification=verification_data,
            memory_used=memory_used,
            lora_enabled=config.get("LORA_ENABLED", False),
            adapter_version=feedback.get("active_adapter_id"),
            task_index=idx + 1,
            active_adapter_id=feedback.get("active_adapter_id"),
            training_triggered=feedback.get("training_triggered", False),
            training_cycle_id=feedback.get("training_cycle_id"),
            training_status=feedback.get("training_status"),
            final_status=status,
            timestamp=time.time()
        )
        results.append(res)

        # ---- Save raw task record ----
        os.makedirs(experiment_dir, exist_ok=True)
        raw_tasks_dir = os.path.join(experiment_dir, "raw_tasks")
        os.makedirs(raw_tasks_dir, exist_ok=True)
        raw_task_path = os.path.join(raw_tasks_dir, f"{task.task_id}.json")

        if os.path.exists(raw_task_path):
            raise FileExistsError(
                f"Raw task record already exists for {task.task_id}. Refusing to overwrite."
            )

        raw_record = {
            # Identity
            "experiment_id": experiment_id,
            "task_id": task.task_id,
            "task_index": idx + 1,
            "mode": mode,

            # Outcome
            "status": status,
            "success": success,
            "final_status": status,

            # Attempt data
            "attempts_used": attempts,
            "repair_effort": attempts,

            # Generated artifacts
            "generated_code": resp.get("generated_code"),
            "initial_code": feedback.get("initial_code"),

            # Error information (structured — never just a class name)
            "error_category": error_category,
            "error_type": error_type,
            "error_message": error_message,
            "error_stage": error_stage,
            "exception_class": error_type,
            "traceback": error_traceback,

            # Full diagnostics for infrastructure failures
            "error_diagnostic": error_diagnostic,

            # Execution results
            "execution": resp.get("execution"),
            "tests": resp.get("tests"),
            "history": resp.get("history"),

            # Verification
            "verification": verification_data,

            # Strategy and difficulty
            "strategy_history": strategy_history,
            "difficulty": difficulty,

            # Memory
            "memory_used": memory_used,

            # LoRA
            "lora_enabled": feedback.get("lora_enabled", config.get("LORA_ENABLED", False)),
            "active_adapter_id": feedback.get("active_adapter_id"),
            "adapter_version": feedback.get("active_adapter_id"),
            "training_triggered": feedback.get("training_triggered", False),
            "training_cycle_id": feedback.get("training_cycle_id"),
            "training_status": feedback.get("training_status"),

            # Feedback (full record from app/main.py pipeline)
            "feedback_record": resp.get("feedback_record"),

            # Timing
            "timing": {
                "total_ms": elapsed_ms,
            },
            "runtime_ms": elapsed_ms,
            "timestamp": time.time()
        }

        with open(raw_task_path, "x") as f:
            json.dump(raw_record, f, indent=4)

        # ---- Atomic Checkpoint ----
        checkpoint_tmp = checkpoint_path + ".tmp"
        with open(checkpoint_tmp, "w") as f:
            json.dump(
                [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in results],
                f,
                indent=4
            )
            f.flush()
            os.fsync(f.fileno())
        os.replace(checkpoint_tmp, checkpoint_path)

        snapshot_experiment_state(experiment_dir)

    return results


# =========================================================
# CLI ENTRY POINT
# =========================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run LITE-CODER benchmark")
    parser.add_argument("--mode", type=str, required=True, help="Ablation mode")
    parser.add_argument("--size", type=int, default=None, help="Number of tasks to run")
    parser.add_argument("--experiment-id", type=str, required=True, help="Experiment ID for folder creation")
    parser.add_argument("--dataset", type=str, default="data/benchmark/v1.0/dataset.json",
                        help="Path to dataset JSON file")
    args = parser.parse_args()

    run_benchmark(
        args.experiment_id,
        args.mode,
        size=args.size,
        dataset_path=args.dataset
    )
