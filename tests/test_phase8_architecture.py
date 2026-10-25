import os
import shutil
import tempfile
import pytest
from app.project_test_runner import project_test_runner
from app.repair_memory import RepairMemory
from app.strategy_selector import StrategySelector
from app.multi_file_orchestrator import MultiFileEngineeringOrchestrator
from app.engineering_loop import EngineeringSession, EngineeringState

# ==============================================================================
# 1. COMMAND EXECUTION SECURITY TESTS
# ==============================================================================

def test_command_security_allowed_commands():
    assert project_test_runner.is_command_allowed("pytest") is True
    assert project_test_runner.is_command_allowed("pytest tests/test_foo.py") is True
    assert project_test_runner.is_command_allowed("pytest -v -s tests/") is True
    assert project_test_runner.is_command_allowed("python -m pytest") is True
    assert project_test_runner.is_command_allowed("python -m pytest tests/test_bar.py -q") is True
    assert project_test_runner.is_command_allowed("python3 -m pytest") is True

def test_command_security_rejected_commands():
    # Shell operators and chaining
    assert project_test_runner.is_command_allowed("pytest; rm -rf /") is False
    assert project_test_runner.is_command_allowed("pytest && echo 1") is False
    assert project_test_runner.is_command_allowed("pytest || echo 2") is False
    assert project_test_runner.is_command_allowed("pytest | cat") is False
    assert project_test_runner.is_command_allowed("pytest &") is False
    assert project_test_runner.is_command_allowed("pytest\nls") is False

    # Redirection and substitutions
    assert project_test_runner.is_command_allowed("pytest > out.txt") is False
    assert project_test_runner.is_command_allowed("pytest < in.txt") is False
    assert project_test_runner.is_command_allowed("pytest $(whoami)") is False
    assert project_test_runner.is_command_allowed("pytest `id`") is False

    # Arbitrary code execution via python
    assert project_test_runner.is_command_allowed("python -c \"import os; os.system('calc')\"") is False
    assert project_test_runner.is_command_allowed("python evil.py") is False
    assert project_test_runner.is_command_allowed("python3 evil.py") is False

    # Dangerous pytest flags
    assert project_test_runner.is_command_allowed("pytest --pdb") is False
    assert project_test_runner.is_command_allowed("pytest -c evil.ini") is False
    assert project_test_runner.is_command_allowed("pytest -o evil=1") is False

    # Non-allowlisted binaries
    assert project_test_runner.is_command_allowed("curl http://evil.com") is False
    assert project_test_runner.is_command_allowed("bash -c 'pytest'") is False

# ==============================================================================
# 2. DYNAMIC AST FALLBACK SYNTHESIZER TESTS
# ==============================================================================

def test_dynamic_ast_fallback_single_function():
    with tempfile.TemporaryDirectory() as td:
        py_file = os.path.join(td, "math_mod.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a - b\n")

        session = EngineeringSession(
            task_prompt="Fix add function in math_mod.py",
            repo_root=td,
            test_command="pytest",
            fallback_enabled=True,
            eager_policy_check=False
        )

        # Raw response with python fence but no SEARCH/REPLACE delimiters
        raw_model_response = "Here is the fix:\n```python\ndef add(a, b):\n    return a + b\n```"
        synthesized = session._synthesize_single_function_fallback(raw_model_response)
        assert synthesized != ""
        assert "FILE: math_mod.py" in synthesized
        assert "<<<<<<< SEARCH" in synthesized
        assert "return a - b" in synthesized
        assert "return a + b" in synthesized
        assert ">>>>>>> REPLACE" in synthesized
        assert session.fallback_rejected_reason == ""

