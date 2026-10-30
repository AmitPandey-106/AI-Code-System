# LITE-Coder Phase E3 — Authorization Handshake Repair Design

**Document Date:** October 27, 2026  
**Auditor / Engineer:** Senior Software Reliability Engineer, Windows Systems Engineer & Experimental Reproducibility Auditor  
**Phase:** E3 — Authorization Handshake Repair Design and Test Specification  
**Repository Root:** `D:\Amit Stuff\ai-code-system`  
**Active Git Branch:** `fix/phase8-1-integration`  
**Active Head Commit:** `4cb53fbcbd8c2ce0f9cb7286ac0dcd4377915395`  
**Canonical Plan Digest:** `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`  
**Target Plan File:** `eval_results_phase8_2_1\20261025_142828_IST\final_gate_v3\experiment_plan.json`  
**Preserved Failed Run ID:** `a6172b256ecf4001a8f68f7c7b7fc924`  
**Preserved Run Location:** `eval_results_phase8_2_1\20261025_142828_IST\runs\A`  

---

## 1. Executive Summary & Design Scope

In Phase E2, the canonical Arm A trial was initiated under strict operator supervision. The parent runner verified the plan digest (`7430f22335ee...`), prompted for manual confirmation, claimed the run output directory, initialized Win32 Job Object containment, and launched the internal worker. Exactly 838 milliseconds later, the worker terminated with exit code 1, and the parent halted with `ChildProcessError: Worker failed; exit=1`.

The Phase E2.A diagnostic investigation confirmed the failure mechanism:
1. `venv\Scripts\python.exe` is a compiled C launcher stub (`py.exe` / `venvlauncher.exe`, 268,568 bytes).
2. Spawning the worker via `subprocess.Popen([sys.executable, ...])` launches the stub (`PID 7392`).
3. The stub calls Windows API `CreateProcessW` to spawn base Python (`C:\...\Python310\python.exe`) as a grandchild process.
4. In the worker process:
   - `os.getpid()` returns the base Python interpreter PID (not `7392`).
   - `os.getppid()` returns the launcher stub PID (`7392`, not parent runner PID `3012`).
5. The capability check in `consume_authorization()` (`scripts/phase8_2_1_controls.py`, lines 169–170) strictly checked `child_pid == os.getpid()` and `parent_pid == os.getppid()`. Both failed closed, raising `PermissionError("Internal worker authorization rejected")`.

### Objective of Phase E3:
Deliver a complete, mathematically sound repair design and regression test specification that resolves the Windows venv redirector failure without weakening isolation, compromising the one-use capability model, or modifying the canonical plan files in place.

---

## 2. Deconstruction of the Existing Authorization Handshake

### 2.1 Current Handshake Sequence
```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant Parent as Parent Runner (PID 3012)
    participant Job as Win32 Job Object
    participant Stub as venvlauncher.exe (PID 7392)
    participant Worker as Base python.exe (PID 8940)
    participant Disk as control/ Records

    Operator->>Parent: Types canonical plan SHA-256
    Parent->>Disk: claim() writes owner.json (parent_pid=3012)
    Parent->>Job: CreateJobObjectW & SetInformation (KILL_ON_JOB_CLOSE)
    Parent->>Stub: subprocess.Popen(CREATE_SUSPENDED) -> PID 7392
    Parent->>Job: AssignProcessToJobObject(Stub)
    Parent->>Stub: NtResumeProcess()
    Parent->>Disk: authorize() writes authorization.json (child_pid=7392, parent_pid=3012)
    Parent->>Stub: Writes token (256-bit hex) to stdin pipe
    Stub->>Worker: CreateProcessW(base python.exe) & inherits pipes
    Note over Worker: Automatically assigned to Job Object
    Stub->>Worker: Forwards token over stdin pipe
    Worker->>Disk: consume_authorization() reads owner.json & authorization.json
    Worker->>Worker: Checks auth["child_pid"] (7392) == os.getpid() (8940) -> FAIL
    Worker->>Worker: Checks auth["parent_pid"] (3012) == os.getppid() (7392) -> FAIL
    Worker->>Parent: Raises PermissionError; exits with code 1
    Parent->>Job: CloseHandle(Job) terminates Stub & Worker
    Parent->>Disk: finalize() writes terminal.json (child_failure)
```

