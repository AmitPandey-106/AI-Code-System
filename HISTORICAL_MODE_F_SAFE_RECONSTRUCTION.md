# HISTORICAL MODE_F_SAFE RECONSTRUCTION

## 1. Exact historical MODE_F configuration
- **Memory**: ON
- **Adaptive Strategy Learning**: ON
- **Difficulty-Aware Allocation**: ON
- **LoRA**: ON
- **Source**: `benchmark/ablation.py` explicitly enables `MEMORY_ENABLED=True`, `STRATEGY_LEARNING_ENABLED=True`, `LORA_ENABLED=True`, `DIFFICULTY_ALLOCATION_ENABLED=True`.

## 2. Exact historical SAFE configuration
- **Mode string**: `MODE_F`
- **Config Flags injected via wrapper**: 
  - `LORA_CANARY_ENABLED = True`
  - `LORA_REPLAY_SIZE = 4`
  - `LORA_REPLAY_STRATEGY = "all"`
- **Source**: `scripts/run_mode_f_safe_100.py`

## 3. Whether SAFE requires LoRA
- **YES**. The SAFE mechanism (Canary Gate + Replay) exclusively operates during the training and promotion of continuous LoRA adapters. Without `LORA_ENABLED=True`, the `train_worker.py` pipeline is not invoked, rendering the Canary Gate dead code.

## 4. Whether SAFE requires Memory
- **YES**. Historically, `MODE_F_SAFE` was executed via `scripts/run_mode_f_safe_100.py` which explicitly sets `MEMORY_ENABLED = True`. There is no historical evidence of a memory-ablated SAFE configuration (`MODE_A_SAFE` or `MODE_E_SAFE`).

## 5. Whether SAFE requires Replay
- **YES**. Replay is explicitly configured alongside the Canary Gate (`LORA_REPLAY_SIZE=4`, `LORA_REPLAY_STRATEGY="all"`) to provide adapter rollback and stability against negative transfer.

## 6. Exact Canary Gate behavior
- **Mechanism**: After a successful repair attempt, the continuous learning pipeline (`train_worker.run_training_pipeline`) trains a new LoRA adapter. Before promoting this adapter to `active`, it is evaluated against a deterministic suite of canary tests (`app/canary.py`). If it fails the `LORA_CANARY_PASS_THRESHOLD`, the candidate is rejected, and the previous stable adapter is rolled back/preserved.

## 7. Exact files implementing the mechanism
- `scripts/run_mode_f_safe_100.py` (Experiment Runner)
- `app/canary.py` (Canary Gate Evaluation Suite)
- `train_worker.py` (Pipeline orchestrating the Canary evaluation)
- `app/config.py` (Configuration flags)

## 8. Exact configuration variables and their values
- `LORA_CANARY_ENABLED`: `True`
- `LORA_CANARY_PASS_THRESHOLD`: `1.0`
- `LORA_REPLAY_SIZE`: `4`
- `LORA_REPLAY_STRATEGY`: `"all"`

## 9. Exact benchmark entry point
- `benchmark.runner.run_benchmark(experiment_id="LITE_CODER_MODE_F_SAFE", mode="MODE_F", size=100, dataset_path="data/benchmark/v1.0/dataset.json")`

## 10. Exact historical experiment naming if recoverable
- `LITE_CODER_MODE_F_SAFE`

## 11. Any uncertainty that remains
- **Architectural Contradiction**: The proposed `EXP-03` configuration (`Memory=OFF`, `LoRA=OFF`, `SAFE=ON`) directly contradicts the historical implementation, as `SAFE` relies entirely on LoRA's training path. There is zero historical evidence of an `oracle="SAFE"` argument or a non-LoRA `SAFE` mode. 

HISTORICAL_CONFIGURATION_NOT_PROVEN
