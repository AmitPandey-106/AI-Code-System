import os
import csv
import json

MODES = {
    "MODE_A": "experiments/LITE_CODER_100TASK_MODE_A_BASELINE",
    "MODE_D": "experiments/LITE_CODER_100TASK_MODE_D",
    "MODE_F_ORIG": "experiments/LITE_CODER_100TASK_MODE_F",
    "MODE_F_TRAINED": "experiments/LITE_CODER_100TASK_MODE_F_TRAINED",
    "MODE_F_SAFE": "experiments/LITE_CODER_MODE_F_SAFE"
}

def build_csv():
    task_maps = {}
    for mode, path in MODES.items():
        with open(os.path.join(path, "checkpoint.json"), "r", encoding="utf-8") as f:
            ckpt = json.load(f)
        if isinstance(ckpt, dict):
            ckpt = ckpt.get("completed_tasks", [])
        task_maps[mode] = {t["task_id"]: t for t in ckpt}
        
    out_path = "experiments/FINAL_LITE_CODER_EVIDENCE/task_level_comparison_all_modes.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "task_index", "task_id",
            "mode_a_success", "mode_a_attempts",
            "mode_d_success", "mode_d_attempts",
            "mode_f_orig_success", "mode_f_orig_attempts",
            "mode_f_trained_success", "mode_f_trained_attempts", "mode_f_trained_adapter",
            "mode_f_safe_success", "mode_f_safe_attempts", "mode_f_safe_adapter"
        ])
        
        # Sort by task index in SAFE
        safe_tasks = sorted(task_maps["MODE_F_SAFE"].values(), key=lambda x: x.get("task_index", 0))
        for t in safe_tasks:
            tid = t["task_id"]
            tidx = t.get("task_index")
            
            a_t = task_maps["MODE_A"].get(tid, {})
            d_t = task_maps["MODE_D"].get(tid, {})
            fo_t = task_maps["MODE_F_ORIG"].get(tid, {})
            ft_t = task_maps["MODE_F_TRAINED"].get(tid, {})
            fs_t = t
            
            writer.writerow([
                tidx, tid,
                a_t.get("success"), a_t.get("attempts"),
                d_t.get("success"), d_t.get("attempts"),
                fo_t.get("success"), fo_t.get("attempts"),
                ft_t.get("success"), ft_t.get("attempts"), ft_t.get("active_adapter_id"),
                fs_t.get("success"), fs_t.get("attempts"), fs_t.get("active_adapter_id")
            ])
            
    print(f"Wrote complete 5-way task level comparison to {out_path}")

if __name__ == "__main__":
    build_csv()
