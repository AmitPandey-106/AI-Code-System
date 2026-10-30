import json
import os
from typing import List, Dict, Any
from benchmark.schemas import BenchmarkTask

DATASET_PATH = "data/benchmark/dataset.json"

INITIAL_TASKS = [
    {
        "task_id": "T001",
        "category": "recursion",
        "difficulty": "EASY",
        "prompt": "Write a factorial function named factorial(n). Handle n=0.",
        "expected_tests": [
            "assert factorial(0) == 1",
            "assert factorial(5) == 120",
            "assert factorial(1) == 1"
        ],
        "source": "synthetic"
    },
    {
        "task_id": "T002",
        "category": "algorithms",
        "difficulty": "MEDIUM",
        "prompt": "Write a binary search implementation named binary_search(arr, target). Return index or -1.",
        "expected_tests": [
            "assert binary_search([1, 2, 3, 4, 5], 3) == 2",
            "assert binary_search([1, 2, 3, 4, 5], 6) == -1",
            "assert binary_search([], 1) == -1"
        ],
        "source": "synthetic"
    },
    {
        "task_id": "T003",
        "category": "strings",
        "difficulty": "EASY",
        "prompt": "Write a palindrome checker named is_palindrome(s). Ignore spaces and case.",
        "expected_tests": [
            "assert is_palindrome('A man a plan a canal Panama') == True",
            "assert is_palindrome('hello') == False",
            "assert is_palindrome('') == True"
        ],
        "source": "synthetic"
    },
    {
        "task_id": "T004",
        "category": "algorithms",
        "difficulty": "HARD",
        "prompt": "Write a quicksort implementation named quicksort(arr).",
        "expected_tests": [
            "assert quicksort([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]) == [1, 1, 2, 3, 3, 4, 5, 5, 5, 6, 9]",
            "assert quicksort([]) == []",
            "assert quicksort([1]) == [1]"
        ],
        "source": "synthetic"
    },
    {
        "task_id": "T005",
        "category": "recursion",
        "difficulty": "EASY",
        "prompt": "Write a fibonacci function named fibonacci(n) returning the nth number (0-indexed, fib(0)=0, fib(1)=1).",
        "expected_tests": [
            "assert fibonacci(0) == 0",
            "assert fibonacci(1) == 1",
            "assert fibonacci(5) == 5",
            "assert fibonacci(10) == 55"
        ],
        "source": "synthetic"
    },
    {
        "task_id": "T006",
        "category": "algorithms",
        "difficulty": "MEDIUM",
        "prompt": "Write a prime number checker named is_prime(n).",
        "expected_tests": [
            "assert is_prime(2) == True",
            "assert is_prime(4) == False",
            "assert is_prime(1) == False",
            "assert is_prime(17) == True"
        ],
        "source": "synthetic"
    }
]

def generate_dataset():
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    if not os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "w") as f:
            json.dump(INITIAL_TASKS, f, indent=4)
        print(f"Generated default dataset at {DATASET_PATH}")

def load_dataset(path: str = "data/benchmark/dataset.json") -> List[BenchmarkTask]:
    """Loads the benchmark dataset from JSON."""
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        data = json.load(f)
    return [BenchmarkTask(**task) for task in data]
