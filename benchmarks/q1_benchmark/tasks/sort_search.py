"""
benchmarks/q1_benchmark/tasks/sort_search.py
=============================================
20 Sorting, Binary Search & Intervals benchmark tasks for Q1 Journal Evaluation.
"""

SORT_SEARCH_TASKS = [
    {
        "task_id": "TASK_SRT_01",
        "task_name": "binary_search_first_occurrence",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def binary_search_first_occurrence(arr: list, target: int) -> int:
    """
    Find the index of the first occurrence of target in sorted ascending list arr.
    Requirements:
    1. Returns 0-based index of first occurrence.
    2. Returns -1 if target is not found.
    3. Handles empty input list by returning -1.
    4. Do not modify input list.
    """
''',
        "seeded_defect": '''def binary_search_first_occurrence(arr: list, target: int) -> int:
    # Seeded defect: returns arbitrary midpoint on duplicate match
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
''',
        "defect_description": "Returns arbitrary matching index rather than scanning left for first occurrence",
        "authoritative_tests": [
            "assert binary_search_first_occurrence([1, 2, 2, 2, 3], 2) == 1",
            "assert binary_search_first_occurrence([2, 2, 2, 2], 2) == 0",
            "assert binary_search_first_occurrence([1, 3, 5, 7], 4) == -1",
            "assert binary_search_first_occurrence([], 1) == -1"
        ]
    },
    {
        "task_id": "TASK_SRT_02",
        "task_name": "binary_search_last_occurrence",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def binary_search_last_occurrence(arr: list, target: int) -> int:
    """
    Find index of last occurrence of target in sorted ascending list arr.
    Requirements:
    1. Returns 0-based index of last occurrence.
    2. Returns -1 if target is not found.
    3. Empty list returns -1.
    """
''',
        "seeded_defect": '''def binary_search_last_occurrence(arr: list, target: int) -> int:
    # Seeded defect: returns first occurrence instead of last
    if target not in arr: return -1
    return arr.index(target)
''',
        "defect_description": "Uses arr.index() which returns first occurrence instead of last",
        "authoritative_tests": [
            "assert binary_search_last_occurrence([1, 2, 2, 2, 3], 2) == 3",
            "assert binary_search_last_occurrence([2, 2, 2], 2) == 2",
            "assert binary_search_last_occurrence([1, 3, 5], 2) == -1",
            "assert binary_search_last_occurrence([], 5) == -1"
        ]
    },
    {
        "task_id": "TASK_SRT_03",
        "task_name": "search_insert_position",
        "domain": "Sorting & Binary Search",
        "difficulty": "EASY",
        "prompt": '''def search_insert_position(nums: list, target: int) -> int:
    """
    Return index if target is found. If not, return index where it would be if inserted in order.
    Requirements:
    1. nums is sorted ascending with distinct values.
    2. O(log n) time complexity.
    """
''',
        "seeded_defect": '''def search_insert_position(nums: list, target: int) -> int:
    # Seeded defect: off-by-one returns high instead of low
    low, high = 0, len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target: return mid
        elif nums[mid] < target: low = mid + 1
        else: high = mid - 1
    return high
''',
        "defect_description": "Returns high instead of low when target is not found",
        "authoritative_tests": [
            "assert search_insert_position([1, 3, 5, 6], 5) == 2",
            "assert search_insert_position([1, 3, 5, 6], 2) == 1",
            "assert search_insert_position([1, 3, 5, 6], 7) == 4",
            "assert search_insert_position([1, 3, 5, 6], 0) == 0"
        ]
    },
    {
        "task_id": "TASK_SRT_04",
        "task_name": "search_in_rotated_sorted",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def search_in_rotated_sorted(nums: list, target: int) -> int:
    """
    Search for target in sorted array that was rotated at an unknown pivot.
    Requirements:
    1. All values in nums are unique.
    2. Return index of target, or -1 if not found.
    3. O(log n) time complexity.
    """
''',
        "seeded_defect": '''def search_in_rotated_sorted(nums: list, target: int) -> int:
    # Seeded defect: assumes array is not rotated
    low, high = 0, len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target: return mid
        elif nums[mid] < target: low = mid + 1
        else: high = mid - 1
    return -1
''',
        "defect_description": "Standard binary search that fails on rotated arrays",
        "authoritative_tests": [
            "assert search_in_rotated_sorted([4, 5, 6, 7, 0, 1, 2], 0) == 4",
            "assert search_in_rotated_sorted([4, 5, 6, 7, 0, 1, 2], 3) == -1",
            "assert search_in_rotated_sorted([1], 0) == -1",
            "assert search_in_rotated_sorted([3, 1], 1) == 1"
        ]
    },
    {
        "task_id": "TASK_SRT_05",
        "task_name": "find_min_in_rotated_sorted",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def find_min_in_rotated_sorted(nums: list) -> int:
    """
    Find minimum element in sorted array rotated between 1 and n times.
    Requirements:
    1. All values are unique.
    2. Runs in O(log n).
    """
''',
        "seeded_defect": '''def find_min_in_rotated_sorted(nums: list) -> int:
    # Seeded defect: compares nums[mid] to nums[low] instead of nums[high]
    low, high = 0, len(nums) - 1
    while low < high:
        mid = (low + high) // 2
        if nums[mid] > nums[low]:
            low = mid + 1
        else:
            high = mid
    return nums[low]
''',
        "defect_description": "Compares against low pointer instead of high pointer, breaking sorted arrays",
        "authoritative_tests": [
            "assert find_min_in_rotated_sorted([3, 4, 5, 1, 2]) == 1",
            "assert find_min_in_rotated_sorted([4, 5, 6, 7, 0, 1, 2]) == 0",
            "assert find_min_in_rotated_sorted([11, 13, 15, 17]) == 11",
            "assert find_min_in_rotated_sorted([2, 1]) == 1"
        ]
    },
    {
        "task_id": "TASK_SRT_06",
        "task_name": "merge_intervals",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def merge_intervals(intervals: list) -> list:
    """
    Merge all overlapping intervals and return resulting list.
    Requirements:
    1. Merge overlapping intervals where next start <= current end.
    2. Return intervals sorted by start time.
    3. Input list must not be modified.
    """
''',
        "seeded_defect": '''def merge_intervals(intervals: list) -> list:
    # Seeded defect: does not sort intervals before merging
    if not intervals: return []
    merged = [intervals[0]]
    for cur in intervals[1:]:
        if cur[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], cur[1])
        else:
            merged.append(cur)
    return merged
''',
        "defect_description": "Fails to sort intervals by start time before linear scan",
        "authoritative_tests": [
            "assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]",
            "assert merge_intervals([[2, 3], [4, 5], [6, 7], [8, 9], [1, 10]]) == [[1, 10]]",
            "assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]",
            "assert merge_intervals([]) == []"
        ]
    },
    {
        "task_id": "TASK_SRT_07",
        "task_name": "insert_interval",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def insert_interval(intervals: list, new_interval: list) -> list:
    """
    Insert new_interval into non-overlapping sorted intervals, merging if necessary.
    Requirements:
    1. Return new list of intervals.
    2. Original intervals list must not be modified.
    """
''',
        "seeded_defect": '''def insert_interval(intervals: list, new_interval: list) -> list:
    # Seeded defect: appends and doesn't merge overlapping
    return sorted(intervals + [new_interval])
''',
        "defect_description": "Appends interval without merging overlapping neighbors",
        "authoritative_tests": [
            "assert insert_interval([[1, 3], [6, 9]], [2, 5]) == [[1, 5], [6, 9]]",
            "assert insert_interval([[1, 2], [3, 5], [6, 7], [8, 10], [12, 16]], [4, 8]) == [[1, 2], [3, 10], [12, 16]]",
            "assert insert_interval([], [5, 7]) == [[5, 7]]"
        ]
    },
    {
        "task_id": "TASK_SRT_08",
        "task_name": "non_overlapping_intervals_to_remove",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def non_overlapping_intervals_to_remove(intervals: list) -> int:
    """
    Find minimum number of intervals to remove to make the rest non-overlapping.
    Requirements:
    1. Intervals touching at points like [1, 2] and [2, 3] do not overlap.
    2. Empty or single interval returns 0.
    """
''',
        "seeded_defect": '''def non_overlapping_intervals_to_remove(intervals: list) -> int:
    # Seeded defect: sorts by start time instead of end time (greedy error)
    if not intervals: return 0
    intervals = sorted(intervals, key=lambda x: x[0])
    removals = 0
    end = intervals[0][1]
    for i in range(1, len(intervals)):
        if intervals[i][0] < end:
            removals += 1
        else:
            end = intervals[i][1]
    return removals
''',
        "defect_description": "Sorts by start time instead of end time, yielding suboptimal removals",
        "authoritative_tests": [
            "assert non_overlapping_intervals_to_remove([[1, 2], [2, 3], [3, 4], [1, 3]]) == 1",
            "assert non_overlapping_intervals_to_remove([[1, 2], [1, 2], [1, 2]]) == 2",
            "assert non_overlapping_intervals_to_remove([[1, 2], [2, 3]]) == 0",
            "assert non_overlapping_intervals_to_remove([]) == 0"
        ]
    },
    {
        "task_id": "TASK_SRT_09",
        "task_name": "min_meeting_rooms",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def min_meeting_rooms(intervals: list) -> int:
    """
    Find minimum number of conference rooms required.
    Requirements:
    1. Each interval is [start, end].
    2. If meeting ends at time t and next begins at t, same room can be used.
    3. Empty list returns 0.
    """
''',
        "seeded_defect": '''def min_meeting_rooms(intervals: list) -> int:
    # Seeded defect: checks max overlap at 0 only
    if not intervals: return 0
    return len(intervals)
''',
        "defect_description": "Returns total interval count instead of calculating concurrent overlap",
        "authoritative_tests": [
            "assert min_meeting_rooms([[0, 30], [5, 10], [15, 20]]) == 2",
            "assert min_meeting_rooms([[7, 10], [2, 4]]) == 1",
            "assert min_meeting_rooms([]) == 0",
            "assert min_meeting_rooms([[1, 5], [5, 10]]) == 1"
        ]
    },
    {
        "task_id": "TASK_SRT_10",
        "task_name": "kth_largest_element",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def kth_largest_element(nums: list, k: int) -> int:
    """
    Find the kth largest element in an unsorted array.
    Requirements:
    1. It is the kth largest in sorted order, not kth distinct.
    2. 1 <= k <= len(nums).
    3. Do not modify original list.
    """
''',
        "seeded_defect": '''def kth_largest_element(nums: list, k: int) -> int:
    # Seeded defect: mutates input nums in place via sort() and picks kth distinct
    nums.sort()
    unique = sorted(list(set(nums)))
    return unique[-k]
''',
        "defect_description": "Mutates input list and finds kth distinct element instead of kth element",
        "authoritative_tests": [
            "orig = [3, 2, 1, 5, 6, 4]; res = kth_largest_element(orig, 2); assert res == 5 and orig == [3, 2, 1, 5, 6, 4]",
            "assert kth_largest_element([3, 2, 3, 1, 2, 4, 5, 5, 6], 4) == 4",
            "assert kth_largest_element([1], 1) == 1"
        ]
    },
    {
        "task_id": "TASK_SRT_11",
        "task_name": "top_k_frequent_elements",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def top_k_frequent_elements(nums: list, k: int) -> list:
    """
    Return the k most frequent elements in nums.
    Requirements:
    1. Return list in any order.
    2. Guaranteed that answer is unique.
    """
''',
        "seeded_defect": '''def top_k_frequent_elements(nums: list, k: int) -> list:
    # Seeded defect: returns k least frequent elements
    from collections import Counter
    c = Counter(nums)
    return [x[0] for x in c.most_common()][-k:]
''',
        "defect_description": "Returns k least frequent elements instead of top k most frequent",
        "authoritative_tests": [
            "res = top_k_frequent_elements([1, 1, 1, 2, 2, 3], 2); assert set(res) == {1, 2}",
            "assert top_k_frequent_elements([1], 1) == [1]",
            "res2 = top_k_frequent_elements([4, 1, -1, 2, -1, 2, 3], 2); assert set(res2) == {-1, 2}"
        ]
    },
    {
        "task_id": "TASK_SRT_12",
        "task_name": "sort_colors_dutch_flag",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def sort_colors_dutch_flag(nums: list) -> list:
    """
    Given array nums with 0s, 1s, and 2s (red, white, blue), return a sorted array.
    Requirements:
    1. Returns a new sorted list.
    2. Does not modify original list nums.
    """
''',
        "seeded_defect": '''def sort_colors_dutch_flag(nums: list) -> list:
    # Seeded defect: mutates input in place using sort()
    nums.sort()
    return nums
''',
        "defect_description": "In-place mutation of input list",
        "authoritative_tests": [
            "orig = [2, 0, 2, 1, 1, 0]; res = sort_colors_dutch_flag(orig); assert res == [0, 0, 1, 1, 2, 2] and orig == [2, 0, 2, 1, 1, 0]",
            "assert sort_colors_dutch_flag([2, 0, 1]) == [0, 1, 2]",
            "assert sort_colors_dutch_flag([0]) == [0]"
        ]
    },
    {
        "task_id": "TASK_SRT_13",
        "task_name": "find_median_sorted_arrays",
        "domain": "Sorting & Binary Search",
        "difficulty": "HARD",
        "prompt": '''def find_median_sorted_arrays(nums1: list, nums2: list) -> float:
    """
    Find the median of two sorted arrays nums1 and nums2.
    Requirements:
    1. Overall run time complexity should be O(log(m+n)).
    2. Returns float.
    """
''',
        "seeded_defect": '''def find_median_sorted_arrays(nums1: list, nums2: list) -> float:
    # Seeded defect: integer division causes precision loss on even length
    merged = sorted(nums1 + nums2)
    n = len(merged)
    if n % 2 == 1: return float(merged[n // 2])
    return float((merged[n // 2] + merged[n // 2 - 1]) // 2)
''',
        "defect_description": "Integer division floor truncates the average of two medians",
        "authoritative_tests": [
            "assert find_median_sorted_arrays([1, 3], [2]) == 2.0",
            "assert find_median_sorted_arrays([1, 2], [3, 4]) == 2.5",
            "assert find_median_sorted_arrays([0, 0], [0, 0]) == 0.0"
        ]
    },
    {
        "task_id": "TASK_SRT_14",
        "task_name": "search_2d_matrix",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def search_2d_matrix(matrix: list, target: int) -> bool:
    """
    Search for target in m x n integer matrix where:
    - Each row is sorted ascending.
    - First integer of each row is greater than last integer of previous row.
    Requirements:
    1. Returns True if target in matrix, else False.
    2. Runs in O(log(m * n)).
    """
''',
        "seeded_defect": '''def search_2d_matrix(matrix: list, target: int) -> bool:
    # Seeded defect: checks only first and last column
    if not matrix or not matrix[0]: return False
    return target in [row[0] for row in matrix] or target in [row[-1] for row in matrix]
''',
        "defect_description": "Only inspects outer boundary columns, missing interior elements",
        "authoritative_tests": [
            "m = [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]]; assert search_2d_matrix(m, 3) is True",
            "m = [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]]; assert search_2d_matrix(m, 13) is False",
            "assert search_2d_matrix([], 1) is False"
        ]
    },
    {
        "task_id": "TASK_SRT_15",
        "task_name": "custom_sort_by_frequency",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def custom_sort_by_frequency(nums: list) -> list:
    """
    Sort array in increasing order based on the frequency of values.
    Requirements:
    1. If multiple values have same frequency, sort them in decreasing order of value.
    2. Return new list without modifying original.
    """
''',
        "seeded_defect": '''def custom_sort_by_frequency(nums: list) -> list:
    # Seeded defect: sorts ties in ascending order instead of decreasing
    from collections import Counter
    c = Counter(nums)
    return sorted(nums, key=lambda x: (c[x], x))
''',
        "defect_description": "Sorts frequency ties in ascending order instead of descending",
        "authoritative_tests": [
            "assert custom_sort_by_frequency([1, 1, 2, 2, 2, 3]) == [3, 1, 1, 2, 2, 2]",
            "assert custom_sort_by_frequency([2, 3, 1, 3, 2]) == [1, 3, 3, 2, 2]",
            "assert custom_sort_by_frequency([-1, 1, -6, 4, 5, -6, 1, 4, 1]) == [5, -1, 4, 4, -6, -6, 1, 1, 1]"
        ]
    },
    {
        "task_id": "TASK_SRT_16",
        "task_name": "merge_k_sorted_lists",
        "domain": "Sorting & Binary Search",
        "difficulty": "HARD",
        "prompt": '''def merge_k_sorted_lists(lists: list) -> list:
    """
    Merge k sorted integer lists and return one sorted list.
    Requirements:
    1. Output is sorted ascending.
    2. Input lists must not be modified.
    """
''',
        "seeded_defect": '''def merge_k_sorted_lists(lists: list) -> list:
    # Seeded defect: pops elements from sublists, modifying input structures
    res = []
    for l in lists:
        while l:
            res.append(l.pop(0))
    return sorted(res)
''',
        "defect_description": "Mutates sublists in-place with pop(0)",
        "authoritative_tests": [
            "l = [[1, 4, 5], [1, 3, 4], [2, 6]]; res = merge_k_sorted_lists(l); assert res == [1, 1, 2, 3, 4, 4, 5, 6] and len(l[0]) == 3",
            "assert merge_k_sorted_lists([]) == []",
            "assert merge_k_sorted_lists([[]]) == []"
        ]
    },
    {
        "task_id": "TASK_SRT_17",
        "task_name": "find_first_and_last_position",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def find_first_and_last_position(nums: list, target: int) -> list:
    """
    Find starting and ending position of target in sorted nums.
    Requirements:
    1. Returns [start, end].
    2. If target not found, return [-1, -1].
    3. Runs in O(log n).
    """
''',
        "seeded_defect": '''def find_first_and_last_position(nums: list, target: int) -> list:
    # Seeded defect: returns [mid, mid] without boundary expansion
    if target not in nums: return [-1, -1]
    idx = nums.index(target)
    return [idx, idx]
''',
        "defect_description": "Returns single index for both start and end positions",
        "authoritative_tests": [
            "assert find_first_and_last_position([5, 7, 7, 8, 8, 10], 8) == [3, 4]",
            "assert find_first_and_last_position([5, 7, 7, 8, 8, 10], 6) == [-1, -1]",
            "assert find_first_and_last_position([], 0) == [-1, -1]",
            "assert find_first_and_last_position([1], 1) == [0, 0]"
        ]
    },
    {
        "task_id": "TASK_SRT_18",
        "task_name": "h_index",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def h_index(citations: list) -> int:
    """
    Calculate researcher's h-index from array of citations.
    Requirements:
    1. h-index is max value h such that at least h papers have >= h citations.
    2. Empty list returns 0.
    """
''',
        "seeded_defect": '''def h_index(citations: list) -> int:
    # Seeded defect: sorts ascending and breaks indexing logic
    citations.sort()
    for i, c in enumerate(citations):
        if c >= len(citations) - i:
            return c
    return 0
''',
        "defect_description": "Returns paper citation count rather than rank h, and mutates input list",
        "authoritative_tests": [
            "assert h_index([3, 0, 6, 1, 5]) == 3",
            "assert h_index([1, 3, 1]) == 1",
            "assert h_index([]) == 0",
            "assert h_index([100]) == 1"
        ]
    },
    {
        "task_id": "TASK_SRT_19",
        "task_name": "interval_intersection",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def interval_intersection(first_list: list, second_list: list) -> list:
    """
    Return intersection of two closed interval lists.
    Requirements:
    1. Returns list of overlapping closed intervals.
    2. If no intersection, return [].
    """
''',
        "seeded_defect": '''def interval_intersection(first_list: list, second_list: list) -> list:
    # Seeded defect: only compares intervals with equal indices i == j
    res = []
    for i in range(min(len(first_list), len(second_list))):
        s = max(first_list[i][0], second_list[i][0])
        e = min(first_list[i][1], second_list[i][1])
        if s <= e: res.append([s, e])
    return res
''',
        "defect_description": "Lockstep index matching instead of two-pointer interval scan",
        "authoritative_tests": [
            "a = [[0, 2], [5, 10], [13, 23], [24, 25]]; b = [[1, 5], [8, 12], [15, 24], [25, 26]]; assert interval_intersection(a, b) == [[1, 2], [5, 5], [8, 10], [15, 23], [24, 24], [25, 25]]",
            "assert interval_intersection([[1, 3], [5, 9]], []) == []"
        ]
    },
    {
        "task_id": "TASK_SRT_20",
        "task_name": "car_fleet_count",
        "domain": "Sorting & Binary Search",
        "difficulty": "MEDIUM",
        "prompt": '''def car_fleet_count(target: int, position: list, speed: list) -> int:
    """
    Return number of car fleets that will arrive at the destination target.
    Requirements:
    1. A car cannot pass another car ahead; it catches up and becomes a fleet.
    2. Empty position returns 0.
    """
''',
        "seeded_defect": '''def car_fleet_count(target: int, position: list, speed: list) -> int:
    # Seeded defect: sorts by speed instead of position
    if not position: return 0
    cars = sorted(zip(position, speed), key=lambda x: x[1])
    return len(cars)
''',
        "defect_description": "Sorts by speed and fails to combine fleets based on arrival times",
        "authoritative_tests": [
            "assert car_fleet_count(12, [10, 8, 0, 5, 3], [2, 4, 1, 1, 3]) == 3",
            "assert car_fleet_count(10, [3], [3]) == 1",
            "assert car_fleet_count(100, [0, 2, 4], [4, 2, 1]) == 1"
        ]
    }
]
