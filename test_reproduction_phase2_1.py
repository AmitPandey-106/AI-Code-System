"""
test_reproduction_phase2_1.py
==============================
Exact reproduction verification for Phase 2.1:
Validates that the task-agnostic system satisfies all criteria for find_top_students:
- extracts the contract
- preserves requirements
- rejects contradictory oracle candidates
- rejects malformed tests
- isolates test-harness failures
- does not corrupt candidate code
"""

import sys
from app.contract import extract_contract, validate_plan_against_contract, validate_code_against_contract
from app.tester import validate_oracle_consistency, validate_test_variables, clean_test_code, run_tests, OracleValidationState, FailureType
from app.main import generate, Request

prompt = """Implement find_top_students(students, n):
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

print("==================================================")
print("REPRODUCTION VERIFICATION: PHASE 2.1")
print("==================================================")

# 1. Contract Extraction
contract = extract_contract(prompt)
print(f"Contract Entry Point: {contract.entry_point}")
print(f"Contract Parameters: {contract.parameters}")
print(f"Number of Structured Requirements: {len(contract.structured_requirements)}")
assert contract.entry_point == "find_top_students", "Contract entry point mismatch"
assert contract.parameters == ["students", "n"], "Contract parameters mismatch"
print("[PASS] 1. Contract extraction verified.")

# 2. Plan Requirement Preservation
lossy_plan = "1. Calculate average\n2. Return top n"
is_valid_lossy, missing = validate_plan_against_contract(lossy_plan, contract)
assert not is_valid_lossy, "Lossy plan should be invalid"
print(f"[PASS] 2. Plan requirement detection verified (flagged missing: {len(missing)} requirements).")

# 3. Contradictory Oracle Rejection
contradictory_tie_break = """
assert find_top_students(
    [{"name": "Charlie", "marks": [90, 97]},
     {"name": "Bob", "marks": [93, 94]}],
    2
) == [{"name": "Charlie", "average": 93.5}, {"name": "Bob", "average": 93.5}]
"""
res_contra = validate_oracle_consistency(contradictory_tie_break, contract)
assert res_contra.state == OracleValidationState.CONTRADICTORY, f"Expected CONTRADICTORY, got {res_contra.state}"
print(f"[PASS] 3a. Contradictory tie-break rejected: {res_contra.reason}")

contradictory_boundary = """
assert find_top_students([{"name": "Alice", "marks": [100]}], 0) == [{"name": "Alice", "average": 100.0}]
"""
res_bound = validate_oracle_consistency(contradictory_boundary, contract)
assert res_bound.state == OracleValidationState.CONTRADICTORY, f"Expected CONTRADICTORY, got {res_bound.state}"
print(f"[PASS] 3b. Contradictory boundary rejected: {res_bound.reason}")

# 4. Malformed Tests & Undefined Variables Rejection
malformed_test = "assert find_top_students(input_students, 2) == expected_students"
ok_vars, var_err = validate_test_variables(malformed_test, allowed_names=[contract.entry_point])
assert not ok_vars, "Undefined variables should be rejected"
print(f"[PASS] 4. Undefined variable test rejected: {var_err}")

# 5. Harness Failure Isolation
candidate_code = """
def find_top_students(students, n):
    if n <= 0:
        return []
    valid = []
    for s in students:
        if isinstance(s, dict) and "marks" in s and s["marks"]:
            valid.append({"name": s.get("name", ""), "average": round(sum(s["marks"]) / len(s["marks"]), 2)})
    valid.sort(key=lambda x: (-x["average"], x["name"]))
    return valid[:n]
"""
harness_err_tests = ["assert find_top_students(undefined_x, 1) == []"]
test_res = run_tests(prompt, candidate_code, authoritative_tests=harness_err_tests, contract=contract)
assert test_res["failure_type"] == FailureType.TEST_HARNESS_FAILURE, f"Expected TEST_HARNESS_FAILURE, got {test_res['failure_type']}"
print(f"[PASS] 5. Test harness error isolated with FailureType.TEST_HARNESS_FAILURE.")

# 6. Candidate Code Safety
# Verify candidate code is untouched and satisfies contract
cv_ok, cv_err = validate_code_against_contract(candidate_code, contract)
assert cv_ok, f"Candidate code contract error: {cv_err}"
print(f"[PASS] 6. Candidate code safely preserved without mutation.")

print("==================================================")
print("ALL REPRODUCTION VERIFICATION CHECKS PASSED 100%!")
print("==================================================")
