# LITE-CODER Statistical Analysis

Paired task-level analysis of repair attempts across the authoritative 100-task experiments.

## Statistical methods

- Exact two-sided sign test
- Wilcoxon signed-rank test
- Paired standardized effect size
- Deterministic bootstrap 95% CI for mean paired difference
- Bonferroni correction for three pairwise comparisons

| Comparison | Mean Diff | Median Diff | Improved | Worse | Equal | Sign p | Wilcoxon p | Effect |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MODE_A_vs_MODE_D | 0.3200 | 0.0000 | 17 | 0 | 83 | 3.0517578e-05 | 7.9956428e-05 | 0.4426 |
| MODE_A_vs_MODE_F | 0.3200 | 0.0000 | 17 | 0 | 83 | 3.0517578e-05 | 7.9956428e-05 | 0.4426 |
| MODE_D_vs_MODE_F | 0.0000 | 0.0000 | 0 | 0 | 100 | 1 | 1 | 0.0000 |

## Confidence intervals

- **MODE_A_vs_MODE_D**: mean difference 95% bootstrap CI = [0.1800, 0.4700]
- **MODE_A_vs_MODE_F**: mean difference 95% bootstrap CI = [0.1800, 0.4700]
- **MODE_D_vs_MODE_F**: mean difference 95% bootstrap CI = [0.0000, 0.0000]

## Interpretation

The analysis treats task identity as paired across modes. Success rate is not the discriminating metric because all three authoritative experiments achieved 100/100 final successful repairs. Repair attempts are therefore analyzed as an efficiency measure.

Statistical significance must not be interpreted as proof that a particular internal mechanism caused the observed difference. The experimental configuration and mechanism evidence must also be considered.
