# LITE-CODER Project Audit

## 1. Executive Summary

LITE-CODER is currently a **Research Prototype** of an AI-driven code generation and repair framework. It is designed to solve the problem of generating reliable Python code using lightweight, locally hosted Large Language Models (LLMs) by wrapping the generation process in an iterative, execution-guided repair loop.

Currently, the implementation acts as a stateless code generation service with a retry loop. It queries a 1.5B parameter Qwen model to write Python code, executes it locally, detects syntax and runtime errors, and iteratively prompts the model to fix the code up to 5 times. It also generates and runs assert statements to verify functional correctness.

*   **Estimated Completion Percentage:** ~45%
*   **Current Maturity Level:** Research Prototype
*   **Strongest Capabilities:** The iterative generation-execution-repair loop is fully functional, and the integration of autonomous LLM-generated test cases for verification is implemented.
*   **Biggest Missing Capabilities:** Genuine "self-improvement" or memory. While a feedback JSON file is maintained, it is not correctly populated with the before/after repair data, and there is no retrieval system to learn from past mistakes during runtime.

## 2. Current Architecture

The current architecture is a linear, iterative loop exposed via a FastAPI endpoint.

**Actual Workflow Diagram:**
User Request → Prompt Processing (Planning) → Code Generation → Code Cleaning/AST Validation → Execution (Subprocess) → Error Detection → Test Generation → Test Execution (Eval) → Code Repair (Prompting) → Final Output

### Component Details:
*   **FastAPI Backend (`app/main.py`)**:
    *   *Role*: Exposes the `/generate` API and orchestrates the autonomous retry loop (max 5 retries).
    *   *Status*: Implemented.
*   **Model Interface (`app/model.py`)**:
    *   *Role*: Handles LLM inference using Huggingface `transformers` and `peft`. Generates execution plans, writes code, cleans output (removing markdown/explanations), classifies errors using string matching, and builds repair prompts.
    *   *Status*: Implemented.
*   **Code Executor (`app/executor.py`)**:
    *   *Role*: Automatically determines function arguments, writes the generated code to a temporary file, and runs it via `subprocess.run` with a 5-second timeout to catch runtime errors.
    *   *Status*: Implemented, but insecure (runs directly on host).
*   **Test Generator & Runner (`app/tester.py`)**:
    *   *Role*: Prompts the LLM to generate `assert` statements, cleans them, removes contradictory tests, and executes them against the generated code using Python's `exec()` and `eval()`.
    *   *Status*: Implemented, but highly insecure.
*   **Feedback Manager (`app/feedback.py`)**:
    *   *Role*: Appends generation results to a JSON file.
    *   *Status*: Partially implemented (contains a critical logical bug where error and fix data are lost).

## 3. Repository Structure Analysis

| Component/File | Purpose | Implementation Status | Important Functions | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `app/main.py` | API server and main retry loop orchestration. | 🟡 PARTIALLY IMPLEMENTED | `generate()` | The feedback saving logic fails to store the original error and fixed code. |
| `app/model.py` | LLM interactions, prompting, error classification. | ✅ FULLY IMPLEMENTED | `generate_code()`, `fix_code()`, `clean_generated_code()`, `classify_error()` | Uses Qwen2.5-Coder-1.5B. Error classification relies on basic string matching. |
| `app/executor.py` | Subprocess execution of generated code. | ✅ FULLY IMPLEMENTED | `execute_code()`, `ensure_execution()` | Uses clever heuristics to auto-generate function arguments based on parameter counts and names. |
| `app/tester.py` | Dynamic generation and execution of test asserts. | ✅ FULLY IMPLEMENTED | `run_tests()`, `generate_tests_with_llm()` | Evaluates asserts using `exec()`. A major security risk. |
| `app/feedback.py` | Simple JSON file appender. | ✅ FULLY IMPLEMENTED | `save_feedback()` | Extremely basic; no concurrency controls. |
| `data/benchmark_tasks.json` | Dataset of prompts for benchmarking. | ✅ FULLY IMPLEMENTED | N/A | Contains 15 standard algorithms and 15 hard prompts (duplicated in `run_tests.py`). |
| `data/feedback.json` | Storage for execution history. | 🟡 PARTIALLY IMPLEMENTED | N/A | Contains mostly empty fields due to the bug in `main.py`. |
| `train_lora.py` | Huggingface Trainer script for LoRA fine-tuning. | 🔵 EXPERIMENTAL | N/A | Designed to train on `feedback.json`, but the data format it expects is never produced by the runtime. |
| `benchmark.py` | Evaluates the system's success rate and repair usage. | 🟡 PARTIALLY IMPLEMENTED | N/A | Does not compare against a non-repair baseline. |
| `run_tests.py` | Another test script sending 75 prompts to the API. | ✅ FULLY IMPLEMENTED | N/A | Prints success/fail metrics and saves to `generation_results.json`. |
| `lora-finetuned/` | Directory containing trained LoRA weights. | ✅ FULLY IMPLEMENTED | N/A | Contains `adapter_model.safetensors` (loaded by `model.py`). |