def test_dynamic_ast_fallback_rejects_class_method():
    with tempfile.TemporaryDirectory() as td:
        py_file = os.path.join(td, "calc.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("class Calculator:\n    def compute(self, x):\n        return x * 1\n")

        session = EngineeringSession(
            task_prompt="Fix compute method",
            repo_root=td,
            test_command="pytest",
            fallback_enabled=True,
            eager_policy_check=False
        )

        # Candidate defines class method or matches class in repo
        raw_response = "```python\nclass Calculator:\n    def compute(self, x):\n        return x * 2\n```"
        synthesized = session._synthesize_single_function_fallback(raw_response)
        assert synthesized == ""
        assert session.fallback_rejected_reason == "class_method_rejected"

def test_dynamic_ast_fallback_rejects_multiple_functions():
    with tempfile.TemporaryDirectory() as td:
        session = EngineeringSession(
            task_prompt="Fix helper functions",
            repo_root=td,
            test_command="pytest",
            fallback_enabled=True,
            eager_policy_check=False
        )

        raw_response = "```python\ndef fn1(): pass\ndef fn2(): pass\n```"
        synthesized = session._synthesize_single_function_fallback(raw_response)
        assert synthesized == ""
        assert session.fallback_rejected_reason == "multiple_functions_rejected"

# ==============================================================================
# 3. VERIFIED REPAIR EXPERIENCE MEMORY TESTS
# ==============================================================================

def test_repair_memory_isolation_and_gating():
    with tempfile.TemporaryDirectory() as td:
        mem = RepairMemory(storage_dir=td, enabled=True)
        # 1. Unverified experience must be rejected
        unverified_res = mem.add_verified_experience(
            task="fix bug",
            error_type="AssertionError",
            error_message="assert False",
            broken_code="def f(): return False",
            successful_fix="def f(): return True",
            tests="pytest",
            verification={"passed": False, "status": "failed"},
            repair_attempts=1
        )
        assert unverified_res is False
        assert len(mem.memories) == 0

        # 2. Verified experience must be ingested
        verified_res = mem.add_verified_experience(
            task="fix bug",
            error_type="AssertionError",
            error_message="assert False",
            broken_code="def f(): return False",
            successful_fix="FILE: mod.py\n<<<<<<< SEARCH\nreturn False\n=======\nreturn True\n>>>>>>> REPLACE",
            tests="pytest",
            verification={"passed": True, "status": "success"},
            repair_attempts=1
        )
        assert verified_res is True
        assert len(mem.memories) == 1

        # 3. Search retrieves schema with successful_fix accessible both ways
        results = mem.search_similar_experiences(
            task="fix bug",
            error_type="AssertionError",
            error_message="assert False",
            broken_code=""
        )
        assert len(results) >= 1
        assert "successful_fix" in results[0]
        assert "memory" in results[0]
        assert "return True" in results[0]["successful_fix"]
        assert "return True" in results[0]["memory"]["successful_fix"]

# ==============================================================================
# 4. ADAPTIVE STRATEGY SELECTOR TESTS
# ==============================================================================

def test_strategy_selector_isolation_and_rewards():
    with tempfile.TemporaryDirectory() as td:
        selector = StrategySelector(storage_dir=td, enabled=True)
        decision = selector.select_strategy(
            error_type="AssertionError",
            attempt_number=1,
            previous_strategies=[],
            memory_available=True,
            difficulty="standard"
        )
        assert "selected_strategy" in decision
        selected = decision["selected_strategy"]

        # Record positive outcome
        selector.record_outcome(
            strategy_id=selected,
            error_type="AssertionError",
            task="Test task",
            attempt_number=1,
            success=True,
            tests_passed=True,
            execution_passed=True,
            duration_ms=150,
            feedback_id="fb_1",
            security_violation=False,
            timeout=False
        )
        assert selector.stats[selected]["AssertionError"]["successes"] == 1
        assert selector.stats[selected]["AssertionError"]["reward"] > 0

# ==============================================================================
# 5. MULTI-FILE ORCHESTRATOR TESTS (TRANSACTION & ROLLBACK)
# ==============================================================================

from unittest.mock import patch

def test_multi_file_orchestrator_atomic_rollback():
    with tempfile.TemporaryDirectory() as td:
        file_a = os.path.join(td, "file_a.py")
        file_b = os.path.join(td, "file_b.py")
        with open(file_a, "w", encoding="utf-8") as f:
            f.write("# ORIGINAL A\n")
        with open(file_b, "w", encoding="utf-8") as f:
            f.write("# ORIGINAL B\n")

        test_file = os.path.join(td, "test_ab.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def test_never_pass():\n    assert False\n")

        orchestrator = MultiFileEngineeringOrchestrator(
            repo_root=td,
            test_command="pytest test_ab.py",
            fallback_enabled=True,
            approval_callback=lambda proposal: True
        )

        with patch("app.engineering_loop.generate_raw") as mock_gen:
            mock_gen.side_effect = [
                "FILE: file_a.py\n<<<<<<< SEARCH\n# ORIGINAL A\n=======\n# MODIFIED A\n>>>>>>> REPLACE",
                "FILE: file_b.py\n<<<<<<< SEARCH\n# ORIGINAL B\n=======\n# MODIFIED B\n>>>>>>> REPLACE"
            ]

            # Execute plan on files where tests will fail
            res = orchestrator.execute_plan(
                task_prompt="Update both files",
                target_files=["file_a.py", "file_b.py"]
            )

        # Must report failure and rolled_back = True
        assert res.success is False
        assert res.rolled_back is True

        # Verify disk contents are 100% restored to original snapshot
        with open(file_a, "r", encoding="utf-8") as f:
            assert f.read() == "# ORIGINAL A\n"
        with open(file_b, "r", encoding="utf-8") as f:
            assert f.read() == "# ORIGINAL B\n"
