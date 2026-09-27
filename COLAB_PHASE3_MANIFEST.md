# LITE-CODER PHASE 3 COLAB RUNTIME MANIFEST

## 1. Project & Phase Metadata
* **Project Name**: `LITE-CODER` (Autonomous Code Generation and Adaptive Repair System)
* **Phase**: `PHASE 3 — TARGETED 24-TASK MODE-A RERUN`
* **Purpose**: Verify that Fix A eliminates the bookkeeping `TypeError` on Google Colab GPU and validates the true Pass@5 / repair outcomes of the 24 previously affected tasks without altering benchmark semantics.
* **Creation Timestamp**: `2026-09-20T13:54:30+05:30`
* **Git Commit**: `731942e707c1eb7d2aea894450794719edcd6aa4`
* **Git Branch**: `main`
* **Python Runtime Target**: Python `>= 3.10` (Tested on Python 3.10 / Colab Python 3.10-3.11)

---

## 2. Model & Mode Configuration
* **Base Model**: `Qwen/Qwen2.5-Coder-1.5B` (Hugging Face Hub ID)
* **Ablation Mode**: `MODE_A` (Baseline)
* **LoRA Configuration**:
  - `LORA_ENABLED`: `False` (Enforced by `benchmark.ablation.apply_ablation_mode("MODE_A")`)
  - **LoRA Adapter Required**: `NO`. In `MODE_A`, the model runs purely in zero-shot/few-shot base inference with prompting; no adapter weights are loaded or used.
* **Deterministic Generation**: `True` (`BENCHMARK_SEED = 42`)
* **Max Repair Retries**: `5`

---

## 3. Dataset Information
* **Dataset Path**: `data/benchmark/v1.0/dataset.json`
* **Dataset SHA256**: `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`
* **Total Tasks in Dataset**: 100
* **Tasks Selected for Phase 3**: Exactly 24 target tasks (the original set affected by the TypeError)

---

## 4. Memory & Embedding Configuration
* **Memory Status in MODE-A**: `MEMORY_ENABLED = False` (retrieval is disabled during repair)
* **State Isolation**: Reset before execution via `benchmark.runner.reset_state()`
* **Embedding Model**: `all-MiniLM-L6-v2` (auto-downloaded via `sentence-transformers`, $\approx 80\text{ MB}$, 384 dimensions)
* **FAISS Architecture**: `faiss-cpu` (CPU IndexFlatIP; no GPU FAISS needed or used)
* **State Files Preserved**:
  - `data/repair_memory.json`
  - `data/repair_memory_index.faiss`
  - `data/strategy_memory.json`
  - `data/strategy_stats.json`

---

## 5. Bug Fix Verification
* **Fix A Status**: **PRESENT** in `app/main.py`:
  ```python
  next_err = next_att.get("error_type") or ""
  sec_viol = "SecurityViolation" in next_err
  t_out = "TimeoutError" in next_err
  ```
* **Fix B Status**: **CORRECTLY ABSENT**:
  The guard `if not config.get("STRATEGY_LEARNING_ENABLED"): return` was **NOT** implemented, preserving the authentic control flow.

---

## 6. Authoritative Target Task IDs (24 Tasks)
Obtained directly from the original forensic backup checkpoint (`experiments/LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636-20260918T074352Z-1-001/LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636/checkpoint.json`):

1. `TASK_1E88EF5E`
2. `TASK_FB475E1F`
3. `TASK_527A01D3`
4. `TASK_1AC7E084`
5. `TASK_55A55247`
6. `TASK_7C30D0A1`
7. `TASK_761B7D7E`
8. `TASK_96161F4B`
9. `TASK_492A6DB5`
10. `TASK_BC89315E`
11. `TASK_435DA3AE`
12. `TASK_E86381A6`
13. `TASK_50B0F89F`
14. `TASK_34E90ED9`
15. `TASK_61DE3671`
16. `TASK_61ECFD6A`
17. `TASK_495776C1`
18. `TASK_8FC95909`
19. `TASK_71B9E063`
20. `TASK_2A60D1B1`
21. `TASK_64497C8C`
22. `TASK_52F6CB07`
23. `TASK_3CA90906`
24. `TASK_0DB97680`

All 24 task IDs exist and match the official dataset annotations.

---

## 7. Execution & Output Directory
* **Execution Script**: `scripts/run_phase3_24.py`
* **Setup Verification Script**: `scripts/colab_phase3_setup.py`
* **Dependencies**: `requirements-colab-phase3.txt`
* **Expected Output Directory**: `experiments/LITE_CODER_24TASK_POST_FIX_A_RERUN/`
* **Artifacts Generated on Rerun**:
  - `experiments/LITE_CODER_24TASK_POST_FIX_A_RERUN/checkpoint.json`
  - `experiments/LITE_CODER_24TASK_POST_FIX_A_RERUN/experiment_manifest.json`
  - `experiments/LITE_CODER_24TASK_POST_FIX_A_RERUN/raw_tasks/<task_id>.json`
  - `experiments/LITE_CODER_24TASK_POST_FIX_A_RERUN/state_snapshot/`
