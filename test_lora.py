from app.model import get_model, generate_raw
from app.config import config
import os

print("1. Loading model...")
model, tokenizer = get_model()
print(f"Is PEFT: {hasattr(model, 'disable_adapter')}")

print("\n2. Testing LORA_ENABLED=False...")
config.set("LORA_ENABLED", False)
try:
    generate_raw("def add(a, b):")
    print("Generation with LORA_ENABLED=False succeeded.")
except Exception as e:
    print(f"Failed: {e}")

print("\n3. Testing Hot Reload Mechanism...")
import app.model
app.model._model = None # Simulating what we need
model2, _ = get_model()
print(f"Model ID 1: {id(model)}")
print(f"Model ID 2: {id(model2)}")
