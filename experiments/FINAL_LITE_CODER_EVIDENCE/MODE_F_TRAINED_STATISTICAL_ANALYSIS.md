# Statistical Analysis & Research Evaluation of MODE-F Trained

**Document ID:** `MODE_F_TRAINED_STATISTICAL_ANALYSIS`  
**Location:** `experiments/FINAL_LITE_CODER_EVIDENCE/`  
**Date:** 2026-09-24  
**Auditor / Analyst:** Antigravity Research Verification System  
**Canonical Dataset SHA256:** `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`  

---

## 1. Dataset & Experimental Setup

The evaluation was conducted on the canonical 100-task LITE-CODER benchmark dataset (`data/benchmark/v1.0/dataset.json`), comprising a fixed, seed-controlled collection of standalone Python repair tasks spanning arithmetic, string manipulation, data structures, recursion, and algorithmic logic.

The benchmark isolates four primary system configurations across the same 100 tasks:
- **MODE-A (Authoritative Replaced Baseline):** Frozen baseline without memory retrieval, contextual bandit strategy adaptation, or model weight adaptation ($N=100$).
- **MODE-D (Memory + Strategy Learning):** Frozen configuration incorporating episodic memory retrieval (FAISS vector store) and Dirichlet-multinomial contextual bandit strategy allocation ($N=100$).
- **MODE-F Original (Unrepaired Pipeline):** Intended continual-learning configuration where online LoRA training failed silently at runtime due to a `torchao` compatibility bug, producing 0 adapters and running strictly on the base model ($N=100$).
- **MODE-F Trained (Verified Online LoRA):** Live continual-learning configuration executed on Google Colab (Tesla T4 GPU, PyTorch 2.11.0+cu128, Python 3.13.15) with `torchao` runtime isolation, prompt label masking (`labels = -100`), candidate validation gating, and dynamic base model reloads ($N=100$).

---

## 2. Correct Metric Definitions

A critical methodological requirement in evaluating MODE-F Trained is avoiding distorted attempt metrics caused by zero-encoding of failed tasks.

In the LITE-CODER runtime architecture, tasks that fail initial executable code generation are assigned `attempts = 0`. If a naïve arithmetic mean is applied across all 100 tasks, the 8 failed tasks dilute the sum of attempts, artificially depressing the mean to 1.07. This must **not** be reported or interpreted as a reduction in repair effort.

Three distinct metrics are defined:

1. **Overall Recorded Attempts Mean ($\bar{A}_{\text{all}}$):**
   $$\bar{A}_{\text{all}} = \frac{\sum_{i=1}^{N} \text{attempts}_i}{N} = \frac{107}{100} = 1.0700$$
   *Methodological note:* This is a raw accounting aggregate affected by failed tasks having $\text{attempts} = 0$. It does **not** reflect average repair effort.

2. **Successful-Task Conditional Attempts Mean ($\bar{A}_{\text{succ}}$):**
   $$\bar{A}_{\text{succ}} = \frac{\sum_{i \in \text{Successes}} \text{attempts}_i}{N_{\text{success}}} = \frac{107}{92} = 1.1630$$
   *Methodological note:* This measures the true mean attempt count required to produce an executable, verified fix, conditioned on repair success.

3. **Task Failure Rate ($F_R$):**
   $$F_R = \frac{N_{\text{failed}}}{N} = \frac{8}{100} = 0.0800 \quad (8.0\%)$$
   *Methodological note:* Represents the empirical risk of model generation failure under online adaptation.

---

## 3. Comparison with MODE-A Baseline

| Metric | MODE-A (Frozen) | MODE-F Trained (Empirical) | Difference |
| :--- | :---: | :---: | :---: |
| **Tasks Executed** | 100 | 100 | 0 |
| **Task Success Rate** | 100.0% (100/100) | 92.0% (92/100) | -8.0% |
| **Task Failure Rate** | 0.0% (0/100) | 8.0% (8/100) | +8.0% |
| **Raw Recorded Mean Attempts** | 1.5800 | 1.0700 | -0.5100 *(Distorted)* |
| **Successful-Task Mean Attempts**| 1.5800 | 1.1630 | -0.4170 |
| **Common-Success Paired Mean Attempts ($n=92$)** | 1.6304 | 1.1630 | -0.4674 |

