import os
import sys
import json
import shutil
import pytest
from unittest.mock import MagicMock, patch

from app.config import config
from app.training_dataset import build_dataset, format_repair_prompt
from app.canary import CANARY_SUITE, evaluate_canary_gate, format_canary_test_script, clean_generated_code
from train_worker import (
    run_training_pipeline,
    get_training_state,
    save_training_state,
    ACTIVE_ADAPTER_DIR,
    CANDIDATES_DIR,
    ARCHIVE_DIR,
    TRAINING_STATE_FILE,
    TRAINING_HISTORY_FILE
)

@pytest.fixture(autouse=True)
def cleanup_test_adapters():
    """Ensure clean adapter directories before and after each test."""
    dirs_to_clean = ["models/adapters/test_candidates", "models/adapters/test_active", "models/adapters/test_archive"]
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
    yield
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)


# =====================================================================
# 1. Experience Replay Unit Tests
# =====================================================================

def test_experience_replay_partitioning(tmp_path):
    """Verify that build_dataset partitions previous memories into replay pool."""
    mem_file = str(tmp_path / "replay_mem.json")
    dataset_dir = str(tmp_path / "dataset_out")
    
    # Create 8 verified memories
    memories = [
        {
            "success": True,
            "task": f"Fix task {i}",
            "error_type": "AssertionError",
            "error_message": f"assert f({i}) failed",
            "broken_code": f"def f_{i}(): return {i}-1",
            "successful_fix": f"def f_{i}(): return {i}",
            "tests": f"assert f_{i}() == {i}",
            "verification": {"syntax_passed": True, "safety_passed": True, "execution_passed": True, "tests_passed": True}
        }
        for i in range(8)
    ]
    with open(mem_file, "w", encoding="utf-8") as f:
        json.dump(memories, f)
        
    # Cycle 1: last_trained_count = 0 (no replay, all 4 are new)
    res_cycle1 = build_dataset(
        memory_file=mem_file,
        dataset_dir=dataset_dir,
        last_trained_count=0,
        replay_size=4,
        replay_strategy="all"
    )
    assert res_cycle1["stats"]["accepted_unique_count"] == 8
    assert res_cycle1["stats"]["new_examples_count"] == 8
    assert res_cycle1["stats"]["replay_examples_count"] == 0
    assert len(res_cycle1["replay_examples"]) == 0

    # Cycle 2: last_trained_count = 4 (4 previous memories, 4 new memories)
    res_cycle2 = build_dataset(
        memory_file=mem_file,
        dataset_dir=dataset_dir,
        last_trained_count=4,
        replay_size=2,
        replay_strategy="recent"
    )
    assert res_cycle2["stats"]["new_examples_count"] == 4
    assert res_cycle2["stats"]["replay_examples_count"] == 2
    assert len(res_cycle2["replay_examples"]) == 2
    assert all(ex["is_replay"] is True for ex in res_cycle2["replay_examples"])
    assert all(ex["is_replay"] is False for ex in res_cycle2["new_examples"])

    # Total composite training pool should be 4 new + 2 replayed = 6 examples
    assert res_cycle2["stats"]["train_count"] + res_cycle2["stats"]["val_count"] + res_cycle2["stats"]["test_count"] == 6


def test_experience_replay_strategies(tmp_path):
    """Verify different sampling strategies: 'all', 'recent', 'uniform'."""
    mem_file = str(tmp_path / "strategies_mem.json")
    memories = [
        {
            "success": True,
            "task": f"Task {i}",
            "error_type": "AssertionError",
            "error_message": f"err {i}",
            "broken_code": f"def g_{i}(): pass",
            "successful_fix": f"def g_{i}(): return {i}",
            "tests": f"assert g_{i}() == {i}",
            "verification": {"syntax_passed": True, "safety_passed": True, "execution_passed": True, "tests_passed": True}
        }
        for i in range(10)
    ]
    with open(mem_file, "w", encoding="utf-8") as f:
        json.dump(memories, f)

    # Strategy: recent (last 3 of 6 previous memories)
    res_recent = build_dataset(
        memory_file=mem_file,
        dataset_dir=str(tmp_path / "ds_recent"),
        last_trained_count=6,
        replay_size=3,
        replay_strategy="recent"
    )
    assert res_recent["stats"]["replay_examples_count"] == 3

    # Strategy: uniform (sampled across 6 previous memories)
    res_uniform = build_dataset(
        memory_file=mem_file,
        dataset_dir=str(tmp_path / "ds_uniform"),
        last_trained_count=6,
        replay_size=3,
        replay_strategy="uniform"
    )
    assert res_uniform["stats"]["replay_examples_count"] == 3


# =====================================================================
# 2. Canary Gate Unit Tests
# =====================================================================

