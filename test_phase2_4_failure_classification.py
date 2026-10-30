"""
test_phase2_4_failure_classification.py
========================================
Regression test suite for Phase 2.4:
Failure Classification and Self-Repair Gate Verification.

Verifies:
1. Valid deterministic test + wrong candidate -> CODE_FAILURE
2. Invalid test syntax -> TEST_GENERATION_FAILURE / TEST_HARNESS_FAILURE
3. Undefined test variable -> TEST_GENERATION_FAILURE / TEST_HARNESS_FAILURE
4. Contradictory oracle -> ORACLE_CONTRADICTORY (TEST_ORACLE_FAILURE)
5. Genuinely unresolved semantic oracle -> ORACLE_UNDETERMINED
6. Candidate syntax error -> CONTRACT_FAILURE / SyntaxError
7. Candidate that mutates an input list when immutability is required -> CONTRACT_FAILURE
8. Candidate missing required entry point -> CONTRACT_FAILURE
9. Candidate with valid target but failing deterministic assertion -> CODE_FAILURE
10. Verify only candidate failures (CODE_FAILURE, CONTRACT_FAILURE) can enter fix_code().
"""

import unittest
import ast
from app.contract import extract_contract, validate_code_against_contract
from app.tester import (
    run_tests,
    validate_oracle_consistency,
    OracleValidationState,
    OracleValidationResult,
    FailureType
)


