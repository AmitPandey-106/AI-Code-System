# LITE-CODER Forensic Audit Report

**Experiment:** `LITE_CODER_100TASK_POST_P0_002_A`  
**Mode:** `MODE_A`  
**Model:** `Qwen/Qwen2.5-Coder-1.5B`  
**Audit Generated:** 2026-09-18T14:11:06.074247  

---

## 1. Dataset

| Field | Value |
|---|---|
| Path | `/content/drive/MyDrive/LITE-CODER Code/ai-code-system/data/benchmark/v1.0/dataset.json` |
| Exists | False |
| Task Count | 0 |
| SHA256 | `` |
| Duplicate IDs | [] |

**Issues:** Dataset file not found

---

## 2. Experiment Manifest

| Field | Value |
|---|---|
| Experiment ID | `LITE_CODER_100TASK_POST_P0_002_A` |
| Mode | `MODE_A` |
| Model | `Qwen/Qwen2.5-Coder-1.5B` |
| Seed | `42` |
| Deterministic | `True` |
| Benchmark Size | `100` |
| Dataset SHA256 | `7f7ff7305431cc66e8ee327a3c209b788d84818a9651789d70a56653376c47f6` |
| Memory Enabled | `False` |
| Strategy Learning | `False` |
| LoRA Enabled | `False` |

---

## 3. Checkpoint

| Field | Count |
|---|---|
| Total Records | 100 |
| Unique Task IDs | 100 |
| success=True | 76 |
| success=False | 0 |
| success=null | 24 |

**Status Counts:**

- `unspecified`: 100

**Error Categories:**

- `none`: 100

**Error Types:**

- `none`: 76
- `TypeError`: 24

---

## 4. Raw Task Records

| Field | Count |
|---|---|
| Total Files | 100 |
| Has Generated Code | 76 |
| Has Attempts | 76 |
| Has Execution | 76 |
| Has Tests | 76 |
| Has Verification | 76 |
| Has Traceback (infra errors) | 0 |
| Has Error Diagnostic | 0 |

**Outcome Breakdown:**

- `INFRASTRUCTURE_FAILURE`: 24
- `MODEL_SUCCESS`: 76

---

## 5. Feedback

| Field | Value |
|---|---|
| Feedback File Exists | True |
| Feedback Count | 76 |

---

## 6. Summary

| Metric | Value |
|---|---|
| Dataset Size | 100 |
| Tasks Executed | 100 |
| MODEL_SUCCESS | **76** |
| MODEL_FAILURE | 0 |
| INFRASTRUCTURE_FAILURE | 24 |
| VERIFICATION_FAILURE | 0 |
| UNRESOLVED | 0 |
| Is Complete Run | True |
| All Resolved | False |

---

## 7. Per-Task Detail

