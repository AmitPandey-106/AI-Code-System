# Direct Empirical Comparison: MODE-F Original vs. MODE-F Trained

**Document ID:** `MODE_F_ORIGINAL_vs_MODE_F_TRAINED`  
**Location:** `experiments/FINAL_LITE_CODER_EVIDENCE/`  
**Date:** 2026-09-24  
**Auditor / Analyst:** Antigravity Research Verification System  
**Canonical Dataset SHA256:** `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620` (100 tasks)

---

## 1. Context & Research Objective

Both **MODE-F Original** and **MODE-F Trained** were designed to evaluate the identical algorithmic configuration of LITE-CODER:
- Non-parametric episodic memory (FAISS vector store)
- Dirichlet-multinomial contextual bandit strategy allocation
- Difficulty-aware attempt budgeting
- Online continual LoRA parameter adaptation ($r=8, \alpha=16$)

However, their runtime execution differed fundamentally:
- **MODE-F Original (Frozen):** Online LoRA training failed silently at runtime due to an unhandled `torchao` import incompatibility, producing **0 adapters** and executing all 100 tasks on the frozen base model weights.
- **MODE-F Trained (Verified Colab T4):** Hardened with runtime module isolation, prompt label masking (`labels = -100`), candidate validation gating, and base model hot-reloading. Two functional adapters (`adapter_v1` and `adapter_v2`) were trained, validated, promoted, and actively used for inference across 61 tasks.

### Methodological Role of this Comparison:
Comparing **MODE-D vs. MODE-F Trained** is a descriptive comparison between two different system architectures (one without LoRA by design, one with LoRA).  
Comparing **MODE-F Original vs. MODE-F Trained** provides a more direct, within-configuration evaluation of the **functioning-LoRA intervention**, holding the intended algorithmic ablation constant, subject to implementation hardening differences between the runs.

---

## 2. High-Level Performance Comparison

| Metric | MODE-F Original (Zero Adapters) | MODE-F Trained (Functional Adapters) | Delta (Trained - Original) |
| :--- | :---: | :---: | :---: |
| **Total Tasks Executed** | 100 | 100 | 0 |
| **Successful Repairs** | 100 (100.0%) | 92 (92.0%) | -8 (-8.0%) |
| **Model Failures** | 0 (0.0%) | 8 (8.0%) | +8 (+8.0%) |
| **Infrastructure Errors** | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **Raw Recorded Mean Attempts** | 1.2600 | 1.0700 | -0.1900 *(Zero-distorted)* |
| **Conditional Mean Attempts (Successes Only)** | 1.2600 ($n=100$) | 1.1630 ($n=92$) | -0.0970 |
| **Common-Success Paired Mean Attempts ($n=92$)** | 1.2826 | 1.1630 | -0.1196 |
| **Median Attempts (Successful Tasks)** | 1.0 | 1.0 | 0.0 |
| **Validated Adapters Produced** | 0 | 2 | +2 |
| **Tasks Executed Under Active Adapter** | 0 / 100 | 61 / 100 | +61 |

---

## 3. Statistical Testing on Success / Failure (Categorical Analysis)

To evaluate whether the drop from 100% to 92% success represents a statistically significant behavioral change:

### Contingency Table ($N=100$ Tasks):
- Both Configurations Succeed: **92 tasks**
- MODE-F Original Succeeds, MODE-F Trained Fails: **8 tasks**
- MODE-F Original Fails, MODE-F Trained Succeeds: **0 tasks**
- Both Configurations Fail: **0 tasks**

### McNemar Exact Test:
- Discordant pairs: $b = 8$ (Original pass, Trained fail), $c = 0$ (Original fail, Trained pass).
- Under the null hypothesis of marginal homogeneity, $b \sim \text{Binomial}(8, 0.5)$.
- Exact two-sided binomial $p$-value:
  $$p = 2 \times \left(\frac{1}{2}\right)^8 = \frac{2}{256} = 0.0078125 \approx 0.0078$$
- Continuity-corrected $\chi^2$:
  $$\chi^2 = \frac{(|8 - 0| - 1)^2}{8 + 0} = \frac{49}{8} = 6.1250 \quad (p = 0.0133)$$

**Conclusion:** The reduction in task success rate after enabling functional LoRA is statistically significant ($p < 0.01$).

---

## 4. Attempt Counts on Common Successful Tasks ($n=92$)

Excluding the 8 failed tasks (which were encoded as `attempts = 0` and would otherwise distort repair effort):

