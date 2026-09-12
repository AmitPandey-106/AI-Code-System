import json
import os
from typing import List
from benchmark.schemas import BenchmarkResult
from benchmark.metrics import calculate_metrics

def save_report(experiment_id: str, results: List[BenchmarkResult], dataset_size: int):
    out_dir = f"experiments/{experiment_id}"
    os.makedirs(out_dir, exist_ok=True)
    
    # Save raw results
    raw_path = f"{out_dir}/results.json"
    with open(raw_path, "w") as f:
        json.dump([r.dict() for r in results], f, indent=4)
        
    metrics = calculate_metrics(results, dataset_size)
    met_path = f"{out_dir}/metrics.json"
    with open(met_path, "w") as f:
        json.dump(metrics, f, indent=4)
        
    md_path = f"{out_dir}/report.md"
    with open(md_path, "w") as f:
        f.write(f"# Benchmark Report: {experiment_id}\n\n")
        f.write("## Overall Performance\n")
        f.write(f"- Dataset Size: {metrics.get('dataset_size')}\n")
        f.write(f"- Completed Tasks: {metrics.get('completed_tasks')}\n")
        f.write(f"- Unexecuted Tasks: {metrics.get('unexecuted_tasks')}\n")
        f.write(f"- Successful Repairs: {metrics.get('successful_repairs')}\n")
        f.write(f"- Repair Failures: {metrics.get('repair_failures')}\n")
        f.write(f"- Infrastructure Errors: {metrics.get('infrastructure_errors')}\n")
        f.write(f"- Success Rate: {metrics.get('success_rate', 0)*100:.2f}%\n")
        f.write(f"- Avg Attempts: {metrics.get('average_attempts', 0):.2f}\n")
        f.write(f"- Median Attempts: {metrics.get('median_attempts', 0)}\n")
        f.write(f"- Avg Time (ms): {metrics.get('average_execution_time_ms', 0):.2f}\n")
        
        f.write("\n## Error Type Performance\n")
        for etype, rate in metrics.get('error_type_performance', {}).items():
            f.write(f"- {etype}: {rate*100:.2f}%\n")
            
        f.write("\n## Strategy Performance\n")
        for strat, rate in metrics.get('strategy_performance', {}).items():
            f.write(f"- {strat}: {rate*100:.2f}%\n")

    print(f"Report saved to {out_dir}")
