import json
import os

with open("eval_results_phase7c/evaluation_results_config_d.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("ERROR MESSAGES AND FAILURE CATEGORIES FOR CONFIG_D")
print("=" * 80)

for i, t in enumerate(data["tasks"]):
    print(f"[{i+1}/20] {t['task_id']} ({t['category']}):")
    print(f"  State: {t['state']}, Passed: {t['acceptance_passed']}, NativeOK: {t['native_syntax_ok']}, FBUsed: {t['fallback_used']}")
    print(f"  Failure Category: {t['failure_category']}")
    print(f"  Error: {t['error_message']}")
