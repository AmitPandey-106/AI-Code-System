import os

base_dir = "D:\\Amit Stuff\\ai-code-system\\LITE-CODER_Q1_JOURNAL_V2\\evidence"
os.makedirs(base_dir, exist_ok=True)

def write_protocol_matrix():
    content = """# EXPERIMENT PROTOCOL MATRIX

| Parameter | MODE_A | MODE_D | MODE_F | MODE_F_SAFE |
|---|---|---|---|---|
| **Model** | Qwen2.5-Coder-1.5B | Qwen2.5-Coder-1.5B | Qwen2.5-Coder-1.5B | Qwen2.5-Coder-1.5B |
| **Model Checkpoint** | Base | Base | LoRA-Finetuned | LoRA-Finetuned |
| **Benchmark Version** | v1.0 | v1.0 | v1.0 | v1.0 |
| **Task Count** | 100 | 100 | 100 | 100 |
| **Random Seed** | 42 | 42 | 42 | 42 |
| **Test Mechanism** | `exec()` / Native | `exec()` / Native | `exec()` / Native | AST/Contract Validation |
| **Memory State (Start)** | Empty (Disabled) | UNKNOWN (File shows 8 records) | UNKNOWN (File shows 8 records) | UNKNOWN (File shows 8 records) |
| **Retrieval Config** | None | Top-K=3, Thresh=0.5 | Top-K=3, Thresh=0.5 | Top-K=3, Thresh=0.5 |
| **Safety Config** | None | None | None | AST Sandbox Enabled |

*Note: Specific hyperparameters (temperature, max attempts) require explicit extraction from each `experiment_manifest.json`, but are intended to be identical across these runs.*
"""
    with open(os.path.join(base_dir, "EXPERIMENT_PROTOCOL_MATRIX.md"), "w") as f:
        f.write(content)

def write_memory_provenance():
    content = """# MEMORY PROVENANCE

Based on repository evidence (`repair_memory.json` snapshots showing exactly 8 records for Mode D, Mode F, and Mode F_SAFE):

**A. Was memory empty before benchmark execution?**
UNKNOWN. The presence of exactly 8 records across different experimental modes suggests either a shared pre-populated state or deterministic online learning that succeeded exactly 8 times.

**B. Was memory pre-populated?**
POSSIBLE. If the files are identical across Mode D and Mode F, it heavily implies they were copied from a shared pre-flight experiment rather than generated online dynamically (since LoRA vs Base model should theoretically yield different success trajectories).

**C. If pre-populated, exactly which experiences were present?**
Requires extracting the `task_id` fields from the 8 records in `repair_memory.json`.

**D. Where did those experiences originate?**
UNKNOWN pending task ID extraction.

**E. Were any experiences generated from benchmark evaluation tasks?**
If the task IDs in the 8 records belong to the 100-task benchmark, yes.

**F. Was memory populated dynamically during the benchmark?**
UNKNOWN. The consistency of "8 records" across modes raises questions about whether the memory updater was active or if a static index was used.

**G. Could task N retrieve an experience generated from task N-1?**
The architecture supports this (online continual learning).

**H. Could a task retrieve an experience generated from the same benchmark dataset?**
Yes, this is cross-task experience reuse (which is a valid evaluation of online learning, provided memory starts empty).

**I. Was the memory reset between runs?**
UNKNOWN.

**J. Was the FAISS index rebuilt or reused?**
UNKNOWN. Timestamps of `.faiss` files must be compared.

**K. Was repair_memory.json copied from another experiment?**
HIGHLY LIKELY given the identical record counts, but requires hash comparison.

## DATA LEAKAGE STATUS
**CLASSIFICATION: UNKNOWN (Requires Hash/Task ID Inspection)**

If memory is dynamically generated from previous evaluation tasks, it is **online continual adaptation** (cross-task experience reuse), which is valid if explicitly stated. However, if the memory was pre-populated with evaluation tasks prior to the run, this constitutes **train/test leakage**.
"""
    with open(os.path.join(base_dir, "MEMORY_PROVENANCE.md"), "w") as f:
        f.write(content)

def write_rq1_comparability():
    content = """# RQ1 COMPARABILITY: MODE A vs MODE D

**RQ1: Does experience memory improve repair effectiveness?**

**Are they comparable?**
YES, structurally. 

**What is identical?**
- Model (Base Qwen2.5-Coder-1.5B)
- Benchmark tasks (100)
- Execution mechanism (`exec()`)
- Seed (42)

**What differs?**
- Memory retrieval enabled in Mode D.

**Caveat for legitimate comparison:**
We must verify that Mode D's memory started *empty* or was pre-populated exclusively with *training/non-evaluation* tasks. If Mode D was given a pre-populated memory of the test set, the comparison is invalid. Assuming memory started empty and populated dynamically (online learning), Mode A vs Mode D perfectly answers RQ1.
"""
    with open(os.path.join(base_dir, "RQ1_COMPARABILITY.md"), "w") as f:
        f.write(content)

def write_lora_comparability():
    content = """# LORA COMPARABILITY: MODE F

**Can MODE_F legitimately be compared with MODE_A / MODE_D?**

**Differences:**
- **Model weights:** Mode F uses LoRA finetuned weights.
- **Training data:** We must strictly verify that the LoRA training dataset (e.g., `lora-finetuned/`) does NOT overlap with the 100-task benchmark.

**Does this answer "How does experience memory compare with parameter adaptation?"**
Only if the LoRA training data was distinct from the benchmark data. If LoRA was trained on the benchmark, comparing it to Mode D (which learns online) is scientifically invalid.

**Conclusion:**
This compares two different system configurations. It can be used to contrast *static parameter adaptation* with *dynamic experience retrieval*, provided data isolation is proven.
"""
    with open(os.path.join(base_dir, "LORA_COMPARABILITY.md"), "w") as f:
        f.write(content)

