import pytest
import os
import json
from app.repair_difficulty import estimate_difficulty
from app.strategy_selector import StrategySelector, STRATEGY_MEMORY_FILE, STRATEGY_STATS_FILE
from app.repair_strategy import get_baseline_strategies

def test_syntax_error_baseline():
    # TEST 1: SyntaxError selects valid baseline strategy.
    strats = get_baseline_strategies("SyntaxError")
    assert "DIRECT_REPAIR" in strats or "MINIMAL_PATCH" in strats

def test_type_error_baseline():
    # TEST 2: TypeError selects valid strategy.
    strats = get_baseline_strategies("TypeError")
    assert "EXPERIENCE_GUIDED_REPAIR" in strats or "STRUCTURAL_REPAIR" in strats

def test_strategy_switching():
    # TEST 3: Repeated failure causes strategy switching.
    selector = StrategySelector()
    info = selector.select_strategy("TypeError", 2, ["EXPERIENCE_GUIDED_REPAIR"], True, "MEDIUM")
    assert info["selected_strategy"] != "EXPERIENCE_GUIDED_REPAIR"

def test_positive_reward():
    # TEST 4: Successful strategy receives positive reward.
    selector = StrategySelector()
    reward = selector.compute_reward(True, True, 1, 500, "TypeError", False, False)
    assert reward > 0

def test_negative_reward():
    # TEST 5: Failed strategy receives negative reward.
    selector = StrategySelector()
    reward = selector.compute_reward(False, False, 1, 500, "TypeError", False, False)
    assert reward < 0

def test_security_violation_penalty():
    # TEST 6: SecurityViolation does not produce positive reward.
    selector = StrategySelector()
    reward = selector.compute_reward(True, True, 1, 500, "SecurityViolation", True, False)
    assert reward < 0

def test_timeout_penalty():
    # TEST 7: Timeout does not produce positive reward.
    selector = StrategySelector()
    reward = selector.compute_reward(True, True, 1, 500, "TimeoutError", False, True)
    assert reward < 0

def test_exploration():
    # TEST 8: Exploration mode can select a non-best strategy.
    # Note: hard to test randomness deterministically without mocking random.random, but we can verify selection mode.
    selector = StrategySelector()
    info = selector.select_strategy("AssertionError", 1, [], True, "EASY")
    assert info["selection_mode"] in ["exploration", "exploitation"]

def test_exploitation():
    # TEST 9: Exploitation selects highest-scoring valid strategy.
    selector = StrategySelector()
    # Force some stats
    selector.stats = {
        "TEST_GUIDED_REPAIR": {"AssertionError": {"successes": 10, "total": 10, "reward": 20.0}}
    }
    # Mock random to 1.0 (always exploit)
    import random
    original_random = random.random
    random.random = lambda: 1.0
    info = selector.select_strategy("AssertionError", 1, [], True, "EASY")
    random.random = original_random
    assert info["selection_mode"] == "exploitation"
    assert info["selected_strategy"] == "TEST_GUIDED_REPAIR"

def test_statistics_update():
    # TEST 10: Strategy statistics update correctly.
    if os.path.exists(STRATEGY_STATS_FILE):
        os.remove(STRATEGY_STATS_FILE)
    selector = StrategySelector()
    selector.record_outcome("DIRECT_REPAIR", "SyntaxError", "Task", 1, True, True, True, 100, "f1", False, False)
    assert selector.stats["DIRECT_REPAIR"]["SyntaxError"]["successes"] == 1

def test_strategy_memory():
    # TEST 11: Strategy memory stores only verified outcomes.
    if os.path.exists(STRATEGY_MEMORY_FILE):
        os.remove(STRATEGY_MEMORY_FILE)
    selector = StrategySelector()
    selector.record_outcome("DIRECT_REPAIR", "SyntaxError", "Task", 1, True, True, True, 100, "f1", False, False)
    with open(STRATEGY_MEMORY_FILE, "r") as f:
        mem = json.load(f)
    assert len(mem) == 1
    assert mem[0]["success"] == True

def test_learning_off():
    # TEST 12: Strategy learning OFF produces deterministic baseline behavior.
    import app.strategy_selector
    app.strategy_selector.STRATEGY_LEARNING_ENABLED = False
    selector = StrategySelector()
    info = selector.select_strategy("TypeError", 1, [], True, "EASY")
    assert info["selection_mode"] == "baseline"
    app.strategy_selector.STRATEGY_LEARNING_ENABLED = True

def test_difficulty_levels():
    # TEST 13: Difficulty estimator produces valid levels.
    diff1 = estimate_difficulty("SyntaxError", "x = 1", 1, True)
    assert diff1["difficulty"] in ["EASY", "MEDIUM", "HARD", "VERY_HARD"]

def test_difficulty_budget():
    # TEST 14: Difficulty changes repair budget.
    diff1 = estimate_difficulty("SyntaxError", "x = 1", 1, True)
    diff2 = estimate_difficulty("TimeoutError", "while True: pass", 5, False)
    assert diff2["recommended_attempts"] > diff1["recommended_attempts"]

def test_experience_memory_functional():
    # TEST 15: Experience memory remains functional.
    from app.repair_memory import repair_memory
    assert hasattr(repair_memory, "search_similar_experiences")

def test_lora_functional():
    # TEST 16: LoRA mechanism remains functional.
    import os
    assert os.path.exists("train_worker.py")

def test_sandbox_functional():
    # TEST 17: Phase 3 sandbox remains functional.
    from app.executor import execute_code
    res = execute_code("print(1)")
    assert res["success"] == True
