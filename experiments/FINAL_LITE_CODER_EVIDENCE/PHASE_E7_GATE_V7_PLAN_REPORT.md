# LITE-Coder Phase E7 — Gate v7 Plan Preparation and Read-Only Validation Report

**Document Date:** October 27, 2026  
**Auditor / Engineer:** Senior Software Reliability Engineer, Windows Systems Engineer & Experimental Reproducibility Auditor  
**Phase:** E7 — Gate v7 Immutable Plan Preparation & Read-Only Validation  
**Repository Root:** `D:\Amit Stuff\ai-code-system`  
**Active Git Branch:** `fix/phase8-1-integration`  
**Active Head Commit:** `4cb53fbcbd8c2ce0f9cb7286ac0dcd4377915395`  
**Gate v7 Directory:** [`eval_results_phase8_2_1\20261027_gate_v7`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v7)  
**Superseded Gate v6 Plan Digest:** `a364f12bba42d5665963de1f1126021d63467db2892d69fbce6a519bba0fd950`  
**Gate v7 Canonical Plan Digest:** `6c06ffe76d421450232cf533f0f5b13a045221ae9e4ce5010b59c1121d7d4b58`  
**Gate v7 Raw Plan File SHA-256:** `aa0455fef1b9bb2f08f1dd1be8cdf6d5890d534d6eb23cef9533e3bb274c828b`  

---

## 1. Executive Summary & Verification Verdict

### Verification Status: **`GATE V7 EXPERIMENT PLAN PREPARED & VALIDATED — AWAITING OPERATOR LAUNCH`**

During the Gate v6 Arm A execution, the runner executed past all previous infrastructure hurdles:
1. Windows trampoline authentication succeeded within the designated Win32 Job Object.
2. The isolated pytest worker executed the initial test oracle, reproducing the canonical router defect (exit code 1).
3. Torch and model dependencies imported cleanly with the Phase E6 null-device exemption.
4. Model weights (`Qwen/Qwen2.5-Coder-1.5B-Instruct`) loaded onto CPU in 3.11s.
5. Model inference ran under greedy decoding (seed 42, repetition penalty 1.1), consuming 628 input tokens and generating a 38-token search/replace patch for [`micro_http/router.py`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v6/runs/A/workspace/fixture/micro_http/router.py).
6. The proposal SHA-256 (`9f42149b685e76d41fbc30b71790ab23dc4b24b0a6a76e7df063a8a4ef06913a`) was presented to the operator at the interactive human review prompt.

At the review gate, the prompt received non-matching input (`?`), causing the runner to fail closed as designed. The proposal was rejected, target writes remained locked, the fixture remained in its pristine failing state (`dcd69f55...`), and final evidence was recorded with `classification: "inconclusive_review_rejected"` and `proposal_approved: false`.

Because the runner strictly prohibits in-place directory re-claims (`output.mkdir(exist_ok=False)` and `FileExistsError: Output already exists; use a newly reviewed unique plan`), Gate v6 is permanently sealed. In accordance with the experiment protocol, **Gate v7** was prepared in a fresh directory with explicit lineage to Gate v6.

Read-only plan validation with full environment verification passed for both Arm A and Arm B in 29.43 seconds. All 86 model-free hardening and preflight tests passed in 15.67 seconds. Zero model weights were loaded, zero inference calls occurred, and zero patches were applied during Gate v7 preparation.

---

## 2. Gate v6 Preserved Evidence & Post-Mortem

