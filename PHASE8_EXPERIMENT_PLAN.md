# LITE-Coder Phase 8 — Autonomous Engineering Experiment Plan

**Document Version:** 1.0.0  
**Date:** October 24, 2026  
**Status:** ACTIVE / BASELINE FROZEN  
**Target Architecture:** LITE-Coder Autonomous Engineering Architecture (Phase 8)  
**Base Repository Commit:** `b940fa3` (`audit/phase7c-integrity`)  
**Active Working Branch:** `feat/phase8-autonomous-engineering`  
**Model Identifier:** `Qwen/Qwen2.5-Coder-1.5B-Instruct` (Local CPU / Colab T4)  

---

## 1. Executive Summary & Research Motivation

Phase 7C established a reproducible 20-task multi-repository generalization benchmark across three independent Python codebases (`micro_http`, `task_flow`, `data_synth`). The experimental integrity audit (`PHASE7C_EXPERIMENTAL_INTEGRITY_AUDIT.md`) uncovered several critical architectural findings:
1. **Fallback Synthesizer Inactivity:** AST fallback synthesis was 100% idle because prompting compliance produced syntactically present SEARCH blocks whose dry-run application failed on non-matching source slices, causing prompt-based retries rather than dynamic AST fallback.
2. **Strategy and Memory Disconnection:** `RepairMemory` indexing and `StrategySelector` reward updates were not dynamically invoked during session completion, leaving memory indices empty (`[]`) and strategies running on static baseline mappings.
3. **Multi-File Horizon Ceiling:** Small local models (1.5B parameters) achieved 0.0% completion (0/5) on coordinated multi-file edits when required to generate multi-file diffs in a single prompt context.
4. **Command Execution Boundary:** Subprocess execution required rigorous allowlisting, tokenized parsing, and environment sanitization to prevent arbitrary script invocation (`python -c`) and shell chaining attacks.

Phase 8 designs, implements, and evaluates an **Autonomous Engineering Architecture** that resolves each bottleneck while preserving complete safety, transaction integrity, and experimental reproducibility.

---

## 2. Research Questions (RQs)

- **RQ1 (Multi-Repository Generalization):** Does the integrated autonomous engineering framework significantly outperform raw LLM prompting and prompt-example baselines across diverse codebases without repository overfitting?
- **RQ2 (Dynamic AST Fallback Synthesis):** Does triggering AST-based single-function synthesis upon dry-run patch validation failure recover failed repairs from malformed or misaligned SEARCH blocks without weakening AST validity?
- **RQ3 (Verified Experience Memory):** Does strict gatekeeping of repair memories (ingesting only native test-passed, oracle-verified patches) prevent catastrophic memory poisoning and improve retrieval relevance for recurring bug patterns?
- **RQ4 (Adaptive Strategy Bandit):** Does online reinforcement learning across repair strategies (`DIRECT_REPAIR`, `EXPERIENCE_GUIDED_REPAIR`, `TEST_GUIDED_REPAIR`, `MINIMAL_PATCH`, `STRUCTURAL_REPAIR`, `ALTERNATIVE_REPAIR`) converge towards optimal strategies for specific failure classifications?
- **RQ5 (Sequential Multi-File Orchestration):** Does decomposing multi-file changes into sequential single-file transactions with byte-level rollback capability break the 0.0% multi-file barrier without leaving dirty working trees upon failure?
- **RQ6 (Negative Safety Enforcement):** Does the hardened command validator (`shell=False`, tokenized argument allowlist, environment sanitization) maintain 100% rejection of code injection, path traversal, subshell chaining, and stale mutations without false rejections of valid pytest suites?

---

## 3. Experimental Design & Task Matrix

The benchmark comprises 20 tasks across 3 synthetic, clean, MIT/Apache-2.0/BSD-3-Clause Python repositories:

| Category | Tasks | Task Count | Description | Primary Failure Mechanism |
| :--- | :--- | :---: | :--- | :--- |
| **Category 1: Single-Function Bugfix** | Tasks 01–05 | 5 | Targeted isolated function logic defects | Off-by-one, regex, exception logic |
| **Category 2: Class-Method Bugfix** | Tasks 06–10 | 5 | Object-oriented state, lifecycle, inheritance | State corruption, argument mismatch |
| **Category 3: Coordinated Multi-File** | Tasks 11–15 | 5 | Dependent interfaces spanning 2+ files | Cross-module contract synchronization |
| **Category 4: Negative Safety Controls** | Tasks 16–20 | 5 | Adversarial injections, path escapes, paradoxes | Shell chaining, traversal, arbitrary code |
| **Total Benchmark** | Tasks 01–20 | **20** | **Comprehensive Engineering Evaluation** | **Cross-Repository Generalization** |

### Evaluated Repositories
1. **`micro_http` (MIT):** Minimal HTTP router, request parser, response serializer, and middleware chain.
2. **`task_flow` (Apache-2.0):** Directed acyclic graph (DAG) task engine with dependency resolution, context passing, and execution cycles.
3. **`data_synth` (BSD-3-Clause):** Tabular DataFrame manipulation, statistical routines, missing value imputation, and feature transforms.

---

## 4. Evaluated Architectural Configurations

To rigorously isolate component contributions, Phase 8 defines five formal ablation configurations:

| Config | Configuration Name | Repo Index | 1-Shot Delimiter | AST Fallback | Repair Memory | Strategy Learning | Multi-File Orchestrator | Safety Guards |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** | **Raw Model Baseline** | Disabled | Disabled | Disabled | Disabled | Disabled | Disabled | Active |
| **B** | **Prompt Example Only** | Disabled | Enabled | Disabled | Disabled | Disabled | Disabled | Active |
| **C** | **Repo Index Enabled** | Enabled | Enabled | Disabled | Disabled | Disabled | Disabled | Active |
| **D** | **Repo Index + Dynamic Fallback** | Enabled | Enabled | Dynamic Trigger | Disabled | Disabled | Disabled | Active |
| **E** | **Autonomous Framework (Full)** | Enabled | Enabled | Dynamic Trigger | Active (FAISS) | Active (Bandit) | Active (Rollback) | Hardened |

---

## 5. Statistical Protocol & Denominator Integrity

Following the audit findings in Phase 7C, all reporting strictly enforces:
1. **Disaggregated Metric Reporting:**
   - **Functional Task Completion ($N=15$):** Single-function, class-method, and multi-file repair tasks (Tasks 01–15).
   - **Safety Control Rejection ($N=5$):** Preflight command blocking, traversal rejection, paradox halting, stale source invalidation (Tasks 16–20).
   - **Overall Benchmark Completion ($N=20$):** Combined task pass rate.
2. **Wilson Score 95% Confidence Intervals:**
   Binomial proportion confidence intervals computed with $z = 1.95996$ for all rates:
   $$\hat{p} = \frac{k}{n}, \quad CI_{95} = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
3. **Model Call Accounting:**
   Preflight security aborts (where test command is blocked before any session planning or model inference) record `model_calls = 0`.
4. **Transaction Integrity Metric:**
   Zero dirty files or partial mutations remaining in repository trees upon aborted or failed repair sessions.

---

## 6. Reproducibility & Colab Package Specification

- **Primary Archive:** `LITE_CODER_PHASE8_COLAB.zip`
- **Verification Manifest:** `colab/COLAB_PACKAGE_MANIFEST.json`
- **Execution Script:** `colab/run_phase8_colab.py`
- **Target Environments:**
  - Local CPU: Windows 11 / Python 3.10 / PyTorch CPU
  - Google Colab: Ubuntu 22.04 / Python 3.10 / T4 GPU or Standard CPU
- **Exclusion Filters:** Strictly zero private credentials, no `.git` metadata, no cached `.pyc` files, no raw model weight tensors (downloaded on demand from HuggingFace), and no unverified scratch scripts.
