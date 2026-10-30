# HISTORICAL SAFE CONFIGURATION AUDIT

## 1. Executive Verdict
**REQUIRES_CONFIGURATION_FIX**
The proposed experimental configuration for `EXP-03_SAFE_BASELINE` (Memory=OFF, SAFE=ON, LoRA=OFF) is a functional contradiction according to historical repository evidence. The only historically implemented "SAFE" mechanism in LITE-Coder is the LoRA Canary Gate (`LORA_CANARY_ENABLED`), which evaluates continuous adapter promotion. If `LoRA = OFF`, the Canary Gate is never executed. Alternatively, AST/Security validation (`app/security.py`) is hardcoded as unconditional baseline behavior for all executions and cannot be toggled via a "SAFE" oracle flag. Therefore, a "SAFE=ON" state with "LoRA=OFF" does not exist in the historical codebase.

## 2. Historical SAFE Experiment Locations
- **Runner Wrapper**: `scripts/run_mode_f_safe_100.py`
- **Manifest**: `experiments/LITE_CODER_MODE_F_SAFE/experiment_manifest.json`
- **Metrics**: `experiments/LITE_CODER_MODE_F_SAFE/metrics.json`
- **Implementation (Canary Gate)**: `app/canary.py`
- **Implementation (AST Validation)**: `app/security.py`

## 3. Exact Historical SAFE Entry Point
1. **Executing Function**: `app.canary.evaluate_canary_gate` (Invoked strictly via `train_worker.py` during adapter training).
2. **Invoking Runner**: `benchmark.runner.run_benchmark` via `scripts/run_mode_f_safe_100.py`.
3. **Exact Mode String**: `MODE_F`
4. **Exact Command**: `python scripts/run_mode_f_safe_100.py`
5. **Config Flags**: `LORA_CANARY_ENABLED = True`, `LORA_REPLAY_SIZE = 4`, `LORA_REPLAY_STRATEGY = "all"`
6. **Oracle**: The standard execution oracle (`app.executor.execute_code`). No "SAFE" oracle string exists.
7. **Implementation Mechanism**: Canary Gate & Experience Replay (Adapter Rollback).

## 4. Exact Historical Mode Name
The actual mode passed to the benchmark runner was strictly **`MODE_F`**. The script `run_mode_f_safe_100.py` simply augmented `MODE_F` by dynamically injecting `LORA_CANARY_ENABLED=True` into the global `config`.

## 5. Historical SAFE Configuration
- **mode name**: `MODE_F` (CONFIRMED)
- **memory setting**: `True` (CONFIRMED)
- **SAFE setting**: `LORA_CANARY_ENABLED=True` (CONFIRMED)
- **LoRA setting**: `True` (CONFIRMED)
- **oracle**: STANDARD EXEC (NOT CONFIRMED that a "SAFE" oracle exists)
- **seed**: `42` (CONFIRMED)
- **model**: `Qwen/Qwen2.5-Coder-1.5B` (CONFIRMED)
- **dataset hash**: `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620` (CONFIRMED)
- **task count**: `100` (CONFIRMED)

## 6. Dataset/Task/Hash Verification
- **Dataset**: `data/benchmark/v1.0/dataset.json`
- **Task count**: `100`
- **SHA256**: `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`
- **Overlap with canonical**: 100%

## 7. Historical Result Evidence
From `experiments/LITE_CODER_MODE_F_SAFE/metrics.json`:
- **Tasks evaluated**: 100
- **Successful tasks**: 100
- **Success rate**: 1.0 (100%)
- **Attempts**: 1.26 average
- **Latency**: 15658.18 ms average
- **Status**: COMPLETE_100_TASK

## 8. SAFE Execution Call Graph
```
scripts/run_mode_f_safe_100.py
        ↓
benchmark.runner.run_benchmark(mode="MODE_F")
        ↓
app.main.generate
        ↓
app.executor.execute_code (Executes AST app.security.validate_code unconditionally)
        ↓
train_worker.run_training_pipeline (Executed if Repair Success)
        ↓
app.canary.evaluate_canary_gate (The actual SAFE Gate mechanism)
        ↓
Adapter Promotion / Rollback
```

## 9. EXP-03 Recommended Configuration
Because historical SAFE depends entirely on LoRA, the requested `EXP-03` setup is technically invalid.
- **experiment**: EXP-03_SAFE_BASELINE
- **memory**: OFF
- **safe**: NOT CONFIRMED (Impossible without LoRA ON)
- **lora**: OFF
- **oracle**: NOT CONFIRMED (No "SAFE" oracle parameter exists)
- **seed**: 42
- **dataset**: `data/benchmark/v1.0/dataset.json`
- **dataset_hash**: `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`

## 10. EXP-04 Recommended Configuration
- **experiment**: EXP-04_SAFE_MEMORY
- **memory**: ON
- **safe**: NOT CONFIRMED
- **lora**: OFF
- **oracle**: NOT CONFIRMED
- **seed**: 42
- **initial memory state**: EMPTY (Confirmed method: `benchmark.runner.reset_state()`)

## 11. Memory Isolation Requirements
- **EMPTY_INITIAL_STATE_METHOD**: CONFIRMED (`repair_memory.index.reset()` via `benchmark/runner.py:reset_state()`).
- **CROSS_RUN_CONTAMINATION_RISK**: HIGH. The historical runner reads and mutates global files (`data/repair_memory.json` and `data/repair_memory_index.faiss`). Absolute path redirection via a pre-execution adapter (as established in V4) is strictly required to prevent EXP-04 from bleeding into subsequent runs.

## 12. Comparability Assessment
**PARTIALLY_COMPARABLE**
The dataset identity, task count, and benchmark hash are perfectly identical (100% overlap). However, the requested configuration for `EXP-03/04` sets `LoRA=OFF`, whereas the only historical execution of the SAFE mechanism was conducted with `LoRA=ON` (`MODE_F_SAFE`).

## 13. Unknown/Unconfirmed Fields
- The existence of an `oracle="SAFE"` argument or equivalent CLI flag is entirely **NOT CONFIRMED**. The codebase uses `execute_code()` as the single execution boundary.
- A "SAFE" mode distinct from continuous LoRA adaptation is **NOT CONFIRMED**.

## 14. Final Recommendation
**REQUIRES_CONFIGURATION_FIX**

---
SOURCE CODE MODIFIED: NO
BENCHMARK MODIFIED: NO
HISTORICAL RESULTS MODIFIED: NO
EXPERIMENTS EXECUTED: NO
EXP-01 MODIFIED: NO
EXP-02 MODIFIED: NO
