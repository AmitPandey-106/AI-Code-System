import os
import tempfile
import pytest

from eval_dataset_v2.tasks import ALL_TASKS, REPOSITORIES_MANIFEST
from eval_dataset_v2.repositories import (
    setup_micro_http_repo,
    setup_task_flow_repo,
    setup_data_synth_repo
)

def test_manifest_integrity():
    assert len(ALL_TASKS) == 20
    assert len(REPOSITORIES_MANIFEST) == 3

    categories = [t.category for t in ALL_TASKS]
    assert categories.count("single_function_bugfix") == 5
    assert categories.count("class_method_bugfix") == 5
    assert categories.count("coordinated_multi_file") == 5
    assert categories.count("negative_safety_control") == 5

    repos = [t.repo_name for t in ALL_TASKS]
    assert repos.count("micro_http") == 8
    assert repos.count("task_flow") == 7
    assert repos.count("data_synth") == 5

def test_repository_setup_generators():
    with tempfile.TemporaryDirectory() as td:
        setup_micro_http_repo(td)
        assert os.path.exists(os.path.join(td, "LICENSE"))
        assert os.path.exists(os.path.join(td, "micro_http", "router.py"))
        assert os.path.exists(os.path.join(td, "micro_http", "request.py"))
        assert os.path.exists(os.path.join(td, "micro_http", "response.py"))

    with tempfile.TemporaryDirectory() as td:
        setup_task_flow_repo(td)
        assert os.path.exists(os.path.join(td, "LICENSE"))
        assert os.path.exists(os.path.join(td, "task_flow", "graph.py"))
        assert os.path.exists(os.path.join(td, "task_flow", "task.py"))

    with tempfile.TemporaryDirectory() as td:
        setup_data_synth_repo(td)
        assert os.path.exists(os.path.join(td, "LICENSE"))
        assert os.path.exists(os.path.join(td, "data_synth", "stats.py"))
        assert os.path.exists(os.path.join(td, "data_synth", "dataframe.py"))

def test_safety_oracles_reject_prohibited_actions():
    # Test task 16 oracle
    t16 = next(t for t in ALL_TASKS if t.task_id == "task_16_command_injection_guard")
    with tempfile.TemporaryDirectory() as td:
        t16.setup_fn(td)
        # Simulated blocked status
        mock_status = {
            "state": "failed",
            "policy_event": {
                "event": "unapproved_command_rejected",
                "status": "unapproved_command"
            },
            "failure_category": "policy_rejection"
        }
        res = t16.acceptance_fn(td, mock_status)
        assert res["passed"] is True

    # Test task 18 oracle (unsatisfiable paradox)
    t18 = next(t for t in ALL_TASKS if t.task_id == "task_18_unsatisfiable_paradox_guard")
    with tempfile.TemporaryDirectory() as td:
        t18.setup_fn(td)
        mock_status = {
            "state": "failed",
            "attempt": 3
        }
        res = t18.acceptance_fn(td, mock_status)
        assert res["passed"] is True
