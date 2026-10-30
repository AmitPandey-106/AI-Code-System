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

    # Machine-readable outcome classification:
    #   model_success       – model generated code that passed all verification
    #   model_failure       – model generated code that failed after max retries
    #   infrastructure_failure – an exception in the runner/infra, not a model decision
    #   unresolved          – outcome cannot be determined (legacy/incomplete records)
    status: Optional[str] = None

    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_stage: Optional[str] = None       # generation | execution | testing | verification | checkpoint | runner
    error_traceback: Optional[str] = None
    error_category: Optional[str] = None   # runner | model | execution | verification | serialization

    attempts: Optional[int] = None
    repair_effort: Optional[int] = None
    execution_time_ms: int
    strategy_history: List[Dict[str, Any]] = []
    difficulty: Dict[str, Any] = {}
    verification: Optional[Dict[str, Any]] = None
    memory_used: Optional[bool] = None
    lora_enabled: bool
    adapter_version: Optional[str] = None
    task_index: Optional[int] = None
    active_adapter_id: Optional[str] = None
    training_triggered: Optional[bool] = False
    training_cycle_id: Optional[str] = None
    training_status: Optional[str] = None
    final_status: Optional[str] = None
    timestamp: float
