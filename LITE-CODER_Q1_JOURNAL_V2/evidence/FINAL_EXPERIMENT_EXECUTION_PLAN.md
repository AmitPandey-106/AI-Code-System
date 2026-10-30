# FINAL EXPERIMENT EXECUTION PLAN

## REQUIRED EXPERIMENTS BY RQ

**RQ1 (Memory effectiveness): Existing evidence sufficient? NO.**
- **Exact experiment required:** Re-run Mode A and Mode D ensuring memory strictly starts empty, logging memory admissions sequentially.
- **Expected output:** Clean success rates; `repair_memory.json` growth over time.

**RQ2 (Repair-effort reduction): Existing evidence sufficient? NO.**
- **Exact experiment required:** Task-level extraction of `attempts_used` from the clean Mode A and Mode D runs.
- **Expected output:** Distribution boxplot of attempts.

**RQ3 (Ablation / Component): Existing evidence sufficient? NO.**
- **Exact experiment required:** Verify LoRA training dataset isolation. If clean, extract success rates for Mode F.
- **Expected output:** Table comparing Base, Base+Memory, LoRA, LoRA+Memory.

**RQ4 (Verification/Contamination): Existing evidence sufficient? NO.**
- **Exact experiment required:** Mode D_SAFE (Base + Memory + AST Oracle) vs Adversarial Dataset.
- **Expected output:** Contamination rejection rate table.

**RQ5 (Computational overhead): Existing evidence sufficient? NO.**
- **Exact experiment required:** Extract latency timestamps from Mode D run.
- **Expected output:** Average retrieval latency (ms).

---

## PRIORITIZED EXPERIMENT PLAN

1. **CRITICAL:** Re-run/Audit Mode A vs Mode D (Base Oracle, Clean Memory Start).
2. **CRITICAL:** Re-run/Audit Mode A_SAFE vs Mode D_SAFE (AST Oracle, Clean Memory Start) to allow fair comparison of safety's impact on success.
3. **CRITICAL:** Adversarial Injection Test on Mode D_SAFE.
4. **HIGH VALUE:** Mode F vs Mode F_SAFE (Assuming LoRA training is isolated).
5. **OPTIONAL:** Embedding dimension ablations.
6. **DO NOT RUN:** LoRA hyperparameter sweeps.

---

## FINAL RECOMMENDED EXPERIMENT MATRIX

| Experiment ID | Configuration | Memory | LoRA | SAFE | Benchmark | Seed | Purpose | RQ | Metric |
|---|---|---|---|---|---|---|---|---|---|
| **EXP_01** | Baseline | Off | Off | Off | 100-task | 42 | Establish zero-shot baseline | RQ1 | Success % |
| **EXP_02** | Memory | On | Off | Off | 100-task | 42 | Measure online experience | RQ1, RQ2 | Success %, Attempts |
| **EXP_03** | SAFE_Base | Off | Off | On | 100-task | 42 | Establish SAFE strictness baseline | RQ4 | Success % |
| **EXP_04** | SAFE_Memory | On | Off | On | 100-task | 42 | Memory performance under strict verification | RQ1, RQ4 | Success % |
| **EXP_05** | LoRA_Base | Off | On | Off | 100-task | 42 | Parameter adaptation baseline | RQ3 | Success % |
| **EXP_06** | Contamination | On | Off | On | Security Set | 42 | Measure verification integrity | RQ4 | Rejection % |

---

## FINAL SCIENTIFIC CHECK

1. **Can we prove memory improves repair without confounding factors?** NO. We must prove memory starts empty.
2. **Can we distinguish memory benefit from SAFE benefit?** NO. We need EXP_03 and EXP_04 to isolate the oracle change.
3. **Can we distinguish memory from LoRA parameter adaptation?** NO. We must audit the LoRA training set for leakage first.
4. **Can we establish whether memory was clean at evaluation start?** NO. The 8 records currently present must be hashed/traced.
5. **Can we quantify repair effort?** YES, pending script extraction.
6. **Can we quantify retrieval contribution?** YES, comparing EXP_01 and EXP_02.
7. **Can we evaluate contamination resistance separately?** YES, via EXP_06.
8. **Can we reproduce the final results?** YES, seeds and configs are locked.
