# LITE-CODER Phase 6 — Continuous Benchmarking & Scientific Self-Evaluation

## 1. Objective
To establish a rigorous, reproducible, scientifically valid benchmarking infrastructure capable of isolating the individual and cumulative contributions of Experience Memory, Trusted Verification, Strategy Learning, and LoRA self-improvement.

## 2. Motivation
LITE-CODER has evolved into a highly complex, multi-layered architecture. To achieve IEEE-level research quality, we must empirically measure the system's claims. An advanced pipeline is meaningless if its components degrade performance, increase computational waste without benefit, or merely overfit on a few tasks.

## 3. Benchmark Architecture
We introduced a dedicated `benchmark` package:
- `dataset.py`: Centralized, versioned task sets with explicit expected tests.
- `ablation.py`: Deterministically isolates experimental modes by injecting config overrides.
- `runner.py`: Orchestrates the testing, ensuring task failures are gracefully caught without terminating the benchmark.
- `reporter.py`: Dumps metrics, statistics, and trajectories into isolated `experiments/{EXP_ID}` directories.
- `statistics.py`: Provides bootstrap confidence intervals for robust comparisons.

## 4. Dataset Design
The `data/benchmark/dataset.json` avoids relying solely on LLM-generated tests. Each task includes deterministic `expected_tests` and covers varying complexity (e.g., Recursion, Algorithms, Strings) and difficulty bounds to correctly evaluate the Difficulty Estimator from Phase 5.

## 5. Experimental Modes
Configurable ablation modes control the test environment:
- **MODE A (Baseline):** Qwen2.5-Coder-1.5B (No Memory, No Strategy, No LoRA).
- **MODE B:** Memory ON (pure RAG).
- **MODE C:** Memory ON + Verification ON.
- **MODE D:** Memory ON + Strategy Learning ON + Difficulty Allocation ON.
- **MODE E:** Memory ON + LoRA ON.
- **MODE F (Full):** All LITE-CODER systems enabled.

## 6. Evaluation Protocol
The benchmark runner utilizes isolated environments per run. It explicitly resets `data/repair_memory.json`, `data/strategy_stats.json`, and FAISS indices before initiating a mode to prevent Cross-Experiment Contamination.

## 7. Metrics
- **Primary:** Repair Success Rate, Average Repair Attempts, Median Execution Time.
- **Diagnostic:** Memory Utilization Rate, Strategy Performance, Error Type Performance.
- **Cost:** Repair Effort (Number of attempts × compute time).

## 8. Ablation Methodology
By running identical tasks under `MODE A` vs `MODE D` vs `MODE F`, we can statistically test H1 (Memory improves success), H2 (Strategy reduces attempts), and H5 (Cumulative synergy).

## 9. Continual Learning Evaluation
The continuous mode feeds tasks sequentially, verifying outputs, building memory, dynamically shifting Strategy scores, and conditionally generating LoRA adapters. Subsequent task performance accurately reflects accumulated knowledge.

## 10. Statistical Methodology
Leveraging `numpy`, the `statistics.py` module computes medians (for skewed execution times) and Bootstrap Confidence Intervals (95% CI) for Success Rates and Repair Effort to ensure results are statistically significant despite small sample sizes.

## 11. Leakage Prevention
Training datasets strictly exclude Anchor Sets. Test trajectories only ever enter the `training_dataset` compiler if continuous evaluation mode explicitly permits it.

## 12. Anchor Set Evaluation
A small reserved pool of tasks evaluates Candidate LoRA models against the active model strictly ensuring that long-term adaptation does not induce catastrophic performance degradation.

## 13. Computational Evaluation
Resource measurements separate *Inference Cost* (model generation time) from *Orchestration Cost* (FAISS lookup, verification time, compilation).

## 14. Reproducibility
Centralized random seed logic (`BENCHMARK_SEED = 42`) in `app.config` controls NumPy, Python Random, and FAISS stochasticity to maximize replication fidelity across varying hardware.

## 15. Tests
We added `tests/test_benchmark.py` guaranteeing metric calculations, data-loading logic, and dynamic config overrides (ablation) function exactly as designed.

## 16. Initial Experimental Results
*Benchmark infrastructure implemented; large-scale evaluation pending.*
A micro end-to-end benchmark (`run_micro_benchmark.py`) successfully executed MODE A and MODE D side-by-side, creating isolated reports and successfully catching and isolating timeouts without crashing.

## 17. Failure Analysis
Because the benchmark runner never swallows fatal Exceptions natively, we can capture which tasks explicitly OOM the local instance vs those which simply time out during generation, separating framework bugs from model limitations.

## 18. Limitations
True multi-epoch continual evaluation on a laptop is fundamentally restricted by hardware thermal throttling and time constraints. Full IEEE evaluation will require migrating the framework to a controlled remote testbed for multi-day uninterrupted runs.

## 19. Research Questions
RQ1: Does adaptive strategy learning reduce repair effort?
RQ2: Does LoRA adaptation improve native repair performance without catastrophic degradation?
RQ3: What is the computational cost of self-improvement on laptop hardware?

## 20. Phase 7 Recommendation
With all theoretical mechanisms proven and the evaluation harness built, **Phase 7** must consist of generating a massive scale (1,000+ task) synthetically corrupted dataset and executing a multi-day continuous benchmark run to publish the empirical findings.