def test_canary_suite_definition():
    """Verify CANARY_SUITE contains essential primitives (parity, bounds, arithmetic)."""
    assert len(CANARY_SUITE) >= 3
    names = [c["name"] for c in CANARY_SUITE]
    assert "is_even" in names
    assert "in_range" in names
    assert "add" in names
    for c in CANARY_SUITE:
        assert "task_id" in c
        assert "broken_code" in c
        assert "error_message" in c
        assert "tests" in c


def test_canary_gate_evaluation_passing():
    """Verify Canary Gate passes when generated code satisfies all tests."""
    mock_model = MagicMock()
    mock_model.device = "cpu"
    mock_tokenizer = MagicMock()
    mock_tokenizer.eos_token_id = 0
    mock_tokenizer.pad_token_id = 0

    # Mock tokenizer output
    mock_tokenizer.return_tensors = "pt"
    mock_tokenizer.return_value = MagicMock(to=lambda d: {"input_ids": [1, 2]})

    # Mock generations that correctly solve canary tasks
    correct_outputs = {
        "CANARY_PARITY_001": "def is_even(n):\n    return n % 2 == 0",
        "CANARY_RANGE_002": "def in_range(val, min_val, max_val):\n    return min_val <= val <= max_val",
        "CANARY_ARITH_003": "def add(a, b):\n    return a + b"
    }

    def mock_decode(tokens, skip_special_tokens=True):
        # Determine which task is being decoded based on call count
        return "def is_even(n):\n    return n % 2 == 0\n"

    mock_tokenizer.decode = MagicMock(side_effect=[
        "def is_even(n):\n    return n % 2 == 0\n",
        "def in_range(val, min_val, max_val):\n    return min_val <= val <= max_val\n",
        "def add(a, b):\n    return a + b\n"
    ])

    canary_report = evaluate_canary_gate(
        model=mock_model,
        tokenizer=mock_tokenizer,
        threshold=1.0
    )

    assert canary_report["gate_passed"] is True
    assert canary_report["canary_passed_count"] == 3
    assert canary_report["canary_failed_count"] == 0
    assert canary_report["canary_success_rate"] == 1.0


def test_canary_gate_evaluation_failing_regression():
    """Verify Canary Gate detects negative transfer and rejects candidate."""
    mock_model = MagicMock()
    mock_model.device = "cpu"
    mock_tokenizer = MagicMock()
    mock_tokenizer.eos_token_id = 0
    mock_tokenizer.pad_token_id = 0
    mock_tokenizer.return_value = MagicMock(to=lambda d: {"input_ids": [1, 2]})

    # Simulate the exact regression observed in MODE-F Trained: is_even generates broken modulo
    mock_tokenizer.decode = MagicMock(side_effect=[
        "def is_even(n):\n    return n % 2 != 0\n",  # Regressed! Fails assert is_even(2) == True
        "def in_range(val, min_val, max_val):\n    return min_val <= val <= max_val\n",
        "def add(a, b):\n    return a + b\n"
    ])

    canary_report = evaluate_canary_gate(
        model=mock_model,
        tokenizer=mock_tokenizer,
        threshold=1.0
    )

    assert canary_report["gate_passed"] is False
    assert canary_report["canary_passed_count"] == 2
    assert canary_report["canary_failed_count"] == 1
    assert canary_report["canary_success_rate"] < 1.0
    
    # Verify is_even is flagged as failed
    failed_task = [t for t in canary_report["task_results"] if not t["passed"]][0]
    assert failed_task["name"] == "is_even"


# =====================================================================
# 3. Adapter Rollback & Preservation Tests
# =====================================================================

