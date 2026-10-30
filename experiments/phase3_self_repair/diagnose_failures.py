"""
experiments/phase3_self_repair/diagnose_failures.py
===================================================
Diagnostic script for Phase 3.1: Root-cause analysis.
Reconstructs and deeply inspects the repair trajectories for TASK_2, TASK_3, TASK_4, TASK_5.
Records exact prompt structure, model raw generation, AST parsing, contract validation, and test traces.
"""

import sys
import os
import json
import hashlib
import textwrap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.contract import extract_contract, validate_code_against_contract
from app.tester import run_tests, validate_oracle_consistency, FailureType
from app.model import generate_raw, extract_code, clean_generated_code, is_code_valid, fix_code
from experiments.phase3_self_repair.tasks import TASKS


def diagnose_task_3():
    print("\n" + "=" * 60)
    print("DIAGNOSING TASK 3: binary_search")
    print("=" * 60)
    task = TASKS[2]
    contract = extract_contract(task["prompt"], authoritative_tests=task["authoritative_tests"])
    print(f"Contract extracted: entry_point={contract.entry_point}, params={contract.parameters}")
    for r in contract.structured_requirements:
        print(f"  - {r.text}")

    res = run_tests(task["prompt"], task["seeded_defect"], authoritative_tests=task["authoritative_tests"], contract=contract)
    print(f"\nInitial Failure: {res.get('failure_type')} -> {res.get('message').splitlines()[0]}")

    # Inspect repair attempt 1
    fixed, prompt1 = fix_code(task["seeded_defect"], res["message"], task_contract=contract, attempt_history=[])
    print(f"\n--- PROMPT ATTEMPT 1 --- (length={len(prompt1)} chars)")
    print(f"Fixed code from attempt 1:\n{fixed}")
    t_res1 = run_tests(task["prompt"], fixed, authoritative_tests=task["authoritative_tests"], contract=contract)
    print(f"Test 1 result: success={t_res1['success']}, fail_type={t_res1.get('failure_type')}")
    print(f"Test 1 failure trace:\n{t_res1.get('message')}")

    # Inspect why attempts 2-4 produced the exact same code
    hist = [{
        "attempt": 1,
        "stage": "testing",
        "error_type": "AssertionError",
        "error": t_res1.get("message")
    }]
    fixed2, prompt2 = fix_code(fixed, t_res1.get("message"), task_contract=contract, attempt_history=hist)
    print(f"\n--- ATTEMPT 2 ---")
    print(f"Fixed 2 == Fixed 1: {fixed2.strip() == fixed.strip()}")
    print(f"Fixed 2:\n{fixed2}")


def diagnose_task_4():
    print("\n" + "=" * 60)
    print("DIAGNOSING TASK 4: merge_intervals")
    print("=" * 60)
    task = TASKS[3]
    contract = extract_contract(task["prompt"], authoritative_tests=task["authoritative_tests"])
    print(f"Contract extracted: entry_point={contract.entry_point}, params={contract.parameters}")
    for r in contract.structured_requirements:
        print(f"  - {r.text}")

    res = run_tests(task["prompt"], task["seeded_defect"], authoritative_tests=task["authoritative_tests"], contract=contract)
    print(f"\nInitial Failure: {res.get('failure_type')} -> {res.get('message').splitlines()[0]}")

    fixed1, prompt1 = fix_code(task["seeded_defect"], res["message"], task_contract=contract, attempt_history=[])
    print(f"\n--- ATTEMPT 1 ---")
    print(f"Candidate:\n{fixed1}")
    c_val1, c_err1 = validate_code_against_contract(fixed1, contract)
    print(f"Contract valid: {c_val1}, err={c_err1}")

    # Why did Attempt 2 return empty code in results.json?
    hist = [{
        "attempt": 1,
        "stage": "contract",
        "error_type": "ContractViolation",
        "error": c_err1
    }]
    _, prompt2 = fix_code(fixed1, c_err1, task_contract=contract, attempt_history=hist)
    print(f"\n--- ATTEMPT 2 PROMPT --- (length={len(prompt2)} chars)\n{prompt2}")
    raw2 = generate_raw(prompt2)
    print(f"Raw gen 2 (length={len(raw2)}):\n{repr(raw2)}")
    ext2 = extract_code(raw2, required_entry_point=contract.entry_point)
    print(f"Extracted 2: {repr(ext2)}")
    cln2 = clean_generated_code(ext2)
    val2 = is_code_valid(cln2, required_entry_point=contract.entry_point)
    print(f"Valid AST & entry_point 2: {val2}")


def diagnose_task_5():
    print("\n" + "=" * 60)
    print("DIAGNOSING TASK 5: schedule_meetings")
    print("=" * 60)
    task = TASKS[4]
    contract = extract_contract(task["prompt"], authoritative_tests=task["authoritative_tests"])
    print(f"Contract extracted: entry_point={contract.entry_point}, params={contract.parameters}")
    for r in contract.structured_requirements:
        print(f"  - {r.text}")

    c_val0, c_err0 = validate_code_against_contract(task["seeded_defect"], contract)
    print(f"Initial Contract Validation: valid={c_val0}, err={c_err0}")

    # Inspect the final candidate from Attempt 3/4
    # In results.json, Attempt 3/4 passed contract and failed tests
    with open("experiments/phase3_self_repair/results.json", "r") as f:
        data = json.load(f)
    t5_data = data["tasks"][4]
    final_code = t5_data["final_code"]
    print(f"\nT5 Final Code:\n{final_code}")
    t_res = run_tests(task["prompt"], final_code, authoritative_tests=task["authoritative_tests"], contract=contract)
    print(f"T5 Final Code Test Result: success={t_res['success']}, fail_type={t_res.get('failure_type')}")
    print(f"T5 Failure Trace:\n{t_res.get('message')}")


if __name__ == "__main__":
    diagnose_task_3()
    diagnose_task_4()
    diagnose_task_5()
