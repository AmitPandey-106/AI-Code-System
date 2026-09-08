import json
import os
import random
import time
from typing import Dict, List, Tuple
from app.repair_strategy import STRATEGIES, get_baseline_strategies

STRATEGY_STATS_FILE = "data/strategy_stats.json"
STRATEGY_MEMORY_FILE = "data/strategy_memory.json"
STRATEGY_EXPLORATION_RATE = 0.20

from app.config import config

class StrategySelector:
    def __init__(self):
        self.stats = self._load_stats()
        
    def _load_stats(self) -> dict:
        if os.path.exists(STRATEGY_STATS_FILE):
            with open(STRATEGY_STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
        
    def _save_stats(self):
        os.makedirs(os.path.dirname(STRATEGY_STATS_FILE), exist_ok=True)
        with open(STRATEGY_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=4)
            
    def _save_memory(self, record: dict):
        os.makedirs(os.path.dirname(STRATEGY_MEMORY_FILE), exist_ok=True)
        memories = []
        if os.path.exists(STRATEGY_MEMORY_FILE):
            with open(STRATEGY_MEMORY_FILE, "r", encoding="utf-8") as f:
                memories = json.load(f)
        memories.append(record)
        with open(STRATEGY_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=4)

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
            
        if not config.get("STRATEGY_LEARNING_ENABLED"):
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
            stats = self.stats.get(strat, {}).get(error_type, {"successes": 0, "total": 0, "reward": 0.0})
            if stats["total"] > 0:
                score = stats["reward"] / stats["total"]
            else:
                score = 0.0 # Prioritize unexplored? Let's leave at 0.0
            
            if score > best_score:
                best_score = score
                best_strategy = strat
                
        # Epsilon greedy exploration
        is_exploration = False
        if random.random() < STRATEGY_EXPLORATION_RATE or best_strategy is None:
            is_exploration = True
            selected = random.choice(available_candidates)
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
        if not config.get("STRATEGY_LEARNING_ENABLED"):
            return
            
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
        self._save_memory(record)
        
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
        
    def reset(self):
        """Clears in-memory statistics to ensure isolation between experiments."""
        self.stats = {}
        self._save_stats()
        
strategy_selector = StrategySelector()
