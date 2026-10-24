import os
import sys
import time
import json

from eval_dataset_v2.eval_runner import CONFIGURATIONS, run_evaluation_benchmark

def main():
    configs_to_run = ["CONFIG_A", "CONFIG_B", "CONFIG_C", "CONFIG_D", "CONFIG_E"]
    if len(sys.argv) > 1:
        configs_to_run = [c.upper() for c in sys.argv[1:] if c.upper() in CONFIGURATIONS]

    print("=" * 80)
    print("PHASE 7C BENCHMARK SUITE: RUNNING ALL CONFIGURATIONS")
    print(f"Configurations to evaluate: {configs_to_run}")
    print("=" * 80)

    start_all = time.time()
    results_summary = {}

    for cname in configs_to_run:
        print(f"\n>>> Starting {cname} ({CONFIGURATIONS[cname]['label']}) ...")
        t0 = time.time()
        res = run_evaluation_benchmark(cname, CONFIGURATIONS[cname]["flags"])
        elapsed = time.time() - t0
        results_summary[cname] = {
            "label": CONFIGURATIONS[cname]["label"],
            "elapsed_s": round(elapsed, 2),
            "summary": res["summary"]
        }
        print(f">>> Completed {cname} in {elapsed:.1f}s\n")

    # Save master summary of all configurations
    out_master = os.path.join("eval_results_phase7c", "benchmark_summary_all_configs.json")
    with open(out_master, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)

    total_time = time.time() - start_all
    print("\n" + "=" * 80)
    print("ALL CONFIGURATIONS COMPLETE!")
    print(f"Master summary saved to: {out_master}")
    print(f"Total Suite Runtime: {total_time / 60:.1f} minutes")
    print("=" * 80)

if __name__ == "__main__":
    main()
