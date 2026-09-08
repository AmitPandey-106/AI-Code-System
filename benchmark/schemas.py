from typing import List, Dict, Optional, Any
from pydantic import BaseModel

class BenchmarkTask(BaseModel):
    task_id: str
    category: str
    difficulty: str
    prompt: str
    reference_code: Optional[str] = None
    broken_code: Optional[str] = None
    fault: Optional[Dict[str, Any]] = None
    complexity: Optional[Dict[str, int]] = None
    expected_tests: List[str] = []
    source: str = "synthetic"
    version: str = "1.0"

class BenchmarkResult(BaseModel):
    experiment_id: str
    task_id: str
    mode: str
    success: bool
    error_type: Optional[str] = None
    attempts: int
    repair_effort: int
    execution_time_ms: int
    strategy_history: List[Dict[str, Any]]
    difficulty: Dict[str, Any]
    verification: Dict[str, Any]
    memory_used: bool
    lora_enabled: bool
    adapter_version: Optional[str] = None
    timestamp: float
