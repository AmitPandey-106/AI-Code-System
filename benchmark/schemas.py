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
    success: Optional[bool] = None
    error_type: Optional[str] = None
    attempts: Optional[int] = None
    repair_effort: Optional[int] = None
    execution_time_ms: int
    strategy_history: List[Dict[str, Any]] = []
    difficulty: Dict[str, Any] = {}
    verification: Optional[Dict[str, Any]] = None
    memory_used: Optional[bool] = None
    lora_enabled: bool
    adapter_version: Optional[str] = None
    timestamp: float
