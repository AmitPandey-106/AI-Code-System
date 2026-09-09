import os
import json
import time
import shutil
from typing import List
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

def snapshot_experiment_state(experiment_dir: str):
    snapshot_dir = os.path.join(experiment_dir, "state_snapshot")
    os.makedirs(snapshot_dir, exist_ok=True)
    for file_path in STATE_FILES:
        if os.path.exists(file_path):
            shutil.copy2(file_path, snapshot_dir)

def restore_experiment_state(experiment_dir: str):
    snapshot_dir = os.path.join(experiment_dir, "state_snapshot")
    if not os.path.exists(snapshot_dir):
        raise RuntimeError(f"Checkpoint exists but state snapshot is missing at {snapshot_dir}. Exact resume cannot be guaranteed.")
        
    for file_path in STATE_FILES:
        basename = os.path.basename(file_path)
        snapshot_file = os.path.join(snapshot_dir, basename)
        if os.path.exists(snapshot_file):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            shutil.copy2(snapshot_file, file_path)

def reset_state():
    # Safely clear memory and strategy states for isolated experiments
    if os.path.exists("data/repair_memory.json"):
        with open("data/repair_memory.json", "w") as f:
            json.dump([], f)
    if os.path.exists("data/strategy_memory.json"):
        with open("data/strategy_memory.json", "w") as f:
            json.dump([], f)
    if os.path.exists("data/strategy_stats.json"):
        with open("data/strategy_stats.json", "w") as f:
            json.dump({}, f)
    # Clear FAISS index
    from app.repair_memory import repair_memory
    from app.strategy_selector import strategy_selector
    
    repair_memory.index.reset()
    repair_memory.memories = []
    
    # Clear in-memory strategy learning stats
    strategy_selector.reset()

def run_benchmark(experiment_id: str, mode: str, size: int = None, dataset_path: str = None) -> List[BenchmarkResult]:
    apply_ablation_mode(mode)
    reset_state()
    
    tasks = load_dataset(dataset_path) if dataset_path else load_dataset()
    if size is not None:
        tasks = tasks[:size]
        
    results = []
    experiment_dir = f"experiments/{experiment_id}"
    checkpoint_path = f"{experiment_dir}/checkpoint.json"
    
    # Resume from checkpoint
    completed_task_ids = set()
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, "r") as f:
            saved_results = json.load(f)
            
        if saved_results:
            checkpoint_mode = saved_results[0].get("mode")
            if checkpoint_mode and checkpoint_mode != mode:
                raise ValueError(f"Checkpoint mode mismatch: checkpoint was created with {checkpoint_mode} but resume requested {mode}")
                
        restore_experiment_state(experiment_dir)
        
        # Reload singletons
        from app.repair_memory import repair_memory
        from app.strategy_selector import strategy_selector
        repair_memory.initialize_memory()
        strategy_selector.stats = strategy_selector._load_stats()

        # Reconstruct BenchmarkResult objects if necessary, or just store the raw dicts
        for r in saved_results:
            results.append(BenchmarkResult(**r))
            completed_task_ids.add(r["task_id"])
        print(f"Resumed {len(completed_task_ids)} tasks from checkpoint.")
    
    for idx, task in enumerate(tasks):
        if task.task_id in completed_task_ids:
            continue
            
        print(f"\n[{experiment_id} | {mode}] Running Task {idx+1}/{len(tasks)}: {task.task_id}")
        
        # We append expected tests to prompt so the model tests it
        prompt = task.prompt
        if task.expected_tests:
            prompt += "\n\nEnsure it passes these tests:\n" + "\n".join(task.expected_tests)
            
        req = Request(
            prompt=prompt,
            authoritative_tests=task.expected_tests
        )
        
        start = time.time()
        try:
            resp = generate(req)
            elapsed_ms = int((time.time() - start) * 1000)
            feedback = resp.get("feedback_record", {})
            attempts = resp.get("attempts_used", feedback.get("total_attempts", 5))
            success = resp.get("success", False)
            
            strategy_history = []
            difficulty = {}
            error_type = None
            memory_used = False
            
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
            
        except Exception as e:
            print(f"Task Failed due to exception: {e}")
            elapsed_ms = int((time.time() - start) * 1000)
            attempts = 0
            success = False
            error_type = e.__class__.__name__
            strategy_history = []
            difficulty = {}
            memory_used = False
            verification_data = {
                "syntax_passed": False,
                "safety_passed": False,
                "execution_passed": False,
                "tests_passed": False,
                "sandboxed_execution": True
            }

        res = BenchmarkResult(
            experiment_id=experiment_id,
            task_id=task.task_id,
            mode=mode,
            success=success,
            error_type=error_type,
            attempts=attempts,
            repair_effort=attempts,
            execution_time_ms=elapsed_ms,
            strategy_history=strategy_history,
            difficulty=difficulty,
            verification=verification_data,
            memory_used=memory_used,
            lora_enabled=config.get("LORA_ENABLED", False),
            timestamp=time.time()
        )
        results.append(res)
        
        # Checkpointing
        os.makedirs(experiment_dir, exist_ok=True)
        with open(checkpoint_path, "w") as f:
            json.dump([r.dict() if hasattr(r, 'dict') else r.model_dump() for r in results], f, indent=4)
            
        snapshot_experiment_state(experiment_dir)
            
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run LITE-CODER benchmark")
    parser.add_argument("--mode", type=str, required=True, help="Ablation mode")
    parser.add_argument("--size", type=int, default=None, help="Number of tasks to run")
    parser.add_argument("--experiment-id", type=str, required=True, help="Experiment ID for folder creation")
    args = parser.parse_args()
    
    run_benchmark(
        args.experiment_id, 
        args.mode, 
        size=args.size, 
        dataset_path="data/benchmark/v1.0/dataset.json"
    )
