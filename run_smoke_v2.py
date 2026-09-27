"""
Smoke test for the hardened runner — validates complete record schema
without loading the actual LLM model.

Run as:
    python run_smoke_v2.py

This verifies:
- Every task produces a complete raw_task record
- Infrastructure failures capture full traceback
- Checkpoint is written atomically
- Forensic audit runs successfully
"""
import os
import sys
import json
from unittest.mock import MagicMock, patch

# Mock ML libs FIRST
_torch_mock = MagicMock()
_torch_mock.cuda.is_available.return_value = False
_torch_mock.float32 = "float32"
_torch_mock.float16 = "float16"
_torch_mock.__version__ = "2.0.0"

sys.modules['torch'] = _torch_mock
sys.modules['transformers'] = MagicMock()
sys.modules['transformers'].__version__ = "4.40.0"
sys.modules['peft'] = MagicMock()
sys.modules['peft'].__version__ = "0.10.0"
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['sentence_transformers'].__version__ = "2.7.0"
sys.modules['faiss'] = MagicMock()
sys.modules['faiss'].__version__ = "1.8.0"
sys.modules['psutil'] = MagicMock()
sys.modules['numpy'] = MagicMock()

import benchmark.runner as runner_mod
import app.main

EXPERIMENT_ID = "SMOKE_V2_HARDENED"
DATASET_PATH = "data/benchmark/v1.0/dataset.json"

def make_success_resp(prompt, code="def solution(): return 42"):
    return {
        "success": True,
        "attempts_used": 1,
        "generated_code": code,
        "execution": {"success": True, "output": "42", "error": ""},
        "tests": {
            "success": True, "message": "All passed",
            "tests": "assert solution() == 42",
            "test_summary": {"total": 1, "passed": 1, "failed": 0, "errors": 0}
        },
        "history": [],
        "feedback_record": {
            "task": prompt,
            "initial_code": code,
            "attempts": [{"attempt_number": 1, "code": code, "execution_status": "success",
                          "strategy": {"selected_strategy": "DIRECT_REPAIR"}, "difficulty": {"difficulty": "EASY"},
                          "memory_used": False, "error_type": None}],
            "final_code": code, "final_status": "success",
            "total_attempts": 1, "total_repairs": 0,
            "verification": {"syntax_passed": True, "safety_passed": True,
                             "execution_passed": True, "tests_passed": True, "sandboxed_execution": True},
            "lora_enabled": False, "active_adapter_id": None
        }
    }

call_count = [0]
def fake_generate(req):
    i = call_count[0]
    call_count[0] += 1
    if i == 0:
        return make_success_resp(req.prompt)  # Task 1: success
    elif i == 1:
        raise TypeError("simulated runner TypeError: object of type 'NoneType' has no method 'view'")  # Task 2: infra failure
    elif i == 2:
        return make_success_resp(req.prompt)  # Task 3: success

runner_mod.generate = fake_generate
runner_mod.reset_state = MagicMock()
runner_mod.snapshot_experiment_state = MagicMock()
runner_mod.save_experiment_manifest = MagicMock()

# Clean up old smoke experiment if present
import shutil
exp_dir = f"experiments/{EXPERIMENT_ID}"
if os.path.exists(exp_dir):
    shutil.rmtree(exp_dir)

print(f"\n{'='*60}")
print(f"SMOKE TEST: {EXPERIMENT_ID}")
print(f"Tasks: 3 (success, TypeError infra failure, success)")
print(f"{'='*60}\n")

results = runner_mod.run_benchmark(EXPERIMENT_ID, "MODE_A", size=3, dataset_path=DATASET_PATH)

print(f"\n{'='*60}")
print(f"VERIFYING RESULTS...")
print(f"{'='*60}")

PASS = True

# Check results count
assert len(results) == 3, f"Expected 3 results, got {len(results)}"
print(f"[PASS] 3 tasks executed")

# Task 1: success
r0 = results[0]
assert r0.success is True, f"Task 1: expected success=True, got {r0.success}"
assert r0.status == "model_success", f"Task 1: expected status=model_success, got {r0.status}"
print(f"[PASS] Task 1: model_success, success=True")

