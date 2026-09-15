import os
import json
import shutil
import time
from app.model import get_model, check_and_reload_adapter, _loaded_adapter_id, _model
from app.config import config

ACTIVE_DIR = "models/adapters/active"

def write_dummy_adapter(adapter_id):
    os.makedirs(ACTIVE_DIR, exist_ok=True)
    with open(os.path.join(ACTIVE_DIR, "metadata.json"), "w") as f:
        json.dump({"adapter_id": adapter_id}, f)
    # A tiny fake adapter config to satisfy peft loading
    with open(os.path.join(ACTIVE_DIR, "adapter_config.json"), "w") as f:
        json.dump({
            "peft_type": "LORA",
            "task_type": "CAUSAL_LM",
            "base_model_name_or_path": "Qwen/Qwen2.5-Coder-1.5B"
        }, f)
    with open(os.path.join(ACTIVE_DIR, "adapter_model.safetensors"), "w") as f:
        f.write("fake_weights")

print("--- TEST 1: LORA_ENABLED=False isolates adapter ---")
config.set("LORA_ENABLED", False)
model1, _ = get_model()
print(f"Loaded Adapter ID: {_loaded_adapter_id}")

print("\n--- TEST 2: LORA_ENABLED=True loads adapter ---")
config.set("LORA_ENABLED", True)
# It won't reload yet unless check_and_reload_adapter is called!
# Wait, get_model() will just return base model because _model is already set!
# Let's call check_and_reload_adapter() to detect the flag change.
check_and_reload_adapter()
if _model is None:
    print("Reload triggered successfully due to flag change.")
write_dummy_adapter("dummy_1")
# We will mock PeftModel.from_pretrained to avoid crashing on fake_weights
import peft
from unittest.mock import MagicMock
original_from_pretrained = peft.PeftModel.from_pretrained
peft.PeftModel.from_pretrained = MagicMock(return_value="PEFT_MOCK")

model2, _ = get_model()
print(f"Loaded Adapter ID: {_loaded_adapter_id}")
print(f"Model object: {model2}")

print("\n--- TEST 3 & 4: Simulate adapter replacement (Hot Reload) ---")
# Currently loaded dummy_1
write_dummy_adapter("dummy_2")
check_and_reload_adapter()
if _model is None:
    print("Task-boundary detected adapter change! _model invalidated.")
model3, _ = get_model()
print(f"Loaded Adapter ID: {_loaded_adapter_id}")

print("\n--- TEST 5: Unchanged identity -> no reload ---")
check_and_reload_adapter()
if _model is not None:
    print("Task-boundary ignored unchanged adapter.")

print("\n--- TEST 6: Mode Isolation ---")
config.set("LORA_ENABLED", False)
check_and_reload_adapter()
if _model is None:
    print("Task-boundary detected LORA disabled! _model invalidated.")
model4, _ = get_model()
print(f"Loaded Adapter ID: {_loaded_adapter_id}")
print(f"Model object is PEFT? {isinstance(model4, str) and model4 == 'PEFT_MOCK'}")

# Cleanup
peft.PeftModel.from_pretrained = original_from_pretrained
if os.path.exists(ACTIVE_DIR):
    shutil.rmtree(ACTIVE_DIR)