### 2.1 Preserved Run Verification
The Gate v6 Arm A run directory remains sealed and byte-verified:
- **Run Directory:** [`eval_results_phase8_2_1/20261027_gate_v6/runs/A`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v6/runs/A)
- **Control Terminal Status:** `"completed"` ([`control/terminal.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v6/runs/A/control/terminal.json))
- **Worker Terminal Classification:** `"inconclusive_review_rejected"` ([`evidence/terminal.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v6/runs/A/evidence/terminal.json))
- **Session State:** `"cancelled"`, error message: `"User rejected proposed patch."`
- **Initial Oracle:** Exit code 1 (FAILED `test_slug_with_hyphen`, PASSED `test_basic_match`)
- **Final Oracle:** Exit code 1 (FAILED `test_slug_with_hyphen`, PASSED `test_basic_match`)
- **Target File Integrity:** [`micro_http/router.py`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v6/runs/A/workspace/fixture/micro_http/router.py) retains its initial hash (`dcd69f55a213daf4732bd53e1abab4f26ee96565bd303868aa8e7ac37609d4ba`). No edits were applied.

---

## 3. Gate v7 Plan Preparation & Binding

### 3.1 Directory Staging
- **Plan Directory:** `eval_results_phase8_2_1\20261027_gate_v7\`
- **Pre-Staged Runs Directory:** `eval_results_phase8_2_1\20261027_gate_v7\runs\`
- **Arm Outputs:**
  - Arm A: `eval_results_phase8_2_1\20261027_gate_v7\runs\A`
  - Arm B: `eval_results_phase8_2_1\20261027_gate_v7\runs\B`

### 3.2 Historical Root Exclusions
The Gate v6 runs root was appended to `historical_roots` to guarantee complete path disjointness:
- `eval_results_phase8_2_1\20261027_gate_v6\runs`
All previous roots (`eval_results_phase8`, `eval_results_phase8_1`, `eval_results_phase8_2`, `20261025_142828_IST\runs`, `20261027_gate_v4\runs`, `20261027_gate_v5\runs`) remain excluded.

### 3.3 Explicit Lineage Chain
Lineage is recorded in [`eval_results_phase8_2_1/20261027_gate_v7/plan_lineage.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v7/plan_lineage.json):
```
Gate v1 (Phase 8.2): cea4b5a9eaa7b0c763b934f0473ea019efed9d333eeac8f2b82e8adf06c98204
  └─ Gate v2:       d4bca7f3f8dbe7e82802577e08fb22fd62ba9043d17a1a4714b33b3c5c1ef25b
       └─ Gate v3:  7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424
            └─ Gate v4: 5bec1e2a44e36c824f09ead174dc8e7338fd503bc28d2c25e369043467bb81e0
                 └─ Gate v5: e90ac2fc8d7a1f7abfe3c94a6ce30b3c01d158a032e896eb203a575a3a03ab3e
                      └─ Gate v6: a364f12bba42d5665963de1f1126021d63467db2892d69fbce6a519bba0fd950
                           └─ Gate v7: 6c06ffe76d421450232cf533f0f5b13a045221ae9e4ce5010b59c1121d7d4b58
```

---

## 4. Verification Deliverables

### 4.1 Plan Paths and Cryptographic Digests
- **Gate v7 Plan Path:** [`eval_results_phase8_2_1/20261027_gate_v7/experiment_plan.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v7/experiment_plan.json)
- **Raw File SHA-256:** `aa0455fef1b9bb2f08f1dd1be8cdf6d5890d534d6eb23cef9533e3bb274c828b`
- **Canonical Plan Digest:** `6c06ffe76d421450232cf533f0f5b13a045221ae9e4ce5010b59c1121d7d4b58`
- **File Mode:** Read-only (`stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH`)

### 4.2 Read-Only Validation Results
Validation executed via [`scripts/phase8_2_1_arm.py:validate_plan`](file:///D:/Amit%20Stuff/ai-code-system/scripts/phase8_2_1_arm.py#L49) with `check_environment=True`:
- **Arm A Validation:** **PASSED**
- **Arm B Validation:** **PASSED**
- **Plan Digest Self-Check:** **PASSED**
- **Duration:** 29.43 seconds
- **Report Artifact:** [`eval_results_phase8_2_1/20261027_gate_v7/final_readonly_validation.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v7/final_readonly_validation.json)

