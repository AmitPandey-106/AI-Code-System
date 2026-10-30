# MEMORY PROVENANCE

Based on repository evidence (`repair_memory.json` snapshots showing exactly 8 records for Mode D, Mode F, and Mode F_SAFE):

**A. Was memory empty before benchmark execution?**
UNKNOWN. The presence of exactly 8 records across different experimental modes suggests either a shared pre-populated state or deterministic online learning that succeeded exactly 8 times.

**B. Was memory pre-populated?**
POSSIBLE. If the files are identical across Mode D and Mode F, it heavily implies they were copied from a shared pre-flight experiment rather than generated online dynamically (since LoRA vs Base model should theoretically yield different success trajectories).

**C. If pre-populated, exactly which experiences were present?**
Requires extracting the `task_id` fields from the 8 records in `repair_memory.json`.

**D. Where did those experiences originate?**
UNKNOWN pending task ID extraction.

**E. Were any experiences generated from benchmark evaluation tasks?**
If the task IDs in the 8 records belong to the 100-task benchmark, yes.

**F. Was memory populated dynamically during the benchmark?**
UNKNOWN. The consistency of "8 records" across modes raises questions about whether the memory updater was active or if a static index was used.

**G. Could task N retrieve an experience generated from task N-1?**
The architecture supports this (online continual learning).

**H. Could a task retrieve an experience generated from the same benchmark dataset?**
Yes, this is cross-task experience reuse (which is a valid evaluation of online learning, provided memory starts empty).

**I. Was the memory reset between runs?**
UNKNOWN.

**J. Was the FAISS index rebuilt or reused?**
UNKNOWN. Timestamps of `.faiss` files must be compared.

**K. Was repair_memory.json copied from another experiment?**
HIGHLY LIKELY given the identical record counts, but requires hash comparison.

## DATA LEAKAGE STATUS
**CLASSIFICATION: UNKNOWN (Requires Hash/Task ID Inspection)**

If memory is dynamically generated from previous evaluation tasks, it is **online continual adaptation** (cross-task experience reuse), which is valid if explicitly stated. However, if the memory was pre-populated with evaluation tasks prior to the run, this constitutes **train/test leakage**.