## 4. Feature Completion Matrix

1. **LLM-based code generation**: ✅ FULLY IMPLEMENTED - Uses Qwen2.5-Coder-1.5B effectively.
2. **Local model inference**: ✅ FULLY IMPLEMENTED - Runs locally via PyTorch/Transformers.
3. **LoRA fine-tuning**: 🟡 PARTIALLY IMPLEMENTED - Script exists, but automated data pipeline is broken.
4. **Code execution**: ✅ FULLY IMPLEMENTED - `executor.py` runs subprocesses.
5. **Sandbox/isolation**: ❌ NOT IMPLEMENTED - Code executes directly on the host machine.
6. **Syntax error detection**: ✅ FULLY IMPLEMENTED - Validated via `ast.parse` and python compilation.
7. **Runtime error detection**: ✅ FULLY IMPLEMENTED - Subprocess stderr is captured.
8. **Error/traceback analysis**: 🟡 PARTIALLY IMPLEMENTED - `classify_error()` uses simple hardcoded substring matching (e.g., looking for "syntaxerror").
9. **Automatic code repair**: ✅ FULLY IMPLEMENTED - The LLM is reprompted with the specific error trace.
10. **Iterative generate → execute → repair loop**: ✅ FULLY IMPLEMENTED - Up to 5 attempts in `main.py`.
11. **Automatic test generation**: ✅ FULLY IMPLEMENTED - LLM generates asserts in `tester.py`.
12. **Unit testing**: 🟡 PARTIALLY IMPLEMENTED - Runs the generated asserts, but they are often hallucinatory or trivial.
13. **Edge-case testing**: ❌ NOT IMPLEMENTED - No structural guarantee that edge cases are generated.
14. **Execution-based verification**: ✅ FULLY IMPLEMENTED - Code must compile, run, and pass asserts.
15. **Feedback collection**: 🟡 PARTIALLY IMPLEMENTED - `main.py` overwrites the original error and code before saving.
16. **Feedback persistence**: ✅ FULLY IMPLEMENTED - Saved to `data/feedback.json`.
17. **Learning from previous failures**: ❌ NOT IMPLEMENTED - Feedback is never read back during runtime.
18. **Local repair memory**: ❌ NOT IMPLEMENTED - No database or vector store for past repairs.
19. **Retrieval of previous successful repairs**: ❌ NOT IMPLEMENTED - No RAG mechanism exists.
20. **Self-improvement**: ⚪ PLACEHOLDER - The only mechanism is an offline LoRA script that currently starves due to bad data.
21. **Multi-agent architecture**: ❌ NOT IMPLEMENTED - Single LLM instance prompted differently.
22. **Planner/reasoning component**: 🟡 PARTIALLY IMPLEMENTED - Generates a textual plan, but just concatenates it to the prompt.
23. **Code reviewer/critic**: ❌ NOT IMPLEMENTED.
24. **Code quality analysis**: ❌ NOT IMPLEMENTED.
25. **Security analysis**: ❌ NOT IMPLEMENTED.
26. **Performance optimization**: ❌ NOT IMPLEMENTED.
27. **Model selection based on task complexity**: ❌ NOT IMPLEMENTED.
28. **Resource-aware execution**: ❌ NOT IMPLEMENTED - Hardcoded 5s timeout is the only limit.
29. **Benchmarking**: ✅ FULLY IMPLEMENTED - Evaluated via `benchmark.py`.
30. **Evaluation metrics**: 🟡 PARTIALLY IMPLEMENTED - Success rate is tracked, but no token or memory metrics.
31. **Baseline comparison**: ❌ NOT IMPLEMENTED - Does not compare against standard generation.
32. **Web/API interface**: ✅ FULLY IMPLEMENTED - Exposes FastAPI endpoints.
33. **CLI interface**: ❌ NOT IMPLEMENTED.
34. **User-facing coding assistant interface**: ❌ NOT IMPLEMENTED.

