"""
benchmarks/q1_benchmark/tasks/all_tasks.py
==========================================
Aggregator for the complete 100-Task Q1 Evaluation Benchmark Suite.
Comprises:
- 20 Strings & Sequences
- 20 Arrays, Pointers & Sliding Window
- 20 Sorting, Binary Search & Intervals
- 20 Hashing, Frequencies & Sets
- 10 Data Immutability & Contract Traps
- 10 Adversarial / Flawed Oracles (Negative Controls)
Total: Exactly 100 tasks.
"""

from typing import List, Dict, Any
from benchmarks.q1_benchmark.tasks.strings import STRINGS_TASKS
from benchmarks.q1_benchmark.tasks.arrays import ARRAYS_TASKS
from benchmarks.q1_benchmark.tasks.sort_search import SORT_SEARCH_TASKS
from benchmarks.q1_benchmark.tasks.hashing import HASHING_TASKS
from benchmarks.q1_benchmark.tasks.immutability import IMMUTABILITY_TASKS
from benchmarks.q1_benchmark.tasks.negative_controls import NEGATIVE_CONTROLS

# 90 Evaluated Functional Tasks
EVALUATION_TASKS: List[Dict[str, Any]] = (
    STRINGS_TASKS +
    ARRAYS_TASKS +
    SORT_SEARCH_TASKS +
    HASHING_TASKS +
    IMMUTABILITY_TASKS
)

# Complete 100 Tasks including Negative Controls
ALL_100_TASKS: List[Dict[str, Any]] = EVALUATION_TASKS + NEGATIVE_CONTROLS

# Category mapping
CATEGORY_COUNTS = {
    "Strings & Sequences": len(STRINGS_TASKS),
    "Arrays & Pointers": len(ARRAYS_TASKS),
    "Sorting & Binary Search": len(SORT_SEARCH_TASKS),
    "Hashing & Frequencies": len(HASHING_TASKS),
    "Immutability & Contract": len(IMMUTABILITY_TASKS),
    "Adversarial Oracles": len(NEGATIVE_CONTROLS),
    "TOTAL": len(ALL_100_TASKS)
}
