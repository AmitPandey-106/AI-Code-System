import json
import os
import random
import time
import math
from pathlib import Path
from filelock import FileLock
from app.file_transaction import atomic_write
from typing import Dict, List, Tuple, Optional
from app.repair_strategy import STRATEGIES, get_baseline_strategies

STRATEGY_STATS_FILE = "data/strategy_stats.json"
STRATEGY_MEMORY_FILE = "data/strategy_memory.json"
STRATEGY_EXPLORATION_RATE = 0.20

from app.config import config

class StrategySelector:
    def __init__(self, storage_dir: Optional[str] = None, enabled: Optional[bool] = None):
        self.storage_dir = storage_dir
        self.enabled = enabled
        if storage_dir:
            self.stats_file = os.path.join(storage_dir, "strategy_stats.json")
            self.memory_file = os.path.join(storage_dir, "strategy_memory.json")
        else:
            self.stats_file = STRATEGY_STATS_FILE
            self.memory_file = STRATEGY_MEMORY_FILE
        self.warnings = []
        self.stats = self._load_stats() if self.is_enabled() else {}

    def is_enabled(self) -> bool:
        if self.enabled is not None:
            return self.enabled
        if "LITECODER_STRATEGY_ENABLED" in os.environ:
            return os.environ["LITECODER_STRATEGY_ENABLED"].lower() in ("true", "1")
        return bool(config.get("STRATEGY_LEARNING_ENABLED", False))

    def _load_stats(self) -> dict:
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        raise ValueError("incompatible strategy schema")
                    for strategy, errors in data.items():
                        if strategy not in STRATEGIES or not isinstance(errors, dict):
                            raise ValueError("invalid strategy record")
                        for values in errors.values():
                            if not isinstance(values, dict) or any(not isinstance(values.get(k), (int, float)) or not math.isfinite(values[k]) or values[k] < 0 for k in ("total_attempts", "successes", "failures")) or not isinstance(values.get("reward"), (int, float)) or not math.isfinite(values["reward"]):
                                raise ValueError("invalid strategy counters")
                    return data
            except (ValueError, OSError) as exc:
                self.warnings.append(f"Strategy load failed: {exc}")
                return {}
        return {}
        
    def _save_stats(self):
        parent_dir = os.path.dirname(self.stats_file)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        atomic_write(Path(self.stats_file), json.dumps(self.stats, indent=2).encode(), 0o600)
            
    def _save_memory(self, record: dict):
        parent_dir = os.path.dirname(self.memory_file)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        memories = []
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    memories = json.load(f)
            except Exception:
                memories = []
        if not isinstance(memories, list):
            memories = []
        if any(m.get("feedback_id") == record["feedback_id"] and m.get("attempt_number") == record["attempt_number"] and m.get("strategy_id") == record["strategy_id"] for m in memories if isinstance(m, dict)):
            return False
        memories.append(record)
        atomic_write(Path(self.memory_file), json.dumps(memories, indent=2).encode(), 0o600)
        return True

    def select_strategy(self, error_type: str, attempt_number: int, previous_strategies: List[str], memory_available: bool, difficulty: str) -> dict:
        """Selects a strategy for the current attempt."""
        
        candidates = get_baseline_strategies(error_type)
        
        # Add fallback
        if not candidates:
            candidates = ["DIRECT_REPAIR", "EXPERIENCE_GUIDED_REPAIR"]
            
        if not memory_available and "EXPERIENCE_GUIDED_REPAIR" in candidates:
            candidates.remove("EXPERIENCE_GUIDED_REPAIR")
            
        if attempt_number > 2 and "ALTERNATIVE_REPAIR" not in candidates:
            candidates.append("ALTERNATIVE_REPAIR")
            
        # Avoid immediate repetition if possible
        available_candidates = [c for c in candidates if c not in previous_strategies]
        if not available_candidates:
            available_candidates = candidates # If all tried, reuse
            
        if not self.is_enabled():
            selected = available_candidates[0]
            return {
                "selected_strategy": selected,
                "confidence": 1.0,
                "reason": f"Baseline mapping for {error_type} (Learning disabled).",
                "alternatives": candidates,
                "selection_mode": "baseline"
            }
            
        # Strategy Learning Mode
        best_strategy = None
        best_score = -999.0
        
        # Calculate scores
        for strat in available_candidates:
            stats = self.stats.get(strat, {}).get(error_type, {"successes": 0, "total_attempts": 0, "reward": 0.0})
            if stats["total_attempts"] > 0:
                score = stats["reward"] / stats["total_attempts"]
            else:
                score = 0.0 # Prioritize unexplored? Let's leave at 0.0
            
            if score > best_score:
                best_score = score
                best_strategy = strat
                
        # Setup RNG
        if config.get("DETERMINISTIC_GENERATION", False):
            seed_components = [
                config.get("BENCHMARK_SEED", 42),
                error_type,
                attempt_number,
                len(previous_strategies),
                tuple(sorted(available_candidates))
            ]
            seed_str = "|".join(map(str, seed_components))
            rng = random.Random(seed_str)
        else:
            rng = random

        # Epsilon greedy exploration
        is_exploration = False
        if rng.random() < STRATEGY_EXPLORATION_RATE or best_strategy is None:
            is_exploration = True
            selected = rng.choice(available_candidates)
            confidence = 0.0
            reason = "Exploration mode selected a random plausible strategy."
        else:
            selected = best_strategy
            confidence = best_score
            reason = f"Exploitation mode selected historically best strategy for {error_type}."
            
        return {
            "selected_strategy": selected,
            "confidence": round(confidence, 2),
            "reason": reason,
            "alternatives": candidates,
            "selection_mode": "exploration" if is_exploration else "exploitation"
        }

    def compute_reward(self, success: bool, tests_passed: bool, attempt_number: int, duration_ms: int, error_type: str, security_violation: bool, timeout: bool) -> float:
        """Computes the reward for a given strategy application."""
        if security_violation:
            return -5.0
        if timeout:
            return -3.0
            
        if not success:
            return -1.0
            
        # Success bonuses
        reward = 2.0
        if tests_passed:
            reward += 1.0
        if attempt_number == 1:
            reward += 1.0 # First shot bonus
        
        # Penalty for being slow
        if duration_ms > 2000:
            reward -= 0.5
            
        return reward
        
    def record_outcome(self, strategy_id: str, error_type: str, task: str, attempt_number: int, success: bool, tests_passed: bool, execution_passed: bool, duration_ms: int, feedback_id: str, security_violation: bool, timeout: bool):
        """Records the outcome and updates policy statistics."""
        if not self.is_enabled():
            return False
        if strategy_id not in STRATEGIES or attempt_number < 1 or duration_ms < 0:
            return False
        if success and (not tests_passed or not execution_passed or security_violation or timeout):
            return False
        Path(self.stats_file).parent.mkdir(parents=True, exist_ok=True)
        with FileLock(self.stats_file + ".lock", timeout=10):
            self.stats = self._load_stats()
            
            reward = self.compute_reward(success, tests_passed, attempt_number, duration_ms, error_type, security_violation, timeout)
        
            # Update Memory
            record = {
                "strategy_id": strategy_id,
                "error_type": error_type,
                "task_category": "general",
                "attempt_number": attempt_number,
                "success": success,
                "tests_passed": tests_passed,
                "execution_passed": execution_passed,
                "duration_ms": duration_ms,
                "reward": reward,
                "timestamp": time.time(),
                "feedback_id": feedback_id
            }
            if not self._save_memory(record):
                return False
        
            # Update Policy
            if strategy_id not in self.stats:
                self.stats[strategy_id] = {}
            
            if error_type not in self.stats[strategy_id]:
                self.stats[strategy_id][error_type] = {
                    "total_attempts": 0,
                    "successes": 0,
                    "failures": 0,
                    "reward": 0.0,
                    "average_attempts": 0.0,
                    "average_runtime_ms": 0.0
                }
            
            st = self.stats[strategy_id][error_type]
            st["total_attempts"] += 1
            if success:
                st["successes"] += 1
            else:
                st["failures"] += 1
            
            st["reward"] += reward
            st["average_runtime_ms"] = ((st["average_runtime_ms"] * (st["total_attempts"] - 1)) + duration_ms) / max(1, st["total_attempts"])
            st["average_attempts"] = ((st["average_attempts"] * (st["total_attempts"] - 1)) + attempt_number) / max(1, st["total_attempts"])
        
            self._save_stats()
        
            return True

    def reset(self):
        """Clears in-memory statistics to ensure isolation between experiments."""
        self.stats = {}
        self._save_stats()
        
strategy_selector = StrategySelector()
