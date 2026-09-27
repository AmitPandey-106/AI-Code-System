# LITE-CODER — 100-TASK MODE-F EXECUTION PACKAGE

## 1. Overview & Purpose
This package is the clean, reproducible, and authoritative runnable package for executing the **FULL 100-TASK MODE-F BENCHMARK EXPERIMENT** on a Google Colab GPU.

### Experimental Definition: MODE-F (Full LITE-CODER)
MODE-F evaluates the complete closed-loop self-improving system, combining:
1. **Episodic Repair Memory** (FAISS similarity search + memory injection)
2. **Adaptive Strategy Learning** (Multi-armed bandit exploration/exploitation)
3. **Difficulty-Aware Allocation** (AST complexity & error tiering)
4. **Online LoRA Fine-Tuning & Hot Reloading** (Continuous adapter training on verified repairs)

| Feature Component | Status in MODE-F | Operational Mechanism |
| :--- | :--- | :--- |
| **Episodic Memory** | **ENABLED** | Stores verified multi-attempt repairs in `data/repair_memory.json` & FAISS (`all-MiniLM-L6-v2`); retrieves top-3 similar experiences ($similarity \ge 0.5$). |
| **Strategy Learning** | **ENABLED** | Epsilon-greedy bandit ($\epsilon = 0.20$); updates policy stats in `data/strategy_stats.json` & logs in `data/strategy_memory.json`. |
| **Difficulty Allocation** | **ENABLED** | Classifies code/error into difficulty tiers (`EASY`, `MEDIUM`, `HARD`, `VERY_HARD`). |
| **LoRA Fine-Tuning** | **ENABLED** | Triggers asynchronous `train_worker.py` on verified repairs; trains LoRA adapter ($r=8, \alpha=16$ on `q_proj`, `v_proj`). |
| **Adapter Hot Reloading** | **ENABLED** | Dynamically detects new active adapter IDs in `models/adapters/active` and hot-reloads model weights between task evaluations. |
| **Base Model** | **Qwen/Qwen2.5-Coder-1.5B** | Foundation model loaded in fp16 on GPU (`device_map="auto"`). |
| **Deterministic Seed** | **42** | Deterministic greedy generation (`do_sample=False`, seed 42) for reproducible benchmarking. |

---

## 2. Dataset & Configuration

- **Dataset Path**: `data/benchmark/v1.0/dataset.json`
- **Canonical Dataset SHA256**: `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`
- **Total Task Count**: 100 tasks (identical to MODE-A and MODE-D)
- **Mode**: `MODE_F`
  - `MEMORY_ENABLED`: `True`
  - `STRATEGY_LEARNING_ENABLED`: `True`
  - `LORA_ENABLED`: `True`
  - `DIFFICULTY_ALLOCATION_ENABLED`: `True`
  - `DETERMINISTIC_GENERATION`: `True`
  - `BENCHMARK_SEED`: `42`
- **Fix A Verified**: Present in `app/main.py` (`next_err = next_att.get("error_type") or ""`).
- **Linux Subprocess Compatibility Verified**: Present in `app/main.py` (`getattr(subprocess, "CREATE_NEW_CONSOLE", 0)`).
- **Fix B Absent**: No strategy learning bypass guard introduced.

---

## 3. Quick Start on Google Colab (GPU Runtime)

### Step 1: Check GPU Runtime
Ensure the Colab runtime is set to GPU (T4, V100, or A100):
```python
!nvidia-smi
```

### Step 2: Unzip Package
```bash
!unzip -q LITE_CODER_MODE_F_100TASK.zip -d /content/ai-code-system
%cd /content/ai-code-system
```

### Step 3: Install Dependencies
```bash
!pip install -r requirements-colab.txt
```

### Step 4: Run Pre-Flight Environment Verification
```bash
!python scripts/colab_mode_f_setup.py
```
Expected output:
```
=================================================================
READY FOR 100-TASK MODE-F RUN
=================================================================
```

### Step 5: Execute the 100-Task MODE-F Benchmark
```bash
!python scripts/run_mode_f_100.py
```
*(Alternatively: `python -m benchmark.run_experiment --mode MODE_F --experiment-id LITE_CODER_100TASK_MODE_F --dataset data/benchmark/v1.0/dataset.json`)*

### Step 6: Verify Outputs
All results, raw task records, atomic checkpoints, metrics, and state snapshots are written to:
`experiments/LITE_CODER_100TASK_MODE_F/`
- `checkpoint.json`
- `experiment_manifest.json`
- `metrics.json`
- `raw_tasks/*.json`
- `state_snapshot/`

---

## 4. Research Integrity Protocol
1. MODE-F starts with clean, empty initial state files (`repair_memory.json = []`, `strategy_memory.json = []`, `strategy_stats.json = {}`, empty FAISS index, and no pre-existing active adapter).
2. As the 100 tasks execute sequentially, memories accumulate, policy stats update, and LoRA adapters are trained and hot-reloaded online.
3. Target output directory is strictly isolated at `experiments/LITE_CODER_100TASK_MODE_F/`.
4. Prior baseline experiments (MODE-A and MODE-D) remain completely separate and unedited.