def write_safe_protocol():
    content = """# SAFE EVALUATION PROTOCOL

SAFE mode (AST/Contract validation) fundamentally alters the testing oracle. 

**A. Repair effectiveness:**
Cannot be directly compared to Mode A/D/F for raw success rates because the oracle is stricter. A fix that passes `exec()` in Mode D might fail AST validation in Mode F_SAFE.

**B. Verification integrity:**
SAFE mode is the primary mechanism for establishing verification integrity.

**C. Contamination resistance & D. Security robustness:**
Must be evaluated independently using a dedicated security/adversarial dataset (e.g., `tests/test_fault_injection.py`), not the standard 100-task benchmark.

**Protocol:** 
Treat SAFE as a separate research dimension determining *trust*. Do not use SAFE success rates as evidence of memory effectiveness without a `MODE_A_SAFE` baseline.
"""
    with open(os.path.join(base_dir, "SAFE_EVALUATION_PROTOCOL.md"), "w") as f:
        f.write(content)

def write_final_plan():
    content = """# FINAL EXPERIMENT EXECUTION PLAN

## REQUIRED EXPERIMENTS BY RQ

**RQ1 (Memory effectiveness): Existing evidence sufficient? NO.**
- **Exact experiment required:** Re-run Mode A and Mode D ensuring memory strictly starts empty, logging memory admissions sequentially.
- **Expected output:** Clean success rates; `repair_memory.json` growth over time.

**RQ2 (Repair-effort reduction): Existing evidence sufficient? NO.**
- **Exact experiment required:** Task-level extraction of `attempts_used` from the clean Mode A and Mode D runs.
- **Expected output:** Distribution boxplot of attempts.

**RQ3 (Ablation / Component): Existing evidence sufficient? NO.**
- **Exact experiment required:** Verify LoRA training dataset isolation. If clean, extract success rates for Mode F.
- **Expected output:** Table comparing Base, Base+Memory, LoRA, LoRA+Memory.

**RQ4 (Verification/Contamination): Existing evidence sufficient? NO.**
- **Exact experiment required:** Mode D_SAFE (Base + Memory + AST Oracle) vs Adversarial Dataset.
- **Expected output:** Contamination rejection rate table.

**RQ5 (Computational overhead): Existing evidence sufficient? NO.**
- **Exact experiment required:** Extract latency timestamps from Mode D run.
- **Expected output:** Average retrieval latency (ms).

---

## PRIORITIZED EXPERIMENT PLAN

1. **CRITICAL:** Re-run/Audit Mode A vs Mode D (Base Oracle, Clean Memory Start).
2. **CRITICAL:** Re-run/Audit Mode A_SAFE vs Mode D_SAFE (AST Oracle, Clean Memory Start) to allow fair comparison of safety's impact on success.
3. **CRITICAL:** Adversarial Injection Test on Mode D_SAFE.
4. **HIGH VALUE:** Mode F vs Mode F_SAFE (Assuming LoRA training is isolated).
5. **OPTIONAL:** Embedding dimension ablations.
6. **DO NOT RUN:** LoRA hyperparameter sweeps.

---

## FINAL RECOMMENDED EXPERIMENT MATRIX

| Experiment ID | Configuration | Memory | LoRA | SAFE | Benchmark | Seed | Purpose | RQ | Metric |
|---|---|---|---|---|---|---|---|---|---|
| **EXP_01** | Baseline | Off | Off | Off | 100-task | 42 | Establish zero-shot baseline | RQ1 | Success % |
| **EXP_02** | Memory | On | Off | Off | 100-task | 42 | Measure online experience | RQ1, RQ2 | Success %, Attempts |
| **EXP_03** | SAFE_Base | Off | Off | On | 100-task | 42 | Establish SAFE strictness baseline | RQ4 | Success % |
| **EXP_04** | SAFE_Memory | On | Off | On | 100-task | 42 | Memory performance under strict verification | RQ1, RQ4 | Success % |
| **EXP_05** | LoRA_Base | Off | On | Off | 100-task | 42 | Parameter adaptation baseline | RQ3 | Success % |
| **EXP_06** | Contamination | On | Off | On | Security Set | 42 | Measure verification integrity | RQ4 | Rejection % |

---

## FINAL SCIENTIFIC CHECK

1. **Can we prove memory improves repair without confounding factors?** NO. We must prove memory starts empty.
2. **Can we distinguish memory benefit from SAFE benefit?** NO. We need EXP_03 and EXP_04 to isolate the oracle change.
3. **Can we distinguish memory from LoRA parameter adaptation?** NO. We must audit the LoRA training set for leakage first.
4. **Can we establish whether memory was clean at evaluation start?** NO. The 8 records currently present must be hashed/traced.
5. **Can we quantify repair effort?** YES, pending script extraction.
6. **Can we quantify retrieval contribution?** YES, comparing EXP_01 and EXP_02.
7. **Can we evaluate contamination resistance separately?** YES, via EXP_06.
8. **Can we reproduce the final results?** YES, seeds and configs are locked.
"""
    with open(os.path.join(base_dir, "FINAL_EXPERIMENT_EXECUTION_PLAN.md"), "w") as f:
        f.write(content)

if __name__ == "__main__":
    write_protocol_matrix()
    write_memory_provenance()
    write_rq1_comparability()
    write_lora_comparability()
    write_safe_protocol()
    write_final_plan()
    print("Locked protocol matrices written successfully.")
