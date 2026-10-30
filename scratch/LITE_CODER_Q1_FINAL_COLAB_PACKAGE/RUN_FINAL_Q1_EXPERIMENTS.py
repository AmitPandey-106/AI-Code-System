#!/usr/bin/env python3
import os
import sys
import hashlib
import subprocess

EXPECTED_BENCHMARK_HASH = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"
EXPECTED_RUNNER_HASH = "8e35d2e0ca6038dcdd3c87ba171fbc30c45a1a95ea3427629f1cc5fa0b934bea"

def get_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def main():
    print("==================================================")
    print(" LITE-CODER Q1 FINAL EXPERIMENT RUNNER")
    print("==================================================")
    
    try:
        import torch
        if not torch.cuda.is_available():
            print("ERROR: CUDA is not available. GPU is required!")
            sys.exit(1)
        print("CUDA: PASSED")
    except ImportError:
        print("ERROR: torch is not installed.")
        sys.exit(1)
        
    bench_hash = get_hash("data/benchmark/v1.0/dataset.json")
    if bench_hash != EXPECTED_BENCHMARK_HASH:
        print("ERROR: Benchmark hash mismatch!")
        sys.exit(1)
    print("Benchmark Hash: PASSED")
        
    runner_hash = get_hash("scripts/run_final_experiments.py")
    if runner_hash != EXPECTED_RUNNER_HASH:
        print("ERROR: Runner hash mismatch!")
        sys.exit(1)
    print("Runner Hash: PASSED")
    
    print("\nExecuting approved runner...")
    subprocess.run([sys.executable, "scripts/run_final_experiments.py"], check=True)
    
    print("\nFINAL OUTPUT LOCATIONS:")
    print("  - experiments/FINAL_Q1_EXP_01_CLEAN_BASELINE")
    print("  - experiments/FINAL_Q1_EXP_02_CLEAN_MEMORY")
    print("  - experiments/FINAL_Q1_EXP_01_EXP_02_COMPARISON.md")

if __name__ == "__main__":
    main()
