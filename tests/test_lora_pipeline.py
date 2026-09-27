import os
import sys
import json
import shutil
import time
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import config
from app.training_dataset import (
    validate_training_experience,
    build_training_example,
    generate_fingerprint,
    build_dataset
)
from train_worker import (
    get_training_state,
    save_training_state,
    append_training_history,
    run_training_pipeline,
    TRAINING_STATE_FILE,
    TRAINING_HISTORY_FILE,
    ACTIVE_ADAPTER_DIR,
    CANDIDATES_DIR,
    ARCHIVE_DIR
)
from app.model import (
    get_model,
    reload_model,
    check_and_reload_adapter
)

@pytest.fixture(autouse=True)
def clean_lora_environment():
    """Ensure clean adapter and config state for every test."""
    config.set("LORA_ENABLED", True)
    config.set("LORA_BUFFER_SIZE", 4)
    config.set("LORA_EPOCHS", 1)
    
    # Clean temporary directories
    for path in [ACTIVE_ADAPTER_DIR, CANDIDATES_DIR, ARCHIVE_DIR]:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    for f in [TRAINING_STATE_FILE, TRAINING_HISTORY_FILE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
    reload_model()
    yield
    # Cleanup after test
    for path in [ACTIVE_ADAPTER_DIR, CANDIDATES_DIR, ARCHIVE_DIR]:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    for f in [TRAINING_STATE_FILE, TRAINING_HISTORY_FILE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
    reload_model()


# -------------------------------------------------------------
# 1. Dataset Formatting & Quality Filtering Tests
# -------------------------------------------------------------

def test_validate_training_experience_quality():
    valid_memory = {
        "success": True,
        "task": "Write concat function",
        "error_type": "AssertionError",
        "error_message": "assert concat('a', 'b') == 'ab'",
        "broken_code": "def concat(a, b): return a",
        "successful_fix": "def concat(a, b): return a + b",
        "verification": {
            "syntax_passed": True,
            "safety_passed": True,
            "execution_passed": True,
            "tests_passed": True
        }
    }
    assert validate_training_experience(valid_memory) is True

    # Reject failed execution
    failed_mem = dict(valid_memory, success=False)
    assert validate_training_experience(failed_mem) is False

    # Reject security violations
    sec_mem = dict(valid_memory, error_type="SecurityViolation")
    assert validate_training_experience(sec_mem) is False

    # Reject timeouts
    timeout_mem = dict(valid_memory, error_type="TimeoutError")
    assert validate_training_experience(timeout_mem) is False

    # Reject missing fields
    missing_fix = dict(valid_memory, successful_fix="")
    assert validate_training_experience(missing_fix) is False


def test_training_example_prompt_alignment():
    mem = {
        "task": "Write concat",
        "broken_code": "def concat(a, b): return a",
        "error_message": "AssertionError: expected 'ab'",
        "successful_fix": "def concat(a, b): return a + b",
        "tests": "assert concat('a', 'b') == 'ab'"
    }
    ex = build_training_example(mem)
    
    # Prompt must contain debugger instruction matching inference
    assert "You are an expert Python debugger." in ex["prompt"]
    assert "CURRENT PROBLEM:" in ex["prompt"]
    assert "BROKEN CODE:" in ex["prompt"]
    assert mem["broken_code"] in ex["prompt"]
    assert mem["error_message"] in ex["prompt"]
    
    # Completion must contain the successful fix
    assert mem["successful_fix"] in ex["completion"]
    
    # Text is the concatenation of prompt and completion
    assert ex["text"] == f"{ex['prompt']}{ex['completion']}"
    
    # Fingerprint is deterministic
    expected_fp = generate_fingerprint(mem["task"], mem["broken_code"], mem["error_message"])
    assert ex["fingerprint"] == expected_fp


# -------------------------------------------------------------
# 2. Buffer Threshold & Continual Learning Strategy Tests
# -------------------------------------------------------------

def test_buffer_threshold_prevents_premature_training(tmp_path):
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
        for i in range(2)  # 2 memories, buffer is 4
    ]
    with open(mem_file, "w", encoding="utf-8") as f:
        json.dump(memories, f)

    res = run_training_pipeline(force=False, memory_file=mem_file)
    assert res["trained"] is False
    assert res["reason"] == "buffer_not_reached"
    assert res["new_memories"] == 2
    assert res["buffer_target"] == 4


# -------------------------------------------------------------
# 3. Adapter Hot-Reload & Versioning Tests
# -------------------------------------------------------------

def test_adapter_hot_reload_lifecycle():
    # Initially no adapter
    config.set("LORA_ENABLED", True)
    reload_model()
    
    import app.model as model_mod
    assert model_mod._loaded_adapter_id is None

    # Simulate adapter v1 creation
    os.makedirs(ACTIVE_ADAPTER_DIR, exist_ok=True)
    with open(os.path.join(ACTIVE_ADAPTER_DIR, "metadata.json"), "w") as f:
        json.dump({"adapter_id": "adapter_v1_1001", "version": 1, "status": "active"}, f)
    with open(os.path.join(ACTIVE_ADAPTER_DIR, "adapter_config.json"), "w") as f:
        json.dump({"peft_type": "LORA", "task_type": "CAUSAL_LM"}, f)
    with open(os.path.join(ACTIVE_ADAPTER_DIR, "adapter_model.safetensors"), "wb") as f:
        f.write(b"dummy_weights")

    # Mock PeftModel.from_pretrained to avoid heavy weight loading during hot-reload unit test
    with patch("peft.PeftModel.from_pretrained", return_value=MagicMock()):
        check_and_reload_adapter()
        m, _ = get_model()
        assert model_mod._loaded_adapter_id == "adapter_v1_1001"

        # Simulate adapter v2 promotion
        with open(os.path.join(ACTIVE_ADAPTER_DIR, "metadata.json"), "w") as f:
            json.dump({"adapter_id": "adapter_v2_1002", "version": 2, "status": "active"}, f)

        check_and_reload_adapter()
        m2, _ = get_model()
        assert model_mod._loaded_adapter_id == "adapter_v2_1002"

        # Simulate LORA_ENABLED=False disabling
        config.set("LORA_ENABLED", False)
        check_and_reload_adapter()
        assert model_mod._loaded_adapter_id is None


# -------------------------------------------------------------
# 4. Failure Handling & Transparency Tests
# -------------------------------------------------------------

def test_training_failure_preserves_state(tmp_path):
    mem_file = str(tmp_path / "test_mem.json")
    memories = [
        {
            "success": True,
            "task": f"Task {i}",
            "error_type": "AssertionError",
            "error_message": f"err_{i}",
            "broken_code": f"def g{i}(): pass",
            "successful_fix": f"def g{i}(): return {i}",
            "verification": {"syntax_passed": True, "safety_passed": True, "execution_passed": True, "tests_passed": True}
        }
        for i in range(5)
    ]
    with open(mem_file, "w", encoding="utf-8") as f:
        json.dump(memories, f)

    # Establish an initial active adapter
    initial_state = {
        "last_trained_count": 0,
        "adapter_version_counter": 1,
        "active_adapter_id": "adapter_v1_init",
        "is_training": False
    }
    save_training_state(initial_state)

    # Mock trainer.train to raise an exception
    with patch("transformers.Trainer.train", side_effect=RuntimeError("GPU OOM / Memory fault")):
        res = run_training_pipeline(force=True, memory_file=mem_file)
        assert res["trained"] is False
        assert res["success"] is False
        assert "GPU OOM / Memory fault" in res["error"]

    # Verify state was NOT advanced
    state_after = get_training_state()
    assert state_after["adapter_version_counter"] == 1
    assert state_after["active_adapter_id"] == "adapter_v1_init"

    # Verify failure was recorded in history
    assert os.path.exists(TRAINING_HISTORY_FILE)
    with open(TRAINING_HISTORY_FILE, "r") as f:
        hist = json.load(f)
    assert len(hist) >= 1
    assert hist[-1]["status"] == "failed"
    assert "GPU OOM" in hist[-1]["error"]


# -------------------------------------------------------------
# 5. Real End-to-End LoRA Training & Inference Validation
# -------------------------------------------------------------

def test_end_to_end_real_lora_training(tmp_path):
    mem_file = str(tmp_path / "real_mem.json")
    memories = [
        {
            "success": True,
            "task": "Fix concat function",
            "error_type": "AssertionError",
            "error_message": "A generated test case failed",
            "broken_code": "def concat(a: str, b: str) -> str:\n    return f'{a} {b}'",
            "successful_fix": "def concat(a: str, b: str) -> str:\n    return f'{a}{b}'",
            "tests": "assert concat('a', 'b') == 'ab'",
            "verification": {"syntax_passed": True, "safety_passed": True, "execution_passed": True, "tests_passed": True}
        }
    ]
    with open(mem_file, "w", encoding="utf-8") as f:
        json.dump(memories, f)

    config.set("LORA_ENABLED", True)
    config.set("LORA_EPOCHS", 1)
    config.set("LORA_LEARNING_RATE", 1e-4)

    # Execute REAL training cycle
    res = run_training_pipeline(force=True, memory_file=mem_file, experiment_id="TEST_REAL_TRAIN")
    assert res["trained"] is True, f"Training did not run: {res}"
    assert res["success"] is True, f"Training failed: {res}"
    assert res["version"] == 1
    adapter_id = res["adapter_id"]

    # Verify physical files on disk
    active_config = os.path.join(ACTIVE_ADAPTER_DIR, "adapter_config.json")
    active_meta = os.path.join(ACTIVE_ADAPTER_DIR, "metadata.json")
    assert os.path.exists(active_config), "Active adapter_config.json missing"
    assert os.path.exists(active_meta), "Active metadata.json missing"

    weights_st = os.path.join(ACTIVE_ADAPTER_DIR, "adapter_model.safetensors")
    weights_bin = os.path.join(ACTIVE_ADAPTER_DIR, "adapter_model.bin")
    has_weights = (os.path.exists(weights_st) and os.path.getsize(weights_st) > 0) or \
                  (os.path.exists(weights_bin) and os.path.getsize(weights_bin) > 0)
    assert has_weights, "Active adapter weights file missing or empty"

    # Verify hot-reload and real inference
    reload_model()
    check_and_reload_adapter()
    from app.model import get_model, generate_raw
    import app.model as model_mod
    get_model()
    assert model_mod._loaded_adapter_id == adapter_id, f"Loaded adapter {model_mod._loaded_adapter_id} != {adapter_id}"

    # Verify inference with trained adapter
    gen = generate_raw("def multiply(a, b):")
    assert isinstance(gen, str) and len(gen) > 0, "Model failed to generate with active adapter"

