import os
import json
import shutil
import glob
import pandas as pd
import matplotlib.pyplot as plt
from RUN_ALL_FINAL_EXPERIMENTS_V5 import isolate_state_in, isolate_state_out
from benchmark.runner import run_benchmark

def run_experiment_stage(exp_name, mode, dataset_path, description):
    print(f"\n========================================================")
    print(f"RUNNING: {description} ({mode})")
    print(f"========================================================\n")
    isolate_state_in(exp_name)
    try:
        run_benchmark(exp_name, mode, dataset_path=dataset_path)
    except Exception as e:
        print(f"[{exp_name}] Execution failed: {e}")
    finally:
        isolate_state_out(exp_name)

if __name__ == '__main__':
    # 1. Baseline Held-out
    run_experiment_stage(
        "CONTROLLED_LORA_PROOF/STAGE1_BASELINE", 
        "MODE_A", 
        "experiments/CONTROLLED_LORA_PROOF/data/heldout_dataset.json",
        "Baseline Held-out Test"
    )
    
    # 2. Main Proof Training
    run_experiment_stage(
        "CONTROLLED_LORA_PROOF/STAGE2_TRAINING", 
        "MODE_F", 
        "experiments/CONTROLLED_LORA_PROOF/data/proof_dataset.json",
        "LoRA Training Proof"
    )
    
    # 3. Learned Held-out
    run_experiment_stage(
        "CONTROLLED_LORA_PROOF/STAGE3_LEARNED", 
        "MODE_F", 
        "experiments/CONTROLLED_LORA_PROOF/data/heldout_dataset.json",
        "Learned Held-out Test"
    )
    
    print("\n[ALL STAGES COMPLETED]")
