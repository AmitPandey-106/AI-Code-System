import numpy as np
from typing import List

def bootstrap_confidence_interval(data: List[float], num_samples=1000, confidence_level=0.95, seed=42):
    if not data:
        return (0.0, 0.0)
    
    np.random.seed(seed)
    n = len(data)
    means = []
    
    for _ in range(num_samples):
        sample = np.random.choice(data, size=n, replace=True)
        means.append(np.mean(sample))
        
    lower_percentile = (1.0 - confidence_level) / 2.0 * 100
    upper_percentile = (1.0 + confidence_level) / 2.0 * 100
    
    return np.percentile(means, lower_percentile), np.percentile(means, upper_percentile)

def calculate_statistics(results_a: List[dict], results_b: List[dict]):
    # Calculates mean, median, CI for comparative analysis
    stat = {}
    
    if not results_a or not results_b:
        return {"error": "Insufficient data"}
        
    attempts_a = [r["attempts"] for r in results_a]
    attempts_b = [r["attempts"] for r in results_b]
    
    stat["attempts"] = {
        "mean_a": np.mean(attempts_a),
        "median_a": np.median(attempts_a),
        "ci_a": bootstrap_confidence_interval(attempts_a),
        "mean_b": np.mean(attempts_b),
        "median_b": np.median(attempts_b),
        "ci_b": bootstrap_confidence_interval(attempts_b)
    }
    
    return stat
