import os
import json

configs = ["config_a", "config_b", "config_c", "config_d", "config_e"]
consolidated = {}

for c in configs:
    path = os.path.join("eval_results_phase7c", f"evaluation_results_{c}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            cname = c.upper()
            consolidated[cname] = {
                "metadata": data.get("metadata", {}),
                "summary": data.get("summary", {})
            }

summary_path = os.path.join("eval_results_phase7c", "phase7c_metrics_summary.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(consolidated, f, indent=2)

print("Consolidated summary saved to:", summary_path)
for cname, d in consolidated.items():
    s = d["summary"]
    print(f"\n{cname} ({s.get('configuration')}):")
    print(f"  Overall Acceptance: {s.get('overall_acceptance_rate')*100:.1f}% ({s.get('overall_accepted_count')}/{s.get('total_tasks')}) CI: {s.get('overall_wilson_ci_95')}")
    print(f"  Functional Repair:  {s.get('functional_repair_rate')*100:.1f}% ({s.get('functional_repaired_count')}/{s.get('functional_total')}) CI: {s.get('functional_wilson_ci_95')}")
    print(f"  Safety Controls:    {s.get('safety_pass_rate')*100:.1f}% ({s.get('safety_passed_count')}/{s.get('safety_total')})")
    print(f"  Native Syntax:      {s.get('native_syntax_compliance_rate')*100:.1f}% ({s.get('native_syntax_compliant_count')}/{s.get('total_tasks')})")
    print(f"  Fallback Assisted:  {s.get('fallback_assisted_rate')*100:.1f}% ({s.get('fallback_assisted_count')}/{s.get('total_tasks')})")
    print(f"  Duration:           {s.get('total_benchmark_duration_s')}s")
    print(f"  Peak RAM:           {s.get('peak_memory_mb')} MB")
