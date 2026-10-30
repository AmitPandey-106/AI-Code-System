# Phase 3: Controlled Closed-Loop Self-Repair Experiment

## Overview
This experiment validates the closed-loop self-repair capability of the LITE-Coder architecture using controlled, reproducible test fixtures.

## Structure
- `tasks.py`: Defines the 5 multi-domain evaluation tasks with seeded defects and 3 negative controls.
- `runner.py`: Executes the automated closed-loop repair trajectory, tracking candidate hashes, error classifications, contract checks, and authoritative test results.
- `results.json`: Raw structured JSON output of the experiment execution.
- `PHASE3_SELF_REPAIR_REPORT.md`: Comprehensive scientific report detailing the methodology, per-task traces, aggregate metrics, negative controls, and findings.

## Execution
To reproduce the experiment:
```bash
python experiments/phase3_self_repair/runner.py
```

To run the unit test verification:
```bash
pytest -q test_phase3_self_repair.py
```
