import os, sys, json
sys.path.insert(0, ".")
from experiments.CONTROLLED_LORA_PROOF.RUN_CONTROLLED_LORA_PROOF import generate_evidence

os.makedirs("experiments/CONTROLLED_LORA_PROOF/STAGE2_TRAINING/memory", exist_ok=True)
os.makedirs("experiments/CONTROLLED_LORA_PROOF/STAGE2_TRAINING/raw_tasks", exist_ok=True)
os.makedirs("experiments/CONTROLLED_LORA_PROOF/STAGE2_TRAINING/state_snapshot/adapters", exist_ok=True)

with open("experiments/CONTROLLED_LORA_PROOF/STAGE2_TRAINING/memory/repair_memory.json", "w") as f:
    json.dump([
        {"task": "PROOF_T1", "error_message": "test_error_1"},
        {"task": {"task_id": "PROOF_T2"}, "error_message": "test_error_2"}
    ], f)

with open("experiments/CONTROLLED_LORA_PROOF/STAGE2_TRAINING/raw_tasks/PROOF_T1.json", "w") as f:
    json.dump({"task_id": "PROOF_T1", "feedback_record": {"attempts": [{}]}, "verification": {"tests_passed": True}}, f)

generate_evidence()
print("Evidence generation passed!")
