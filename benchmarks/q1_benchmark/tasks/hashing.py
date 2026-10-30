"""
benchmarks/q1_benchmark/tasks/hashing.py
=========================================
20 Hashing, Frequencies & Sets benchmark tasks for Q1 Journal Evaluation.
"""

HASHING_TASKS = [
    {
        "task_id": "TASK_HSH_01",
        "task_name": "group_anagrams",
        "domain": "Hashing & Frequencies",
        "difficulty": "MEDIUM",
        "prompt": '''def group_anagrams(words: list) -> list:
    """
    Group words that are anagrams of each other.
    Requirements:
    1. Return list of groups (each group is a list of words).
    2. Words with same character frequencies belong in same group.
    3. Order within groups and order of groups must match original first-seen appearance.
    4. Input list must not be modified.
    """
''',
        "seeded_defect": '''def group_anagrams(words: list) -> list:
    # Seeded defect: sorts all words alphabetically, losing group separation
    return [sorted(words)]
''',
        "defect_description": "Places all words in a single group sorted alphabetically",
        "authoritative_tests": [
            "res = group_anagrams(['eat', 'tea', 'tan', 'ate', 'nat', 'bat']); assert len(res) == 3 and ['eat', 'tea', 'ate'] in res",
            "assert group_anagrams(['']) == [['']]",
            "assert group_anagrams(['a']) == [['a']]",
            "assert group_anagrams([]) == []"
        ]
    },
    {
        "task_id": "TASK_HSH_02",
        "task_name": "first_unique_character",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def first_unique_character(s: str) -> int:
    """
    Find first non-repeating character in string and return its index.
    Requirements:
    1. If it does not exist, return -1.
    2. Case-sensitive.
    """
''',
        "seeded_defect": '''def first_unique_character(s: str) -> int:
    # Seeded defect: returns index of character appearing only once in suffix
    for i, c in enumerate(s):
        if s[i+1:].count(c) == 0:
            return i
    return -1
''',
        "defect_description": "Only checks suffix count, flagging characters that appeared earlier in prefix",
        "authoritative_tests": [
            "assert first_unique_character('leetcode') == 0",
            "assert first_unique_character('loveleetcode') == 2",
            "assert first_unique_character('aabb') == -1",
            "assert first_unique_character('') == -1"
        ]
    },
    {
        "task_id": "TASK_HSH_03",
        "task_name": "word_frequency_counter",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def word_frequency_counter(text: str) -> dict:
    """
    Count frequency of words in text, ignoring case and punctuation.
    Requirements:
    1. Words are sequences of alphanumeric characters.
    2. Keys in returned dict should be lowercase.
    3. Empty string returns {}.
    """
''',
        "seeded_defect": '''def word_frequency_counter(text: str) -> dict:
    # Seeded defect: naive split on space that keeps punctuation attached
    words = text.lower().split()
    counts = {}
    for w in words: counts[w] = counts.get(w, 0) + 1
    return counts
''',
        "defect_description": "Includes attached punctuation marks as part of dictionary keys",
        "authoritative_tests": [
            "assert word_frequency_counter('Hello world, hello!') == {'hello': 2, 'world': 1}",
            "assert word_frequency_counter('Test... 1, 2, test?') == {'test': 2, '1': 1, '2': 1}",
            "assert word_frequency_counter('') == {}"
        ]
    },
    {
        "task_id": "TASK_HSH_04",
        "task_name": "is_isomorphic_strings",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def is_isomorphic_strings(s: str, t: str) -> bool:
    """
    Determine if two strings s and t are isomorphic.
    Requirements:
    1. Characters in s can be replaced to get t.
    2. All occurrences of a character must be replaced with same character while preserving order.
    3. No two characters may map to the same character (bijection).
    """
''',
        "seeded_defect": '''def is_isomorphic_strings(s: str, t: str) -> bool:
    # Seeded defect: only checks one-way mapping (not bijective)
    mapping = {}
    for c1, c2 in zip(s, t):
        if c1 in mapping and mapping[c1] != c2: return False
        mapping[c1] = c2
    return True
''',
        "defect_description": "Fails to enforce injectivity, allowing two source characters to map to same target",
        "authoritative_tests": [
            "assert is_isomorphic_strings('egg', 'add') is True",
            "assert is_isomorphic_strings('foo', 'bar') is False",
            "assert is_isomorphic_strings('paper', 'title') is True",
            "assert is_isomorphic_strings('badc', 'baba') is False"
        ]
    },
    {
        "task_id": "TASK_HSH_05",
        "task_name": "word_pattern_match",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def word_pattern_match(pattern: str, s: str) -> bool:
    """
    Determine if string s follows the same pattern of words.
    Requirements:
    1. Full match: each letter in pattern maps to exactly one word in s, and vice versa.
    2. Bijection between characters and words.
    """
''',
        "seeded_defect": '''def word_pattern_match(pattern: str, s: str) -> bool:
    # Seeded defect: does not check if len(words) == len(pattern)
    words = s.split()
    mapping = {}
    for p, w in zip(pattern, words):
        if p in mapping and mapping[p] != w: return False
        mapping[p] = w
    return True
''',
        "defect_description": "Ignores length mismatch between pattern and word tokens",
        "authoritative_tests": [
            "assert word_pattern_match('abba', 'dog cat cat dog') is True",
            "assert word_pattern_match('abba', 'dog cat cat fish') is False",
            "assert word_pattern_match('aaaa', 'dog cat cat dog') is False",
            "assert word_pattern_match('aaa', 'dog dog dog dog') is False"
        ]
    },
    {
        "task_id": "TASK_HSH_06",
        "task_name": "contains_duplicate_within_k",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def contains_duplicate_within_k(nums: list, k: int) -> bool:
    """
    Return True if nums contains duplicates such that abs(i - j) <= k.
    Requirements:
    1. Returns boolean.
    2. k >= 0.
    """
''',
        "seeded_defect": '''def contains_duplicate_within_k(nums: list, k: int) -> bool:
    # Seeded defect: checks if any duplicate exists in entire array
    return len(nums) != len(set(nums))
''',
        "defect_description": "Checks for global duplicates without enforcing distance window <= k",
        "authoritative_tests": [
            "assert contains_duplicate_within_k([1, 2, 3, 1], 3) is True",
            "assert contains_duplicate_within_k([1, 0, 1, 1], 1) is True",
            "assert contains_duplicate_within_k([1, 2, 3, 1, 2, 3], 2) is False"
        ]
    },
    {
        "task_id": "TASK_HSH_07",
        "task_name": "lru_cache_operations",
        "domain": "Hashing & Frequencies",
        "difficulty": "MEDIUM",
        "prompt": '''def lru_cache_operations(capacity: int, operations: list) -> list:
    """
    Simulate an LRU cache given capacity and list of operations:
    ('put', key, value) or ('get', key).
    Requirements:
    1. 'get' returns value or -1 if not found.
    2. 'put' evicts least recently used if capacity exceeded.
    3. Return list of results for 'get' operations.
    """
''',
        "seeded_defect": '''def lru_cache_operations(capacity: int, operations: list) -> list:
    # Seeded defect: FIFO eviction instead of LRU (doesn't refresh on 'get')
    cache = {}
    res = []
    for op in operations:
        if op[0] == 'put':
            if len(cache) >= capacity and op[1] not in cache:
                first = next(iter(cache))
                del cache[first]
            cache[op[1]] = op[2]
        elif op[0] == 'get':
            res.append(cache.get(op[1], -1))
    return res
''',
        "defect_description": "Evicts keys in FIFO order without refreshing usage upon 'get'",
        "authoritative_tests": [
            "ops = [('put', 1, 1), ('put', 2, 2), ('get', 1), ('put', 3, 3), ('get', 2)]; assert lru_cache_operations(2, ops) == [1, -1]",
            "ops2 = [('get', 1)]; assert lru_cache_operations(1, ops2) == [-1]"
        ]
    },
    {
        "task_id": "TASK_HSH_08",
        "task_name": "ransom_note_can_construct",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def ransom_note_can_construct(ransom_note: str, magazine: str) -> bool:
    """
    Return True if ransom_note can be constructed using letters from magazine.
    Requirements:
    1. Each letter in magazine can only be used once in ransom_note.
    2. Case-sensitive.
    """
''',
        "seeded_defect": '''def ransom_note_can_construct(ransom_note: str, magazine: str) -> bool:
    # Seeded defect: checks set membership without checking frequencies
    return set(ransom_note).issubset(set(magazine))
''',
        "defect_description": "Uses set subset which ignores character frequency counts",
        "authoritative_tests": [
            "assert ransom_note_can_construct('a', 'b') is False",
            "assert ransom_note_can_construct('aa', 'ab') is False",
            "assert ransom_note_can_construct('aa', 'aab') is True",
            "assert ransom_note_can_construct('', 'anything') is True"
        ]
    },
    {
        "task_id": "TASK_HSH_09",
        "task_name": "intersection_of_two_arrays",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def intersection_of_two_arrays(nums1: list, nums2: list) -> list:
    """
    Given two integer arrays nums1 and nums2, return an array of their intersection.
    Requirements:
    1. Each element in result must be unique.
    2. Result can be in any order.
    3. Input arrays must not be modified.
    """
''',
        "seeded_defect": '''def intersection_of_two_arrays(nums1: list, nums2: list) -> list:
    # Seeded defect: mutates nums1 in place
    nums1.clear()
    return []
''',
        "defect_description": "Mutates input list nums1 using clear()",
        "authoritative_tests": [
            "n1, n2 = [1, 2, 2, 1], [2, 2]; res = intersection_of_two_arrays(n1, n2); assert set(res) == {2} and len(n1) == 4",
            "assert set(intersection_of_two_arrays([4, 9, 5], [9, 4, 9, 8, 4])) == {4, 9}",
            "assert intersection_of_two_arrays([], [1, 2]) == []"
        ]
    },
    {
        "task_id": "TASK_HSH_10",
        "task_name": "intersection_of_two_arrays_ii",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def intersection_of_two_arrays_ii(nums1: list, nums2: list) -> list:
    """
    Given two integer arrays, return their intersection including duplicates.
    Requirements:
    1. Each element must appear as many times as it shows in both arrays.
    2. Input arrays must not be modified.
    """
''',
        "seeded_defect": '''def intersection_of_two_arrays_ii(nums1: list, nums2: list) -> list:
    # Seeded defect: returns unique elements only
    return list(set(nums1) & set(nums2))
''',
        "defect_description": "Discards duplicate element occurrences by casting to set()",
        "authoritative_tests": [
            "res = sorted(intersection_of_two_arrays_ii([1, 2, 2, 1], [2, 2])); assert res == [2, 2]",
            "res2 = sorted(intersection_of_two_arrays_ii([4, 9, 5], [9, 4, 9, 8, 4])); assert res2 == [4, 9]"
        ]
    },
    {
        "task_id": "TASK_HSH_11",
        "task_name": "happy_number",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def happy_number(n: int) -> bool:
    """
    Determine if number n is happy.
    Requirements:
    1. Starting with n, replace the number by sum of squares of its digits.
    2. Repeat until number equals 1 (happy), or loops endlessly in a cycle.
    """
''',
        "seeded_defect": '''def happy_number(n: int) -> bool:
    # Seeded defect: infinite loop because cycle set is missing
    while n != 1:
        n = sum(int(d)**2 for d in str(n))
    return True
''',
        "defect_description": "Fails to record visited states, causing infinite loops on unhappy numbers",
        "authoritative_tests": [
            "assert happy_number(19) is True",
            "assert happy_number(2) is False",
            "assert happy_number(7) is True"
        ]
    },
    {
        "task_id": "TASK_HSH_12",
        "task_name": "four_sum_count",
        "domain": "Hashing & Frequencies",
        "difficulty": "MEDIUM",
        "prompt": '''def four_sum_count(nums1: list, nums2: list, nums3: list, nums4: list) -> int:
    """
    Given four integer arrays of length n, return number of tuples (i, j, k, l) such that:
    nums1[i] + nums2[j] + nums3[k] + nums4[l] == 0.
    Requirements:
    1. Runs in O(n^2) using hash map.
    """
''',
        "seeded_defect": '''def four_sum_count(nums1: list, nums2: list, nums3: list, nums4: list) -> int:
    # Seeded defect: checks only if sum of array elements is 0
    return 1 if (sum(nums1) + sum(nums2) + sum(nums3) + sum(nums4)) == 0 else 0
''',
        "defect_description": "Checks aggregate sum of arrays instead of enumerating combinations",
        "authoritative_tests": [
            "assert four_sum_count([1, 2], [-2, -1], [-1, 2], [0, 2]) == 2",
            "assert four_sum_count([0], [0], [0], [0]) == 1"
        ]
    },
    {
        "task_id": "TASK_HSH_13",
        "task_name": "longest_substring_without_repeating",
        "domain": "Hashing & Frequencies",
        "difficulty": "MEDIUM",
        "prompt": '''def longest_substring_without_repeating(s: str) -> int:
    """
    Find length of longest substring without repeating characters.
    Requirements:
    1. Returns integer length.
    2. Empty string returns 0.
    """
''',
        "seeded_defect": '''def longest_substring_without_repeating(s: str) -> int:
    # Seeded defect: returns number of unique characters in entire string
    return len(set(s))
''',
        "defect_description": "Computes global set length rather than longest contiguous substring length",
        "authoritative_tests": [
            "assert longest_substring_without_repeating('abcabcbb') == 3",
            "assert longest_substring_without_repeating('bbbbb') == 1",
            "assert longest_substring_without_repeating('pwwkew') == 3",
            "assert longest_substring_without_repeating('') == 0"
        ]
    },
    {
        "task_id": "TASK_HSH_14",
        "task_name": "min_window_substring",
        "domain": "Hashing & Frequencies",
        "difficulty": "HARD",
        "prompt": '''def min_window_substring(s: str, t: str) -> str:
    """
    Find minimum window substring in s which contains all characters of t (including duplicates).
    Requirements:
    1. If no such window, return empty string "".
    """
''',
        "seeded_defect": '''def min_window_substring(s: str, t: str) -> str:
    # Seeded defect: returns s if all characters in t are present, else ""
    return s if set(t).issubset(set(s)) else ""
''',
        "defect_description": "Returns entire string instead of locating the minimal enclosing window",
        "authoritative_tests": [
            "assert min_window_substring('ADOBECODEBANC', 'ABC') == 'BANC'",
            "assert min_window_substring('a', 'a') == 'a'",
            "assert min_window_substring('a', 'aa') == ''"
        ]
    },
    {
        "task_id": "TASK_HSH_15",
        "task_name": "find_disappeared_numbers",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def find_disappeared_numbers(nums: list) -> list:
    """
    Given array nums of n integers where nums[i] is in range [1, n],
    return an array of all integers in [1, n] that do not appear in nums.
    Requirements:
    1. Result sorted in ascending order.
    2. Do not modify input list.
    """
''',
        "seeded_defect": '''def find_disappeared_numbers(nums: list) -> list:
    # Seeded defect: mutates nums and checks range [0, n-1] instead of [1, n]
    nums.sort()
    return [i for i in range(len(nums)) if i not in nums]
''',
        "defect_description": "Off-by-one 0-indexed range checking and in-place list sorting",
        "authoritative_tests": [
            "orig = [4, 3, 2, 7, 8, 2, 3, 1]; res = find_disappeared_numbers(orig); assert res == [5, 6] and orig == [4, 3, 2, 7, 8, 2, 3, 1]",
            "assert find_disappeared_numbers([1, 1]) == [2]"
        ]
    },
    {
        "task_id": "TASK_HSH_16",
        "task_name": "subdomain_visit_counts",
        "domain": "Hashing & Frequencies",
        "difficulty": "MEDIUM",
        "prompt": '''def subdomain_visit_counts(cpdomains: list) -> list:
    """
    Given count-paired domains, return visit counts for each subdomain.
    Requirements:
    1. e.g. '9001 discuss.leetcode.com' contributes to 'discuss.leetcode.com', 'leetcode.com', 'com'.
    2. Format of output strings: 'count subdomain'.
    """
''',
        "seeded_defect": '''def subdomain_visit_counts(cpdomains: list) -> list:
    # Seeded defect: only counts top-level domain
    counts = {}
    for entry in cpdomains:
        cnt, dom = entry.split()
        tld = dom.split('.')[-1]
        counts[tld] = counts.get(tld, 0) + int(cnt)
    return [f"{cnt} {dom}" for dom, cnt in counts.items()]
''',
        "defect_description": "Only records counts for the top-level domain segment",
        "authoritative_tests": [
            "res = subdomain_visit_counts(['9001 discuss.leetcode.com']); assert '9001 com' in res and '9001 leetcode.com' in res and '9001 discuss.leetcode.com' in res",
            "assert subdomain_visit_counts([]) == []"
        ]
    },
    {
        "task_id": "TASK_HSH_17",
        "task_name": "find_duplicate_files_by_content",
        "domain": "Hashing & Frequencies",
        "difficulty": "MEDIUM",
        "prompt": '''def find_duplicate_files_by_content(paths: list) -> list:
    """
    Find all duplicate files based on content.
    Requirements:
    1. Input: 'root/d1/d2 f1.txt(abc) f2.txt(efg)'
    2. Return list of groups where each group contains >= 2 paths of files with identical content.
    """
''',
        "seeded_defect": '''def find_duplicate_files_by_content(paths: list) -> list:
    # Seeded defect: groups by filename instead of content
    return []
''',
        "defect_description": "Stub return returning empty list",
        "authoritative_tests": [
            "p = ['root/a 1.txt(abcd) 2.txt(efgh)', 'root/c 3.txt(abcd)', 'root/c/d 4.txt(efgh)']; res = find_duplicate_files_by_content(p); assert len(res) == 2",
            "assert find_duplicate_files_by_content([]) == []"
        ]
    },
    {
        "task_id": "TASK_HSH_18",
        "task_name": "jewels_and_stones",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def jewels_and_stones(jewels: str, stones: str) -> int:
    """
    Count how many stones are also jewels.
    Requirements:
    1. Letters in jewels are distinct.
    2. Case-sensitive ('a' is different from 'A').
    """
''',
        "seeded_defect": '''def jewels_and_stones(jewels: str, stones: str) -> int:
    # Seeded defect: case-insensitive match
    j_set = set(jewels.lower())
    return sum(1 for s in stones if s.lower() in j_set)
''',
        "defect_description": "Fails to respect case sensitivity between jewels and stones",
        "authoritative_tests": [
            "assert jewels_and_stones('aA', 'aAAbbbb') == 3",
            "assert jewels_and_stones('z', 'ZZ') == 0",
            "assert jewels_and_stones('', 'abc') == 0"
        ]
    },
    {
        "task_id": "TASK_HSH_19",
        "task_name": "brick_wall_least_cuts",
        "domain": "Hashing & Frequencies",
        "difficulty": "MEDIUM",
        "prompt": '''def brick_wall_least_cuts(wall: list) -> int:
    """
    Find minimum number of crossed bricks by drawing vertical line from top to bottom.
    Requirements:
    1. Line cannot be drawn at edges of wall.
    2. wall is 2D list of positive brick widths.
    """
''',
        "seeded_defect": '''def brick_wall_least_cuts(wall: list) -> int:
    # Seeded defect: draws line at index 0 (which is edge of wall)
    return len(wall)
''',
        "defect_description": "Trivially returns wall height without finding maximal edge alignments",
        "authoritative_tests": [
            "w = [[1, 2, 2, 1], [3, 1, 2], [1, 3, 2], [2, 4], [3, 1, 2], [1, 3, 1, 1]]; assert brick_wall_least_cuts(w) == 2",
            "assert brick_wall_least_cuts([[1], [1], [1]]) == 3"
        ]
    },
    {
        "task_id": "TASK_HSH_20",
        "task_name": "unique_email_addresses",
        "domain": "Hashing & Frequencies",
        "difficulty": "EASY",
        "prompt": '''def unique_email_addresses(emails: list) -> int:
    """
    Return number of different addresses that receive mail.
    Requirements:
    1. In local name, '.' are ignored.
    2. In local name, everything after '+' is ignored.
    3. Domain name is left unchanged.
    """
''',
        "seeded_defect": '''def unique_email_addresses(emails: list) -> int:
    # Seeded defect: strips '.' from domain name too
    cleaned = [e.replace('.', '') for e in emails]
    return len(set(cleaned))
''',
        "defect_description": "Applies dot-stripping rule to domain portion of email address",
        "authoritative_tests": [
            "assert unique_email_addresses(['test.email+alex@leetcode.com', 'test.e.mail+bob.cathy@leetcode.com', 'testemail+david@lee.tcode.com']) == 2",
            "assert unique_email_addresses(['a@leetcode.com', 'b@leetcode.com', 'c@leetcode.com']) == 3"
        ]
    }
]