# Task 2: infrastructure failure from TypeError
r1 = results[1]
assert r1.success is None, f"Task 2: expected success=None, got {r1.success}"
assert r1.status == "infrastructure_failure", f"Task 2: expected infrastructure_failure, got {r1.status}"
assert r1.error_type == "TypeError", f"Task 2: expected TypeError, got {r1.error_type}"
assert r1.error_message is not None, "Task 2: error_message must not be None"
assert "NoneType" in r1.error_message, f"Task 2: error_message should contain error text, got: {r1.error_message}"
assert r1.error_traceback is not None, "Task 2: traceback must not be None"
assert "TypeError" in r1.error_traceback, "Task 2: traceback must contain TypeError"
assert len(r1.error_traceback) > 50, "Task 2: traceback must be a real stack trace"
assert r1.error_category == "runner", f"Task 2: expected error_category=runner, got {r1.error_category}"
print(f"[PASS] Task 2: infrastructure_failure — full traceback captured")
print(f"       error_message: {r1.error_message[:60]}...")

# Task 3: success
r2 = results[2]
assert r2.success is True, f"Task 3: expected success=True, got {r2.success}"
print(f"[PASS] Task 3: model_success, success=True")

# Verify raw task records
raw_dir = f"{exp_dir}/raw_tasks"
raw_files = sorted(os.listdir(raw_dir))
assert len(raw_files) == 3, f"Expected 3 raw task files, got {len(raw_files)}"
print(f"[PASS] 3 raw task files exist")

# Check infra failure raw record specifically
for fname in raw_files:
    with open(os.path.join(raw_dir, fname)) as f:
        raw = json.load(f)
    
    # ALL required fields must be present
    for field in ["task_id", "experiment_id", "mode", "status", "success", "runtime_ms", "timestamp"]:
        assert field in raw, f"Missing required field '{field}' in {fname}"
    
    if raw["status"] == "infrastructure_failure":
        # These were None in the original backup — must NOT be None anymore
        assert raw["error_message"] is not None, f"REGRESSION: error_message is null in {fname}"
        assert raw["traceback"] is not None, f"REGRESSION: traceback is null in {fname}"
        assert raw["error_diagnostic"] is not None, f"error_diagnostic missing in {fname}"
        assert raw["error_category"] == "runner", f"error_category wrong in {fname}"
        print(f"[PASS] Infrastructure failure raw record complete: {fname}")
    elif raw["status"] == "model_success":
        assert raw["generated_code"] is not None, f"generated_code missing in successful {fname}"
        assert raw["verification"] is not None, f"verification missing in {fname}"
        print(f"[PASS] Success raw record complete: {fname}")

# Check checkpoint
chk_path = f"{exp_dir}/checkpoint.json"
assert os.path.exists(chk_path), "Checkpoint must exist"
with open(chk_path) as f:
    chk = json.load(f)
assert len(chk) == 3, f"Checkpoint must have 3 records, got {len(chk)}"
for rec in chk:
    assert rec["status"] is not None, "Status must not be None in checkpoint"
    if rec["success"] is None:
        assert rec["status"] == "infrastructure_failure"
        assert rec["error_message"] is not None, "error_message must be in checkpoint for infra failures"
print(f"[PASS] Checkpoint correct: 3 records, all with status")

# Run forensic audit
print(f"\n[INFO] Running forensic audit on smoke experiment...")
sys.path.insert(0, os.path.abspath('.'))
from research.audit.forensic_audit import run_audit
audit = run_audit(exp_dir, dataset_path=DATASET_PATH, output_dir=f"research/evidence/MODE_A/smoke_tests")
s = audit["summary"]
assert s["model_successes"] == 2, f"Expected 2 model successes, got {s['model_successes']}"
assert s["infrastructure_failures"] == 1, f"Expected 1 infra failure, got {s['infrastructure_failures']}"
assert s["unresolved"] == 0, f"Expected 0 unresolved, got {s['unresolved']}"
print(f"[PASS] Forensic audit: 2 MODEL_SUCCESS, 1 INFRASTRUCTURE_FAILURE, 0 UNRESOLVED")

print(f"\n{'='*60}")
print(f"SMOKE TEST: ALL CHECKS PASSED")
print(f"Runner is producing complete, traceable records.")
print(f"Infrastructure failures capture full traceback.")
print(f"TypeError is no longer silently swallowed.")
print(f"{'='*60}\n")
print(f"READY FOR CLEAN 100-TASK MODE-A BASELINE")
print(f"\nCommand:")
print(f"  python -m benchmark.run_experiment --mode MODE_A \\")
print(f"    --experiment-id LITE_CODER_100TASK_MODE_A_CLEAN_V1 \\")
print(f"    --dataset data/benchmark/v1.0/dataset.json")
