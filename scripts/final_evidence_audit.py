import os
import json
import hashlib
import csv
import statistics
from collections import Counter, defaultdict
from datetime import datetime

BASE = os.getcwd()

EXPERIMENTS = {
    "MODE_A_BASELINE": "experiments/LITE_CODER_100TASK_MODE_A_BASELINE",
    "MODE_A_CLEAN_V1": "experiments/LITE_CODER_100TASK_MODE_A_CLEAN_V1",
    "MODE_D": "experiments/LITE_CODER_100TASK_MODE_D",
    "MODE_F": "experiments/LITE_CODER_100TASK_MODE_F",
}

EVIDENCE_ROOT = os.path.join(
    BASE,
    "experiments",
    "FINAL_LITE_CODER_EVIDENCE"
)

os.makedirs(EVIDENCE_ROOT, exist_ok=True)
os.makedirs(os.path.join(EVIDENCE_ROOT, "tables"), exist_ok=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_records(root):
    raw = os.path.join(root, "raw_tasks")

    if not os.path.isdir(raw):
        return []

    records = []

    for filename in sorted(os.listdir(raw)):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(raw, filename)

        try:
            data = load_json(path)
            records.append(data)
        except Exception as e:
            print(f"WARNING: Could not load {path}: {e}")

    return records


def audit_experiment(label, root):

    print("\n" + "=" * 80)
    print(label)
    print(root)
    print("=" * 80)

    result = {
        "label": label,
        "path": root,
        "exists": os.path.isdir(root),
    }

    if not os.path.isdir(root):
        print("MISSING")
        result["audit_pass"] = False
        return result

    manifest_path = os.path.join(root, "experiment_manifest.json")

    manifest = {}
    if os.path.exists(manifest_path):
        try:
            manifest = load_json(manifest_path)
        except Exception as e:
            print("Manifest error:", e)

    records = load_records(root)

    task_ids = [r.get("task_id") for r in records]

    success_count = sum(
        r.get("success") is True
        for r in records
    )

    model_success_count = sum(
        r.get("status") == "model_success"
        for r in records
    )

    final_success_count = sum(
        (r.get("feedback_record") or {}).get("final_status") == "success"
        for r in records
    )

    execution_passed = sum(
        ((r.get("feedback_record") or {}).get("verification") or {})
            .get("execution_passed") is True
        for r in records
    )

    syntax_passed = sum(
        ((r.get("feedback_record") or {}).get("verification") or {})
            .get("syntax_passed") is True
        for r in records
    )

    tests_passed = sum(
        ((r.get("feedback_record") or {}).get("verification") or {})
            .get("tests_passed") is True
        for r in records
    )

    safety_passed = sum(
        ((r.get("feedback_record") or {}).get("verification") or {})
            .get("safety_passed") is True
        for r in records
    )

    attempts = [
        r.get("attempts_used")
        for r in records
        if isinstance(r.get("attempts_used"), int)
    ]

    repair_effort = [
        r.get("repair_effort")
        for r in records
        if isinstance(r.get("repair_effort"), (int, float))
    ]

    attempt_distribution = dict(
        sorted(Counter(attempts).items())
    )

    none_type_errors = []

    for r in records:
        text = json.dumps(r)

        if "argument of type 'NoneType' is not iterable" in text:
            none_type_errors.append(r.get("task_id"))

    strategy_counts = Counter()

    for r in records:
        for item in r.get("strategy_history", []):
            strategy = item.get("selected_strategy")

            if strategy:
                strategy_counts[strategy] += 1

    state_root = os.path.join(root, "state_snapshot")

    state_files = {}

    for filename in [
        "repair_memory.json",
        "repair_memory_index.faiss",
        "strategy_stats.json",
    ]:
        path = os.path.join(state_root, filename)

        state_files[filename] = {
            "present": os.path.exists(path),
            "size_bytes": os.path.getsize(path) if os.path.exists(path) else 0,
            "sha256": sha256_file(path) if os.path.exists(path) else None,
        }

    adapter_files = []

    for current_root, dirs, files in os.walk(root):

        for filename in files:

            lower = filename.lower()

            keywords = [
                "adapter",
                "lora",
                "trainer",
                "training",
                "peft",
            ]

            if any(k in lower for k in keywords):

                adapter_files.append(
                    os.path.relpath(
                        os.path.join(current_root, filename),
                        root
                    )
                )

    result.update({
        "manifest": manifest,
        "task_count": len(records),
        "unique_task_ids": len(set(task_ids)),
        "missing_task_ids": task_ids.count(None),
        "duplicate_task_ids": len(task_ids) - len(set(task_ids)),
        "success_count": success_count,
        "model_success_count": model_success_count,
        "final_success_count": final_success_count,
        "execution_passed": execution_passed,
        "syntax_passed": syntax_passed,
        "tests_passed": tests_passed,
        "safety_passed": safety_passed,
        "attempt_distribution": attempt_distribution,
        "average_attempts": (
            statistics.mean(attempts)
            if attempts else None
        ),
        "median_attempts": (
            statistics.median(attempts)
            if attempts else None
        ),
        "min_attempts": min(attempts) if attempts else None,
        "max_attempts": max(attempts) if attempts else None,
        "average_repair_effort": (
            statistics.mean(repair_effort)
            if repair_effort else None
        ),
        "median_repair_effort": (
            statistics.median(repair_effort)
            if repair_effort else None
        ),
        "strategy_counts": dict(strategy_counts),
        "none_type_bookkeeping_errors": none_type_errors,
        "state_files": state_files,
        "adapter_training_artifacts": adapter_files,
    })

    result["audit_pass"] = (
        len(records) == 100
        and len(set(task_ids)) == 100
        and success_count == 100
        and model_success_count == 100
        and final_success_count == 100
        and execution_passed == 100
        and syntax_passed == 100
        and tests_passed == 100
        and safety_passed == 100
        and len(none_type_errors) == 0
    )

    print("Tasks:", len(records))
    print("Unique IDs:", len(set(task_ids)))
    print("Success:", success_count)
    print("Model success:", model_success_count)
    print("Final success:", final_success_count)
    print("Execution passed:", execution_passed)
    print("Syntax passed:", syntax_passed)
    print("Tests passed:", tests_passed)
    print("Safety passed:", safety_passed)

    print("Average attempts:", result["average_attempts"])
    print("Median attempts:", result["median_attempts"])
    print("Attempt distribution:", attempt_distribution)

    print("NoneType bookkeeping errors:", len(none_type_errors))

    print("LoRA/training artifact matches:", len(adapter_files))

    print(
        "AUDIT:",
        "PASS" if result["audit_pass"] else "FAIL"
    )

    return result


all_results = {}

for label, relative_root in EXPERIMENTS.items():

    root = os.path.join(BASE, relative_root)

    all_results[label] = audit_experiment(
        label,
        root
    )


# ------------------------------------------------------------------
# Save machine-readable audit
# ------------------------------------------------------------------

audit_json = os.path.join(
    EVIDENCE_ROOT,
    "benchmark_integrity.json"
)

with open(audit_json, "w", encoding="utf-8") as f:
    json.dump(
        all_results,
        f,
        indent=2
    )


# ------------------------------------------------------------------
# Determine MODE-A candidates
# ------------------------------------------------------------------

mode_a_candidates = {
    label: result
    for label, result in all_results.items()
    if label.startswith("MODE_A")
}


# ------------------------------------------------------------------
# Comparison table
# ------------------------------------------------------------------

comparison_rows = []

for label, result in all_results.items():

    comparison_rows.append({
        "mode": label,
        "tasks": result.get("task_count"),
        "successes": result.get("success_count"),
        "success_rate": (
            result.get("success_count", 0) / 100
            if result.get("task_count") == 100
            else None
        ),
        "avg_attempts": result.get("average_attempts"),
        "median_attempts": result.get("median_attempts"),
        "min_attempts": result.get("min_attempts"),
        "max_attempts": result.get("max_attempts"),
        "execution_passed": result.get("execution_passed"),
        "syntax_passed": result.get("syntax_passed"),
        "tests_passed": result.get("tests_passed"),
        "safety_passed": result.get("safety_passed"),
        "none_type_errors": len(
            result.get("none_type_bookkeeping_errors", [])
        ),
        "audit_pass": result.get("audit_pass"),
    })


csv_path = os.path.join(
    EVIDENCE_ROOT,
    "tables",
    "benchmark_comparison.csv"
)

with open(csv_path, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=comparison_rows[0].keys()
    )

    writer.writeheader()
    writer.writerows(comparison_rows)


# ------------------------------------------------------------------
# Hash important artifacts
# ------------------------------------------------------------------

hash_rows = []

for label, relative_root in EXPERIMENTS.items():

    root = os.path.join(BASE, relative_root)

    for filename in [
        "checkpoint.json",
        "experiment_manifest.json",
        "feedback.json",
        "metrics.json",
    ]:

        path = os.path.join(root, filename)

        if os.path.exists(path):

            hash_rows.append({
                "experiment": label,
                "file": os.path.relpath(path, BASE),
                "sha256": sha256_file(path),
                "size_bytes": os.path.getsize(path),
            })


hash_path = os.path.join(
    EVIDENCE_ROOT,
    "experiment_hashes.csv"
)

with open(hash_path, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "experiment",
            "file",
            "sha256",
            "size_bytes",
        ]
    )

    writer.writeheader()
    writer.writerows(hash_rows)


