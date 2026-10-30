import os
import tempfile
import pytest
import threading
from app.engineering_loop import EngineeringSession, EngineeringState, engineering_manager

@pytest.fixture
def repo_env():
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "math_app.py"), "w", encoding="utf-8") as f:
            f.write("def compute(x):\n    return x - 1\n")

        with open(os.path.join(td, "test_app.py"), "w", encoding="utf-8") as f:
            f.write("from math_app import compute\ndef test_compute():\n    assert compute(5) == 10\n")

        with open(os.path.join(td, "test_pass.py"), "w", encoding="utf-8") as f:
            f.write("from math_app import compute\ndef test_pass():\n    assert compute(5) == 10\n")

        yield td

def test_syntax_retry_recovers_to_success(repo_env, monkeypatch):
    """
    Attempt 1: Outputs unparseable garbage text.
    Attempt 2: Self-corrects to valid SEARCH/REPLACE block.
    Verifies that the loop retried within the 3-attempt budget and succeeded.
    """
    import app.engineering_loop

    call_count = 0
    def mock_gen(prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "I am confused. Here is some invalid code: ```python foo() ```"
        else:
            return """
I will now use the correct SEARCH/REPLACE block format:
FILE: math_app.py
<<<<<<< SEARCH
def compute(x):
    return x - 1
=======
def compute(x):
    return x * 2
>>>>>>> REPLACE
"""

    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_gen)

    session = EngineeringSession("Fix compute so compute(5) == 10", repo_env, "pytest test_pass.py")
    session.step()

    # Should have retried and reached AWAITING_APPROVAL on attempt 2
    assert session.state == EngineeringState.AWAITING_APPROVAL
    assert session.current_attempt == 2
    assert session.last_syntax_error == ""

    # Approve and complete
    approved = session.approve()
    assert approved is True
    session.step()

    assert session.state == EngineeringState.COMPLETED
    with open(os.path.join(repo_env, "math_app.py"), "r", encoding="utf-8") as f:
        assert "return x * 2" in f.read()

def test_patch_validation_retry_recovers_to_success(repo_env, monkeypatch):
    """
    Attempt 1: Outputs a SEARCH block that doesn't match the target file.
    Attempt 2: Fixes the SEARCH block to match exactly.
    """
    import app.engineering_loop

    call_count = 0
    def mock_gen(prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return """
FILE: math_app.py
<<<<<<< SEARCH
def non_existent_function():
    pass
=======
def compute(x):
    return x * 2
>>>>>>> REPLACE
"""
        else:
            assert "PREVIOUS PATCH VALIDATION ERROR" in prompt
            return """
FILE: math_app.py
<<<<<<< SEARCH
def compute(x):
    return x - 1
=======
def compute(x):
    return x * 2
>>>>>>> REPLACE
"""

    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_gen)

    session = EngineeringSession("Fix compute", repo_env, "pytest test_pass.py")
    session.step()

    assert session.state == EngineeringState.AWAITING_APPROVAL
    assert session.current_attempt == 2

    assert session.approve() is True
    session.step()
    assert session.state == EngineeringState.COMPLETED

def test_syntax_retry_budget_exhaustion(repo_env, monkeypatch):
    """
    Model outputs malformed syntax on all 3 attempts.
    Loop must halt safely with FAILED and failure_category == 'malformed_patch_syntax'.
    """
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", lambda p: "No patch here!")

    session = EngineeringSession("Fix compute", repo_env, "pytest test_pass.py")
    session.step()

    assert session.state == EngineeringState.FAILED
    assert session.current_attempt == 3
    assert session.failure_category == "malformed_patch_syntax"
    assert "Budget exhausted" in session.error_message

def test_cancellation_during_syntax_retries(repo_env, monkeypatch):
    """
    Cancellation during retries transitions cleanly to CANCELLED.
    """
    import app.engineering_loop

    def slow_gen(prompt):
        session.cancel()
        return "Invalid patch"

    session = EngineeringSession("Fix compute", repo_env, "pytest test_pass.py")
    monkeypatch.setattr(app.engineering_loop, "generate_raw", slow_gen)

    session.step()
    assert session.state == EngineeringState.CANCELLED
    assert session.failure_category == "cancelled"

def test_explicit_policy_event_on_unapproved_command(repo_env, monkeypatch):
    """
    Verifies that when an unapproved command is passed, the test runner intercepts it,
    records an explicit policy_event in the session, sets failure_category to policy_rejection,
    and proves the unauthorized command was NEVER executed.
    """
    import app.engineering_loop

    valid_patch = """
FILE: math_app.py
<<<<<<< SEARCH
def compute(x):
    return x - 1
=======
def compute(x):
    return x * 2
>>>>>>> REPLACE
"""
    monkeypatch.setattr(app.engineering_loop, "generate_raw", lambda p: valid_patch)

    marker_file = os.path.join(repo_env, "unauthorized_executed.txt")
    unsafe_command = f"python -c \"import open; open('{marker_file}', 'w').write('HACK')\""

    session = EngineeringSession("Fix compute", repo_env, unsafe_command)
    session.step()

    assert session.state == EngineeringState.AWAITING_APPROVAL
    # User approves patch
    assert session.approve() is True

    # Step to testing
    session.step()

    assert session.state == EngineeringState.FAILED
    assert session.failure_category == "policy_rejection"
    assert session.policy_event is not None
    assert session.policy_event["event"] == "unapproved_command_rejected"
    assert session.policy_event["status"] == "unapproved_command"
    assert "SecurityViolation" in session.error_message

    # Verify unauthorized command NEVER executed
    assert not os.path.exists(marker_file)

def test_stale_source_hash_records_stale_source_failure(repo_env, monkeypatch):
    """
    Verifies that approving a proposal when target file was modified on disk
    sets failure_category to stale_source.
    """
    import app.engineering_loop
    valid_patch = """
FILE: math_app.py
<<<<<<< SEARCH
def compute(x):
    return x - 1
=======
def compute(x):
    return x * 2
>>>>>>> REPLACE
"""
    monkeypatch.setattr(app.engineering_loop, "generate_raw", lambda p: valid_patch)

    session = EngineeringSession("Fix compute", repo_env, "pytest test_pass.py")
    session.step()
    assert session.state == EngineeringState.AWAITING_APPROVAL

    # Modify file on disk behind the orchestrator's back
    calc_path = os.path.join(repo_env, "math_app.py")
    with open(calc_path, "w", encoding="utf-8") as f:
        f.write("# External edit\ndef compute(x):\n    return x - 1\n")

    approved = session.approve()
    assert approved is False
    assert session.state == EngineeringState.FAILED
    assert session.failure_category == "stale_source"
    assert "StaleSourceError" in session.error_message
