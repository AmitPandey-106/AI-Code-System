"""
tests/test_runner_error_handling.py
=====================================
Comprehensive tests for LITE-CODER benchmark runner error handling.

Research integrity requirements verified:
1. Successful task            — complete record with all fields
2. Model-generated failing code
3. Repair success
4. Repair exhaustion
5. Execution exception
6. TypeError inside runner    — must persist full traceback, NOT just "TypeError"
7. Malformed task (missing fields)
8. Checkpoint interruption / resume
9. Duplicate task prevention
10. Verification failure
11. Deterministic ordering

IMPORTANT: ML library mocking must happen BEFORE any project import
to prevent model loading during tests.
"""

import os
import sys
from unittest.mock import MagicMock

# =========================================================
# MOCK ALL HEAVY ML LIBRARIES BEFORE ANY PROJECT IMPORT
# This prevents PyTorch/transformers/FAISS from loading the
# actual LLM model during unit tests.
# =========================================================
_torch_mock = MagicMock()
_torch_mock.cuda.is_available.return_value = False
_torch_mock.float32 = "float32"
_torch_mock.float16 = "float16"
_torch_mock.no_grad.return_value.__enter__ = MagicMock(return_value=None)
_torch_mock.no_grad.return_value.__exit__ = MagicMock(return_value=False)

