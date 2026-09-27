# LITE-CODER — 100-TASK MODE-A BASELINE EXECUTION PACKAGE

## 1. Overview & Purpose
This package is the clean, reproducible, and authoritative runnable package for executing the **FULL 100-TASK MODE-A BASELINE EXPERIMENT** on a Google Colab GPU.

### Critical Research Protocol
- **Frozen Evidence Isolation**: The previously recovered 24-task Phase-3 result (`LITE_CODER_PHASE3_24TASK_FIX_A_FROZEN.zip`) is separate frozen research evidence.
- **Fresh Full Run Required**: The 100-task benchmark must be executed fresh from this package.
- **No Hybrid Splicing**: Do NOT manually insert or splice the 24 recovered results into this package or its results folder. All 100 tasks must run in order under standard benchmark execution.
- **Fix A Verified**: The bookkeeping fix in `app/main.py` is present, preventing spurious `TypeError` on non-string error types.
- **Fix B Absent**: The guard `if not config.get("STRATEGY_LEARNING_ENABLED"): return` is NOT implemented, preserving original control flow.

---

## 2. Dataset & Configuration

- **Dataset Path**: `data/benchmark/v1.0/dataset.json`
- **Canonical Dataset SHA256**: `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`
- **Total Task Count**: 100 tasks
- **Mode**: `MODE_A` (Baseline)
  - `MEMORY_ENABLED`: `False`
  - `STRATEGY_LEARNING_ENABLED`: `False`
  - `LORA_ENABLED`: `False` (LoRA adapter is NOT loaded or required)
  - `DIFFICULTY_ALLOCATION_ENABLED`: `False`
  - `DETERMINISTIC_GENERATION`: `True`
  - `BENCHMARK_SEED`: `42`
- **Base Model**: `Qwen/Qwen2.5-Coder-1.5B` (auto-downloaded from Hugging Face Hub)

---

## 3. Quick Start on Google Colab (GPU Runtime)

### Step 1: Check GPU Runtime
Ensure the Colab runtime is set to GPU (T4, V100, or A100):
```python
!nvidia-smi
```

### Step 2: Unzip Package
```bash
!unzip -q LITE_CODER_MODE_A_100TASK_FIX_A.zip -d /content/ai-code-system
%cd /content/ai-code-system
```

### Step 3: Install Dependencies
```bash
!pip install -r requirements-colab.txt
```

### Step 4: Run Pre-Flight Environment Verification
```bash
!python scripts/colab_mode_a_setup.py
```
Expected output:
```
OVERALL VERIFICATION RESULT: READY FOR 100-TASK MODE-A RUN
```

### Step 5: Execute the 100-Task MODE-A Benchmark
```bash
!python scripts/run_mode_a_100.py
```
*(Alternatively: `python -m benchmark.run_experiment --mode MODE_A --experiment-id LITE_CODER_100TASK_MODE_A_BASELINE --dataset data/benchmark/v1.0/dataset.json`)*

### Step 6: Verify Outputs
All results, raw task executions, atomic checkpoints, and metrics are written to:
`experiments/LITE_CODER_100TASK_MODE_A_BASELINE/`
- `checkpoint.json`
- `experiment_manifest.json`
- `metrics.json`
- `raw_tasks/*.json`
- `state_snapshot/`

---

## 4. Integrity Checklist Before Execution
1. Dataset SHA256 matches `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`
2. Exactly 100 tasks present in `data/benchmark/v1.0/dataset.json`
3. Fix A verified in `app/main.py`:
   ```python
   next_err = next_att.get("error_type") or ""
   sec_viol = "SecurityViolation" in next_err
   t_out = "TimeoutError" in next_err
   ```
4. Fix B is absent.
5. No prior experiment outputs or caches included.
