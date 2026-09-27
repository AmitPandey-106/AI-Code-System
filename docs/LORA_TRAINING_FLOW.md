# LITE-CODER LoRA Training Lifecycle Flow

**Date:** 2026-09-24  
**Project:** LITE-CODER Continual Learning Research  
**Document:** End-to-End Execution Trace and Failure Surface Analysis  
**File:** `docs/LORA_TRAINING_FLOW.md`

---

## 1. Intended Complete Training Cycle

The continuous adaptation lifecycle is intended to progress through 13 sequential stages:

```
[Task Arrival]
      │
      ▼
1. Model Generates Initial Code & Failure Encountered
      │
      ▼
2. Model Generates Repair (Autonomous Retry Loop)
      │
      ▼
3. Execution Verification in Sandbox
      │
      ▼
4. Test Verification (Unit / Property Tests)
      │
      ▼
5. Successful Repair Verification Complete
      │
      ▼
6. Experience Stored in Vector Repair Memory
      │
      ▼
7. SFT Training Example Formatted & Validated
      │
      ▼
8. Training Job Triggered (Synchronous / Controlled Async)
      │
      ▼
9. LoRA Trainer Initializes & Trains on Accumulated Buffer
      │
      ▼
10. Candidate Adapter Saved with Metadata & Evaluation Gating
      │
      ▼
11. Adapter Promoted to Active & Version Incremented
      │
      ▼
12. Inference Engine Reloads Active Adapter Cleanly
      │
      ▼
13. Subsequent Benchmark Task Uses Updated Adapter
```

---

## 2. Detailed Stage-by-Stage Trace and Failure Breakdown

### Stage 1: Initial Generation & Failure
* **Files & Functions:**
  - `benchmark/runner.py`: `run_benchmark()` calls `app/main.py:generate()`
  - `app/main.py`: `generate()` calls `app/model.py:generate_code()`
  - `app/executor.py`: `execute_code()` executes generated Python code
* **Intended Behavior:**
  Initial generated code throws an `AssertionError` or execution error, triggering the repair loop.
* **Failure Modes:**
  - `generate_code()` produces unparseable syntax for all 3 generation attempts, returning empty code.
  - Initial code passes immediately on Attempt 1 (no repair needed $\rightarrow$ no repair memory generated).

---

### Stage 2: Model Generates Repair
* **Files & Functions:**
  - `app/main.py`: loop over `MAX_RETRIES` (attempts 1 to 5)
  - `app/repair_difficulty.py`: `estimate_difficulty()`
  - `app/strategy_selector.py`: `select_strategy()`
  - `app/model.py`: `fix_code()`
* **Intended Behavior:**
  `fix_code()` takes broken code, error traceback, and optional memory/strategy prompt, producing a valid repaired program.
* **Failure Modes:**
  - `fix_code()` returns invalid Python or empty code across all retry attempts.
  - Model fails to produce a program that changes code (`repair_changed_code == False`).
  - Max retries (5) exhausted without repair.

---

### Stage 3 & 4: Execution & Test Verification
* **Files & Functions:**
  - `app/executor.py`: `execute_code()`
  - `app/tester.py`: `run_tests()`
* **Intended Behavior:**
  Repaired code executes with syntax pass, safety pass, execution pass, and authoritative tests pass (`tests["success"] == True`).
* **Failure Modes:**
  - Security violation (`SecurityViolation`) raised by AST sandbox.
  - Infinite loop or timeout (`TimeoutError`).
  - Assertion failure on authoritative tests.

---

### Stage 5 & 6: Successful Repair Experience Stored
* **Files & Functions:**
  - `app/main.py`: lines 310–330
  - `app/repair_memory.py`: `RepairMemory.add_repair_experience()`
* **Intended Behavior:**
  `add_repair_experience` checks that `error_message`, `broken_code`, and `successful_fix` are non-empty. It checks for exact duplicate experiences in `self.memories`. If unique, it embeds via `sentence-transformers`, adds to FAISS index, appends to `data/repair_memory.json`, and returns `True`.
* **Break Points Identified:**
  - **Duplicate Rejection:** If the exact same error and code was seen previously, `add_repair_experience()` returns `False`. In `app/main.py`, `memories_added` remains `False`, bypassing the training trigger.
  - **Memory Persistence Failure:** File write error or FAISS index corruption on disk.

---

### Stage 7: Training Example Formatted & Validated
* **Files & Functions:**
  - `app/training_dataset.py`: `build_dataset()`, `validate_training_experience()`, `build_training_example()`
* **Intended Behavior:**
  Reads `data/repair_memory.json`. Filters memories ensuring `success == True`, verification flags are `True`, and no security/timeout errors. Formats examples and splits into train/val/test splits.
* **Break Points Identified:**
  - **Format Inconsistency:** Training example uses `"Fix this Python code:\n\n{broken}\n\nError:\n{error}\n\nCorrect Code:\n{fix}\n"` while inference uses a much longer system prompt with different headers.
  - **Truncation Data Loss:** Truncating at 512 tokens with `truncation=True` chops the target code off at the right end for long tasks.
  - **Zero Loss Masking:** Input tokens are not masked with `-100`, forcing the model to calculate loss on the prompt.

---

### Stage 8: Training Job Triggered
* **Files & Functions:**
  - `app/main.py`: lines 331–336
* **Intended Behavior:**
  Spawns `train_worker.py` to train an updated adapter.