### 2.2 Why Existing Tests Missed This Behavior
A review of `tests/test_phase8_2_1_hardening.py` revealed two critical test design blind spots:
1. `test_internal_authorization_is_one_use_and_bound` (lines 94–112):
   Tested `consume_authorization()` by passing explicit keyword arguments:
   `consume_authorization(out, expected, token, pid=123, parent_pid=os.getpid())`
   Passing `pid` and `parent_pid` bypassed the default runtime evaluation of `os.getpid()` and `os.getppid()`.
2. `test_parent_supervision_authorization_and_terminal_audit_with_fixed_double` (lines 301–375):
   Substituted `FakeSupervisor` and a mock `Process` with an in-memory `StringIO` buffer. No real Windows process was spawned via `venv\Scripts\python.exe`.

---

## 3. Empirical Process Ancestry on Windows

Host-level probing scripts (`scratch/check_launcher_chain.py`, `scratch/check_job_membership.py`, and `scratch/test_toolhelp.py`) confirmed:

1. **Launcher Binary Identity**:
   `D:\Amit Stuff\ai-code-system\venv\Scripts\python.exe`
   - Original filename: `py.exe`
   - File description: `Python Launcher`
   - Architecture: PE32+ (x64) executable
2. **Process Lifetime & Grandparent Relationship**:
   - The launcher stub (`venvlauncher.exe`) remains running for the entire duration of the child process. It invokes `WaitForSingleObject` on the child process handle and forwards the child's exit code upon completion.
   - The child process's immediate parent (`os.getppid()`) is guaranteed to be the launcher stub.
   - Using the Windows Toolhelp32 API (`CreateToolhelp32Snapshot`), the parent of the launcher stub is confirmed to be the parent runner (`auth["parent_pid"]`).
3. **Win32 Job Object Inheritance**:
   - Because the parent attaches the launcher stub to the Job Object *before* resuming execution, any child process spawned via `CreateProcessW` is automatically trapped in the Job Object by the Windows NT kernel.
   - Probing with `kernel32.IsProcessInJob` confirmed:
     `CHILD_PID: 15036, CHILD_PPID: 2420, IN_JOB: 1`
   - Probing with `QueryInformationJobObject` (`JobObjectBasicProcessIdList`) confirmed that all processes (parent runner excluded; launcher stub, worker interpreter, and console host) are assigned to the Job Object.

---

## 4. Threat Analysis of Proposed Workarounds

### 4.1 Evaluation of Naive Workaround (`windows_trampoline_match`)
The preliminary diagnosis considered:
```python
windows_trampoline_match = (
    os.name == "nt"
    and pid is None
    and parent_pid is None
    and auth.get("child_pid") == os.getppid()
)
```

#### Security Analysis:
| Threat Vector | Severity | Vulnerability in Naive Workaround | Evaluation & Reality |
|---|:---:|---|---|
| **PID Recycling Race** | Low | If `auth["child_pid"]` terminated, the OS could reassign the PID to another process. | **Mitigated**: The parent runner holds an open handle (`process._handle`) to `auth["child_pid"]`. In Windows NT kernel semantics, a PID cannot be recycled while an open kernel handle exists. Furthermore, `venvlauncher.exe` does not exit until the worker exits. |
| **Missing Grandparent Verification** | Medium | The check asserts `os.getppid() == auth["child_pid"]`, but does not verify who spawned `os.getppid()`. | **Vulnerable**: An unrelated child spawned by another process that happened to share a PID (if unheld) would not be rejected by parent identity. |
| **Job Object Containment Verification** | High | The worker does not verify whether it is executing inside the supervisory Job Object. | **Vulnerable**: If a child broke away or was launched outside a Job Object, the check would still pass. |
| **Audit Identity Discrepancy** | Low | `owner.json` records `child_pid: 7392` (stub), but execution events and memory profiles reflect `PID 8940`. | **Defect**: The durable evidence records conflicting PIDs for the worker process. |

