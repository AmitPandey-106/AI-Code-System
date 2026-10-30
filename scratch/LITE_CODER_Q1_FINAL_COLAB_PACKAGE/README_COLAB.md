# LITE-CODER FINAL Q1 EXPERIMENTS

## INSTRUCTIONS
STEP 1: Upload/extract ZIP.
STEP 2: Open Google Colab.
STEP 3: Enable GPU: Runtime -> Change runtime type -> GPU
STEP 4: Verify: `torch.cuda.is_available()`
STEP 5: Run: `bash setup_colab.sh` (or `!bash setup_colab.sh` in Colab cell)
STEP 6: Run: `python RUN_FINAL_Q1_EXPERIMENTS.py`
STEP 7: Wait for: `FINAL EXPERIMENT PREFLIGHT: PASS`
STEP 8: Verify EXP_01 completion.
STEP 9: Verify EXP_02 starts with:
        Initial memory entries = 0
        Initial FAISS vectors = 0
STEP 10: After completion, collect:
        FINAL_Q1_EXP_01_CLEAN_BASELINE
        FINAL_Q1_EXP_02_CLEAN_MEMORY
        FINAL_Q1_EXP_01_EXP_02_COMPARISON.md

## SAFETY INSTRUCTIONS
- DO NOT upload the original development repository into the experiment runtime.
- DO NOT copy historical `repair_memory.json` into the package.
- DO NOT copy historical FAISS indexes.
- DO NOT manually populate EXP_02 memory.
- DO NOT modify the benchmark.
- DO NOT modify the runner after the GO audit.
- If preflight fails: STOP. Do not bypass the preflight check.

## EXPECTED OUTPUT STRUCTURE
```
experiments/
  FINAL_Q1_EXP_01_CLEAN_BASELINE/
    raw_tasks/
    statistics/
    logs/
    manifest.json
    experiment_manifest.json
    summary.json
    RESULTS.md
  FINAL_Q1_EXP_02_CLEAN_MEMORY/
    raw_tasks/
    statistics/
    logs/
    memory/
    retrieval/
    manifest.json
    experiment_manifest.json
    summary.json
    INITIAL_MEMORY_MANIFEST.json
    FINAL_MEMORY_MANIFEST.json
    RESULTS.md
  FINAL_Q1_EXP_01_EXP_02_COMPARISON.md
```
