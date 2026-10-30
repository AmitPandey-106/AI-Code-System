"""
experiments/phase3_self_repair/runner_phase3_4.py
=================================================
Ablation experiment driver for Phase 3.4:
Same Prompt (Phase 3.2 baseline) + Dynamic Temperature Escalation
ONLY after a repeated candidate is detected.

Protocol:
- Attempt 1: Temperature = 0.2 (baseline)
- Attempt N: Temperature = 0.2 normally
- If candidate N == candidate N-1:
  Record REPEATED_CANDIDATE
  Next attempt escalates Temperature = 0.6 ONLY for that attempt to break mode collapse
- Outputs to experiments/phase3_self_repair/phase3_4_results.json
"""

import sys
import os
import time
import json
import hashlib
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.contract import extract_contract, validate_code_against_contract
from app.tester import run_tests, validate_oracle_consistency, OracleValidationState, FailureType
from app.model import fix_code
from experiments.phase3_self_repair.tasks import TASKS, NEGATIVE_CONTROLS


def compute_hash(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()[:12]


def run_phase3_4_experiment() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("STARTING PHASE 3.4: TEMPERATURE ESCALATION ONLY AFTER REPEATED CANDIDATE")
    print("=" * 60 + "\n")

    # Load Phase 3.2 baseline for comparison
    baseline_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "results.json"))
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)
    baseline_tasks = {t["task_id"]: t for t in baseline_data["tasks"]}

    task_results: List[Dict[str, Any]] = []
    total_start_time = time.time()

    # =========================================================
    # PART 1: EVALUATE 5 SEEDED DEFECT TASKS
    # =========================================================

    for task in TASKS:
        t_id = task["task_id"]
        t_name = task["task_name"]
        domain = task["domain"]
        seeded_code = task["seeded_defect"]
        authoritative_tests = task["authoritative_tests"]
        base_t = baseline_tasks.get(t_id, {})

        print(f"\n--- Running Task: {t_id} [{t_name}] (Domain: {domain}) ---")
        task_start = time.time()
        initial_hash = compute_hash(seeded_code)

        # 1. Extract Task Contract
        contract = extract_contract(task["prompt"], authoritative_tests=authoritative_tests)

        # 2. Initial Contract & Test Validation
        contract_valid, contract_err = validate_code_against_contract(seeded_code, contract)
        if not contract_valid:
            initial_failure_type = "CONTRACT_FAILURE"
            initial_failure_trace = contract_err
            print(f"Initial Failure: CONTRACT_FAILURE -> {contract_err}")
        else:
            test_res = run_tests(task["prompt"], seeded_code, authoritative_tests=authoritative_tests, contract=contract)
            if not test_res["success"]:
                initial_failure_type = test_res.get("failure_type", "CODE_FAILURE")
                initial_failure_trace = test_res.get("message", "Test Failed")
                print(f"Initial Failure: {initial_failure_type} -> {initial_failure_trace.splitlines()[0]}")
            else:
                initial_failure_type = "NONE"
                initial_failure_trace = "None"
                print("WARNING: Seeded code unexpectedly passed initial evaluation!")

        # 3. Verify Initial Defect Tripped Candidate Gate
        is_candidate_failure = initial_failure_type in ("CODE_FAILURE", "CONTRACT_FAILURE")
        repair_invoked = is_candidate_failure

        current_code = seeded_code
        current_error = initial_failure_trace
        attempt_history = []
        repair_candidate_hashes = []
        temperature_per_attempt = []
        failure_type_per_attempt = [initial_failure_type]
        accepted = False
        model_calls = 0
        repeated_candidate_count = 0
        max_attempts = 4

        # 4. Closed-Loop Repair Trajectory with Conditional Temperature Escalation
        if repair_invoked:
            for attempt in range(max_attempts):
                attempt_num = attempt + 1
                model_calls += 1

                # Determine active temperature: 0.6 if last attempt was repeated, else 0.2
                is_after_repeated = bool(attempt_history and attempt_history[-1].get("is_repeated_candidate"))
                active_temp = 0.6 if is_after_repeated else 0.2
                temperature_per_attempt.append(active_temp)

                print(f"  Attempt {attempt_num}: Invoking fix_code() (Temperature={active_temp}, after_repeated={is_after_repeated})...")

                fixed_code, debug_prompt = fix_code(
                    original_code=current_code,
                    error=current_error,
                    task_contract=contract,
                    attempt_history=attempt_history,
                    temperature=active_temp
                )

                if not fixed_code or not fixed_code.strip():
                    print("    fix_code returned empty code.")
                    break

                cand_hash = compute_hash(fixed_code)
                is_repeated = (len(repair_candidate_hashes) > 0 and cand_hash == repair_candidate_hashes[-1])
                if is_repeated:
                    repeated_candidate_count += 1
                    print(f"    WARNING: REPEATED_CANDIDATE detected [hash: {cand_hash}]")

                repair_candidate_hashes.append(cand_hash)
                print(f"    Generated repair candidate [hash: {cand_hash}] (repeated={is_repeated})")

                # Validate repaired candidate against contract
                c_valid, c_err = validate_code_against_contract(fixed_code, contract)
                if not c_valid:
                    print(f"    Repair attempt {attempt_num} failed contract: {c_err}")
                    current_error = c_err
                    current_code = fixed_code
                    attempt_history.append({
                        "attempt": attempt_num,
                        "stage": "contract",
                        "error_type": "ContractViolation",
                        "error": c_err,
                        "candidate_hash": cand_hash,
                        "is_repeated_candidate": is_repeated,
                        "temperature": active_temp
                    })
                    failure_type_per_attempt.append("CONTRACT_FAILURE")
                    continue

                # Run authoritative tests on candidate
                t_res = run_tests(task["prompt"], fixed_code, authoritative_tests=authoritative_tests, contract=contract)
                if t_res["success"]:
                    print(f"    SUCCESS: Repair attempt {attempt_num} passed all authoritative tests and contract validation!")
                    accepted = True
                    current_code = fixed_code
                    attempt_history.append({
                        "attempt": attempt_num,
                        "stage": "testing",
                        "status": "passed",
                        "candidate_hash": cand_hash,
                        "is_repeated_candidate": is_repeated,
                        "temperature": active_temp
                    })
                    failure_type_per_attempt.append("NONE")
                    break
                else:
                    fail_type = t_res.get("failure_type", "CODE_FAILURE")
                    err_msg = t_res.get("message", "Test assertion failed")
                    print(f"    Repair attempt {attempt_num} failed test ({fail_type}): {err_msg.splitlines()[0]}")
                    current_error = err_msg
                    current_code = fixed_code
                    attempt_history.append({
                        "attempt": attempt_num,
                        "stage": "testing",
                        "error_type": "AssertionError",
                        "error": err_msg,
                        "candidate_hash": cand_hash,
                        "is_repeated_candidate": is_repeated,
                        "temperature": active_temp
                    })
                    failure_type_per_attempt.append(fail_type)

        elapsed = round(time.time() - task_start, 2)
        differs_from_seed = (compute_hash(current_code) != initial_hash)

        is_self_repair_success = (
            initial_failure_type in ("CODE_FAILURE", "CONTRACT_FAILURE")
            and repair_invoked
            and differs_from_seed
            and accepted
        )

        task_result = {
            "task_id": t_id,
            "task_name": t_name,
            "domain": domain,
            "baseline_phase3_2_result": "SUCCESS" if base_t.get("self_repair_success") else "FAILED",
            "phase3_4_result": "SUCCESS" if is_self_repair_success else "FAILED",
            "initial_failure": initial_failure_type,
            "initial_candidate_hash": initial_hash,
            "repair_attempts": len(repair_candidate_hashes),
            "model_calls": model_calls,
            "candidate_hashes": repair_candidate_hashes,
            "temperature_per_attempt": temperature_per_attempt,
            "repeated_candidate_count": repeated_candidate_count,
            "final_contract": "VALID" if (accepted or c_valid) else "FAILED",
            "final_tests": "ALL_PASSED" if accepted else "FAILED",
            "accepted": accepted,
            "self_repair_success": is_self_repair_success,
            "elapsed_time": elapsed,
            "final_code": current_code
        }
        task_results.append(task_result)

    # =========================================================
    # PART 2: NEGATIVE CONTROLS (Safety & Failure Isolation)
    # =========================================================

    print("\n" + "=" * 60)
    print("PART 2: EVALUATING NEGATIVE CONTROLS (SAFETY ISOLATION)")
    print("=" * 60)

    negative_control_results: List[Dict[str, Any]] = []

    for nc in NEGATIVE_CONTROLS:
        c_id = nc["control_id"]
        c_name = nc["name"]
        print(f"\n--- Negative Control: {c_id} [{c_name}] ---")

        if c_id == "NC_1":
            res = run_tests(nc["prompt"], nc["candidate"], authoritative_tests=[nc["test"]])
            passed = (res["failure_type"] in (FailureType.TEST_GENERATION_FAILURE, FailureType.TEST_HARNESS_FAILURE))
            fix_called = False
            print(f"  Result: failure_type={res['failure_type']}, fix_code() called={fix_called} -> Pass: {passed}")

        elif c_id == "NC_2":
            c_contract = extract_contract(nc["prompt"])
            v_res = validate_oracle_consistency(nc["test"], c_contract)
            t_res = run_tests(nc["prompt"], nc["candidate"], authoritative_tests=[nc["test"]], contract=c_contract)
            passed = (v_res.is_contradictory and t_res["failure_type"] in (FailureType.TEST_ORACLE_FAILURE, FailureType.ORACLE_CONTRADICTORY))
            fix_called = False
            print(f"  Result: oracle_state={v_res.state}, failure_type={t_res['failure_type']}, fix_code() called={fix_called} -> Pass: {passed}")

        elif c_id == "NC_3":
            v_res = validate_oracle_consistency(nc["test"], None)
            passed = (v_res.state in (OracleValidationState.UNDETERMINED, OracleValidationState.ORACLE_UNDETERMINED))
            fix_called = False
            print(f"  Result: oracle_state={v_res.state}, fix_code() called={fix_called} -> Pass: {passed}")

        negative_control_results.append({
            "control_id": c_id,
            "name": c_name,
            "passed": passed,
            "fix_code_invoked": fix_called
        })

    # =========================================================
    # PART 3: AGGREGATE SUMMARY & SAVE
    # =========================================================

    total_tasks = len(task_results)
    successes = sum(1 for t in task_results if t["self_repair_success"])
    success_rate = round((successes / total_tasks) * 100, 1)
    mean_attempts = round(sum(t["repair_attempts"] for t in task_results) / total_tasks, 2)
    mean_model_calls = round(sum(t["model_calls"] for t in task_results) / total_tasks, 2)
    total_repeated = sum(t["repeated_candidate_count"] for t in task_results)
    total_elapsed = round(time.time() - total_start_time, 2)
    all_nc_passed = all(nc["passed"] for nc in negative_control_results)

    summary = {
        "experiment_name": "PHASE_3_4_TEMPERATURE_ESCALATION_ABLATION",
        "total_tasks": total_tasks,
        "self_repair_successes": successes,
        "self_repair_success_rate_percent": success_rate,
        "baseline_phase3_2_success_rate_percent": 40.0,
        "delta_percentage_points": round(success_rate - 40.0, 1),
        "mean_repair_attempts": mean_attempts,
        "mean_model_calls": mean_model_calls,
        "total_repeated_candidates": total_repeated,
        "negative_controls_all_passed": all_nc_passed,
        "total_elapsed_seconds": total_elapsed
    }

    full_output = {
        "experiment_name": "PHASE_3_4_TEMPERATURE_ESCALATION_ABLATION",
        "timestamp": time.time(),
        "summary": summary,
        "tasks": task_results,
        "negative_controls": negative_control_results
    }

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "phase3_4_results.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print("\n" + "=" * 60)
    print("PHASE 3.4 ABLATION SUMMARY")
    print(f"Total Tasks Evaluated : {total_tasks}")
    print(f"Phase 3.4 Successes   : {successes}/{total_tasks} ({success_rate}%)")
    print(f"Phase 3.2 Baseline    : 2/5 (40.0%)")
    print(f"Delta                 : {summary['delta_percentage_points']} percentage points")
    print(f"Total Repeated Cand   : {total_repeated}")
    print(f"Negative Controls Pass: {all_nc_passed}")
    print(f"Results written to    : {out_path}")
    print("=" * 60 + "\n")

    return full_output


if __name__ == "__main__":
    run_phase3_4_experiment()
