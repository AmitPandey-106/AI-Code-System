import os
import json
import time
from typing import List
from benchmark.schemas import BenchmarkResult
from benchmark.dataset import load_dataset
from benchmark.ablation import apply_ablation_mode
from app.main import generate, Request
from app.config import config

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
    checkpoint_path = f"experiments/{experiment_id}/checkpoint.json"
    
    # Resume from checkpoint
    completed_task_ids = set()
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, "r") as f:
            saved_results = json.load(f)
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
        checkpoint_path = f"experiments/{experiment_id}/checkpoint.json"
        os.makedirs(f"experiments/{experiment_id}", exist_ok=True)
        with open(checkpoint_path, "w") as f:
            json.dump([r.dict() if hasattr(r, 'dict') else r.model_dump() for r in results], f, indent=4)
            
    return results
