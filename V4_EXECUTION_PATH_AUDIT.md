# V4 EXECUTION PATH AUDIT

### Historical Runner
- **Path**: `benchmark/runner.py`
- **Function**: `run_benchmark(experiment_id, mode, dataset_path)`
- **Task Loop**: Native `for idx, task in enumerate(tasks):` inside `runner.py`
- **Persistence**: `with open(raw_task_path, "x") as f: json.dump(...)` preventing overwrites.
- **Resume Mechanism**: Iteration natively filters `if task.task_id in completed_task_ids`.

### Dataset
- **Path**: `data/benchmark/v1.0/dataset.json`
- **SHA256**: 2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620
- **Task Count**: 100

### Memory
- **Original Paths**: `data/repair_memory.json`, `data/repair_memory_index.faiss`
- **Adapter Redirection**: `isolate_state_in()` / `isolate_state_out()` swaps files dynamically between `data/` and `experiments/FINAL_Q1_RUN/EXP_XX/memory/` at runtime boundaries.
- **EXP_02 Reset Scope**: Checked via `exp_dir.startswith(os.path.abspath("experiments"))` and isolated to `EXP_02_CLEAN_MEMORY/memory`.

### Completion
- **Verification Proof**: Adapter validates `len(task_files) == 100` natively via `glob.glob` inside the isolated `raw_tasks` folder before returning `COMPLETED`. Exit code 0 is no longer sufficient.

### Historical Preservation
- The V4 Adapter operates entirely within `experiments/FINAL_Q1_RUN/`. All historical `experiments/LITE_CODER_*` directories are strictly outside the adapter's execution scope.
