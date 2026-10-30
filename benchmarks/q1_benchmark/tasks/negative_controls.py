"""
benchmarks/q1_benchmark/tasks/negative_controls.py
===================================================
10 Adversarial / Flawed Oracles (Negative Controls) for Q1 Journal Evaluation.
These verify that LITE-Coder isolates faulty, contaminated, or contradictory
test suites without corrupting valid candidate implementations.
"""

NEGATIVE_CONTROLS = [
    {
        "control_id": "TASK_NEG_01",
        "name": "Invalid Test Syntax",
        "domain": "Adversarial Oracles",
        "prompt": "def add(a, b): return a + b",
        "candidate": "def add(a, b):\n    return a + b",
        "test": "assert add(2, 3 == ",
        "expected_failure": "TEST_GENERATION_FAILURE"
    },
    {
        "control_id": "TASK_NEG_02",
        "name": "Contradictory Boundary Oracle",
        "domain": "Adversarial Oracles",
        "prompt": '''def filter_records(records, n):
    """Filter records based on limit n."""
    Requirements:
    1. If n <= 0, return []
    2. Return at most n records
''',
        "candidate": "def filter_records(records, n):\n    if n <= 0:\n        return []\n    return records[:n]",
        "test": "assert filter_records([{'id': 1}], 0) == [{'id': 1}]",
        "expected_failure": "TEST_ORACLE_FAILURE"
    },
    {
        "control_id": "TASK_NEG_03",
        "name": "Contradictory Dual Assertion",
        "domain": "Adversarial Oracles",
        "prompt": "def identity(x): return x",
        "candidate": "def identity(x):\n    return x",
        "test": "assert identity(5) == 5 and identity(5) == 10",
        "expected_failure": "TEST_ORACLE_FAILURE"
    },
    {
        "control_id": "TASK_NEG_04",
        "name": "Global Namespace Pollution Trap",
        "domain": "Adversarial Oracles",
        "prompt": "def compute(): return 42",
        "candidate": "def compute():\n    return 42",
        "test": "globals()['compute'] = lambda: 999; assert compute() == 42",
        "expected_failure": "TEST_HARNESS_FAILURE"
    },
    {
        "control_id": "TASK_NEG_05",
        "name": "Unorderable Types Comparison",
        "domain": "Adversarial Oracles",
        "prompt": "def get_val(): return 10",
        "candidate": "def get_val():\n    return 10",
        "test": "assert get_val() < 'string'",
        "expected_failure": "TEST_GENERATION_FAILURE"
    },
    {
        "control_id": "TASK_NEG_06",
        "name": "Impossible Empty vs Non-Empty Requirement",
        "domain": "Adversarial Oracles",
        "prompt": "def empty_checker(lst): return len(lst) == 0",
        "candidate": "def empty_checker(lst):\n    return len(lst) == 0",
        "test": "assert empty_checker([]) is False and empty_checker([1]) is True",
        "expected_failure": "TEST_ORACLE_FAILURE"
    },
    {
        "control_id": "TASK_NEG_07",
        "name": "Harness Monkey-Patch Injection Attack",
        "domain": "Adversarial Oracles",
        "prompt": "def safe_calc(x): return x * 2",
        "candidate": "def safe_calc(x):\n    return x * 2",
        "test": "class InjectedPollution: pass; globals()['safe_calc'] = InjectedPollution(); assert safe_calc(2) == 4",
        "expected_failure": "TEST_HARNESS_FAILURE"
    },
    {
        "control_id": "TASK_NEG_08",
        "name": "Missing Required Attribute Assumption",
        "domain": "Adversarial Oracles",
        "prompt": "def get_length(s): return len(s)",
        "candidate": "def get_length(s):\n    return len(s)",
        "test": "assert get_length('hello').non_existent_method() == 5",
        "expected_failure": "TEST_GENERATION_FAILURE"
    },
    {
        "control_id": "TASK_NEG_09",
        "name": "Direct Memory Pointer Comparison Contradiction",
        "domain": "Adversarial Oracles",
        "prompt": "def clone_list(arr): return list(arr)",
        "candidate": "def clone_list(arr):\n    return list(arr)",
        "test": "l = [1, 2]; assert clone_list(l) is l and clone_list(l) is not l",
        "expected_failure": "TEST_ORACLE_FAILURE"
    },
    {
        "control_id": "TASK_NEG_10",
        "name": "Undetermined Oracle State",
        "domain": "Adversarial Oracles",
        "prompt": "def process_data(items): return items",
        "candidate": "def process_data(items):\n    return items",
        "test": "assert process_data([1, 2]) == [1, 2]",
        "expected_state": "UNDETERMINED"
    }
]
