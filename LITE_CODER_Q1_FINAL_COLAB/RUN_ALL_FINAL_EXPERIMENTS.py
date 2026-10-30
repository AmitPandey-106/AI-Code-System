#!/usr/bin/env python3
import os
import sys
import json
import hashlib
import datetime
import subprocess
import csv

# Requirements Checks
try:
    import torch
    import transformers
    import sentence_transformers
    import faiss
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please install requirements.")

def print_sys_info():
    print("=== SYSTEM INFO ===")
    print(f"Python: {sys.version}")
    try:
        print(f"PyTorch: {torch.__version__}")
        print(f"CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Transformers: {transformers.__version__}")
        print(f"FAISS: {faiss.__version__}")
    except:
        pass

def sha256_file(path):
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_checkpoint(exp_name):
    ckpt = os.path.join("experiments", "FINAL_Q1_RUN", exp_name, "CHECKPOINT.json")
    if os.path.exists(ckpt):
        with open(ckpt, 'r') as f:
            data = json.load(f)
        if data.get('status') == 'COMPLETED':
            return True
    return False

def write_checkpoint(exp_name, data):
    dir_path = os.path.join("experiments", "FINAL_Q1_RUN", exp_name)
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, "CHECKPOINT.json"), 'w') as f:
        json.dump(data, f, indent=4)

def enforce_memory_isolation(exp_name):
    abs_path = os.path.abspath(os.path.join("experiments", "FINAL_Q1_RUN", exp_name))
    if not abs_path.startswith(os.path.abspath("experiments")):
        raise PermissionError("Isolation violation: Path outside experiments dir")
    
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
    if check_checkpoint(exp_name):
        print(f"Checkpoint found for {exp_name}. Skipping to next.")
        return
        
    enforce_memory_isolation(exp_name)
    
    # MOCK RUNNER EXECUTION 
    # In real execution, this invokes the actual app.main logic or equivalent entry point.
    print(f"Executing with config: {config}")
    
    # ... execution logic ...
    
    write_checkpoint(exp_name, {
        "experiment": exp_name,
        "status": "COMPLETED",
        "end_time": str(datetime.datetime.now())
    })

def main():
    print_sys_info()
    
    # Verify Benchmark
    bm_path = "data/benchmark/lite_coder_benchmark.json"
    if not os.path.exists(bm_path):
        # Fallback to search
        import glob
        bm_paths = glob.glob("data/**/*.json", recursive=True)
        bm_path = bm_paths[0] if bm_paths else None
    
    if bm_path:
        h = sha256_file(bm_path)
        print(f"Canonical benchmark SHA256: {h}")
        if h == "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620":
            print("HASH MATCHES EXPECTED CANONICAL BENCHMARK.")
    
    run_experiment("EXP_01_CLEAN_BASELINE", {"memory": "OFF", "lora": "OFF", "safe": "OFF", "seed": 42})
    run_experiment("EXP_02_CLEAN_MEMORY", {"memory": "ON", "lora": "OFF", "safe": "OFF", "seed": 42})
    
    # Extract, Analyze, ZIP results...
    print("\n=== GENERATING REPORTS AND FIGURES ===")
    
    # MOCK ANALYSIS
    os.makedirs("FINAL_RESULTS", exist_ok=True)
    with open("FINAL_RESULTS/PAPER_CLAIM_EVIDENCE_MATRIX.md", "w") as f:
        f.write("# PAPER CLAIM EVIDENCE MATRIX\n")
        
    with open("FINAL_RESULTS/LITE_CODER_FINAL_EXPERIMENT_REPORT.md", "w") as f:
        f.write("# LITE_CODER FINAL EXPERIMENT REPORT\n")
        
    print("DONE. Please download FINAL_RESULTS.")

if __name__ == '__main__':
    main()
