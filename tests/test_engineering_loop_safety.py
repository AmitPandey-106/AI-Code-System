import os
import tempfile
import time
import threading
import pytest
from app.engineering_loop import EngineeringSession, EngineeringState, engineering_manager
from app.patch_engine import PatchEngine

# Mock generators
def mock_generate_raw_math(prompt: str) -> str:
    return """```diff
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,2 @@
 def calc(x):
-    return x - 1
+    return x + 1
```"""

@pytest.fixture
def repo_env():
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "data", "repo_index"), exist_ok=True)
        with open(os.path.join(td, "calculator.py"), "w", encoding="utf-8") as f:
            f.write("def calc(x):\n    return x - 1\n")
        with open(os.path.join(td, "test_calc.py"), "w", encoding="utf-8") as f:
            f.write("from calculator import calc\ndef test_calc():\n    assert calc(2) == 3\n")
        with open(os.path.join(td, "unrelated.py"), "w", encoding="utf-8") as f:
            f.write("# Unrelated user work\nVALUE = 42\n")
        yield td

def test_patch_cannot_apply_before_approval(repo_env, monkeypatch):
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_math)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()

    assert session.state == EngineeringState.AWAITING_APPROVAL
    # File must not be modified yet
    with open(os.path.join(repo_env, "calculator.py"), "r", encoding="utf-8") as f:
        assert "return x - 1" in f.read()

def test_subsequent_repair_requires_fresh_approval(repo_env, monkeypatch):
    import app.engineering_loop
    # Attempt 1 produces wrong patch, attempt 2 produces right patch
    def mock_gen(p):
        if "PREVIOUS TEST FAILURE" in p:
            return """```diff
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,2 @@
 def calc(x):
-    return x * 10
+    return x + 1
```"""
        return """```diff
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,2 @@
 def calc(x):
-    return x - 1
+    return x * 10
```"""
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_gen)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()
    assert session.state == EngineeringState.AWAITING_APPROVAL
    assert session.current_attempt == 1

    # Approve attempt 1
    assert session.approve() is True
    session.step()

    # Must be paused awaiting approval for attempt 2!
    assert session.state == EngineeringState.AWAITING_APPROVAL
    assert session.current_attempt == 2
    # Verify file has attempt 1's modification, NOT attempt 2's yet
    with open(os.path.join(repo_env, "calculator.py"), "r", encoding="utf-8") as f:
        assert "return x * 10" in f.read()

    # Now approve attempt 2
    assert session.approve() is True
    session.step()
    assert session.state == EngineeringState.COMPLETED
    with open(os.path.join(repo_env, "calculator.py"), "r", encoding="utf-8") as f:
        assert "return x + 1" in f.read()

def test_duplicate_approval_prevention(repo_env, monkeypatch):
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_math)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()
    assert session.state == EngineeringState.AWAITING_APPROVAL

    first_app = session.approve()
    second_app = session.approve()

    assert first_app is True
    assert second_app is False

def test_cancellation_terminates_safely(repo_env, monkeypatch):
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_math)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()
    assert session.state == EngineeringState.AWAITING_APPROVAL

    session.cancel()
    assert session.state == EngineeringState.CANCELLED

    # Calling approve or step should fail or do nothing
    assert session.approve() is False
    session.step()
    assert session.state == EngineeringState.CANCELLED

def test_failed_attempts_do_not_overwrite_unrelated_changes(repo_env, monkeypatch):
    bad_diff = """```diff
--- a/calculator.py
+++ b/calculator.py
@@ -99,2 +99,2 @@
 def non_existent():
-    return 0
+    return 1
--- a/unrelated.py
+++ b/unrelated.py
@@ -1,2 +1,2 @@
-# Unrelated user work
+# Modified
 VALUE = 42
```"""
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", lambda p: bad_diff)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()
    # Dry run should fail validation
    assert session.state == EngineeringState.FAILED

    # Verify unrelated.py was completely untouched
    with open(os.path.join(repo_env, "unrelated.py"), "r", encoding="utf-8") as f:
        assert "# Unrelated user work" in f.read()

def test_lock_not_held_during_model_cancel_responsive(repo_env, monkeypatch):
    """
    Verify session lock is NOT held during generate_raw, enabling responsive cancel().
    """
    import app.engineering_loop

    slow_event = threading.Event()
    entered_gen = threading.Event()

    def slow_gen(prompt):
        entered_gen.set()
        slow_event.wait(timeout=3.0)
        return mock_generate_raw_math(prompt)

    monkeypatch.setattr(app.engineering_loop, "generate_raw", slow_gen)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    t = threading.Thread(target=session.step)
    t.start()

    assert entered_gen.wait(timeout=10.0)

    # Calling cancel() while generate_raw is in progress must execute immediately (< 0.2s)
    start_c = time.time()
    session.cancel()
    cancel_duration = time.time() - start_c
    assert cancel_duration < 0.2, f"Cancel was blocked! Took {cancel_duration}s"

    slow_event.set()
    t.join(timeout=5.0)

    # Session must be safely CANCELLED
    assert session.state == EngineeringState.CANCELLED

def test_patch_hash_binding(repo_env, monkeypatch):
    """
    Verify approve rejects when expected patch hash does not match current patch.
    """
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_math)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()
    assert session.state == EngineeringState.AWAITING_APPROVAL

    # Approve with wrong hash should fail
    wrong_hash = "0" * 64
    assert session.approve(expected_patch_hash=wrong_hash) is False
    assert "PatchHashMismatch" in session.error_message
    assert session.state == EngineeringState.AWAITING_APPROVAL

    # Approve with correct hash should succeed
    assert session.approve(expected_patch_hash=session.current_patch_hash) is True
    assert session.state == EngineeringState.PATCH_APPLIED

def test_stale_source_detection_outside_hunk(repo_env, monkeypatch):
    """
    Verify that if a target file is modified on disk after proposal,
    approve() catches the stale source file and rejects without applying.
    """
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_math)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()
    assert session.state == EngineeringState.AWAITING_APPROVAL

    # Simulate user modifying calculator.py on disk outside the hunk context
    calc_path = os.path.join(repo_env, "calculator.py")
    with open(calc_path, "r", encoding="utf-8") as f:
        content = f.read()
    with open(calc_path, "w", encoding="utf-8") as f:
        f.write("# User added comment at top\n" + content)

    # Approve must detect stale source
    approved = session.approve()
    assert approved is False
    assert session.state == EngineeringState.FAILED
    assert "StaleSourceError" in session.error_message

def test_unhandled_exception_transitions_to_failed(repo_env, monkeypatch):
    """
    Verify exceptions during planning transition cleanly to FAILED rather than dangling in PLANNING.
    """
    import app.engineering_loop

    def crashing_gen(prompt):
        raise RuntimeError("Simulated network/GPU crash in model")

    monkeypatch.setattr(app.engineering_loop, "generate_raw", crashing_gen)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()

    assert session.state == EngineeringState.FAILED
    assert "Planning failed with exception" in session.error_message

def test_thread_safe_get_status(repo_env, monkeypatch):
    """
    Verify get_status returns an isolated snapshot.
    """
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_math)

    session = EngineeringSession("Fix calculator", repo_env, "pytest test_calc.py")
    session.step()

    status = session.get_status()
    assert status["state"] == EngineeringState.AWAITING_APPROVAL
    assert "history" in status
    assert len(status["history"]) > 0

    # Mutating returned history does not affect internal history
    status["history"].clear()
    assert len(session.history) > 0
