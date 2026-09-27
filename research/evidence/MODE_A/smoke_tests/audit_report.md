# LITE-CODER Forensic Audit Report

**Experiment:** `None`  
**Mode:** `None`  
**Model:** `None`  
**Audit Generated:** 2026-09-18T14:12:17.873838  

---

## 1. Dataset

| Field | Value |
|---|---|
| Path | `data/benchmark/v1.0/dataset.json` |
| Exists | True |
| Task Count | 100 |
| SHA256 | `2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620` |
| Duplicate IDs | [] |

---

## 2. Experiment Manifest

| Field | Value |
|---|---|
| Experiment ID | `None` |
| Mode | `None` |
| Model | `None` |
| Seed | `None` |
| Deterministic | `None` |
| Benchmark Size | `None` |
| Dataset SHA256 | `None` |
| Memory Enabled | `None` |
| Strategy Learning | `None` |
| LoRA Enabled | `None` |

**Issues:** Manifest file missing

---

## 3. Checkpoint

| Field | Count |
|---|---|
| Total Records | 3 |
| Unique Task IDs | 3 |
| success=True | 2 |
| success=False | 0 |
| success=null | 1 |

**Status Counts:**

- `model_success`: 2
- `infrastructure_failure`: 1

**Error Categories:**

- `none`: 2
- `runner`: 1

**Error Types:**

- `none`: 2
- `TypeError`: 1

---

## 4. Raw Task Records

| Field | Count |
|---|---|
| Total Files | 3 |
| Has Generated Code | 2 |
| Has Attempts | 2 |
| Has Execution | 2 |
| Has Tests | 2 |
| Has Verification | 2 |
| Has Traceback (infra errors) | 1 |
| Has Error Diagnostic | 1 |

**Outcome Breakdown:**

- `INFRASTRUCTURE_FAILURE`: 1
- `MODEL_SUCCESS`: 2

---

## 5. Feedback

| Field | Value |
|---|---|
| Feedback File Exists | False |
| Feedback Count | 0 |

---

## 6. Summary

| Metric | Value |
|---|---|
| Dataset Size | 100 |
| Tasks Executed | 3 |
| MODEL_SUCCESS | **2** |
| MODEL_FAILURE | 0 |
| INFRASTRUCTURE_FAILURE | 1 |
| VERIFICATION_FAILURE | 0 |
| UNRESOLVED | 0 |
| Is Complete Run | False |
| All Resolved | False |

---

## 7. Per-Task Detail

| # | Task ID | Outcome | Success | Has Code | Has Exec | Has Tests | Error Type | Runtime (ms) |
|---|---|---|---|---|---|---|---|---|
| 3 | `TASK_1E88EF5E` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 0 |
| 1 | `TASK_248A149E` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 0 |
| 2 | `TASK_C4A8AE96` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 0 |