#### Conclusion:
While the 256-bit cryptographic token transmitted over the private OS pipe provides strong authentication, relying solely on `auth["child_pid"] == os.getppid()` weakens the defense-in-depth posture by dropping grandparent verification and Job Object containment checks.

---

## 5. Recommended Minimal Repair Design: Verified Trampoline Handshake

### 5.1 Architecture: Two-Tier Verified Ancestry Validation

The recommended correction preserves `scripts/phase8_2_1_arm.py` and `scripts/phase8_2_1_pytest.py` **100% unchanged**. All repairs are isolated to `consume_authorization()` in `scripts/phase8_2_1_controls.py`.

The worker performs three independent verification layers:
1. **Cryptographic Token Verification**:
   - Token is 64 hex characters (256 bits of entropy from `secrets.token_hex(32)`).
   - Delivered exclusively via the anonymous OS stdin pipe created by `subprocess.Popen(stdin=subprocess.PIPE)`.
   - Verified via constant-time `hmac.compare_digest(auth["token_sha256"], sha(token.encode()))`.
   - Single-use enforced by `exclusive_json(... "authorization_consumed.json")`.
2. **Launch Context Binding**:
   - `auth["run_id"] == owner["run_id"]`
   - `auth["supervised"] is True`
   - `0 < auth["expires"] - time.time() <= 30`
   - Complete metadata equality across 7 context fields (`experiment_id`, `arm`, `plan_sha256`, `task_id`, `revision`, `source`, `output`).
3. **Cryptographically & Structurally Bound Process Ancestry**:
   The caller must satisfy either **Direct Binding** (POSIX or native executable) OR **Verified Windows Trampoline Binding**:

```python
# scripts/phase8_2_1_controls.py

def get_process_parent_pid(pid):
    """Query the parent PID of an arbitrary process using Toolhelp32 snapshot."""
    import ctypes
    from ctypes import wintypes as w
    TH32CS_SNAPPROCESS = 0x00000002
    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", w.DWORD),
                    ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    snapshot = kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == w.HANDLE(-1).value:
        return None
    pe = PROCESSENTRY32(); pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    try:
        if not kernel.Process32First(snapshot, ctypes.byref(pe)):
            return None
        while True:
            if pe.th32ProcessID == pid:
                return pe.th32ParentProcessID
            if not kernel.Process32Next(snapshot, ctypes.byref(pe)):
                break
    finally:
        kernel.CloseHandle(snapshot)
    return None

def verify_process_in_job():
    """Verify that current process is running inside an active Windows Job Object."""
    import ctypes
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    in_job = w.BOOL()
    if kernel.IsProcessInJob(kernel.GetCurrentProcess(), None, ctypes.byref(in_job)):
        return bool(in_job.value)
    return False
```

### 5.2 Updated `consume_authorization()` Logic
```python
def consume_authorization(output, expected, token, *, pid=None, parent_pid=None, now=None):
    """One-use local pipe capability, bound to parent/child and complete run identity."""
    try:
        if not isinstance(token, str) or len(token) != 64:
            raise ValueError("Token must be a 64-character hex string")
        owner = read_json(Path(output) / "control/owner.json")
        auth = read_json(Path(output) / "control/authorization.json")
        for key, value in expected.items():
            if owner.get(key) != value or auth.get(key) != value:
                raise ValueError("Expected run context mismatch")
        if (auth.get("run_id") != owner.get("run_id")
                or auth.get("supervised") is not True
                or not (0 < auth["expires"] - (time.time() if now is None else now) <= 30)
                or not hmac.compare_digest(auth["token_sha256"], sha(token.encode()))):
            raise ValueError("Authorization parameters or token hash mismatch")

        # Process ancestry verification
        actual_pid = os.getpid() if pid is None else pid
        actual_ppid = os.getppid() if parent_pid is None else parent_pid

        direct_match = (auth.get("child_pid") == actual_pid
                        and auth.get("parent_pid") == actual_ppid)

        windows_trampoline = False
        if not direct_match and os.name == "nt" and pid is None and parent_pid is None:
            # 1. Immediate parent must match the launched launcher stub
            # 2. Grandparent must match the parent runner PID
            # 3. Worker process must be confirmed active inside the supervisory Job Object
            launcher_pid = actual_ppid
            grandparent_pid = get_process_parent_pid(launcher_pid)
            if (auth.get("child_pid") == launcher_pid
                    and auth.get("parent_pid") == grandparent_pid
                    and verify_process_in_job()):
                windows_trampoline = True

        if not (direct_match or windows_trampoline):
            raise ValueError("Process ancestry verification failed")

        exclusive_json(Path(output) / "control/authorization_consumed.json", {
            "run_id": owner["run_id"],
            "worker_pid": actual_pid,
            "parent_pid": actual_ppid,
            "windows_trampoline": windows_trampoline,
            "timestamp": timestamp()
        })
        return owner
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PermissionError("Internal worker authorization rejected") from None
```

