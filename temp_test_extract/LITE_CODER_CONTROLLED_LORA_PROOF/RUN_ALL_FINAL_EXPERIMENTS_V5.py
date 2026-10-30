#!/usr/bin/env python3
import os
import sys
import json
import glob
import shutil
import hashlib
import datetime

TARGET_HASH = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"
EXPECTED_TASKS = 100

STATE_FILES = [
    "data/repair_memory.json",
    "data/repair_memory_index.faiss",
    "data/strategy_memory.json",
    "data/strategy_stats.json"
]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(4096), b""):
            h.update(b)
    return h.hexdigest()

def isolate_state_in(exp_name):
    # Swap isolated state into active global path for the historical runner
    exp_mem_dir = os.path.abspath(os.path.join("experiments", "FINAL_Q1_RUN", exp_name, "memory"))
    os.makedirs(exp_mem_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    for f in STATE_FILES:
        active_path = f
        isolated_path = os.path.join(exp_mem_dir, os.path.basename(f))
        
        # Clear global state to ensure no contamination
        if os.path.exists(active_path):
            os.remove(active_path)
            
        # Restore isolated state if resuming
        if os.path.exists(isolated_path):
            shutil.copy2(isolated_path, active_path)

def isolate_state_out(exp_name):
    # Swap active global state back to isolated experiment path
    exp_mem_dir = os.path.abspath(os.path.join("experiments", "FINAL_Q1_RUN", exp_name, "memory"))
    os.makedirs(exp_mem_dir, exist_ok=True)
    
    for f in STATE_FILES:
        active_path = f
        isolated_path = os.path.join(exp_mem_dir, os.path.basename(f))
        if os.path.exists(active_path):
            shutil.copy2(active_path, isolated_path)
            os.remove(active_path)

def run_isolated_experiment(exp_name, mode_name):
    print(f"\n=== EXECUTING {exp_name} ===")
    exp_dir = os.path.abspath(os.path.join("experiments", "FINAL_Q1_RUN", exp_name))
    ckpt_path = os.path.join(exp_dir, "CHECKPOINT.json")
    
    # 1. Checkpoint Verification
    if os.path.exists(ckpt_path):
        with open(ckpt_path, "r") as f:
            data = json.load(f)
        if data.get("status") == "COMPLETED":
            print(f"[{exp_name}] Checkpoint COMPLETED. Skipping.")
            return

    # 2. Strict EXP_02 Initial Memory Enforcement
    if exp_name == "EXP_02_CLEAN_MEMORY":
        if not exp_dir.startswith(os.path.abspath("experiments")):
            raise PermissionError("Path resolution breached isolated directory structure.")
        
        # Hard wipe EXP_02 memory
        mem_dir = os.path.join(exp_dir, "memory")
        if os.path.exists(mem_dir):
            shutil.rmtree(mem_dir)
        os.makedirs(mem_dir)
        
        init_manifest = {
            "memory_records": 0, "faiss_vectors": 0, 
            "memory_file_exists": False, "timestamp": str(datetime.datetime.now()),
            "dataset_hash": TARGET_HASH, "seed": 42
        }
        with open(os.path.join(exp_dir, "INITIAL_MEMORY_MANIFEST.json"), "w") as f:
            json.dump(init_manifest, f)
            
    # 3. State In
    isolate_state_in(exp_name)
    
    # 4. Invoke Historical Runner (Direct python import)
    try:
        from benchmark.runner import run_benchmark
        # The runner natively writes raw_tasks internally based on exp_id
        # We pass the relative ID to route it to FINAL_Q1_RUN/<exp_name>
        run_benchmark(f"FINAL_Q1_RUN/{exp_name}", mode_name, dataset_path="data/benchmark/v1.0/dataset.json")
    except Exception as e:
        print(f"[{exp_name}] Execution failed: {e}")
        isolate_state_out(exp_name)
        return
        
    # 5. State Out
    isolate_state_out(exp_name)
    
    # 6. Artifact Verification - 100 Tasks
    raw_tasks_dir = os.path.join(exp_dir, "raw_tasks")
    if not os.path.exists(raw_tasks_dir):
        print(f"[{exp_name}] INCOMPLETE: raw_tasks/ missing.")
        return
        
    task_files = glob.glob(os.path.join(raw_tasks_dir, "*.json"))
    if len(task_files) != EXPECTED_TASKS:
        print(f"[{exp_name}] INCOMPLETE: Found {len(task_files)} tasks, expected {EXPECTED_TASKS}.")
        return
        
    # 7. Write COMPLETED Checkpoint only after proof
    with open(ckpt_path, "w") as f:
        json.dump({
            "experiment": exp_name, "status": "COMPLETED",
            "end_time": str(datetime.datetime.now()), "tasks_evaluated": len(task_files)
        }, f)
    
    # Final Memory Manifest
    if exp_name == "EXP_02_CLEAN_MEMORY":
        # Calculate final size by inspecting isolated memory path
        mem_path = os.path.join(exp_dir, "memory", "repair_memory.json")
        recs = 0
        if os.path.exists(mem_path):
            try:
                with open(mem_path, "r") as mf:
                    mem_data = json.load(mf)
                    recs = len(mem_data)
            except:
                pass
        with open(os.path.join(exp_dir, "FINAL_MEMORY_MANIFEST.json"), "w") as f:
            json.dump({"final_records": recs, "timestamp": str(datetime.datetime.now())}, f)

def main():
    bm_path = "data/benchmark/v1.0/dataset.json"
    if not os.path.exists(bm_path):
        print("FATAL: Canonical benchmark missing.")
        sys.exit(1)
        
    h = sha256_file(bm_path)
    if h != TARGET_HASH:
        print(f"FATAL: Benchmark hash mismatch! Got {h}")
        sys.exit(1)
        
    with open(bm_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        tasks = data if isinstance(data, list) else data.get("tasks", list(data.keys()))
        if len(tasks) != EXPECTED_TASKS:
            print(f"FATAL: Benchmark has {len(tasks)} tasks instead of {EXPECTED_TASKS}.")
            sys.exit(1)
            
    print("V4 Preflight & Identity Verification PASS.")
    
    # Run the exact modes mapped to their historical configurations
    # MODE_A: Memory OFF, LoRA OFF, SAFE OFF, Oracle exec
    run_isolated_experiment("EXP_01_CLEAN_BASELINE", "MODE_A")
    # MODE_D: Memory ON, LoRA OFF, SAFE OFF, Oracle exec
    run_isolated_experiment("EXP_02_CLEAN_MEMORY", "MODE_D")
    # MODE_F: Memory ON, Strategy Learning ON, LoRA ON (Canary SAFE natively enabled)
    run_isolated_experiment("EXP_03_FULL_SYSTEM", "MODE_F")

if __name__ == '__main__':
    main()