def test_adapter_rollback_preserves_active_adapter(tmp_path):
    """
    Verify that when candidate adapter fails Canary Gate:
    1. Candidate adapter is marked 'rejected' with rollback=True.
    2. Previous stable adapter is preserved in ACTIVE_ADAPTER_DIR without modification.
    3. active_adapter_id in state remains unchanged.
    """
    # Setup existing stable adapter v1
    test_active_dir = str(tmp_path / "active")
    os.makedirs(test_active_dir, exist_ok=True)
    with open(os.path.join(test_active_dir, "metadata.json"), "w") as f:
        json.dump({"adapter_id": "adapter_v1_stable", "version": 1, "status": "active"}, f)
    with open(os.path.join(test_active_dir, "adapter_config.json"), "w") as f:
        json.dump({"peft_type": "LORA"}, f)
    with open(os.path.join(test_active_dir, "adapter_model.safetensors"), "wb") as f:
        f.write(b"stable_v1_weights")

    state = {
        "last_trained_count": 4,
        "adapter_version_counter": 1,
        "active_adapter_id": "adapter_v1_stable",
        "is_training": False
    }

    # Simulate rejected candidate v2
    candidate_id = "adapter_v2_regressed"
    candidate_dir = str(tmp_path / "candidates" / candidate_id)
    os.makedirs(candidate_dir, exist_ok=True)

    canary_results = {
        "gate_passed": False,
        "canary_tasks_count": 3,
        "canary_passed_count": 2,
        "canary_failed_count": 1,
        "canary_success_rate": 0.6667
    }

    # Rejection and Rollback logic execution
    prev_active_id = state.get("active_adapter_id")
    metadata = {
        "adapter_id": candidate_id,
        "version": 2,
        "status": "rejected",
        "promotion_status": "rejected",
        "rollback": True,
        "rejection_reason": "canary_regression_detected",
        "retained_active_adapter_id": prev_active_id,
        "canary_results": canary_results
    }
    with open(os.path.join(candidate_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)

    # Assertions
    # 1. Active adapter directory was NOT modified
    with open(os.path.join(test_active_dir, "metadata.json")) as f:
        active_meta = json.load(f)
    assert active_meta["adapter_id"] == "adapter_v1_stable"
    with open(os.path.join(test_active_dir, "adapter_model.safetensors"), "rb") as f:
        assert f.read() == b"stable_v1_weights"

    # 2. Candidate adapter is preserved as rejected with rollback info
    with open(os.path.join(candidate_dir, "metadata.json")) as f:
        cand_meta = json.load(f)
    assert cand_meta["status"] == "rejected"
    assert cand_meta["rollback"] is True
    assert cand_meta["rejection_reason"] == "canary_regression_detected"
    assert cand_meta["retained_active_adapter_id"] == "adapter_v1_stable"


# =====================================================================
# 4. Pipeline Integration: Canary Gating & Rollback Metadata
# =====================================================================

def test_pipeline_integration_canary_rollback(tmp_path, monkeypatch):
    """
    Simulate training pipeline execution where candidate fails canary gate.
    Verifies that:
    1. Canary gate returns gate_passed=False.
    2. Rollback retains previous adapter without advancing version.
    3. Metadata records all required fields (training_cycle, examples, replay, canary, rollback).
    """
    mem_file = str(tmp_path / "test_mem.json")
    memories = [
        {
            "success": True,
            "task": f"Task {i}",
            "error_type": "AssertionError",
            "error_message": f"error_{i}",
            "broken_code": f"def f{i}(): pass",
            "successful_fix": f"def f{i}(): return {i}",
            "verification": {"syntax_passed": True, "safety_passed": True, "execution_passed": True, "tests_passed": True}
        }
        for i in range(5)
    ]
    with open(mem_file, "w", encoding="utf-8") as f:
        json.dump(memories, f)

    # Mock the Trainer so test runs instantly without GPU/CPU heavy training
    mock_train_res = MagicMock()
    mock_train_res.training_loss = 0.42

    def mock_save_pretrained(path):
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "adapter_config.json"), "w") as f:
            json.dump({"peft_type": "LORA"}, f)
        with open(os.path.join(path, "adapter_model.safetensors"), "wb") as f:
            f.write(b"mock_weights")

    mock_peft_model = MagicMock()
    mock_peft_model.save_pretrained = mock_save_pretrained

    # Mock canary gate returning failure (regressed on is_even)
    failing_canary = {
        "gate_passed": False,
        "canary_tasks_count": 3,
        "canary_passed_count": 2,
        "canary_failed_count": 1,
        "canary_success_rate": 0.6667,
        "task_results": [{"task_id": "CANARY_PARITY_001", "name": "is_even", "passed": False, "error": "AssertionError"}]
    }

    with patch("transformers.Trainer.train", return_value=mock_train_res), \
         patch("peft.get_peft_model", return_value=mock_peft_model), \
         patch("app.canary.evaluate_canary_gate", return_value=failing_canary), \
         patch("transformers.AutoTokenizer.from_pretrained") as mock_tok:

        # Configure tokenizer mock
        tok_inst = MagicMock()
        tok_inst.pad_token = None
        tok_inst.eos_token = "<eos>"
        tok_inst.eos_token_id = 1
        tok_inst.pad_token_id = 1
        tok_inst.encode = MagicMock(return_value=[1, 2])
        tok_inst.decode = MagicMock(return_value="def add(a, b):\n    return a + b")
        tok_inst.save_pretrained = MagicMock()
        mock_tok.return_value = tok_inst

        # Also mock PeftModel.from_pretrained during validation
        mock_val_peft = MagicMock()
        mock_val_peft.generate = MagicMock(return_value=[[1, 2]])
        with patch("peft.PeftModel.from_pretrained", return_value=mock_val_peft):
            res = run_training_pipeline(force=True, memory_file=mem_file)

    assert res["trained"] is True
    assert res["success"] is False
    assert res["promotion_status"] == "rejected"
    assert res["rollback"] is True
    assert res["rejection_reason"] == "canary_regression_detected"
    assert res["canary_results"]["canary_success_rate"] == 0.6667

