"""
Phase 2 Architecture Verification Tests
Covers the 16 required tests for Phase 2:
1. Bare prompt extraction
2. Full function wording extraction
3. Plan requirement preservation
4. Correct alphabetical oracle (Bob before Charlie accepted)
5. Contradictory oracle rejection (Charlie before Bob rejected)
6. Valid multi-line test preservation
7. Undefined input_data rejection
8. Undefined expected_output rejection
9. Test-harness NameError must NOT enter fix_code()
10. "No valid tests generated" must NOT enter fix_code()
11. Valid AssertionError from failing authoritative test MUST enter fix_code()
12. Candidate code must remain unchanged after TEST_HARNESS_FAILURE
13. Candidate code must remain unchanged after TEST_ORACLE_FAILURE
14. Repair history must contain code failures but not harness failures
15. Maximum repair attempts must still be enforced
16. Repair loop must terminate cleanly on repeated oracle failure
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

from app.contract import (
    TaskContract,
    extract_contract,
    format_contract_instruction,
    validate_code_against_contract,
    validate_plan_against_contract
)
from app.tester import (
    FailureType,
    clean_test_code,
    validate_test_variables,
    validate_oracle_consistency,
    run_tests
)
from app.main import Request, generate
from app.config import config


class TestPhase2Architecture(unittest.TestCase):

    def setUp(self):
        self.reproduction_prompt = """Implement find_top_students(students, n):
- calculate averages for each student's marks
- ignore empty marks
- sort by average descending
- alphabetical tie-break when averages are equal
- return top n
- output dictionaries containing {name, average}
- round averages to 2 decimals
- if n > valid students, return all valid students
- if n <= 0, return []
- do not mutate the input
- skip invalid student records
- skip nonnumeric marks"""

    def test_01_bare_prompt_extraction(self):
        """Test 1: Bare prompt extraction: Implement find_top_students(students, n):"""
        print("\n--- Running Test 1: Bare Prompt Extraction ---")
        contract = extract_contract(self.reproduction_prompt)
        self.assertEqual(contract.entry_point, "find_top_students")
        self.assertEqual(contract.parameters, ["students", "n"])
        self.assertGreaterEqual(len(contract.requirements), 10)
        print("[PASS] Test 1: Bare prompt extraction extracted entry_point and parameters successfully.")

    def test_02_full_function_wording_extraction(self):
        """Test 2: Full function wording variations must all extract entry_point and params."""
        print("\n--- Running Test 2: Full Function Wording Extraction ---")
        variations = [
            ("Write a Python function find_top_students(students, n)", "find_top_students", ["students", "n"]),
            ("Implement a function called find_top_students(students, n)", "find_top_students", ["students", "n"]),
            ("Create a function named find_top_students(students, n)", "find_top_students", ["students", "n"]),
            ("def find_top_students(students, n):", "find_top_students", ["students", "n"]),
            ("Implement a Python function called `find_top_students(students, n)`.", "find_top_students", ["students", "n"]),
        ]
        for p, expected_ep, expected_params in variations:
            c = extract_contract(p)
            self.assertEqual(c.entry_point, expected_ep, f"Failed on prompt: {p}")
            self.assertEqual(c.parameters, expected_params, f"Failed params on prompt: {p}")
        print("[PASS] Test 2: All 5 prompt syntax variations extracted entry_point and parameters.")

    def test_03_plan_requirement_preservation(self):
        """Test 3: Plan requirement preservation validation."""
        print("\n--- Running Test 3: Plan Requirement Preservation ---")
        contract = extract_contract(self.reproduction_prompt)
        lossy_plan = """1. Calculate average helper
2. Filter empty marks
3. Sort students
4. Return top n"""
        is_valid, missing = validate_plan_against_contract(lossy_plan, contract)
        self.assertFalse(is_valid)
        self.assertTrue(any("tie-break" in m for m in missing))
        self.assertTrue(any("n <= 0" in m for m in missing))

        comprehensive_plan = """1. Validate inputs and return [] if n <= 0.
2. Filter out invalid student records and nonnumeric marks.
3. Calculate average for students with non-empty marks, rounding to 2 decimal places.
4. Sort valid students primarily by average descending, with alphabetical tie-break for equal averages.
5. If n > valid students, return all valid students, else return top n as dicts with name and average without mutating input."""
        is_comp_valid, comp_missing = validate_plan_against_contract(comprehensive_plan, contract)
        self.assertTrue(is_comp_valid)
        print("[PASS] Test 3: Plan requirement validator accurately detected missing vs preserved constraints.")

    def test_04_correct_alphabetical_oracle(self):
        """Test 4: Correct alphabetical oracle: Bob before Charlie for equal averages is accepted."""
        print("\n--- Running Test 4: Correct Alphabetical Oracle Accepted ---")
        contract = extract_contract(self.reproduction_prompt)
        valid_oracle_test = """
