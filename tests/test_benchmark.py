import pytest
import os
from benchmark.dataset import load_dataset
from benchmark.ablation import apply_ablation_mode
from benchmark.metrics import calculate_metrics
from benchmark.schemas import BenchmarkResult
from app.config import config

def test_dataset_loads():
    tasks = load_dataset()
    assert len(tasks) > 0
    assert tasks[0].task_id == "T001"

def test_ablation_configuration():
    apply_ablation_mode("MODE_A")
    assert not config.get("MEMORY_ENABLED")
    assert not config.get("STRATEGY_LEARNING_ENABLED")
    
    apply_ablation_mode("MODE_F")
    assert config.get("MEMORY_ENABLED")
    assert config.get("STRATEGY_LEARNING_ENABLED")

def test_metrics_calculation():
    results = [
        BenchmarkResult(
            experiment_id="test", task_id="1", mode="A", success=True, 
            error_type="SyntaxError", attempts=2, repair_effort=2, 
            execution_time_ms=1000, strategy_history=[{"strategy_id": "DIRECT_REPAIR", "success": True}], 
            difficulty={}, verification={}, memory_used=False, lora_enabled=False, timestamp=0.0
        ),
        BenchmarkResult(
            experiment_id="test", task_id="2", mode="A", success=False, 
            error_type="SyntaxError", attempts=5, repair_effort=5, 
            execution_time_ms=2000, strategy_history=[], 
            difficulty={}, verification={}, memory_used=False, lora_enabled=False, timestamp=0.0
        )
    ]
    metrics = calculate_metrics(results)
    assert metrics["success_rate"] == 0.5
    assert metrics["average_attempts"] == 3.5
    assert metrics["error_type_performance"]["SyntaxError"] == 0.5
    assert metrics["strategy_performance"]["DIRECT_REPAIR"] == 1.0

def test_registry_persists():
    from benchmark.reporter import save_report
    save_report("TEST_EXP", [])
    assert os.path.exists("experiments/TEST_EXP/report.md")
