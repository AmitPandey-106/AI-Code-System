import os
import json
import shutil
from benchmark.runner import reset_state
from app.config import config
from app.model import get_model, _model, _loaded_adapter_id, reload_model

def setup_test():
    # Make sure we have a clean test env
    if not os.path.exists("models/adapters"):
        os.makedirs("models/adapters")

def mock_publish_adapter(adapter_id="test_adapter_123"):
    active_path = "models/adapters/active"
    if os.path.exists(active_path):
        shutil.rmtree(active_path)
    os.makedirs(active_path, exist_ok=True)
    with open(os.path.join(active_path, "metadata.json"), "w") as f:
        json.dump({"adapter_id": adapter_id}, f)
    # mock the model directory to be valid for peft loading
    with open(os.path.join(active_path, "adapter_config.json"), "w") as f:
        json.dump({}, f)

def test_isolation():
    setup_test()
    
    # 1. Start F1
    print("--- Starting Experiment F1 ---")
    config.set("LORA_ENABLED", True)
    reset_state()
    model, tok = get_model()
    # It should not have any adapter loaded initially
    assert _loaded_adapter_id in [None, "legacy"], f"F1 started with adapter {_loaded_adapter_id}!"
    print(f"F1 Initial Adapter: {_loaded_adapter_id} (Expected None/legacy)")
    
    # Simulate F1 publishing an adapter
    print("Simulating F1 publishing an adapter...")
    mock_publish_adapter("F1_trained_adapter")
    
    # Force reload via check_and_reload_adapter (simulating task boundary)
    from app.model import check_and_reload_adapter
    check_and_reload_adapter()
    
    model, tok = get_model()
    import app.model
    assert app.model._loaded_adapter_id == "F1_trained_adapter", f"Expected F1_trained_adapter, got {app.model._loaded_adapter_id}"
    print(f"F1 After Training Adapter: {app.model._loaded_adapter_id}")

    # 2. Start F2
    print("\n--- Starting Experiment F2 ---")
    config.set("LORA_ENABLED", True)
    reset_state()
    model, tok = get_model()
    import app.model
    assert app.model._loaded_adapter_id in [None, "legacy"], f"F2 started with adapter {app.model._loaded_adapter_id} leaked from F1!"
    print(f"F2 Initial Adapter: {app.model._loaded_adapter_id} (Expected None/legacy - Leak Prevented!)")

    # 3. Simulate F2 publishing an adapter
    print("Simulating F2 publishing an adapter...")
    mock_publish_adapter("F2_trained_adapter")
    check_and_reload_adapter()
    model, tok = get_model()
    import app.model
    assert app.model._loaded_adapter_id == "F2_trained_adapter", f"Expected F2_trained_adapter, got {app.model._loaded_adapter_id}"

    # 4. Start MODE A (LORA_ENABLED=False)
    print("\n--- Starting Experiment Mode A (after F2) ---")
    config.set("LORA_ENABLED", False)
    reset_state()
    model, tok = get_model()
    import app.model
    assert app.model._loaded_adapter_id is None, f"Mode A started with adapter {app.model._loaded_adapter_id}!"
    print(f"Mode A Initial Adapter: {app.model._loaded_adapter_id} (Expected None)")

    print("\nALL ISOLATION TESTS PASSED!")

if __name__ == "__main__":
    # We must mock PeftModel.from_pretrained to avoid actually loading model weights during tests
    from unittest.mock import patch, MagicMock
    with patch("app.model.AutoModelForCausalLM.from_pretrained", return_value=MagicMock()), \
         patch("app.model.AutoTokenizer.from_pretrained", return_value=MagicMock()), \
         patch("app.model.PeftModel.from_pretrained", return_value=MagicMock()):
        test_isolation()