assert find_top_students(
    [{"name": "Alice", "marks": [85, 90]},
     {"name": "Bob", "marks": [95, 92]},
     {"name": "Charlie", "marks": [95, 92]}],
    3
) == [
    {"name": "Bob", "average": 93.5},
    {"name": "Charlie", "average": 93.5},
    {"name": "Alice", "average": 87.5}
]
"""
        valid, err = validate_oracle_consistency(valid_oracle_test, contract)
        self.assertTrue(valid, f"Valid alphabetical oracle was incorrectly rejected: {err}")
        print("[PASS] Test 4: Consistent alphabetical oracle (Bob < Charlie) successfully validated.")

    def test_05_contradictory_oracle_rejection(self):
        """Test 5: Contradictory oracle (Charlie before Bob for equal averages) must be rejected."""
        print("\n--- Running Test 5: Contradictory Oracle Rejection ---")
        contract = extract_contract(self.reproduction_prompt)
        contradictory_oracle_test = """
assert find_top_students(
    [{"name": "Alice", "marks": [85, 90]},
     {"name": "Bob", "marks": [95, 92]},
     {"name": "Charlie", "marks": [95, 92]}],
    3
) == [
    {"name": "Charlie", "average": 93.5},
    {"name": "Bob", "average": 93.5},
    {"name": "Alice", "average": 87.5}
]
"""
        valid, err = validate_oracle_consistency(contradictory_oracle_test, contract)
        self.assertFalse(valid, "Contradictory oracle (Charlie before Bob) MUST be rejected!")
        self.assertIn("Alphabetical tie-break violated", err)
        print(f"Detected Oracle Contradiction: {err}")
        print("[PASS] Test 5: Contradictory oracle (Charlie before Bob) rejected with TEST_ORACLE_FAILURE.")

    def test_06_valid_multi_line_test_preservation(self):
        """Test 6: Valid multi-line test setup statements must be preserved."""
        print("\n--- Running Test 6: Valid Multi-Line Test Preservation ---")
        raw_test = """
input_data = [
    {"name": "Bob", "marks": [90, 90]},
    {"name": "Alice", "marks": [90, 90]}
]
expected_output = [
    {"name": "Alice", "average": 90.0},
    {"name": "Bob", "average": 90.0}
]
assert find_top_students(input_data, 2) == expected_output
"""
        cleaned = clean_test_code(raw_test)
        self.assertIn("input_data = [", cleaned)
        self.assertIn("expected_output = [", cleaned)
        self.assertIn("assert find_top_students(input_data, 2) == expected_output", cleaned)
        print("[PASS] Test 6: Multi-line setup variables and assert statements preserved without stripping.")

    def test_07_undefined_input_data_rejection(self):
        """Test 7: Undefined input_data must be rejected before execution."""
        print("\n--- Running Test 7: Undefined input_data Rejection ---")
        undefined_test = "assert find_top_students(input_data, 3) == [{'name': 'Alice', 'average': 90.0}]"
        valid, err = validate_test_variables(undefined_test, allowed_names=["find_top_students"])
        self.assertFalse(valid, "Undefined input_data should be rejected")
        self.assertIn("input_data", err)
        print(f"Rejected undefined test: {err}")
        print("[PASS] Test 7: Undefined 'input_data' rejected before execution.")

    def test_08_undefined_expected_output_rejection(self):
        """Test 8: Undefined expected_output must be rejected before execution."""
        print("\n--- Running Test 8: Undefined expected_output Rejection ---")
        undefined_test = "assert find_top_students([], 1) == expected_output"
        valid, err = validate_test_variables(undefined_test, allowed_names=["find_top_students"])
        self.assertFalse(valid, "Undefined expected_output should be rejected")
        self.assertIn("expected_output", err)
        print(f"Rejected undefined test: {err}")
        print("[PASS] Test 8: Undefined 'expected_output' rejected before execution.")

    def test_09_test_harness_name_error_must_not_enter_fix_code(self):
        """Test 9: Test-harness NameError must NOT enter fix_code()."""
        print("\n--- Running Test 9: Harness NameError Isolation ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        contract = extract_contract(self.reproduction_prompt)
        initial_code = """
