import os
import json
import csv
import statistics
from collections import Counter

BASE = os.getcwd()

EXPERIMENTS = {
    "MODE_A": "experiments/LITE_CODER_100TASK_MODE_A_BASELINE",
    "MODE_D": "experiments/LITE_CODER_100TASK_MODE_D",
    "MODE_F": "experiments/LITE_CODER_100TASK_MODE_F",
}

OUTPUT = "experiments/FINAL_LITE_CODER_EVIDENCE"

os.makedirs(OUTPUT, exist_ok=True)


def load_records(root):
    raw = os.path.join(BASE, root, "raw_tasks")

    records = {}

    for filename in os.listdir(raw):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(raw, filename)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        task_id = data.get("task_id")

        if task_id:
            records[task_id] = data

    return records


all_data = {
    mode: load_records(path)
    for mode, path in EXPERIMENTS.items()
}


print("=" * 80)
print("LITE-CODER TASK-LEVEL COMPARISON")
print("=" * 80)

for mode, data in all_data.items():
    print(f"{mode}: {len(data)} tasks")


# ---------------------------------------------------------
# Common task set
# ---------------------------------------------------------

common_ids = (
    set(all_data["MODE_A"])
    & set(all_data["MODE_D"])
    & set(all_data["MODE_F"])
)

print("\nCommon tasks:", len(common_ids))

if len(common_ids) != 100:
    print("WARNING: Expected 100 common tasks.")


# ---------------------------------------------------------
# Extract attempts
# ---------------------------------------------------------

rows = []

for task_id in sorted(common_ids):

    row = {"task_id": task_id}

    for mode in ["MODE_A", "MODE_D", "MODE_F"]:

        record = all_data[mode][task_id]

        attempts = record.get("attempts_used")

        if not isinstance(attempts, int):
            attempts = None

        row[f"{mode}_attempts"] = attempts

        row[f"{mode}_success"] = (
            record.get("success") is True
        )

        row[f"{mode}_final_status"] = (
            (record.get("feedback_record") or {})
            .get("final_status")
        )

    if all(
        row[f"{m}_attempts"] is not None
        for m in ["MODE_A", "MODE_D", "MODE_F"]
    ):

        row["A_minus_D"] = (
            row["MODE_A_attempts"]
            - row["MODE_D_attempts"]
        )

        row["A_minus_F"] = (
            row["MODE_A_attempts"]
            - row["MODE_F_attempts"]
        )

        row["D_minus_F"] = (
            row["MODE_D_attempts"]
            - row["MODE_F_attempts"]
        )

    rows.append(row)


# ---------------------------------------------------------
# Pairwise analysis
# ---------------------------------------------------------

def analyze_pair(rows, left, right):

    differences = [
        r[f"{left}_attempts"] - r[f"{right}_attempts"]
        for r in rows
        if (
            r[f"{left}_attempts"] is not None
            and r[f"{right}_attempts"] is not None
        )
    ]

    improved = sum(d > 0 for d in differences)
    worse = sum(d < 0 for d in differences)
    equal = sum(d == 0 for d in differences)

    return {
        "n": len(differences),
        "mean_left": statistics.mean(
            r[f"{left}_attempts"] for r in rows
        ),
        "mean_right": statistics.mean(
            r[f"{right}_attempts"] for r in rows
        ),
        "mean_difference": statistics.mean(differences),
        "median_difference": statistics.median(differences),
        "improved": improved,
        "worse": worse,
        "equal": equal,
        "difference_distribution": dict(
            sorted(Counter(differences).items())
        ),
    }


pairs = {
    "MODE_A_vs_MODE_D": analyze_pair(
        rows, "MODE_A", "MODE_D"
    ),
    "MODE_A_vs_MODE_F": analyze_pair(
        rows, "MODE_A", "MODE_F"
    ),
    "MODE_D_vs_MODE_F": analyze_pair(
        rows, "MODE_D", "MODE_F"
    ),
}


# ---------------------------------------------------------
# Print results
# ---------------------------------------------------------

print("\n" + "=" * 80)
print("PAIRWISE ATTEMPT ANALYSIS")
print("=" * 80)

for name, result in pairs.items():

    print("\n", name)

    print("N:", result["n"])
    print(
        "Mean attempts:",
        round(result["mean_left"], 4),
        "vs",
        round(result["mean_right"], 4)
    )

    print(
        "Mean difference:",
        round(result["mean_difference"], 4)
    )

    print(
        "Median difference:",
        result["median_difference"]
    )

    print("Tasks improved:", result["improved"])
    print("Tasks worse:", result["worse"])
    print("Tasks equal:", result["equal"])

    print(
        "Difference distribution:",
        result["difference_distribution"]
    )


# ---------------------------------------------------------
# Exact task-level improvement table
# ---------------------------------------------------------

improvement_path = os.path.join(
    OUTPUT,
    "task_level_comparison.csv"
)

with open(
    improvement_path,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    fieldnames = [
        "task_id",
        "MODE_A_attempts",
        "MODE_D_attempts",
        "MODE_F_attempts",
        "MODE_A_success",
        "MODE_D_success",
        "MODE_F_success",
        "A_minus_D",
        "A_minus_F",
        "D_minus_F",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for row in rows:

        writer.writerow({
            k: row.get(k)
            for k in fieldnames
        })


# ---------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------

report = os.path.join(
    OUTPUT,
    "TASK_LEVEL_ANALYSIS.md"
)

with open(report, "w", encoding="utf-8") as f:

    f.write("# LITE-CODER Task-Level Analysis\n\n")

    f.write(
        f"Common tasks analyzed: {len(rows)}\n\n"
    )

    f.write(
        "| Comparison | Mean Difference | "
        "Improved | Worse | Equal |\n"
    )

    f.write(
        "|---|---:|---:|---:|---:|\n"
    )

    for name, result in pairs.items():

        f.write(
            f"| {name} | "
            f"{result['mean_difference']:.4f} | "
            f"{result['improved']} | "
            f"{result['worse']} | "
            f"{result['equal']} |\n"
        )

    f.write("\n## Important Interpretation\n\n")

    f.write(
        "- Success rate alone cannot distinguish the three modes "
        "because all three completed all 100 tasks successfully.\n"
    )

    f.write(
        "- Attempt count is therefore analyzed as an efficiency "
        "measure.\n"
    )

    f.write(
        "- MODE-D and MODE-F must not be described as different "
        "in efficiency unless task-level evidence demonstrates "
        "a difference.\n"
    )

print("\n" + "=" * 80)
print("TASK-LEVEL ANALYSIS COMPLETE")
print("=" * 80)

print("\nCreated:")
print(improvement_path)
print(report)