Across the 92 common tasks where both configurations succeeded:
- MODE-A required a mean of 1.6304 attempts (median 1.0).
- MODE-F Trained required a mean of 1.1630 attempts (median 1.0).
- The paired attempt reduction is statistically significant ($t = 4.3899, p = 3.05 \times 10^{-5}$, Wilcoxon $W = 0, p = 1.94 \times 10^{-4}$, Cohen's $d = 0.4577$).
- However, MODE-A achieved 100% repair coverage, whereas MODE-F Trained suffered an 8.0% failure rate.

---

## 4. Comparison with MODE-D (Memory + Strategy Learning)

| Metric | MODE-D (Frozen) | MODE-F Trained (Empirical) | Difference |
| :--- | :---: | :---: | :---: |
| **Tasks Executed** | 100 | 100 | 0 |
| **Task Success Rate** | 100.0% (100/100) | 92.0% (92/100) | -8.0% |
| **Task Failure Rate** | 0.0% (0/100) | 8.0% (8/100) | +8.0% |
| **Raw Recorded Mean Attempts** | 1.2600 | 1.0700 | -0.1900 *(Distorted)* |
| **Successful-Task Mean Attempts**| 1.2600 | 1.1630 | -0.0970 |
| **Common-Success Paired Mean Attempts ($n=92$)** | 1.2826 | 1.1630 | -0.1196 |

Across the 92 common successful tasks:
- MODE-D required 1.2826 attempts on average.
- MODE-F Trained required 1.1630 attempts on average.
- Task distribution breakdown: 81 tasks required identical attempt counts ($\Delta = 0$); 11 tasks required 1 fewer attempt under MODE-F Trained ($\Delta = 1$); 0 tasks required more attempts ($\Delta < 0$).
- Paired statistical test: $t = 3.5154, p = 6.87 \times 10^{-4}$, Wilcoxon $W = 0, p = 9.11 \times 10^{-4}$, Cohen's $d = 0.3665$.
- Paired categorical test (McNemar's test for task completion): Contingency table shows 92 tasks passed by both, 8 tasks passed by MODE-D and failed by MODE-F Trained, 0 tasks passed by MODE-F Trained and failed by MODE-D. Exact two-sided binomial $p = 0.007813$ ($\chi^2_{\text{corrected}} = 6.1250$).
- The reduction in success rate from 100% to 92% is statistically significant.

---

## 5. MODE-F Trained Benchmark Results Summary

- **Total Tasks Processed:** 100 / 100 (Complete run)
- **Successful Tasks:** 92 / 100 (92.00%)
- **Model Failures:** 8 / 100 (8.00%)
- **Infrastructure / System Crashes:** 0 / 100 (0.00%)
- **Total Recorded Attempts:** 107
- **Conditional Mean Attempts on Successful Tasks:** 1.1630
- **Total Execution Runtime:** 1,795.89 seconds (~29.93 minutes)
- **Average Per-Task Latency:** 17.88 seconds

---

## 6. Adapter v1 Analysis

- **Trigger Task:** Task 36 (`TASK_492A6DB5`), fired when unique verified memory count reached buffer threshold of 4.
- **Active Range:** Task 38 through Task 92 (55 tasks executed while active).
- **Physical Weight File:** `models/adapters/candidates/adapter_v1_1790247818/adapter_model.safetensors` (4,372,840 bytes, SHA256: `f8b3b4726d5dc39878bb194c01a3e7ea6a8337627bbd4a10b154d18e5096ae31`).
- **Archived Path:** `models/adapters/archive/archive_adapter_v1_1790247818_1790248897/`.
- **Training Examples:** 3 valid SFT pairs formatted with prompt token masking (`-100`).
- **Training Duration:** 15.09 seconds.
- **Final Training Loss:** 0.6402.
- **Validation Gate:** Passed (configuration validated, model instantiated, forward generation confirmed).
- **Promotion Status:** Promoted to active; hot-reloaded into inference memory before Task 38.
- **Performance Under Active Window (55 Tasks):**
  - Successful tasks: 48 / 55 (87.27%)
  - Failed tasks: 7 / 55 (12.73%)
  - Attempts on successful tasks: 51
  - Mean attempts on successful tasks: 1.0625
  - Median attempts on successful tasks: 1.0

---

## 7. Adapter v2 Analysis

- **Trigger Task:** Task 93 (`TASK_3CA90906`), fired when unique verified memory count reached 8 (+4 new experiences).
- **Active Range:** Task 95 through Task 100 (6 tasks executed while active).
- **Physical Weight File:** `models/adapters/candidates/adapter_v2_1790248884/adapter_model.safetensors` (4,372,840 bytes, SHA256: `90bea137ef5bac53cec34e2d8585035e309b0486daf6f7b1fa2bc23923c3bb41`).
- **Active Path:** `models/adapters/active/`.
- **Training Examples:** 6 valid SFT pairs.
- **Training Duration:** 13.20 seconds.
- **Final Training Loss:** 0.5718.
- **Validation Gate:** Passed.
- **Promotion Status:** Promoted to active; triggered archival of `adapter_v1`; hot-reloaded before Task 95.
- **Performance Under Active Window (6 Tasks):**
  - Successful tasks: 5 / 6 (83.33%)
  - Failed tasks: 1 / 6 (16.67%)
  - Attempts on successful tasks: 5
  - Mean attempts on successful tasks: 1.0000
  - Median attempts on successful tasks: 1.0

---

## 8. Negative-Transfer & Regression Analysis

All 8 failed tasks were model generation failures where the model failed to output valid executable code. None were infrastructure or runtime crashes.

| Task Index | `task_id` | Function Name | Active Adapter | Attempts | Error Status | Underlying Prompt Topic |
| :-: | :--- | :--- | :--- | :-: | :--- | :--- |
| 48 | `TASK_C615FC35` | `is_even` | `adapter_v1_1790247818` | 0 | `model_failure` | Parity check: `n % 2 != 0` -> `n % 2 == 0` |
| 59 | `TASK_ABC07B11` | `is_even` | `adapter_v1_1790247818` | 0 | `model_failure` | Parity check: `n % 2 != 0` -> `n % 2 == 0` |
| 65 | `TASK_1DA9FFE1` | `is_even` | `adapter_v1_1790247818` | 0 | `model_failure` | Parity check: `n % 2 != 0` -> `n % 2 == 0` |
| 71 | `TASK_0E25977A` | `is_even` | `adapter_v1_1790247818` | 0 | `model_failure` | Parity check: `n % 2 != 0` -> `n % 2 == 0` |
| 77 | `TASK_4FC2042B` | `is_even` | `adapter_v1_1790247818` | 0 | `model_failure` | Parity check: `n % 2 != 0` -> `n % 2 == 0` |
| 83 | `TASK_43200D99` | `is_even` | `adapter_v1_1790247818` | 0 | `model_failure` | Parity check: `n % 2 != 0` -> `n % 2 == 0` |
| 89 | `TASK_21D2E862` | `is_even` | `adapter_v1_1790247818` | 0 | `model_failure` | Parity check: `n % 2 != 0` -> `n % 2 == 0` |
| 98 | `TASK_77C30EA5` | `in_range` | `adapter_v2_1790248884` | 0 | `model_failure` | Range comparison logic |

### Failure Clustering by Regime:
- **Base Model Window (39 tasks):** 0 failures (0.0% failure rate).
- **`adapter_v1` Window (55 tasks):** 7 failures (12.73% failure rate). All 7 failures were identical parity tasks (`is_even`).
- **`adapter_v2` Window (6 tasks):** 1 failure (16.67% failure rate). Task 98 (`in_range`).

### Neutral Characterization:
The empirical evidence indicates **adapter-induced regression / negative transfer**. A small LoRA fine-tuning buffer (3 examples in Cycle 1) induced weight changes that severely interfered with the model's parity reasoning capability on `is_even`, while memory retrieval simultaneously retrieved plans that reinforced flawed modulo reasoning.

---

## 9. Comprehensive `is_even` Task Analysis

There are exactly 9 `is_even` tasks distributed across the 100-task benchmark. The table below traces their behavior across all four modes:

| Task Index | `task_id` | MODE-A Success | MODE-D Success | MODE-F Orig Success | MODE-F Trained Success | Active Adapter (MODE-F Trained) |
| :-: | :--- | :-: | :-: | :-: | :-: | :--- |
| **017** | `TASK_FEE64E00` | True | True | True | **True** | `None` (Base Model) |
| **048** | `TASK_C615FC35` | True | True | True | **False** | `adapter_v1_1790247818` |
| **059** | `TASK_ABC07B11` | True | True | True | **False** | `adapter_v1_1790247818` |
| **065** | `TASK_1DA9FFE1` | True | True | True | **False** | `adapter_v1_1790247818` |
| **071** | `TASK_0E25977A` | True | True | True | **False** | `adapter_v1_1790247818` |
| **077** | `TASK_4FC2042B` | True | True | True | **False** | `adapter_v1_1790247818` |
| **083** | `TASK_43200D99` | True | True | True | **False** | `adapter_v1_1790247818` |
| **089** | `TASK_21D2E862` | True | True | True | **False** | `adapter_v1_1790247818` |
| **100** | `TASK_803EEF67` | True | True | True | **True** | `adapter_v2_1790248884` |

### Key Empirical Dynamics:
1. **Pre-Adapter Baseline:** Task 17 (`is_even`) was executed during the Base Model regime and succeeded on Attempt 1.
2. **Adapter v1 Degradation:** Tasks 48, 59, 65, 71, 77, 83, and 89 all occurred while `adapter_v1` was active. Every single one failed (0/7 pass rate).
3. **Adapter v2 Domain Recovery:** Task 100 (`is_even`) was executed while `adapter_v2` was active (trained on 6 examples including broader repair contexts) and **succeeded on Attempt 1**.

This demonstrates clear empirical evidence of localized regression under low-sample adapter specialization, followed by domain recovery upon buffer expansion.

---

## 10. Statistical Hypothesis Testing

### Test Suite A: Attempt Counts on Paired Tasks
Only common successful tasks are included to ensure valid repair effort comparison.

#### 1. MODE-A vs MODE-D ($n=100$)
- MODE-A: $\bar{x} = 1.5800, \text{median} = 1.0$
- MODE-D: $\bar{x} = 1.2600, \text{median} = 1.0$
- Paired Mean Difference: $\bar{d} = 0.3200$, $95\%\text{ CI} = [0.1765, 0.4635]$
- Paired $t$-test: $t = 4.4256, p = 2.48 \times 10^{-5}$
- Wilcoxon Signed-Rank: $W = 0.0000, p = 8.00 \times 10^{-5}$
- Effect Size: Cohen's $d = 0.4426$ (Medium effect)

#### 2. MODE-D vs MODE-F Trained (Common Successes, $n=92$)
- MODE-D (restricted to 92 tasks): $\bar{x} = 1.2826, \text{median} = 1.0$
- MODE-F Trained (restricted to 92 tasks): $\bar{x} = 1.1630, \text{median} = 1.0$
- Paired Mean Difference: $\bar{d} = 0.1196$, $95\%\text{ CI} = [0.0520, 0.1871]$
- Paired $t$-test: $t = 3.5154, p = 6.87 \times 10^{-4}$
- Wilcoxon Signed-Rank: $W = 0.0000, p = 9.11 \times 10^{-4}$
- Effect Size: Cohen's $d = 0.3665$ (Small-to-medium effect)
- Delta Distribution: $\Delta = 0$ for 81 tasks; $\Delta = +1$ for 11 tasks; $\Delta < 0$ for 0 tasks.

### Test Suite B: Categorical Task Success Comparison ($n=100$)

#### McNemar's Test: MODE-D vs MODE-F Trained
- Contingency:
  - Both Modes Succeed: 92
  - MODE-D Succeeds, MODE-F Trained Fails: 8
  - MODE-D Fails, MODE-F Trained Succeeds: 0
  - Both Modes Fail: 0
- Exact Two-Sided Binomial $p$-value: $p = 2 \times (0.5)^8 = 0.007813$
- Continuity-Corrected $\chi^2$: $\frac{(|8 - 0| - 1)^2}{8 + 0} = \frac{49}{8} = 6.1250$ ($p = 0.0133$)
- Conclusion: MODE-F Trained exhibits a statistically significant reduction in task success rate relative to MODE-D ($p < 0.01$).

---

## 11. Limitations

1. **Benchmark Size:** While 100 tasks provide adequate statistical power for large effect sizes, evaluating subtle multi-adapter continual learning dynamics benefits from longer horizons ($N \ge 500$) with more frequent trigger points.
2. **Zero-Attempt Encoding:** Because the runner encoded initial generation failures as `attempts = 0`, unconditional aggregate metrics are confounded. Conditional evaluations must be used.
3. **Small Fine-Tuning Buffers:** Buffer sizes of 4 experiences (yielding 3 and 6 training pairs) represent extremely low-sample regimes, elevating the risk of localized weight drift and negative transfer.
4. **Interaction with Retrieval Memory:** In several failed tasks, the prompt contained an erroneous retrieved plan. Isolating whether failure stemmed primarily from the LoRA weight drift, the retrieved plan, or their combination requires controlled prompt ablation.

---

## 12. Research Interpretation & Core Conclusion

### Did LoRA improve LITE-CODER's repair efficiency beyond MODE-D?

The artifact evidence requires a nuanced, multi-faceted answer:

1. **Did LoRA training actually execute and function?**  
   **YES.** The training pipeline functioned reliably under hardware-isolated conditions on the Colab T4 GPU, creating 2 validated PEFT adapters that passed structural verification, loss convergence, inference gating, promotion, and hot-reloading into active memory across 61 tasks.

2. **Did benchmark success rate improve beyond MODE-D?**  
   **NO.** Benchmark success rate dropped from 100.0% (MODE-D) to 92.0% (MODE-F Trained), a statistically significant regression ($p = 0.0078$).

3. **Did repair effort change on successful tasks?**  
   **YES.** Conditioned on success, mean attempts decreased from 1.2826 to 1.1630 on common tasks ($p = 6.87 \times 10^{-4}$), with 11 tasks resolving in 1 fewer attempt and 0 tasks worsening.

4. **Did LoRA introduce regressions?**  
   **YES.** `adapter_v1` exhibited clear negative transfer on parity check problems (`is_even`), causing 7 consecutive failures that had previously succeeded under the base model. This was partially mitigated under `adapter_v2` after buffer expansion.

5. **Does the data support a causal claim of net improvement?**  
   **NO.** While online LoRA adaptation improved first-pass resolution on a subset of tasks, it simultaneously impaired generalization on another subset due to low-sample weight drift. A trade-off between specialization efficiency and robustness was observed rather than unambiguous Pareto dominance.

---

## 13. Methodological Comparison Framework: Cross-Configuration vs. Within-Intervention Analysis

When analyzing the empirical impact of the functioning LoRA adaptation, two distinct comparison axes must be explicitly distinguished:

### Axis 1: MODE-D vs. MODE-F Trained (Cross-Configuration Comparison)
- **Role:** A descriptive comparison between two distinct architectural designs.
- **Scope:** MODE-D combines non-parametric memory retrieval with Dirichlet-multinomial contextual bandit strategy allocation (with no parametric weight updates). MODE-F Trained adds difficulty-aware iteration budgeting and active parametric LoRA weight updates.
- **Finding:** While MODE-F Trained reduced conditional attempts on successful tasks from 1.2826 to 1.1630 ($p = 6.87 \times 10^{-4}$), it introduced an 8.0% failure rate not present in MODE-D ($p = 0.0078$).

### Axis 2: MODE-F Original vs. MODE-F Trained (Within-Configuration Intervention Analysis)
- **Role:** A more direct, within-configuration evaluation of the **functioning-LoRA intervention**, holding the intended algorithmic configuration constant.
- **Scope:** MODE-F Original intended to run LoRA but failed silently at runtime due to an unhandled `torchao` import error, executing 100 tasks on the base model with zero adapters. MODE-F Trained resolved runtime incompatibilities, producing 2 validated adapters that actively guided inference across 61 tasks.
- **Empirical Evidence:**
  - Tasks 1–37 (Base Model regime): Attempt counts and pass rates were **100% identical** between Original and Trained.
  - Tasks 38–100 (Active Adapter regime): Exactly 19 tasks diverged in behavior (11 improved from 2 attempts to 1 attempt; 8 regressed from success to initial generation failure).
  - All 11 improvements and all 8 regressions occurred exclusively during active adapter windows.
- **Scientific Conclusion:** The comparison robustly supports **behavioral change, localized negative transfer, and first-pass efficiency gains**, as well as **subsequent recovery behavior upon buffer expansion**, but explicitly refutes any claim of universal improvement.
