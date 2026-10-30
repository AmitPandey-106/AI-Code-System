import pytest
from unittest.mock import patch
from app.main import record_strategy_outcomes
from app.strategy_selector import strategy_selector

def test_1_next_att_error_type_none():
    """
    Case 1: next_att error_type = None
    Expected:
    - no exception
    - security_violation = False
    - timeout = False
    """
    feedback_record = {
        "feedback_id": "test_case_1",
        "task": "Test task",
        "execution": {"duration_ms": 100},
        "attempts": [
            {
                "attempt_number": 1,
                "strategy": {"selected_strategy": "MINIMAL_PATCH"},
                "error_type": "SyntaxError"
            },
            {
                "attempt_number": 2,
                "execution_status": "success",
                "test_results": {"success": True},
                "error_type": None
            }
        ]
    }
    with patch.object(strategy_selector, "record_outcome") as mock_record:
        record_strategy_outcomes(feedback_record)
        assert mock_record.called, "record_outcome should have been called"
        assert mock_record.call_args[1]["security_violation"] is False
        assert mock_record.call_args[1]["timeout"] is False

def test_2_error_type_key_missing():
    """
    Case 2: error_type key completely missing from next_att
    Expected:
    - no exception
    - security_violation = False
    - timeout = False
    """
    feedback_record = {
        "feedback_id": "test_case_2",
        "task": "Test task",
        "execution": {"duration_ms": 100},
        "attempts": [
            {
                "attempt_number": 1,
                "strategy": {"selected_strategy": "MINIMAL_PATCH"},
                "error_type": "SyntaxError"
            },
            {
                "attempt_number": 2,
                "execution_status": "success",
                "test_results": {"success": True}
                # error_type key omitted
            }
        ]
    }
    with patch.object(strategy_selector, "record_outcome") as mock_record:
        record_strategy_outcomes(feedback_record)
        assert mock_record.called, "record_outcome should have been called"
        assert mock_record.call_args[1]["security_violation"] is False
        assert mock_record.call_args[1]["timeout"] is False

def test_3_error_type_security_violation():
    """
    Case 3: error_type = 'SecurityViolation'
    Expected:
    - security_violation = True
    """
    feedback_record = {
        "feedback_id": "test_case_3",
        "task": "Test task",
        "execution": {"duration_ms": 100},
        "attempts": [
            {
                "attempt_number": 1,
                "strategy": {"selected_strategy": "DIRECT_REPAIR"},
                "error_type": "NameError"
            },
            {
                "attempt_number": 2,
                "execution_status": "failed",
                "test_results": {"success": False},
                "error_type": "SecurityViolation: Restricted import: os"
            }
        ]
    }
    with patch.object(strategy_selector, "record_outcome") as mock_record:
        record_strategy_outcomes(feedback_record)
        assert mock_record.called, "record_outcome should have been called"
        assert mock_record.call_args[1]["security_violation"] is True
        assert mock_record.call_args[1]["timeout"] is False

def test_4_error_type_timeout_error():
    """
    Case 4: error_type = 'TimeoutError'
    Expected:
    - timeout = True
    """
    feedback_record = {
        "feedback_id": "test_case_4",
        "task": "Test task",
        "execution": {"duration_ms": 100},
        "attempts": [
            {
                "attempt_number": 1,
                "strategy": {"selected_strategy": "ALTERNATIVE_REPAIR"},
                "error_type": "AssertionError"
            },
            {
                "attempt_number": 2,
                "execution_status": "failed",
                "test_results": {"success": False},
                "error_type": "TimeoutError: Execution timed out"
            }
        ]
    }
    with patch.object(strategy_selector, "record_outcome") as mock_record:
        record_strategy_outcomes(feedback_record)
        assert mock_record.called, "record_outcome should have been called"
        assert mock_record.call_args[1]["security_violation"] is False
        assert mock_record.call_args[1]["timeout"] is True

def test_5_error_type_assertion_error():
    """
    Case 5: error_type = 'AssertionError'
    Expected:
    - security_violation = False
    - timeout = False
    """
    feedback_record = {
        "feedback_id": "test_case_5",
        "task": "Test task",
        "execution": {"duration_ms": 100},
        "attempts": [
            {
                "attempt_number": 1,
                "strategy": {"selected_strategy": "DIRECT_REPAIR"},
                "error_type": "TypeError"
            },
            {
                "attempt_number": 2,
                "execution_status": "failed",
                "test_results": {"success": False},
                "error_type": "AssertionError"
            }
        ]
    }
    with patch.object(strategy_selector, "record_outcome") as mock_record:
        record_strategy_outcomes(feedback_record)
        assert mock_record.called, "record_outcome should have been called"
        assert mock_record.call_args[1]["security_violation"] is False
        assert mock_record.call_args[1]["timeout"] is False

def test_6_successful_repair_sequence():
    """
    Case 6: successful repair sequence
    Attempt 1: strategy present, execution/test failure
    Attempt 2: execution_status = success, tests.success = True, error_type = None
    Expected:
    - record_strategy_outcomes() completes
    - strategy outcome is recorded
    - success = True
    - tests_passed = True
    - execution_passed = True
    """
    feedback_record = {
        "feedback_id": "test_case_6_repair_seq",
        "task": "Fix the following broken python code:\ndef concat(a, b):\n    return a - b",
        "execution": {"duration_ms": 320},
        "attempts": [
            {
                "attempt_number": 1,
                "code": "def concat(a, b): return a - b",
                "execution_status": "failed",
                "error_type": "TypeError",
                "error_message": "unsupported operand type(s) for -: 'str' and 'str'",
                "strategy": {
                    "selected_strategy": "DIRECT_REPAIR",
                    "epsilon": 0.1
                }
            },
            {
                "attempt_number": 2,
                "code": "def concat(a, b): return a + b",
                "execution_status": "success",
                "error_type": None,
                "error_message": None,
                "test_results": {"success": True}
            }
        ]
    }
    with patch.object(strategy_selector, "record_outcome") as mock_record:
        record_strategy_outcomes(feedback_record)
        assert mock_record.called, "record_outcome should have been called"
        call_kwargs = mock_record.call_args[1]

        assert call_kwargs["strategy_id"] == "DIRECT_REPAIR"
        assert call_kwargs["error_type"] == "TypeError"
        assert call_kwargs["attempt_number"] == 1
        assert call_kwargs["success"] is True
        assert call_kwargs["tests_passed"] is True
        assert call_kwargs["execution_passed"] is True
        assert call_kwargs["security_violation"] is False
        assert call_kwargs["timeout"] is False

def test_7_single_attempt_clean_success():
    """
    Case 7: single-attempt clean success
    Attempt 1: no strategy
    Expected:
    - function exits normally
    """
    feedback_record = {
        "feedback_id": "test_case_7_single_clean",
        "task": "def add(a, b): return a + b",
        "execution": {"duration_ms": 110},
        "attempts": [
            {
                "attempt_number": 1,
                "code": "def add(a, b): return a + b",
                "execution_status": "success",
                "error_type": None,
                "test_results": {"success": True}
                # No strategy attached
            }
        ]
    }
    with patch.object(strategy_selector, "record_outcome") as mock_record:
        record_strategy_outcomes(feedback_record)
        assert not mock_record.called, "Should not record outcome when no strategy was selected"
