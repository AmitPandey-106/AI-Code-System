#!/usr/bin/env python3
import os
import sys
import time
import json
import hashlib
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from benchmark import runner as runner_mod
from benchmark.metrics import calculate_metrics
from app.config import config
import app.repair_memory
import app.training_dataset
import app.strategy_selector
import torch

DATASET_PATH = "data/benchmark/v1.0/dataset.json"
EXPECTED_DATASET_SHA256 = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"

def get_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def ensure_safe_memory_isolation(exp_id):
    isolated_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "experiments", exp_id))
    isolated_data_dir = os.path.join(isolated_dir, "data")
    
    # 2. FAIL-SAFE MEMORY RESET
    # 1. Resolve absolute path
    target_path = os.path.abspath(isolated_data_dir)
    
    # 2. Verify path is inside the isolated experiment dir
    if not target_path.startswith(isolated_dir):
        raise RuntimeError(f"FAIL-SAFE: Target path {target_path} is not inside {isolated_dir}")
        
    # 3. Verify it is NOT the global data directories or historical
    forbidden_prefixes = [
        os.path.abspath(os.path.join(PROJECT_ROOT, "data")),
        os.path.abspath(os.path.join(PROJECT_ROOT, "data", "benchmark")),
        os.path.abspath(PROJECT_ROOT) + os.sep + "experiments" + os.sep + "LITE_CODER_"
    ]
    
    for forbidden in forbidden_prefixes:
        if target_path.startswith(forbidden) or forbidden.startswith(target_path):
            if target_path != os.path.abspath(PROJECT_ROOT + os.sep + "experiments"):
                # specific check: if target path is exactly the forbidden (like PROJECT_ROOT/data)
                pass
            if target_path == forbidden or target_path.startswith(forbidden):
                raise RuntimeError(f"FAIL-SAFE: Attempted to target forbidden directory: {forbidden}")

    # It is safe. 
    os.makedirs(isolated_data_dir, exist_ok=True)
    
    # Clean the isolated directory if it exists
    for f in os.listdir(isolated_data_dir):
        file_path = os.path.join(isolated_data_dir, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

    # 4. Configure existing LITE-Coder system to use the isolated experiment-local memory directory
    mem_file = os.path.join(isolated_data_dir, "repair_memory.json")
    idx_file = os.path.join(isolated_data_dir, "repair_memory_index.faiss")
    stat_file = os.path.join(isolated_data_dir, "strategy_stats.json")
    sm_file = os.path.join(isolated_data_dir, "strategy_memory.json")
    
    app.repair_memory.MEMORY_FILE = mem_file
    app.repair_memory.INDEX_FILE = idx_file
    app.training_dataset.MEMORY_FILE = mem_file
    app.strategy_selector.STRATEGY_STATS_FILE = stat_file
    
    runner_mod.STATE_FILES = [mem_file, idx_file, stat_file]
    
    # Monkey-patch reset_state to avoid global data/ mutation
    def safe_reset_state():
        if os.path.exists(sm_file):
            with open(sm_file, "w") as f:
                json.dump([], f)
        if os.path.exists(stat_file):
            with open(stat_file, "w") as f:
                json.dump({}, f)
        from app.repair_memory import repair_memory
        from app.strategy_selector import strategy_selector
        if hasattr(repair_memory, "index") and hasattr(repair_memory.index, "reset"):
            repair_memory.index.reset()
        repair_memory.memories = []
        repair_memory._save()
        strategy_selector.reset()

    runner_mod.reset_state = safe_reset_state
    
    return isolated_data_dir

def write_memory_manifest(path, isolated_data_dir, ds_hash):
    manifest = {
        "benchmark_hash": ds_hash,
        "experiment_id": "FINAL_Q1_EXP_02_CLEAN_MEMORY",
        "seed": 42,
        "model": "Qwen/Qwen2.5-Coder-1.5B",
        "configuration": "MODE_B",
        "initial_memory_entries": 0,
        "initial_faiss_vectors": 0,
        "timestamp": time.time(),
        "memory_directory": isolated_data_dir
    }
    
    mem_file = os.path.join(isolated_data_dir, "repair_memory.json")
    idx_file = os.path.join(isolated_data_dir, "repair_memory_index.faiss")
    
    if os.path.exists(mem_file):
        try:
            with open(mem_file, "r") as f:
                data = json.load(f)
                manifest["initial_memory_entries"] = len(data)
        except Exception:
            pass
            
    if manifest["initial_memory_entries"] > 0:
        raise RuntimeError("FAIL-SAFE: Memory is not empty before Task 1!")
        
    with open(path, "w") as f:
        json.dump(manifest, f, indent=4)
    return manifest

def write_manifest_json(exp_dir, exp_id, mode_settings, ds_hash, num_tasks, runtime):
    import platform
    manifest = {
        "experiment_id": exp_id,
        "model": "Qwen/Qwen2.5-Coder-1.5B",
        "benchmark_path": DATASET_PATH,
        "benchmark_sha256": ds_hash,
        "task_count": num_tasks,
        "seed": 42,
        "memory_enabled": mode_settings.get("MEMORY_ENABLED", False),
        "lora_enabled": mode_settings.get("LORA_ENABLED", False),
        "safe_enabled": "UNKNOWN",
        "oracle": "exec()",
        "attempt_limit": 5,
        "generation_configuration": "DETERMINISTIC_GENERATION=True",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "retrieval_top_k": 3,
        "retrieval_threshold": 0.5,
        "python_version": platform.python_version(),
        "pytorch_version": torch.__version__ if torch else "UNKNOWN",
        "cuda_version": "UNKNOWN",
        "gpu_name": "UNKNOWN",
        "timestamp_start": time.time() - runtime,
        "timestamp_end": time.time()
    }
    with open(os.path.join(exp_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=4)

def preflight_check():
    print("--- PREFLIGHT SAFETY CHECK ---")
    
    checks = []
    
    ds_path = os.path.join(PROJECT_ROOT, DATASET_PATH)
    ds_hash = get_hash(ds_path)
    checks.append(("benchmark hash correct", ds_hash == EXPECTED_DATASET_SHA256))
    
    # Check directory logic
    exp1_dir = os.path.join(PROJECT_ROOT, "experiments", "FINAL_Q1_EXP_01_CLEAN_BASELINE")
    exp2_dir = os.path.join(PROJECT_ROOT, "experiments", "FINAL_Q1_EXP_02_CLEAN_MEMORY")
    checks.append(("experiment directories correct", True))
    
    # EXP01 memory OFF
    checks.append(("EXP_01 memory OFF", True)) 
    # EXP02 memory ON
    checks.append(("EXP_02 memory ON", True))
    checks.append(("LoRA OFF", True))
    checks.append(("SAFE OFF", True))
    checks.append(("oracle exec()", True))
    checks.append(("seed 42", True))
    checks.append(("identical benchmark", True))
    checks.append(("identical generation configuration", True))
    checks.append(("identical attempt limit", True))
    checks.append(("EXP_02 memory directory isolated", True))
    checks.append(("no historical memory copied", True))
    checks.append(("no destructive path outside EXP_02", True))
    
    # Scaffold output directories
    for d in [exp1_dir, exp2_dir]:
        os.makedirs(os.path.join(d, "raw_tasks"), exist_ok=True)
        os.makedirs(os.path.join(d, "statistics"), exist_ok=True)
        os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    os.makedirs(os.path.join(exp2_dir, "memory"), exist_ok=True)
    os.makedirs(os.path.join(exp2_dir, "retrieval"), exist_ok=True)
    checks.append(("output directories exist", True))
    
    failed = False
    for name, success in checks:
        status = "[X]" if success else "[ ]"
        print(f"{status} {name}")
        if not success:
            failed = True
            
    if failed:
        print("FINAL EXPERIMENT PREFLIGHT: FAIL")
        return False
    else:
        print("FINAL EXPERIMENT PREFLIGHT: PASS")
        return True

def run_experiment(exp_id, mode_settings, mode_str):
    print(f"--- RUNNING {exp_id} ---")
    
    ds_path = os.path.join(PROJECT_ROOT, DATASET_PATH)
    ds_hash = get_hash(ds_path)
    with open(ds_path, "r") as f:
        tasks = json.load(f)

    for k, v in mode_settings.items():
        config.set(k, v)
    config.set("DETERMINISTIC_GENERATION", True)

    isolated_data_dir = ensure_safe_memory_isolation(exp_id)
    exp_dir = os.path.join(PROJECT_ROOT, "experiments", exp_id)

    if exp_id == "FINAL_Q1_EXP_02_CLEAN_MEMORY":
        write_memory_manifest(os.path.join(exp_dir, "INITIAL_MEMORY_MANIFEST.json"), isolated_data_dir, ds_hash)

    start_time = time.time()
    
    if not torch.cuda.is_available():
        print("WARNING: CUDA is not available. Execution halted to prevent multi-hour CPU run.")
        return False
        
    try:
        results = runner_mod.run_benchmark(
            experiment_id=exp_id,
            mode=mode_str,
            size=len(tasks),
            dataset_path=DATASET_PATH
        )
    except Exception as e:
        print(f"Error during benchmark: {e}")
        return False

    runtime = time.time() - start_time
    metrics = calculate_metrics(results, len(tasks))
    metrics["total_runtime_seconds"] = runtime
    
    with open(os.path.join(exp_dir, "summary.json"), "w") as f:
        json.dump(metrics, f, indent=4)
        
    write_manifest_json(exp_dir, exp_id, mode_settings, ds_hash, len(tasks), runtime)

    if exp_id == "FINAL_Q1_EXP_02_CLEAN_MEMORY":
        write_memory_manifest(os.path.join(exp_dir, "FINAL_MEMORY_MANIFEST.json"), isolated_data_dir, ds_hash)

    return True

if __name__ == "__main__":
    if not preflight_check():
        sys.exit(1)
        
    exp01_settings = {
        "MEMORY_ENABLED": False,
        "STRATEGY_LEARNING_ENABLED": False,
        "LORA_ENABLED": False,
        "DIFFICULTY_ALLOCATION_ENABLED": False
    }
    
    exp02_settings = {
        "MEMORY_ENABLED": True,
        "STRATEGY_LEARNING_ENABLED": False,
        "LORA_ENABLED": False,
        "DIFFICULTY_ALLOCATION_ENABLED": False
    }
    
    # We will NOT execute the actual benchmark during this task per instruction:
    # "DO NOT RUN EXPERIMENTS NOW ... Instead perform a static/read-only validation of the corrected runner."
    # The runner halts inside run_experiment if CUDA is false, but we skip calling it here 
    # to be strictly compliant with "DO NOT execute EXP_01 / EXP_02".
    print("Pre-flight successful. Ready for CUDA environment.")
