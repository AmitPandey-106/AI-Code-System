# LITE-CODER — 100-TASK MODE-D EXECUTION PACKAGE

## 1. Overview & Purpose
This package is the clean, reproducible, and authoritative runnable package for executing the **FULL 100-TASK MODE-D BENCHMARK EXPERIMENT** on a Google Colab GPU.

### Experimental Definition: MODE-D
MODE-D evaluates the synergistic impact of **Episodic Repair Memory** and **Adaptive Strategy Learning** on top of the base foundation model, with LoRA fine-tuning remaining disabled.

| Feature Component | Status in MODE-D | Operational Mechanism |
| :--- | :--- | :--- |
| **Episodic Memory** | **ENABLED** | Stores verified repair experiences in `data/repair_memory.json` & FAISS Index (`all-MiniLM-L6-v2`); retrieves top-3 similar experiences ($similarity \ge 0.5$) during repair prompting. |
| **Strategy Learning** | **ENABLED** | Epsilon-greedy multi-armed bandit ($\epsilon = 0.20$); rewards successful fixes, penalizes regressions/security violations; updates `data/strategy_stats.json` & `data/strategy_memory.json`. |
| **Difficulty Allocation** | **ENABLED** | Analyzes error type, code complexity (AST), and retry trajectory to assess difficulty category and guide strategy selection. |
| **LoRA Fine-Tuning** | **DISABLED** | Zero adapter fine-tuning or loading; runs purely on base model weights. |
| **Base Model** | **Qwen/Qwen2.5-Coder-1.5B** | Pinned base model running in fp16 on GPU (device_map="auto"). |
| **Deterministic Seed** | **42** | Deterministic greedy decoding (`do_sample=False`, seed 42) for scientific reproducibility. |

---

## 2. Dataset & Configuration

- **Dataset Path**: `data/benchmark/v1.0/dataset.json`
- **Canonical Dataset SHA256**: `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`
- **Total Task Count**: 100 tasks (identical to MODE-A baseline)
- **Mode**: `MODE_D`
  - `MEMORY_ENABLED`: `True`
  - `STRATEGY_LEARNING_ENABLED`: `True`
  - `LORA_ENABLED`: `False`
  - `DIFFICULTY_ALLOCATION_ENABLED`: `True`
  - `DETERMINISTIC_GENERATION`: `True`
  - `BENCHMARK_SEED`: `42`
- **Fix A Verified**: Present in `app/main.py` (`next_err = next_att.get("error_type") or ""`).
- **Fix B Absent**: No bypass guard introduced.

---

## 3. Quick Start on Google Colab (GPU Runtime)

### Step 1: Check GPU Runtime
Ensure the Colab runtime is set to GPU (T4, V100, or A100):
```python
!nvidia-smi
```

### Step 2: Unzip Package
```bash
!unzip -q LITE_CODER_MODE_D_100TASK_COLAB.zip -d /content/ai-code-system
%cd /content/ai-code-system
```

### Step 3: Install Dependencies
```bash
!pip install -r requirements-colab.txt
```

### Step 4: Run Pre-Flight Environment Verification
```bash
!python scripts/colab_mode_d_setup.py
```
Expected output:
```
OVERALL VERIFICATION RESULT: READY FOR 100-TASK MODE-D RUN
```

### Step 5: Execute the 100-Task MODE-D Benchmark
```bash
!python scripts/run_mode_d_100.py
```
*(Alternatively: `python -m benchmark.run_experiment --mode MODE_D --experiment-id LITE_CODER_100TASK_MODE_D --dataset data/benchmark/v1.0/dataset.json`)*

### Step 6: Verify Outputs
All results, raw task executions, atomic checkpoints, metrics, and state snapshots are written to:
`experiments/LITE_CODER_100TASK_MODE_D/`
- `checkpoint.json`
- `experiment_manifest.json`
- `metrics.json`
- `raw_tasks/*.json`
- `state_snapshot/`

---

## 4. Research Integrity Protocol
1. MODE-D begins with clean, empty initial state files (`repair_memory.json = []`, `strategy_memory.json = []`, `strategy_stats.json = {}`, and an empty FAISS index).
2. As the 100 tasks execute sequentially, memories and policy statistics accumulate online.
3. Output directory is strictly isolated at `experiments/LITE_CODER_100TASK_MODE_D/`.
4. Frozen MODE-A baseline evidence (`experiments/LITE_CODER_100TASK_MODE_A_BASELINE/`) is untouched.
