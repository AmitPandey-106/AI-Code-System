import os
import json

RESULTS_DIR = "experiments/LITE_CODER_MODE_F_SAFE_RESULTS"

def audit():
    print("=" * 60)
    print("MODE-F SAFE ARTIFACT AUDIT")
    print("=" * 60)
    
    # 1. Metrics
    metrics_path = os.path.join(RESULTS_DIR, "metrics.json")
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    print("\n--- METRICS SUMMARY ---")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # 2. Checkpoint tasks
    ckpt_path = os.path.join(RESULTS_DIR, "checkpoint.json")
    with open(ckpt_path, "r", encoding="utf-8") as f:
        ckpt = json.load(f)
    
    if isinstance(ckpt, list):
        completed_tasks = ckpt
    else:
        completed_tasks = ckpt.get("completed_tasks", [])
    print(f"\n--- CHECKPOINT AUDIT ---")
    print(f"Total completed tasks in checkpoint: {len(completed_tasks)}")
    
    attempts_list = []
    success_count = 0
    failure_count = 0
    error_count = 0
    
    for t in completed_tasks:
        tid = t.get("task_id")
        succ = t.get("success")
        att = t.get("attempts", 0)
        attempts_list.append(att)
        if succ:
            success_count += 1
        else:
            if t.get("error_type") == "INFRASTRUCTURE_ERROR":
                error_count += 1
            else:
                failure_count += 1
                
    print(f"Success count: {success_count} / {len(completed_tasks)}")
    print(f"Failure count: {failure_count}")
    print(f"Error count:   {error_count}")
    print(f"Sum of attempts: {sum(attempts_list)}")
    print(f"Mean attempts (overall): {sum(attempts_list) / len(attempts_list):.4f}")
    if success_count > 0:
        succ_attempts = [t.get("attempts", 0) for t in completed_tasks if t.get("success")]
        print(f"Mean attempts (conditional on success): {sum(succ_attempts) / len(succ_attempts):.4f}")

    # 3. Training History & Canary Gating
    th_path = os.path.join(RESULTS_DIR, "training_history.json")
    with open(th_path, "r", encoding="utf-8") as f:
        history = json.load(f)
        
    print(f"\n--- TRAINING & CANARY GATE AUDIT ---")
    print(f"Total training cycles triggered: {len(history)}")
    for i, c in enumerate(history):
        cid = c.get("candidate_adapter") or c.get("candidate_id")
        tid = c.get("trigger_task_id")
        tidx = c.get("trigger_task_index")
        loss = c.get("training_loss") or c.get("train_loss")
        crate = c.get("canary_success_rate")
        pstatus = c.get("promotion_status") or c.get("status")
        rb = c.get("rollback")
        print(f"\nCycle {i+1}:")
        print(f"  Candidate Adapter ID: {cid}")
        print(f"  Triggered at Task:    {tid} (index {tidx})")
        print(f"  Training Loss:        {loss}")
        print(f"  Canary Pass Rate:     {crate*100:.1f}%")
        print(f"  Promotion Status:     {pstatus}")
        print(f"  Rollback Executed:    {rb}")
        
        canary_res = c.get("metadata", {}).get("canary_results", {})
        for task_res in canary_res.get("task_results", []):
            print(f"    * Canary Task '{task_res.get('name')}': passed={task_res.get('passed')}, error={task_res.get('error')}")

    # 4. Check previously regressed tasks from MODE-F Trained:
    # MODE-F Trained failed on: TASK_3A3CF9DE (48), TASK_7DE3DA65 (59), TASK_BEED682C (65), TASK_7B65AF21 (71), TASK_651EE46B (77), TASK_7BCB4D17 (83), TASK_129DC2E6 (89), and in_range TASK_38BE98EC (98)
    regressed_in_trained = [
        "TASK_C615FC35", "TASK_ABC07B11", "TASK_1DA9FFE1", "TASK_0E25977A",
        "TASK_4FC2042B", "TASK_43200D99", "TASK_21D2E862", "TASK_77C30EA5"
    ]
    print(f"\n--- STATUS OF TASKS THAT FAILED IN MODE-F TRAINED ---")
    task_map = {t["task_id"]: t for t in completed_tasks}
    for tid in regressed_in_trained:
        t_info = task_map.get(tid, {})
        print(f"  Task {tid}: success={t_info.get('success')}, attempts={t_info.get('attempts')}, adapter={t_info.get('active_adapter_id')}")

if __name__ == "__main__":
    audit()
