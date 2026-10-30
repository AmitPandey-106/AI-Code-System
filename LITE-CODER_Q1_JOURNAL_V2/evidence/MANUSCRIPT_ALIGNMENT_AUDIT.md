# FINAL MANUSCRIPT-TO-EVIDENCE ALIGNMENT AUDIT

## 1. CLAIM-BY-CLAIM AUDIT

**Claim:** "acquires and reuses verified program-repair experience without requiring continual weight updates."
**Exact manuscript location:** 01_abstract.tex, 02_introduction.tex
**Claim type:** IMPLEMENTATION VERIFIED, PARTIALLY VERIFIED (Experimentally)
**Evidence:** `repair_memory.json` shows 8 records dynamically added in Mode D.
**Evidence file:** `LITECODER_Q1_EVIDENCE_AUDIT.md`
**Experiment:** LITE_CODER_100TASK_MODE_D
**Configuration:** MEMORY_ENABLED=True
**Task count:** 100
**Status:** PARTIALLY VERIFIED (Need full success rate validation vs baseline).
**Required action:** Run extraction to formally show memory hits > 0 resulted in success.

**Claim:** "achieving comparable structural fixes at a fraction of the compute cost of fine-tuning."
**Exact manuscript location:** 01_abstract.tex
**Claim type:** REQUIRES EXPERIMENT
**Evidence:** None yet extracted for side-by-side compute cost or success equality between LoRA and Memory.
**Evidence file:** N/A
**Experiment:** Mode D vs Mode F
**Configuration:** N/A
**Task count:** 100
**Status:** REQUIRES EXPERIMENT
**Required action:** Extract task success rate of Mode F vs Mode D and measure FLOPs/latency.

**Claim:** "Retrieval operations execute in under 100ms"
**Exact manuscript location:** 09_results.tex
**Claim type:** REQUIRES EVIDENCE
**Evidence:** Stated in historical draft, but no raw log metric extracted yet.
**Evidence file:** N/A
**Experiment:** Mode D
**Configuration:** MiniLM CPU
**Task count:** 100
**Status:** REQUIRES EXPERIMENT / EXTRACTION
**Required action:** Parse `raw_tasks/*.json` for retrieval timestamp latency.

**Claim:** "strict gating mechanism ensuring only successfully executed and validated repairs enter the memory"
**Exact manuscript location:** 02_introduction.tex, 06_methodology.tex
**Claim type:** IMPLEMENTATION VERIFIED
**Evidence:** Mentioned in `LITECODER_Q1_EVIDENCE_AUDIT.md` based on architecture.
**Evidence file:** `LITECODER_Q1_EVIDENCE_AUDIT.md`
**Experiment:** N/A
**Configuration:** N/A
**Task count:** N/A
**Status:** IMPLEMENTATION VERIFIED
**Required action:** None for implementation, but needs contamination adversarial test.

## 3. RESEARCH QUESTIONS MATRIX

| RQ | Experiment | Metric | Dataset | Baseline | Evidence Available | Missing Evidence |
|---|---|---|---|---|---|---|
| **RQ1 (Effectiveness)** | Mode D vs Mode A | Success Rate | 100-task benchmark | Mode A | Partial | Final aggregate numerical comparison |
| **RQ2 (Repair effort)** | Mode D vs Mode A | Avg Attempts | 100-task benchmark | Mode A | Partial | Distribution of attempts |
| **RQ3 (Components)** | Mode D vs Mode F | Success Rate | 100-task benchmark | Mode A | No | Mode F LoRA side-by-side run results |
| **RQ4 (Safety/Adversarial)** | Mode F_SAFE vs Mode D | Contamination Rate | Security dataset | Mode D | No | REQUIRES EXPERIMENT (Full Mode F_SAFE) |
| **RQ5 (Overhead)** | Mode D | Latency (ms) | 100-task benchmark | Mode A | No | Extraction of timestamp logs |

## 4. EXPERIMENTAL FAIRNESS
- **Benchmark:** Mode A, Mode D, and Mode F all claim to use the same 100-task benchmark.
- **Task Set:** Identical.
- **Seed:** `BENCHMARK_SEED = 42` used uniformly.
- **Test Oracle Fairness Issue:** Mode A and D historically used `exec()` which might have false positives (namespace pollution). `Mode F_SAFE` uses AST validation. Comparing Mode D success rates to Mode F_SAFE success rates directly may be **UNFAIR** because F_SAFE has a stricter oracle.
- **Required Action:** Run Mode D with AST validation (e.g., Mode D_SAFE) to ensure an apples-to-apples oracle comparison.

