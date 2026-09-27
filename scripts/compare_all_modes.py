import os
import json
import math
from scipy import stats

MODES = {
    "MODE_A": "experiments/LITE_CODER_100TASK_MODE_A_BASELINE",
    "MODE_D": "experiments/LITE_CODER_100TASK_MODE_D",
    "MODE_F_ORIG": "experiments/LITE_CODER_100TASK_MODE_F",
    "MODE_F_TRAINED": "experiments/LITE_CODER_100TASK_MODE_F_TRAINED",
    "MODE_F_SAFE": "experiments/LITE_CODER_MODE_F_SAFE"
}

def load_data():
    data = {}
    for name, path in MODES.items():
        with open(os.path.join(path, "metrics.json"), "r", encoding="utf-8") as f:
            metrics = json.load(f)
        with open(os.path.join(path, "checkpoint.json"), "r", encoding="utf-8") as f:
            ckpt = json.load(f)
        if isinstance(ckpt, dict):
            ckpt = ckpt.get("completed_tasks", [])
        data[name] = {"metrics": metrics, "ckpt": ckpt}
    return data

def run_stats():
    data = load_data()
    print("=" * 70)
    print("5-WAY SYSTEM BENCHMARK COMPARATIVE ANALYSIS")
    print("=" * 70)
    
    # 1. Summary Table
    print("\n| Metric | MODE-A Baseline | MODE-D Memory | MODE-F Orig (Crashed) | MODE-F Trained (Unsafe) | MODE-F SAFE (Canary Gate) |")
    print("|---|---|---|---|---|---|")
    
    row_completed = "| Completed Tasks |"
    row_successes = "| Successful Repairs |"
    row_failures = "| Model Failures |"
    row_infra_err = "| Infra Errors |"
    row_succ_rate = "| Success Rate |"
    row_sum_att = "| Total Recorded Attempts |"
    row_overall_att = "| Overall Mean Attempts |"
    row_cond_att = "| Conditional Mean (Succ) |"
    row_runtime = "| Total Runtime (s) |"
    row_adapters = "| Active Adapters Promoted |"
    
    for name in ["MODE_A", "MODE_D", "MODE_F_ORIG", "MODE_F_TRAINED", "MODE_F_SAFE"]:
        m = data[name]["metrics"]
        ckpt = data[name]["ckpt"]
        
        comp = len(ckpt)
        succ = sum(1 for t in ckpt if t.get("success"))
        fail = sum(1 for t in ckpt if not t.get("success") and t.get("error_type") != "INFRASTRUCTURE_ERROR")
        err = sum(1 for t in ckpt if t.get("error_type") == "INFRASTRUCTURE_ERROR")
        srate = f"{succ/comp*100:.1f}%"
        
        all_att = [t.get("attempts", 0) for t in ckpt]
        succ_att = [t.get("attempts", 0) for t in ckpt if t.get("success")]
        
        sum_att = sum(all_att)
        mean_all = f"{sum_att / comp:.2f}"
        mean_succ = f"{sum(succ_att) / len(succ_att):.2f}"
        runtime = f"{m.get('total_runtime_seconds', 0):.1f}s"
        
        row_completed += f" {comp} |"
        row_successes += f" {succ} |"
        row_failures += f" {fail} |"
        row_infra_err += f" {err} |"
        row_succ_rate += f" {srate} |"
        row_sum_att += f" {sum_att} |"
        row_overall_att += f" {mean_all} |"
        row_cond_att += f" {mean_succ} |"
        row_runtime += f" {runtime} |"
        
        # Check adapters promoted
        if name in ["MODE_A", "MODE_D", "MODE_F_ORIG"]:
            row_adapters += " 0 (N/A) |"
        elif name == "MODE_F_TRAINED":
            row_adapters += " 2 (v1, v2) |"
        elif name == "MODE_F_SAFE":
            row_adapters += " 0 (5 rejected) |"

    print(row_completed)
    print(row_successes)
    print(row_failures)
    print(row_infra_err)
    print(row_succ_rate)
    print(row_sum_att)
    print(row_overall_att)
    print(row_cond_att)
    print(row_runtime)
    print(row_adapters)
    
    # 2. Pairwise statistical tests between MODE-F Trained and MODE-F SAFE
    trained_ckpt = {t["task_id"]: t for t in data["MODE_F_TRAINED"]["ckpt"]}
    safe_ckpt = {t["task_id"]: t for t in data["MODE_F_SAFE"]["ckpt"]}
    
    # McNemar contingency
    # b: passed in SAFE, failed in Trained
    # c: passed in Trained, failed in SAFE
    b = 0
    c = 0
    mutual_succ = []
    
    for tid, s_task in safe_ckpt.items():
        t_task = trained_ckpt.get(tid)
        if not t_task:
            continue
        s_pass = s_task.get("success", False)
        t_pass = t_task.get("success", False)
        
        if s_pass and not t_pass:
            b += 1
        elif not s_pass and t_pass:
            c += 1
            
        if s_pass and t_pass:
            mutual_succ.append((tid, t_task.get("attempts", 0), s_task.get("attempts", 0)))
            
    print("\n--- STATISTICAL TESTS: MODE-F TRAINED vs MODE-F SAFE ---")
    print(f"Passed in SAFE but failed in Trained (b): {b}")
    print(f"Passed in Trained but failed in SAFE (c): {c}")
    
    # Exact McNemar binomial p-value
    # Under H0, b ~ Binomial(b+c, 0.5)
    n_discordant = b + c
    if n_discordant > 0:
        # Two-tailed exact binomial
        p_val_mcnemar = 2 * stats.binom.cdf(min(b, c), n_discordant, 0.5)
        print(f"McNemar Exact Binomial p-value: {p_val_mcnemar:.6f} (statistically significant: {p_val_mcnemar < 0.05})")
    else:
        print("No discordant pairs.")

    print(f"\nMutually successful tasks count: {len(mutual_succ)}")
    trained_mutual_att = [x[1] for x in mutual_succ]
    safe_mutual_att = [x[2] for x in mutual_succ]
    print(f"Trained mutual mean attempts: {sum(trained_mutual_att)/len(trained_mutual_att):.4f}")
    print(f"SAFE mutual mean attempts:    {sum(safe_mutual_att)/len(safe_mutual_att):.4f}")
    
    diffs = [s - t for t, s in zip(trained_mutual_att, safe_mutual_att)]
    print(f"Attempt difference (SAFE - Trained):")
    print(f"  SAFE required fewer attempts: {sum(1 for d in diffs if d < 0)}")
    print(f"  Equal attempts:               {sum(1 for d in diffs if d == 0)}")
    print(f"  SAFE required more attempts:  {sum(1 for d in diffs if d > 0)}")

if __name__ == "__main__":
    run_stats()