# ------------------------------------------------------------------
# Human-readable report
# ------------------------------------------------------------------

report_path = os.path.join(
    EVIDENCE_ROOT,
    "FINAL_EVIDENCE_REPORT.md"
)

with open(report_path, "w", encoding="utf-8") as f:

    f.write("# LITE-CODER Final Experimental Evidence Audit\n\n")

    f.write(
        f"Generated: {datetime.now().isoformat()}\n\n"
    )

    f.write(
        "This report is generated from existing experiment artifacts. "
        "The experiment directories are read-only inputs to this audit.\n\n"
    )

    f.write("## Experiment Summary\n\n")

    f.write(
        "| Experiment | Tasks | Success | Avg Attempts | "
        "Median | Tests Passed | Audit |\n"
    )

    f.write(
        "|---|---:|---:|---:|---:|---:|---|\n"
    )

    for row in comparison_rows:

        f.write(
            f"| {row['mode']} "
            f"| {row['tasks']} "
            f"| {row['successes']} "
            f"| {row['avg_attempts']} "
            f"| {row['median_attempts']} "
            f"| {row['tests_passed']} "
            f"| {'PASS' if row['audit_pass'] else 'FAIL'} |\n"
        )

    f.write("\n## MODE-A Candidate Comparison\n\n")

    for label, result in mode_a_candidates.items():

        f.write(f"### {label}\n\n")

        f.write(
            f"- Tasks: {result.get('task_count')}\n"
        )

        f.write(
            f"- Successes: {result.get('success_count')}\n"
        )

        f.write(
            f"- Average attempts: "
            f"{result.get('average_attempts')}\n"
        )

        f.write(
            f"- Median attempts: "
            f"{result.get('median_attempts')}\n"
        )

        f.write(
            f"- Attempt distribution: "
            f"{result.get('attempt_distribution')}\n"
        )

        f.write(
            f"- NoneType bookkeeping errors: "
            f"{len(result.get('none_type_bookkeeping_errors', []))}\n"
        )

    f.write("\n## MODE-F LoRA Evidence\n\n")

    mode_f = all_results.get("MODE_F", {})

    f.write(
        f"- LoRA/training artifact matches found: "
        f"{len(mode_f.get('adapter_training_artifacts', []))}\n"
    )

    f.write(
        "- The presence of `lora_enabled=true` in a manifest is "
        "configuration evidence, not proof of successful adapter training.\n"
    )

    f.write(
        "- Any LoRA training failure observed in the original run "
        "should remain documented separately from repair success.\n"
    )

    f.write("\n## State Artifacts\n\n")

    for label, result in all_results.items():

        f.write(f"### {label}\n\n")

        for filename, state in result.get(
            "state_files", {}
        ).items():

            f.write(
                f"- `{filename}`: "
                f"{'PRESENT' if state['present'] else 'ABSENT'}"
                f", size={state['size_bytes']} bytes\n"
            )

    f.write("\n## Integrity Notes\n\n")

    f.write(
        "- Benchmark experiment directories were not modified by this audit.\n"
    )

    f.write(
        "- No benchmark was executed by this audit.\n"
    )

    f.write(
        "- MODE-A artifacts are kept as separate candidates until "
        "their provenance is reviewed.\n"
    )

print("\n")
print("=" * 80)
print("FINAL EVIDENCE AUDIT COMPLETE")
print("=" * 80)

print("\nEvidence directory:")
print(EVIDENCE_ROOT)

print("\nCreated:")
print("  benchmark_integrity.json")
print("  experiment_hashes.csv")
print("  tables/benchmark_comparison.csv")
print("  FINAL_EVIDENCE_REPORT.md")

print("\nIMPORTANT:")
print("No benchmark was executed.")
print("Existing experiment directories were only read.")
print("=" * 80)