## 5. Actual End-to-End Workflow

1. User submits prompt to `POST /generate` in `app/main.py`.
2. `model.py:generate_code()` is called. It first asks the LLM to generate a textual plan, then generates the code based on the plan.
3. The generated text is cleaned by `model.py:clean_generated_code()` and verified for Python syntax via `ast.parse`.
4. `executor.py:execute_code()` dynamically appends mock arguments (e.g., passing `5` if the function takes one parameter) and executes the script in a subprocess.
5. `stdout` and `stderr` are captured. If an error occurs, it is categorized (`model.py:classify_error()`) and the LLM is prompted to fix the code (`model.py:fix_code()`). The loop continues.
6. If the code executes successfully, `tester.py:run_tests()` asks the LLM to generate `assert` statements.
7. The tests are executed sequentially within the FastAPI process using `exec()` and `eval()`.
8. If a test fails, the LLM is reprompted to fix the code using the assertion failure.
9. If all passes, `app/main.py` saves feedback to `data/feedback.json`.
10. `MISSING`: The original broken code and the error that was fixed are discarded and NOT saved in the final successful feedback object.
11. The final code is returned to the user.

## 6. Self-Improvement Analysis

Does LITE-CODER currently perform REAL self-improvement? **NO.**

**Classification:** A. No self-improvement

**Evidence:**
*   **File:** `app/main.py`
*   **Function:** `/generate` route
*   **Explanation:** When code is successfully fixed, `current_code` is updated in the loop. Upon success, the system saves feedback: `{"generated_code": current_code, "error": "", "fixed_code": "", "success": True}`. The original error and the original broken code are lost.
*   **File:** `train_lora.py`
*   **Explanation:** The offline training script requires `item["error"]` and `item["fixed_code"]` to build training data. Since these are always empty on success, the model cannot learn from runtime repairs. Furthermore, there is no online learning or retrieval memory system implemented in the generation pipeline (`model.py`).

## 7. Execution and Verification Analysis

The system verifies code using: **D. Multiple verification mechanisms pass**

**Evidence:**
*   **File:** `app/executor.py` -> `is_valid_python()` ensures code compiles without syntax errors before execution.
*   **File:** `app/executor.py` -> `subprocess.run()` ensures the code runs without throwing runtime exceptions.
*   **File:** `app/tester.py` -> `run_tests()` generates and evaluates `assert` statements to verify functional correctness.

*Security Warning:* The system executes arbitrary LLM-generated code via `exec()` in `tester.py` directly inside the API process. This is extremely dangerous.

## 8. LoRA / Fine-Tuning Analysis

*   **Base model:** `Qwen/Qwen2.5-Coder-1.5B`
*   **LoRA configuration:** Rank 8, Alpha 16, Dropout 0.05. Target modules: `q_proj`, `v_proj`.
*   **Training data:** Fetched from `feedback.json`. (Currently broken in production).
*   **Status:** `TRAINED` (The repository contains a `lora-finetuned` directory).
*   **Loaded at runtime:** `ACTUALLY USED IN RUNTIME` (Loaded via `PeftModel.from_pretrained` in `model.py`).
*   **Explanation:** The system does load a LoRA adapter during inference. However, because the autonomous data collection is bugged, this adapter was likely trained on manually created sample data (like the first entry in `feedback.json`), rather than actual system improvements.

