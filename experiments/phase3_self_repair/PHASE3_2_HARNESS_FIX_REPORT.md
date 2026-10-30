# LITE-CODER PHASE 3.2: TEST-HARNESS POLLUTION REMOVAL REPORT

**Date:** September 29, 2026  
**Phase:** 3.2 — Harness Architecture Remediation  
**Scope:** Elimination of `_AdaptiveResult` monkey-patching from user-code execution  
**Target File:** `experiments/phase3_self_repair/PHASE3_2_HARNESS_FIX_REPORT.md`  
**Test Suite:** `test_phase3_2_harness_isolation.py` (9/9 passed)  
**Total Regression Status:** 73/73 passed across all phases (1, 2, 2.1, 2.2, 2.3, 2.4, 3, 3.2)  
**Experiment Rerun:** `experiments/phase3_self_repair/runner.py`  
**Results JSON:** `experiments/phase3_self_repair/results.json`

---

## 1. Original Harness Mechanism

In prior revisions, [`app/tester.py`](file:///d:/Amit%20Stuff/ai-code-system/app/tester.py) generated an execution script wrapper around candidate user code and test assertions. To allow fuzzy comparisons (such as equating single-element lists `[x]` with scalar `x`, or empty collections with `0`/`None`), the test harness injected a custom class called `_AdaptiveResult` and monkey-patched the user's primary function in `globals()`:

```python
# Legacy mechanism in app/tester.py (now removed)
class _AdaptiveResult:
    def __init__(self, val):
        self._val = val
    def __eq__(self, other):
        ...

def _wrap_callable(_target_fn):
    def _inner(*args, **kwargs):
        _r = _target_fn(*args, **kwargs)
        if isinstance(_r, (bool, type(None))):
            return _r
        return _AdaptiveResult(_r)
    return _inner

# Injected global monkey-patching loop:
for _t_stmt in test_lines:
    _match_call = _re_tester.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', _t_stmt)
    if _match_call:
        _target_call = _match_call.group(1)
        if _target_call in globals() and callable(globals()[_target_call]):
            globals()[_target_call] = _wrap_callable(globals()[_target_call])
```

---

## 2. Why It Polluted Recursive Execution

The monkey-patching loop replaced `globals()[entry_point]` with `_wrap_callable(...)`. 

When candidate code executed a non-recursive function, the wrapper returned `_AdaptiveResult` at the outer assertion site. However, when the model synthesized a **recursive** algorithm—such as the divide-and-conquer implementation for `reverse_string`:
```python
def reverse_string(s):
    if len(s) <= 1:
        return s
    mid = len(s) // 2
    return reverse_string(s[mid:]) + reverse_string(s[:mid])
```
Each recursive invocation called `globals()['reverse_string']`, thereby invoking `_wrap_callable` recursively. The two sub-calls returned `_AdaptiveResult` objects rather than native Python `str` instances.

When the function executed string concatenation (`+`):
```python
return reverse_string(s[mid:]) + reverse_string(s[:mid])
```
Python checked whether `_AdaptiveResult` supported `+` (`__add__`). Because `_AdaptiveResult` did not implement `__add__`, Python aborted execution with:
$$\text{TypeError: unsupported operand type(s) for +: '\_AdaptiveResult' and '\_AdaptiveResult'}$$

This error:
- Had **nothing** to do with the candidate's algorithmic logic.
- Leaked internal test harness classes into the user's execution environment.
- Injected an unresolvable error message into the repair loop, misleading the LLM on subsequent attempts.

---

## 3. Exact Code Changes

In [`app/tester.py`](file:///d:/Amit%20Stuff/ai-code-system/app/tester.py), lines 871 to 924 were completely removed:
- Removed `import re as _re_tester`
- Removed `class _AdaptiveResult` definition
- Removed `def _wrap_callable` definition
- Removed the AST regex search loop that dynamically monkey-patched `globals()[_target_call]`

The test wrapper was restored to standard, unpolluted Python execution:
```python
# Clean execution architecture in app/tester.py
wrapper = [
    "import json",
    "import traceback",
    "test_results = {'total': " + str(total_tests) + ", 'passed': 0, 'failed': 0, 'errors': 0, 'message': 'All tests passed', 'success': True, 'failure_type': None, 'failing_test': ''}",
    "try:"
]
```

No monkey-patching is performed. Global functions retain their native identities and return native Python types.

---

## 4. New Execution Architecture

Under the revised architecture:
1. **Normal Definition:** Candidate code is placed into the execution script exactly as defined.
2. **Standard Invocation:** Test assertions invoke the candidate's entry point using standard Python semantics.
3. **Native Argument & Return Passing:** Arguments passed to the candidate are standard Python primitives/objects; return values returned by the candidate are standard Python primitives/objects.
4. **Direct Assertion Checking:** Assertions evaluate equality (`==`) using standard Python operator semantics (`assert fn(x) == expected`).
5. **Preserved Oracle Isolation:**
   - Pre-execution AST test syntax verification is fully preserved.
   - AST undefined variable detection is fully preserved.
   - Contract consistency validation (detecting contradictory or undetermined oracles) is fully preserved.
   - Sandboxed execution in isolated temporary environments with minimal environment variables is fully preserved.
   - Error classification (`CODE_FAILURE`, `TEST_ORACLE_FAILURE`, `TEST_HARNESS_FAILURE`, `CONTRACT_FAILURE`, `TIMEOUT`) is fully preserved.

---

## 5. Regression Results

### Dedicated Harness Isolation Regression Suite (`test_phase3_2_harness_isolation.py`)
A comprehensive regression suite was authored to verify the new unpolluted execution path across diverse programming paradigms:
1. `test_01_recursive_string_reversal_exact_reproduction` $\longrightarrow$ **PASSED**
2. `test_02_recursive_numeric_function` (factorial) $\longrightarrow$ **PASSED**
3. `test_03_function_calling_itself_multiple_times` (fibonacci tree recursion) $\longrightarrow$ **PASSED**
4. `test_04_return_value_in_arithmetic` ($+$, $*$, $-$ expressions) $\longrightarrow$ **PASSED**
5. `test_05_return_value_in_string_concatenation` (string formatting & $+$) $\longrightarrow$ **PASSED**
6. `test_06_function_returning_list` (list comprehensions & indexing) $\longrightarrow$ **PASSED**
7. `test_07_function_returning_dict` (key lookup & dictionary equality) $\longrightarrow$ **PASSED**
8. `test_08_normal_equality_assertions` (strict float/int arithmetic) $\longrightarrow$ **PASSED**
9. `test_09_actual_return_values_not_monkey_patched` (verifying `isinstance(fn, FunctionType)` and no `_is_adaptive`) $\longrightarrow$ **PASSED**

Result: **9 / 9 passed in 9.25 seconds**.

### Full Architecture Regression Suite (Phases 1 through 3.2)
```
test_phase1_architecture.py ......                                       [  8%]
test_phase2_architecture.py ................                             [ 30%]
test_phase2_1_agnostic.py .......                                        [ 39%]
test_phase2_2_audit.py ......                                            [ 47%]
test_phase2_3_oracle_hardening.py .............                          [ 65%]
test_phase2_4_failure_classification.py ..........                       [ 79%]
test_phase3_self_repair.py ......                                        [ 87%]
test_phase3_2_harness_isolation.py .........                             [100%]

============================= 73 passed in 37.45s =============================
```

---

## 6. Reverse-String Reproduction Result

The exact recursive repair candidate from Task 2 was evaluated:
```python
def reverse_string(s):
    if len(s) <= 1:
        return s
    mid = len(s) // 2
    left_half = s[:mid]
    right_half = s[mid:]
    return reverse_string(right_half) + reverse_string(left_half)
```

**Verification:**
- Executed against:
  - `assert reverse_string('hello') == 'olleh'`
  - `assert reverse_string('') == ''`
  - `assert reverse_string('a') == 'a'`
  - `assert reverse_string('racecar') == 'racecar'`
- **Result:** **PASSED ALL ASSERTIONS.**
- **Artifacts:** Zero `_AdaptiveResult` types created; zero `TypeError` exceptions raised; execution completed with standard Python semantics.

---

## 7. Comparative Experiment Results (Before vs. After Fix)

| Metric | Phase 3 Baseline (With Harness Pollution) | Phase 3.2 (After Harness Isolation Fix) | Delta / Impact |
|---|:---:|:---:|:---:|
| **Total Tasks Evaluated** | 5 | 5 | Same benchmark |
| **Genuine Self-Repair Successes** | **1 / 5** | **2 / 5** | **+100% Increase** |
| **Self-Repair Success Rate** | **20.0%** | **40.0%** | **+20.0 percentage points** |
| **TASK_1 (`add`)** | SUCCESS (Attempt 1) | SUCCESS (Attempt 1) | Preserved |
| **TASK_2 (`reverse_string`)** | **FAILED** (Harness TypeError) | **SUCCESS** (Attempt 1) | **Repaired & Accepted** |
| **TASK_3 (`binary_search`)** | FAILED (Model Reasoning) | FAILED (Model Reasoning) | Preserved failure |
| **TASK_4 (`merge_intervals`)** | FAILED (Model Generation) | FAILED (Model Generation) | Preserved failure |
| **TASK_5 (`schedule_meetings`)** | FAILED (Model Capacity) | FAILED (Model Capacity) | Preserved failure |
| **Negative Controls Passed** | 3 / 3 (100%) | 3 / 3 (100%) | Full safety preserved |
| **Mean Repair Attempts** | 2.4 | 2.2 | Reduced |
| **Mean Model Calls** | 2.8 | 2.4 | Reduced |
| **Total Experiment Runtime** | 1775.93s | 1497.97s | Faster execution |

---

## 8. Detailed Task 2 Trajectory After Fix

In the full experiment rerun with unpolluted execution:
- **Task:** `TASK_2` (`reverse_string`, Domain: String Processing)
- **Initial Defect:** `return s` (identity return)
- **Initial Execution:** Failed on `assert reverse_string('hello') == 'olleh'` with `AssertionError`. Classified as `CODE_FAILURE`.
- **Repair Invocation:** `fix_code()` triggered.
- **Attempt 1 Candidate (Hash `6d58eae5394a`):**
  ```python
  def reverse_string(s):
      if len(s) <= 1:
          return s

      mid = len(s) // 2
      left_half = s[:mid]
      right_half = s[mid:]

      return reverse_string(right_half) + reverse_string(left_half)
  ```
- **Execution & Validation:**
  - Contract Validation: **VALID**
  - Authoritative Tests: **ALL PASSED (6/6)** (`'hello'` $\rightarrow$ `'olleh'`, `''` $\rightarrow$ `''`, `'a'` $\rightarrow$ `'a'`, `'hello world'` $\rightarrow$ `'dlrow olleh'`, `'racecar'` $\rightarrow$ `'racecar'`, `'123!'` $\rightarrow$ `'!321'`).
- **Outcome:** **ACCEPTED (Self-Repair Success)** on Attempt 1 in 44.23 seconds.

---

## 9. Remaining Failures (Scientific Evidence of Model Limitations)

As required by the scientific protocol, no artificial tuning or heuristics were applied to force Tasks 3, 4, and 5 to pass. The failures in these tasks persist and reflect genuine model capability limits:

1. **TASK_3 (`binary_search`) — FAILED (Model Limitation):**
   The model generated an off-by-one edge condition when `mid == 0` in first-occurrence matching (`if mid > 0 and arr[mid - 1] != target:` fails when target is at index 0). The model mode-collapsed and regenerated the exact same candidate hash (`779eafeb86b0`) across all 4 attempts.
2. **TASK_4 (`merge_intervals`) — FAILED (Model Limitation):**
   Attempt 1 was properly intercepted by contract validation for calling `intervals.sort()` (violating list immutability). On Attempt 2, the model regressed to emitting a placeholder comment (`# Your solution here`).
3. **TASK_5 (`schedule_meetings`) — FAILED (Model Limitation):**
   The model successfully adapted from `meetings.sort()` to `sorted(meetings)` on Attempt 3, passing contract validation. However, the 1.5B parameter model failed to coordinate all 11 complex constraints simultaneously, failing title joining (`'+'` vs `' + '`), boundary strictness (`<=` vs `<`), and invalid meeting pre-filtering.

---

## 10. Confirmation of Task-Agnostic Design

- **Zero task-specific heuristics:** No keywords such as `"reverse"`, `"string"`, `"binary"`, `"interval"`, or `"meeting"` were added to `app/tester.py` or any production module.
- **Universal applicability:** The removal of `_AdaptiveResult` benefits *all* Python programs (recursive functions, classes, mathematical operator overloading, custom container types).
- **Zero weakening of contract or test gates:** The contract validator continues to strictly enforce parameter immutability and boundary rules, and all negative controls continue to halt without corrupting candidate code.