### 5.3 Security Properties of the Repaired Handshake
1. **Defense-in-Depth Restored**: The worker will reject authorization if it is not inside a Job Object, or if its parent was not spawned by `auth["parent_pid"]`.
2. **Zero Modification to Runner Orchestrator**: `scripts/phase8_2_1_arm.py` requires zero changes.
3. **POSIX & Direct Windows Compatibility**: Standard direct process execution (`direct_match`) continues to operate identically without invoking Toolhelp32.
4. **Durable Worker PID Accounting**: `authorization_consumed.json` records `worker_pid` and `windows_trampoline: true`, resolving the audit trail identity gap.

---

## 6. Comprehensive Regression Test Specification

The test suite in `tests/test_phase8_2_1_hardening.py` will be expanded to validate all six required failure and success scenarios:

### Test Case Matrix
| Test Case ID | Test Name | Invocation Method | Expected Outcome | Assertion Criteria |
|---|---|---|:---:|---|
| **AUTH-01** | `test_direct_worker_launch_without_pipe` | Worker spawned with `sys.stdin = devnull` or terminal stdin. | **REJECTED** | Exits with `PermissionError("Internal worker requires an authenticated private pipe")` before plan validation or imports. |
| **AUTH-02** | `test_windows_venv_trampoline_success` | Full child spawned via real `venv\Scripts\python.exe` attached to `Supervisor` Win32 Job Object. | **ACCEPTED** | Successfully consumes authorization; `authorization_consumed.json` written with `windows_trampoline=True` and real worker PID. |
| **AUTH-03** | `test_tampered_parent_or_child_identity` | Worker spawned under Job Object, but `parent_pid` in `authorization.json` is set to an arbitrary PID (e.g. 99999). | **REJECTED** | Toolhelp32 detects grandparent mismatch; throws `PermissionError("Internal worker authorization rejected")`. |
| **AUTH-04** | `test_trampoline_outside_job_object_rejected` | Worker spawned by matching parent/grandparent, but intentionally excluded from Job Object. | **REJECTED** | `verify_process_in_job()` returns `False`; throws `PermissionError`. |
| **AUTH-05** | `test_expired_and_reused_token_rejected` | 1. `now = auth["expires"] + 1`.<br/>2. Second call to `consume_authorization()`. | **REJECTED** | 1. Fails expiration check.<br/>2. `FileExistsError` on `authorization_consumed.json` converted to `PermissionError`. |
| **AUTH-06** | `test_forged_context_or_token_hash_mismatch` | Tampered token (e.g. `token[:63] + "0"`), altered `run_id`, or modified `source_export`. | **REJECTED** | HMAC comparison fails constant-time check; throws `PermissionError`. |
| **AUTH-07** | `test_worker_crash_and_timeout_cleanup` | Worker enters infinite sleep or exits with code 42. | **SUPERVISED** | Parent watchdog terminates Win32 Job Object (killing stub and worker); parent lifecycle records `terminal.json` with `timeout` or `child_failure`. |

---

## 7. Plan-Bound Artifacts & Gate v4 Transition Plan

### 7.1 Impact on Plan-Bound Files
In accordance with the immutable plan architecture, updating `scripts/phase8_2_1_controls.py` and adding tests to `tests/test_phase8_2_1_hardening.py` will change the following file hashes:

