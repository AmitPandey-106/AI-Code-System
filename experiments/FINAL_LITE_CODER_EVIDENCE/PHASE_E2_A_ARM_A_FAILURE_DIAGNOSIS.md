# LITE-Coder Phase E2 — Arm A Worker Failure Diagnosis Report

**Document Date:** October 27, 2026  
**Auditor / Engineer:** Senior Software Reliability Engineer, Windows Systems Engineer & Reproducibility Auditor  
**Phase:** E2.A — Arm A Execution Failure Diagnosis  
**Repository Root:** `D:\Amit Stuff\ai-code-system`  
**Active Git Branch:** `fix/phase8-1-integration`  
**Active Head Commit:** `4cb53fbcbd8c2ce0f9cb7286ac0dcd4377915395`  
**Canonical Plan Digest:** `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`  
**Target Plan File:** `eval_results_phase8_2_1\20261025_142828_IST\final_gate_v3\experiment_plan.json`  
**Run ID:** `a6172b256ecf4001a8f68f7c7b7fc924`  
**Failed Run Directory:** `eval_results_phase8_2_1\20261025_142828_IST\runs\A`  

---

## 1. Executive Summary & Diagnostic Verdict

During the canonical Arm A launch on October 27, 2026, the parent runner successfully verified the canonical plan digest, accepted manual confirmation from the operator, claimed the output directory, initialized Win32 Job Object supervision, and spawned the worker process. Exactly 838 milliseconds after approval, the execution halted with:

```
ChildProcessError: Worker failed; exit=1
  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 443, in run_parent
```

### Primary Diagnostic Finding:
**The failure was caused by an in-process capability check mismatch in `consume_authorization()` triggered by the standard Windows Python virtual environment (`venv`) redirector stub architecture.**

On Windows, `venv\Scripts\python.exe` is not the actual Python interpreter, but a compiled C launcher stub (`venvlauncher.exe`). When the parent process executes `subprocess.Popen([sys.executable, ...])`, Windows spawns the launcher stub (`PID 7392`). The stub immediately spawns the actual base Python interpreter as a grandchild process.

Inside the Python worker:
- `os.getpid()` returns the base Python interpreter PID, **not** the stub's PID recorded by the parent in `auth["child_pid"]` (`7392`).
- `os.getppid()` returns the launcher stub's PID (`7392`), **not** the parent runner's PID recorded in `auth["parent_pid"]` (`3012`).

Consequently, the worker's security capability validation check in `consume_authorization()` (`scripts/phase8_2_1_controls.py`, line 169–170):
```python
if (auth.get("child_pid") != (os.getpid() if pid is None else pid)
        or auth.get("parent_pid") != (os.getppid() if parent_pid is None else parent_pid)):
    raise ValueError()
```
failed closed and raised `PermissionError("Internal worker authorization rejected")`, exiting with code 1 before initializing the workspace, before loading model libraries, and before generating or applying any patch.

---

## 2. Evidence Inventory & Artifact Analysis

### 2.1 File State in `runs\A`
The run directory was inspected directly:

```
eval_results_phase8_2_1\20261025_142828_IST\runs\A\
├── control\
│   ├── owner.json                                      # Present (created 2026-10-27T08:04:41.261464+00:00)
│   ├── authorization.json                              # Present (child_pid: 7392, parent_pid: 3012)
│   ├── authorization_consumed.json                     # ABSENT (worker aborted prior to consumption)
│   ├── terminal.json                                   # Present (status: "child_failure", error: ChildProcessError)
│   └── event_*.json                                    # 13 event records capturing worker stdout/stderr
├── evidence\                                           # EMPTY (0 files, worker never reached evidence initialization)
└── workspace\                                          # EMPTY (0 files, workspace was never populated)
```

### 2.2 Chronological Event Sequence
The parent process redirected worker stderr into worker stdout (`stderr=subprocess.STDOUT`) and captured every line as an immutable event in `runs\A\control`:

