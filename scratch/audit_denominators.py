import json
import os
import math

def wilson_ci(k, n, confidence=0.95):
    if n == 0:
        return (0.0, 0.0)
    z = 1.95996
    p_hat = k / n
    denom = 1 + (z**2) / n
    center = (p_hat + (z**2) / (2 * n)) / denom
    margin = (z * math.sqrt((p_hat * (1 - p_hat) / n) + ((z**2) / (4 * (n**2))))) / denom
    return (max(0.0, round(center - margin, 4)), min(1.0, round(center + margin, 4)))

configs = ["config_a", "config_b", "config_c", "config_d", "config_e"]
data = {}
for c in configs:
    with open(os.path.join("eval_results_phase7c", f"evaluation_results_{c}.json"), "r", encoding="utf-8") as f:
        data[c] = json.load(f)

print("=" * 100)
print("AUDIT OF DENOMINATORS AND DISCREPANCIES ACROSS ALL CONFIGURATIONS")
print("=" * 100)

for c in configs:
    cname = c.upper()
    tasks = data[c]["tasks"]
    summary = data[c]["summary"]
    
    func_tasks = [t for t in tasks if t["category"] != "negative_safety_control"]
    safety_tasks = [t for t in tasks if t["category"] == "negative_safety_control"]
    attempted_patch_tasks = [t for t in tasks if t["duration_s"] > 0 or t["attempts"] > 1 or t["model_calls"] > 0]
    
    # 1. Functional repairs
    func_pass = [t for t in func_tasks if t["acceptance_passed"]]
    recalc_func_rate = len(func_pass) / len(func_tasks)
    recalc_func_ci = wilson_ci(len(func_pass), len(func_tasks))
    
    # 2. Safety pass
    safe_pass = [t for t in safety_tasks if t["acceptance_passed"]]
    recalc_safe_rate = len(safe_pass) / len(safety_tasks)
    recalc_safe_ci = wilson_ci(len(safe_pass), len(safety_tasks))
    
    # 3. Overall acceptance
    all_pass = [t for t in tasks if t["acceptance_passed"]]
    recalc_all_rate = len(all_pass) / len(tasks)
    recalc_all_ci = wilson_ci(len(all_pass), len(tasks))
    
    # 4. Syntax compliance:
    # A) As reported in summary (denominator = 20)
    rep_syntax_count = summary.get("native_syntax_compliant_count")
    rep_syntax_rate = summary.get("native_syntax_compliance_rate")
    
    # B) With denominator = attempted patch generation (18 tasks, excluding tasks 16 & 19)
    syntax_in_attempted = [t for t in attempted_patch_tasks if t.get("native_syntax_ok")]
    recalc_syntax_attempted_rate = round(len(syntax_in_attempted) / len(attempted_patch_tasks), 4)
    recalc_syntax_attempted_ci = wilson_ci(len(syntax_in_attempted), len(attempted_patch_tasks))
    
    # C) With denominator = functional tasks only (15 tasks)
    syntax_in_func = [t for t in func_tasks if t.get("native_syntax_ok")]
    recalc_syntax_func_rate = round(len(syntax_in_func) / len(func_tasks), 4)
    recalc_syntax_func_ci = wilson_ci(len(syntax_in_func), len(func_tasks))
    
    # 5. Distinct outcomes:
    # - Valid syntax
    # - Patch approved & applied
    # - Tests passed
    # - Oracle accepted
    applied_tasks = [t for t in tasks if t["state"] == "completed" or t["failure_category"] == "test_failure"]
    tests_passed_tasks = [t for t in tasks if t["state"] == "completed"]
    oracle_passed_tasks = all_pass
    
    print(f"\n>>> {cname}:")
    print(f"  Functional Repairs: {len(func_pass)}/{len(func_tasks)} ({recalc_func_rate*100:.1f}%) | Reported: {summary.get('functional_repair_rate')*100:.1f}% | CI: {recalc_func_ci}")
    print(f"  Safety Compliance:  {len(safe_pass)}/{len(safety_tasks)} ({recalc_safe_rate*100:.1f}%) | Reported: {summary.get('safety_pass_rate')*100:.1f}% | CI: {recalc_safe_ci}")
    print(f"  Overall Acceptance: {len(all_pass)}/{len(tasks)} ({recalc_all_rate*100:.1f}%) | Reported: {summary.get('overall_acceptance_rate')*100:.1f}% | CI: {recalc_all_ci}")
    print(f"  Syntax (N=20 reported):    {rep_syntax_count}/20 ({rep_syntax_rate*100:.1f}%)")
    print(f"  Syntax (N=18 attempted):   {len(syntax_in_attempted)}/18 ({recalc_syntax_attempted_rate*100:.1f}%) CI: {recalc_syntax_attempted_ci}")
    print(f"  Syntax (N=15 functional):  {len(syntax_in_func)}/15 ({recalc_syntax_func_rate*100:.1f}%) CI: {recalc_syntax_func_ci}")
    print(f"  Outcome Stages: ValidSyntax={len(syntax_in_attempted)}, Applied={len(applied_tasks)}, TestsPassed={len(tests_passed_tasks)}, OracleAccepted={len(oracle_passed_tasks)}")
