import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "MEMORY_ENABLED": True,
    "STRATEGY_LEARNING_ENABLED": True,
    "LORA_ENABLED": True,
    "DIFFICULTY_ALLOCATION_ENABLED": True,
    "BENCHMARK_SEED": 42,
    "DETERMINISTIC_GENERATION": False,
    "LORA_BUFFER_SIZE": 4,
    "LORA_EPOCHS": 3,
    "LORA_LEARNING_RATE": 2e-4,
    "LORA_RANK": 8,
    "LORA_ALPHA": 16,
    "LORA_DROPOUT": 0.05,
    "LORA_REPLAY_SIZE": 4,
    "LORA_REPLAY_STRATEGY": "all",
    "LORA_CANARY_ENABLED": True,
    "LORA_CANARY_PASS_THRESHOLD": 1.0
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                self.config.update(json.load(f))

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value):
        self.config[key] = value
        self.save()

config = ConfigManager()
