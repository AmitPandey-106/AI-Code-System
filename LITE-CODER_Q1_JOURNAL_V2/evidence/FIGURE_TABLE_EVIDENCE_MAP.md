# FIGURE / TABLE EVIDENCE MAP

| Planned Figure / Table | Data Source | Experiment | Sample Size | Metric | RQ Supported | Availability of Data |
|---|---|---|---|---|---|---|
| **Table 1: Research Questions** | Manuscript Text | N/A | N/A | N/A | N/A | Available |
| **Table 2: Configurations** | `experiment_manifest.json` | All Modes | N/A | N/A | N/A | Available |
| **Table 3: Benchmark Characteristics** | `data/benchmark/v1.0/dataset.json` | N/A | 100 tasks | Difficulty, Domain | Setup | Available |
| **Table 4: Overall Results** | `raw_tasks/*.json` | Modes A, D, F, F_SAFE | 100 tasks/mode | Success Rate | RQ1, RQ3 | **REQUIRES EXTRACTION / EXPERIMENT** |
| **Table 5: Repair Effort** | `raw_tasks/*.json` | Modes A, D | 100 tasks/mode | Avg Attempts, Median | RQ2 | **REQUIRES EXTRACTION** |
| **Table 6: Ablation Results** | N/A | Mode D vs Mode F | 100 tasks/mode | Success, Latency | RQ3 | **REQUIRES EXPERIMENT** |
| **Table 7: Memory Statistics** | `repair_memory.json` | Mode D | 100 tasks | Growth rate, Similarity | RQ1 | **REQUIRES EXTRACTION** |
| **Table 8: Safety/Negative-Control** | Security tests | Mode D vs Mode F_SAFE | subset | Contamination Rate | RQ4 | **REQUIRES EXPERIMENT** |
| **Figure 1: Architecture** | Repo implementation | N/A | N/A | Diagram | Setup | Available |
| **Figure 2: Memory Growth** | `repair_memory.json` timestamps | Mode D | 100 tasks | Index size over time | RQ1 | **REQUIRES EXTRACTION** |
| **Figure 3: Repair Attempts (Boxplot)** | `raw_tasks/*.json` | Mode A vs D | 100 tasks/mode | Attempts distribution | RQ2 | **REQUIRES EXTRACTION** |
