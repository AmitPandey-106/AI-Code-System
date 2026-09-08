import os
import json
import time
import platform
import argparse
from typing import List

from benchmark.runner import run_benchmark
from benchmark.reporter import save_report

def get_hardware_info():
    import psutil
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "cpu": platform.processor(),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "python": platform.python_version()
    }
    try:
        import torch
        info["pytorch"] = torch.__version__
        info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None"
        if torch.cuda.is_available():
            info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    except ImportError:
        pass
    return info

def run_isolated_ablation(modes: List[str], dataset_path: str, base_dir: str = "experiments/ablation"):
    # This runs the benchmark with completely wiped states to ensure no cross-contamination
    print(f"Starting Isolated Ablation on modes: {modes}")
    hw_info = get_hardware_info()
    
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
    print(f"Loaded {len(dataset)} tasks from {dataset_path}")
    
    for mode in modes:
        exp_id = f"{base_dir}/EXP_{mode}_{int(time.time())}"
        os.makedirs(exp_id, exist_ok=True)
        
        # Save manifest
        manifest = {
            "mode": mode,
            "dataset_version": "1.0",
            "dataset_path": dataset_path,
            "hardware": hw_info,
            "experiment_type": "ISOLATED_ABLATION"
        }
        with open(f"{exp_id}/experiment_manifest.json", "w") as f:
            json.dump(manifest, f, indent=4)
            
        print(f"\n=============================================")
        print(f"Executing Mode: {mode} (Saving to {exp_id})")
        size_limit = len(dataset) if args.large else 5
        results = run_benchmark(exp_id, mode, size=size_limit, dataset_path=dataset_path)
        save_report(exp_id, results)
        
def run_continual_learning(batch_size: int, dataset_path: str, base_dir: str = "experiments/continual"):
    print("Continual Learning Pipeline NOT YET FULLY IMPLEMENTED IN THIS SCRIPT.")
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LITE-CODER Phase 8 Executor")
    parser.add_argument("--large", action="store_true", help="RUN_LARGE_BENCHMARK flag")
    parser.add_argument("--modes", nargs="+", default=["MODE_A", "MODE_D", "MODE_F"], help="Modes to run")
    args = parser.parse_args()
    
    if args.large:
        print("RUNNING LARGE BENCHMARK (This may take several hours!)")
    else:
        print("RUNNING MICRO/SMALL BENCHMARK PREFLIGHT")
        
    dataset = "data/benchmark/v1.0/dataset.json"
    
    if not os.path.exists(dataset):
        print(f"CRITICAL ERROR: Dataset {dataset} not found. Generate it first.")
        exit(1)
        
    run_isolated_ablation(args.modes, dataset)
