"""
test_phase3_self_repair.py
==========================
Automated verification test suite for Phase 3:
Controlled Closed-Loop Self-Repair Validation.

Verifies:
1. Seeded candidates trigger initial failure (CODE_FAILURE or CONTRACT_FAILURE).
2. fix_code() produces modified repair candidates.
3. Repaired candidates satisfy TaskContract and authoritative test assertions.
4. Negative controls isolate invalid, contradictory, and undetermined oracles.
5. In-place input mutations are caught as CONTRACT_FAILURE before execution.
"""

import unittest
import hashlib
from app.contract import extract_contract, validate_code_against_contract
from app.tester import run_tests, validate_oracle_consistency, OracleValidationState, FailureType
from app.model import fix_code
from experiments.phase3_self_repair.tasks import TASKS, NEGATIVE_CONTROLS


class TestPhase3SelfRepair(unittest.TestCase):

    def test_01_seeded_candidates_initially_fail(self):
        """Verify that every seeded defect in the experiment suite fails initial evaluation."""
        for task in TASKS:
            contract = extract_contract(task["prompt"], authoritative_tests=task["authoritative_tests"])
            c_valid, c_err = validate_code_against_contract(task["seeded_defect"], contract)
            if not c_valid:
                self.assertIn("ContractViolation", c_err)
            else:
                test_res = run_tests(
                    task["prompt"],
                    task["seeded_defect"],
                    authoritative_tests=task["authoritative_tests"],
                    contract=contract
                )
                self.assertFalse(test_res["success"], f"Task {task['task_id']} unexpectedly passed with seeded defect!")
                self.assertEqual(test_res["failure_type"], FailureType.CODE_FAILURE)

    def test_02_arithmetic_closed_loop_repair(self):
        """Closed-loop repair on Task 1 (add with seeded subtraction)."""
        task = TASKS[0]  # add
        contract = extract_contract(task["prompt"], authoritative_tests=task["authoritative_tests"])
        
        # 1. Initial failure
        test_res = run_tests(task["prompt"], task["seeded_defect"], authoritative_tests=task["authoritative_tests"], contract=contract)
        self.assertFalse(test_res["success"])
        self.assertEqual(test_res["failure_type"], FailureType.CODE_FAILURE)

        # 2. Invoke repair
        fixed_code, _ = fix_code(
            original_code=task["seeded_defect"],
            error=test_res["message"],
            task_contract=contract
        )
        self.assertTrue(bool(fixed_code.strip()))
        self.assertNotEqual(fixed_code.strip(), task["seeded_defect"].strip())

        # 3. Validate repaired candidate
        c_valid, _ = validate_code_against_contract(fixed_code, contract)
        self.assertTrue(c_valid)
        t_res = run_tests(task["prompt"], fixed_code, authoritative_tests=task["authoritative_tests"], contract=contract)
        self.assertTrue(t_res["success"])

    def test_03_negative_control_invalid_test_isolation(self):
        """Negative Control 1: Invalid test syntax must be isolated and not trigger repair."""
        nc = NEGATIVE_CONTROLS[0]
        res = run_tests(nc["prompt"], nc["candidate"], authoritative_tests=[nc["test"]])
        self.assertFalse(res["success"])
        self.assertIn(res["failure_type"], (FailureType.TEST_GENERATION_FAILURE, FailureType.TEST_HARNESS_FAILURE))

    def test_04_negative_control_contradictory_oracle_isolation(self):
        """Negative Control 2: Contradictory test oracle must be rejected and isolated."""
        nc = NEGATIVE_CONTROLS[1]
        contract = extract_contract(nc["prompt"])
        val_res = validate_oracle_consistency(nc["test"], contract)
        self.assertTrue(val_res.is_contradictory)
        res = run_tests(nc["prompt"], nc["candidate"], authoritative_tests=[nc["test"]], contract=contract)
        self.assertFalse(res["success"])
        self.assertIn(res["failure_type"], (FailureType.TEST_ORACLE_FAILURE, FailureType.ORACLE_CONTRADICTORY))

    def test_05_negative_control_undetermined_oracle_isolation(self):
        """Negative Control 3: Undetermined test oracle in isolation must yield UNDETERMINED state."""
        nc = NEGATIVE_CONTROLS[2]
        val_res = validate_oracle_consistency(nc["test"], None)
        self.assertIn(val_res.state, (OracleValidationState.UNDETERMINED, OracleValidationState.ORACLE_UNDETERMINED))

    def test_06_schedule_meetings_seeded_mutation_detected(self):
        """Task 5 seeded candidate with in-place meetings.sort() must fail contract validation."""
        task = TASKS[4]  # schedule_meetings
        contract = extract_contract(task["prompt"], authoritative_tests=task["authoritative_tests"])
        c_valid, c_err = validate_code_against_contract(task["seeded_defect"], contract)
        self.assertFalse(c_valid)
        self.assertIn("In-place mutation detected", c_err)
        self.assertIn("meetings", c_err)


if __name__ == "__main__":
    unittest.main()
