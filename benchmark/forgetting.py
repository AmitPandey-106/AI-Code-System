from typing import List, Dict
from benchmark.schemas import BenchmarkResult

def evaluate_capability_retention(base_results: List[BenchmarkResult], adapter_results: List[BenchmarkResult]) -> dict:
    """
    Measures Capability Degradation by comparing anchor set execution 
    between the base model and an adapter model.
    """
    base_map = {r.task_id: r for r in base_results}
    adapter_map = {r.task_id: r for r in adapter_results}
    
    degradations = 0
    improvements = 0
    
    for task_id, base_res in base_map.items():
        if task_id in adapter_map:
            ad_res = adapter_map[task_id]
            if base_res.success and not ad_res.success:
                degradations += 1
            elif not base_res.success and ad_res.success:
                improvements += 1
                
    total = len(base_map)
    if total == 0:
        return {}
        
    return {
        "anchor_tasks_evaluated": total,
        "degraded_count": degradations,
        "improved_count": improvements,
        "degradation_rate": degradations / total,
        "improvement_rate": improvements / total
    }
