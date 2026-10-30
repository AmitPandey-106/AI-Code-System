import os
import json
import glob

def generate_paper_tables():
    report = "# LITE-CODER Phase 8 — Large-Scale Empirical Evaluation\n\n"
    
    report += "## 1. Objective\n"
    report += "Evaluate the empirical impact of LITE-CODER's verified experience memory and adaptive strategy learning against the base model using a controlled AST-mutated benchmark.\n\n"
    
    # Load all completed experiments
    experiments = []
    for exp_dir in glob.glob("experiments/ablation/EXP_*"):
        man_path = f"{exp_dir}/experiment_manifest.json"
        met_path = f"{exp_dir}/metrics.json"
        if os.path.exists(man_path) and os.path.exists(met_path):
            with open(man_path) as f:
                man = json.load(f)
            with open(met_path) as f:
                met = json.load(f)
            experiments.append({"manifest": man, "metrics": met})
            
    if not experiments:
        report += "*(Evaluation pending. No completed experiment metrics found.)*\n\n"

    # Group by mode
    modes = {}
    for exp in experiments:
        modes[exp["manifest"]["mode"]] = exp["metrics"]
        
    report += "## Table 2: Overall Performance\n"
    report += "| Mode | Tasks | Success Rate | Avg Attempts | Median Attempts | Avg Runtime (ms) |\n"
    report += "|---|---|---|---|---|---|\n"
    
    # Sort modes logically
    mode_order = ["MODE_A", "MODE_B", "MODE_C", "MODE_D", "MODE_E", "MODE_F"]
    for m in mode_order:
        if m in modes:
            met = modes[m]
            report += f"| {m} | {met.get('total_tasks')} | {met.get('success_rate', 0)*100:.2f}% | {met.get('average_attempts', 0):.2f} | {met.get('median_attempts', 0)} | {met.get('average_execution_time_ms', 0):.0f} |\n"

    report += "\n## Table 3: Ablation Study\n"
    report += "| Comparison | Absolute Improvement | Relative Improvement | Attempt Reduction |\n"
    report += "|---|---|---|---|\n"
    
    if "MODE_A" in modes and "MODE_D" in modes:
        a_succ = modes["MODE_A"].get("success_rate", 0)
        d_succ = modes["MODE_D"].get("success_rate", 0)
        a_att = modes["MODE_A"].get("average_attempts", 0)
        d_att = modes["MODE_D"].get("average_attempts", 0)
        
        abs_imp = d_succ - a_succ
        rel_imp = (abs_imp / a_succ) if a_succ else 0
        att_red = a_att - d_att
        report += f"| A vs D | +{abs_imp*100:.2f}% | +{rel_imp*100:.2f}% | {att_red:.2f} |\n"
        
    report += "\n## Table 4: Error-Type Performance (Mode D)\n"
    if "MODE_D" in modes:
        report += "| Error Type | Success Rate |\n"
        report += "|---|---|\n"
        err_perf = modes["MODE_D"].get("error_type_performance", {})
        for etype, rate in err_perf.items():
            report += f"| {etype} | {rate*100:.2f}% |\n"
            
    report += "\n## Table 7: Strategy Learning (Mode D)\n"
    if "MODE_D" in modes:
        report += "| Strategy | Success Rate |\n"
        report += "|---|---|\n"
        strat_perf = modes["MODE_D"].get("strategy_performance", {})
        for strat, rate in strat_perf.items():
            report += f"| {strat} | {rate*100:.2f}% |\n"
            
    report += "\n## Table 11: Computational Cost\n"
    report += "*(Inference vs Verification split pending final framework telemetry extensions)*\n"
    
    report += "## 1. Objective\n"
    report += "Empirical evaluation of LITE-CODER's adaptive learning mechanisms.\n\n"
    
    report += "## 2. Experimental Setup\n"
    report += "Frozen AST-injected dataset executed under isolated states to prevent memory contamination.\n\n"
    
    report += "## 3. Hardware\n"
    # Append hardware if available
    if experiments:
        hw = experiments[0]["manifest"].get("hardware", {})
        report += f"- OS: {hw.get('os')} {hw.get('os_version')}\n"
        report += f"- CPU: {hw.get('cpu')}\n"
        report += f"- RAM: {hw.get('ram_gb')} GB\n"
        report += f"- GPU: {hw.get('gpu')} ({hw.get('vram_gb')} GB VRAM)\n"
    
    report += "\n## 4. Dataset\n"
    report += "- Version: 1.0\n- Validation: Fault-Injected AST Mutations\n\n"
    
    report += "## 5. Dataset Validation\n"
    report += "100 tasks functionally verified to fail on reference tests, proving the fault's validity.\n\n"
    
    report += "## 6. Experimental Modes\n"
    report += "- MODE A: Baseline\n- MODE D: Memory + Strategy\n- MODE F: Full\n\n"
    
    report += "## 7. Evaluation Protocol\n"
    report += "Offline ablation tests.\n\n"
    
    report += "## 8. Primary Metrics\n"
    report += "(Pending execution completion.)\n\n"
    
    # ... other sections placeholder
    for i in range(9, 24):
        headers = {
            9: "Memory Results", 10: "Strategy Results", 11: "LoRA Results",
            12: "Continual Learning Results", 13: "Capability Retention",
            14: "Error-Type Analysis", 15: "Difficulty Analysis", 16: "Computational Cost",
            17: "Statistical Analysis", 18: "Ablation Study", 19: "Failure Analysis",
            20: "Limitations", 21: "Research Findings", 22: "Research Questions Answered",
            23: "Phase 9 Recommendation"
        }
        report += f"## {i}. {headers[i]}\n(Pending execution completion.)\n\n"
        
    with open("LITE_CODER_PHASE8_REPORT.md", "w") as f:
        f.write(report)
    print("Generated LITE_CODER_PHASE8_REPORT.md")

if __name__ == "__main__":
    generate_paper_tables()
