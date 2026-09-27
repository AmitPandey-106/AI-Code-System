# LITE-CODER Final Experimental Evidence Audit

Generated: 2026-09-24T12:50:44.496681

This report is generated from existing experiment artifacts. The experiment directories are read-only inputs to this audit.

## Experiment Summary

| Experiment | Tasks | Success | Avg Attempts | Median | Tests Passed | Audit |
|---|---:|---:|---:|---:|---:|---|
| MODE_A_BASELINE | 100 | 100 | 1.58 | 1.0 | 100 | PASS |
| MODE_A_CLEAN_V1 | 18 | 15 | 1 | 1 | 15 | FAIL |
| MODE_D | 100 | 100 | 1.26 | 1.0 | 100 | PASS |
| MODE_F | 100 | 100 | 1.26 | 1.0 | 100 | PASS |

## MODE-A Candidate Comparison

### MODE_A_BASELINE

- Tasks: 100
- Successes: 100
- Average attempts: 1.58
- Median attempts: 1.0
- Attempt distribution: {1: 76, 2: 6, 3: 2, 4: 16}
- NoneType bookkeeping errors: 0
### MODE_A_CLEAN_V1

- Tasks: 18
- Successes: 15
- Average attempts: 1
- Median attempts: 1
- Attempt distribution: {1: 15}
- NoneType bookkeeping errors: 3

## MODE-F LoRA Evidence

- LoRA/training artifact matches found: 0
- The presence of `lora_enabled=true` in a manifest is configuration evidence, not proof of successful adapter training.
- Any LoRA training failure observed in the original run should remain documented separately from repair success.

## State Artifacts

### MODE_A_BASELINE

- `repair_memory.json`: PRESENT, size=2 bytes
- `repair_memory_index.faiss`: PRESENT, size=45 bytes
- `strategy_stats.json`: PRESENT, size=2 bytes
### MODE_A_CLEAN_V1

- `repair_memory.json`: PRESENT, size=2 bytes
- `repair_memory_index.faiss`: PRESENT, size=45 bytes
- `strategy_stats.json`: PRESENT, size=2 bytes
### MODE_D

- `repair_memory.json`: PRESENT, size=12442 bytes
- `repair_memory_index.faiss`: PRESENT, size=12333 bytes
- `strategy_stats.json`: PRESENT, size=549 bytes
### MODE_F

- `repair_memory.json`: PRESENT, size=12294 bytes
- `repair_memory_index.faiss`: PRESENT, size=12333 bytes
- `strategy_stats.json`: PRESENT, size=550 bytes

## Integrity Notes

- Benchmark experiment directories were not modified by this audit.
- No benchmark was executed by this audit.
- MODE-A artifacts are kept as separate candidates until their provenance is reviewed.
