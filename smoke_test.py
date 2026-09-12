import os
import sys
import time
from benchmark.runner import run_benchmark
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

app.main.generate = fake_generate

print("Running smoke test...")
results = run_benchmark("SMOKE_TEST", "MODE_A", size=1, dataset_path="data/benchmark/v1.0/dataset.json")

print(f"Smoke test completed. {len(results)} tasks executed.")
if os.path.exists("experiments/SMOKE_TEST/checkpoint.json"):
    print("Checkpoint exists.")
if os.path.exists("experiments/SMOKE_TEST/experiment_manifest.json"):
    print("Manifest exists.")
if os.path.exists("experiments/SMOKE_TEST/feedback.json"):
    print("Feedback exists.")
    
raw_tasks = os.listdir("experiments/SMOKE_TEST/raw_tasks")
print(f"Raw tasks saved: {len(raw_tasks)}")
