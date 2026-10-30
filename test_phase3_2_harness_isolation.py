"""
test_phase3_2_harness_isolation.py
===================================
Regression test suite for Phase 3.2:
Removal of test-harness pollution (_AdaptiveResult monkey-patching)
from user code execution.

Verifies:
1. Recursive string reversal executes and returns standard strings.
2. Recursive numeric function (e.g. factorial / fibonacci) executes cleanly.
3. Function that calls itself multiple times executes normally.
4. Function whose return value participates in arithmetic (+, *, -).
5. Function whose return value participates in string concatenation (+).
6. Function returning a list.
7. Function returning a dictionary.
8. Normal equality assertions.
9. Exact reproduction case of TASK_2 candidate passes without TypeError.
"""

import unittest
from app.tester import run_tests, FailureType


class TestPhase32HarnessIsolation(unittest.TestCase):

    def test_01_recursive_string_reversal_exact_reproduction(self):
        """Exact TASK_2 candidate: recursive reverse_string must succeed without _AdaptiveResult TypeError."""
        code = """def reverse_string(s):
    if len(s) <= 1:
        return s
    mid = len(s) // 2
    return reverse_string(s[mid:]) + reverse_string(s[:mid])
"""
        tests = [
            "assert reverse_string('hello') == 'olleh'",
            "assert reverse_string('') == ''",
            "assert reverse_string('a') == 'a'",
            "assert reverse_string('racecar') == 'racecar'"
        ]
        res = run_tests("def reverse_string(s): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")
        self.assertEqual(res["test_summary"]["passed"], 4)
        self.assertEqual(res["test_summary"]["failed"], 0)

    def test_02_recursive_numeric_function(self):
        """Recursive numeric function (factorial) must execute with native int arithmetic."""
        code = """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        tests = [
            "assert factorial(0) == 1",
            "assert factorial(1) == 1",
            "assert factorial(5) == 120",
            "assert factorial(6) == 720"
        ]
        res = run_tests("def factorial(n): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")
        self.assertEqual(res["test_summary"]["passed"], 4)

    def test_03_function_calling_itself_multiple_times(self):
        """Binary recursive tree traversal (fibonacci) must execute without wrapper overhead."""
        code = """def fib(n):
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)
"""
        tests = [
            "assert fib(0) == 0",
            "assert fib(1) == 1",
            "assert fib(6) == 8",
            "assert fib(7) == 13"
        ]
        res = run_tests("def fib(n): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")
        self.assertEqual(res["test_summary"]["passed"], 4)

    def test_04_return_value_in_arithmetic(self):
        """Return value participating in external arithmetic expressions."""
        code = """def get_value(x):
    return x * 2
"""
        tests = [
            "res = get_value(5) + 10; assert res == 20",
            "assert get_value(3) * 2 == 12",
            "assert 50 - get_value(10) == 30"
        ]
        res = run_tests("def get_value(x): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")
        self.assertEqual(res["test_summary"]["passed"], 3)

    def test_05_return_value_in_string_concatenation(self):
        """Return value participating in string concatenation and formatting."""
        code = """def greet(name):
    return 'Hello, ' + name
"""
        tests = [
            "assert greet('Alice') + '!' == 'Hello, Alice!'",
            "assert 'Prefix: ' + greet('Bob') == 'Prefix: Hello, Bob'",
            "assert greet('') == 'Hello, '"
        ]
        res = run_tests("def greet(name): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")
        self.assertEqual(res["test_summary"]["passed"], 3)

    def test_06_function_returning_list(self):
        """Function returning lists behaves normally with list methods and operators."""
        code = """def generate_evens(n):
    return [i for i in range(n) if i % 2 == 0]
"""
        tests = [
            "assert generate_evens(10) == [0, 2, 4, 6, 8]",
            "assert generate_evens(1) == [0]",
            "assert generate_evens(0) == []",
            "assert len(generate_evens(6)) == 3"
        ]
        res = run_tests("def generate_evens(n): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")
        self.assertEqual(res["test_summary"]["passed"], 4)

    def test_07_function_returning_dict(self):
        """Function returning dictionaries behaves normally with dict methods and equality."""
        code = """def create_profile(name, score):
    return {'name': name, 'score': score, 'passed': score >= 50}
"""
        tests = [
            "assert create_profile('Alice', 85) == {'name': 'Alice', 'score': 85, 'passed': True}",
            "assert create_profile('Bob', 40)['passed'] is False",
            "assert 'score' in create_profile('Eve', 90)"
        ]
        res = run_tests("def create_profile(name, score): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")
        self.assertEqual(res["test_summary"]["passed"], 3)

    def test_08_normal_equality_assertions(self):
        """Normal strict equality assertions pass cleanly without type distortion."""
        code = """def compute(a, b):
    return a + b
"""
        tests = [
            "assert compute(10, 20) == 30",
            "assert compute(-5, 5) == 0",
            "assert compute(0.5, 0.5) == 1.0"
        ]
        res = run_tests("def compute(a, b): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")
        self.assertEqual(res["test_summary"]["passed"], 3)

    def test_09_actual_return_values_not_monkey_patched(self):
        """Candidate function in globals() retains its actual function type and identity."""
        code = """def target_fn(x):
    return x * 10
"""
        tests = [
            "import types",
            "assert isinstance(target_fn, types.FunctionType)",
            "assert not hasattr(target_fn, '_is_adaptive')",
            "assert target_fn(5) == 50"
        ]
        res = run_tests("def target_fn(x): pass", code, authoritative_tests=tests)
        self.assertTrue(res["success"], f"Failed with: {res.get('message')}")


if __name__ == "__main__":
    unittest.main()