| File Path | Role | Current SHA-256 (Gate v3) | Status in Gate v4 |
|---|---|---|---|
| `scripts/phase8_2_1_controls.py` | Execution Control Adapter | `9b4383f1b9fa4fa94ca0901c07f6db1391831bd71b45ee2746e3dbd163547abd` | **Will Change** (repaired logic) |
| `tests/test_phase8_2_1_hardening.py` | Control Test Suite | `bfc9f426e73e3980ae63c2bd6bf2da0bccb65046e062aa273bb230104f83c3ad` | **Will Change** (7 regression tests) |
| `scripts/phase8_2_1_arm.py` | Runner Orchestrator | `3d6163bd22da1b8e1268888c6e03b6e477bf994a7d880591c9046df806b933a6` | **UNCHANGED** |
| `scripts/phase8_2_1_pytest.py` | Oracle Transport Harness | `0f026f6054aeb1194d854f9e36f11d95680018a15b9d1ba0cd73719ec2dfdee0` | **UNCHANGED** |
| `eval_results_phase8_2_1\...\source_hash_manifest.json` | Manifest of execution files | Bound to Gate v3 files | **Will Change** (Gate v4 manifest) |
| `eval_results_phase8_2_1\...\test_results.json` | Hardening test execution log | 57 passed | **Will Change** (64 passed in v4) |
| `eval_results_phase8_2_1\...\experiment_plan.json` | Canonical Plan Manifest | Digest: `7430f22335ee...` | **Superseded by Gate v4** |

### 7.2 Run Output Directory Segregation
The failed Arm A run directory `eval_results_phase8_2_1\20261025_142828_IST\runs\A` contains authentic evidence of the Windows venv stub behavior and must remain preserved and sealed.

Because `claim()` enforces `output.mkdir(exist_ok=False)`, the Gate v4 plan will specify a clean run root:
- `run_root`: `D:\Amit Stuff\ai-code-system\eval_results_phase8_2_1\20261027_145000_IST\runs`
- `arms.A.run_output`: `D:\Amit Stuff\ai-code-system\eval_results_phase8_2_1\20261027_145000_IST\runs\A`
- `arms.B.run_output`: `D:\Amit Stuff\ai-code-system\eval_results_phase8_2_1\20261027_145000_IST\runs\B`

### 7.3 Canonical Digest Lineage
The Gate v4 plan will formally record its lineage:
- `supersedes_unapproved_plan_sha256`: `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`
- `supersedes_prepared_plan_sha256`: `cea4b5a9eaa7b0c763b934f0473ea019efed9d333eeac8f2b82e8adf06c98204`
- `experiment_id`: `20261027_145000_IST_final_gate_v4`

---

## 8. Implementation & Verification Runbook (For Later Approved Phase)

When authorized, the repair will proceed through strict sequential gates:

1. **Step 1 — Code Editing**:
   Apply the verified trampoline match and Toolhelp32 inspection logic to `scripts/phase8_2_1_controls.py`.
2. **Step 2 — Test Augmentation**:
   Append the 7 regression tests to `tests/test_phase8_2_1_hardening.py`.
3. **Step 3 — Deterministic Test Execution**:
   Run `pytest tests/test_phase8_2_1_hardening.py -v` to ensure all 64 tests pass.
4. **Step 4 — Gate v4 Manifest Generation**:
   Execute `scripts/phase8_2_1_prepare.py` (or a dedicated gate v4 script) to:
   - Compute SHA-256 hashes of updated source files.
   - Stage `final_gate_v4\source_hash_manifest.json` and `final_gate_v4\test_results.json`.
   - Generate `final_gate_v4\experiment_plan.json`.
   - Compute and record the new canonical plan digest (`plan_file_sha256.txt`).
5. **Step 5 — Preflight Gate Audit**:
   Execute `validate_plan(check_environment=True)` on the new Gate v4 plan for Arm A and Arm B.
6. **Step 6 — Operator Approval & Live Launch**:
   Prompt operator to approve the new plan SHA-256, then launch Arm A.

---

## 9. Auditor Certification

I certify that during this phase:
- Zero project code files, tests, manifests, or plans were edited or overwritten.
- Zero model inference calls occurred.
- Zero experiment arms were executed.
- The preserved failed Arm A run artifacts remain untouched on disk.

*Design report complete. Standing by for user authorization to proceed to implementation.*
