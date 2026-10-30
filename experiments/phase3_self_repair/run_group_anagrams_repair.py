"""
experiments/phase3_self_repair/run_group_anagrams_repair.py
===========================================================
Executes the closed-loop repair sequence for group_anagrams:
1. Initial Defective Code
2. Execution Failure
3. Failure Diagnosis
4. Model-Driven Repair (fix_code)
5. Contract Validation
6. Re-Execution against Authoritative Tests
7. Final Acceptance Decision
"""

import sys
import os
import json
import hashlib
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.contract import extract_contract, validate_code_against_contract
from app.tester import run_tests, FailureType
from app.model import fix_code


def compute_hash(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()[:12]


TASK_PROMPT = """Implement the following Python function:

def group_anagrams(words):
    \"\"\"
    Group words that are anagrams of each other.

    Requirements:
    1. Return a list of groups.
    2. Words with exactly the same characters and frequencies belong
       to the same group.
    3. Character order must not affect grouping.
    4. Preserve the original spelling of each word.
    5. Preserve the original input order of words within each group.
    6. Order groups according to the position of the first word from
       each group in the original input.
    7. Words with different character frequencies must not be grouped.
    8. Empty input -> [].
    9. Single word -> one group containing it.
    10. Do not modify the input list.
    11. Do not modify the original strings.
    12. Return a newly created list containing newly created groups.
    \"\"\"
"""

INITIAL_DEFECTIVE_CODE = """def group_anagrams(words):
    groups = {}

    for word in words:
        key = ''.join(sorted(word))
        groups[key] = [word]

    return list(groups.values())
"""

AUTHORITATIVE_TESTS = [
    'assert group_anagrams(["eat","tea","tan","ate","nat","bat"]) == [["eat","tea","ate"],["tan","nat"],["bat"]]',
    'assert group_anagrams([]) == []',
    'assert group_anagrams(["a"]) == [["a"]]',
    'assert group_anagrams(["", ""]) == [["", ""]]',
    'assert group_anagrams(["a", "b", "a"]) == [["a", "a"], ["b"]]'
]


def run_experiment():
    print("=" * 70)
    print("STARTING EXPERIMENT: group_anagrams CLOSED-LOOP REPAIR")
    print("=" * 70)

    # 1. Contract Extraction
    contract = extract_contract(TASK_PROMPT, authoritative_tests=AUTHORITATIVE_TESTS)
    print(f"\n[CONTRACT] Extracted primary entry point: {contract.entry_point}")
    print(f"[CONTRACT] Parameters: {contract.parameters}")
    for req in contract.structured_requirements:
        print(f"  - {req.text}")

    # 2. Step 1: Initial Defective Code Evaluation
    init_hash = compute_hash(INITIAL_DEFECTIVE_CODE)
    print(f"\n[STEP 1: INITIAL CANDIDATE (ATTEMPT 0)] Hash: {init_hash}")
    print(INITIAL_DEFECTIVE_CODE)

    # Check contract before execution
    c_valid, c_err = validate_code_against_contract(INITIAL_DEFECTIVE_CODE, contract)
    print(f"[CONTRACT CHECK] Valid: {c_valid} (Error: {c_err})")

    # Execute against authoritative tests
    print("\n[STEP 2: EXECUTING INITIAL CANDIDATE AGAINST AUTHORITATIVE TESTS]")
    initial_test_res = run_tests(TASK_PROMPT, INITIAL_DEFECTIVE_CODE, authoritative_tests=AUTHORITATIVE_TESTS, contract=contract)
    print(f"Success: {initial_test_res['success']}")
    print(f"Failure Type: {initial_test_res.get('failure_type')}")
    print(f"Message:\n{initial_test_res.get('message')}")

    if initial_test_res["success"]:
        print("ERROR: Initial defective candidate unexpectedly passed!")
        return

    # 3. Step 3: Failure Diagnosis
    print("\n[STEP 3: FAILURE DIAGNOSIS]")
    failure_msg = initial_test_res.get("message", "")
    print(f"Diagnosed failure: {failure_msg.splitlines()[0]}")
    print("Cause: Overwriting dictionary entry on duplicate keys instead of appending to existing group.")

    # 4. Step 4: Repair Loop
    attempt_history = []
    repair_candidate_hashes = []
    current_code = INITIAL_DEFECTIVE_CODE
    current_error = failure_msg
    accepted = False
    max_attempts = 4

    for attempt in range(max_attempts):
        attempt_num = attempt + 1
        print(f"\n" + "-" * 50)
        print(f"[STEP 4: REPAIR ATTEMPT {attempt_num}] Invoking fix_code()...")
        print("-" * 50)

        t_start = time.time()
        fixed_code, debug_prompt = fix_code(
            original_code=current_code,
            error=current_error,
            task_contract=contract,
            attempt_history=attempt_history
        )
        elapsed = round(time.time() - t_start, 2)

        if not fixed_code or not fixed_code.strip():
            print(f"Attempt {attempt_num}: fix_code returned empty code.")
            break

        cand_hash = compute_hash(fixed_code)
        repair_candidate_hashes.append(cand_hash)
        print(f"Generated repair candidate [Hash: {cand_hash}] in {elapsed}s:")
        print(fixed_code)

        # 5. Step 5: Contract Validation
        print(f"\n[STEP 5: CONTRACT VALIDATION - ATTEMPT {attempt_num}]")
        c_val, c_err = validate_code_against_contract(fixed_code, contract)
        print(f"Contract Valid: {c_val}")
        if not c_val:
            print(f"Contract Violation: {c_err}")
            current_error = c_err
            current_code = fixed_code
            attempt_history.append({
                "attempt": attempt_num,
                "stage": "contract",
                "error_type": "ContractViolation",
                "error": c_err,
                "candidate_hash": cand_hash
            })
            continue

        # 6. Step 6: Test Execution
        print(f"\n[STEP 6: EXECUTING REPAIRED CANDIDATE AGAINST AUTHORITATIVE TESTS]")
        test_res = run_tests(TASK_PROMPT, fixed_code, authoritative_tests=AUTHORITATIVE_TESTS, contract=contract)
        print(f"Test Success: {test_res['success']}")
        print(f"Test Summary: {test_res.get('test_summary')}")

        if test_res["success"]:
            print(f"\n*** SUCCESS: Candidate passed all {len(AUTHORITATIVE_TESTS)} authoritative tests! ***")
            accepted = True
            current_code = fixed_code
            attempt_history.append({
                "attempt": attempt_num,
                "stage": "testing",
                "status": "passed",
                "candidate_hash": cand_hash
            })
            break
        else:
            print(f"Test Failed: {test_res.get('message').splitlines()[0]}")
            current_error = test_res.get("message")
            current_code = fixed_code
            attempt_history.append({
                "attempt": attempt_num,
                "stage": "testing",
                "error_type": "AssertionError",
                "error": current_error,
                "candidate_hash": cand_hash
            })

    # 7. Step 7: Final Result & Decision
    print("\n" + "=" * 70)
    print("FINAL EXPERIMENT DECISION")
    print("=" * 70)
    differs_from_seed = (compute_hash(current_code) != init_hash)
    self_repair_success = accepted and differs_from_seed

    result_summary = {
        "task": "group_anagrams",
        "initial_candidate_hash": init_hash,
        "initial_failure_type": initial_test_res.get("failure_type"),
        "total_repair_attempts": len(repair_candidate_hashes),
        "repair_candidate_hashes": repair_candidate_hashes,
        "accepted": accepted,
        "self_repair_success": self_repair_success,
        "final_code": current_code
    }

    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "group_anagrams_repair_result.json"))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result_summary, f, indent=2)

    if self_repair_success:
        print("DECISION: VERIFIED PASSED")
    else:
        print("DECISION: FAILED")
    print(f"Report saved to: {out_file}")
    print("=" * 70)

    return result_summary


if __name__ == "__main__":
    run_experiment()
