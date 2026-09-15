import os
from benchmark.runner import run_benchmark
from app.config import config

def run_smoke_test():
    # Enforce deterministic settings
    config.set("BENCHMARK_SEED", 42)
    config.set("DETERMINISTIC_GENERATION", True)
    
    modes = [
        ("MODE_A", "smoke_test_A"),
        ("MODE_B", "smoke_test_B"),
        ("MODE_D", "smoke_test_D"),
        ("MODE_F", "smoke_test_F"),
        # and test isolation back to A
        ("MODE_A", "smoke_test_A_post_F")
    ]
    
    for mode, exp_id in modes:
        print(f"\n============================================================")
        print(f"RUNNING SMOKE TEST: {exp_id} ({mode})")
        print(f"============================================================")
        
        run_benchmark(
            experiment_id=exp_id,
            mode=mode,
            size=10,
            dataset_path="data/benchmark/v1.0/dataset.json"
        )
        
if __name__ == "__main__":
    run_smoke_test()
