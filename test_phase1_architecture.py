"""
Phase 1 Architecture Verification Tests
Verifies the 6 key architectural fixes in LITE-Coder:
1. Test 1: Original Task Preservation (find_top_students preserved, entry point not dropped)
2. Test 2: No Test Contamination (no fabricated sort_list(...) assertions)
3. Test 3: No Execution Harness Contamination (no calculate_average('hello') type errors)
4. Test 4: Contract Rejection (rejecting code that only defines helpers)
5. Test 5: Cumulative Repair (attempt 2 receives attempt 1 history and error context)
6. Test 6: Regression Protection (rejecting candidate that drops contract and rolling back to best candidate)
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

from app.contract import (
    TaskContract,
    extract_contract,
    format_contract_instruction,
    validate_code_against_contract,
)
from app.executor import ensure_execution, execute_code
from app.tester import run_tests
from app.main import Request, generate, infer_initial_tests
from app.config import config


class TestPhase1Architecture(unittest.TestCase):

    def setUp(self):
        self.task_prompt = """Implement a Python function called `find_top_students(students, n)`.

Requirements:
1. Calculate each student's average from their marks.
2. Ignore students whose `marks` list is empty.
3. Sort students by average descending.
4. If two students have the same average, sort alphabetically by name.
5. Return the top `n` students.
6. Return dictionaries containing `name` and `average`.
7. Round averages to exactly 2 decimal places.
8. If `n > number of valid students`, return all valid students.
"""

    def test_01_original_task_preservation(self):
        """Test 1: Contract extracts and preserves find_top_students(students, n)."""
        print("\n--- Running Test 1: Original Task Preservation ---")
        contract = extract_contract(self.task_prompt)
        
        self.assertEqual(contract.entry_point, "find_top_students", "Entry point should be 'find_top_students'")
        self.assertEqual(contract.expected_params, ["students", "n"], "Expected params should be ['students', 'n']")
        
        # Verify instructions enforce the contract
        instruction = format_contract_instruction(contract)
        self.assertIn("find_top_students(students, n)", instruction)
        self.assertIn("CRITICAL REQUIREMENT", instruction)
        
        # Verify valid code containing find_top_students is accepted
        valid_code = """
def calculate_average(marks):
    if not marks:
        return 0.0
    return round(sum(marks) / len(marks), 2)

def find_top_students(students, n):
    valid = []
    for s in students:
        if s.get('marks'):
            valid.append({'name': s['name'], 'average': calculate_average(s['marks'])})
    valid.sort(key=lambda x: (-x['average'], x['name']))
    return valid[:n]
"""
        valid, msg = validate_code_against_contract(valid_code, contract)
        self.assertTrue(valid, f"Valid code should pass contract validation: {msg}")
        print("[PASS] Test 1: Contract extracted and preserved find_top_students(students, n).")

    def test_02_no_test_contamination(self):
        """Test 2: Prompts containing words like 'sort' must NEVER generate or execute sort_list."""
        print("\n--- Running Test 2: No Test Contamination ---")
        contract = extract_contract(self.task_prompt)
        
        # 1. Check infer_initial_tests
        inferred = infer_initial_tests(self.task_prompt, contract=contract)
        print(f"Inferred tests: {inferred}")
        for test in inferred:
            self.assertNotIn("sort_list", test, "Inferred test contaminated with 'sort_list'!")
            self.assertIn("find_top_students", test, "Inferred test must target 'find_top_students'")
            
        # 2. Check tester sanitization if contaminated tests are somehow introduced
        dirty_tests = [
            "assert sort_list([3, 1, 2]) == [1, 2, 3]",
            "assert find_top_students([], 1) == []"
        ]
        code = """
def find_top_students(students, n):
    return []
"""
        test_result = run_tests(prompt=self.task_prompt, code=code, authoritative_tests=dirty_tests, contract=contract)
        # Even with dirty_tests, sort_list must have been filtered out
        self.assertTrue(test_result["success"], f"Test execution should pass because sort_list was sanitized: {test_result.get('message')}")
        self.assertNotIn("sort_list", test_result.get("tests", ""))
        print("[PASS] Test 2: sort_list contamination eliminated from test inference and runner.")

    def test_03_no_execution_harness_contamination(self):
        """Test 3: calculate_average(marks) must NEVER receive 'hello' as input."""
        print("\n--- Running Test 3: No Execution Harness Contamination ---")
        code = """
def calculate_average(marks):
    if not marks:
        return 0.0
    return sum(marks) / len(marks)
"""
        harness = ensure_execution(code)
        print(f"Generated Harness:\n{harness}")
        
        # Verify 'hello' is not injected
        self.assertNotIn("'hello'", harness, "String 'hello' was injected into calculate_average(marks)!")
        self.assertNotIn('"hello"', harness, 'String "hello" was injected into calculate_average(marks)!')
        
        # Verify harness executes without TypeError
        exec_res = execute_code(code)
        self.assertTrue(exec_res["success"], f"Execution harness failed: {exec_res.get('error')}")
        print("[PASS] Test 3: calculate_average received appropriate numerical/list inputs, no 'hello' TypeError.")

    def test_04_contract_rejection(self):
        """Test 4: Solution with ONLY calculate_average must be rejected with contract violation."""
        print("\n--- Running Test 4: Contract Rejection ---")
        contract = extract_contract(self.task_prompt)
        
        partial_code = """
