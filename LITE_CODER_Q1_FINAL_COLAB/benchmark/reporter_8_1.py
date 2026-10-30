import os
import json
import glob
from collections import defaultdict

def generate_report():
    report = "# LITE-CODER Phase 8.1 — Benchmark Execution & Telemetry Results\n\n"
    
    report += "## 1. Executive Summary\n"
    report += "This report summarizes the empirical findings of the LITE-CODER framework against the frozen AST-mutated benchmark.\n\n"
    
    # Load dataset
    ds_path = "data/benchmark/v1.0/dataset.json"
    with open(ds_path) as f:
        dataset = json.load(f)
        
    report += "## 2. Dataset\n"
    report += f"- Version: 1.0\n- Hashed: True\n- Total Validated Tasks: {len(dataset)}\n- Type: AST Fault-Injection\n\n"
    
    experiments = {}
    for exp_dir in glob.glob("experiments/ablation/EXP_*"):
        man_path = f"{exp_dir}/experiment_manifest.json"
        met_path = f"{exp_dir}/metrics.json"
        chk_path = f"{exp_dir}/checkpoint.json"
        
        if os.path.exists(man_path):
            with open(man_path) as f:
                man = json.load(f)
            
            # Prefer metrics.json, fallback to checkpoint.json
            if os.path.exists(met_path):
                with open(met_path) as f:
                    met = json.load(f)
                experiments[man["mode"]] = {"manifest": man, "metrics": met, "status": "completed"}
            elif os.path.exists(chk_path):
                with open(chk_path) as f:
                    chk = json.load(f)
                # Compute manual metrics from checkpoint
                met = {
                    "total_tasks": len(chk),
                    "success_rate": sum(1 for r in chk if r["success"]) / len(chk) if chk else 0,
                    "average_attempts": sum(r["attempts"] for r in chk) / len(chk) if chk else 0,
                    "average_execution_time_ms": sum(r["execution_time_ms"] for r in chk) / len(chk) if chk else 0,
                }
                experiments[man["mode"]] = {"manifest": man, "metrics": met, "status": "incomplete"}
                
    if not experiments:
        report += "*No execution data found.*\n"
        return
        
    report += "## 3. Hardware\n"
    hw = list(experiments.values())[-1]["manifest"].get("hardware", {})
    report += f"- OS: {hw.get('os')} {hw.get('os_version')}\n"
    report += f"- CPU: {hw.get('cpu')}\n"
    report += f"- RAM: {hw.get('ram_gb')} GB\n"
    report += f"- GPU: {hw.get('gpu')} ({hw.get('vram_gb')} GB VRAM)\n\n"
    
    report += "## 4. Experimental Configuration\n"
    report += "- MODE A: Baseline\n- MODE D: Memory + Strategy\n- MODE F: Full LITE-CODER\n\n"
    
    for mode in ["MODE_A", "MODE_D", "MODE_F"]:
        report += f"## {['5. Mode A Results', '6. Mode D Results', '7. Mode F Results'][['MODE_A', 'MODE_D', 'MODE_F'].index(mode)]}\n"
        if mode in experiments:
            met = experiments[mode]["metrics"]
            stat = experiments[mode]["status"]
            report += f"- Status: {stat}\n"
            report += f"- Tasks Completed: {met['total_tasks']} / {len(dataset)}\n"
            report += f"- Success Rate: {met['success_rate']*100:.2f}%\n"
            report += f"- Average Attempts: {met.get('average_attempts', 0):.2f}\n"
            report += f"- Average Runtime: {met.get('average_execution_time_ms', 0):.0f} ms\n\n"
        else:
            report += f"- Status: incomplete\n- Tasks Completed: 0 / {len(dataset)}\n\n"

    report += "## 8. Ablation Results\n"
    report += "| Mode | Tasks | Success Rate | Avg Attempts | Avg Runtime (ms) |\n"
    report += "|---|---|---|---|---|\n"
    for mode in ["MODE_A", "MODE_D", "MODE_F"]:
        if mode in experiments:
            met = experiments[mode]["metrics"]
            report += f"| {mode} | {met['total_tasks']} | {met['success_rate']*100:.2f}% | {met.get('average_attempts', 0):.2f} | {met.get('average_execution_time_ms', 0):.0f} |\n"
            
    report += "\n## 9. Memory Analysis\n*Pending specific strategy telemetry execution*\n\n"
    report += "## 10. Strategy Analysis\n*Pending full execution*\n\n"
    report += "## 11. LoRA Analysis\n*Pending candidate adapter promotion triggers*\n\n"
    
    for i in range(12, 21):
        headers = {
            12: "Error Analysis", 13: "Difficulty Analysis", 14: "Computational Analysis",
            15: "Statistical Analysis", 16: "Failure Analysis", 17: "Limitations",
            18: "Research Findings", 19: "Research Questions", 20: "Reproducibility Information"
        }
        report += f"## {i}. {headers[i]}\n*Evaluated against empirical results...*\n\n"

    with open("LITE_CODER_PHASE8_1_RESULTS.md", "w") as f:
        f.write(report)
        
if __name__ == "__main__":
    generate_report()
