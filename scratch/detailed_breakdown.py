import os
import json

configs = ["config_a", "config_b", "config_c", "config_d", "config_e"]
data = {}
for c in configs:
    with open(os.path.join("eval_results_phase7c", f"evaluation_results_{c}.json"), "r", encoding="utf-8") as f:
        data[c] = json.load(f)

print("=" * 80)
print("PHASE 7C MULTI-REPO BREAKDOWN BY TASK CATEGORY")
print("=" * 80)

categories = ["single_function_bugfix", "class_method_bugfix", "coordinated_multi_file", "negative_safety_control"]
repos = ["micro_http", "task_flow", "data_synth"]

header = f"{'Category':<28} | {'Config A':<10} | {'Config B':<10} | {'Config C':<10} | {'Config D':<10} | {'Config E':<10}"
print(header)
print("-" * len(header))

for cat in categories:
    row = [f"{cat:<28}"]
    for c in configs:
        b = data[c]["summary"]["by_category"][cat]
        row.append(f"{b['passed']}/{b['total']} ({b['pass_rate']*100:.0f}%)")
    print(" | ".join(row))

print("\n" + "=" * 80)
print("PHASE 7C MULTI-REPO BREAKDOWN BY REPOSITORY")
print("=" * 80)

header_r = f"{'Repository':<15} | {'Domain':<22} | {'Config A':<10} | {'Config B':<10} | {'Config C':<10} | {'Config D':<10} | {'Config E':<10}"
print(header_r)
print("-" * len(header_r))

repo_domains = {
    "micro_http": "Networking / HTTP",
    "task_flow": "DAG / Async Engine",
    "data_synth": "Tabular / Analytics"
}

for r in repos:
    row = [f"{r:<15}", f"{repo_domains[r]:<22}"]
    for c in configs:
        b = data[c]["summary"]["by_repository"][r]
        row.append(f"{b['passed']}/{b['total']} ({b['pass_rate']*100:.0f}%)")
    print(" | ".join(row))

print("\n" + "=" * 80)
print("DETAILED TASK-BY-TASK MATRIX")
print("=" * 80)

tasks = data["config_a"]["tasks"]
print(f"{'Task ID':<38} | {'Cat':<15} | {'A':<3} | {'B':<3} | {'C':<3} | {'D':<3} | {'E':<3}")
print("-" * 75)
for i in range(len(tasks)):
    tid = tasks[i]["task_id"]
    cat = tasks[i]["category"]
    short_cat = "func_single" if cat == "single_function_bugfix" else ("func_method" if cat == "class_method_bugfix" else ("func_multi" if cat == "coordinated_multi_file" else "safety"))
    res_str = []
    for c in configs:
        p = data[c]["tasks"][i]["acceptance_passed"]
        res_str.append("P" if p else "F")
    print(f"{tid:<38} | {short_cat:<15} | {' | '.join(res_str)}")
