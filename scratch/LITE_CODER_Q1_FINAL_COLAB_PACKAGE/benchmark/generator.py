import json
import os
import uuid
from typing import List
from benchmark.schemas import BenchmarkTask
from benchmark.fault_injector import FaultInjector, validate_mutation, calculate_complexity

BASE_PROGRAMS = [
    {
        "category": "arithmetic",
        "code": "def add(a, b):\n    return a + b",
        "tests": ["assert add(2, 3) == 5", "assert add(-1, 1) == 0"]
    },
    {
        "category": "algorithms",
        "code": "def is_even(n):\n    return n % 2 == 0",
        "tests": ["assert is_even(2) == True", "assert is_even(3) == False"]
    },
    {
        "category": "logic",
        "code": "def max_val(a, b):\n    if a > b:\n        return a\n    return b",
        "tests": ["assert max_val(10, 5) == 10", "assert max_val(3, 7) == 7"]
    },
    {
        "category": "strings",
        "code": "def concat(a, b):\n    return a + b",
        "tests": ["assert concat('a', 'b') == 'ab'"]
    },
    {
        "category": "arithmetic",
        "code": "def multiply(a, b):\n    return a * b",
        "tests": ["assert multiply(3, 4) == 12"]
    },
    {
        "category": "logic",
        "code": "def in_range(val, minimum, maximum):\n    return val >= minimum and val <= maximum",
        "tests": ["assert in_range(5, 1, 10) == True", "assert in_range(0, 1, 10) == False"]
    }
]

def generate_dataset(size: int = 20, output_path: str = "data/benchmark/dataset.json"):
    injector = FaultInjector()
    tasks = []
    
    # We loop until we fulfill the size requirement, reusing base programs.
    idx = 0
    while len(tasks) < size:
        base = BASE_PROGRAMS[idx % len(BASE_PROGRAMS)]
        idx += 1
        
        # Inject fault
        res = injector.inject(base["code"])
        if not res["success"]:
            continue
            
        mutated_code = res["mutated_code"]
        fault = res["fault"]
        
        # Validate
        is_valid = validate_mutation(base["code"], mutated_code, base["tests"])
        if not is_valid:
            continue
            
        complexity = calculate_complexity(base["code"])
        
        task = BenchmarkTask(
            task_id=f"TASK_{uuid.uuid4().hex[:8].upper()}",
            category=base["category"],
            difficulty="EASY",
            prompt=f"Fix the following broken python code:\n\n{mutated_code}",
            reference_code=base["code"],
            broken_code=mutated_code,
            fault=fault,
            complexity=complexity,
            expected_tests=base["tests"],
            source="fault_injection_synthetic",
            version="2.0"
        )
        tasks.append(task)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump([t.dict() if hasattr(t, 'dict') else t.model_dump() for t in tasks], f, indent=4)
        
    import hashlib
    with open(output_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
        
    with open(output_path.replace("dataset.json", "dataset_hash.txt"), "w") as f:
        f.write(file_hash)
        
    print(f"Successfully generated and validated {len(tasks)} fault-injected tasks at {output_path}.")
    print(f"Dataset Hash: {file_hash}")
    return tasks

if __name__ == "__main__":
    generate_dataset(100, "data/benchmark/v1.0/dataset.json")
