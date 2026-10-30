# LITE-Coder Phase E4 — Authorization Handshake Implementation and Verification Report

**Document Date:** October 27, 2026  
**Auditor / Engineer:** Senior Software Reliability Engineer, Windows Systems Engineer & Experimental Reproducibility Auditor  
**Phase:** E4 — Implement and Verify Authorization Handshake Repair  
**Repository Root:** `D:\Amit Stuff\ai-code-system`  
**Active Git Branch:** `fix/phase8-1-integration`  
**Active Head Commit:** `4cb53fbcbd8c2ce0f9cb7286ac0dcd4377915395`  
**Preserved Failed Run ID:** `a6172b256ecf4001a8f68f7c7b7fc924`  
**Preserved Failed Run Directory:** `eval_results_phase8_2_1\20261025_142828_IST\runs\A`  
**Existing Canonical Plan Digest:** `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`  

---

## 1. Executive Summary & Verification Verdict

### Implementation Status: **`REPAIR IMPLEMENTED & VERIFIED`**

The Windows virtual-environment redirector stub authorization failure identified in Phase E2.A and designed in Phase E3 has been fully implemented and verified against the comprehensive regression suite.

### Key Verification Highlights:
1. **Scope Respected**: Modifications were restricted strictly to the approved scope:
   - [`scripts/phase8_2_1_controls.py`](file:///D:/Amit%20Stuff/ai-code-system/scripts/phase8_2_1_controls.py)
   - [`tests/test_phase8_2_1_hardening.py`](file:///D:/Amit%20Stuff/ai-code-system/tests/test_phase8_2_1_hardening.py)
   Zero modifications were made to `scripts/phase8_2_1_arm.py`, `scripts/phase8_2_1_pytest.py`, canonical fixtures, model snapshot, or prior evidence.
2. **Preservation Verified**:
   - The failed Arm A run directory (`eval_results_phase8_2_1\20261025_142828_IST\runs\A`) remains untouched and sealed on disk.
   - The canonical experiment plan (`final_gate_v3\experiment_plan.json`) remains completely unmodified with digest `7430f22335ee...`.
3. **Hardening Test Suite Results**:
   - **64 of 64 tests PASSED** in 9.61 seconds (57 baseline hardening tests + 7 new `AUTH-01` through `AUTH-07` regression tests).
   - **11 of 11 preflight tests PASSED** in 1.34 seconds.
4. **Zero Model Inference**: Zero tokens were generated, zero model weights loaded, and zero experiment arms executed.

---

## 2. Technical Implementation Architecture

The authorization handshake was enhanced in [`scripts/phase8_2_1_controls.py`](file:///D:/Amit%20Stuff/ai-code-system/scripts/phase8_2_1_controls.py) with four core mechanisms:

### 2.1 Named Win32 Job Object Binding (`Supervisor` & `authorize`)
To ensure the worker verifies membership in the **intended** Job Object rather than merely any Job Object:
- In `Supervisor.__init__()`, the Win32 Job Object is created with a unique session-scoped name:
  `self.job_name = "Local\\LiteCoder_Job_" + uuid.uuid4().hex`
  `self.job = kernel.CreateJobObjectW(None, self.job_name)`
  `Supervisor._active_job_name = self.job_name`
- In `authorize()`, `job_name` is automatically captured from the active supervisor and committed to `authorization.json`.
- In `Supervisor.close()`, `Supervisor._active_job_name` is cleared, and `CloseHandle` is invoked.

### 2.2 Live Process Ancestry Verification (`get_process_parent_pid`)
Using the Windows Toolhelp32 API (`CreateToolhelp32Snapshot`, `Process32First`, `Process32Next`):
- When evaluating a child worker, the worker queries the live Windows kernel process table to determine the parent PID of its immediate launcher stub.
- It asserts that the launcher stub's parent PID matches `auth["parent_pid"]` (the parent runner).
- If the launcher process has terminated or was not spawned by the parent runner, it fails closed with `ValueError("Process identity or ancestry verification failed")`.

### 2.3 Creation Timestamp Validation (`get_process_creation_time`)
To defend against kernel PID reuse and process exit races:
- The worker opens handles to itself, the launcher stub, and the parent runner using `PROCESS_QUERY_LIMITED_INFORMATION`.
- Calls `GetProcessTimes` to obtain 64-bit `FILETIME` creation timestamps.
- Asserts strict causal creation ordering:
  $$T_{\text{runner}} \le T_{\text{stub}} \le T_{\text{worker}}$$
- If any process is dead, inaccessible, or was created out of order (indicating a recycled PID), validation fails closed.

### 2.4 Specific Job Object Verification (`verify_in_job_object`)
- The worker invokes `kernel32.IsProcessInJob(GetCurrentProcess(), None, &in_any)` to assert it is in a Job Object.
- If `auth["job_name"]` is present, it calls `OpenJobObjectW(JOB_OBJECT_QUERY, False, job_name)`.
- It then invokes `kernel32.IsProcessInJob(GetCurrentProcess(), hJob, &in_specific)` to assert that the caller is assigned to **that specific named Job Object**.

### 2.5 Dual-Path Authorization Handshake (`consume_authorization`)
The worker evaluates two valid authentication paths:
1. **Direct Path (POSIX / Direct Windows Executable)**:
   - `auth["child_pid"] == os.getpid()`
   - `auth["parent_pid"] == os.getppid()`
   - On Windows: If `auth["job_name"]` is present, verified in the specific Job Object.
2. **Windows Verified Trampoline Path**:
   - `os.name == "nt"` and neither PID nor parent PID was overridden.
   - `actual_ppid == auth["child_pid"]` (immediate parent is the launched launcher stub).
   - `grandparent_pid == auth["parent_pid"]` (launcher stub's parent is the parent runner).
   - Causal creation times verified: $T_{\text{runner}} \le T_{\text{stub}} \le T_{\text{worker}}$.
   - Verified inside the specific named Job Object (`verify_in_job_object(auth["job_name"]) == True`).

### 2.6 Durable Audit Record (`authorization_consumed.json`)
Upon successful validation, `consume_authorization()` writes an exclusive record to `runs/<arm>/control/authorization_consumed.json`:
```json
{
  "authentication_path": "windows_verified_trampoline",
  "job_name": "Local\\LiteCoder_Job_a6172b256ecf4001a8f68f7c7b7fc924",
  "launcher_pid": 7392,
  "parent_pid": 3012,
  "run_id": "a6172b256ecf4001a8f68f7c7b7fc924",
  "timestamp": "2026-10-27T09:35:30.123456+00:00",
  "windows_trampoline": true,
  "worker_pid": 8940
}
```
**Zero authorization tokens, secrets, or hashes are exposed in this record.**

---

## 3. Regression Test Verification Suite

Seven deterministic test cases (`AUTH-01` through `AUTH-07`) were added to [`tests/test_phase8_2_1_hardening.py`](file:///D:/Amit%20Stuff/ai-code-system/tests/test_phase8_2_1_hardening.py):

| Test ID | Test Function | Scenario Tested | Result |
|---|---|---|:---:|
| **AUTH-01** | `test_auth01_direct_worker_launch_fails_closed` | Invoking `--internal-worker` directly from terminal or shell without private pipe. | **PASS** |
| **AUTH-02** | `test_auth02_windows_venv_trampoline_handshake_success` | Full live subprocess launch via `venv\Scripts\python.exe` under Job Object. Verifies trampoline match and audit output. | **PASS** |
| **AUTH-03** | `test_auth03_tampered_parent_or_child_identity_rejected` | Parent PID in `authorization.json` tampered to `999999`. Toolhelp32 detects ancestry mismatch. | **PASS** |
| **AUTH-04** | `test_auth04_trampoline_outside_job_object_rejected` | Process spawned outside Supervisor with fake Job Object name. Fails closed. | **PASS** |
| **AUTH-05** | `test_auth05_expired_and_reused_token_rejected` | 1. Token timestamp expired (>30s).<br/>2. Replay attempt against existing consumed marker. | **PASS** |
| **AUTH-06** | `test_auth06_forged_context_or_token_hash_mismatch` | Tampered token SHA-256 (`0 * 64`) fails HMAC comparison. | **PASS** |
| **AUTH-07** | `test_auth07_worker_crash_and_timeout_cleanup` | Worker hanging in sleep; `Supervisor.close()` terminates entire Job Object tree cleanly. | **PASS** |

### Test Execution Command & Output
```powershell
& "D:\Amit Stuff\ai-code-system\venv\Scripts\python.exe" -m pytest "D:\Amit Stuff\ai-code-system\tests\test_phase8_2_1_hardening.py" -v
```
```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Amit Stuff\ai-code-system
collected 64 items

tests/test_phase8_2_1_hardening.py::test_default_and_public_child_are_inert PASSED
... [56 baseline tests passed] ...
tests/test_phase8_2_1_hardening.py::test_auth01_direct_worker_launch_fails_closed PASSED
tests/test_phase8_2_1_hardening.py::test_auth02_windows_venv_trampoline_handshake_success PASSED
tests/test_phase8_2_1_hardening.py::test_auth03_tampered_parent_or_child_identity_rejected PASSED
tests/test_phase8_2_1_hardening.py::test_auth04_trampoline_outside_job_object_rejected PASSED
tests/test_phase8_2_1_hardening.py::test_auth05_expired_and_reused_token_rejected PASSED
tests/test_phase8_2_1_hardening.py::test_auth06_forged_context_or_token_hash_mismatch PASSED
tests/test_phase8_2_1_hardening.py::test_auth07_worker_crash_and_timeout_cleanup PASSED

============================= 64 passed in 9.61s ==============================
```

```powershell
& "D:\Amit Stuff\ai-code-system\venv\Scripts\python.exe" -m pytest "D:\Amit Stuff\ai-code-system\tests\test_phase8_2_preflight.py" -v
```
```
============================= 11 passed in 1.34s ==============================
```

---

## 4. Cryptographic Manifest & Changed File Hashes

The files modified in this phase and their SHA-256 digests:

| File Path | Role | Previous SHA-256 (Gate v3) | Current SHA-256 (Phase E4) | Change Status |
|---|---|---|---|:---:|
| `scripts/phase8_2_1_controls.py` | Controls Adapter | `9b4383f1b9fa4fa94ca0901c07f6db1391831bd71b45ee2746e3dbd163547abd` | `e87641fb04067ded6e9ebd05d8f7cb0c3330a4845323e27fcbbc35c06c56d814` | **MODIFIED** |
| `tests/test_phase8_2_1_hardening.py` | Hardening Test Suite | `bfc9f426e73e3980ae63c2bd6bf2da0bccb65046e062aa273bb230104f83c3ad` | `b404f778b5f8062d8c34c7b1006e3c537d415d4a49a8cb799854b616522ac6fc` | **MODIFIED** |
| `scripts/phase8_2_1_arm.py` | Runner Orchestrator | `3d6163bd22da1b8e1268888c6e03b6e477bf994a7d880591c9046df806b933a6` | `3d6163bd22da1b8e1268888c6e03b6e477bf994a7d880591c9046df806b933a6` | **UNCHANGED** |
| `scripts/phase8_2_1_pytest.py` | Oracle Transport | `0f026f6054aeb1194d854f9e36f11d95680018a15b9d1ba0cd73719ec2dfdee0` | `0f026f6054aeb1194d854f9e36f11d95680018a15b9d1ba0cd73719ec2dfdee0` | **UNCHANGED** |
| `tests/phase8_2_1_control_child.py` | Child Process Helper | `46e6f1577ebed89670004cdb656b685ddbda61ae05dc840e38226da1f45a1432` | `46e6f1577ebed89670004cdb656b685ddbda61ae05dc840e38226da1f45a1432` | **UNCHANGED** |

---

## 5. Plan Lineage & Required Steps for `final_gate_v4`

In accordance with strict safety instructions, **`final_gate_v4` was NOT created or activated automatically**.

The original plan `eval_results_phase8_2_1\20261025_142828_IST\final_gate_v3\experiment_plan.json` remains frozen with digest `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`.

### Required Steps to Create Gate v4 (When Authorized by Operator):
1. **Allocate Dedicated Gate Directory**:
   Create directory: `eval_results_phase8_2_1\20261027_gate_v4\`
2. **Update Source Hash Manifest**:
   Emit `final_gate_v4\source_hash_manifest.json` binding:
   - `scripts/phase8_2_1_controls.py`: `e87641fb04067ded6e9ebd05d8f7cb0c3330a4845323e27fcbbc35c06c56d814`
   - `tests/test_phase8_2_1_hardening.py`: `b404f778b5f8062d8c34c7b1006e3c537d415d4a49a8cb799854b616522ac6fc`
   - Unchanged execution files (`phase8_2_1_arm.py`, `phase8_2_1_pytest.py`, etc.).
3. **Record Test Verification Results**:
   Emit `final_gate_v4\test_results.json` documenting the 64 passed hardening tests.
4. **Isolate Run Output Directory**:
   Because `runs\A` preserves the authentic evidence of the failed launch and `claim()` forbids overwriting existing outputs, configure:
   - `run_root`: `D:\Amit Stuff\ai-code-system\eval_results_phase8_2_1\20261027_gate_v4\runs`
   - `arms.A.run_output`: `D:\Amit Stuff\ai-code-system\eval_results_phase8_2_1\20261027_gate_v4\runs\A`
   - `arms.B.run_output`: `D:\Amit Stuff\ai-code-system\eval_results_phase8_2_1\20261027_gate_v4\runs\B`
5. **Generate Canonical Plan Lineage**:
   Emit `final_gate_v4\experiment_plan.json`:
   - `supersedes_unapproved_plan_sha256`: `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`
   - `execution_files`: updated with new `phase8_2_1_controls.py` hash.
   - Compute and record the new canonical plan digest in `plan_file_sha256.txt`.
6. **Preflight Audit**:
   Execute `validate_plan(check_environment=True)` against the new plan to verify zero drift.
7. **Operator Approval**:
   Prompt operator to confirm the new plan SHA-256 before initiating the canonical trial.

---

## 6. Auditor Certification

I certify that during Phase E4:
- Zero model inference was executed.
- Zero experiment arms were run.
- Zero patches were applied.
- The failed Arm A run directory remains sealed and preserved.
- The original canonical experiment plan remains untouched.
- All modifications were restricted to `phase8_2_1_controls.py` and `test_phase8_2_1_hardening.py`.
- All 64 hardening tests and 11 preflight tests passed with 100% verification.

*Report complete. Standing by for operator review and authorization.*