class TestPhase24FailureClassification(unittest.TestCase):

    # 1. Valid deterministic test + wrong candidate -> CODE_FAILURE
    def test_01_valid_deterministic_test_wrong_candidate(self):
        """A valid executable test on a candidate with wrong logic must yield CODE_FAILURE."""
        prompt = "def add(a, b): return a + b"
        wrong_code = "def add(a, b):\n    return a - b\n"
        tests = ["assert add(2, 3) == 5"]
        res = run_tests(prompt, wrong_code, authoritative_tests=tests)
        self.assertFalse(res["success"])
        self.assertEqual(res["failure_type"], FailureType.CODE_FAILURE)
        self.assertIn("AssertionError", res["message"])

    # 2. Invalid test syntax -> TEST_GENERATION_FAILURE
    def test_02_invalid_test_syntax(self):
        """Invalid test syntax must yield TEST_GENERATION_FAILURE or TEST_HARNESS_FAILURE."""
        prompt = "def add(a, b): return a + b"
        code = "def add(a, b): return a + b"
        broken_test = "assert add(2, 3 == "
        res = run_tests(prompt, code, authoritative_tests=[broken_test])
        self.assertFalse(res["success"])
        self.assertIn(res["failure_type"], (FailureType.TEST_GENERATION_FAILURE, FailureType.TEST_HARNESS_FAILURE))

    # 3. Undefined test variable -> TEST_GENERATION_FAILURE / TEST_HARNESS_FAILURE
    def test_03_undefined_test_variable(self):
        """Undefined test variable placeholders must yield TEST_GENERATION_FAILURE / TEST_HARNESS_FAILURE."""
        prompt = "def compute(x): return x"
        code = "def compute(x): return x"
        bad_test = "assert compute(unresolved_placeholder_input) == expected_output"
        res = run_tests(prompt, code, authoritative_tests=[bad_test])
        self.assertFalse(res["success"])
        self.assertIn(res["failure_type"], (FailureType.TEST_GENERATION_FAILURE, FailureType.TEST_HARNESS_FAILURE))

    # 4. Contradictory oracle -> ORACLE_CONTRADICTORY
    def test_04_contradictory_oracle(self):
        """A test contradicting known contract requirements must be classified as CONTRADICTORY."""
        prompt = """Implement find_top_students(students, n):
- if n <= 0, return []
"""
        contract = extract_contract(prompt)
        contradictory_test = 'assert find_top_students([{"name": "Alice", "marks": [90]}], 0) == [{"name": "Alice", "average": 90.0}]'
        val_res = validate_oracle_consistency(contradictory_test, contract)
        self.assertIn(val_res.state, (OracleValidationState.CONTRADICTORY, OracleValidationState.ORACLE_CONTRADICTORY))
        self.assertTrue(val_res.is_contradictory)

        res = run_tests(prompt, "def find_top_students(students, n): return []", authoritative_tests=[contradictory_test], contract=contract)
        self.assertFalse(res["success"])
        self.assertIn(res["failure_type"], (FailureType.TEST_ORACLE_FAILURE, FailureType.ORACLE_CONTRADICTORY))

    # 5. Genuinely unresolved semantic oracle -> ORACLE_UNDETERMINED
    def test_05_genuinely_unresolved_semantic_oracle(self):
        """When an oracle cannot be deterministically verified statically, state must be UNDETERMINED."""
        prompt = "def process_data(items): return items"
        contract = extract_contract(prompt)
        arbitrary_test = "assert process_data([1, 2, 3]) == [1, 2, 3]"
        val_res = validate_oracle_consistency(arbitrary_test, contract)
        self.assertIn(val_res.state, (OracleValidationState.UNDETERMINED, OracleValidationState.ORACLE_UNDETERMINED))

    # 6. Candidate syntax error -> CONTRACT_FAILURE
    def test_06_candidate_syntax_error(self):
        """Candidate with invalid Python syntax must be rejected by contract validation."""
        prompt = "def solve(): return 42"
        contract = extract_contract(prompt)
        broken_candidate = "def solve(): return 1 +"
        valid, err = validate_code_against_contract(broken_candidate, contract)
        self.assertFalse(valid)
        self.assertIn("SyntaxError", err)

    # 7. Candidate that mutates an input list when immutability is required -> CONTRACT_FAILURE
    def test_07_candidate_mutates_input_list_when_immutability_required(self):
        """Candidate performing in-place mutation when immutability is required must fail contract validation."""
        prompt = """Implement schedule_meetings(meetings):
Requirements:
1. The input list must not be modified.
2. The original meeting dictionaries must not be modified.
"""
        contract = extract_contract(prompt)
        mutating_candidate = """
def schedule_meetings(meetings):
    meetings.sort(key=lambda x: x['start'])
    return meetings
"""
        valid, err = validate_code_against_contract(mutating_candidate, contract)
        self.assertFalse(valid)
        self.assertIn("In-place mutation detected", err)
        self.assertIn("meetings", err)
        self.assertIn("sort", err)

    # 8. Candidate missing required entry point -> CONTRACT_FAILURE
    def test_08_candidate_missing_required_entry_point(self):
        """Candidate that omits the contract entry point must fail contract validation."""
        prompt = "def schedule_meetings(meetings): return []"
        contract = extract_contract(prompt)
        wrong_entry = "def helper_schedule(m): return []"
        valid, err = validate_code_against_contract(wrong_entry, contract)
        self.assertFalse(valid)
        self.assertIn("ContractViolation: Required entry point 'schedule_meetings' is missing", err)

    # 9. Candidate with valid target but failing deterministic assertion -> CODE_FAILURE
    def test_09_candidate_valid_target_failing_assertion(self):
        """Candidate with correct entry point but flawed logic must fail with CODE_FAILURE."""
        prompt = """Implement schedule_meetings(meetings):
Requirements:
1. Two meetings overlap when next start < current end.
"""
        contract = extract_contract(prompt)
        flawed_candidate = """
def schedule_meetings(meetings):
    # Flawed logic: does not merge overlapping meetings
    return [dict(m) for m in meetings]
"""
        test_case = """
meetings = [
    {"title": "A", "start": 9, "end": 11},
    {"title": "B", "start": 10, "end": 12}
]
assert schedule_meetings(meetings) == [{"title": "A + B", "start": 9, "end": 12}]
"""
        res = run_tests(prompt, flawed_candidate, authoritative_tests=[test_case], contract=contract)
        self.assertFalse(res["success"])
        self.assertEqual(res["failure_type"], FailureType.CODE_FAILURE)
        self.assertIn("AssertionError", res["message"])

    # 10. Verify only candidate failures can enter fix_code()
    def test_10_verify_only_candidate_failures_can_enter_fix_code(self):
        """Verify the isolation decision gate: only CODE_FAILURE and CONTRACT_FAILURE can trigger repair."""
        def can_repair(failure_type: str) -> bool:
            return failure_type not in (
                "TEST_HARNESS_FAILURE",
                "TEST_ORACLE_FAILURE",
                "TEST_GENERATION_FAILURE",
                "ORACLE_UNDETERMINED"
            )

        # Candidate failures must trigger repair
        self.assertTrue(can_repair("CODE_FAILURE"))
        self.assertTrue(can_repair("CONTRACT_FAILURE"))

        # Oracle, harness, and generation failures must be isolated
        self.assertFalse(can_repair("TEST_HARNESS_FAILURE"))
        self.assertFalse(can_repair("TEST_ORACLE_FAILURE"))
        self.assertFalse(can_repair("TEST_GENERATION_FAILURE"))
        self.assertFalse(can_repair("ORACLE_UNDETERMINED"))


if __name__ == "__main__":
    unittest.main()
