import pytest
import os
import sys
import tempfile
import subprocess
from app.project_test_runner import ProjectTestRunner, project_test_runner

def test_executable_allowlist_boundaries():
    runner = ProjectTestRunner()
    # Explicitly allowed
    assert runner.is_command_allowed("pytest tests/test_foo.py") is True
    assert runner.is_command_allowed("python -m pytest tests/") is True
    assert runner.is_command_allowed("python3 -m pytest tests/") is True
    assert runner.is_command_allowed("pytest -k test_router") is True
    
    # Prohibited executables and commands
    assert runner.is_command_allowed('python -c "import os"') is False
    assert runner.is_command_allowed("python script.py") is False
    assert runner.is_command_allowed("python3 -m unittest") is False
    assert runner.is_command_allowed("python -m http.server") is False
    assert runner.is_command_allowed("bash tests.sh") is False
    assert runner.is_command_allowed("cmd.exe /c pytest") is False
    assert runner.is_command_allowed("powershell pytest") is False
    assert runner.is_command_allowed("sh -c pytest") is False

def test_shell_operator_and_chaining_rejections():
    runner = ProjectTestRunner()
    # Operators and chaining
    assert runner.is_command_allowed("pytest tests/ ; whoami") is False
    assert runner.is_command_allowed("pytest tests/ && whoami") is False
    assert runner.is_command_allowed("pytest tests/ || whoami") is False
    assert runner.is_command_allowed("pytest tests/ | whoami") is False
    assert runner.is_command_allowed("pytest tests/ & whoami") is False
    assert runner.is_command_allowed("pytest tests/ \n whoami") is False
    assert runner.is_command_allowed("pytest tests/ \r whoami") is False
    
    # Substitutions & backticks
    assert runner.is_command_allowed("pytest `id`") is False
    assert runner.is_command_allowed("pytest $(id)") is False
    assert runner.is_command_allowed("pytest $FOO") is False
    
    # Redirections
    assert runner.is_command_allowed("pytest > output.txt") is False
    assert runner.is_command_allowed("pytest < input.txt") is False

def test_pytest_dangerous_flag_boundaries():
    runner = ProjectTestRunner()
    # Forbidden flags exact and prefix
    assert runner.is_command_allowed("pytest --pdb") is False
    assert runner.is_command_allowed("pytest --pdb=True") is False
    assert runner.is_command_allowed("pytest -c malicious.ini") is False
    assert runner.is_command_allowed("pytest -c=malicious.ini") is False
    assert runner.is_command_allowed("pytest --config-file malicious.ini") is False
    assert runner.is_command_allowed("pytest --config-file=malicious.ini") is False
    assert runner.is_command_allowed("pytest -o foo=bar") is False
    assert runner.is_command_allowed("pytest --override-ini=foo=bar") is False
    assert runner.is_command_allowed("pytest --import-mode=importlib") is False
    assert runner.is_command_allowed("pytest --assert=plain") is False

def test_untested_attack_surface_analysis():
    runner = ProjectTestRunner()
    # Phase 8.1 closes the plugin-loading surface recorded by the historical audit
    # For example, -p plugin can load plugins if installed or in pythonpath
    plugin_flag_allowed = runner.is_command_allowed("pytest -p my_plugin")
    # User-supplied plugin loading must now be rejected
    assert plugin_flag_allowed is False

def test_working_directory_validation():
    runner = ProjectTestRunner()
    # Non-existent repo root
    res = runner.run_tests("/non/existent/path/for/audit/test", "pytest")
    assert res["success"] is False
    assert res["status"] == "invalid_directory"

def test_environment_sanitization():
    runner = ProjectTestRunner()
    with tempfile.TemporaryDirectory() as td:
        # Create a passing dummy test
        test_file = os.path.join(td, "test_dummy.py")
        with open(test_file, "w") as f:
            f.write("def test_env(): pass\n")
        
        # Test run with poisoned environment
        os.environ["LD_PRELOAD"] = "malicious.so"
        os.environ["PYTHONSTARTUP"] = "malicious.py"
        os.environ["PYTHONBREAKPOINT"] = "pdb.set_trace"
        try:
            res = runner.run_tests(td, "python -m pytest test_dummy.py")
            assert res["success"] is True
        finally:
            os.environ.pop("LD_PRELOAD", None)
            os.environ.pop("PYTHONSTARTUP", None)
            os.environ.pop("PYTHONBREAKPOINT", None)
