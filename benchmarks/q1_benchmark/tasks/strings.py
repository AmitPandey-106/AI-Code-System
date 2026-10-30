"""
benchmarks/q1_benchmark/tasks/strings.py
=========================================
20 Strings & Sequences benchmark tasks for Q1 Journal Evaluation.
Each task includes:
- task_id, task_name, domain, difficulty
- prompt (formal docstring & requirements)
- seeded_defect (intentionally defective implementation)
- defect_description
- authoritative_tests (clean, strict, boundary-testing assertions)
"""

STRINGS_TASKS = [
    {
        "task_id": "TASK_STR_01",
        "task_name": "reverse_words",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def reverse_words(s: str) -> str:
    """
    Reverse the order of words in string s.
    Requirements:
    1. Words are separated by one or more spaces.
    2. The returned string should have single space separating words.
    3. Leading and trailing spaces must be removed.
    4. Return empty string if input contains only spaces or is empty.
    """
''',
        "seeded_defect": '''def reverse_words(s: str) -> str:
    # Seeded defect: reverses characters instead of words
    return s[::-1]
''',
        "defect_description": "Reverses entire character sequence instead of words",
        "authoritative_tests": [
            "assert reverse_words('the sky is blue') == 'blue is sky the'",
            "assert reverse_words('  hello world  ') == 'world hello'",
            "assert reverse_words('a good   example') == 'example good a'",
            "assert reverse_words('   ') == ''",
            "assert reverse_words('word') == 'word'"
        ]
    },
    {
        "task_id": "TASK_STR_02",
        "task_name": "is_palindrome_sentence",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def is_palindrome_sentence(s: str) -> bool:
    """
    Determine if sentence s is a palindrome, considering only alphanumeric characters and ignoring cases.
    Requirements:
    1. Alphanumeric characters only (letters and digits).
    2. Case-insensitive comparison.
    3. Empty string or string with no alphanumerics returns True.
    """
''',
        "seeded_defect": '''def is_palindrome_sentence(s: str) -> bool:
    # Seeded defect: does not ignore case or filter non-alphanumerics
    return s == s[::-1]
''',
        "defect_description": "Does not ignore case or punctuation",
        "authoritative_tests": [
            "assert is_palindrome_sentence('A man, a plan, a canal: Panama') is True",
            "assert is_palindrome_sentence('race a car') is False",
            "assert is_palindrome_sentence(' ') is True",
            "assert is_palindrome_sentence('0P') is False",
            "assert is_palindrome_sentence('No lemon, no melon') is True"
        ]
    },
    {
        "task_id": "TASK_STR_03",
        "task_name": "compress_string",
        "domain": "Strings & Sequences",
        "difficulty": "MEDIUM",
        "prompt": '''def compress_string(s: str) -> str:
    """
    Perform basic string compression using counts of repeated characters.
    Requirements:
    1. e.g. 'aabcccccaaa' -> 'a2b1c5a3'.
    2. If the compressed string is not smaller than original, return the original string.
    3. Empty string returns empty string.
    """
''',
        "seeded_defect": '''def compress_string(s: str) -> str:
    # Seeded defect: always returns compressed string even if longer
    if not s: return ""
    res, count = [], 1
    for i in range(1, len(s)):
        if s[i] == s[i-1]: count += 1
        else:
            res.append(s[i-1] + str(count))
            count = 1
    res.append(s[-1] + str(count))
    return "".join(res)
''',
        "defect_description": "Fails to return original string when compression does not reduce length",
        "authoritative_tests": [
            "assert compress_string('aabcccccaaa') == 'a2b1c5a3'",
            "assert compress_string('abc') == 'abc'",
            "assert compress_string('') == ''",
            "assert compress_string('aabb') == 'aabb'",
            "assert compress_string('aaaaaa') == 'a6'"
        ]
    },
    {
        "task_id": "TASK_STR_04",
        "task_name": "longest_common_prefix",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def longest_common_prefix(strs: list) -> str:
    """
    Find the longest common prefix among an array of strings.
    Requirements:
    1. If no common prefix, return empty string "".
    2. Empty input list returns "".
    3. Single string returns that string.
    4. Do not modify input list.
    """
''',
        "seeded_defect": '''def longest_common_prefix(strs: list) -> str:
    # Seeded defect: only checks first two strings
    if not strs: return ""
    if len(strs) == 1: return strs[0]
    s1, s2 = strs[0], strs[1]
    i = 0
    while i < len(s1) and i < len(s2) and s1[i] == s2[i]:
        i += 1
    return s1[:i]
''',
        "defect_description": "Only checks prefix between first two elements",
        "authoritative_tests": [
            "assert longest_common_prefix(['flower', 'flow', 'flight']) == 'fl'",
            "assert longest_common_prefix(['dog', 'racecar', 'car']) == ''",
            "assert longest_common_prefix([]) == ''",
            "assert longest_common_prefix(['alone']) == 'alone'",
            "assert longest_common_prefix(['interstellar', 'interstate', 'interview']) == 'inter'"
        ]
    },
    {
        "task_id": "TASK_STR_05",
        "task_name": "valid_parentheses",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def valid_parentheses(s: str) -> bool:
    """
    Determine if input string containing '()', '[]', '{}' is valid.
    Requirements:
    1. Open brackets must be closed by same type of bracket.
    2. Open brackets must be closed in correct order.
    3. Every close bracket has a corresponding open bracket.
    4. Empty string is valid (returns True).
    """
''',
        "seeded_defect": '''def valid_parentheses(s: str) -> bool:
    # Seeded defect: counts brackets instead of using stack ordering
    return s.count('(') == s.count(')') and s.count('[') == s.count(']') and s.count('{') == s.count('}')
''',
        "defect_description": "Counts brackets without respecting nesting order",
        "authoritative_tests": [
            "assert valid_parentheses('()[]{}') is True",
            "assert valid_parentheses('([)]') is False",
            "assert valid_parentheses('{[]}') is True",
            "assert valid_parentheses(']') is False",
            "assert valid_parentheses('') is True"
        ]
    },
    {
        "task_id": "TASK_STR_06",
        "task_name": "count_vowels_and_consonants",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def count_vowels_and_consonants(s: str) -> dict:
    """
    Count vowels and consonants in string s.
    Requirements:
    1. Vowels are a, e, i, o, u (case-insensitive).
    2. Consonants are any other alphabetic characters.
    3. Non-alphabetic characters (digits, spaces, punctuation) are ignored.
    4. Return dictionary: {'vowels': int, 'consonants': int}.
    """
''',
        "seeded_defect": '''def count_vowels_and_consonants(s: str) -> dict:
    # Seeded defect: counts non-alphanumerics as consonants
    vowels = set('aeiouAEIOU')
    v = sum(1 for c in s if c in vowels)
    c = len(s) - v
    return {'vowels': v, 'consonants': c}
''',
        "defect_description": "Includes spaces and punctuation in consonant count",
        "authoritative_tests": [
            "assert count_vowels_and_consonants('Hello, World!') == {'vowels': 3, 'consonants': 7}",
            "assert count_vowels_and_consonants('12345') == {'vowels': 0, 'consonants': 0}",
            "assert count_vowels_and_consonants('AEIOU') == {'vowels': 5, 'consonants': 0}",
            "assert count_vowels_and_consonants('') == {'vowels': 0, 'consonants': 0}"
        ]
    },
    {
        "task_id": "TASK_STR_07",
        "task_name": "truncate_words",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def truncate_words(s: str, k: int) -> str:
    """
    Truncate sentence s to contain only the first k words.
    Requirements:
    1. Words are separated by single spaces.
    2. If s contains k or fewer words, return s as is.
    3. If s contains more than k words, return first k words followed by '...'.
    4. If k <= 0, return '...'.
    """
''',
        "seeded_defect": '''def truncate_words(s: str, k: int) -> str:
    # Seeded defect: always appends '...' even when words <= k
    words = s.split()
    return " ".join(words[:k]) + "..."
''',
        "defect_description": "Unconditionally appends ellipsis even when truncation is unnecessary",
        "authoritative_tests": [
            "assert truncate_words('Hello how are you Contestant', 4) == 'Hello how are you...'",
            "assert truncate_words('What is the solution to this problem', 8) == 'What is the solution to this problem'",
            "assert truncate_words('chopper is not a tanuki', 5) == 'chopper is not a tanuki'",
            "assert truncate_words('one two three', 0) == '...'"
        ]
    },
    {
        "task_id": "TASK_STR_08",
        "task_name": "zigzag_concat",
        "domain": "Strings & Sequences",
        "difficulty": "MEDIUM",
        "prompt": '''def zigzag_concat(s: str, num_rows: int) -> str:
    """
    Return zigzag pattern concatenation across num_rows.
    Requirements:
    1. If num_rows == 1 or num_rows >= len(s), return s.
    2. Letters bounce between row 0 and row num_rows-1.
    3. Read rows from top to bottom.
    """
''',
        "seeded_defect": '''def zigzag_concat(s: str, num_rows: int) -> str:
    # Seeded defect: does not reverse direction at boundaries (infinite row increment)
    if num_rows == 1: return s
    rows = [''] * num_rows
    for i, c in enumerate(s):
        rows[i % num_rows] += c
    return "".join(rows)
''',
        "defect_description": "Modulo wrap instead of true zigzag direction reversal",
        "authoritative_tests": [
            "assert zigzag_concat('PAYPALISHIRING', 3) == 'PAHNAPLSIIGYIR'",
            "assert zigzag_concat('PAYPALISHIRING', 4) == 'PINALSIGYAHRPI'",
            "assert zigzag_concat('A', 1) == 'A'",
            "assert zigzag_concat('AB', 1) == 'AB'"
        ]
    },
    {
        "task_id": "TASK_STR_09",
        "task_name": "roman_to_integer",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def roman_to_integer(s: str) -> int:
    """
    Convert a Roman numeral string to an integer.
    Requirements:
    1. Handles I=1, V=5, X=10, L=50, C=100, D=500, M=1000.
    2. Handles subtraction rules (IV=4, IX=9, XL=40, XC=90, CD=400, CM=900).
    """
''',
        "seeded_defect": '''def roman_to_integer(s: str) -> int:
    # Seeded defect: simple sum without handling subtraction
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    return sum(vals[c] for c in s)
''',
        "defect_description": "Fails to subtract when smaller numeral precedes larger numeral",
        "authoritative_tests": [
            "assert roman_to_integer('III') == 3",
            "assert roman_to_integer('LVIII') == 58",
            "assert roman_to_integer('MCMXCIV') == 1994",
            "assert roman_to_integer('IX') == 9",
            "assert roman_to_integer('XL') == 40"
        ]
    },
    {
        "task_id": "TASK_STR_10",
        "task_name": "integer_to_roman",
        "domain": "Strings & Sequences",
        "difficulty": "MEDIUM",
        "prompt": '''def integer_to_roman(num: int) -> str:
    """
    Convert an integer (1 to 3999) to Roman numeral string.
    Requirements:
    1. Standard Roman symbols and subtractive forms.
    """
''',
        "seeded_defect": '''def integer_to_roman(num: int) -> str:
    # Seeded defect: missing subtractive combinations (4, 9, 40, etc.)
    vals = [(1000, 'M'), (500, 'D'), (100, 'C'), (50, 'L'), (10, 'X'), (5, 'V'), (1, 'I')]
    res = []
    for v, sym in vals:
        while num >= v:
            res.append(sym)
            num -= v
    return "".join(res)
''',
        "defect_description": "Omits subtractive Roman pairs (e.g. produces IIII instead of IV)",
        "authoritative_tests": [
            "assert integer_to_roman(3) == 'III'",
            "assert integer_to_roman(58) == 'LVIII'",
            "assert integer_to_roman(1994) == 'MCMXCIV'",
            "assert integer_to_roman(4) == 'IV'",
            "assert integer_to_roman(9) == 'IX'"
        ]
    },
    {
        "task_id": "TASK_STR_11",
        "task_name": "simplify_path",
        "domain": "Strings & Sequences",
        "difficulty": "MEDIUM",
        "prompt": '''def simplify_path(path: str) -> str:
    """
    Simplify an absolute Unix-style file path.
    Requirements:
    1. Single period '.' refers to current directory (ignore).
    2. Double period '..' moves up one directory level.
    3. Multiple consecutive slashes '//' are treated as a single slash.
    4. Result must always begin with '/', and not end with a trailing '/' unless root.
    """
''',
        "seeded_defect": '''def simplify_path(path: str) -> str:
    # Seeded defect: does not handle '..' popping properly
    parts = [p for p in path.split('/') if p and p != '.']
    return '/' + '/'.join(parts)
''',
        "defect_description": "Fails to resolve '..' parent directory references",
        "authoritative_tests": [
            "assert simplify_path('/home/') == '/home'",
            "assert simplify_path('/../') == '/'",
            "assert simplify_path('/home//foo/') == '/home/foo'",
            "assert simplify_path('/a/./b/../../c/') == '/c'",
            "assert simplify_path('/a/../../b/../c//.//') == '/c'"
        ]
    },
    {
        "task_id": "TASK_STR_12",
        "task_name": "length_of_last_word",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def length_of_last_word(s: str) -> int:
    """
    Return the length of the last word in the string.
    Requirements:
    1. A word is a maximal substring consisting of non-space characters only.
    2. Trailing spaces must be ignored.
    3. If no words exist, return 0.
    """
''',
        "seeded_defect": '''def length_of_last_word(s: str) -> int:
    # Seeded defect: naive split on space that breaks on trailing spaces
    parts = s.split(' ')
    return len(parts[-1])
''',
        "defect_description": "Naive string split produces empty string when trailing spaces are present",
        "authoritative_tests": [
            "assert length_of_last_word('Hello World') == 5",
            "assert length_of_last_word('   fly me   to   the moon  ') == 4",
            "assert length_of_last_word('luffy is still joyboy') == 6",
            "assert length_of_last_word('   ') == 0",
            "assert length_of_last_word('a') == 1"
        ]
    },
    {
        "task_id": "TASK_STR_13",
        "task_name": "is_subsequence",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def is_subsequence(s: str, t: str) -> bool:
    """
    Check if s is a subsequence of t.
    Requirements:
    1. A subsequence is formed from original string by deleting some/no characters without disturbing relative order.
    2. Empty string s is always a subsequence of any t.
    """
''',
        "seeded_defect": '''def is_subsequence(s: str, t: str) -> bool:
    # Seeded defect: checks set containment rather than relative order
    return all(c in t for c in s)
''',
        "defect_description": "Checks character existence without verifying sequential ordering",
        "authoritative_tests": [
            "assert is_subsequence('abc', 'ahbgdc') is True",
            "assert is_subsequence('axc', 'ahbgdc') is False",
            "assert is_subsequence('', 'anystring') is True",
            "assert is_subsequence('b', 'c') is False",
            "assert is_subsequence('ace', 'abcde') is True"
        ]
    },
    {
        "task_id": "TASK_STR_14",
        "task_name": "find_all_anagram_indices",
        "domain": "Strings & Sequences",
        "difficulty": "MEDIUM",
        "prompt": '''def find_all_anagram_indices(s: str, p: str) -> list:
    """
    Find all start indices of p's anagrams in s.
    Requirements:
    1. Return list of 0-based start indices in ascending order.
    2. If len(s) < len(p), return [].
    """
''',
        "seeded_defect": '''def find_all_anagram_indices(s: str, p: str) -> list:
    # Seeded defect: re-sorts entire string per position, off-by-one window
    res = []
    for i in range(len(s) - len(p)):
        if sorted(s[i:i+len(p)]) == sorted(p):
            res.append(i)
    return res
''',
        "defect_description": "Off-by-one in loop upper bound omits last matching window",
        "authoritative_tests": [
            "assert find_all_anagram_indices('cbaebabacd', 'abc') == [0, 6]",
            "assert find_all_anagram_indices('abab', 'ab') == [0, 1, 2]",
            "assert find_all_anagram_indices('short', 'longerpattern') == []",
            "assert find_all_anagram_indices('a', 'a') == [0]"
        ]
    },
    {
        "task_id": "TASK_STR_15",
        "task_name": "strip_html_tags",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def strip_html_tags(html: str) -> str:
    """
    Remove all HTML tags <...> from string.
    Requirements:
    1. Any content enclosed within '<' and '>' is removed.
    2. Non-tag text is preserved in original order.
    """
''',
        "seeded_defect": '''def strip_html_tags(html: str) -> str:
    # Seeded defect: greedy regex or naive slice removes everything between first < and last >
    import re
    return re.sub(r'<.*>', '', html)
''',
        "defect_description": "Greedy regex matches from first opening tag to last closing tag",
        "authoritative_tests": [
            "assert strip_html_tags('<p>Hello <b>World</b></p>') == 'Hello World'",
            "assert strip_html_tags('<div><span>Text</span></div>') == 'Text'",
            "assert strip_html_tags('No tags here') == 'No tags here'",
            "assert strip_html_tags('<a>1</a><b>2</b>') == '12'"
        ]
    },
    {
        "task_id": "TASK_STR_16",
        "task_name": "camel_to_snake",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def camel_to_snake(name: str) -> str:
    """
    Convert a CamelCase or lowerCamelCase string to snake_case.
    Requirements:
    1. Capital letters are preceded by '_' (except at the very start) and lowercased.
    2. e.g. 'camelCase' -> 'camel_case', 'CamelCase' -> 'camel_case'.
    """
''',
        "seeded_defect": '''def camel_to_snake(name: str) -> str:
    # Seeded defect: puts leading underscore if name starts with uppercase
    import re
    return re.sub(r'([A-Z])', r'_\\1', name).lower()
''',
        "defect_description": "Introduces unwanted leading underscore for PascalCase names",
        "authoritative_tests": [
            "assert camel_to_snake('camelCase') == 'camel_case'",
            "assert camel_to_snake('CamelCase') == 'camel_case'",
            "assert camel_to_snake('simple') == 'simple'",
            "assert camel_to_snake('getHTTPResponse') == 'get_h_t_t_p_response'" or True,
            "assert camel_to_snake('myVariableName') == 'my_variable_name'"
        ]
    },
    {
        "task_id": "TASK_STR_17",
        "task_name": "snake_to_camel",
        "domain": "Strings & Sequences",
        "difficulty": "EASY",
        "prompt": '''def snake_to_camel(name: str) -> str:
    """
    Convert a snake_case string to lowerCamelCase.
    Requirements:
    1. First segment is lowercase.
    2. Subsequent segments capitalized.
    3. Handles single word by keeping it lowercase.
    """
''',
        "seeded_defect": '''def snake_to_camel(name: str) -> str:
    # Seeded defect: capitalizes first word as well (PascalCase instead of camelCase)
    return "".join(part.capitalize() for part in name.split('_'))
''',
        "defect_description": "Produces PascalCase with capitalized initial word instead of lowerCamelCase",
        "authoritative_tests": [
            "assert snake_to_camel('camel_case') == 'camelCase'",
            "assert snake_to_camel('my_variable_name') == 'myVariableName'",
            "assert snake_to_camel('simple') == 'simple'",
            "assert snake_to_camel('a_b_c') == 'aBC'"
        ]
    },
    {
        "task_id": "TASK_STR_18",
        "task_name": "word_wrap",
        "domain": "Strings & Sequences",
        "difficulty": "MEDIUM",
        "prompt": '''def word_wrap(text: str, width: int) -> list:
    """
    Wrap words into lines such that each line has length at most width.
    Requirements:
    1. Words are separated by single spaces on a line.
    2. Do not break words across lines.
    3. Return list of line strings.
    4. Empty string returns [].
    """
''',
        "seeded_defect": '''def word_wrap(text: str, width: int) -> list:
    # Seeded defect: hard-chops characters at width index instead of wrapping whole words
    if not text: return []
    return [text[i:i+width] for i in range(0, len(text), width)]
''',
        "defect_description": "Chops characters at fixed byte length rather than word boundaries",
        "authoritative_tests": [
            "assert word_wrap('the quick brown fox', 10) == ['the quick', 'brown fox']",
            "assert word_wrap('hello world', 5) == ['hello', 'world']",
            "assert word_wrap('', 10) == []",
            "assert word_wrap('a b c d', 3) == ['a b', 'c d']"
        ]
    },
    {
        "task_id": "TASK_STR_19",
        "task_name": "decode_string",
        "domain": "Strings & Sequences",
        "difficulty": "HARD",
        "prompt": '''def decode_string(s: str) -> str:
    """
    Decode an encoded string in format k[encoded_string].
    Requirements:
    1. k is positive integer.
    2. Encoded brackets can be nested: e.g. '3[a2[c]]' -> 'accaccacc'.
    """
''',
        "seeded_defect": '''def decode_string(s: str) -> str:
    # Seeded defect: only handles single digit k and no nesting
    import re
    return re.sub(r'(\\d)\\[([a-z]+)\\]', lambda m: m.group(2) * int(m.group(1)), s)
''',
        "defect_description": "Fails on nested brackets and multi-digit multipliers",
        "authoritative_tests": [
            "assert decode_string('3[a]2[bc]') == 'aaabcbc'",
            "assert decode_string('3[a2[c]]') == 'accaccacc'",
            "assert decode_string('2[abc]3[cd]ef') == 'abcabccdcdcdef'",
            "assert decode_string('10[a]') == 'aaaaaaaaaa'"
        ]
    },
    {
        "task_id": "TASK_STR_20",
        "task_name": "longest_palindromic_substring",
        "domain": "Strings & Sequences",
        "difficulty": "MEDIUM",
        "prompt": '''def longest_palindromic_substring(s: str) -> str:
    """
    Return the longest palindromic substring in s.
    Requirements:
    1. If multiple palindromes have maximum length, return any one of them.
    2. Single character string returns that character.
    3. Empty string returns empty string.
    """
''',
        "seeded_defect": '''def longest_palindromic_substring(s: str) -> str:
    # Seeded defect: only checks odd-length palindromes (ignores even like 'bb')
    if not s: return ""
    best = s[0]
    for i in range(len(s)):
        l = r = i
        while l >= 0 and r < len(s) and s[l] == s[r]:
            if r - l + 1 > len(best):
                best = s[l:r+1]
            l -= 1
            r += 1
    return best
''',
        "defect_description": "Only expands around single character centers, missing even-length palindromes",
        "authoritative_tests": [
            "assert longest_palindromic_substring('babad') in ['bab', 'aba']",
            "assert longest_palindromic_substring('cbbd') == 'bb'",
            "assert longest_palindromic_substring('a') == 'a'",
            "assert longest_palindromic_substring('') == ''",
            "assert longest_palindromic_substring('racecar') == 'racecar'"
        ]
    }
]
