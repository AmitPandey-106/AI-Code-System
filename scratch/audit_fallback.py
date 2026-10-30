import json
import os

configs = ["config_a", "config_b", "config_c", "config_d", "config_e"]
data = {}
for c in configs:
    with open(os.path.join("eval_results_phase7c", f"evaluation_results_{c}.json"), "r", encoding="utf-8") as f:
        data[c] = json.load(f)

print("=" * 80)
print("FALLBACK CONFIGURATION AUDIT: CONFIGS C, D, E")
print("=" * 80)

for c in ["config_c", "config_d", "config_e"]:
    cfg_name = c.upper()
    flags = data[c]["metadata"]["flags"]
    tasks = data[c]["tasks"]
    fallback_enabled = flags.get("fallback_enabled", False)
    print(f"\nConfiguration {cfg_name}: fallback_enabled = {fallback_enabled}")
    
    # Check per-task metrics
    count_fb_used = sum(1 for t in tasks if t.get("fallback_used"))
    count_native_syntax = sum(1 for t in tasks if t.get("native_syntax_ok"))
    count_passed = sum(1 for t in tasks if t.get("acceptance_passed"))
    
    print(f"  Summary from JSON: fallback_assisted_count = {data[c]['summary'].get('fallback_assisted_count')}")
    print(f"  Tasks with fallback_used == True: {count_fb_used}")
    print(f"  Tasks with native_syntax_ok == True: {count_native_syntax}")
    print(f"  Tasks with acceptance_passed == True: {count_passed}")

print("\n" + "=" * 80)
print("PER-TASK INSPECTION FOR CONFIG_D AND CONFIG_E")
print("=" * 80)

for i, t_d in enumerate(data["config_d"]["tasks"]):
    t_c = data["config_c"]["tasks"][i]
    t_e = data["config_e"]["tasks"][i]
    tid = t_d["task_id"]
    cat = t_d["category"]
    
    # Check if diff was produced
    diff_d = t_d.get("current_diff") or ""
    # In task record, let's see what keys exist
    # Let's print keys if i == 0
    if i == 0:
        print("Task record keys:", list(t_d.keys()))
    
    print(f"\n[{i+1}/20] {tid} ({cat}):")
    print(f"  Config C: State={t_c['state']}, Passed={t_c['acceptance_passed']}, NativeOK={t_c.get('native_syntax_ok')}, FBUsed={t_c.get('fallback_used')}, Cat={t_c.get('failure_category')}")
    print(f"  Config D: State={t_d['state']}, Passed={t_d['acceptance_passed']}, NativeOK={t_d.get('native_syntax_ok')}, FBUsed={t_d.get('fallback_used')}, Cat={t_d.get('failure_category')}")
    print(f"  Config E: State={t_e['state']}, Passed={t_e['acceptance_passed']}, NativeOK={t_e.get('native_syntax_ok')}, FBUsed={t_e.get('fallback_used')}, Cat={t_e.get('failure_category')}")
