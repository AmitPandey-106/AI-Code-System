from typing import List
from benchmark.schemas import BenchmarkResult
import numpy as np

def calculate_metrics(results: List[BenchmarkResult], dataset_size: int) -> dict:
    if not results and dataset_size == 0:
        return {}

    completed_tasks = len(results)
    unexecuted_tasks = dataset_size - completed_tasks
    
    # success is True (successful repair), False (repair failure), or None (infrastructure error)
    successes = [r for r in results if r.success is True]
    failures = [r for r in results if r.success is False]
    infra_errors = [r for r in results if r.success is None]
    
    successful_repairs = len(successes)
    repair_failures = len(failures)
    infrastructure_errors = len(infra_errors)
    
    valid_attempts = [r.attempts for r in results if r.attempts is not None]
    valid_repair_efforts = [r.repair_effort for r in results if r.repair_effort is not None]
    valid_exec_times = [r.execution_time_ms for r in results if r.execution_time_ms is not None]
    
    # Error type breakdown
    error_types = {}
    for r in results:
        etype = r.error_type or "NoError"
        if etype not in error_types:
            error_types[etype] = {"total": 0, "success": 0}
        error_types[etype]["total"] += 1
        if r.success is True:
            error_types[etype]["success"] += 1

    # Strategy breakdown
    strategies = {}
    for r in results:
        for strat in r.strategy_history:
            sid = strat.get("selected_strategy")
            if not sid: continue
            if sid not in strategies:
                strategies[sid] = {"total": 0, "success": 0}
            strategies[sid]["total"] += 1
            if strat.get("success"):
                strategies[sid]["success"] += 1

    metrics = {
        "dataset_size": dataset_size,
        "completed_tasks": completed_tasks,
        "unexecuted_tasks": unexecuted_tasks,
        "successful_repairs": successful_repairs,
        "repair_failures": repair_failures,
        "infrastructure_errors": infrastructure_errors,
        "success_rate": successful_repairs / dataset_size if dataset_size > 0 else 0,
        "is_complete_run": unexecuted_tasks == 0,
        "average_attempts": sum(valid_attempts) / len(valid_attempts) if valid_attempts else 0,
        "median_attempts": float(np.median(valid_attempts)) if valid_attempts else 0.0,
        "average_repair_effort": sum(valid_repair_efforts) / len(valid_repair_efforts) if valid_repair_efforts else 0,
        "median_repair_effort": float(np.median(valid_repair_efforts)) if valid_repair_efforts else 0.0,
        "average_execution_time_ms": sum(valid_exec_times) / len(valid_exec_times) if valid_exec_times else 0,
        "median_execution_time_ms": float(np.median(valid_exec_times)) if valid_exec_times else 0.0,
        "error_type_performance": {
            k: v["success"] / v["total"] if v["total"] > 0 else 0 for k, v in error_types.items()
        },
        "strategy_performance": {
            k: v["success"] / v["total"] if v["total"] > 0 else 0 for k, v in strategies.items()
        },
        "memory_utilization_rate": len([r for r in results if r.memory_used]) / completed_tasks if completed_tasks > 0 else 0
    }
    
    return metrics
