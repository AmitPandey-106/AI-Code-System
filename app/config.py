import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "MEMORY_ENABLED": True,
    "STRATEGY_LEARNING_ENABLED": True,
    "LORA_ENABLED": True,
    "DIFFICULTY_ALLOCATION_ENABLED": True,
    "BENCHMARK_SEED": 42,
    "DETERMINISTIC_GENERATION": False
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
