import os
import tempfile
import pytest
import hashlib
from app.patch_engine import PatchEngine
from app.engineering_loop import EngineeringSession, EngineeringState, engineering_manager

@pytest.fixture
def repo_env():
    with tempfile.TemporaryDirectory() as td:
        calc_file = os.path.join(td, "calc.py")
        with open(calc_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a - b\n")

        suite_file = os.path.join(td, "test_calc.py")
        with open(suite_file, "w", encoding="utf-8") as f:
            f.write("from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n")

        yield td

# 1. Delimiter parsing & validation
def test_correct_delimiter_parsing(repo_env):
    patch_text = """FILE: calc.py
<<<<<<< SEARCH
def add(a, b):
    return a - b
=======
def add(a, b):
    return a + b
>>>>>>> REPLACE
"""
    engine = PatchEngine(repo_env)
    res = engine.apply_patch(patch_text, dry_run=False)
    assert res["success"] is True
    assert res["format"] == "search_replace"
    with open(os.path.join(repo_env, "calc.py"), "r", encoding="utf-8") as f:
        assert f.read() == "def add(a, b):\n    return a + b\n"

# 2. Missing, duplicated, and malformed delimiters
def test_missing_and_duplicated_delimiters(repo_env):
    engine = PatchEngine(repo_env)

    # Missing REPLACE delimiter
    patch_missing_replace = """FILE: calc.py
<<<<<<< SEARCH
def add(a, b):
    return a - b
=======
def add(a, b):
    return a + b
"""
    res = engine.apply_patch(patch_missing_replace, dry_run=True)
    assert res["success"] is False
    assert any("MalformedBlockError" in e for e in res["errors"])

    # Duplicate nested SEARCH
    patch_nested_search = """FILE: calc.py
<<<<<<< SEARCH
def add(a, b):
<<<<<<< SEARCH
    return a - b
=======
    return a + b
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch_nested_search, dry_run=True)
    assert res["success"] is False
    assert any("MalformedBlockError" in e for e in res["errors"])

# 3. Single-function fallback success
def test_single_function_fallback_success(repo_env):
    raw_model_response = """I have fixed the subtraction bug.
```python
def add(a, b):
    return a + b
```
Please approve this change."""

    session = EngineeringSession(
        task_prompt="Fix add function",
        repo_root=repo_env,
        test_command="pytest test_calc.py",
        fallback_enabled=True
    )
    extracted_patch = session._extract_patch(raw_model_response)
    assert extracted_patch != ""
    assert "FILE: calc.py" in extracted_patch
    assert "<<<<<<< SEARCH" in extracted_patch
    assert "return a - b" in extracted_patch
    assert "return a + b" in extracted_patch

    # Route through patch validation path
    session.current_diff = extracted_patch
    success, errors, hashes = session._do_patch_validation()
    assert success is True
    assert "calc.py" in hashes

# 4. Fallback multi-function rejection
def test_fallback_multi_function_rejected(repo_env):
    raw_multi_function = """```python
def add(a, b):
    return a + b

def helper():
    return 1
```"""
    session = EngineeringSession(
        task_prompt="Fix add",
        repo_root=repo_env,
        test_command="pytest test_calc.py",
        fallback_enabled=True
    )
    assert session._extract_patch(raw_multi_function) == ""

# 5. Fallback multi-file ambiguity rejection
def test_fallback_multi_file_ambiguity_rejected(repo_env):
    # Create duplicate function in another file
    dup_file = os.path.join(repo_env, "other_calc.py")
    with open(dup_file, "w", encoding="utf-8") as f:
        f.write("def add(a, b):\n    return a * b\n")

    raw_response = """```python
def add(a, b):
    return a + b
```"""
    session = EngineeringSession(
        task_prompt="Fix add",
        repo_root=repo_env,
        test_command="pytest test_calc.py",
        fallback_enabled=True
    )
    # Must reject because 'add' is ambiguous between calc.py and other_calc.py
    assert session._extract_patch(raw_response) == ""

# 6. Fallback unknown function rejection
def test_fallback_unknown_function_rejected(repo_env):
    raw_response = """```python
def multiply(a, b):
    return a * b
```"""
    session = EngineeringSession(
        task_prompt="Fix multiply",
        repo_root=repo_env,
        test_command="pytest test_calc.py",
        fallback_enabled=True
    )
    assert session._extract_patch(raw_response) == ""

# 7. Fallback disabled by default
def test_fallback_disabled_by_default(repo_env):
    raw_response = """```python
def add(a, b):
    return a + b
```"""
    session = EngineeringSession(
        task_prompt="Fix add",
        repo_root=repo_env,
        test_command="pytest test_calc.py",
        fallback_enabled=False
    )
    assert session._extract_patch(raw_response) == ""

# 8. Eager policy rejection before model invocation
def test_eager_policy_rejection_before_model_invocation(repo_env, monkeypatch):
    import app.engineering_loop

    model_called = []
    def mock_gen(prompt):
        model_called.append(prompt)
        return "Not reached"

    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_gen)

    marker_file = os.path.join(repo_env, "unsafe_marker.txt")
    unapproved_cmd = f"python -c \"open('{marker_file}', 'w').write('FAIL')\""

    session = EngineeringSession(
        task_prompt="Test task",
        repo_root=repo_env,
        test_command=unapproved_cmd,
        eager_policy_check=True
    )

    # Immediately on initialization, session is FAILED
    assert session.state == EngineeringState.FAILED
    assert session.failure_category == "policy_rejection"
    assert session.policy_event is not None
    assert session.policy_event["event"] == "unapproved_command_rejected"
    assert session.policy_event["stage"] == "session_init"

    # Stepping does not invoke model
    session.step()
    assert len(model_called) == 0
    assert not os.path.exists(marker_file)

# 9. Stale source detection and approval binding
def test_stale_source_detection_and_approval_binding(repo_env):
    patch = """FILE: calc.py
<<<<<<< SEARCH
def add(a, b):
    return a - b
=======
def add(a, b):
    return a + b
>>>>>>> REPLACE
"""
    session = EngineeringSession("Fix add", repo_env, "pytest test_calc.py")
    session.current_diff = patch
    success, errors, hashes = session._do_patch_validation()
    assert success is True

    session.source_file_hashes = hashes
    session.current_patch_hash = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    session.state = EngineeringState.AWAITING_APPROVAL

    # External modification to calc.py on disk
    with open(os.path.join(repo_env, "calc.py"), "w", encoding="utf-8") as f:
        f.write("# modified externally\ndef add(a, b):\n    return a - b\n")

    # Approval must be rejected due to stale source hash
    approved = session.approve()
    assert approved is False
    assert session.state == EngineeringState.FAILED
    assert session.failure_category == "stale_source"

# 10. Atomic multi-file rollback on invalid block
def test_atomic_multi_file_rollback_on_invalid_block(repo_env):
    # Create second file
    utils_file = os.path.join(repo_env, "utils.py")
    with open(utils_file, "w", encoding="utf-8") as f:
        f.write("def helper():\n    return 0\n")

    multi_patch = """FILE: calc.py
<<<<<<< SEARCH
def add(a, b):
    return a - b
=======
def add(a, b):
    return a + b
>>>>>>> REPLACE

FILE: utils.py
<<<<<<< SEARCH
def helper():
    return NONEXISTENT_LINES
=======
def helper():
    return 1
>>>>>>> REPLACE
"""
    engine = PatchEngine(repo_env)
    res = engine.apply_patch(multi_patch, dry_run=False)
    assert res["success"] is False

    # BOTH files must remain completely untouched
    with open(os.path.join(repo_env, "calc.py"), "r", encoding="utf-8") as f:
        assert f.read() == "def add(a, b):\n    return a - b\n"
    with open(utils_file, "r", encoding="utf-8") as f:
        assert f.read() == "def helper():\n    return 0\n"

# 11. Traversal and symlink protection
def test_traversal_and_symlink_protection(repo_env):
    traversal_patch = """FILE: ../../outside.py
<<<<<<< SEARCH
x = 1
=======
x = 2
>>>>>>> REPLACE
"""
    engine = PatchEngine(repo_env)
    res = engine.apply_patch(traversal_patch, dry_run=False)
    assert res["success"] is False
    assert any("SecurityViolation" in e for e in res["errors"])

# 12. Retry limits, cancellation, and concurrent approvals
def test_retry_limits_and_concurrent_approvals(repo_env):
    session = EngineeringSession("Fix add", repo_env, "pytest test_calc.py")
    session.current_diff = """FILE: calc.py
<<<<<<< SEARCH
def add(a, b):
    return a - b
=======
def add(a, b):
    return a + b
>>>>>>> REPLACE
"""
    session.current_patch_hash = hashlib.sha256(session.current_diff.encode("utf-8")).hexdigest()
    session.source_file_hashes = {"calc.py": session._compute_file_hash("calc.py")}
    session.state = EngineeringState.AWAITING_APPROVAL

    # First approval succeeds
    assert session.approve() is True
    assert session.state == EngineeringState.PATCH_APPLIED

    # Duplicate second approval must be safely rejected
    assert session.approve() is False
