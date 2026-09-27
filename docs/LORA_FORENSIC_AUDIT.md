# LITE-CODER LoRA Forensic Audit Report

**Date:** 2026-09-24  
**Project:** LITE-CODER Continual Learning Research  
**Subject:** Forensic Code & Architectural Inspection of LoRA Fine-Tuning Pipeline (MODE-F)  
**Status:** Authoritative Forensic Audit

---

## 1. Executive Summary

During the frozen `LITE_CODER_100TASK_MODE_F` benchmark run, the experiment achieved a 100/100 success rate with a mean repair effort of 1.26 attempts. Although `LORA_ENABLED=True` was recorded in the manifest and configuration, **zero LoRA adapters were created, activated, or utilized by any task during the benchmark**. Every single task record in the 100-task checkpoint contains `adapter_version = None` and `active_adapter_id = None`.

Forensic inspection reveals that:
1. **Model / Weight Learning did NOT occur in MODE-F.** The observed performance improvements over the baseline (Mode-A: 1.58 attempts $\rightarrow$ Mode-F: 1.26 attempts) were entirely driven by **Memory Learning** (vector retrieval via FAISS) and **Strategy Learning** (multi-armed bandit selection of prompt strategies), identical to Mode-D (mean attempts: 1.26).
2. The failure of LoRA continual learning stemmed from a fatal combination of:
   - An environment dependency crash (`ImportError` triggered by `peft.import_utils` upon detecting pre-installed `torchao < 0.16.0` on Google Colab).
   - An unmonitored detached asynchronous background worker (`subprocess.Popen` in fire-and-forget mode).
   - A silent exception-swallowing block in `train_worker.py` (`except Exception as e: print(...)`).
   - A flawed acceptance gate (`accepted = cand_success >= base_success and cand_success > 0`) that unconditionally rejects adapters when evaluation execution success is zero.
   - An in-memory PEFT wrapping bug in `app/model.py` where reloading wraps an already-modified base model rather than resetting or cleanly switching adapters.

---

## 2. Fundamental Distinction: Learning Modalities in LITE-CODER

To maintain scientific integrity, the LITE-CODER architecture distinguishes three independent adaptation mechanisms:

| Learning Modality | Subsystem | Storage Mechanism | Actual Status in Frozen MODE-F |
| :--- | :--- | :--- | :--- |
| **Memory Learning** | `app/repair_memory.py` | `data/repair_memory.json` + FAISS index | **ACTIVE & FUNCTIONAL** (8 verified repair experiences accumulated) |
| **Strategy Learning** | `app/strategy_selector.py` | `data/strategy_stats.json` | **ACTIVE & FUNCTIONAL** (Dynamic selection across repair prompt strategies) |
| **Model/Weight Learning** | `train_worker.py` / `peft` | Low-Rank Adaptation (LoRA) parameter matrices | **FAILED SILENTLY** (0 adapter weights trained, 0 adapters loaded) |

Memory storage and prompt manipulation must never be conflated with parameter updates. MODE-F must be scientifically classified as **Mode-D + Difficulty Allocation with LoRA Inactive**.

---

## 3. Systematic Investigation Questions (A through T)