| Timestamp (UTC) | Event Status | Content / Payload |
|---|---|---|
| `2026-10-27T08:04:41.265982` | `parent_approved` | Parent operator confirmed exact SHA-256; output directories claimed. |
| `2026-10-27T08:04:41.307198` | `worker_started` | Child PID `7392` assigned to Win32 Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. |
| `2026-10-27T08:04:41.873253` | `worker_output` | `Traceback (most recent call last):` |
| `2026-10-27T08:04:41.878314` | `worker_output` | `  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 502, in <module>` |
| `2026-10-27T08:04:41.882816` | `worker_output` | `    main()` |
| `2026-10-27T08:04:41.882816` | `worker_output` | `  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 494, in main` |
| `2026-10-27T08:04:41.889828` | `worker_output` | `    internal_worker(args.plan, args.arm)` |
| `2026-10-27T08:04:41.896569` | `worker_output` | `  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_arm.py", line 345, in internal_worker` |
| `2026-10-27T08:04:41.901657` | `worker_output` | `    consume_authorization(output, context, token)` |
| `2026-10-27T08:04:41.906364` | `worker_output` | `  File "D:\Amit Stuff\ai-code-system\scripts\phase8_2_1_controls.py", line 178, in consume_authorization` |
| `2026-10-27T08:04:41.907987` | `worker_output` | `    raise PermissionError("Internal worker authorization rejected") from None` |
| `2026-10-27T08:04:41.907987` | `worker_output` | `PermissionError: Internal worker authorization rejected` |
| `2026-10-27T08:04:42.103622` | `post_run_audit` | Protected files verified (`protected_after_verified: true`), model calls started/returned: 0. |

The error was **not lost**. It was fully recorded in the parent's control event logs.

---

## 3. Execution State & Activity Verification

All execution activities were audited against empirical evidence:

| Activity | Status | Empirical Supporting Evidence |
|---|:---:|---|
| **Model Imports** | **NO** | Worker failed at line 345, prior to line 242 (`import app.model`). PyTorch and Hugging Face libraries were never imported by the worker. |
| **Model Snapshot Loading** | **NO** | No model loading occurred. `runs\A\evidence` contains 0 files; no `model_loaded` event exists. |
| **Model Calls Started** | **0** | Confirmed by `post_run_audit` (`actual_model_calls_started: 0`). `GenerationBudget` was never instantiated. |
| **Model Calls Returned** | **0** | Confirmed by `post_run_audit` (`actual_model_calls_returned: 0`). |
| **Tokens Generated** | **0** | `output_tokens: null`. No text generation occurred. |
| **Patch Generated** | **NO** | No candidate proposal diff or `proposed_patch.txt` artifact exists. |
| **Patch Applied** | **NO** | `runs\A\workspace\fixture` was never populated; `runs\A\workspace` has 0 files. |
| **Defect Reproduction** | **NO** | Initial test oracle was never invoked because worker halted before fixture staging. |

---

## 4. Deep-Dive Root Cause Analysis: Windows Virtual Environment Process Model

### 4.1 The Mechanism of CPython Virtual Environments on Windows
On Windows, CPython's `venv` module cannot create POSIX-style symlinks for executables without elevated privileges. Instead, it places compiled C redirector executables into `venv\Scripts\`:
- `D:\Amit Stuff\ai-code-system\venv\Scripts\python.exe` (105,864 bytes)
- Target configured in `venv\pyvenv.cfg`: `home = C:\Users\T14s\AppData\Local\Programs\Python\Python310`

When `venv\Scripts\python.exe` is launched:
1. The redirector executable parses `pyvenv.cfg`.
2. It calls Windows API `CreateProcessW` to spawn `C:\Users\T14s\AppData\Local\Programs\Python\Python310\python.exe`.
3. It passes standard handles (`stdin`, `stdout`, `stderr`) to the child and waits for termination.

### 4.2 Empirical Process Hierarchy Test
An isolated empirical probe was conducted on the host runtime:
```
sys.executable: D:\Amit Stuff\ai-code-system\venv\Scripts\python.exe
PARENT: os.getpid()  = 18840
PARENT: process.pid  = 17552  (the venv redirector stub)
CHILD:  os.getpid()  = 6900   (the base python.exe interpreter)
CHILD:  os.getppid() = 17552  (the venv redirector stub)
```

In the canonical run:
- Parent runner PID: **3012** (`owner["parent_pid"]`)
- Launcher stub PID: **7392** (`auth["child_pid"]` / `process.pid`)
- Real worker PID: **`<actual_worker_pid>`**
- Real worker PPID: **7392** (`os.getppid()`)

### 4.3 Why the Authorization Failed
In `consume_authorization` (`scripts/phase8_2_1_controls.py`, lines 168–172):
```python
if (auth.get("run_id") != owner.get("run_id")
        or auth.get("supervised") is not True
        or auth.get("child_pid") != (os.getpid() if pid is None else pid)
        or auth.get("parent_pid") != (os.getppid() if parent_pid is None else parent_pid)
        or not (0 < auth["expires"] - (time.time() if now is None else now) <= 30)
        or not hmac.compare_digest(auth["token_sha256"], sha(token.encode()))):
    raise ValueError()
```

