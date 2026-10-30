# HISTORICAL RUNNER RECOVERY AUDIT

## 1. EXECUTIVE SUMMARY
The forensic audit successfully located the true historical benchmark execution harness hidden in `benchmark/runner.py` and executed via wrapper scripts like `scripts/run_mode_d_100.py`. Unlike the dummy `app/main.py` path analyzed previously, this runner possesses a rigorous 100-task execution loop, active error capturing, memory resets, and atomic per-task serialization into `raw_tasks/*.json` artifacts. It is the definitive harness that produced all historical LITE-Coder Q1 evidence.

## 2. HISTORICAL 100-TASK RUNNER IDENTIFIED
The true runner is located at:
**FILE**: `benchmark/runner.py`
**FUNCTION**: `run_benchmark(experiment_id: str, mode: str, size: int = None, dataset_path: str = None)`

## 3. EXACT COMMAND / ENTRY POINT
Historical executions were launched via Python script wrappers. For example:
**COMMAND**: `python scripts/run_mode_d_100.py`
**DATASET PATH**: `data/benchmark/v1.0/dataset.json` (Locked to `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620`)
**TASK LOOP**: `for idx, task in enumerate(tasks):` inside `benchmark/runner.py`.
**MODEL INVOCATION**: `resp = generate(req)` (invoking `app.main.generate`).
**RESULT WRITER**: `with open(raw_task_path, "x") as f: json.dump(raw_record, f, indent=4)` inside `benchmark/runner.py`.

## 4. DATASET LOADING TRACE
In `benchmark/runner.py`:
`tasks = load_dataset(dataset_path) if dataset_path else load_dataset()`
This delegates to `benchmark.dataset.load_dataset` which parses the JSON and yields the `Task` schemas.

## 5. 100-TASK LOOP TRACE
In `benchmark/runner.py`:
`for idx, task in enumerate(tasks):`
The loop iterates sequentially, tracking `completed_task_ids` to gracefully skip previously evaluated tasks upon resuming from a checkpoint.

## 6. MODEL GENERATION TRACE
Inside the task loop:
`resp = generate(req)` natively calls the application layer (`app.main.generate`) and extracts `feedback = resp.get("feedback_record", {})`.

## 7. REPAIR LOOP TRACE
The repair loop is internally encapsulated inside `app.main.generate` (`for attempt in range(MAX_RETRIES):`). The benchmark harness treats this as a black box and captures its output metrics (`attempts_used`, `success`).

## 8. RESULT PERSISTENCE TRACE
Task artifacts are serialized natively:
`raw_task_path = f"{experiment_dir}/raw_tasks/{task.task_id}.json"`
`with open(raw_task_path, "x") as f:` -> The `"x"` (exclusive creation) flag prevents accidental overwriting.
Aggregate status is simultaneously maintained via atomic tmp-renamed `checkpoint.json`.

## 9. HISTORICAL MODE-A TRACE
Created by: `scripts/run_mode_a_100.py`
Calls: `run_benchmark("LITE_CODER_100TASK_MODE_A_BASELINE", "MODE_A", ...)`

## 10. HISTORICAL MODE-D TRACE
Created by: `scripts/run_mode_d_100.py`
Calls: `run_benchmark("LITE_CODER_100TASK_MODE_D", "MODE_D", ...)`

## 11. HISTORICAL MODE-F TRACE
Created by: `scripts/run_mode_f_100.py`
Calls: `run_benchmark("LITE_CODER_100TASK_MODE_F", "MODE_F", ...)`

## 12. HISTORICAL MODE-F-SAFE TRACE
Created by: `scripts/run_mode_f_safe_100.py`
Calls: `run_benchmark("LITE_CODER_MODE_F_SAFE", "MODE_F_SAFE", ...)`

## 13. COLAB ENVIRONMENT EVIDENCE
Colab history is documented directly in the wrapper docstrings (e.g., `scripts/run_mode_d_100.py`):
- Base Model: `Qwen/Qwen2.5-Coder-1.5B`
- GPU: Colab GPU (referenced generically)
- Core Dependencies: PyTorch, Transformers, FAISS, Sentence-Transformers.

## 14. MEMORY INITIALIZATION/PERSISTENCE TRACE
- **Memory file**: `data/repair_memory.json`
- **FAISS file**: `data/repair_memory_index.faiss`
- **Initialization/Reset**: Managed by `reset_state()` in `benchmark/runner.py`, which executes `repair_memory.index.reset()`, `repair_memory.memories = []`, and `repair_memory._save()`.
- **Snapshotting**: Upon completion/suspension, `snapshot_experiment_state()` clones the global `data/` memory into `experiments/{id}/state_snapshot/`.

## 15. CHECKPOINT/RESUME EVIDENCE
The harness supports resilient execution:
```python
if os.path.exists(checkpoint_path):
    with open(checkpoint_path, "r") as f:
        saved_results = json.load(f)
    for r in saved_results:
        completed_task_ids.add(r["task_id"])
```
This enables the 100-task evaluation to safely span multiple disconnected Colab sessions.

## 16. REUSE FEASIBILITY
A. **Can it be reused?** Yes.
B. **Can it be isolated?** Yes, provided an adapter injects a patched path or safely coordinates the global `data/` memory files.
C. **Can memory be forced empty?** Yes, `reset_state()` natively achieves this.
D. **Can hash remain locked?** Yes.
E. **Historical results untouched?** Yes.
F. **Run in one session?** Yes, but protected by the checkpoint mechanism.
G. **Supports checkpoint?** Yes.

## 17. RISKS / CONFIRMATION NEEDED
The primary risk is the architectural decision of `repair_memory.py` binding tightly to global `data/` files rather than dynamic paths per experiment. Because `run_benchmark()` operates on this global state and later snapshots it, concurrent execution is strictly impossible, and sequential execution demands perfect `reset_state()` operation between `EXP_01` and `EXP_02`.

## 18. FINAL RECOMMENDATION

HISTORICAL RUNNER REQUIRES ISOLATED ADAPTER
