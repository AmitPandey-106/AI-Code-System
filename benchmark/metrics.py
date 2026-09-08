from typing import List
from benchmark.schemas import BenchmarkResult
import numpy as np

def calculate_metrics(results: List[BenchmarkResult]) -> dict:
    if not results:
        return {}

    total = len(results)
    successes = [r for r in results if r.success]
    success_count = len(successes)
    
    attempts = [r.attempts for r in results]
    repair_efforts = [r.repair_effort for r in results]
    exec_times = [r.execution_time_ms for r in results]
    
    # Error type breakdown
    error_types = {}
    for r in results:
        etype = r.error_type or "NoError"
        if etype not in error_types:
            error_types[etype] = {"total": 0, "success": 0}
        error_types[etype]["total"] += 1
        if r.success:
            error_types[etype]["success"] += 1

    # Strategy breakdown
    strategies = {}
    for r in results:
        for strat in r.strategy_history:
            sid = strat.get("strategy_id")
            if not sid: continue
            if sid not in strategies:
                strategies[sid] = {"total": 0, "success": 0}
            strategies[sid]["total"] += 1
            if strat.get("success"):
                strategies[sid]["success"] += 1

    metrics = {
        "total_tasks": total,
        "success_rate": success_count / total,
        "average_attempts": sum(attempts) / total,
        "median_attempts": float(np.median(attempts)),
        "average_repair_effort": sum(repair_efforts) / total,
        "median_repair_effort": float(np.median(repair_efforts)),
        "average_execution_time_ms": sum(exec_times) / total,
        "median_execution_time_ms": float(np.median(exec_times)),
        "error_type_performance": {
            k: v["success"] / v["total"] for k, v in error_types.items()
        },
        "strategy_performance": {
            k: v["success"] / v["total"] for k, v in strategies.items()
        },
        "memory_utilization_rate": len([r for r in results if r.memory_used]) / total
    }
    
    return metrics