When evaluated in the real Python worker:
1. `auth.get("child_pid")` is `7392`, but `os.getpid()` is `<actual_worker_pid>`. **Mismatch**.
2. `auth.get("parent_pid")` is `3012`, but `os.getppid()` is `7392` (the launcher stub). **Mismatch**.

Both checks failed, throwing `ValueError()`, which `consume_authorization()` caught and converted into `PermissionError("Internal worker authorization rejected")`.

### 4.4 Why Unit Tests Did Not Catch This
In `tests/test_phase8_2_1_hardening.py`:
- `test_internal_authorization_is_one_use_and_bound` (lines 94–112) tested authorization by explicitly passing `pid=123` and `parent_pid=os.getpid()`, bypassing the default `os.getpid()` and `os.getppid()` resolution.
- `test_parent_supervision_authorization_and_terminal_audit_with_fixed_double` (lines 301–375) used a `FakeSupervisor` with a mock `Process` and never spawned an actual subprocess via `venv\Scripts\python.exe`.
- Thus, the Windows venv stub trampoline behavior was never exercised under real subprocess conditions until the live trial.

---

## 5. System & Workspace Integrity Status

| Target | Authoritative Hash / Baseline | Verification Result |
|---|---|:---:|
| **Canonical Plan Digest** | `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424` | **MATCH (100%)** |
| **Execution Source Adapters** | 3 files (`phase8_2_1_arm/controls/pytest.py`) | **MATCH (3/3)** |
| **Protected Fixtures & Exports** | 122 files across exports & fixture | **MATCH (122/122)** |
| **Model Snapshot** | 7 files (3,099,021,808 bytes) | **MATCH (7/7)** |
| **Git Working Tree** | Branch `fix/phase8-1-integration` | **0 Tracked Modifications** |
| **Failed Run State** | `eval_results_phase8_2_1\... \runs\A` | **Sealed & Untouched** |

No project files, fixtures, test files, or historical evidence were modified or corrupted.

---

## 6. Recommended Corrective Action

### 6.1 The Plan Invariance Constraint
In `experiment_plan.json`, `plan["execution_files"]` binds the exact SHA-256 hashes of:
- `scripts/phase8_2_1_arm.py` (`00ddc139dbbb1ff66085a0899015c9ff88d22d25087cb548a3c8cb08064cf449`)
- `scripts/phase8_2_1_controls.py` (`a4929a5fe2bb3d9642ca02bdfab4335606d2036c64ea492215c0e14e21aeb37a`)

Modifying either file changes its SHA-256 hash. Because the canonical plan digest (`7430f22335ee...`) binds `execution_files`, any code correction requires a structured gate advance (e.g., `final_gate_v4`) that computes and authorizes a new plan digest.

### 6.2 Smallest Corrective Code Change
The smallest, most targeted fix is in `scripts/phase8_2_1_controls.py`, inside `consume_authorization()`:

Recognize that on Windows (`os.name == "nt"`), when launched via a `venv` redirector stub, the immediate parent of the Python worker is the stub recorded in `auth["child_pid"]`:

```python
# In consume_authorization (scripts/phase8_2_1_controls.py):
# Direct match (POSIX, or native executable without launcher stub):
direct_match = (
    auth.get("child_pid") == (os.getpid() if pid is None else pid)
    and auth.get("parent_pid") == (os.getppid() if parent_pid is None else parent_pid)
)
# Windows venv launcher trampoline match (worker is child of the launched stub):
windows_trampoline_match = (
    os.name == "nt"
    and pid is None
    and parent_pid is None
    and auth.get("child_pid") == os.getppid()
)

if not (direct_match or windows_trampoline_match):
    raise ValueError()
```

### 6.3 Run Output Directory Requirement
`claim()` enforces that the target run output directory does not exist prior to launch (`output.mkdir(exist_ok=False)`).
Because `runs\A` now contains the diagnostic evidence of this failed run:
1. `runs\A` must remain preserved on disk as immutable audit evidence.
2. The corrected plan (`final_gate_v4`) should either:
   - Target an incremental run directory root (e.g., `eval_results_phase8_2_1\20261027_133500_IST\runs`), OR
   - Specify a distinct, unique run identifier.

---

## 7. Summary & Next Step

1. **Diagnosis Complete**: The Arm A failure is fully diagnosed and proven with empirical host evidence.
2. **Safety Verified**: Zero model inference calls occurred, zero tokens were generated, and zero patches were applied.
3. **Integrity Preserved**: All protected assets and the git working tree remain completely pristine.
4. **Action Required**: Await explicit user authorization before preparing any code correction or new plan iteration.
