import os
import sys
from unittest.mock import MagicMock

# Aggressively mock out all ML imports before importing benchmark runner
sys.modules['app.model'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['peft'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['faiss'] = MagicMock()
sys.modules['app.repair_memory'] = MagicMock()
sys.modules['app.strategy_selector'] = MagicMock()

import benchmark.runner
import app.main

# Mock generate function to avoid LLM inference
def fake_generate(req):
    return {
        "success": True,
        "attempts_used": 1,
        "generated_code": "def hello(): pass",
        "execution": "Success",
        "tests": "All passed",
        "history": [],
        "feedback_record": {
            "task": req.prompt,
            "initial_code": "",
            "attempts": [
                {
                    "strategy": {"selected_strategy": "baseline"},
                    "execution_status": "success",
                    "error_type": None,
                    "difficulty": {"level": "easy"},
                    "memory_used": False
                }
            ],
            "final_code": "def hello(): pass",
            "final_status": "success",
            "verification": {
                "syntax_passed": True,
                "safety_passed": True,
                "execution_passed": True,
                "tests_passed": True,
                "sandboxed_execution": True
            }
        }
    }

benchmark.runner.generate = fake_generate
benchmark.runner.reset_state = MagicMock()
benchmark.runner.snapshot_experiment_state = MagicMock()

print("Running fast smoke test...")
results = benchmark.runner.run_benchmark("SMOKE_TEST", "MODE_A", size=1, dataset_path="data/benchmark/v1.0/dataset.json")

print(f"Smoke test completed. {len(results)} tasks executed.")
if os.path.exists("experiments/SMOKE_TEST/checkpoint.json"):
    print("Checkpoint exists.")
else:
    print("MISSING: Checkpoint")
    
if os.path.exists("experiments/SMOKE_TEST/experiment_manifest.json"):
    print("Manifest exists.")
else:
    print("MISSING: Manifest")
    
raw_tasks = os.listdir("experiments/SMOKE_TEST/raw_tasks")
print(f"Raw tasks saved: {len(raw_tasks)}")
if len(raw_tasks) != 1:
    print("ERROR: Raw task count mismatch")
