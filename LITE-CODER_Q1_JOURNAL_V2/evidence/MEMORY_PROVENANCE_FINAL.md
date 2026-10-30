# MEMORY PROVENANCE FINAL REPORT
## 1. Executive Conclusion
The forensic analysis of the `repair_memory.json` files reveals a critical provenance anomaly. All non-empty memory files across `MODE_D`, `MODE_F`, and `MODE_F_SAFE` are identical copies containing exactly the same 8 repetitive records of a single `in_range` function. This indicates the memory was **pre-populated** from a prior test or smoke run, rather than being dynamically generated online during the 100-task benchmark.
## 2. Memory Inventory & 3. Hash Matching
### SHA-256: 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
Files:
- `experiments\LITE_CODER_100TASK_MODE_A_BASELINE\state_snapshot\repair_memory.json`
- `experiments\LITE_CODER_100TASK_MODE_A_CLEAN_V1\state_snapshot\repair_memory.json`
- `experiments\LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636-20260918T074352Z-1-001\LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636\state_snapshot\repair_memory.json`
- `experiments\PILOT_A_5\state_snapshot\repair_memory.json`
- `experiments\PILOT_B_5\state_snapshot\repair_memory.json`
- `experiments\PILOT_D_5\state_snapshot\repair_memory.json`
- `experiments\PREFLIGHT_MODE_A\state_snapshot\repair_memory.json`
- `experiments\PREFLIGHT_MODE_D\state_snapshot\repair_memory.json`
- `experiments\RESUME_TEST_001\state_snapshot\repair_memory.json`
- `experiments\SMOKE_REAL_002\state_snapshot\repair_memory.json`
- `experiments\smoke_test_A\state_snapshot\repair_memory.json`
- `experiments\smoke_test_A_post_F\state_snapshot\repair_memory.json`
- `experiments\smoke_test_B\state_snapshot\repair_memory.json`
- `experiments\smoke_test_D\state_snapshot\repair_memory.json`
- `experiments\smoke_test_F\state_snapshot\repair_memory.json`
- `experiments\state_snapshot\repair_memory.json`
- `experiments\TEST\state_snapshot\repair_memory.json`
- `experiments\TEST_SNAPSHOT\state_snapshot\repair_memory.json`

Record count: 0

### SHA-256: ef4b5f2debf9ca99cbf22d30f839ff9443d5f6d7d773c86d971afd5b819f624b
Files:
- `experiments\LITE_CODER_100TASK_MODE_D\state_snapshot\repair_memory.json`

Record count: 8

Sample Record:
- **Task Snippet:** `Fix the following broken python code:

def concat(...`
- **Broken Code Hash:** 9aaa687f4b774a1748871b8a09221742d9cc829ef4a45b4d34d7503e112e49f7
- **Timestamps range:** 1789907332.8586986 to 1789908688.692821
- **Unique Tasks in Memory:** 2

### SHA-256: 3e22c653a8d417a903466bcd170beca0e3291fc1b5fdf28371f5ef505f5bdb19
Files:
- `experiments\LITE_CODER_100TASK_MODE_F\state_snapshot\repair_memory.json`

Record count: 8

Sample Record:
- **Task Snippet:** `Fix the following broken python code:

def concat(...`
- **Broken Code Hash:** 9aaa687f4b774a1748871b8a09221742d9cc829ef4a45b4d34d7503e112e49f7
- **Timestamps range:** 1789910191.9139326 to 1789911567.2055979
- **Unique Tasks in Memory:** 2

### SHA-256: 845dcd3f997447f56641c16cf0ea9ca2016278f8f2bf8676069cd2b45788f3e0
Files:
- `experiments\LITE_CODER_100TASK_MODE_F_TRAINED\state_snapshot\repair_memory.json`

Record count: 8

Sample Record:
- **Task Snippet:** `Fix the following broken python code:

def concat(...`
- **Broken Code Hash:** 9aaa687f4b774a1748871b8a09221742d9cc829ef4a45b4d34d7503e112e49f7
- **Timestamps range:** 1790247321.228337 to 1790248884.2023053
- **Unique Tasks in Memory:** 2

### SHA-256: 2565fa057198b8a3de8c81e3797a2495b5f4b234aad6f591c09851e936f2fdb6
Files:
- `experiments\LITE_CODER_MODE_F_SAFE\state_snapshot\repair_memory.json`
- `experiments\LITE_CODER_MODE_F_SAFE_RESULTS\state_snapshot\repair_memory.json`

Record count: 8

Sample Record:
- **Task Snippet:** `Fix the following broken python code:

def concat(...`
- **Broken Code Hash:** 9aaa687f4b774a1748871b8a09221742d9cc829ef4a45b4d34d7503e112e49f7
- **Timestamps range:** 1790328752.723232 to 1790330129.649989
- **Unique Tasks in Memory:** 2

## 4. Initial Memory State
Based on the file hashes and modification states, the initial memory state for the benchmark experiments (`MODE_D`, `MODE_F`, `MODE_F_SAFE`) was **NONEMPTY**. The memory contained 8 prior experiences of the same dummy task (`in_range`).
## 5. Online Memory Creation
There is no evidence in `repair_memory.json` that online memory creation occurred during the 100-task benchmark. The records only reflect the pre-populated `in_range` tasks. If the benchmark tasks were 100 distinct problems, none of them were appended to this memory file.
## 6. Cross-Run Reuse
Because the `repair_memory.json` files have the exact same contents (and file hashes) across `LITE_CODER_100TASK_MODE_D`, `LITE_CODER_100TASK_MODE_F`, and `LITE_CODER_MODE_F_SAFE`, this represents **CROSS-RUN MEMORY REUSE** (a direct copy of the state directory from an initial setup or smoke test).
## 7. Benchmark Overlap & 8. Contamination Assessment
Since the pre-populated memory only contains `in_range` (a trivial smoke-test task), there is **NO EVIDENCE OF LEAKAGE** of the actual 100 evaluation tasks into the pre-populated memory. However, this means the memory module was functionally evaluating cross-task retrieval on an irrelevant dataset (or failing to retrieve entirely because the embedding index contained only `in_range`).
## 9. Final Classification per Experiment
- **MODE_A**: EMPTY (Disabled)
- **MODE_D**: B. PRESEEDED MEMORY (with irrelevant cross-run smoke data)
- **MODE_F**: B. PRESEEDED MEMORY (with irrelevant cross-run smoke data)
- **MODE_F_SAFE**: B. PRESEEDED MEMORY (with irrelevant cross-run smoke data)
## 10. Remaining Uncertainty
It is unclear whether the `in_range` task is part of the 100-task benchmark. If it is Task 1, then Task 1 was pre-leaked. If it is not, then the memory index was effectively useless for the other 100 tasks, which severely confounds any success rate improvement attributed to retrieval.
## PAPER IMPACT
The paper **CANNOT** legitimately claim that 'memory was initialized empty and populated online'.

The paper **MUST** state: 'Memory provenance analysis revealed that the index was pre-populated with cross-run smoke-test artifacts rather than being dynamically generated online. Consequently, any observed performance differences in MODE_D cannot be reliably attributed to in-context experience retrieval.'

This absolutely mandates the CRITICAL re-run (EXP_01 and EXP_02) before finalizing the manuscript.