def calculate_average(marks):
    if not marks:
        return 0.0
    return round(sum(marks) / len(marks), 2)
"""
        valid, msg = validate_code_against_contract(partial_code, contract)
        self.assertFalse(valid, "Code without find_top_students MUST be rejected")
        self.assertIn("find_top_students", msg)
        self.assertTrue("is missing" in msg.lower() or "missing" in msg.lower())
        print(f"Rejection message: {msg}")
        print("[PASS] Test 4: Code lacking find_top_students is strictly rejected with ContractViolation.")

    def test_05_cumulative_repair(self):
        """Test 5: Multi-turn repair passes Attempt 1 history, code, and error into Attempt 2."""
        print("\n--- Running Test 5: Cumulative Repair History ---")
        import app.model
        
        contract = extract_contract(self.task_prompt)
        attempt_history = [
            {
                "attempt": 1,
                "code": "def find_top_students(students, n):\n    return students",
                "error": "AssertionError: Expected 2 students, got 3",
                "diagnosis": "Failed sorting logic",
            }
        ]
        
        captured_prompt = None
        def mock_generate_raw(prompt, *args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return "def find_top_students(students, n):\n    return []"

        with patch("app.model.generate_raw", side_effect=mock_generate_raw):
            code, debug_prompt = app.model.fix_code(
                "def find_top_students(students, n):\n    return students",
                "AssertionError: Expected 2 students, got 3",
                task_contract=contract,
                attempt_history=attempt_history
            )
            
            self.assertIsNotNone(captured_prompt, "fix_code did not call generate_raw")
            # Verify attempt history was injected
            self.assertIn("Attempt 1", captured_prompt)
            self.assertIn("AssertionError: Expected 2 students, got 3", captured_prompt)
            self.assertIn("find_top_students(students, n)", captured_prompt)
            self.assertIn("PREVIOUS REPAIR ATTEMPTS", captured_prompt)
            print("Captured cumulative prompt includes prior attempt code, error, and contract.")
            print("[PASS] Test 5: Attempt 2 receives Attempt 1 history and error context cumulatively.")

    def test_06_regression_protection_and_rollback(self):
        """Test 6: If Attempt 2 drops find_top_students, it is rejected and Attempt 1 is preserved."""
        print("\n--- Running Test 6: Regression Protection and Rollback ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        contract = extract_contract(self.task_prompt)
        
        # Attempt 1: Has find_top_students (passes contract), passes 1 of 2 tests
        attempt1_code = """
def find_top_students(students, n):
    return students[:n]
"""
        # Attempt 2: Drops find_top_students (only has calculate_average)
        attempt2_code = """
def calculate_average(marks):
    return sum(marks) / len(marks)
"""
        # Attempt 3: Another invalid attempt
        attempt3_code = """
def broken_syntax(
"""

        codes = [attempt1_code, attempt2_code, attempt3_code, attempt3_code, attempt3_code]
        call_idx = 0

        def mock_generate_code(*args, **kwargs):
            return codes[0], "mock generation prompt"

        def mock_fix_code(*args, **kwargs):
            nonlocal call_idx
            call_idx += 1
            idx = min(call_idx, len(codes) - 1)
            return codes[idx], f"mock fix prompt {call_idx}"

        def mock_run_tests(code, *args, **kwargs):
            # Attempt 1 passes 1/2 tests
            if "find_top_students" in code and "students[:n]" in code:
                return {
                    "success": False,
                    "message": "AssertionError: averages not calculated",
                    "tests": "assert find_top_students([], 1) == []",
                    "test_summary": {"passed": 1, "failed": 1, "total": 2}
                }
            return {
                "success": False,
                "message": "AssertionError",
                "tests": "",
                "test_summary": {"passed": 0, "failed": 2, "total": 2}
            }

        with patch("app.main.generate_code", side_effect=mock_generate_code):
            with patch("app.main.fix_code", side_effect=mock_fix_code):
                with patch("app.main.run_tests", side_effect=mock_run_tests):
                    req = Request(prompt=self.task_prompt)
                    result = generate(req)
                    
                    final_code = result["code"]
                    print(f"Final restored code:\n{final_code}")
                    
                    # Verify final code is Attempt 1 (rollback candidate), NOT Attempt 2 (which dropped entry point)
                    self.assertIn("find_top_students", final_code, "Final code should preserve find_top_students via rollback!")
                    self.assertNotIn("calculate_average(marks):", final_code, "Attempt 2 should not have overwritten Attempt 1!")
                    
                    # Verify attempts recorded contract failure on Attempt 2
                    attempts = result["feedback_record"]["attempts"]
                    # Attempt 2 was rejected due to contract violation
                    attempt_2_record = attempts[1]
                    self.assertIn("ContractViolation", attempt_2_record["error_message"])
                    print("[PASS] Test 6: Regression detected on Attempt 2, rolled back to best candidate.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
