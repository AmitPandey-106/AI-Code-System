"""Control-plane tests only: no models are loaded or generated."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts/phase8_2_arm.py"
spec = importlib.util.spec_from_file_location("phase82_adapter_test", ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_plan_digest_binds_all_controls():
    plan = {"task_id": "task_01_router_slug_param", "max_model_calls": 2}
    plan["plan_sha256"] = adapter.plan_digest(plan)
    assert adapter.check_approval(plan, plan["plan_sha256"]) == plan["plan_sha256"]
    plan["max_model_calls"] = 3
    with pytest.raises(ValueError, match="explicit approval"):
        adapter.check_approval(plan, plan["plan_sha256"])


@pytest.mark.parametrize("supplied", [None, "", "0" * 64])
def test_approval_is_never_inferred(supplied):
    plan = {"task_id": "task_01_router_slug_param"}
    plan["plan_sha256"] = adapter.plan_digest(plan)
    with pytest.raises(ValueError, match="explicit approval"):
        adapter.check_approval(plan, supplied)


def test_execution_without_approval_stops_before_output_or_import(tmp_path):
    plan = {"task_id": "task_01_router_slug_param"}
    plan["plan_sha256"] = adapter.plan_digest(plan)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    output = tmp_path / "must_not_exist"
    result = subprocess.run([sys.executable, str(ADAPTER), "--run", "--plan", str(plan_path),
        "--arm", "A", "--source", str(tmp_path / "missing_source"), "--output", str(output)],
        capture_output=True, text=True, timeout=10, shell=False)
    assert result.returncode != 0
    assert "explicit approval" in result.stderr
    assert not output.exists()


def test_adapter_drift_rejects_a_matching_plan_digest(tmp_path):
    plan = {"task_id": "task_01_router_slug_param", "adapter_sha256": "0" * 64}
    plan["plan_sha256"] = adapter.plan_digest(plan)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    output = tmp_path / "must_not_exist"
    result = subprocess.run([sys.executable, str(ADAPTER), "--run", "--plan", str(plan_path),
        "--approved-plan-sha256", plan["plan_sha256"], "--arm", "A", "--source", str(tmp_path),
        "--output", str(output)], capture_output=True, text=True, timeout=10, shell=False)
    assert result.returncode != 0
    assert "adapter changed" in result.stderr
    assert not output.exists()


def test_environment_failure_is_not_counted_as_failed_repair():
    status = {"state": "failed", "failure_category": "model_generation_failure"}
    assert adapter.classify_outcome(status, {"passed": False, "exit_code": 1}, False, False, True, False) == "inconclusive_execution_error"


def test_passing_oracle_is_required_and_review_rejection_is_inconclusive():
    status = {"state": "completed"}
    assert adapter.classify_outcome(status, {"passed": False, "exit_code": 1}, True, False, True, True) == "functional_failure"
    assert adapter.classify_outcome(status, {"passed": True, "exit_code": 0}, True, False, True, True) == "functional_success"
    assert adapter.classify_outcome(status, {"passed": True, "exit_code": 0}, False, True, True, True) == "inconclusive_review_rejected"


def test_successful_rollback_is_not_a_functional_repair():
    status = {"state": "failed", "failure_category": "test_failure", "rollback": {"success": True}}
    assert adapter.classify_outcome(status, {"passed": False, "exit_code": 1}, True, False, True, False) == "functional_failure"


def test_existing_evidence_is_never_overwritten(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    record = output / "run_result.json"
    original = b'{"previous":"untouched"}\n'
    record.write_bytes(original)
    result = subprocess.run([sys.executable, str(ADAPTER), "--source", str(tmp_path),
                             "--output", str(output)], capture_output=True, text=True, timeout=10, shell=False)
    assert result.returncode != 0 and "refusing to overwrite" in result.stderr
    assert record.read_bytes() == original
    assert sorted(p.name for p in output.iterdir()) == ["run_result.json"]


def test_native_test_executable_uses_the_same_interpreter_directory(monkeypatch):
    import os
    from unittest.mock import patch
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    with patch.dict(os.environ, {"PATH": "ambient-uncontrolled-path"}, clear=True):
        adapter.configure_environment()
        assert os.environ["PATH"].split(os.pathsep)[0] == str(Path(sys.executable).parent)
        assert os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
        assert os.environ["PYTEST_ADDOPTS"] == "-p no:cacheprovider"
