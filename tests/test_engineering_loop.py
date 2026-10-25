import os
import tempfile
import pytest
from app.engineering_loop import engineering_manager, EngineeringState

# We will mock generate_raw in tests
def mock_generate_raw_success(prompt: str) -> str:
    return """
I will fix the file.
```diff
--- a/test_math.py
+++ b/test_math.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
```
"""

def mock_generate_raw_malformed(prompt: str) -> str:
    return "I am a bad model. No diff for you."

def mock_generate_raw_repair(prompt: str) -> str:
    if "PREVIOUS TEST FAILURE DIAGNOSIS" in prompt:
        # Repair attempt
        return """
```diff
--- a/test_math.py
+++ b/test_math.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
```
"""
    else:
        # Initial attempt - fails tests
        return """
```diff
--- a/test_math.py
+++ b/test_math.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a * b
```
"""

@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as td:
        # Initialize an index directory so repo_index doesn't fail
        os.makedirs(os.path.join(td, "data", "repo_index"))
        
        with open(os.path.join(td, "test_math.py"), "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a - b\n")
            
        with open(os.path.join(td, "test_suite.py"), "w", encoding="utf-8") as f:
            f.write("from test_math import add\ndef test_add():\n    assert add(2, 3) == 5\n")
            
        yield td

def test_successful_task(temp_repo, monkeypatch):
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_success)
    
    session_id = engineering_manager.start_session("Fix addition", temp_repo, "pytest test_suite.py")
    session = engineering_manager.get_session(session_id)
    
    assert session.state == EngineeringState.AWAITING_APPROVAL
    assert session.current_attempt == 1
    
    # Approve
    session.approve()
    session.step()
    
    assert session.state == EngineeringState.COMPLETED
    assert session.current_attempt == 1
    
    with open(os.path.join(temp_repo, "test_math.py"), "r") as f:
        assert "return a + b" in f.read()

def test_repair_budget_exhaustion(temp_repo, monkeypatch):
    import app.engineering_loop
    # Always outputs the wrong fix `return a * b`
    monkeypatch.setattr(app.engineering_loop, "generate_raw", lambda p: """
```diff
--- a/test_math.py
+++ b/test_math.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a * b
```
""" if "PREVIOUS" not in p else """
```diff
--- a/test_math.py
+++ b/test_math.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a * b
```
""")

    session_id = engineering_manager.start_session("Fix addition", temp_repo, "pytest test_suite.py")
    session = engineering_manager.get_session(session_id)
    
    assert session.state == EngineeringState.AWAITING_APPROVAL
    
    # Attempt 1
    session.approve()
    session.step()
    assert session.state == EngineeringState.AWAITING_APPROVAL
    assert session.current_attempt == 2
    
    # Attempt 2
    session.approve()
    session.step()
    assert session.state == EngineeringState.AWAITING_APPROVAL
    assert session.current_attempt == 3
    
    # Attempt 3 (exhausts budget)
    session.approve()
    session.step()
    assert session.state == EngineeringState.FAILED
    assert "Budget exhausted" in session.error_message
    
def test_successful_repair(temp_repo, monkeypatch):
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_repair)
    
    session_id = engineering_manager.start_session("Fix addition", temp_repo, "pytest test_suite.py")
    session = engineering_manager.get_session(session_id)
    
    assert session.state == EngineeringState.AWAITING_APPROVAL
    
    # Attempt 1 (will fail tests because it makes it a * b)
    session.approve()
    session.step()
    
    assert session.state == EngineeringState.AWAITING_APPROVAL
    assert session.current_attempt == 2
    
    # Attempt 2 (will pass tests because it makes it a + b)
    session.approve()
    session.step()
    
    assert session.state == EngineeringState.COMPLETED
    assert session.current_attempt == 2

def test_malformed_patch_rejection(temp_repo, monkeypatch):
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_malformed)
    
    session_id = engineering_manager.start_session("Fix addition", temp_repo, "pytest test_suite.py")
    session = engineering_manager.get_session(session_id)
    
    assert session.state == EngineeringState.FAILED
    assert "valid unified diff" in session.error_message

def test_user_rejection(temp_repo, monkeypatch):
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_success)
    
    session_id = engineering_manager.start_session("Fix addition", temp_repo, "pytest test_suite.py")
    session = engineering_manager.get_session(session_id)
    
    assert session.state == EngineeringState.AWAITING_APPROVAL
    
    session.reject()
    
    assert session.state == EngineeringState.CANCELLED

def test_unsafe_command_rejected(temp_repo, monkeypatch):
    import app.engineering_loop
    monkeypatch.setattr(app.engineering_loop, "generate_raw", mock_generate_raw_success)
    
    # Attempting to run rm -rf
    session_id = engineering_manager.start_session("Fix addition", temp_repo, "rm -rf /")
    session = engineering_manager.get_session(session_id)
    
    assert session.state == EngineeringState.AWAITING_APPROVAL
    
    session.approve()
    session.step()
    
    # ProjectTestRunner will fail the command and report failed status
    # The engineering loop treats success=False as a test failure, and loops for diagnosis.
    # However, since the mock generator returns the same patch again, validation fails and it aborts.
    assert session.state == EngineeringState.FAILED
    
    # The test results recorded after test execution
    test_res_entry = next(h["test_results"] for h in session.history if h.get("test_results"))
    assert test_res_entry["status"] == "unapproved_command"
