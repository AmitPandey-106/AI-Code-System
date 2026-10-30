"""
benchmarks/q1_benchmark/tasks/arrays.py
========================================
20 Arrays, Pointers & Sliding Window benchmark tasks for Q1 Journal Evaluation.
"""

ARRAYS_TASKS = [
    {
        "task_id": "TASK_ARR_01",
        "task_name": "two_sum",
        "domain": "Arrays & Pointers",
        "difficulty": "EASY",
        "prompt": '''def two_sum(nums: list, target: int) -> list:
    """
    Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.
    Requirements:
    1. Each input has exactly one solution.
    2. May not use the same element twice.
    3. Return 0-indexed list [i, j] with i < j.
    4. Do not modify input list.
    """
''',
        "seeded_defect": '''def two_sum(nums: list, target: int) -> list:
    # Seeded defect: can reuse the same element if target == 2 * nums[i]
    seen = {}
    for i, n in enumerate(nums):
        diff = target - n
        if diff in nums:
            return [i, nums.index(diff)]
    return []
''',
        "defect_description": "Can pick the same element twice or return unsorted indices",
        "authoritative_tests": [
            "assert two_sum([2, 7, 11, 15], 9) == [0, 1]",
            "assert two_sum([3, 2, 4], 6) == [1, 2]",
            "assert two_sum([3, 3], 6) == [0, 1]"
        ]
    },
    {
        "task_id": "TASK_ARR_02",
        "task_name": "max_subarray_sum",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def max_subarray_sum(nums: list) -> int:
    """
    Find the contiguous subarray with the largest sum and return its sum.
    Requirements:
    1. Handles arrays with all negative numbers.
    2. Minimum length of subarray is 1.
    """
''',
        "seeded_defect": '''def max_subarray_sum(nums: list) -> int:
    # Seeded defect: initializes max_sum to 0, breaking all-negative arrays
    max_sum = 0
    curr = 0
    for x in nums:
        curr = max(x, curr + x)
        max_sum = max(max_sum, curr)
    return max_sum
''',
        "defect_description": "Initializes max_sum to 0 causing 0 to be returned on all-negative inputs",
        "authoritative_tests": [
            "assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6",
            "assert max_subarray_sum([1]) == 1",
            "assert max_subarray_sum([5, 4, -1, 7, 8]) == 23",
            "assert max_subarray_sum([-1, -2, -3]) == -1"
        ]
    },
    {
        "task_id": "TASK_ARR_03",
        "task_name": "rotate_array",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def rotate_array(nums: list, k: int) -> list:
    """
    Rotate array to the right by k steps.
    Requirements:
    1. Return a new rotated list.
    2. Original list must not be modified.
    3. k can be larger than len(nums).
    4. Empty list returns [].
    """
''',
        "seeded_defect": '''def rotate_array(nums: list, k: int) -> list:
    # Seeded defect: mutates input list in-place and fails when k >= len(nums)
    if not nums: return []
    for _ in range(k):
        nums.insert(0, nums.pop())
    return nums
''',
        "defect_description": "Mutates input in-place and is slow/faulty for large k",
        "authoritative_tests": [
            "orig = [1, 2, 3, 4, 5, 6, 7]; res = rotate_array(orig, 3); assert res == [5, 6, 7, 1, 2, 3, 4] and orig == [1, 2, 3, 4, 5, 6, 7]",
            "assert rotate_array([-1, -100, 3, 99], 2) == [3, 99, -1, -100]",
            "assert rotate_array([1, 2], 3) == [2, 1]",
            "assert rotate_array([], 5) == []"
        ]
    },
    {
        "task_id": "TASK_ARR_04",
        "task_name": "remove_duplicates_sorted",
        "domain": "Arrays & Pointers",
        "difficulty": "EASY",
        "prompt": '''def remove_duplicates_sorted(nums: list) -> list:
    """
    Return unique elements from a sorted list, preserving relative order.
    Requirements:
    1. Return a new list of unique elements.
    2. Do not modify the input list.
    3. Empty list returns [].
    """
''',
        "seeded_defect": '''def remove_duplicates_sorted(nums: list) -> list:
    # Seeded defect: uses set() which scrambles order on some types / runs
    return list(set(nums))
''',
        "defect_description": "Uses set() conversion which does not guarantee order preservation",
        "authoritative_tests": [
            "orig = [1, 1, 2]; res = remove_duplicates_sorted(orig); assert res == [1, 2] and orig == [1, 1, 2]",
            "assert remove_duplicates_sorted([0, 0, 1, 1, 1, 2, 2, 3, 3, 4]) == [0, 1, 2, 3, 4]",
            "assert remove_duplicates_sorted([]) == []",
            "assert remove_duplicates_sorted([5]) == [5]"
        ]
    },
    {
        "task_id": "TASK_ARR_05",
        "task_name": "move_zeroes",
        "domain": "Arrays & Pointers",
        "difficulty": "EASY",
        "prompt": '''def move_zeroes(nums: list) -> list:
    """
    Move all zeroes in nums to the end while maintaining the relative order of non-zero elements.
    Requirements:
    1. Return a new list.
    2. Do not modify the input list.
    """
''',
        "seeded_defect": '''def move_zeroes(nums: list) -> list:
    # Seeded defect: mutates input nums in place using remove() and append()
    for x in nums:
        if x == 0:
            nums.remove(0)
            nums.append(0)
    return nums
''',
        "defect_description": "Mutates input in-place and skips zeroes due to iterating while modifying",
        "authoritative_tests": [
            "orig = [0, 1, 0, 3, 12]; res = move_zeroes(orig); assert res == [1, 3, 12, 0, 0] and orig == [0, 1, 0, 3, 12]",
            "assert move_zeroes([0]) == [0]",
            "assert move_zeroes([0, 0, 1]) == [1, 0, 0]",
            "assert move_zeroes([1, 2, 3]) == [1, 2, 3]"
        ]
    },
    {
        "task_id": "TASK_ARR_06",
        "task_name": "product_except_self",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def product_except_self(nums: list) -> list:
    """
    Return an array output such that output[i] is equal to product of all elements of nums except nums[i].
    Requirements:
    1. Solves in O(n) without using division.
    2. Handles zeroes in array properly.
    3. Do not modify input list.
    """
''',
        "seeded_defect": '''def product_except_self(nums: list) -> list:
    # Seeded defect: uses division which crashes with ZeroDivisionError
    import math
    total = math.prod(nums)
    return [total // x for x in nums]
''',
        "defect_description": "Uses division which raises ZeroDivisionError on zeroes",
        "authoritative_tests": [
            "assert product_except_self([1, 2, 3, 4]) == [24, 12, 8, 6]",
            "assert product_except_self([-1, 1, 0, -3, 3]) == [0, 0, 9, 0, 0]",
            "assert product_except_self([0, 0]) == [0, 0]"
        ]
    },
    {
        "task_id": "TASK_ARR_07",
        "task_name": "container_with_most_water",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def container_with_most_water(height: list) -> int:
    """
    Find two lines that together with the x-axis form a container containing the most water.
    Requirements:
    1. Returns max area.
    2. List length is at least 2.
    """
''',
        "seeded_defect": '''def container_with_most_water(height: list) -> int:
    # Seeded defect: only checks adjacent bars
    return max(min(height[i], height[i+1]) for i in range(len(height)-1))
''',
        "defect_description": "Only evaluates adjacent columns instead of maximum span",
        "authoritative_tests": [
            "assert container_with_most_water([1, 8, 6, 2, 5, 4, 8, 3, 7]) == 49",
            "assert container_with_most_water([1, 1]) == 1",
            "assert container_with_most_water([4, 3, 2, 1, 4]) == 16"
        ]
    },
    {
        "task_id": "TASK_ARR_08",
        "task_name": "trapping_rain_water",
        "domain": "Arrays & Pointers",
        "difficulty": "HARD",
        "prompt": '''def trapping_rain_water(height: list) -> int:
    """
    Compute how much water can be trapped after raining.
    Requirements:
    1. Non-negative integers representing elevation map where width of each bar is 1.
    2. Empty or <3 bars returns 0.
    """
''',
        "seeded_defect": '''def trapping_rain_water(height: list) -> int:
    # Seeded defect: takes min of first and last bar instead of prefix/suffix max
    if len(height) < 3: return 0
    boundary = min(height[0], height[-1])
    return sum(max(0, boundary - h) for h in height[1:-1])
''',
        "defect_description": "Uses global endpoints rather than local prefix/suffix maxes",
        "authoritative_tests": [
            "assert trapping_rain_water([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6",
            "assert trapping_rain_water([4, 2, 0, 3, 2, 5]) == 9",
            "assert trapping_rain_water([]) == 0",
            "assert trapping_rain_water([2, 0, 2]) == 2"
        ]
    },
    {
        "task_id": "TASK_ARR_09",
        "task_name": "longest_consecutive_sequence",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def longest_consecutive_sequence(nums: list) -> int:
    """
    Find the length of the longest consecutive elements sequence.
    Requirements:
    1. Must run in O(n) time.
    2. Numbers are not necessarily sorted.
    3. Empty list returns 0.
    """
''',
        "seeded_defect": '''def longest_consecutive_sequence(nums: list) -> int:
    # Seeded defect: fails on duplicates within consecutive runs
    if not nums: return 0
    nums = sorted(nums)
    best, curr = 1, 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i-1] + 1:
            curr += 1
            best = max(best, curr)
        else:
            curr = 1
    return best
''',
        "defect_description": "Resets streak to 1 when encountering duplicate values",
        "authoritative_tests": [
            "assert longest_consecutive_sequence([100, 4, 200, 1, 3, 2]) == 4",
            "assert longest_consecutive_sequence([0, 3, 7, 2, 5, 8, 4, 6, 0, 1]) == 9",
            "assert longest_consecutive_sequence([]) == 0",
            "assert longest_consecutive_sequence([1, 2, 0, 1]) == 3"
        ]
    },
    {
        "task_id": "TASK_ARR_10",
        "task_name": "find_peak_element",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def find_peak_element(nums: list) -> int:
    """
    Find a peak element (strictly greater than its neighbors) and return its index.
    Requirements:
    1. nums[-1] = nums[n] = -infinity.
    2. Return index of any peak.
    """
''',
        "seeded_defect": '''def find_peak_element(nums: list) -> int:
    # Seeded defect: crashes with IndexError on single element or edge element
    for i in range(len(nums)):
        if nums[i] > nums[i-1] and nums[i] > nums[i+1]:
            return i
    return 0
''',
        "defect_description": "IndexError on boundary elements nums[0] and nums[len-1]",
        "authoritative_tests": [
            "assert find_peak_element([1, 2, 3, 1]) == 2",
            "assert find_peak_element([1, 2, 1, 3, 5, 6, 4]) in [1, 5]",
            "assert find_peak_element([1]) == 0",
            "assert find_peak_element([2, 1]) == 0"
        ]
    },
    {
        "task_id": "TASK_ARR_11",
        "task_name": "min_size_subarray_sum",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def min_size_subarray_sum(target: int, nums: list) -> int:
    """
    Find minimal length of contiguous subarray whose sum is >= target.
    Requirements:
    1. If no such subarray, return 0.
    2. All elements are positive integers.
    """
''',
        "seeded_defect": '''def min_size_subarray_sum(target: int, nums: list) -> int:
    # Seeded defect: only checks if entire sum >= target
    if sum(nums) < target: return 0
    return 1
''',
        "defect_description": "Returns 1 unconditionally if array sum is sufficient",
        "authoritative_tests": [
            "assert min_size_subarray_sum(7, [2, 3, 1, 2, 4, 3]) == 2",
            "assert min_size_subarray_sum(4, [1, 4, 4]) == 1",
            "assert min_size_subarray_sum(11, [1, 1, 1, 1, 1, 1, 1, 1]) == 0"
        ]
    },
    {
        "task_id": "TASK_ARR_12",
        "task_name": "sliding_window_max",
        "domain": "Arrays & Pointers",
        "difficulty": "HARD",
        "prompt": '''def sliding_window_max(nums: list, k: int) -> list:
    """
    Return max sliding window of size k moving from left to right.
    Requirements:
    1. Returns list of maximums.
    2. If nums is empty or k <= 0, return [].
    """
''',
        "seeded_defect": '''def sliding_window_max(nums: list, k: int) -> list:
    # Seeded defect: off-by-one window end
    if not nums or k <= 0: return []
    return [max(nums[i:i+k-1]) for i in range(len(nums) - k + 1)]
''',
        "defect_description": "Window slice is k-1 elements wide instead of k",
        "authoritative_tests": [
            "assert sliding_window_max([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]",
            "assert sliding_window_max([1], 1) == [1]",
            "assert sliding_window_max([], 3) == []",
            "assert sliding_window_max([9, 11], 2) == [11]"
        ]
    },
    {
        "task_id": "TASK_ARR_13",
        "task_name": "majority_element",
        "domain": "Arrays & Pointers",
        "difficulty": "EASY",
        "prompt": '''def majority_element(nums: list) -> int:
    """
    Return the majority element that appears more than floor(n / 2) times.
    Requirements:
    1. Assume majority element always exists in array.
    """
''',
        "seeded_defect": '''def majority_element(nums: list) -> int:
    # Seeded defect: returns most frequent even if not majority or breaks on ties
    return nums[0]
''',
        "defect_description": "Returns first element without counting occurrences",
        "authoritative_tests": [
            "assert majority_element([3, 2, 3]) == 3",
            "assert majority_element([2, 2, 1, 1, 1, 2, 2]) == 2",
            "assert majority_element([1]) == 1"
        ]
    },
    {
        "task_id": "TASK_ARR_14",
        "task_name": "merge_sorted_arrays",
        "domain": "Arrays & Pointers",
        "difficulty": "EASY",
        "prompt": '''def merge_sorted_arrays(a: list, b: list) -> list:
    """
    Merge two sorted lists a and b into a single sorted list.
    Requirements:
    1. Returns a new sorted list.
    2. Does not modify a or b.
    3. Runs in O(len(a) + len(b)).
    """
''',
        "seeded_defect": '''def merge_sorted_arrays(a: list, b: list) -> list:
    # Seeded defect: mutates list a in place using extend and sort
    a.extend(b)
    a.sort()
    return a
''',
        "defect_description": "Mutates input list a in place using extend() and sort()",
        "authoritative_tests": [
            "l1, l2 = [1, 2, 4], [1, 3, 4]; res = merge_sorted_arrays(l1, l2); assert res == [1, 1, 2, 3, 4, 4] and l1 == [1, 2, 4] and l2 == [1, 3, 4]",
            "assert merge_sorted_arrays([], [0]) == [0]",
            "assert merge_sorted_arrays([1], []) == [1]"
        ]
    },
    {
        "task_id": "TASK_ARR_15",
        "task_name": "three_sum",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def three_sum(nums: list) -> list:
    """
    Find all unique triplets [nums[i], nums[j], nums[k]] such that i != j != k and nums[i] + nums[j] + nums[k] == 0.
    Requirements:
    1. Return list of sorted triplets.
    2. Must not contain duplicate triplets.
    """
''',
        "seeded_defect": '''def three_sum(nums: list) -> list:
    # Seeded defect: includes duplicate triplets and doesn't sort
    res = []
    n = len(nums)
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                if nums[i] + nums[j] + nums[k] == 0:
                    res.append([nums[i], nums[j], nums[k]])
    return res
''',
        "defect_description": "Generates duplicate triplet combinations",
        "authoritative_tests": [
            "res = three_sum([-1, 0, 1, 2, -1, -4]); sorted_res = sorted([sorted(x) for x in res]); assert sorted_res == [[-1, -1, 2], [-1, 0, 1]]",
            "assert three_sum([0, 1, 1]) == []",
            "assert three_sum([0, 0, 0]) == [[0, 0, 0]]"
        ]
    },
    {
        "task_id": "TASK_ARR_16",
        "task_name": "spiral_matrix_traverse",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def spiral_matrix_traverse(matrix: list) -> list:
    """
    Return all elements of m x n matrix in spiral order.
    Requirements:
    1. Top-left to top-right, down, bottom-right to bottom-left, up.
    2. Empty matrix returns [].
    """
''',
        "seeded_defect": '''def spiral_matrix_traverse(matrix: list) -> list:
    # Seeded defect: pop(0) on rows mutates input matrix
    res = []
    while matrix:
        res.extend(matrix.pop(0))
        matrix = list(zip(*matrix))[::-1]
    return res
''',
        "defect_description": "Mutates input matrix rows using pop(0)",
        "authoritative_tests": [
            "m = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]; res = spiral_matrix_traverse(m); assert res == [1, 2, 3, 6, 9, 8, 7, 4, 5]",
            "assert spiral_matrix_traverse([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]) == [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]",
            "assert spiral_matrix_traverse([]) == []"
        ]
    },
    {
        "task_id": "TASK_ARR_17",
        "task_name": "rotate_matrix_90",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def rotate_matrix_90(matrix: list) -> list:
    """
    Rotate n x n 2D matrix by 90 degrees clockwise.
    Requirements:
    1. Returns a newly created rotated matrix.
    2. Does not modify original matrix.
    """
''',
        "seeded_defect": '''def rotate_matrix_90(matrix: list) -> list:
    # Seeded defect: rotates counter-clockwise instead of clockwise
    return [list(row) for row in zip(*matrix)][::-1]
''',
        "defect_description": "Performs counter-clockwise 90 degree rotation instead of clockwise",
        "authoritative_tests": [
            "m = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]; res = rotate_matrix_90(m); assert res == [[7, 4, 1], [8, 5, 2], [9, 6, 3]] and m[0] == [1, 2, 3]",
            "assert rotate_matrix_90([[1, 2], [3, 4]]) == [[3, 1], [4, 2]]",
            "assert rotate_matrix_90([[1]]) == [[1]]"
        ]
    },
    {
        "task_id": "TASK_ARR_18",
        "task_name": "summary_ranges",
        "domain": "Arrays & Pointers",
        "difficulty": "EASY",
        "prompt": '''def summary_ranges(nums: list) -> list:
    """
    Return the smallest sorted list of ranges that cover all the numbers in the array.
    Requirements:
    1. e.g. [0, 1, 2, 4, 5, 7] -> ['0->2', '4->5', '7'].
    2. Single number range is just 'a'.
    3. Empty list returns [].
    """
''',
        "seeded_defect": '''def summary_ranges(nums: list) -> list:
    # Seeded defect: formats single numbers with arrow like '7->7'
    if not nums: return []
    res = []
    start = nums[0]
    for i in range(1, len(nums) + 1):
        if i == len(nums) or nums[i] != nums[i-1] + 1:
            res.append(f"{start}->{nums[i-1]}")
            if i < len(nums): start = nums[i]
    return res
''',
        "defect_description": "Formats isolated numbers as 'a->a' instead of 'a'",
        "authoritative_tests": [
            "assert summary_ranges([0, 1, 2, 4, 5, 7]) == ['0->2', '4->5', '7']",
            "assert summary_ranges([0, 2, 3, 4, 6, 8, 9]) == ['0', '2->4', '6', '8->9']",
            "assert summary_ranges([]) == []",
            "assert summary_ranges([-1]) == ['-1']"
        ]
    },
    {
        "task_id": "TASK_ARR_19",
        "task_name": "subarray_sum_equals_k",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def subarray_sum_equals_k(nums: list, k: int) -> int:
    """
    Return total number of continuous subarrays whose sum equals k.
    Requirements:
    1. Numbers can be negative, zero, or positive.
    """
''',
        "seeded_defect": '''def subarray_sum_equals_k(nums: list, k: int) -> int:
    # Seeded defect: sliding window that assumes all positive numbers (breaks on negatives)
    count = 0
    for i in range(len(nums)):
        s = 0
        for j in range(i, len(nums)):
            s += nums[j]
            if s == k: count += 1
            elif s > k: break
    return count
''',
        "defect_description": "Premature break when sum > k fails on arrays with negative numbers",
        "authoritative_tests": [
            "assert subarray_sum_equals_k([1, 1, 1], 2) == 2",
            "assert subarray_sum_equals_k([1, 2, 3], 3) == 2",
            "assert subarray_sum_equals_k([1, -1, 0], 0) == 3",
            "assert subarray_sum_equals_k([-1, -1, 1], 0) == 1"
        ]
    },
    {
        "task_id": "TASK_ARR_20",
        "task_name": "jump_game_can_reach",
        "domain": "Arrays & Pointers",
        "difficulty": "MEDIUM",
        "prompt": '''def jump_game_can_reach(nums: list) -> bool:
    """
    Given array nums where each element represents max jump length, determine if you can reach last index.
    Requirements:
    1. Start at index 0.
    2. Return True if you can reach index len(nums) - 1, else False.
    """
''',
        "seeded_defect": '''def jump_game_can_reach(nums: list) -> bool:
    # Seeded defect: greedy step doesn't check if current position is reachable
    max_reach = 0
    for i, x in enumerate(nums):
        max_reach = max(max_reach, i + x)
    return max_reach >= len(nums) - 1
''',
        "defect_description": "Fails to check if current index is reachable before extending reach",
        "authoritative_tests": [
            "assert jump_game_can_reach([2, 3, 1, 1, 4]) is True",
            "assert jump_game_can_reach([3, 2, 1, 0, 4]) is False",
            "assert jump_game_can_reach([0]) is True",
            "assert jump_game_can_reach([2, 0, 0]) is True"
        ]
    }
]
