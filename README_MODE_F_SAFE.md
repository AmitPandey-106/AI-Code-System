# LITE-CODER 100-Task MODE-F SAFE Experiment (Colab GPU Execution Guide)

## Overview
This package contains the authoritative, reproducible code and dataset for **MODE-F SAFE**:
- **Experiment ID:** `LITE_CODER_MODE_F_SAFE`
- **Benchmark Size:** 100 tasks
- **Dataset SHA256:** `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`
- **Hardware Target:** Google Colab T4 GPU (or equivalent CUDA runtime)

## Core Mechanisms Implemented:
1. **Experience Replay:**
   - Combines new verified repair experiences with replayed previously verified experiences.
   - Prevents representation collapse and weight drift during online adaptation.
   - Configurable: `LORA_REPLAY_SIZE=4`, `LORA_REPLAY_STRATEGY="all"`.

2. **Regression / Canary Evaluation Gate:**
   - Evaluates newly trained candidate adapters against a deterministic canary suite (`app/canary.py`) covering core primitives (`is_even`, `in_range`, `add`).
   - Rejects candidate if canary pass threshold is violated.
   - Configurable: `LORA_CANARY_ENABLED=True`, `LORA_CANARY_PASS_THRESHOLD=1.0`.

3. **Adapter Rollback & Preservation:**
   - Preserves previously active adapter if candidate is rejected.
   - Saves candidate under `models/adapters/candidates/` with status `"rejected"` and canary diagnostics.
   - Prevents unvalidated or regressed adapters from taking over active inference.

---

## Google Colab Execution Instructions

### Cell 1: Setup & Pre-flight Verification
```bash
# 1. Unzip package
unzip -q LITE_CODER_MODE_F_SAFE_100TASK.zip -d lite_coder
cd lite_coder

# 2. Install dependencies
pip install -r requirements-colab.txt

# 3. Run pre-flight verification
python scripts/colab_mode_f_safe_setup.py
```

### Cell 2: Run Full 100-Task Benchmark
```bash
# Execute complete benchmark (approx. 25-30 minutes on T4 GPU)
python scripts/run_mode_f_safe_100.py
```

### Cell 3: Package Results for Download
```python
import shutil
from google.colab import files

shutil.make_archive('LITE_CODER_MODE_F_SAFE_RESULTS', 'zip', 'experiments/LITE_CODER_MODE_F_SAFE')
files.download('LITE_CODER_MODE_F_SAFE_RESULTS.zip')
```
