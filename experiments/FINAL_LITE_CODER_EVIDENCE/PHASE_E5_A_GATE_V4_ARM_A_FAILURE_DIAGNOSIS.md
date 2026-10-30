# LITE-Coder Phase E5.A — Gate v4 Arm A Worker Failure Diagnosis Report

**Document Date:** October 27, 2026  
**Auditor / Engineer:** Senior Software Reliability Engineer, Windows Systems Engineer & Reproducibility Auditor  
**Phase:** E5.A — Gate v4 Arm A Worker Failure Diagnosis  
**Repository Root:** `D:\Amit Stuff\ai-code-system`  
**Active Git Branch:** `fix/phase8-1-integration`  
**Active Head Commit:** `4cb53fbcbd8c2ce0f9cb7286ac0dcd4377915395`  
**Canonical Plan Digest:** `5bec1e2a44e36c824f09ead174dc8e7338fd503bc28d2c25e369043467bb81e0`  
**Target Plan File:** [`eval_results_phase8_2_1\20261027_gate_v4\experiment_plan.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/experiment_plan.json)  
**Run ID:** `f9772109247841928bb7a4ce4930d0aa`  
**Failed Run Directory:** [`eval_results_phase8_2_1\20261027_gate_v4\runs\A`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/runs/A)  

---

## 1. Executive Summary & Diagnostic Verdict

During the authorized Gate v4 Arm A launch on October 27, 2026, the parent runner successfully accepted the operator's typed plan digest confirmation, claimed the newly-staged `runs\A` directory, spawned the worker, and delivered the private pipe authorization token. 

### Key Milestone Achieved:
**The Phase E4 authorization repair functioned perfectly.**  
As recorded in [`eval_results_phase8_2_1\20261027_gate_v4\runs\A\control\authorization_consumed.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/runs/A/control/authorization_consumed.json):
- `authentication_path`: `"windows_verified_trampoline"`
- `launcher_pid`: `8280`
- `worker_pid`: `12924`
- `parent_pid`: `18164`
- `job_name`: `"Local\\LiteCoder_Job_ba1460f6acff49ffb7c797ba4e781dd5"`
- `windows_trampoline`: `true`

The worker verified its process ancestry ($T_{\text{runner}} \le T_{\text{stub}} \le T_{\text{worker}}$), validated containment in the named Win32 Job Object, unpacked the canonical fixture into `runs\A\workspace\fixture`, verified the fixture tree hashes, and initialized the write policy.