def find_top_students(students, n):
    return []
"""
        # Pass contaminated test with undefined input_data
        dirty_tests = ["assert find_top_students(input_data, 3) == expected_output"]

        fix_code_called = False
        def mock_fix_code(*args, **kwargs):
            nonlocal fix_code_called
            fix_code_called = True
            return "def should_not_run(): pass", "prompt"

        with patch("app.main.generate_code", return_value=(initial_code, "gen_prompt")):
            with patch("app.main.fix_code", side_effect=mock_fix_code):
                req = Request(prompt=self.reproduction_prompt, authoritative_tests=dirty_tests)
                result = generate(req)

                self.assertFalse(fix_code_called, "fix_code() MUST NOT be called on TEST_HARNESS_FAILURE!")
                print("[PASS] Test 9: Test-harness NameError isolated; fix_code() was not invoked.")

    def test_10_no_valid_tests_generated_must_not_enter_fix_code(self):
        """Test 10: 'No valid tests generated' must NOT enter fix_code()."""
        print("\n--- Running Test 10: 'No Valid Tests Generated' Isolation ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        contract = extract_contract(self.reproduction_prompt)
        initial_code = """
def find_top_students(students, n):
    return []
"""
        fix_code_called = False
        def mock_fix_code(*args, **kwargs):
            nonlocal fix_code_called
            fix_code_called = True
            return "def should_not_run(): pass", "prompt"

        with patch("app.main.generate_code", return_value=(initial_code, "gen_prompt")):
            with patch("app.main.run_tests", return_value={
                "success": False,
                "failure_type": FailureType.TEST_GENERATION_FAILURE,
                "message": "No valid tests generated",
                "tests": "",
                "test_summary": {}
            }):
                with patch("app.main.fix_code", side_effect=mock_fix_code):
                    req = Request(prompt=self.reproduction_prompt)
                    result = generate(req)

                    self.assertFalse(fix_code_called, "fix_code() MUST NOT be called on TEST_GENERATION_FAILURE!")
                    print("[PASS] Test 10: 'No valid tests generated' isolated; fix_code() was not invoked.")

    def test_11_valid_assertion_error_must_enter_fix_code(self):
        """Test 11: Valid AssertionError from an actual failing test MUST enter fix_code()."""
        print("\n--- Running Test 11: Valid AssertionError Enters fix_code ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        initial_code = """
def find_top_students(students, n):
    return []
"""
        fix_code_called = False
        def mock_fix_code(*args, **kwargs):
            nonlocal fix_code_called
            fix_code_called = True
            return initial_code, "mock debug prompt"

        with patch("app.main.generate_code", return_value=(initial_code, "gen_prompt")):
            with patch("app.main.run_tests", return_value={
                "success": False,
                "failure_type": FailureType.CODE_FAILURE,
                "message": "AssertionError: Expected 2 items, got 0",
                "tests": "assert find_top_students([{'name': 'A', 'marks': [100]}], 1) != []",
                "test_summary": {"passed": 0, "failed": 1, "total": 1}
            }):
                with patch("app.main.fix_code", side_effect=mock_fix_code):
                    req = Request(prompt=self.reproduction_prompt)
                    result = generate(req)

                    self.assertTrue(fix_code_called, "fix_code() MUST be called on legitimate CODE_FAILURE!")
                    print("[PASS] Test 11: Valid AssertionError correctly triggered fix_code().")

    def test_12_candidate_code_unchanged_after_test_harness_failure(self):
        """Test 12: Candidate code must remain unchanged after TEST_HARNESS_FAILURE."""
        print("\n--- Running Test 12: Candidate Code Preservation on Harness Failure ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        candidate_code = """
def find_top_students(students, n):
    # Preserved candidate code
    return [{"name": s["name"], "average": sum(s["marks"])/len(s["marks"])} for s in students if s.get("marks")][:n]
"""
        dirty_tests = ["assert find_top_students(undefined_var, 3) == []"]

        with patch("app.main.generate_code", return_value=(candidate_code, "gen_prompt")):
            req = Request(prompt=self.reproduction_prompt, authoritative_tests=dirty_tests)
            result = generate(req)

            self.assertEqual(result["code"].strip(), candidate_code.strip())
            print("[PASS] Test 12: Candidate code remained completely intact following TEST_HARNESS_FAILURE.")

    def test_13_candidate_code_unchanged_after_test_oracle_failure(self):
        """Test 13: Candidate code must remain unchanged after TEST_ORACLE_FAILURE."""
        print("\n--- Running Test 13: Candidate Code Preservation on Oracle Failure ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        candidate_code = """