### A. Where is training triggered?
Training is triggered in [`app/main.py`](file:///d:/Amit%20Stuff/ai-code-system/app/main.py#L310-L336) inside the `generate()` route. When a task passes all four verification checks (`syntax_passed`, `safety_passed`, `execution_passed`, and `tests_passed`), required more than 1 attempt (`len(attempts) > 1`), and successfully registered a novel repair experience into `repair_memory` (`memories_added == True`), the runner executes:
```python
if config.get("LORA_ENABLED") and memories_added:
    import subprocess, sys
    creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen([sys.executable, "train_worker.py"], creationflags=creation_flags)
```

### B. What exact data is sent to training?
No in-memory data payload is passed via IPC or CLI arguments. Instead, [`train_worker.py`](file:///d:/Amit%20Stuff/ai-code-system/train_worker.py#L48) calls `build_dataset()` from [`app/training_dataset.py`](file:///d:/Amit%20Stuff/ai-code-system/app/training_dataset.py#L47), which independently reads [`data/repair_memory.json`](file:///d:/Amit%20Stuff/ai-code-system/data/repair_memory.json) from disk.

### C. How are successful repairs converted into training examples?
In [`app/training_dataset.py:build_training_example`](file:///d:/Amit%20Stuff/ai-code-system/app/training_dataset.py#L35-L45), each validated memory entry is formatted as:
```python
{
    "text": f"Fix this Python code:\n\n{memory['broken_code']}\n\nError:\n{memory['error_message']}\n\nCorrect Code:\n{memory['successful_fix']}\n",
    "fingerprint": generate_fingerprint(memory["task"], memory["broken_code"], memory["error_message"]),
    "raw_task": memory["task"],
    "raw_broken_code": memory["broken_code"],
    "raw_error_message": memory["error_message"],
    "raw_successful_fix": memory["successful_fix"],
    "raw_tests": memory.get("tests", "")
}
```

### D. Is the training data actually valid for supervised fine-tuning?
Forensic analysis reveals three severe deficiencies in training data validity:
1. **Prompt Distribution Mismatch:** Inference in [`app/model.py:fix_code`](file:///d:/Amit%20Stuff/ai-code-system/app/model.py#L375-L398) uses a complex system prompt (`"You are an expert Python debugger..."`, rules, `CURRENT PROBLEM:`, `BROKEN CODE:`, `ERROR:`). The training string in `app/training_dataset.py` uses `"Fix this Python code:\n\n{broken}\n\nError:\n{error}\n\nCorrect Code:\n{fix}"`. The model is trained on a prompt format that does not match the prompt format used during benchmark inference.
2. **Missing Prompt Loss Masking:** In `train_worker.py` (lines 96-105), labels are a direct copy of tokenized inputs (`tokens["labels"] = tokens["input_ids"].copy()`). Standard SFT requires masking the prompt tokens with `-100` so that gradients only update weights to predict the repair completion, rather than predicting the prompt and broken code.
3. **Right-Truncation Risk:** Tokenization enforces `truncation=True, padding="max_length", max_length=512`. Truncating from the right means that for programs exceeding 512 tokens, the `Correct Code` at the tail end is truncated first, causing the model to learn incomplete syntax.

### E. What model is trained?
The base model configured in both `train_worker.py` and `app/model.py` is `Qwen/Qwen2.5-Coder-1.5B`. In `train_worker.py`, it is loaded via:
```python
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    dtype=torch.float32,
    device_map="auto"
)
```
*(Note: `dtype` is non-standard Hugging Face Transformers syntax; standard is `torch_dtype`.)*

### F. What PEFT/LoRA configuration is used?
In [`train_worker.py:83-90`](file:///d:/Amit%20Stuff/ai-code-system/train_worker.py#L83-L90):
```python
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
```
This is a standard low-rank parameterization targeting query and value projection matrices with rank 8 and scaling factor 2 ($\alpha / r = 2.0$).

### G. Where is the adapter saved?
When training finishes, candidate weights are initially saved to:
`models/adapters/candidates/adapter_<unix_timestamp>/`
If accepted by the evaluator gate, the candidate is copied to:
`models/adapters/active/`
Previous active adapters are moved to:
`models/adapters/archive/archive_<unix_timestamp>/`

### H. Is the adapter actually saved after training?
In the frozen MODE-F run, **no adapter was saved at all** because training crashed before reaching `model.save_pretrained()`.
In an earlier pre-run artifact found on disk (`models/adapters/candidates/adapter_1787477490`), weights were saved to `candidates/`, but the metadata recorded `"status": "rejected"`, so it was never copied to `models/adapters/active`.

### I. How is adapter_version generated?
The candidate ID is generated via `f"adapter_{int(time.time())}"`. The active version is tracked in `models/adapters/active/metadata.json` under `"adapter_id"`. In the benchmark runner (`benchmark/runner.py`), `adapter_version` is pulled from `feedback.get("active_adapter_id")`.

### J. How does the inference model load the adapter?
In [`app/model.py:get_model()`](file:///d:/Amit%20Stuff/ai-code-system/app/model.py#L71-L98):
If `config.get("LORA_ENABLED")` is True and `models/adapters/active` exists, it calls:
`model = PeftModel.from_pretrained(_base_model, ACTIVE_ADAPTER_PATH)`
Before each generation, [`app/main.py:generate()`](file:///d:/Amit%20Stuff/ai-code-system/app/main.py#L93-L94) calls `check_and_reload_adapter()`, which inspects `models/adapters/active/metadata.json` and invokes `reload_model()` if the disk `adapter_id` differs from `_loaded_adapter_id`.

### K. Is the newly trained adapter actually used by subsequent tasks?
**NO.** In the frozen MODE-F run, `models/adapters/active` never existed. Consequently, `_loaded_adapter_id` remained `None` for all 100 tasks. Every task ran on the naked base model without any adapter weights.

### L. Is training synchronous or asynchronous?
Training was invoked **asynchronously** as a detached background process using:
`subprocess.Popen([sys.executable, "train_worker.py"], creationflags=CREATE_NEW_CONSOLE | DETACHED_PROCESS)`
This design created severe race conditions: the benchmark loop proceeded to subsequent tasks while the worker either lagged behind or crashed invisibly.

### M. What happens when training fails?
In [`train_worker.py:194-196`](file:///d:/Amit%20Stuff/ai-code-system/train_worker.py#L194-L196):
```python
except Exception as e:
    print("Training job failed:", e)
```
The detached process printed the exception to an unattached/lost stdout stream and terminated. It did not write failure state, did not alert the parent runner, did not raise an exit error code checked by any caller, and left no trace in the benchmark checkpoint.

### N. Does the benchmark continue despite training failure?
**YES.** Because the training worker was detached and asynchronous, the main benchmark runner had zero awareness of whether training succeeded or failed. It completed all 100 tasks without interruption.

### O. Why did the torchao incompatibility occur?
In [`peft/import_utils.py:126-146`](file:///d:/Amit%20Stuff/ai-code-system/venv/lib/site-packages/peft/import_utils.py#L126-L146):
```python
@lru_cache
def is_torchao_available():
    if importlib.util.find_spec("torchao") is None:
        return False
    TORCHAO_MINIMUM_VERSION = packaging.version.parse("0.16.0")
    ...
    if torchao_version < TORCHAO_MINIMUM_VERSION:
        raise ImportError(
            f"Found an incompatible version of torchao. Found version {torchao_version}, "
            f"but only versions above {TORCHAO_MINIMUM_VERSION} are supported"
        )
    return True
```
When running on Google Colab, the base Python environment contained a pre-installed `torchao 0.10.0`. When `peft` was imported inside `train_worker.py`, `is_torchao_available()` was evaluated. Because `torchao` was present and had version `0.10.0 < 0.16.0`, PEFT explicitly raised a fatal `ImportError`.

### P. Is torchao actually required by our training path or indirectly imported?
**`torchao` is completely unneeded.** Our pipeline performs standard FP32/FP16 LoRA on standard `torch.nn.Linear` layers (`q_proj`, `v_proj`). `torchao` is only used for architecture-level quantization optimizations (e.g., 4-bit / 8-bit quantized LoRA). It was imported purely as an optional backend check inside `peft` and `transformers`. If `torchao` is not installed, `find_spec("torchao")` returns `None`, and `is_torchao_available()` safely returns `False`.

### Q. Is the current LoRA implementation technically correct?
**NO.** In addition to the `torchao` issue, the current pipeline suffers from:
1. **Flawed Evaluator Gate:** In `train_worker.py:155`, `accepted = cand_success >= base_success and cand_success > 0`. On small memory sets, both base and candidate model get 0 zero-shot execution successes on the test task, meaning `cand_success > 0` evaluates to `False`, permanently rejecting all trained adapters.
2. **In-Memory PEFT Corruption on Reload:** In `app/model.py`, `reload_model()` sets `_model = None` but leaves `_base_model` in memory. `PeftModel.from_pretrained(_base_model, ...)` mutates the base model's internal layers. Wrapping it again triggers `UserWarning: Already found a peft_config attribute in the model...` and stacks adapters unpredictably.
3. **Training State File Path Discrepancy:** `benchmark/runner.py:157` looks for `"data/training_state.json"`, but `train_worker.py:12` writes to `"models/adapters/training_state.json"`.

### R. Are there any silent exception/fallback paths?
Yes:
- `train_worker.py` wraps the entire training execution in a broad `try...except Exception as e:` block that prints to standard output and exits cleanly.
- `app/model.py:check_and_reload_adapter()` wraps JSON reading in `try...except Exception: pass`.
- `app/main.py` ignores the return code and status of the background training process.

### S. Are checkpoints sufficient to resume training?
No. The benchmark checkpoint (`checkpoint.json`) only records task-level test results and `adapter_version: null`. It contains no training loss, optimizer state, adapter checkpoints, or training worker heartbeats.

### T. Is continual learning actually occurring or are we only storing memory?
**We are only storing memory.** In MODE-F, exactly 8 experiences were added to `repair_memory.json` and FAISS. Model weights remained 100% frozen. No parameter adaptation occurred.

---

## 4. Summary Table of Audit Findings

| Component | Intended Behavior | Actual Audited Behavior | Failure Severity |
| :--- | :--- | :--- | :--- |
| **Worker Launch** | Asynchronous daemon | Detached fire-and-forget; race conditions | High |
| **Worker Execution** | Trains LoRA adapter on new verified repairs | Crashed on `ImportError: torchao` | Critical (Blocked all training) |
| **Worker Error Handling** | Report failure to runner / record in manifest | Caught and silently swallowed | Critical (Masked failure) |
| **Acceptance Gate** | Accept non-regressing adapters | Rejected candidate when score is 0 (`cand > 0`) | High (Blocks valid adapters) |
| **Adapter Reloading** | Hot-swap active adapter weights | Mutates `_base_model` in-place, stacking hooks | High |
| **Path Consistency** | Uniform state file paths | `data/training_state.json` vs `models/adapters/...` | Medium |
| **Prompt Alignment** | SFT prompt matches inference prompt | Simple 3-line format vs verbose instruction prompt | Medium |
| **Loss Masking** | Mask prompt tokens (`-100`) | Loss computed over prompt + answer | Medium |