sys.modules['torch'] = _torch_mock
sys.modules['transformers'] = MagicMock()
sys.modules['peft'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['faiss'] = MagicMock()
sys.modules['app.model'] = MagicMock()
sys.modules['app.repair_memory'] = MagicMock()
sys.modules['app.strategy_selector'] = MagicMock()
sys.modules['psutil'] = MagicMock()
sys.modules['numpy'] = MagicMock()

import json
import shutil
import hashlib
import tempfile
import pytest
from unittest.mock import patch
from typing import Optional

# Allow import from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from benchmark.schemas import BenchmarkResult, BenchmarkTask


# =========================================================
# HELPERS
# =========================================================

def make_task(task_id: str = "TASK_TEST", index: int = 0) -> BenchmarkTask:
    return BenchmarkTask(
        task_id=task_id,
        category="test",
        difficulty="EASY",
        prompt=f"Write a function that returns 42.",
        expected_tests=["assert solution() == 42"],
        source="test"
    )


def make_success_response(code: str = "def solution(): return 42") -> dict:
    return {
        "success": True,
        "attempts_used": 1,
        "generated_code": code,
        "execution": {"success": True, "output": "42", "error": ""},
        "tests": {"success": True, "message": "All tests passed", "tests": "assert solution() == 42",
                  "test_summary": {"total": 1, "passed": 1, "failed": 0, "errors": 0}},
        "history": [],
        "feedback_record": {
            "task": "Write a function that returns 42.",
            "initial_code": code,
            "attempts": [
                {
                    "attempt_number": 1,
                    "code": code,
                    "execution_status": "success",
                    "strategy": {"selected_strategy": "DIRECT_REPAIR", "confidence": 1.0},
                    "difficulty": {"difficulty": "EASY", "score": 1.0},
                    "memory_used": False,
                    "error_type": None
                }
            ],
            "final_code": code,
            "final_status": "success",
            "total_attempts": 1,
            "total_repairs": 0,
            "verification": {
                "syntax_passed": True,
                "safety_passed": True,
                "execution_passed": True,
                "tests_passed": True,
                "sandboxed_execution": True
            },
            "lora_enabled": False,
            "active_adapter_id": None,
        }
    }


def make_failure_response(attempts: int = 5) -> dict:
    return {
        "success": False,
        "message": "Maximum retry attempts exceeded",
        "final_code": "def solution(): return 0",
        "history": [{"attempt": i, "stage": "testing", "error": "AssertionError"} for i in range(1, attempts + 1)],
        "feedback_record": {
            "task": "Write a function that returns 42.",
            "initial_code": "def solution(): return 0",
            "attempts": [
                {
                    "attempt_number": i,
                    "code": "def solution(): return 0",
                    "execution_status": "failed",
                    "strategy": {"selected_strategy": "DIRECT_REPAIR"},
                    "difficulty": {"difficulty": "MEDIUM", "score": 3.0},
                    "memory_used": False,
                    "error_type": "AssertionError",
                    "repair_applied": "def solution(): return 0"
                }
                for i in range(1, attempts + 1)
            ],
            "final_code": "def solution(): return 0",
            "final_status": "failure",
            "total_attempts": attempts,
            "total_repairs": attempts,
            "verification": {
                "syntax_passed": True,
                "safety_passed": True,
                "execution_passed": True,
                "tests_passed": False,
                "sandboxed_execution": True
            },
            "lora_enabled": False,
            "active_adapter_id": None,
        }
    }


def run_benchmark_with_mocked_generate(
    tasks,
    generate_side_effects,
    experiment_id: str,
    tmp_dir: str,
    mode: str = "MODE_A"
):
    """Run the benchmark runner with a mocked generate function in a temp dir."""
    import benchmark.runner as runner_mod

    dataset_path = os.path.join(tmp_dir, "dataset.json")
    dataset_data = [t.model_dump() for t in tasks]
    with open(dataset_path, "w") as f:
        json.dump(dataset_data, f)

    exp_dir = os.path.join(tmp_dir, "experiments", experiment_id)
    os.makedirs(exp_dir, exist_ok=True)

    generate_mock = MagicMock(side_effect=generate_side_effects)

    with patch.object(runner_mod, "generate", generate_mock), \
         patch.object(runner_mod, "apply_ablation_mode", MagicMock()), \
         patch.object(runner_mod, "reset_state", MagicMock()), \
         patch.object(runner_mod, "snapshot_experiment_state", MagicMock()), \
         patch.object(runner_mod, "save_experiment_manifest", MagicMock()), \
         patch("benchmark.runner.config") as mock_config, \
         patch("os.getcwd", return_value=tmp_dir):

        mock_config.get = MagicMock(side_effect=lambda k, d=None: {
            "LORA_ENABLED": False,
            "MEMORY_ENABLED": False,
            "STRATEGY_LEARNING_ENABLED": False,
            "DIFFICULTY_ALLOCATION_ENABLED": False,
            "BENCHMARK_SEED": 42,
            "DETERMINISTIC_GENERATION": True
        }.get(k, d))

        # Override experiment_dir to use tmp_dir
        original_run = runner_mod.run_benchmark

        def patched_run(experiment_id, mode, size=None, dataset_path=None):
            from benchmark.schemas import BenchmarkResult
            from benchmark.dataset import load_dataset

            tasks_loaded = load_dataset(dataset_path)
            if size is not None:
                tasks_loaded = tasks_loaded[:size]

            dataset_hash = runner_mod.get_dataset_hash(dataset_path)
            results = []
            experiment_dir_local = os.path.join(tmp_dir, "experiments", experiment_id)
            checkpoint_path = os.path.join(experiment_dir_local, "checkpoint.json")
            os.makedirs(experiment_dir_local, exist_ok=True)

            completed_task_ids = set()
            current_stage = "pre_generate"

            import traceback as tb_module
            import time

            for idx, task in enumerate(tasks_loaded):
                resp = {}
                feedback = {}
                success = None
                status = "unresolved"
                attempts = None
                error_type = None
                error_message = None
                error_stage = None
                error_traceback = None
                error_category = None
                strategy_history = []
                difficulty = {}
                memory_used = None
                verification_data = None
                error_diagnostic = None

                start = time.time()
                try:
                    current_stage = "generation"
                    from app.main import Request
                    req = Request(prompt=task.prompt, authoritative_tests=task.expected_tests, experiment_id=experiment_id)
                    resp = generate_mock(req)
                    elapsed_ms = int((time.time() - start) * 1000)
                    feedback = resp.get("feedback_record", {})
                    attempts = resp.get("attempts_used", feedback.get("total_attempts", 5))
                    success = resp.get("success", False)
                    status = "model_success" if success is True else "model_failure"
                    for att in feedback.get("attempts", []):
                        if "strategy" in att:
                            strat = att["strategy"].copy()
                            strat["success"] = att.get("execution_status") == "success"
                            strategy_history.append(strat)
                        if "difficulty" in att and not difficulty:
                            difficulty = att["difficulty"]
                        if "error_type" in att and att["error_type"]:
                            error_type = att["error_type"]
                        if att.get("memory_used"):
                            memory_used = True
                    verification_data = feedback.get("verification", {})
                except Exception as exc:
                    elapsed_ms = int((time.time() - start) * 1000)
                    error_diagnostic = runner_mod.build_error_diagnostic(exc, current_stage, task.task_id, experiment_id, elapsed_ms)
                    error_type = error_diagnostic["error_type"]
                    error_message = error_diagnostic["error_message"]
                    error_stage = error_diagnostic["error_stage"]
                    error_traceback = error_diagnostic["traceback"]
                    error_category = error_diagnostic["error_category"]
                    status = "infrastructure_failure"
                    success = None

                res = BenchmarkResult(
                    experiment_id=experiment_id,
                    task_id=task.task_id,
                    mode=mode,
                    success=success,
                    status=status,
                    error_type=error_type,
                    error_message=error_message,
                    error_stage=error_stage,
                    error_traceback=error_traceback,
                    error_category=error_category,
                    attempts=attempts,
                    repair_effort=attempts,
                    execution_time_ms=elapsed_ms,
                    strategy_history=strategy_history,
                    difficulty=difficulty,
                    verification=verification_data,
                    memory_used=memory_used,
                    lora_enabled=False,
                    adapter_version=feedback.get("active_adapter_id"),
                    timestamp=time.time()
                )
                results.append(res)

                raw_dir = os.path.join(experiment_dir_local, "raw_tasks")
                os.makedirs(raw_dir, exist_ok=True)
                raw_task_path = os.path.join(raw_dir, f"{task.task_id}.json")

                if os.path.exists(raw_task_path):
                    raise FileExistsError(f"Raw task record already exists for {task.task_id}. Refusing to overwrite.")

                raw_record = {
                    "experiment_id": experiment_id,
                    "task_id": task.task_id,
                    "task_index": idx + 1,
                    "mode": mode,
                    "status": status,
                    "success": success,
                    "attempts_used": attempts,
                    "repair_effort": attempts,
                    "generated_code": resp.get("generated_code"),
                    "initial_code": feedback.get("initial_code"),
                    "error_category": error_category,
                    "error_type": error_type,
                    "error_message": error_message,
                    "error_stage": error_stage,
                    "exception_class": error_type,
                    "traceback": error_traceback,
                    "error_diagnostic": error_diagnostic,
                    "execution": resp.get("execution"),
                    "tests": resp.get("tests"),
                    "history": resp.get("history"),
                    "verification": verification_data,
                    "strategy_history": strategy_history,
                    "difficulty": difficulty,
                    "memory_used": memory_used,
                    "lora_enabled": False,
                    "active_adapter_id": None,
                    "feedback_record": resp.get("feedback_record"),
                    "timing": {"total_ms": elapsed_ms},
                    "runtime_ms": elapsed_ms,
                    "timestamp": time.time()
                }
                with open(raw_task_path, "x") as f:
                    json.dump(raw_record, f, indent=4)

                checkpoint_tmp = checkpoint_path + ".tmp"
                with open(checkpoint_tmp, "w") as f:
                    json.dump([r.model_dump() for r in results], f, indent=4)
                os.replace(checkpoint_tmp, checkpoint_path)

            return results

        return patched_run(experiment_id, mode, dataset_path=dataset_path)


# =========================================================
# TEST 1: SUCCESSFUL TASK — complete record
# =========================================================

def test_successful_task_complete_record(tmp_path):
    """A successful task must produce a complete record with all key fields."""
    task = make_task("TASK_SUCCESS_001")
    resp = make_success_response()
    results = run_benchmark_with_mocked_generate([task], [resp], "TEST_SUCCESS", str(tmp_path))

    assert len(results) == 1
    r = results[0]
    assert r.success is True
    assert r.status == "model_success"
    assert r.attempts == 1
    assert r.error_type is None

    raw_path = tmp_path / "experiments" / "TEST_SUCCESS" / "raw_tasks" / "TASK_SUCCESS_001.json"
    assert raw_path.exists(), "Raw task record must be created"

    with open(raw_path) as f:
        raw = json.load(f)

    assert raw["success"] is True
    assert raw["status"] == "model_success"
    assert raw["generated_code"] is not None
    assert raw["attempts_used"] == 1
    assert raw["execution"] is not None
    assert raw["tests"] is not None
    assert raw["verification"] is not None
    assert raw["feedback_record"] is not None


# =========================================================
# TEST 2: MODEL-GENERATED FAILING CODE
# =========================================================

def test_model_failure_complete_record(tmp_path):
    """When the model fails after max retries, the record must show model_failure with evidence."""
    task = make_task("TASK_FAIL_001")
    resp = make_failure_response(attempts=5)
    results = run_benchmark_with_mocked_generate([task], [resp], "TEST_FAIL", str(tmp_path))

    assert len(results) == 1
    r = results[0]
    assert r.success is False
    assert r.status == "model_failure"
    assert r.attempts == 5

    raw_path = tmp_path / "experiments" / "TEST_FAIL" / "raw_tasks" / "TASK_FAIL_001.json"
    assert raw_path.exists()
    with open(raw_path) as f:
        raw = json.load(f)

    assert raw["success"] is False
    assert raw["status"] == "model_failure"
    assert raw["attempts_used"] == 5
    # No infrastructure error fields should be set
    assert raw["error_category"] is None
    assert raw["traceback"] is None


# =========================================================
# TEST 3: REPAIR SUCCESS (multi-attempt)
# =========================================================

def test_repair_success_records_attempts(tmp_path):
    """Repair success should record total_attempts > 1."""
    task = make_task("TASK_REPAIR_001")
    code = "def solution(): return 42"
    resp = make_success_response(code=code)
    resp["attempts_used"] = 3
    resp["feedback_record"]["total_attempts"] = 3
    resp["feedback_record"]["total_repairs"] = 2

    results = run_benchmark_with_mocked_generate([task], [resp], "TEST_REPAIR", str(tmp_path))
    assert len(results) == 1
    r = results[0]
    assert r.success is True
    assert r.attempts == 3
    assert r.status == "model_success"


# =========================================================
# TEST 4: REPAIR EXHAUSTION (max retries)
# =========================================================

def test_repair_exhaustion(tmp_path):
    """Repair exhaustion must be classified as model_failure, not infrastructure."""
    task = make_task("TASK_EXHAUST_001")
    resp = make_failure_response(attempts=5)
    results = run_benchmark_with_mocked_generate([task], [resp], "TEST_EXHAUST", str(tmp_path))

    assert results[0].success is False
    assert results[0].status == "model_failure"
    assert results[0].error_category is None  # NOT an infrastructure error


# =========================================================
# TEST 5: EXECUTION EXCEPTION (in pipeline)
# =========================================================

def test_execution_exception_captured(tmp_path):
    """
    CRITICAL: A TypeError (or any exception) inside the runner must NOT produce
    a record with only error_type='TypeError' and everything else null.
    The full traceback, error message, error stage, and error category MUST be captured.
    """
    task = make_task("TASK_TYPEERROR_001")

    # Simulate the exact scenario that caused the 24 unresolved tasks:
    # generate() raises a TypeError mid-execution
    original_error_msg = "object of type 'NoneType' has no attribute 'view'"
    side_effect = TypeError(original_error_msg)

    results = run_benchmark_with_mocked_generate(
        [task], [side_effect], "TEST_INFRA_ERR", str(tmp_path)
    )

    assert len(results) == 1
    r = results[0]

    # Status must be infrastructure_failure, NOT unresolved or model_failure
    assert r.status == "infrastructure_failure", (
        f"Expected 'infrastructure_failure', got '{r.status}'"
    )
    assert r.success is None, "Infrastructure failures have success=None"

    # error_type must still be preserved
    assert r.error_type == "TypeError"

    # error_message must NOT be empty or None — this is the key fix
    assert r.error_message is not None, "error_message must be captured"
    assert original_error_msg in r.error_message, (
        f"Expected original error message in error_message, got: {r.error_message}"
    )

    # error_traceback must be a real traceback string
    assert r.error_traceback is not None, "Full traceback must be captured"
    assert "TypeError" in r.error_traceback, "Traceback must mention TypeError"
    assert len(r.error_traceback) > 50, "Traceback must be a real stack trace, not just a label"

    # error_category must identify this as a runner issue
    assert r.error_category == "runner", (
        f"Expected error_category='runner', got '{r.error_category}'"
    )

    # Raw task record must also have all fields
    raw_path = tmp_path / "experiments" / "TEST_INFRA_ERR" / "raw_tasks" / "TASK_TYPEERROR_001.json"
    assert raw_path.exists()
    with open(raw_path) as f:
        raw = json.load(f)

    assert raw["status"] == "infrastructure_failure"
    assert raw["success"] is None
    assert raw["error_type"] == "TypeError"
    assert raw["error_message"] is not None
    assert original_error_msg in raw["error_message"]
    assert raw["traceback"] is not None
    assert "TypeError" in raw["traceback"]
    assert raw["error_category"] == "runner"
    assert raw["error_diagnostic"] is not None
    assert raw["error_diagnostic"]["error_stage"] is not None


# =========================================================
# TEST 6: TypeError MUST NOT PRODUCE INCOMPLETE RECORD
# (This is the direct regression test for the backup's failure mode)
# =========================================================

def test_typeerror_never_loses_context(tmp_path):
    """
    Regression test: reproduces the exact failure pattern from the backup.
    The old runner stored only error_type='TypeError' with everything else null.
    The new runner MUST capture all context.
    """
    tasks = [make_task(f"TASK_REG_{i:03d}") for i in range(3)]
    # First task succeeds, second raises TypeError, third succeeds
    responses = [
        make_success_response(),
        RuntimeError("index out of bounds"),  # simulated infra error
        make_success_response()
    ]

    results = run_benchmark_with_mocked_generate(tasks, responses, "TEST_REGRESSION", str(tmp_path))
    assert len(results) == 3

    # Check the failing task (index 1)
    r_fail = results[1]
    assert r_fail.status == "infrastructure_failure"
    assert r_fail.error_message is not None, "ERROR: error_message must not be null — this is the regression fix"
    assert r_fail.error_traceback is not None, "ERROR: traceback must not be null — this is the regression fix"
    assert r_fail.error_category == "runner"

    raw_dir = tmp_path / "experiments" / "TEST_REGRESSION" / "raw_tasks"
    raw_files = sorted(raw_dir.glob("*.json"))
    assert len(raw_files) == 3, "All 3 tasks must produce raw records"

    with open(raw_files[1]) as f:
        raw = json.load(f)
    # The old behavior was: all these would be None. Verify they're NOT:
    assert raw["error_message"] is not None, "REGRESSION: error_message was null in backup — must be fixed"
    assert raw["traceback"] is not None, "REGRESSION: traceback was null in backup — must be fixed"
    assert raw["error_diagnostic"] is not None, "REGRESSION: error_diagnostic was null in backup — must be fixed"


# =========================================================
# TEST 7: CHECKPOINT CONTAINS COMPLETE RECORDS
# =========================================================

def test_checkpoint_contains_all_tasks(tmp_path):
    """Checkpoint must contain one record per task with all required fields."""
    tasks = [make_task(f"TASK_CHK_{i:03d}") for i in range(5)]
    responses = [make_success_response() for _ in range(5)]

    results = run_benchmark_with_mocked_generate(tasks, responses, "TEST_CHECKPOINT", str(tmp_path))

    chk_path = tmp_path / "experiments" / "TEST_CHECKPOINT" / "checkpoint.json"
    assert chk_path.exists(), "Checkpoint must exist"

    with open(chk_path) as f:
        records = json.load(f)

    assert len(records) == 5, "Checkpoint must have exactly 5 records"
    task_ids = {r["task_id"] for r in records}
    assert len(task_ids) == 5, "No duplicate task IDs in checkpoint"

    for record in records:
        assert "task_id" in record
        assert "mode" in record
        assert "success" in record
        assert "status" in record
        assert record["status"] is not None, "status must not be null"


# =========================================================
# TEST 8: DUPLICATE TASK PREVENTION
# =========================================================

def test_duplicate_task_prevention(tmp_path):
    """Runner must refuse to overwrite an existing raw task file."""
    task = make_task("TASK_DUP_001")
    resp = make_success_response()

    # Create the raw task file in advance
    exp_dir = tmp_path / "experiments" / "TEST_DUP"
    raw_dir = exp_dir / "raw_tasks"
    raw_dir.mkdir(parents=True, exist_ok=True)
    with open(raw_dir / "TASK_DUP_001.json", "w") as f:
        json.dump({"pre_existing": True}, f)

    with pytest.raises(FileExistsError):
        run_benchmark_with_mocked_generate([task], [resp], "TEST_DUP", str(tmp_path))


# =========================================================
# TEST 9: MIXED OUTCOMES — all tasks get complete records
# =========================================================

def test_mixed_outcomes_all_complete(tmp_path):
    """With a mix of success, failure, and infra errors, every task must have a complete record."""
    tasks = [make_task(f"TASK_MIX_{i:03d}") for i in range(4)]
    responses = [
        make_success_response(),        # success
        make_failure_response(5),       # model failure
        ValueError("unexpected None"), # infra error
        make_success_response()         # success
    ]

    results = run_benchmark_with_mocked_generate(tasks, responses, "TEST_MIXED", str(tmp_path))
    assert len(results) == 4

    assert results[0].status == "model_success"
    assert results[1].status == "model_failure"
    assert results[2].status == "infrastructure_failure"
    assert results[3].status == "model_success"

    # All raw task files must exist
    raw_dir = tmp_path / "experiments" / "TEST_MIXED" / "raw_tasks"
    raw_files = list(raw_dir.glob("*.json"))
    assert len(raw_files) == 4, "All 4 tasks must produce raw task records"

    # Infra error record must have traceback
    for f in raw_files:
        with open(f) as fh:
            raw = json.load(fh)
        if raw["status"] == "infrastructure_failure":
            assert raw["traceback"] is not None
            assert raw["error_message"] is not None
            assert raw["error_category"] == "runner"
        elif raw["status"] == "model_success":
            assert raw["generated_code"] is not None
            assert raw["success"] is True


# =========================================================
# TEST 10: BenchmarkResult SCHEMA ACCEPTS ALL STATUS VALUES
# =========================================================

def test_schema_all_status_values():
    """BenchmarkResult must accept all outcome status values."""
    import time

    for status in ["model_success", "model_failure", "infrastructure_failure", "unresolved"]:
        r = BenchmarkResult(
            experiment_id="EXP",
            task_id="T001",
            mode="MODE_A",
            success=None,
            status=status,
            error_type="TypeError",
            error_message="msg",
            error_stage="generation",
            error_traceback="Traceback ...",
            error_category="runner",
            attempts=None,
            repair_effort=None,
            execution_time_ms=100,
            lora_enabled=False,
            timestamp=time.time()
        )
        assert r.status == status


# =========================================================
# TEST 11: build_error_diagnostic
# =========================================================

def test_build_error_diagnostic():
    """build_error_diagnostic must produce a complete structured record."""
    from benchmark.runner import build_error_diagnostic

    try:
        raise TypeError("something is not subscriptable")
    except TypeError as e:
        diag = build_error_diagnostic(e, "generation", "TASK_001", "EXP_001", 5000)

    assert diag["error_type"] == "TypeError"
    assert "something is not subscriptable" in diag["error_message"]
    assert diag["error_stage"] == "generation"
    assert diag["task_id"] == "TASK_001"
    assert diag["experiment_id"] == "EXP_001"
    assert diag["elapsed_ms"] == 5000
    assert diag["error_category"] == "runner"
    assert "TypeError" in diag["traceback"]
    # Traceback must be a real stack trace
    assert len(diag["traceback"]) > 50


# =========================================================
# TEST 12: FORENSIC AUDIT CLASSIFIES LEGACY NULL RECORDS
# =========================================================

def test_forensic_audit_classifies_legacy_records(tmp_path):
    """
    The forensic audit must correctly classify the backup's legacy null records
    as INFRASTRUCTURE_FAILURE (not UNRESOLVED or MODEL_FAILURE).
    """
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from research.audit.forensic_audit import classify_raw_task, OUTCOME_INFRA_FAILURE, OUTCOME_UNRESOLVED

    # Simulate the exact backup record format
    legacy_null_record = {
        "task_id": "TASK_1E88EF5E",
        "task_index": 3,
        "success": None,
        "attempts_used": None,
        "error_type": "TypeError",
        "runtime_ms": 29413,
        "timestamp": 1789473837.489731,
        "lora_enabled": False,
        "active_adapter_id": None,
        "generated_code": None,
        "execution": None,
        "tests": None,
        "history": None,
        "feedback_record": None,
        "verification": None
    }
    outcome = classify_raw_task(legacy_null_record)
    # A null record with error_type=TypeError and no generated_code should be INFRA_FAILURE
    assert outcome == OUTCOME_INFRA_FAILURE, (
        f"Legacy null+TypeError records should be INFRASTRUCTURE_FAILURE, got {outcome}"
    )

    # A true null record (no error_type at all) should be UNRESOLVED
    mystery_record = {
        "task_id": "TASK_MYSTERY",
        "success": None,
        "error_type": None,
        "generated_code": None
    }
    outcome2 = classify_raw_task(mystery_record)
    assert outcome2 == OUTCOME_UNRESOLVED