* **Break Points Identified:**
  - **Detached Fire-and-Forget Process:** Spawning with `subprocess.Popen(..., creationflags=CREATE_NEW_CONSOLE | DETACHED_PROCESS)` gives the runner no way to know if training crashed.
  - **Race Condition with Next Benchmark Task:** The runner immediately moves to Task $N+1$ before the background worker has even initialized its tokenizer.
  - **Lock Collisions:** If Task $N+1$ also finishes a repair while the worker for Task $N$ is still compiling the model, the second worker hits `Timeout` on `models/adapters/training.lock` and discards the training request.

---

### Stage 9: LoRA Trainer Starts & Trains
* **Files & Functions:**
  - `train_worker.py`: `_run_training_pipeline_internal()`
  - `transformers.Trainer`, `peft.get_peft_model`
* **Intended Behavior:**
  Loads `Qwen/Qwen2.5-Coder-1.5B`, wraps with `LoraConfig(r=8, lora_alpha=16, ...)`, prepares dataset, and executes `trainer.train()`.
* **Break Points Identified:**
  - **Incompatible Dependency Crash (`torchao`):** `peft.import_utils.is_torchao_available()` raises `ImportError` if `torchao < 0.16.0` is present in the environment (as on Google Colab).
  - **Silent Catch Block:** `except Exception as e: print("Training job failed:", e)` swallows the exception and exits with return code 0, without alerting anyone.
  - **Insufficient Epochs / Underfitting:** Training 1 epoch on 1 example with default learning rate ($5 \times 10^{-5}$) makes virtually zero gradient impact on 1.5B parameters.

---

### Stage 10: Candidate Adapter Saved & Gated
* **Files & Functions:**
  - `train_worker.py`: lines 126–172
  - `app/evaluator.py`: `evaluate_model_on_test_set()`
* **Intended Behavior:**
  Saves candidate adapter to `models/adapters/candidates/adapter_<ts>`. Evaluates base model and candidate adapter on `data/dataset/test.json`. Accepts candidate if it performs at least as well as base.
* **Break Points Identified:**
  - **Defective Acceptance Criterion:** `accepted = cand_success >= base_success and cand_success > 0`. If `test.json` has 1 item and neither zero-shot base nor 1-step candidate passes it, `cand_success = 0`, so `accepted = False`. The adapter is marked `"status": "rejected"` and never activated.
  - **Overfitting / Leakage on Test Split:** In `build_dataset()`, if dataset size $< 3$, `train_set = examples` and `test_set = examples`. Evaluating on the exact training set leaks training data.

---

### Stage 11: Adapter Promotion & Versioning
* **Files & Functions:**
  - `train_worker.py`: lines 173–186
* **Intended Behavior:**
  Copies candidate adapter to `models/adapters/active/`. Archives old active adapter to `models/adapters/archive/`.
* **Break Points Identified:**
  - **Windows File Lock Collision:** `shutil.copytree` and `os.rename` on directories with active file handles fail with `PermissionError` on Windows.
  - **Broken Atomicity:** If process terminates midway through rename, `models/adapters/active` is left corrupted or missing.

---

### Stage 12: Model Reloads Active Adapter
* **Files & Functions:**
  - `app/main.py`: line 94 `check_and_reload_adapter()`
  - `app/model.py`: `check_and_reload_adapter()`, `reload_model()`, `get_model()`
* **Intended Behavior:**
  Detects changed `adapter_id` in `models/adapters/active/metadata.json`, calls `reload_model()`, and loads the new adapter into inference.
* **Break Points Identified:**
  - **PEFT Hook Stacking Bug:** `reload_model()` sets `_model = None` but does not reload `_base_model`. `PeftModel.from_pretrained(_base_model, ...)` is called on an already-peft-modified base model, triggering `UserWarning: Already found a peft_config attribute in the model...` and corrupting the weight forward passes.
  - **Timing Lag:** If training takes 90 seconds, the runner may have already executed 5 tasks before the new adapter is registered.

---

### Stage 13: Subsequent Task Uses Updated Adapter
* **Files & Functions:**
  - `app/model.py`: `generate_raw()`
  - `benchmark/runner.py`: records `active_adapter_id` in `BenchmarkResult`
* **Intended Behavior:**
  Generation runs with LoRA adapters active, producing improved code generation and repair.
* **Break Points Identified:**
  - If `models/adapters/active` does not exist or was rejected, `_loaded_adapter_id` is `None`, and the runner records `adapter_version = None`.

---

## 3. Root Cause Summary Matrix

| Break Point | File | Line | Cause | Fix Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **BP-1: torchao Crash** | `peft/import_utils.py` | 142 | `torchao` version check raises `ImportError` | Ensure `torchao` is uninstalled or $\ge 0.16.0$ |
| **BP-2: Asynchronous Race** | `app/main.py` | 335 | Detached fire-and-forget subprocess | Controlled batch/scheduled training with sync verification |
| **BP-3: Silent Failure** | `train_worker.py` | 194 | Swallows all exceptions without record | Explicit logging, error recording, and runner notification |
| **BP-4: Flawed Acceptance Gate** | `train_worker.py` | 155 | `cand_success > 0` rejects when score is 0 | Validation on loss reduction and code validity, not strict $>0$ test pass |
| **BP-5: Reload Corruption** | `app/model.py` | 21 | `reload_model()` does not unload/reset PEFT | Clean adapter switching via `load_adapter()`/`set_adapter()` or fresh base load |
| **BP-6: State Path Discrepancy** | `benchmark/runner.py` | 157 | `data/` vs `models/adapters/` | Unified configuration path constants |
