# LITE-CODER Phase 1 Report

## 1. Objective

The objective of Phase 1 is to perform "Feedback Pipeline Hardening". The primary goal is to establish a reliable, traceable, and reproducible foundation for future self-improvement mechanisms (like Repair Memory, RAG, and LoRA adaptation). The previous pipeline discarded critical information (the original broken code and original error message) upon successful repair. Phase 1 ensures that complete repair trajectories are captured and saved in a structured JSON schema without altering the core generation or repair logic.

## 2. Files Changed

*   **`app/main.py`**: Rewrote the `generate` endpoint to build a structured `feedback_record` and track every attempt's `code`, `execution_status`, `error_type`, `error_message`, test results, and the applied repair. Removed the bug where `error` and `fixed_code` were wiped on success.
*   **`app/model.py`**: Updated `classify_error()` to extract specific Python exceptions (e.g., `SyntaxError`, `TypeError`) and their corresponding error messages using regex parsing on the traceback, rather than simple substring matching.
*   **`app/tester.py`**: Updated `run_tests()` to return a detailed `test_summary` indicating `total`, `passed`, and `failed` tests, while safely stopping on the first failure.
*   **`app/feedback.py`**: Made `save_feedback()` robust by automatically creating missing directories, validating the basic structure of the record before appending, and safely handling empty or corrupted JSON files.
*   **`train_lora.py`**: Updated the data parsing loop to support the new structured JSON format (specifically the `attempts` array) while maintaining backward compatibility with the legacy schema.

## 3. Feedback Pipeline Before

Previously, the `POST /generate` endpoint stored a local `attempt_history` list containing only the attempt number, stage, and raw error string. If the model successfully repaired the code within 5 attempts, `save_feedback` was called with `error: ""` and `fixed_code: ""`, and the original buggy code was permanently lost. The system only saved the final successful code under `generated_code`, rendering the data useless for LoRA training or retrieval memory.

## 4. Feedback Pipeline After

The endpoint now initializes a comprehensive `feedback_record` struct at the start of the request. During the autonomous retry loop, each attempt generates an `attempt_record` that stores the exact generated `code`, whether it failed during `execution` or `testing`, the specific `error_type` and `error_message`, the `test_results` (if applicable), and the `repair_applied` (the resulting code from `fix_code`). The final result is appended to `data/feedback.json` via a robust manager, preserving the entire repair trajectory from initial failure to final success.

## 5. New Feedback Schema

```json
{
    "feedback_id": "c1f7b2e3a0984...",
    "timestamp": 1729019232.123,
    "task": "Write an intentionally incorrect factorial function",
    "initial_code": "def factorial(n):\n    return n + factorial(n-1)",
    "attempts": [
        {
            "attempt_number": 1,
            "code": "def factorial(n):\n    return n + factorial(n-1)",
            "execution_status": "failed",
            "error_type": "RecursionError",
            "error_message": "maximum recursion depth exceeded",
            "tests_generated": "",
            "test_results": null,
            "repair_applied": "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n-1)"
        }
    ],
    "final_code": "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n-1)",
    "final_status": "success",
    "total_attempts": 1,
    "total_repairs": 1,
    "verification": {
        "syntax_passed": true,
        "execution_passed": true,
        "tests_passed": true
    },
    "execution_time": 4.52
}
```

## 6. Repair Trajectory Example

**Task**: `Write an intentionally incorrect factorial function that fails a basic test`

*   **Initial Code**: A function that returns 1 for everything.
*   **Error**: Assertion failed during execution.
*   **Repair**: The system reprompted the LLM with the Assertion failure.
*   **Fixed Code**: A functionally correct factorial implementation.
*   **Test**: Generated `assert factorial(5) == 120`.
*   **Final Result**: Tests pass. The entire chain (Attempt 1 failure + Attempt 2 success) is stored in the `attempts` array.

## 7. Error Classification

The system now parses the traceback to extract specific Python error types and messages. Supported categories mapped to specific types include:
*   **syntax**: `SyntaxError`, `IndentationError`
*   **logic**: `AssertionError`, `TypeError`, `ValueError`, `IndexError`, `KeyError`, `NameError`, `AttributeError`, `ZeroDivisionError`
*   **timeout**: `TimeoutExpired`
*   **import**: `ImportError`, `ModuleNotFoundError`
*   **general**: `UnknownError`

## 8. Verification Recording

Verification state is now definitively tracked via booleans:
*   `syntax_passed`: Implicitly true if `ast.parse` succeeds and execution doesn't throw a `SyntaxError`.
*   `execution_passed`: True if the subprocess runs the code without returning a non-zero exit code or writing to `stderr`.
*   `tests_passed`: True if the autonomous LLM-generated assertions execute successfully via `eval()`.
These flags are stored in the `verification` object of the feedback record.

## 9. LoRA Compatibility

The new feedback data is fully compatible with future LoRA training. `train_lora.py` has been updated to iterate through the `attempts` array in the new structured format. It extracts `(attempt['code'], attempt['error_message']) -> attempt['repair_applied']` pairs, ensuring that the model can be fine-tuned to map specific broken code + error combinations directly to the correct fixed code.

## 10. Tests Performed

Manually verified via script:
1.  **TEST 1**: A simple correct coding request (`"Write Python code to add two numbers"`). Succeeded immediately. Verified feedback saved 1 attempt with no repairs.
2.  **TEST 2**: A coding request that fails a test and requires repair (`"Write an intentionally incorrect factorial function"`). Verified the `attempts` array captured the initial failure and the subsequent fix.
3.  **TEST 3**: A coding request with a syntax error (`"Write code with a syntax error intentionally"`). Verified the `SyntaxError` was properly extracted and the trajectory recorded.

## 11. Results

The feedback pipeline is now robust. Data loss has been eliminated. The JSON records in `data/feedback.json` accurately reflect the multi-step nature of code repair, capturing exact tracebacks and intermediate code blocks.

## 12. Remaining Problems

*   The execution environment (`app/executor.py` and `app/tester.py`) is still inherently unsafe, executing generated code directly on the host machine.
*   The LLM-generated tests are occasionally hallucinated or logically flawed, which can cause correct code to be "fixed" into incorrect code.

## 13. Phase 2 Recommendation

### Repair Memory / Experience Retrieval (RAG)
With reliable repair trajectories now being saved to disk, Phase 2 should focus on implementing a Retrieval-Augmented Generation (RAG) system. A vector database (such as ChromaDB or FAISS) can embed the `error_message` and `initial_code` of past successful repairs. When the system encounters a new error, it can retrieve the most similar past error and provide the LLM with an example of how it previously solved that exact problem.
