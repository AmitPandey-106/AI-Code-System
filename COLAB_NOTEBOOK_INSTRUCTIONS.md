# Google Colab Execution Guide for LITE-Coder Q1 Benchmark

This guide allows you to run the complete **100-Task Q1 Benchmark Evaluation** across **all modes in a single one-shot run** on Google Colab with GPU acceleration (NVIDIA T4 / V100 / A100).

---

## Step 1: Open Google Colab
1. Go to [Google Colab](https://colab.research.google.com).
2. Create a **New Notebook**.
3. Enable GPU:
   * Click **Runtime** > **Change runtime type**
   * Select **T4 GPU** (or A100 if Colab Pro)
   * Click **Save**

---

## Step 2: Upload `litecoder_q1_eval.zip`
1. On the left sidebar of Colab, click the **Folder icon** (`Files`).
2. Click the **Upload** button (or drag and drop).
3. Select `litecoder_q1_eval.zip` from your computer.

---

## Step 3: Run the One-Shot Evaluation (Single Cell)
Paste and run the following code cell in Colab:

```python
# ========================================================
# 1. Install Dependencies
# ========================================================
!pip install -q transformers accelerate peft torch

# ========================================================
# 2. Unzip Evaluation Suite
# ========================================================
!unzip -o -q litecoder_q1_eval.zip

# ========================================================
# 3. Execute Unified Multi-Mode Benchmark (All 100 Tasks)
# ========================================================
!python colab_runner.py

# ========================================================
# 4. Download Results Automatically to Your Browser
# ========================================================
from google.colab import files
files.download("q1_results.zip")
```

---

## What Happens During the Run:
1. **Model Loading**: `Qwen2.5-Coder-1.5B` loads into GPU memory in ~1 minute (in half-precision `float16`).
2. **One-Shot Evaluation Across All 4 Modes**:
   * **Mode 1**: Zero-Shot baseline (`pass@1`)
   * **Mode 2**: Naive Iterative Repair (re-prompting with raw tracebacks)
   * **Mode 3**: LITE-Coder Full Architecture (contract validation + AST invariant shield + isolated sandbox + closed-loop repair)
   * **Mode 4**: Negative Controls (10 adversarial oracles evaluated for safe isolation)
3. **Execution Time**: ~15–20 minutes on Colab T4 GPU (instead of 5+ hours on CPU).
4. **Auto-Download**: At completion, Colab triggers an automatic download of `q1_results.zip` containing:
   * `q1_results_master.json`: Machine-readable results and telemetry for all 100 tasks.
   * `Q1_EVALUATION_REPORT.md`: Publication-ready tables and LaTeX snippet for the Q1 paper!
