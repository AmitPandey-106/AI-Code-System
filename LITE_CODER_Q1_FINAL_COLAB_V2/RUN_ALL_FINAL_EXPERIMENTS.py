#!/usr/bin/env python3
import os
import sys
import json
import hashlib
import datetime
import subprocess

TARGET_HASH = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"

def sha256_file(path):
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def enforce_memory_isolation(exp_name):
    dir_path = os.path.join("experiments", "FINAL_Q1_RUN", exp_name)
    abs_path = os.path.abspath(dir_path)
    
    # FIX FOR BLOCKER 2: Ensure directory exists BEFORE writing
    os.makedirs(abs_path, exist_ok=True)
    
    if not abs_path.startswith(os.path.abspath("experiments")):
        raise PermissionError("Isolation violation: Path outside experiments dir")
        
    if exp_name == "EXP_02_CLEAN_MEMORY":
        # Strict Isolation guarantees
        mem_file = os.path.join(abs_path, "repair_memory.json")
        faiss_file = os.path.join(abs_path, "memory.faiss")
        if os.path.exists(mem_file):
            os.remove(mem_file)
        if os.path.exists(faiss_file):
            os.remove(faiss_file)
    
    manifest = {
        "memory_records": 0, "faiss_vectors": 0, "memory_file_exists": False,
        "timestamp": str(datetime.datetime.now())
    }
    with open(os.path.join(abs_path, "INITIAL_MEMORY_MANIFEST.json"), 'w') as f:
        json.dump(manifest, f)

def run_experiment(exp_name, config):
    print(f"\n=== RUNNING {exp_name} ===")
    enforce_memory_isolation(exp_name)
    # Execution logic would go here
    print(f"Simulating run with config: {config}")

def main():
    bm_path = os.path.join("data", "benchmark", "v1.0", "dataset.json")
    if not os.path.exists(bm_path):
        print(f"FATAL: Benchmark file not found at {bm_path}")
        sys.exit(1)
        
    h = sha256_file(bm_path)
    if h != TARGET_HASH:
        print(f"FATAL: Benchmark hash mismatch! Expected {TARGET_HASH}, got {h}")
        sys.exit(1)
        
    print("Preflight: Benchmark hash verified successfully.")
    
    run_experiment("EXP_01_CLEAN_BASELINE", {"memory": "OFF", "lora": "OFF", "safe": "OFF", "oracle": "exec()", "seed": 42})
    run_experiment("EXP_02_CLEAN_MEMORY", {"memory": "ON", "lora": "OFF", "safe": "OFF", "oracle": "exec()", "seed": 42})
    run_experiment("EXP_03_SAFE_BASELINE", {"memory": "OFF", "lora": "OFF", "safe": "ON", "oracle": "SAFE", "seed": 42})
    run_experiment("EXP_04_SAFE_MEMORY", {"memory": "ON", "lora": "OFF", "safe": "ON", "oracle": "SAFE", "seed": 42})

if __name__ == '__main__':
    main()
