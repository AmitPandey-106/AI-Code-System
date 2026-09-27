import os
import csv
import math
import statistics

try:
    from scipy.stats import (
        binomtest,
        wilcoxon,
    )
except ImportError:
    raise SystemExit(
        "scipy is required. Install it with: pip install scipy"
    )

BASE = os.getcwd()

INPUT = os.path.join(
    BASE,
    "experiments",
    "FINAL_LITE_CODER_EVIDENCE",
    "task_level_comparison.csv"
)

OUTPUT = os.path.join(
    BASE,
    "experiments",
    "FINAL_LITE_CODER_EVIDENCE",
    "statistical_analysis.md"
)

rows = []

with open(INPUT, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        rows.append({
            "task_id": row["task_id"],
            "A": float(row["MODE_A_attempts"]),
            "D": float(row["MODE_D_attempts"]),
            "F": float(row["MODE_F_attempts"]),
        })


def analyze(left_name, right_name):

    differences = [
        r[left_name] - r[right_name]
        for r in rows
    ]

    positive = sum(d > 0 for d in differences)
    negative = sum(d < 0 for d in differences)
    zero = sum(d == 0 for d in differences)

    nonzero = [
        d for d in differences
        if d != 0
    ]

    mean_diff = statistics.mean(differences)
    median_diff = statistics.median(differences)

    # Exact two-sided sign test
    if positive + negative > 0:

        smaller = min(
            positive,
            negative
        )

        sign_p = min(
            1.0,
            2.0 * binomtest(
                smaller,
                positive + negative,
                0.5
            ).pvalue
        )

    else:
        sign_p = 1.0

    # Wilcoxon signed-rank
    if nonzero:

        try:
            wilcoxon_result = wilcoxon(
                differences,
                alternative="two-sided",
                zero_method="wilcox",
                method="auto"
            )

            wilcoxon_stat = float(
                wilcoxon_result.statistic
            )

            wilcoxon_p = float(
                wilcoxon_result.pvalue
            )

        except Exception as e:

            wilcoxon_stat = None
            wilcoxon_p = None

            print(
                f"Wilcoxon warning for "
                f"{left_name} vs {right_name}: {e}"
            )

    else:

        wilcoxon_stat = 0.0
        wilcoxon_p = 1.0

    # Paired standardized effect size:
    # mean difference / SD of paired differences
    if len(differences) > 1:

        sd = statistics.stdev(
            differences
        )

        if sd != 0:
            effect_size = mean_diff / sd
        else:
            effect_size = 0.0

    else:
        effect_size = 0.0

    # Bootstrap 95% CI for mean paired difference
    # Deterministic seed
    import random

    rng = random.Random(42)

    bootstrap_means = []

    for _ in range(10000):

        sample = [
            rng.choice(differences)
            for _ in differences
        ]

        bootstrap_means.append(
            statistics.mean(sample)
        )

    bootstrap_means.sort()

    lower = bootstrap_means[
        int(0.025 * len(bootstrap_means))
    ]

    upper = bootstrap_means[
        int(0.975 * len(bootstrap_means))
    ]

    return {
        "n": len(differences),
        "mean_difference": mean_diff,
        "median_difference": median_diff,
        "positive": positive,
        "negative": negative,
        "zero": zero,
        "sign_test_p": sign_p,
        "wilcoxon_statistic": wilcoxon_stat,
        "wilcoxon_p": wilcoxon_p,
        "effect_size": effect_size,
        "bootstrap_ci_lower": lower,
        "bootstrap_ci_upper": upper,
    }


comparisons = {
    "MODE_A_vs_MODE_D": analyze("A", "D"),
    "MODE_A_vs_MODE_F": analyze("A", "F"),
    "MODE_D_vs_MODE_F": analyze("D", "F"),
}


print("=" * 80)
print("LITE-CODER STATISTICAL ANALYSIS")
print("=" * 80)

for name, result in comparisons.items():

    print("\n" + name)
    print("-" * 60)

    for key, value in result.items():
        print(f"{key}: {value}")


# Bonferroni correction for three pairwise comparisons
alpha = 0.05
corrected_alpha = alpha / 3

print("\n" + "=" * 80)
print("MULTIPLE-COMPARISON THRESHOLD")
print("=" * 80)

print("Original alpha:", alpha)
print("Bonferroni alpha:", corrected_alpha)


with open(OUTPUT, "w", encoding="utf-8") as f:

    f.write("# LITE-CODER Statistical Analysis\n\n")

    f.write(
        "Paired task-level analysis of repair attempts "
        "across the authoritative 100-task experiments.\n\n"
    )

    f.write(
        "## Statistical methods\n\n"
    )

    f.write(
        "- Exact two-sided sign test\n"
        "- Wilcoxon signed-rank test\n"
        "- Paired standardized effect size\n"
        "- Deterministic bootstrap 95% CI for mean paired difference\n"
        "- Bonferroni correction for three pairwise comparisons\n\n"
    )

    f.write(
        "| Comparison | Mean Diff | Median Diff | "
        "Improved | Worse | Equal | "
        "Sign p | Wilcoxon p | Effect |\n"
    )

    f.write(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )

    for name, r in comparisons.items():

        f.write(
            f"| {name} | "
            f"{r['mean_difference']:.4f} | "
            f"{r['median_difference']:.4f} | "
            f"{r['positive']} | "
            f"{r['negative']} | "
            f"{r['zero']} | "
            f"{r['sign_test_p']:.8g} | "
            f"{r['wilcoxon_p']:.8g} | "
            f"{r['effect_size']:.4f} |\n"
        )

    f.write("\n## Confidence intervals\n\n")

    for name, r in comparisons.items():

        f.write(
            f"- **{name}**: "
            f"mean difference 95% bootstrap CI = "
            f"[{r['bootstrap_ci_lower']:.4f}, "
            f"{r['bootstrap_ci_upper']:.4f}]\n"
        )

    f.write("\n## Interpretation\n\n")

    f.write(
        "The analysis treats task identity as paired across modes. "
        "Success rate is not the discriminating metric because all "
        "three authoritative experiments achieved 100/100 final "
        "successful repairs. Repair attempts are therefore analyzed "
        "as an efficiency measure.\n\n"
    )

    f.write(
        "Statistical significance must not be interpreted as proof "
        "that a particular internal mechanism caused the observed "
        "difference. The experimental configuration and mechanism "
        "evidence must also be considered.\n"
    )

print("\n")
print("=" * 80)
print("STATISTICAL ANALYSIS COMPLETE")
print("=" * 80)
print("Created:")
print(OUTPUT)