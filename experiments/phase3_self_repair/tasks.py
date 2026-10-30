"""
experiments/phase3_self_repair/tasks.py
========================================
Defines the five evaluation tasks across distinct domains with deliberately
seeded defects for the Phase 3 closed-loop self-repair experiment, along
with negative control fixtures.
"""

from typing import Dict, Any, List


TASKS: List[Dict[str, Any]] = [
    {
        "task_id": "TASK_1",
        "task_name": "add",
        "domain": "Arithmetic",
        "prompt": """Implement the following Python function:

def add(a, b):
    \"\"\"Return the sum of a and b.\"\"\"
    Requirements:
    1. Calculate and return the sum of a and b.
    2. Handle positive numbers, negative numbers, and zero.
""",
        "seeded_defect": """def add(a, b):
    # Seeded defect: subtraction instead of addition
    return a - b
""",
        "defect_description": "Subtracted instead of added (return a - b)",
        "authoritative_tests": [
            "assert add(2, 3) == 5",
            "assert add(0, 0) == 0",
            "assert add(-1, 1) == 0",
            "assert add(-5, -5) == -10",
            "assert add(100, 250) == 350"
        ]
    },
    {
        "task_id": "TASK_2",
        "task_name": "reverse_string",
        "domain": "String Processing",
        "prompt": """Implement the following Python function:

def reverse_string(s):
    \"\"\"Return the input string reversed.\"\"\"
    Requirements:
    1. Return the reversed string.
    2. Empty string works and returns empty string.
    3. Single character works.
    4. Spaces are preserved.
    5. Punctuation is preserved.
    6. Input string is not modified.
""",
        "seeded_defect": """def reverse_string(s):
    # Seeded defect: returns string unchanged
    return s
""",
        "defect_description": "Returns string unchanged (identity return)",
        "authoritative_tests": [
            "assert reverse_string('hello') == 'olleh'",
            "assert reverse_string('') == ''",
            "assert reverse_string('a') == 'a'",
            "assert reverse_string('hello world') == 'dlrow olleh'",
            "assert reverse_string('racecar') == 'racecar'",
            "assert reverse_string('123!') == '!321'"
        ]
    },
    {
        "task_id": "TASK_3",
        "task_name": "binary_search",
        "domain": "Searching",
        "prompt": """Implement the following Python function:

def binary_search(arr, target):
    \"\"\"Perform binary search on a sorted ascending list and return the index of target.\"\"\"
    Requirements:
    1. Sorted ascending input list arr.
    2. Return target index if found.
    3. Return -1 when target is absent.
    4. Return the first occurrence when duplicates exist.
    5. Do not modify input list.
    6. Handle empty input list by returning -1.
""",
        "seeded_defect": """def binary_search(arr, target):
    # Seeded defect: returns first matching midpoint immediately without finding first occurrence
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
""",
        "defect_description": "Returns arbitrary matching midpoint on duplicates instead of first occurrence",
        "authoritative_tests": [
            "assert binary_search([1, 3, 5, 7, 9], 5) == 2",
            "assert binary_search([1, 3, 5, 7], 2) == -1",
            "assert binary_search([], 1) == -1",
            "assert binary_search([1, 2, 2, 2, 3], 2) == 1",
            "assert binary_search([2, 2, 2], 2) == 0",
            "assert binary_search([10], 10) == 0"
        ]
    },
    {
        "task_id": "TASK_4",
        "task_name": "merge_intervals",
        "domain": "Interval Processing",
        "prompt": """Implement the following Python function:

def merge_intervals(intervals):
    \"\"\"Merge all overlapping intervals and return the result.\"\"\"
    Requirements:
    1. Merge overlapping intervals where next start <= current end.
    2. Output intervals sorted by start time.
    3. Empty input list supported and returns [].
    4. Input list must not be modified.
    5. Output must contain new interval objects.
""",
        "seeded_defect": """def merge_intervals(intervals):
    # Seeded defect: returns intervals without merging
    return [list(x) for x in intervals]
""",
        "defect_description": "Fails to merge overlapping intervals",
        "authoritative_tests": [
            "assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]",
            "assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]",
            "assert merge_intervals([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]",
            "assert merge_intervals([]) == []",
            "assert merge_intervals([[5, 10]]) == [[5, 10]]"
        ]
    },
    {
        "task_id": "TASK_5",
        "task_name": "schedule_meetings",
        "domain": "Difficult Structured Task",
        "prompt": """Implement the following Python function:

def schedule_meetings(meetings):
    \"\"\"
    Merge overlapping meetings and return the resulting schedule.

    Each meeting is represented as a dictionary:
        {
            "title": str,
            "start": int,
            "end": int
        }

    Requirements:

    1. Meetings must be ordered by start time before merging.

    2. Two meetings overlap when the next meeting's start time is
       strictly less than the current merged meeting's end time.

    3. Meetings that only touch at a boundary must NOT be merged.
       For example:
           [9, 10] and [10, 11]
       must remain separate.

    4. When overlapping meetings are merged:
       - start = earliest start time
       - end = latest end time
       - title = titles of all merged meetings joined using " + "
         in their original chronological order.

    5. If multiple meetings have the same start time, preserve their
       original input order when determining title order.

    6. Meetings with end <= start are invalid and must be ignored.

    7. The input list must not be modified.

    8. The original meeting dictionaries must not be modified.

    9. The returned meetings must be newly created dictionaries.

    10. Return an empty list when the input contains no valid meetings.

    11. The returned list must be sorted by start time.
    \"\"\"
""",
        "seeded_defect": """def schedule_meetings(meetings):
    # Seeded defect: mutates input list in place via sort() and fails to merge
    meetings.sort(key=lambda x: x['start'])
    valid = [dict(m) for m in meetings if m['end'] > m['start']]
    if not valid:
        return []
    return valid
""",
        "defect_description": "In-place sort() mutation on input list and failing to merge overlapping meetings",
        "authoritative_tests": [
            "m1 = [{'title': 'A', 'start': 9, 'end': 11}, {'title': 'B', 'start': 10, 'end': 12}, {'title': 'C', 'start': 12, 'end': 13}]; assert schedule_meetings(m1) == [{'title': 'A + B', 'start': 9, 'end': 12}, {'title': 'C', 'start': 12, 'end': 13}]",
            "m_touch = [{'title': 'X', 'start': 9, 'end': 10}, {'title': 'Y', 'start': 10, 'end': 11}]; assert schedule_meetings(m_touch) == [{'title': 'X', 'start': 9, 'end': 10}, {'title': 'Y', 'start': 10, 'end': 11}]",
            "m_inv = [{'title': 'Bad', 'start': 12, 'end': 10}, {'title': 'Good', 'start': 1, 'end': 2}]; assert schedule_meetings(m_inv) == [{'title': 'Good', 'start': 1, 'end': 2}]",
            "assert schedule_meetings([]) == []"
        ]
    }
]


NEGATIVE_CONTROLS: List[Dict[str, Any]] = [
    {
        "control_id": "NC_1",
        "name": "Invalid Test Syntax",
        "prompt": "def add(a, b): return a + b",
        "candidate": "def add(a, b): return a + b",
        "test": "assert add(2, 3 == ",
        "expected_failure": "TEST_GENERATION_FAILURE"
    },
    {
        "control_id": "NC_2",
        "name": "Contradictory Oracle",
        "prompt": """Implement the following Python function:

def filter_records(records, n):
    \"\"\"Filter records based on limit n.\"\"\"
    Requirements:
    1. If n <= 0, return []
    2. Return at most n records
""",
        "candidate": "def filter_records(records, n):\n    if n <= 0:\n        return []\n    return records[:n]",
        "test": "assert filter_records([{'id': 1}], 0) == [{'id': 1}]",
        "expected_failure": "TEST_ORACLE_FAILURE"
    },
    {
        "control_id": "NC_3",
        "name": "Undetermined Oracle",
        "prompt": "def process_data(items): return items",
        "candidate": "def process_data(items): return items",
        "test": "assert process_data([1, 2]) == [1, 2]",
        "expected_state": "UNDETERMINED"
    }
]