## 9. Benchmark and Evaluation Analysis

*   **Number of benchmark tasks:** 15 basic algorithmic tasks (`data/benchmark_tasks.json`).
*   **Metrics measured:** Code generation success rate, average repair iterations, runtime execution time.
*   **Metrics NOT implemented:** Token usage, memory usage, CPU/GPU utilization, baseline comparisons.
*   **Evidence:** `benchmark.py` iterates over the JSON file and hits the local API, tracking how many attempts were used before success, but it does not compare this to a zero-shot baseline.

## 10. Research Contribution Analysis

### Strong claims we can safely make
*   Execution-guided iterative code generation using local, lightweight (1.5B) models.
*   Autonomous generation and evaluation of unit tests as a secondary verification layer.

### Claims that require additional implementation
*   "Self-Improving" capabilities (requires fixing the feedback loop and adding RAG/online learning).
*   Learning from historical failures.

### Claims we should NOT make
*   Secure code isolation/sandboxing.
*   Continual learning.

## 11. Comparison With Existing AI Coding Systems

Unlike cloud-heavy assistants (GitHub Copilot, Claude), LITE-CODER's niche is **resource efficiency and localized execution-guided repair**. By using a highly constrained 1.5B parameter model, it substitutes raw model intelligence with an iterative "trial-and-error" execution loop. The primary research gap it can fill is **Offline, local, feedback-driven code repair** using extremely constrained hardware, provided the memory retrieval system is implemented.

## 12. Gap Analysis

| Capability | Current State | Required for Strong LITE-CODER | Priority |
| :--- | :--- | :--- | :--- |
| Feedback Data Persistence | Partially Implemented (Bugged) | Yes | 🔴 CRITICAL |
| Repair Memory (RAG) | Not Implemented | Yes | 🔴 CRITICAL |
| Secure Code Execution Sandbox | Not Implemented | Yes | 🟠 HIGH |
| Baseline Benchmark Comparison | Not Implemented | Yes | 🟠 HIGH |
| Automated LoRA Pipeline | Placeholder | Yes | 🟡 MEDIUM |

## 13. Recommended Next Architecture

**CURRENT**
User → Code Generator → Executor → LLM Test Generator → Feedback Appender (Broken)

**NEXT VERSION**
User → Code Generator ↔ **Repair Memory (Vector DB)** → **Secure Docker Sandbox** → Test Generator → Verification Engine → Feedback Manager

**Proposed Components:**
*   **Repair Memory (Vector DB):** Retrieve similar past errors and their successful fixes to inject into the prompt *before* attempting a fix. Integrates into `model.py:fix_code()`.
*   **Secure Sandbox:** Replace `subprocess.run` and `exec()` with a Docker container or restricted chroot environment to execute untrusted code safely. Integrates into `executor.py` and `tester.py`.

## 14. Most Important Features to Add

1.  **Fix Feedback Data Pipeline**
    *   *Priority:* Critical
    *   *Difficulty:* Low
    *   *Research Value:* Critical prerequisite
    *   *Files affected:* `app/main.py`
2.  **Retrieval of previous successful repairs (Repair Memory)**
    *   *Priority:* Critical
    *   *Difficulty:* Medium
    *   *Research Value:* High (Actualizes the "self-improving" claim)
    *   *Files affected:* `app/model.py`, `app/main.py`
3.  **Secure Execution Sandbox**
    *   *Priority:* High
    *   *Difficulty:* Medium
    *   *Research Value:* Medium (Required for safety)
    *   *Files affected:* `app/executor.py`, `app/tester.py`
4.  **Baseline Benchmark Evaluation**
    *   *Priority:* High
    *   *Difficulty:* Low
    *   *Research Value:* High (Proves the system works better than raw LLM)
    *   *Files affected:* `benchmark.py`
