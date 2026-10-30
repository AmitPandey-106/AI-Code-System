# PAPER CLAIM EVIDENCE MATRIX

| CLAIM | EVIDENCE | SOURCE FILE | EXPERIMENT | METRIC | STATUS |
|---|---|---|---|---|---|
| LITE-Coder memory improves success rate | Extracted stats | historical_task_level_results.csv | MODE_A vs MODE_D | success_rate | PARTIALLY_SUPPORTED |
| LITE-Coder reduces attempts | Extracted stats | historical_task_level_results.csv | MODE_A vs MODE_D | mean_attempts | PARTIALLY_SUPPORTED |
| Retrieval overhead < 100ms | Latency fields | latency_evidence.csv | MODE_D | retrieval_time_ms | REQUIRES_NEW_EXPERIMENT |
| Safe Mode protects against execution vulnerabilities | SAFE extraction | mode_f_safe_evidence.csv | MODE_F_SAFE | adversarial_results | REQUIRES_NEW_EXPERIMENT |
