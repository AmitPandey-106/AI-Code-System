import threading
import pytest
import app.engineering_loop as loop


def session(tmp_path, **options):
    (tmp_path / "mod.py").write_text("def f():\n    return 0\n")
    return loop.EngineeringSession("Fix f", str(tmp_path), "pytest", repo_index_enabled=False,
                                  memory_enabled=False, strategy_enabled=False, **options)


def test_invalid_and_unverified_transitions(tmp_path):
    s = session(tmp_path)
    with pytest.raises(ValueError, match="Invalid transition"):
        s._transition(loop.S.COMPLETED)
    s._transition(loop.S.INSPECTING)
    s._transition(loop.S.PLANNING)
    s._transition(loop.S.GENERATING)
    s._transition(loop.S.PATCH_PROPOSED)
    with pytest.raises(ValueError, match="Unvalidated"):
        s._transition(loop.S.AWAITING_APPROVAL)


def test_budget_is_bounded_and_observable(tmp_path, monkeypatch):
    s = session(tmp_path, max_attempts=2)
    monkeypatch.setattr(loop, "generate_raw", lambda p: "invalid")
    assert s.step() == loop.S.FAILED
    assert s.current_attempt == 2
    assert s.metrics["model_calls"] == 2
    assert any(e["to"] == loop.S.RETRY_PLANNING for e in s.events)
    assert s.step() == loop.S.FAILED


def test_exception_terminates_and_records_error(tmp_path, monkeypatch):
    s = session(tmp_path)
    def crash(prompt):
        raise RuntimeError("controlled failure")
    monkeypatch.setattr(loop, "generate_raw", crash)
    assert s.step() == loop.S.FAILED
    assert "controlled failure" in s.error_message


def test_cancel_waits_for_inference_and_concurrent_step_is_inert(tmp_path, monkeypatch):
    s = session(tmp_path)
    entered, release = threading.Event(), threading.Event()
    def slow(prompt):
        entered.set()
        assert release.wait(5)
        return "invalid"
    monkeypatch.setattr(loop, "generate_raw", slow)
    worker = threading.Thread(target=s.step)
    worker.start()
    assert entered.wait(5)
    assert s.step() == loop.S.GENERATING
    assert s.metrics["model_calls"] == 1
    s.cancel()
    assert s.state == loop.S.CANCELLING
    assert not s.approve()
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert s.state == loop.S.CANCELLED
    assert s.get_status()["functional_success"] is False
