import json
import os

configs = ["config_a", "config_b", "config_c", "config_d", "config_e"]
data = {}
for c in configs:
    with open(os.path.join("eval_results_phase7c", f"evaluation_results_{c}.json"), "r", encoding="utf-8") as f:
        data[c] = json.load(f)

print("=" * 90)
print(f"{'Config':<10} | {'Syntax Valid':<13} | {'Applied':<10} | {'Tests Pass':<12} | {'Accepted Functional':<20} | {'Accepted Total':<15}")
print("=" * 90)

for c in configs:
    cname = c.upper()
    tasks = data[c]["tasks"]
    func_tasks = [t for t in tasks if t["category"] != "negative_safety_control"]
    
    # 1. Syntax Valid:
    syntax_valid = sum(1 for t in tasks if t.get("native_syntax_ok"))
    
    # 2. Applied: patches that were approved and applied to disk
    # In EngineeringSession, state becomes PATCH_APPLIED, then TESTING.
    # If tests pass -> COMPLETED. If tests fail -> FAILED with cat='test_failure'.
    applied = sum(1 for t in tasks if t["state"] == "completed" or t.get("failure_category") == "test_failure")
    
    # 3. Tests Passed:
    tests_passed = sum(1 for t in tasks if t["state"] == "completed")
    
    # 4. Accepted Functional:
    accepted_func = sum(1 for t in func_tasks if t["acceptance_passed"])
    
    # 5. Accepted Total:
    accepted_total = sum(1 for t in tasks if t["acceptance_passed"])
    
    print(f"{cname:<10} | {syntax_valid:<13} | {applied:<10} | {tests_passed:<12} | {accepted_func:<20} | {accepted_total:<15}")
