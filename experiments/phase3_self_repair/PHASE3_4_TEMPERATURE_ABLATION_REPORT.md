# LITE-CODER PHASE 3.4: DYNAMIC TEMPERATURE ESCALATION ABLATION REPORT

**Date:** September 29, 2026  
**Investigation Type:** Controlled Temperature-Escalation Ablation  
**System:** LITE-Coder Autonomous Code-Generation and Self-Repair Pipeline  
**Model:** Qwen/Qwen2.5-Coder-1.5B (Local CPU PyTorch Transformers)  
**Control Baseline:** Phase 3.2 (`experiments/phase3_self_repair/results.json`)  
**Experimental Variant:** Phase 3.4 (`experiments/phase3_self_repair/phase3_4_results.json`)  
**Runner:** `experiments/phase3_self_repair/runner_phase3_4.py`

---

## 1. Executive Summary

Phase 3.4 tested the hypothesis:
$$\text{Baseline Prompt (Phase 3.2)} + \text{Default Temp } 0.2 + \text{Escalate Temp } (0.2 \rightarrow 0.6) \text{ ONLY After Repeated Candidate} \longrightarrow \text{Measure Effect}$$

Unlike Phase 3.3 (which bloated the prompt with 12 instructions and caused regressions down to 20%), Phase 3.4 kept the concise Phase 3.2 baseline prompt completely unchanged and held the decoding temperature at 0.2 by default. Only when candidate $N$ matched the hash of candidate $N-1$ was the temperature escalated to 0.6 for the subsequent attempt.

### Primary Empirical Findings
1. **Self-Repair Success Rate: 40.0% (2/5 tasks)**:
   - Succeeded on **TASK_1** (`add`) on Attempt 1.
   - Succeeded on **TASK_2** (`reverse_string`) on Attempt 1.
   - Failed on **TASK_3** (`binary_search`), **TASK_4** (`merge_intervals`), **TASK_5** (`schedule_meetings`).
   - Net performance: **40.0%** (Identical to Phase 3.2 baseline; avoided the -20 pp regression observed in Phase 3.3).
2. **Temperature Escalation Activation on Task 3**:
   - On Task 3 (`binary_search`), Attempt 1 produced hash `779eafeb86b0` (temp 0.2).
   - Attempt 2 reproduced hash `779eafeb86b0` (temp 0.2) $\longrightarrow$ flagged as `REPEATED_CANDIDATE`.
   - Attempt 3 dynamically escalated to **temperature = 0.6**.
   - Attempt 4 dynamically maintained **temperature = 0.6**.
3. **Model Weight Attractor Persistence**:
   Even at temperature = 0.6, Qwen2.5-Coder-1.5B regenerated the exact same candidate hash (`779eafeb86b0`). In a 1.5B model, the canonical tokens for standard binary search are so dominant that raising temperature to 0.6 without logit-level penalties was insufficient to escape the local minimum.
4. **Safety & Negative Controls**:
   All 3 negative controls passed (100%), and all 73 regression tests remained green.

---

## 2. Experimental Condition Comparison

| Dimension | Phase 3.2 Baseline | Phase 3.3 Failure-Guided | Phase 3.4 Dynamic Temperature |
|---|:---:|:---:|:---:|
| **Prompt Structure** | Concise Phase 3.2 | Bloated 12-item protocol | Concise Phase 3.2 |
| **Default Temperature** | 0.2 | 0.2 | 0.2 |
| **Repeated Candidate Action** | Prompt warning only | Prompt warning only | **Dynamic Temperature Escalation to 0.6** |
| **Self-Repair Success Rate** | **40.0% (2/5)** | **20.0% (1/5)** | **40.0% (2/5)** |
| **Total Repeated Candidates** | 3 | 11 | 3 |
| **TASK_1 (`add`)** | SUCCESS | SUCCESS | **SUCCESS** |
| **TASK_2 (`reverse_string`)** | SUCCESS | FAILED (Regressed) | **SUCCESS** (Preserved) |
| **TASK_3 (`binary_search`)** | FAILED | FAILED | FAILED |
| **TASK_4 (`merge_intervals`)** | FAILED | FAILED | FAILED |
| **TASK_5 (`schedule_meetings`)** | FAILED | FAILED | FAILED |

