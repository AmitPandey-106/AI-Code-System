# LITE-Coder Phase 8: Autonomous Engineering Architecture on Google Colab

This directory provides the reproducible benchmark evaluation for **LITE-Coder Phase 8**.

## Quickstart Instructions (Google Colab)

### Step 1: Environment Setup
In a new Colab notebook (T4 GPU or standard CPU runtime), upload `LITE_CODER_PHASE8_COLAB.zip` and extract:

```bash
!unzip -q LITE_CODER_PHASE8_COLAB.zip
%cd ai-code-system
!pip install -q -r requirements.txt
```

### Step 2: Verification of Package Integrity
Verify the unzipped files against the authoritative manifest:

```python
import json, hashlib, os

with open("colab/COLAB_PACKAGE_MANIFEST.json", "r") as f:
    manifest = json.load(f)

print(f"Verifying {manifest['total_files']} files...")
mismatches = []
for entry in manifest["files"]:
    p = entry["path"]
    if not os.path.exists(p):
        mismatches.append(f"Missing: {p}")
        continue
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if h != entry["sha256"]:
        mismatches.append(f"Checksum mismatch: {p}")

if not mismatches:
    print("ALL FILES VERIFIED OK!")
else:
    print(f"Validation errors: {mismatches}")
```

### Step 3: Run Full Architecture Test Suite
```bash
!pytest tests/test_phase8_architecture.py -v
```

### Step 4: Run Autonomous Engineering Benchmark
To run the evaluation across all 20 multi-repository generalization tasks:

```bash
!python colab/run_phase8_colab.py Config_E_Autonomous
```

Results will be saved in `eval_results_phase8/`:
- `evaluation_results_config_e_autonomous.json`: Task-by-task trajectories, attempts, durations, and oracle results.
- `summary_config_e_autonomous.json`: Disaggregated metrics, pass rates, and Wilson score 95% confidence intervals.