### 4.3 Model-Free Controls Test Results
The 86 offline hardening and preflight tests were re-executed against Gate v7:
- **Suite Command:** `venv\Scripts\python.exe -B -m pytest tests/test_phase8_2_1_hardening.py tests/test_phase8_2_preflight.py -q -p no:cacheprovider --junitxml=eval_results_phase8_2_1\20261027_gate_v7\controls_passed.xml`
- **Tests Passed:** **86 of 86 (100%)**
- **Failures / Errors:** 0
- **Duration:** 15.67 seconds
- **JUnit XML:** [`eval_results_phase8_2_1/20261027_gate_v7/controls_passed.xml`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v7/controls_passed.xml)
- **Test Summary Record:** [`eval_results_phase8_2_1/20261027_gate_v7/test_results.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v7/test_results.json)

### 4.4 Confirmed Component Hashes

| Component | Bound Path / Identifier | Verified SHA-256 Digest |
| :--- | :--- | :--- |
| **Adapter** | `scripts/phase8_2_1_arm.py` | `3d6163bd22da1b8e1268888c6e03b6e477bf994a7d880591c9046df806b933a6` |
| **Controls** | `scripts/phase8_2_1_controls.py` | `ebda0b4960a05f7c50cbf64116440c1cf3b7631235eae78c5bfe1ad74ca74c74` |
| **Pytest Worker** | `scripts/phase8_2_1_pytest.py` | `0f026f6054aeb1194d854f9e36f11d95680018a15b9d1ba0cd73719ec2dfdee0` |
| **Canonical Prompt** | `common_model_prompt.txt` | `9f9ed1d8310e6792670551e66c9348e2192b4992a8df2630cab3a77cbb35af6d` |
| **Canonical Router Fixture** | `micro_http/router.py` | `dcd69f55a213daf4732bd53e1abab4f26ee96565bd303868aa8e7ac37609d4ba` |
| **Canonical Oracle Test** | `tests/test_router.py` | `1476656eefe48924bbe83ccc07d9d122e906ca7584f2f1aa77c6531fb9804838` |
| **Model Snapshot** | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | Pinned revision `2e1fd397ee46e1388853d2af2c993145b0f1098a` |

---

## 5. Approval-Gated Commands (NOT EXECUTED)

The launch commands are recorded in [`eval_results_phase8_2_1/20261027_gate_v7/approval_gated_commands.json`](file:///D:/Amit%20Stuff/ai-code-system/eval_results_phase8_2_1/20261027_gate_v7/approval_gated_commands.json). Neither command has been executed:

### Arm A (Baseline — Revision `9ef57511...`) — **NOT EXECUTED**
```powershell
venv\Scripts\python.exe -B scripts\phase8_2_1_arm.py --run --plan eval_results_phase8_2_1\20261027_gate_v7\experiment_plan.json --arm A --approved-plan-sha256 6c06ffe76d421450232cf533f0f5b13a045221ae9e4ce5010b59c1121d7d4b58
```
- **Operator Prompt 1 (Parent Approval):** Type the exact Gate v7 plan digest:
  ```text
  6c06ffe76d421450232cf533f0f5b13a045221ae9e4ce5010b59c1121d7d4b58
  ```
- **Operator Prompt 2 (Proposal Approval):** Review generated proposal and type the exact proposal SHA-256 (expected `9f42149b685e76d41fbc30b71790ab23dc4b24b0a6a76e7df063a8a4ef06913a`).

### Arm B (Candidate — Revision `920c01aa...`) — **NOT EXECUTED**
```powershell
venv\Scripts\python.exe -B scripts\phase8_2_1_arm.py --run --plan eval_results_phase8_2_1\20261027_gate_v7\experiment_plan.json --arm B --approved-plan-sha256 6c06ffe76d421450232cf533f0f5b13a045221ae9e4ce5010b59c1121d7d4b58
```
*(Requires prior successful completion of Arm A.)*

---

## 6. Risks and Open Issues

- **None.** All code, test, and control files are clean and unmodified. All 86 offline tests passed. The Gate v7 plan is immutable, validated, and ready for operator authorization.