def find_top_students(students, n):
    # Preserved correct candidate code
    return [{"name": "Bob", "average": 93.5}, {"name": "Charlie", "average": 93.5}]
"""
        contradictory_test = """
assert find_top_students([], 2) == [
    {"name": "Charlie", "average": 93.5},
    {"name": "Bob", "average": 93.5}
]
"""
        with patch("app.main.generate_code", return_value=(candidate_code, "gen_prompt")):
            with patch("app.main.run_tests", return_value={
                "success": False,
                "failure_type": FailureType.TEST_ORACLE_FAILURE,
                "message": "TestOracleError: Alphabetical tie-break violated: 'Charlie' placed before 'Bob'",
                "tests": contradictory_test,
                "test_summary": {"total": 1, "passed": 0, "failed": 0, "errors": 1}
            }):
                req = Request(prompt=self.reproduction_prompt)
                result = generate(req)

                self.assertEqual(result["code"].strip(), candidate_code.strip())
                print("[PASS] Test 13: Candidate code remained completely intact following TEST_ORACLE_FAILURE.")

    def test_14_repair_history_contains_code_failures_not_harness_failures(self):
        """Test 14: Repair history must contain code failures but not harness failures."""
        print("\n--- Running Test 14: Clean Repair History ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        candidate_code = "def find_top_students(students, n): return []"
        dirty_tests = ["assert find_top_students(input_data, 1) == []"]

        with patch("app.main.generate_code", return_value=(candidate_code, "gen_prompt")):
            req = Request(prompt=self.reproduction_prompt, authoritative_tests=dirty_tests)
            result = generate(req)

            history = result.get("history", [])
            for item in history:
                self.assertNotEqual(item.get("failure_type"), FailureType.TEST_HARNESS_FAILURE)
                self.assertNotEqual(item.get("failure_type"), FailureType.TEST_ORACLE_FAILURE)
            print("[PASS] Test 14: Repair history was not polluted by test harness failures.")

    def test_15_maximum_repair_attempts_enforced(self):
        """Test 15: Maximum repair attempts must still be strictly enforced."""
        print("\n--- Running Test 15: Maximum Repair Attempts Enforced ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        code = "def find_top_students(students, n): return []"
        repair_calls = 0

        def mock_fix_code(*args, **kwargs):
            nonlocal repair_calls
            repair_calls += 1
            return code, "prompt"

        with patch("app.main.generate_code", return_value=(code, "gen_prompt")):
            with patch("app.main.run_tests", return_value={
                "success": False,
                "failure_type": FailureType.CODE_FAILURE,
                "message": "AssertionError: Genuine code bug",
                "tests": "assert False",
                "test_summary": {"passed": 0, "failed": 1, "total": 1}
            }):
                with patch("app.main.fix_code", side_effect=mock_fix_code):
                    req = Request(prompt=self.reproduction_prompt)
                    result = generate(req)

                    self.assertFalse(result["success"])
                    self.assertEqual(repair_calls, 5, "Should stop at exactly MAX_RETRIES = 5")
                    print("[PASS] Test 15: Exactly 5 repair attempts executed and terminated.")

    def test_16_repair_loop_terminates_cleanly_on_repeated_oracle_failure(self):
        """Test 16: Repair loop must terminate cleanly on repeated oracle failure."""
        print("\n--- Running Test 16: Clean Termination on Oracle Failure ---")
        config.set("LORA_ENABLED", False)
        config.set("MEMORY_ENABLED", False)

        code = "def find_top_students(students, n): return []"
        oracle_calls = 0

        def mock_run_tests(*args, **kwargs):
            nonlocal oracle_calls
            oracle_calls += 1
            return {
                "success": False,
                "failure_type": FailureType.TEST_ORACLE_FAILURE,
                "message": "TestOracleError: Contradictory test",
                "tests": "",
                "test_summary": {}
            }

        with patch("app.main.generate_code", return_value=(code, "gen_prompt")):
            with patch("app.main.run_tests", side_effect=mock_run_tests):
                req = Request(prompt=self.reproduction_prompt)
                result = generate(req)

                self.assertFalse(result["success"])
                # Must exit cleanly without looping 5 times!
                self.assertEqual(oracle_calls, 1, "Should terminate immediately on oracle failure without looping 5 times!")
                print("[PASS] Test 16: Oracle failure terminated cleanly on first occurrence.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