---

## 3. Per-Task Execution Breakdown in Phase 3.4

### Task 1: `add` (Domain: Arithmetic)
- **Temperatures Used:** Attempt 1: 0.2
- **Initial Defect:** Subtraction (`return a - b`), Hash `ead7ab5e4bde`
- **Attempt 1:** Produced Hash `61ccca78448a` (`return a + b`)
- **Outcome:** **SUCCESS (Accepted on Attempt 1)** in 23.15s.

---

### Task 2: `reverse_string` (Domain: String Processing)
- **Temperatures Used:** Attempt 1: 0.2
- **Initial Defect:** Identity return (`return s`), Hash `3edd4616b10e`
- **Attempt 1:** Produced Hash `6d58eae5394a` (recursive divide-and-conquer)
- **Outcome:** **SUCCESS (Accepted on Attempt 1)** in 39.22s.
- *Significance:* Preserved the Phase 3.2 success and avoided the inverted concatenation regression of Phase 3.3.

---

### Task 3: `binary_search` (Domain: Searching)
- **Temperatures Used:**
  - Attempt 1: 0.2 (Hash `779eafeb86b0`, FAILED on `binary_search([2, 2, 2], 2) == 0`)
  - Attempt 2: 0.2 (Hash `779eafeb86b0`, REPEATED_CANDIDATE detected)
  - Attempt 3: **0.6** (Escalated after repeated candidate) $\longrightarrow$ Hash `779eafeb86b0`
  - Attempt 4: **0.6** (Maintained escalated temperature) $\longrightarrow$ Hash `779eafeb86b0`
- **Outcome:** FAILED after 4 attempts (Total runtime 620.94s).
- *Observation:* Temperature escalation alone did not overcome the model's structural bias for this canonical routine.

---

### Task 4: `merge_intervals` (Domain: Interval Processing)
- **Temperatures Used:** Attempt 1: 0.2, Attempt 2: 0.2
- **Attempt 1:** Generated Hash `ac2363545881` calling `intervals.sort()`. Properly intercepted by AST contract validator as `CONTRACT_FAILURE`.
- **Attempt 2:** Model generated `# Your solution here` placeholder; rejected by AST statement validator.
- **Outcome:** FAILED.

---

### Task 5: `schedule_meetings` (Domain: Structured Task)
- **Temperatures Used:** Attempts 1–4: all 0.2 (Each attempt generated a distinct hash, so temperature escalation was never triggered!)
  - Attempt 1: Hash `94ff8faeb23c` (mutating sort)
  - Attempt 2: Hash `079206b51126` (mutating sort)
  - Attempt 3: Hash `855348b5039d` (adapted to non-mutating `sorted()`)
  - Attempt 4: Hash `1d864fd22aa4` (refined boundary)
- **Outcome:** FAILED due to 1.5B model capacity limits on 11 concurrent constraints.

---

## 4. Scientific Conclusions

1. **Safety of Targeted Dynamic Temperature**:
   Restricting temperature escalation strictly to post-repeated attempts ensured that clean, deterministic tasks (Tasks 1 & 2) were completely insulated from high-temperature hallucinations or regressions.
2. **The Limit of Pure Temperature Escalation**:
   On canonical algorithmic tasks like `binary_search`, the token probability distribution in Qwen2.5-Coder-1.5B is heavily peaked. Bumping temperature from 0.2 to 0.6 does not flatten the distribution enough to escape the attractor state without additional interventions (such as negative logit masking, AST rewrite rules, or larger model parameter capacity).
3. **Preservation of Benchmark Integrity**:
   Phase 3.4 maintains the highest verified self-repair rate (40.0%), retains 100% negative control safety, and passes all 73 architecture tests.