## 5. DATA LEAKAGE
- **Benchmark tasks in memory:** LEAKAGE STATUS UNKNOWN.
- **Training data overlaps with eval:** LEAKAGE STATUS UNKNOWN for the base Qwen2.5 model.
- **LoRA training data overlaps with benchmark:** LEAKAGE STATUS UNKNOWN.
- **Pre-populated memory:** Mode D memory shows 8 records, it is currently unknown if these were pre-populated before the evaluation or generated dynamically during the evaluation.
- **Required Action:** Audit `raw_tasks/` to confirm memory timestamps are strictly sequential and do not contain future tasks.

## 6. MEMORY CLAIMS
- **Representation/Embedding/Similarity:** 384-dimensional MiniLM, FAISS IndexFlatIP, Cosine Similarity. (IMPLEMENTATION VERIFIED)
- **Top-K / Threshold:** K=3, Threshold=0.5. (IMPLEMENTATION VERIFIED)
- **Verified Experience:** Claimed. (IMPLEMENTATION VERIFIED - but only relative to the oracle used).
- **Prevents Contamination:** (REQUIRES EXPERIMENT - requires adversarial tests to prove).

## 7. SAFE / SECURITY CLAIMS
- **AST / Contracts / Canary / Adversarial controls:** 
  - IMPLEMENTED ONLY and TESTED (in `tests/*security*.py`).
  - NOT BENCHMARKED. The full `MODE_F_SAFE` 100-task evaluation is explicitly pending.

## 8. PERFORMANCE CLAIMS
- **"<100ms retrieval overhead":** REQUIRES EVIDENCE. No extracted logs verify this currently.
- **"reduces iterative generation cycles":** REQUIRES EVIDENCE. Task-level parsing of `attempts_used` is required.

## 9. STATISTICAL CLAIMS
- The manuscript correctly uses "positive shift" rather than "statistically significant improvement". 
- No unsupported statistical claims (p-values, effects) currently exist in the V2 manuscript.

## 11. MINIMUM REQUIRED EXPERIMENTS
**CRITICAL 1: Full Scale Benchmark Matrix (Apples-to-Apples)**
- **Objective:** Finalize success rates across identical oracles.
- **Configuration:** Mode A, Mode D, Mode F using the exact same SAFE oracle (AST).
- **Dataset:** 100-task benchmark.
- **Expected Output:** `benchmark_comparison.csv` with identical strictness.

**CRITICAL 2: Adversarial Contamination Test (RQ4)**
- **Objective:** Prove that verification-gated memory rejects false/malicious fixes.
- **Configuration:** Mode D (Unsafe) vs Mode D_SAFE (AST).
- **Dataset:** `tests/test_fault_injection.py` converted to a mini-benchmark.
- **Expected Output:** Contamination rate table.

**CRITICAL 3: Latency & Effort Extraction (RQ2, RQ5)**
- **Objective:** Prove <100ms latency and reduced attempts.
- **Expected Output:** Distribution of `attempts_used` and `retrieval_time_ms`.

## 12. REVIEWER ATTACK TEST
**A. Novelty:** *Reviewer: "RAG for code is not new."* -> **Resolve:** Emphasize that storing exact error-message-to-AST-verified-patch trajectories in a dynamic feedback loop for edge LLMs is the specific novelty.
**B. Baseline fairness:** *Reviewer: "Mode A used exec(), F_SAFE used AST, your success rates aren't comparable."* -> **Resolve:** Must run all modes with the SAFE evaluator.
**D. Data Leakage:** *Reviewer: "Did the memory index contain solutions from the test set before the run started?"* -> **Resolve:** Sequentially log memory admissions and prove index was empty at Task 0.
**E. Statistical validity:** *Reviewer: "Is the reduction in attempts just variance?"* -> **Resolve:** Conduct paired t-tests (or Wilcoxon signed-rank) on task-level attempts between Mode A and Mode D.

## 13. FINAL DECISION
**PAPER READINESS: NOT READY**
(Requires the CRITICAL experiments to extract exact numerical evidence and ensure oracle fairness).