| # | Task ID | Outcome | Success | Has Code | Has Exec | Has Tests | Error Type | Runtime (ms) |
|---|---|---|---|---|---|---|---|---|
| 84 | `TASK_00487A65` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18498 |
| 42 | `TASK_01CF853B` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11809 |
| 68 | `TASK_02A5297E` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 9498 |
| 49 | `TASK_07E3AAD9` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 19221 |
| 96 | `TASK_0DB97680` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 27313 |
| 71 | `TASK_0E25977A` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12328 |
| 35 | `TASK_115EF1B7` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 9765 |
| 20 | `TASK_16D34D22` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10677 |
| 37 | `TASK_171B092B` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11858 |
| 14 | `TASK_18282011` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10801 |
| 40 | `TASK_1949AD82` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10697 |
| 19 | `TASK_1AC7E084` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28490 |
| 65 | `TASK_1DA9FFE1` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12578 |
| 3 | `TASK_1E88EF5E` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 29413 |
| 89 | `TASK_21D2E862` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 14660 |
| 43 | `TASK_22EF6E15` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18083 |
| 25 | `TASK_24351ED5` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10607 |
| 1 | `TASK_248A149E` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12082 |
| 70 | `TASK_26E9FDB3` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11267 |
| 75 | `TASK_29DC986C` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17920 |
| 79 | `TASK_2A60D1B1` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 26560 |
| 5 | `TASK_2B6D2849` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18288 |
| 51 | `TASK_2BECF080` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 9896 |
| 6 | `TASK_343500D2` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11822 |
| 55 | `TASK_34E90ED9` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28278 |
| 78 | `TASK_37352093` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18338 |
| 93 | `TASK_3CA90906` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 20044 |
| 83 | `TASK_43200D99` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 13007 |
| 44 | `TASK_435DA3AE` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28514 |
| 60 | `TASK_43D5CB16` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18207 |
| 54 | `TASK_44FC1C51` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18380 |
| 94 | `TASK_46D3F670` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10825 |
| 58 | `TASK_46FE7E87` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11869 |
| 36 | `TASK_492A6DB5` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 20491 |
| 63 | `TASK_495776C1` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 20332 |
| 82 | `TASK_4DD4E728` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12081 |
| 81 | `TASK_4F646FFF` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17264 |
| 77 | `TASK_4FC2042B` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12544 |
| 50 | `TASK_50B0F89F` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28147 |
| 13 | `TASK_527A01D3` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28304 |
| 91 | `TASK_52F6CB07` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 27376 |
| 15 | `TASK_53CB0778` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17120 |
| 21 | `TASK_55A55247` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 20882 |
| 56 | `TASK_58D4007C` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10637 |
| 4 | `TASK_5A10345D` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10009 |
| 16 | `TASK_5A9419BC` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11939 |
| 7 | `TASK_5C5F2013` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18223 |
| 28 | `TASK_602420FB` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18400 |
| 57 | `TASK_61DE3671` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 19373 |
| 61 | `TASK_61ECFD6A` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28097 |
| 85 | `TASK_64497C8C` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28367 |
| 18 | `TASK_69A14E63` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18102 |
| 11 | `TASK_6D787E00` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11933 |
| 73 | `TASK_71B9E063` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 26931 |
| 29 | `TASK_761B7D7E` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28440 |
| 98 | `TASK_77C30EA5` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17634 |
| 10 | `TASK_78F9D7AB` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17337 |
| 31 | `TASK_7AE983CC` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17594 |
| 24 | `TASK_7C30D0A1` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 27025 |
| 90 | `TASK_7D2AAE3E` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18317 |
| 100 | `TASK_803EEF67` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12337 |
| 64 | `TASK_86ABF08F` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11000 |
| 38 | `TASK_88179AD5` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18151 |
| 76 | `TASK_8CAFAF3C` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11974 |
| 22 | `TASK_8CCE471D` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11591 |
| 9 | `TASK_8E0AE6BB` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10998 |
| 33 | `TASK_8E25E875` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 19028 |
| 67 | `TASK_8FC95909` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 26455 |
| 62 | `TASK_92164E2D` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10699 |
| 34 | `TASK_96161F4B` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 28201 |
| 53 | `TASK_995A9CD2` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11621 |
| 41 | `TASK_996BE834` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17497 |
| 99 | `TASK_9A262A5F` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11656 |
| 26 | `TASK_A076C74B` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17498 |
| 59 | `TASK_ABC07B11` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12818 |
| 12 | `TASK_AC1D1EC0` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18187 |
| 74 | `TASK_ACCDEA61` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10211 |
| 86 | `TASK_B1315198` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10590 |
| 80 | `TASK_B8A15ABC` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10835 |
| 39 | `TASK_BC89315E` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 26667 |
| 66 | `TASK_BDCCF2EB` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 19085 |
| 47 | `TASK_C305BDB3` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11382 |
| 32 | `TASK_C3E37906` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11905 |
| 2 | `TASK_C4A8AE96` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18699 |
| 48 | `TASK_C615FC35` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12820 |
| 87 | `TASK_D027C3B7` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 17360 |
| 72 | `TASK_D63646F1` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18978 |
| 27 | `TASK_D6757592` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11941 |
| 97 | `TASK_DA1469C8` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10318 |
| 95 | `TASK_DA87DDDF` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18766 |
| 45 | `TASK_DAE61E15` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10931 |
| 69 | `TASK_E4D12ED6` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18217 |
| 30 | `TASK_E6E16446` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10744 |
| 46 | `TASK_E86381A6` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 19850 |
| 23 | `TASK_F4CD3BEC` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18528 |
| 92 | `TASK_F69F485C` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 10431 |
| 88 | `TASK_F8BC87BE` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 11796 |
| 8 | `TASK_FB475E1F` | INFRASTRUCTURE_FAILURE | None | ✗ | ✗ | ✗ | `TypeError` | 26876 |
| 52 | `TASK_FE335544` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 18289 |
| 17 | `TASK_FEE64E00` | MODEL_SUCCESS | True | ✓ | ✓ | ✓ | `-` | 12997 |