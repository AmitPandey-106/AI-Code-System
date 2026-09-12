import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from unittest.mock import MagicMock
sys.modules['app.main'] = MagicMock()
sys.modules['app.model'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()

import json
import pytest
import shutil
import tempfile
import time
import hashlib
from benchmark.schemas import BenchmarkResult
from benchmark.runner import get_dataset_hash, save_experiment_manifest
from benchmark.metrics import calculate_metrics

def test_dataset_hash(tmp_path):
    dataset_file = tmp_path / "mock_dataset.json"
    content = b"[{'task_id': '1'}]"
    dataset_file.write_bytes(content)
    
    expected_hash = hashlib.sha256(content).hexdigest()
    actual_hash = get_dataset_hash(str(dataset_file))
    
    assert actual_hash == expected_hash

def test_dataset_hash_missing():
    assert get_dataset_hash("nonexistent_file.json") == ""

def test_metrics_denominator():
    # 2 successful, 1 failure, 1 infra error. Dataset size = 5 (1 unexecuted)
    results = [
        BenchmarkResult(experiment_id="E", task_id="1", mode="A", success=True, attempts=1, execution_time_ms=10, lora_enabled=False, timestamp=0.0),
        BenchmarkResult(experiment_id="E", task_id="2", mode="A", success=True, attempts=1, execution_time_ms=10, lora_enabled=False, timestamp=0.0),
        BenchmarkResult(experiment_id="E", task_id="3", mode="A", success=False, attempts=5, execution_time_ms=50, lora_enabled=False, timestamp=0.0),
        BenchmarkResult(experiment_id="E", task_id="4", mode="A", success=None, attempts=None, error_type="INFRASTRUCTURE_ERROR", execution_time_ms=5, lora_enabled=False, timestamp=0.0),
    ]
    metrics = calculate_metrics(results, 5)
    
    assert metrics["dataset_size"] == 5
    assert metrics["completed_tasks"] == 4
    assert metrics["unexecuted_tasks"] == 1
    assert metrics["successful_repairs"] == 2
    assert metrics["repair_failures"] == 1
    assert metrics["infrastructure_errors"] == 1
    assert metrics["success_rate"] == 2 / 5
    assert metrics["average_attempts"] == (1+1+5)/3
    assert metrics["is_complete_run"] is False

def test_metrics_complete_run():
    results = [
        BenchmarkResult(experiment_id="E", task_id="1", mode="A", success=True, attempts=1, execution_time_ms=10, lora_enabled=False, timestamp=0.0),
        BenchmarkResult(experiment_id="E", task_id="2", mode="A", success=False, attempts=5, execution_time_ms=10, lora_enabled=False, timestamp=0.0),
    ]
    metrics = calculate_metrics(results, 2)
    assert metrics["is_complete_run"] is True
    assert metrics["success_rate"] == 1 / 2

def test_save_manifest(tmp_path):
    exp_dir = tmp_path / "exp_dir"
    save_experiment_manifest(str(exp_dir), "MODE_A", "mock_dataset.json", 100, "hash123")
    
    manifest_path = exp_dir / "experiment_manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r") as f:
        data = json.load(f)
        
    assert data["mode"] == "MODE_A"
    assert data["dataset_sha256"] == "hash123"
    assert data["task_count"] == 100
    assert "hardware" in data
    assert data["hardware"]["os"] is not None

def test_schema_optional_fields():
    # Should not throw validation error when missing attempts and success is None
    res = BenchmarkResult(
        experiment_id="E",
        task_id="T001",
        mode="MODE_A",
        success=None,
        attempts=None,
        error_type="SomeError",
        execution_time_ms=150,
        lora_enabled=False,
        timestamp=time.time()
    )
    assert res.success is None
    assert res.attempts is None
