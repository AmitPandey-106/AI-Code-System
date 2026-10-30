import os
import tempfile
import pytest
from app.project_test_runner import project_test_runner

@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as td:
        # Create passing test
        with open(os.path.join(td, "test_pass.py"), "w", encoding="utf-8") as f:
            f.write("def test_ok():\n    assert True")
            
        # Create failing test
        with open(os.path.join(td, "test_fail.py"), "w", encoding="utf-8") as f:
            f.write("def test_bad():\n    assert False")
            
        # Create verbose test for truncation
        with open(os.path.join(td, "test_verbose.py"), "w", encoding="utf-8") as f:
            f.write("def test_verbose():\n    print('A' * 15000)\n    assert True")

        # Create infinite loop for timeout
        with open(os.path.join(td, "test_timeout.py"), "w", encoding="utf-8") as f:
            f.write("import time\ndef test_timeout():\n    while True:\n        time.sleep(0.1)")
            
        yield td

def test_passing_suite(temp_repo):
    # A passing pytest suite.
    res = project_test_runner.run_tests(temp_repo, "pytest test_pass.py")
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["exit_code"] == 0

def test_failing_assertion(temp_repo):
    # A failing pytest assertion.
    res = project_test_runner.run_tests(temp_repo, "pytest test_fail.py")
    assert res["success"] is False
    assert res["status"] == "failed"
    assert res["exit_code"] != 0
    assert "assert False" in res["output"]

def test_missing_executable(temp_repo, monkeypatch):
    # Simulate missing pytest by mocking shutil.which
    import shutil
    monkeypatch.setattr(shutil, "which", lambda x: None)
    res = project_test_runner.run_tests(temp_repo, "pytest test_pass.py")
    assert res["status"] == "missing_executable"
    
def test_command_timeout(temp_repo):
    # A command timeout.
    res = project_test_runner.run_tests(temp_repo, "pytest test_timeout.py", timeout=1)
    assert res["success"] is False
    assert res["status"] == "timeout"
    assert res["timeout"] is True

def test_captured_stdout_stderr(temp_repo):
    # Captured stdout and stderr.
    with open(os.path.join(temp_repo, "test_stdout.py"), "w", encoding="utf-8") as f:
        f.write("import sys\ndef test_out():\n    print('HELLO STDOUT')\n    print('HELLO STDERR', file=sys.stderr)\n    assert True")
    res = project_test_runner.run_tests(temp_repo, "pytest test_stdout.py -s")
    assert "HELLO STDOUT" in res["output"]
    assert "HELLO STDERR" in res["output"]
    
def test_invalid_repository_root():
    # An invalid repository root.
    res = project_test_runner.run_tests("/invalid/path/does/not/exist", "pytest")
    assert res["success"] is False
    assert res["status"] == "invalid_directory"

def test_rejected_unapproved_command(temp_repo):
    # A rejected unapproved command.
    res = project_test_runner.run_tests(temp_repo, "rm -rf /")
    assert res["success"] is False
    assert res["status"] == "unapproved_command"
    
def test_output_truncation(temp_repo):
    # Output truncation for excessively verbose tests.
    res = project_test_runner.run_tests(temp_repo, "pytest test_verbose.py -s")
    assert len(res["output"]) <= project_test_runner.max_output_length + 100
    assert "[OUTPUT TRUNCATED]" in res["output"]

def test_distinction_between_failure_types(temp_repo):
    # Correct distinction between failure, timeout, and successful execution.
    res1 = project_test_runner.run_tests(temp_repo, "pytest test_pass.py")
    assert res1["status"] == "success"
    
    res2 = project_test_runner.run_tests(temp_repo, "pytest test_fail.py")
    assert res2["status"] == "failed"
    
    res3 = project_test_runner.run_tests(temp_repo, "pytest test_timeout.py", timeout=1)
    assert res3["status"] == "timeout"
