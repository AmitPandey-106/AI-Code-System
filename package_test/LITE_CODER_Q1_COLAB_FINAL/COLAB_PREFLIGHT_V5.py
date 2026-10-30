#!/usr/bin/env python3
import os
import sys
import hashlib
import json

TARGET_HASH = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"

def preflight():
    # 1. Dataset Hash
    bm_path = "data/benchmark/v1.0/dataset.json"
    if not os.path.exists(bm_path):
        return "FAIL: Benchmark missing."
    h = hashlib.sha256(open(bm_path, 'rb').read()).hexdigest()
    if h != TARGET_HASH:
        return f"FAIL: Benchmark hash mismatch: {h}"
        
    # 2. Historical Runner Availability
    try:
        from benchmark.runner import run_benchmark
    except ImportError:
        return "FAIL: benchmark.runner.run_benchmark is missing."
        
    # 3. Output directories
    for exp in ["EXP_01_CLEAN_BASELINE", "EXP_02_CLEAN_MEMORY", "EXP_03_FULL_SYSTEM"]:
        if not os.path.exists(f"experiments/FINAL_Q1_RUN/{exp}"):
            return f"FAIL: Missing isolated dir {exp}"
            
    return "FINAL V5 PREFLIGHT: PASS"

if __name__ == '__main__':
    print(preflight())