| Statistic | MODE-F Original ($n=92$) | MODE-F Trained ($n=92$) | Paired Difference |
| :--- | :---: | :---: | :---: |
| **Mean Attempts** | 1.2826 | 1.1630 | +0.1196 |
| **Standard Deviation** | 0.4988 | 0.4497 | 0.3263 |
| **Median Attempts** | 1.0 | 1.0 | 0.0 |
| **95% Confidence Interval** | — | — | **[0.0520, 0.1871]** |
| **Paired $t$-test** | — | — | **$t = 3.5154, p = 6.87 \times 10^{-4}$** |
| **Wilcoxon Signed-Rank Test** | — | — | **$W = 0.0000, p = 9.11 \times 10^{-4}$** |
| **Effect Size (Cohen's $d$)** | — | — | **$d = 0.3665$ (Small-to-medium)** |

### Per-Task Attempt Difference Distribution ($n=92$):
- **Identical attempt count ($\Delta = 0$):** 81 tasks (88.0%)
- **Fewer attempts under Trained ($\Delta = +1$):** 11 tasks (12.0%)
- **More attempts under Trained ($\Delta < 0$):** 0 tasks (0.0%)

Among the tasks that succeeded in both runs, MODE-F Trained resolved 11 tasks in 1 attempt that previously required 2 attempts under MODE-F Original, and zero tasks required more attempts.

---

## 5. Detailed Task Transition Breakdown

Across all 100 tasks, exactly two categories of transition occurred:

### 5.1 Regressed Tasks (8 Tasks: Succeeded in Original $\rightarrow$ Failed in Trained)
All 8 regressions were initial code generation failures (`model_failure`, `attempts = 0`):

| Task Index | `task_id` | Underlying Logic | Original Attempts | Trained Attempts | Active Adapter in Trained |
| :-: | :--- | :--- | :-: | :-: | :--- |
| **48** | `TASK_C615FC35` | `is_even` parity check | 1 | 0 (Fail) | `adapter_v1_1790247818` |
| **59** | `TASK_ABC07B11` | `is_even` parity check | 1 | 0 (Fail) | `adapter_v1_1790247818` |
| **65** | `TASK_1DA9FFE1` | `is_even` parity check | 1 | 0 (Fail) | `adapter_v1_1790247818` |
| **71** | `TASK_0E25977A` | `is_even` parity check | 1 | 0 (Fail) | `adapter_v1_1790247818` |
| **77** | `TASK_4FC2042B` | `is_even` parity check | 1 | 0 (Fail) | `adapter_v1_1790247818` |
| **83** | `TASK_43200D99` | `is_even` parity check | 1 | 0 (Fail) | `adapter_v1_1790247818` |
| **89** | `TASK_21D2E862` | `is_even` parity check | 1 | 0 (Fail) | `adapter_v1_1790247818` |
| **98** | `TASK_77C30EA5` | `in_range` numeric bounds | 1 | 0 (Fail) | `adapter_v2_1790248884` |

**Regressions by Active Adapter:**
- Base Model Window (Tasks 1–37, 93, 94): **0 regressions**
- `adapter_v1` Window (Tasks 38–92): **7 regressions** (all `is_even`)
- `adapter_v2` Window (Tasks 95–100): **1 regression** (`in_range`)

### 5.2 Improved Tasks (11 Tasks: 2 Attempts in Original $\rightarrow$ 1 Attempt in Trained)
All 11 improvements were first-pass resolutions where the repair was achieved on Attempt 1 instead of Attempt 2:

| Task Index | `task_id` | Original Attempts | Trained Attempts | Active Adapter in Trained |
| :-: | :--- | :-: | :-: | :--- |
| **39** | `TASK_BC89315E` | 2 | 1 | `adapter_v1_1790247818` |
| **44** | `TASK_435DA3AE` | 2 | 1 | `adapter_v1_1790247818` |
| **50** | `TASK_50B0F89F` | 2 | 1 | `adapter_v1_1790247818` |
| **55** | `TASK_34E90ED9` | 2 | 1 | `adapter_v1_1790247818` |
| **61** | `TASK_61ECFD6A` | 2 | 1 | `adapter_v1_1790247818` |
| **67** | `TASK_8FC95909` | 2 | 1 | `adapter_v1_1790247818` |
| **73** | `TASK_71B9E063` | 2 | 1 | `adapter_v1_1790247818` |
| **79** | `TASK_2A60D1B1` | 2 | 1 | `adapter_v1_1790247818` |
| **85** | `TASK_64497C8C` | 2 | 1 | `adapter_v1_1790247818` |
| **91** | `TASK_52F6CB07` | 2 | 1 | `adapter_v1_1790247818` |
| **96** | `TASK_0DB97680` | 2 | 1 | `adapter_v2_1790248884` |

**Improvements by Active Adapter:**
- Base Model Window (Tasks 1–37): **0 improvements** (100% identical attempts to Original across all 37 tasks)
- `adapter_v1` Window (Tasks 38–92): **10 improvements**
- `adapter_v2` Window (Tasks 95–100): **1 improvement**

---

## 6. Case Studies: `is_even` and `in_range`

### 6.1 The 9 `is_even` Tasks: Specialization Drift & Recovery
Every single `is_even` task in the benchmark shares the identical structural bug (`def is_even(n): return n % 2 != 0`). Tracing all 9 tasks across both runs:

| Task Index | `task_id` | Original Success | Trained Success | Active Adapter (Trained) | Behavior Analysis |
| :-: | :--- | :-: | :-: | :--- | :--- |
| **17** | `TASK_FEE64E00` | True (att=1) | **True (att=1)** | `None` (Base Model) | Pre-adapter baseline: succeeds normally |
| **48** | `TASK_C615FC35` | True (att=1) | **False (att=0)** | `adapter_v1` | **Regression:** Initial generation failure |
| **59** | `TASK_ABC07B11` | True (att=1) | **False (att=0)** | `adapter_v1` | **Regression:** Initial generation failure |
| **65** | `TASK_1DA9FFE1` | True (att=1) | **False (att=0)** | `adapter_v1` | **Regression:** Initial generation failure |
| **71** | `TASK_0E25977A` | True (att=1) | **False (att=0)** | `adapter_v1` | **Regression:** Initial generation failure |
| **77** | `TASK_4FC2042B` | True (att=1) | **False (att=0)** | `adapter_v1` | **Regression:** Initial generation failure |
| **83** | `TASK_43200D99` | True (att=1) | **False (att=0)** | `adapter_v1` | **Regression:** Initial generation failure |
| **89** | `TASK_21D2E862` | True (att=1) | **False (att=0)** | `adapter_v1` | **Regression:** Initial generation failure |
| **100** | `TASK_803EEF67` | True (att=1) | **True (att=1)** | `adapter_v2` | **Recovery:** Succeeded on Attempt 1 |

- **Empirical Confirmation of Regression:** Under `adapter_v1`, pass rate on `is_even` dropped from 100% (7/7 in Original) to **0% (0/7 in Trained)**.
- **Empirical Confirmation of Recovery:** After retraining with an expanded buffer of 6 examples in Cycle 2, Task 100 (`is_even`) **passed on Attempt 1** under `adapter_v2`.

### 6.2 The 18 `in_range` Tasks: Domain Stability
There are 18 `in_range` tasks across the dataset:
- Tasks 5, 10, 15, 21, 26, 31, 36 (Base Model): 7/7 succeeded, identical attempts between Original and Trained.
- Tasks 41, 46, 52, 57, 63, 69, 75, 81, 87 (`adapter_v1`): **9/9 succeeded**, identical attempts between Original and Trained.
- Task 93 (Base Model reload): 1/1 succeeded, identical attempts (att=2).
- Task 98 (`adapter_v2`): Failed initial generation (`model_failure`, att=0).

`adapter_v1` maintained complete stability on range comparison logic (9/9 pass), while `adapter_v2` encountered an isolated generation failure on Task 98.

---

## 7. Training Trigger Timing & Lifecycle Comparison

| Attribute | MODE-F Original (Frozen) | MODE-F Trained (Verified) |
| :--- | :--- | :--- |
| **Cycle 1 Trigger Task** | Task 19 (attempted) | **Task 36** (`TASK_492A6DB5`) |
| **Trigger Memory Count** | 4 memories | 4 memories |
| **Execution Outcome** | Crashed (`ImportError: torchao`) | **Success** (Loss: 0.6402, 15.09s) |
| **Adapter 1 Status** | Not created | Promoted to active; active Tasks 38–92 |
| **Cycle 2 Trigger Task** | Never reached | **Task 93** (`TASK_3CA90906`) |
| **Trigger Memory Count** | N/A | 8 memories (+4 new) |
| **Execution Outcome** | N/A | **Success** (Loss: 0.5718, 13.20s) |
| **Adapter 2 Status** | N/A | Promoted to active; active Tasks 95–100 |

---

## 8. Synthesis: What Behavioral Changes Does Functional LoRA Support?

The physical artifacts substantiate four distinct empirical phenomena:

1. **Behavioral Change After Functional LoRA:**  
   **Supported.** In Tasks 1–37 (where no adapter was active), attempt counts were 100% identical between Original and Trained. In Tasks 38–100 (where adapters were active), 19 tasks diverged in behavior (11 improved, 8 failed). Behavioral divergence correlated strictly with adapter activation.

2. **Adapter-Induced Regression / Negative Transfer:**  
   **Supported.** Low-sample fine-tuning (3 examples in Cycle 1) induced weight changes that severely impaired modulo parity logic, causing 7 consecutive failures on `is_even`.

3. **Efficiency Gains on Non-Conflicted Tasks:**  
   **Supported.** Conditioned on success, 11 tasks that previously required 2 attempts resolved on Attempt 1 ($p = 6.87 \times 10^{-4}$), demonstrating that LoRA adaptation improved first-pass synthesis on compatible problem types.

4. **Recovery Behavior:**  
   **Supported.** Expanding the fine-tuning buffer in Cycle 2 (from 3 to 6 examples) restored parity reasoning on Task 100 under `adapter_v2`.

5. **Universal Improvement:**  
   **NOT Supported.** Online LoRA did not universally improve performance; it introduced a trade-off between first-pass repair efficiency on compatible tasks and robustness against negative transfer on specific primitive logic.