### Primary Diagnostic Finding:
**The worker halted with `PermissionError: Only the fixed guarded pytest worker may launch` inside [`scripts/phase8_2_1_controls.py:WritePolicy.audit`](file:///D:/Amit%20Stuff/ai-code-system/scripts/phase8_2_1_controls.py#L368) due to a Windows CPython `subprocess.Popen` audit hook platform divergence.**

When the worker attempted to execute the initial baseline test oracle to verify that the target router defect reproduces before invoking the model, `run_guarded_tests()` called `subprocess.Popen(argv)`. In Python 3.10 standard library on Windows (`Lib/subprocess.py:Popen._execute_child`):
1. Python converts `args` from a list of arguments to a single formatted command line string via `subprocess.list2cmdline(args)` **before** triggering the audit hook.
2. Python invokes `sys.audit("subprocess.Popen", executable, args, cwd, env)` with `args` as a `str` (e.g. `'"D:\\...\\python.exe" -B "D:\\...\\phase8_2_1_pytest.py" ...'`).
3. `WritePolicy.audit()` evaluated:
   ```python
   if self.subprocess_argv is None or list(args[1]) != list(self.subprocess_argv):
       raise PermissionError("Only the fixed guarded pytest worker may launch")
   ```
4. On Windows, `list(args[1])` converted the command line string into a list of single characters (`['"', 'D', ':', '\\', ...]`), while `list(self.subprocess_argv)` was a list of argument strings (`['D:\\...\\python.exe', '-B', ...]`).
5. Because a list of characters can never equal a list of argument words, the audit check failed closed and rejected the valid oracle worker launch.

---

## 2. Evidence Inventory & Artifact Analysis

### 2.1 File State in `eval_results_phase8_2_1\20261027_gate_v4\runs\A`

```
eval_results_phase8_2_1\20261027_gate_v4\runs\A\
├── control\
│   ├── owner.json                                      # Present (parent_pid: 18164, run_id: f9772109247841928bb7a4ce4930d0aa)
│   ├── authorization.json                              # Present (child_pid: 8280, parent_pid: 18164)
│   ├── authorization_consumed.json                     # Present (worker_pid: 12924, path: windows_verified_trampoline)
│   ├── terminal.json                                   # Present (status: "child_failure", error: ChildProcessError)
│   └── event_*.json                                    # 29 event records capturing parent lifecycle and worker stdout/stderr
├── evidence\
│   ├── event_745dd15f69ff46dbb930f9b1d086ad10.json     # Present (status: "worker_authenticated", actual_model_calls: 0)
│   └── terminal.json                                   # Present (status: "execution_exception", error: PermissionError)
└── workspace\
    ├── fixture\                                        # Present (micro_http/router.py, tests/test_router.py, LICENSE)
    └── tmp\                                            # Present (empty)
```

### 2.2 Worker Exception Traceback
Recorded in [`evidence\terminal.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/runs/A/evidence/terminal.json):
```
Traceback (most recent call last):
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_controls.py", line 469, in lifecycle
    yield
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 362, in internal_worker
    experiment_worker(plan, arm, evidence, policy, review)
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 237, in experiment_worker
    initial = oracle(task, fixture, {}, argv)
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 144, in oracle
    return task.acceptance_fn(str(fixture), status)
  File "D:\Amit Stuff\ai-code-system\eval_results_phase8_2_1\20261025_142828_IST\exports\baseline\eval_dataset_v2\tasks.py", line 61, in eval_task_01
    res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 141, in fixed
    return run_guarded_tests(argv, fixture)
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 121, in run_guarded_tests
    process = supervisor.launch(argv, cwd=fixture, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_controls.py", line 417, in launch
    self.process = subprocess.Popen(argv, start_new_session=os.name != "nt",
  File "C:\Users\T14s\AppData\Local\Programs\Python\Python310\lib\subprocess.py", line 971, in __init__
    self._execute_child(args, executable, preexec_fn, close_fds,
  File "C:\Users\T14s\AppData\Local\Programs\Python\Python310\lib\subprocess.py", line 1452, in _execute_child
    sys.audit("subprocess.Popen", executable, args, cwd, env)
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_controls.py", line 369, in audit
    raise PermissionError("Only the fixed guarded pytest worker may launch")
PermissionError: Only the fixed guarded pytest worker may launch
```

---

## 3. Boundary & Non-Contamination Verification

1. **Model Weights & Tokenizer:** **`NOT LOADED`**  
   The failure occurred at line 237 of `scripts/phase8_2_1_arm.py` during `oracle(task, fixture, {}, argv)`. This precedes line 242 where `torch`, `app.engineering_loop`, and `app.model` are imported.
2. **Coding Model Inference Calls:** **`0`**
3. **Generated Tokens:** **`0`**
4. **Patches Generated:** **`0`**
5. **Patches Applied:** **`0`**
6. **Plan Integrity:**  
   The Gate v4 plan digest was recomputed from disk:
   - **Canonical Digest:** `5bec1e2a44e36c824f09ead174dc8e7338fd503bc28d2c25e369043467bb81e0` *(Exact Match)*
   - **Plan File SHA-256:** `894f483fdb64e61957b1a7a9c3a33f034166096f713a7ffd12e9ae5007e9eecc` *(Exact Match)*

---

## 4. Assessment of Accidental Markdown Code Fences

The command entered by the operator contained leading and trailing Markdown code fences (` ```powershell ` and ` ``` `).
- PowerShell parsed the input as three sequential commands:
  1. ` ```powershell ` -> Errored as unrecognized cmdlet.
  2. `venv\Scripts\python.exe -B scripts\phase8_2_1_arm.py ...` -> Executed cleanly with exact arguments.
  3. ` ``` ` -> Errored as unrecognized cmdlet after the Python runner had already exited.
- **Causal Assessment:** The shell fence errors were purely ambient terminal noise. The Python process received clean, uncorrupted `sys.argv`, validated the plan digest successfully, and progressed all the way to initial oracle invocation. They had zero causal connection to the worker failure.

---

## 5. Technical Root Cause: Windows CPython Audit Hook Behavior

### 5.1 CPython Platform Divergence
In Python 3.8+ on POSIX systems (`Modules/_posixsubprocess.c`):
- `sys.audit("subprocess.Popen", executable, args, cwd, env)` passes `args` as a `list` or `tuple` of argument strings.

On Windows systems (`Lib/subprocess.py:Popen._execute_child`):
```python
if not isinstance(args, str):
    args = list2cmdline(args)   # args is converted to a string here!
...
sys.audit("subprocess.Popen", executable, args, cwd, env)
```
The standard library formats the argument list into a single command line string **before** calling `sys.audit`. Thus:
- `args[1]` in the audit callback is a `str`, e.g.:
  `'"D:\\Amit Stuff\\ai-code-system\\venv\\Scripts\\python.exe" -B "D:\\Amit Stuff\\ai-code-system\\scripts\\phase8_2_1_pytest.py" "D:\\Amit Stuff\\ai-code-system\\eval_results_phase8_2_1\\20261027_gate_v4\\runs\\A\\workspace\\fixture" 1476656eefe48924bbe83ccc07d9d122e906ca7584f2f1aa77c6531fb9804838'`

### 5.2 The Defective Check in `WritePolicy.audit`
Line 368 of `scripts/phase8_2_1_controls.py`:
```python
elif event == "subprocess.Popen":
    if self.subprocess_argv is None or list(args[1]) != list(self.subprocess_argv):
        raise PermissionError("Only the fixed guarded pytest worker may launch")
```
When `args[1]` is a string:
- `list(args[1])` evaluates to `['"', 'D', ':', '\\', 'A', 'm', 'i', 't', ' ', ...]`
- `list(self.subprocess_argv)` evaluates to `['D:\\...\\python.exe', '-B', ...]`
- They will never match on Windows.

### 5.3 Why Unit Tests Did Not Catch This
In [`tests/test_phase8_2_1_hardening.py`](file:///D:/Amit%20Stuff/ai-code-system/tests/test_phase8_2_1_hardening.py), `test_python_network_and_subprocess_guards_are_fail_closed()` tested the hook by synthetically passing:
`("subprocess.Popen", ("python", ["python", "arbitrary"], None, None))`
which simulated POSIX behavior. No test ever called `subprocess.Popen` under an active `WritePolicy` on Windows with `policy.subprocess_argv` set.

---

## 6. Minimal Safe Remediation Design

To resolve this platform divergence while preserving fail-closed security across all platforms, `WritePolicy.audit` in [`scripts/phase8_2_1_controls.py`](file:///D:/Amit%20Stuff/ai-code-system/scripts/phase8_2_1_controls.py) should handle both `str` (Windows) and `list`/`tuple` (POSIX):

```python
elif event == "subprocess.Popen":
    if self.subprocess_argv is None:
        raise PermissionError("Only the fixed guarded pytest worker may launch")
    cmd = args[1]
    if isinstance(cmd, str):
        if cmd != subprocess.list2cmdline(self.subprocess_argv):
            raise PermissionError("Only the fixed guarded pytest worker may launch")
    elif list(cmd) != list(self.subprocess_argv):
        raise PermissionError("Only the fixed guarded pytest worker may launch")
```

### Plan Revision Requirement: **`GATE V5 REQUIRED`**
Because [`scripts/phase8_2_1_controls.py`](file:///D:/Amit%20Stuff/ai-code-system/scripts/phase8_2_1_controls.py) is a plan-bound execution file (`plan["execution_files"]["phase8_2_1_controls.py"]`), updating it modifies its SHA-256 hash. Additionally:
1. `eval_results_phase8_2_1\20261027_gate_v4\runs\A` already exists on disk and contains terminal records. The runner contract strictly forbids overwriting or reusing an existing run output directory (`if output.exists(): raise FileExistsError`).
2. Therefore, an immutable **Gate v5 plan** in `eval_results_phase8_2_1\20261027_gate_v5\` must be generated with explicit lineage to Gate v4 (`5bec1e2a...`), preserving the failed Gate v4 run untouched.

---

## 7. Model-Free Test Suite Status

All 75 current hardening and preflight tests pass:
```powershell
venv\Scripts\python.exe -B -m pytest tests/test_phase8_2_1_hardening.py tests/test_phase8_2_preflight.py -q -p no:cacheprovider
```
**Result:** **`75 passed in 10.00s`**

---

## 8. Preserved Run Artifacts Summary

All Gate v4 artifacts remain permanently preserved:
- [`eval_results_phase8_2_1\20261027_gate_v4\runs\A\control\owner.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/runs/A/control/owner.json)
- [`eval_results_phase8_2_1\20261027_gate_v4\runs\A\control\authorization_consumed.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/runs/A/control/authorization_consumed.json)
- [`eval_results_phase8_2_1\20261027_gate_v4\runs\A\control\terminal.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/runs/A/control/terminal.json)
- [`eval_results_phase8_2_1\20261027_gate_v4\runs\A\evidence\terminal.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/runs/A/evidence/terminal.json)
- [`eval_results_phase8_2_1\20261027_gate_v4\experiment_plan.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v4/experiment_plan.json) *(Digest: `5bec1e2a44e36c824f09ead174dc8e7338fd503bc28d2c25e369043467bb81e0`)*

---

## 9. Review & Approval Request

In strict compliance with execution protocol, **no code changes or plan modifications have been performed**.

Please confirm whether to proceed with:
1. Updating `WritePolicy.audit` in `scripts/phase8_2_1_controls.py` to support Windows `subprocess.list2cmdline` command strings.
2. Adding dedicated regression tests in `tests/test_phase8_2_1_hardening.py` verifying that Windows `subprocess.Popen` audit hook calls succeed for the authorized pytest worker and fail-closed for arbitrary commands.
3. Creating the immutable Gate v5 experiment plan in `eval_results_phase8_2_1\20261027_gate_v5\` (with `runs` pre-staged) and computing the new canonical plan digest.