5.  **Resource-aware execution metrics (Tokens/RAM)**
    *   *Priority:* Medium
    *   *Difficulty:* Low
    *   *Research Value:* High (Substantiates the "Lightweight" claim)
    *   *Files affected:* `app/model.py`, `benchmark.py`

## 15. Experimental Plan

**Goal:** Prove that the execution-guided loop + memory is superior to raw generation on a constrained model.

*   **Baseline A:** One-shot generation using `Qwen2.5-Coder-1.5B` (No repair loop). Measure Success Rate.
*   **Baseline B:** LITE-CODER current implementation (Iterative repair, no memory). Measure Success Rate, Average Iterations.
*   **LITE-CODER Final:** Iterative repair + Retrieval Memory. Measure Success Rate, Average Iterations (Hypothesis: Iterations should decrease over time as it learns).

**Metrics:** Initial success rate, Final success rate, Average repair iterations, Execution time, Memory footprint.

## 16. Laptop Feasibility

*   **Model:** Qwen2.5-Coder-1.5B is exceptionally lightweight.
*   **RAM/VRAM:** Requires ~3-6GB depending on quantization. Highly practical for local laptop inference.
*   **Fine-tuning:** LoRA on a 1.5B model is completely feasible on a consumer GPU (e.g., RTX 3060/4060).
*   **Verdict:** The project's goal of being a lightweight framework is absolutely realistic for standard development laptops.

## 17. Research Paper Readiness

*   **Implementation readiness:** 40/100 (Core loop exists, but memory/learning is missing and execution is unsafe).
*   **Research novelty:** 30/100 (Iterative repair is standard; novelty hinges on adding the missing RAG/self-improvement).
*   **Experimental readiness:** 50/100 (Benchmark scripts exist, but lack baseline comparisons).
*   **Reproducibility:** 80/100 (Code is straightforward, lightweight model is easily accessible).
*   **Overall Publication Readiness:** 40/100.

## 18. Final Completion Report

CURRENT COMPLETION: 45%

### Already Completed
*   FastAPI backend architecture.
*   Integration with Qwen 1.5B via Transformers/PEFT.
*   Execution loop with syntax and runtime validation.
*   LLM-driven unit test generation.
*   Iterative error-repair prompting.

### Partially Completed
*   Feedback collection (critical bug prevents storing error/repair pairs).
*   Benchmarking (missing baselines).
*   Error classification (relies on basic string matching).

### Missing
*   Repair memory (RAG) and retrieval.
*   Secure sandboxing.
*   Online/automated feedback training pipeline.
*   Edge-case test generation structural enforcement.

### Critical Next Steps
1.  Fix the feedback JSON collection in `app/main.py` to store the original broken code and error alongside the fix.
2.  Implement a vector database (e.g., ChromaDB) to retrieve past fixes during `fix_code()`.
3.  Rewrite `tester.py` and `executor.py` to use a secure sandbox rather than raw `exec()`.
4.  Update `benchmark.py` to run Baseline comparisons.
5.  Establish a mechanism to trigger LoRA training automatically after a threshold of new successful repairs.

## 19. Evidence Appendix

**Feature:** Self-improvement memory loop
**Status:** Broken / Not Implemented
**Evidence:** In `app/main.py`, lines 129-135, `save_feedback()` is called upon successful test execution. However, it passes `error: ""` and `fixed_code: ""`, permanently losing the data of what was actually broken and how it was fixed. Consequently, `train_lora.py` (lines 12-14) skips all runtime-generated data because it checks for `item["error"] and item["fixed_code"]`.

**Feature:** Secure Execution Sandbox
**Status:** Not Implemented
**Evidence:** In `app/tester.py`, line 324, the application calls `exec(code, exec_globals)`. This executes LLM-generated code directly within the host FastAPI process, representing a critical security vulnerability.

**Feature:** Iterative Code Repair
**Status:** Fully Implemented
**Evidence:** In `app/main.py`, lines 76-169, a `for attempt in range(MAX_RETRIES):` loop catches execution and test failures, logs them to `attempt_history`, and passes the error string back to `fix_code()` in `app/model.py`.
