import threading
import time
from pathlib import Path
import app.engineering_loop as loop
from test_phase8_1_patches import patch


def setup(tmp_path, **options):
    (tmp_path / "mod.py").write_bytes(b"def f():\r\n    return 0\r\n")
    (tmp_path / "test_mod.py").write_text("from mod import f\ndef test_f():\n    assert f() == 1\n")
    return loop.EngineeringSession("Fix f", str(tmp_path), "pytest test_mod.py", repo_index_enabled=False,
                                  memory_enabled=False, strategy_enabled=False, **options)


def test_malformed_retry_then_native_repair(tmp_path, monkeypatch):
    s = setup(tmp_path)
    responses = iter(["malformed", patch()])
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: next(responses))
    assert s.step() == loop.S.AWAITING_APPROVAL
    assert s.current_attempt == 2
    assert s.approve(s.current_patch_hash)
    assert s.step() == loop.S.COMPLETED, s.get_status()
    assert s.verification_results["success"] and s.current_test_results["success"]
    assert (tmp_path / "mod.py").read_bytes() == b"def f():\r\n    return 1\r\n"


def test_test_failure_restored_before_new_approval(tmp_path, monkeypatch):
    s = setup(tmp_path)
    prompts = []
    def generate(prompt):
        prompts.append(prompt)
        return patch(new="return 2") if len(prompts) == 1 else patch()
    monkeypatch.setattr(loop, "generate_raw", generate)
    s.step(); assert s.approve()
    assert s.step() == loop.S.AWAITING_APPROVAL
    assert s.rollback_result["success"]
    assert (tmp_path / "mod.py").read_bytes() == b"def f():\r\n    return 0\r\n"
    assert "STRUCTURED FAILURE CONTEXT" in prompts[1] and "assert 2 == 1" in prompts[1]
    assert s.approve() and s.step() == loop.S.COMPLETED


def test_cancellation_during_tests_restores_patch(tmp_path, monkeypatch):
    marker = tmp_path.parent / (tmp_path.name + "-running")
    s = setup(tmp_path)
    (tmp_path / "test_mod.py").write_text(f"import time\nfrom pathlib import Path\ndef test_wait():\n    Path({str(marker)!r}).write_text('running')\n    time.sleep(30)\n")
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch())
    s.step(); assert s.approve()
    worker = threading.Thread(target=s.step)
    worker.start()
    deadline = time.monotonic() + 10
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert marker.exists()
    s.cancel()
    worker.join(10)
    assert not worker.is_alive()
    assert s.state == loop.S.CANCELLED
    assert s.rollback_result["success"]
    assert (tmp_path / "mod.py").read_bytes() == b"def f():\r\n    return 0\r\n"


def test_timeout_is_not_success_and_restores_patch(tmp_path, monkeypatch):
    s = setup(tmp_path, test_timeout=0.2)
    (tmp_path / "test_mod.py").write_text("import time\ndef test_wait(): time.sleep(10)\n")
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch())
    s.step(); assert s.approve()
    assert s.step() == loop.S.FAILED
    assert s.failure_category == "timeout" and s.current_test_results["timeout"]
    assert s.rollback_result["success"]


def test_stale_source_and_traversal_fail_without_overwriting(tmp_path, monkeypatch):
    s = setup(tmp_path)
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch())
    s.step()
    (tmp_path / "mod.py").write_bytes(b"# external user edit\n")
    assert not s.approve()
    assert s.state == loop.S.FAILED and s.failure_category == "stale_source"
    assert (tmp_path / "mod.py").read_bytes() == b"# external user edit\n"
    unsafe = setup(tmp_path)
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch("../outside.py"))
    assert unsafe.step() == loop.S.FAILED
    assert unsafe.failure_category == "policy_rejection"


def test_concurrent_same_root_cannot_mutate_during_transaction(tmp_path, monkeypatch):
    a = setup(tmp_path)
    b = loop.EngineeringSession("Fix f", str(tmp_path), "pytest test_mod.py", repo_index_enabled=False,
                                memory_enabled=False, strategy_enabled=False)
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch())
    a.step(); b.step()
    assert a.approve()
    assert not b.approve() and b.failure_category == "concurrent_session"
    a.cancel()
    assert a.rollback_result["success"]


def test_created_files_and_directories_are_removed_on_failure(tmp_path, monkeypatch):
    s = setup(tmp_path, max_attempts=1)
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch("new/sub/module.py", "", "VALUE = 1"))
    s.step(); assert s.approve()
    assert (tmp_path / "new/sub/module.py").exists()
    assert s.step() == loop.S.FAILED
    assert s.rollback_result["success"]
    assert not (tmp_path / "new").exists()


def test_rollback_failure_is_explicit_and_preserves_external_work(tmp_path, monkeypatch):
    s = setup(tmp_path, max_attempts=1)
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch())
    s.step(); assert s.approve()
    (tmp_path / "mod.py").write_bytes(b"# concurrent external work\n")
    s.cancel()
    assert s.state == loop.S.FAILED
    assert s.failure_category == "rollback_failure"
    assert not s.get_status()["functional_success"]
    assert s.rollback_result["errors"]
    assert (tmp_path / "mod.py").read_bytes() == b"# concurrent external work\n"
