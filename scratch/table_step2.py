import json
import os

configs = ["config_a", "config_b", "config_c", "config_d", "config_e"]
data = {}
for c in configs:
    with open(os.path.join("eval_results_phase7c", f"evaluation_results_{c}.json"), "r", encoding="utf-8") as f:
        data[c] = json.load(f)

print("=" * 100)
print("STEP 2 TABLE: FALLBACK AUDIT PER CONFIGURATION ACROSS ALL 20 TASKS (N=20)")
print("=" * 100)

header = f"{'Configuration':<12} | {'FB Enabled':<10} | {'FB Invoked':<10} | {'FB Rejected':<11} | {'FB Validated':<12} | {'Applied':<8} | {'Tests Pass':<10} | {'Oracle Pass':<11}"
print(header)
print("-" * len(header))

for c in configs:
    cname = c.upper()
    flags = data[c]["metadata"]["flags"]
    tasks = data[c]["tasks"]
    fb_enabled_count = 20 if flags.get("fallback_enabled") else 0
    # Did fallback ever get invoked?
    # In _extract_patch, fallback is only called if "<<<<<<< SEARCH" not in text and fallback_enabled == True.
    # In all 20 tasks, fallback_used is False.
    fb_invoked_count = sum(1 for t in tasks if t.get("fallback_used"))
    fb_rejected_count = 0
    fb_accepted_count = 0
    
    # Applied count: tasks where patch was approved and applied (state in ('completed', 'failed' after patch applied, or test failed))
    # In result_record, if state == 'completed' or cat == 'test_failure', patch was approved and applied!
    applied_count = sum(1 for t in tasks if t["state"] == "completed" or t["failure_category"] == "test_failure")
    test_pass_count = sum(1 for t in tasks if t["state"] == "completed")
    oracle_pass_count = sum(1 for t in tasks if t["acceptance_passed"])
    
    print(f"{cname:<12} | {fb_enabled_count:<10} | {fb_invoked_count:<10} | {fb_rejected_count:<11} | {fb_accepted_count:<12} | {applied_count:<8} | {test_pass_count:<10} | {oracle_pass_count:<11}")
