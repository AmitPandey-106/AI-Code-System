"""
benchmarks/q1_benchmark/tasks/immutability.py
=============================================
10 Data Immutability & Contract Trap benchmark tasks for Q1 Journal Evaluation.
These specifically evaluate LITE-Coder's AST contract enforcement against
accidental caller-side state mutations.
"""

IMMUTABILITY_TASKS = [
    {
        "task_id": "TASK_IMM_01",
        "task_name": "sort_without_mutation",
        "domain": "Immutability & Contract",
        "difficulty": "EASY",
        "prompt": '''def sort_without_mutation(arr: list) -> list:
    """
    Return a new list containing elements of arr sorted in ascending order.
    Requirements:
    1. The input list arr must NOT be modified.
    2. Returns a newly created sorted list.
    """
''',
        "seeded_defect": '''def sort_without_mutation(arr: list) -> list:
    # Seeded defect: mutates input list in-place via sort()
    arr.sort()
    return arr
''',
        "defect_description": "In-place arr.sort() modifies caller data structure",
        "authoritative_tests": [
            "orig = [5, 2, 8, 1]; res = sort_without_mutation(orig); assert res == [1, 2, 5, 8] and orig == [5, 2, 8, 1]",
            "orig2 = [1]; res2 = sort_without_mutation(orig2); assert res2 == [1] and orig2 == [1]",
            "orig3 = []; res3 = sort_without_mutation(orig3); assert res3 == [] and orig3 == []"
        ]
    },
    {
        "task_id": "TASK_IMM_02",
        "task_name": "reverse_without_mutation",
        "domain": "Immutability & Contract",
        "difficulty": "EASY",
        "prompt": '''def reverse_without_mutation(arr: list) -> list:
    """
    Return a new list containing elements of arr in reversed order.
    Requirements:
    1. The input list arr must NOT be modified.
    2. Returns a newly created reversed list.
    """
''',
        "seeded_defect": '''def reverse_without_mutation(arr: list) -> list:
    # Seeded defect: in-place reverse()
    arr.reverse()
    return arr
''',
        "defect_description": "In-place arr.reverse() modifies caller data structure",
        "authoritative_tests": [
            "orig = [1, 2, 3, 4]; res = reverse_without_mutation(orig); assert res == [4, 3, 2, 1] and orig == [1, 2, 3, 4]",
            "orig2 = []; res2 = reverse_without_mutation(orig2); assert res2 == [] and orig2 == []"
        ]
    },
    {
        "task_id": "TASK_IMM_03",
        "task_name": "remove_evens_without_mutation",
        "domain": "Immutability & Contract",
        "difficulty": "EASY",
        "prompt": '''def remove_evens_without_mutation(arr: list) -> list:
    """
    Return a list containing only the odd numbers from arr.
    Requirements:
    1. Input list arr must NOT be modified.
    2. Preserves relative order of odd elements.
    """
''',
        "seeded_defect": '''def remove_evens_without_mutation(arr: list) -> list:
    # Seeded defect: mutates arr in place using remove()
    for x in list(arr):
        if x % 2 == 0:
            arr.remove(x)
    return arr
''',
        "defect_description": "Modifies input list in-place using arr.remove()",
        "authoritative_tests": [
            "orig = [1, 2, 3, 4, 5, 6]; res = remove_evens_without_mutation(orig); assert res == [1, 3, 5] and orig == [1, 2, 3, 4, 5, 6]",
            "orig2 = [2, 4, 6]; res2 = remove_evens_without_mutation(orig2); assert res2 == [] and orig2 == [2, 4, 6]"
        ]
    },
    {
        "task_id": "TASK_IMM_04",
        "task_name": "truncate_list_without_mutation",
        "domain": "Immutability & Contract",
        "difficulty": "EASY",
        "prompt": '''def truncate_list_without_mutation(arr: list, n: int) -> list:
    """
    Return the first n elements of arr.
    Requirements:
    1. Input list arr must NOT be modified.
    2. If n >= len(arr), return a copy of entire list.
    3. If n <= 0, return [].
    """
''',
        "seeded_defect": '''def truncate_list_without_mutation(arr: list, n: int) -> list:
    # Seeded defect: deletes elements from input list using del slice
    del arr[n:]
    return arr
''',
        "defect_description": "Uses del arr[n:] which mutates caller input list",
        "authoritative_tests": [
            "orig = [10, 20, 30, 40, 50]; res = truncate_list_without_mutation(orig, 3); assert res == [10, 20, 30] and orig == [10, 20, 30, 40, 50]",
            "orig2 = [1, 2]; res2 = truncate_list_without_mutation(orig2, 0); assert res2 == [] and orig2 == [1, 2]"
        ]
    },
    {
        "task_id": "TASK_IMM_05",
        "task_name": "schedule_non_destructive",
        "domain": "Immutability & Contract",
        "difficulty": "MEDIUM",
        "prompt": '''def schedule_non_destructive(meetings: list) -> list:
    """
    Sort meetings by start time and filter out invalid meetings (end <= start).
    Each meeting is a dictionary: {'title': str, 'start': int, 'end': int}.
    Requirements:
    1. Input list and meeting dicts must NOT be modified.
    2. Returned list must contain newly created meeting dicts.
    """
''',
        "seeded_defect": '''def schedule_non_destructive(meetings: list) -> list:
    # Seeded defect: sorts meetings in-place
    meetings.sort(key=lambda m: m['start'])
    return [m for m in meetings if m['end'] > m['start']]
''',
        "defect_description": "Mutates input list in-place via meetings.sort()",
        "authoritative_tests": [
            "m = [{'title': 'B', 'start': 10, 'end': 11}, {'title': 'A', 'start': 9, 'end': 10}]; res = schedule_non_destructive(m); assert res[0]['title'] == 'A' and m[0]['title'] == 'B'",
            "assert schedule_non_destructive([]) == []"
        ]
    },
    {
        "task_id": "TASK_IMM_06",
        "task_name": "normalize_dict_keys_immutable",
        "domain": "Immutability & Contract",
        "difficulty": "EASY",
        "prompt": '''def normalize_dict_keys_immutable(d: dict) -> dict:
    """
    Return a new dictionary with all string keys converted to lowercase.
    Requirements:
    1. Input dictionary d must NOT be modified.
    2. Returns a new dictionary.
    """
''',
        "seeded_defect": '''def normalize_dict_keys_immutable(d: dict) -> dict:
    # Seeded defect: mutates input dictionary by popping and reassigning keys
    for k in list(d.keys()):
        val = d.pop(k)
        d[k.lower()] = val
    return d
''',
        "defect_description": "Mutates input dictionary using pop() and in-place assignment",
        "authoritative_tests": [
            "orig = {'Name': 'Alice', 'AGE': 30}; res = normalize_dict_keys_immutable(orig); assert res == {'name': 'Alice', 'age': 30} and 'Name' in orig",
            "assert normalize_dict_keys_immutable({}) == {}"
        ]
    },
    {
        "task_id": "TASK_IMM_07",
        "task_name": "pop_minimum_immutable",
        "domain": "Immutability & Contract",
        "difficulty": "EASY",
        "prompt": '''def pop_minimum_immutable(arr: list) -> tuple:
    """
    Find minimum element and return (min_val, remaining_list).
    Requirements:
    1. Input list arr must NOT be modified.
    2. remaining_list is a new list with first occurrence of min_val removed.
    """
''',
        "seeded_defect": '''def pop_minimum_immutable(arr: list) -> tuple:
    # Seeded defect: in-place pop from arr
    idx = arr.index(min(arr))
    val = arr.pop(idx)
    return (val, arr)
''',
        "defect_description": "In-place removal of element from input list using arr.pop()",
        "authoritative_tests": [
            "orig = [3, 1, 4, 1, 5]; val, rem = pop_minimum_immutable(orig); assert val == 1 and rem == [3, 4, 1, 5] and orig == [3, 1, 4, 1, 5]",
            "orig2 = [7]; val2, rem2 = pop_minimum_immutable(orig2); assert val2 == 7 and rem2 == [] and orig2 == [7]"
        ]
    },
    {
        "task_id": "TASK_IMM_08",
        "task_name": "append_tag_immutable",
        "domain": "Immutability & Contract",
        "difficulty": "EASY",
        "prompt": '''def append_tag_immutable(records: list, tag: str) -> list:
    """
    Return a new list of dictionaries with 'tag': tag added to each record.
    Requirements:
    1. Original records list and inner dictionaries must NOT be modified.
    2. Returns newly created dictionary objects.
    """
''',
        "seeded_defect": '''def append_tag_immutable(records: list, tag: str) -> list:
    # Seeded defect: mutates inner dictionaries in place
    for r in records:
        r['tag'] = tag
    return records
''',
        "defect_description": "Mutates caller dictionary objects in-place by assigning r['tag']",
        "authoritative_tests": [
            "r1 = {'id': 1}; recs = [r1]; res = append_tag_immutable(recs, 'v1'); assert res[0]['tag'] == 'v1' and 'tag' not in r1",
            "assert append_tag_immutable([], 'test') == []"
        ]
    },
    {
        "task_id": "TASK_IMM_09",
        "task_name": "filter_outliers_immutable",
        "domain": "Immutability & Contract",
        "difficulty": "EASY",
        "prompt": '''def filter_outliers_immutable(data: list, low: float, high: float) -> list:
    """
    Return elements from data that fall within [low, high].
    Requirements:
    1. Input list data must NOT be modified.
    2. Returns a new list.
    """
''',
        "seeded_defect": '''def filter_outliers_immutable(data: list, low: float, high: float) -> list:
    # Seeded defect: clears and re-extends caller list
    valid = [x for x in data if low <= x <= high]
    data.clear()
    data.extend(valid)
    return data
''',
        "defect_description": "Empties and refills caller list using data.clear()",
        "authoritative_tests": [
            "orig = [1.0, 10.5, 50.0, 3.2]; res = filter_outliers_immutable(orig, 2.0, 20.0); assert res == [10.5, 3.2] and len(orig) == 4",
            "assert filter_outliers_immutable([], 0, 10) == []"
        ]
    },
    {
        "task_id": "TASK_IMM_10",
        "task_name": "matrix_transpose_immutable",
        "domain": "Immutability & Contract",
        "difficulty": "MEDIUM",
        "prompt": '''def matrix_transpose_immutable(matrix: list) -> list:
    """
    Return the transpose of a 2D matrix.
    Requirements:
    1. Input matrix must NOT be modified.
    2. Returns newly constructed 2D list.
    """
''',
        "seeded_defect": '''def matrix_transpose_immutable(matrix: list) -> list:
    # Seeded defect: mutates matrix rows in place
    n = len(matrix)
    for i in range(n):
        for j in range(i+1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    return matrix
''',
        "defect_description": "Mutates input matrix cells in-place via matrix[i][j] swapping",
        "authoritative_tests": [
            "m = [[1, 2], [3, 4]]; res = matrix_transpose_immutable(m); assert res == [[1, 3], [2, 4]] and m == [[1, 2], [3, 4]]",
            "assert matrix_transpose_immutable([[1]]) == [[1]]"
        ]
    }
]
