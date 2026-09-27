#!/usr/bin/env python3
"""
research/audit/forensic_audit.py
==================================
LITE-CODER Forensic Audit Script

Usage:
    python research/audit/forensic_audit.py <experiment_dir> [--dataset <path>] [--out <output_dir>]

Produces:
    audit_report.json     — Machine-readable JSON audit
    audit_report.csv      — Machine-readable CSV per-task summary
    audit_report.md       — Human-readable Markdown report

Outcome classifications:
    MODEL_SUCCESS         – generated_code present, success=True, verification passed
    MODEL_FAILURE         – generated_code present (or max retries), success=False
    INFRASTRUCTURE_FAILURE– exception in runner (error_category="runner")
    UNRESOLVED            – success=null, no diagnostic available
    VERIFICATION_FAILURE  – execution passed but tests/verification failed
    INVALID_TASK          – task record missing required identity fields
"""

import os
import sys
import json
import csv
import hashlib
import argparse
import traceback
from datetime import datetime
from collections import defaultdict
from typing import Optional

# Outcome labels
OUTCOME_MODEL_SUCCESS         = "MODEL_SUCCESS"
OUTCOME_MODEL_FAILURE         = "MODEL_FAILURE"
OUTCOME_INFRA_FAILURE         = "INFRASTRUCTURE_FAILURE"
OUTCOME_UNRESOLVED            = "UNRESOLVED"
OUTCOME_VERIFICATION_FAILURE  = "VERIFICATION_FAILURE"
OUTCOME_INVALID_TASK          = "INVALID_TASK"
OUTCOME_EXECUTION_FAILURE     = "EXECUTION_FAILURE"


def sha256_of_file(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def classify_raw_task(raw: dict) -> str:
    """Classify the outcome of a single raw task record."""
    task_id = raw.get("task_id")
    if not task_id:
        return OUTCOME_INVALID_TASK

    success = raw.get("success")
    error_category = raw.get("error_category") or (raw.get("error_diagnostic") or {}).get("error_category")
    generated_code = raw.get("generated_code")
    feedback = raw.get("feedback_record") or {}
    verification = raw.get("verification") or feedback.get("verification") or {}

    # Infrastructure failure: runner exception captured
    if error_category == "runner" or raw.get("traceback"):
        return OUTCOME_INFRA_FAILURE

    # Check status field first (new schema)
    status = raw.get("status")
    if status == "infrastructure_failure":
        return OUTCOME_INFRA_FAILURE
    if status == "model_success":
        return OUTCOME_MODEL_SUCCESS
    if status == "model_failure":
        return OUTCOME_MODEL_FAILURE

    # Legacy records without status field
    if success is True:
        return OUTCOME_MODEL_SUCCESS
    if success is False:
        # Did the model generate code?
        if generated_code or feedback.get("initial_code"):
            # Did execution pass but tests fail?
            if verification.get("execution_passed") and not verification.get("tests_passed"):
                return OUTCOME_VERIFICATION_FAILURE
            return OUTCOME_MODEL_FAILURE
        # No code generated at all — could be infra
        return OUTCOME_UNRESOLVED
    if success is None:
        # The critical legacy case from the backup
        error_type = raw.get("error_type")
        if error_type and not generated_code:
            # Exception before/during generation — infrastructure
            return OUTCOME_INFRA_FAILURE
        return OUTCOME_UNRESOLVED

    return OUTCOME_UNRESOLVED


def audit_dataset(dataset_path: Optional[str]) -> dict:
    result = {
        "dataset_path": dataset_path,
        "exists": False,
        "task_count": 0,
        "sha256": "",
        "duplicate_ids": [],
        "issues": []
    }
    if not dataset_path or not os.path.exists(dataset_path):
        result["issues"].append("Dataset file not found")
        return result

    result["exists"] = True
    result["sha256"] = sha256_of_file(dataset_path)

    try:
        with open(dataset_path, "r") as f:
            data = json.load(f)
        result["task_count"] = len(data)

        ids = [t.get("task_id") for t in data]
        seen = set()
        dups = []
        for tid in ids:
            if tid in seen:
                dups.append(tid)
            seen.add(tid)
        result["duplicate_ids"] = dups
        if dups:
            result["issues"].append(f"Duplicate task IDs: {dups}")
    except Exception as e:
        result["issues"].append(f"Failed to parse dataset: {e}")

    return result


def audit_manifest(experiment_dir: str) -> dict:
    path = os.path.join(experiment_dir, "experiment_manifest.json")
    result = {
        "manifest_path": path,
        "exists": os.path.exists(path),
        "experiment_id": None,
        "mode": None,
        "model": None,
        "seed": None,
        "deterministic": None,
        "benchmark_size": None,
        "dataset_sha256": None,
        "lora_enabled": None,
        "memory_enabled": None,
        "strategy_learning_enabled": None,
        "issues": []
    }
    if not result["exists"]:
        result["issues"].append("Manifest file missing")
        return result

    try:
        with open(path, "r") as f:
            m = json.load(f)
        result["experiment_id"] = m.get("experiment_id")
        result["mode"] = m.get("mode")
        result["model"] = m.get("model_name")
        result["seed"] = m.get("benchmark_seed")
        result["deterministic"] = m.get("deterministic_generation")
        result["benchmark_size"] = m.get("benchmark_size") or m.get("task_count")
        result["dataset_sha256"] = m.get("dataset_sha256")
        result["lora_enabled"] = m.get("lora_enabled")
        result["memory_enabled"] = m.get("memory_enabled")
        result["strategy_learning_enabled"] = m.get("strategy_learning_enabled")
    except Exception as e:
        result["issues"].append(f"Failed to parse manifest: {e}")

    return result


def audit_checkpoint(experiment_dir: str) -> dict:
    path = os.path.join(experiment_dir, "checkpoint.json")
    result = {
        "checkpoint_path": path,
        "exists": os.path.exists(path),
        "total_records": 0,
        "unique_task_ids": 0,
        "duplicate_task_ids": [],
        "success_true": 0,
        "success_false": 0,
        "success_null": 0,
        "error_categories": defaultdict(int),
        "error_types": defaultdict(int),
        "status_counts": defaultdict(int),
        "missing_fields": [],
        "issues": []
    }
    if not result["exists"]:
        result["issues"].append("Checkpoint file missing")
        return result

    try:
        with open(path, "r") as f:
            records = json.load(f)

        result["total_records"] = len(records)
        seen_ids = set()
        dups = []

        REQUIRED_FIELDS = ["task_id", "mode", "success", "execution_time_ms", "timestamp"]

        for r in records:
            tid = r.get("task_id")
            if tid in seen_ids:
                dups.append(tid)
            seen_ids.add(tid)

            s = r.get("success")
            if s is True:
                result["success_true"] += 1
            elif s is False:
                result["success_false"] += 1
            else:
                result["success_null"] += 1

            ec = r.get("error_category") or "none"
            result["error_categories"][ec] += 1

            et = r.get("error_type") or "none"
            result["error_types"][et] += 1

            st = r.get("status") or "unspecified"
            result["status_counts"][st] += 1

            for field in REQUIRED_FIELDS:
                if field not in r:
                    result["missing_fields"].append(f"{tid}:{field}")

        result["unique_task_ids"] = len(seen_ids)
        result["duplicate_task_ids"] = dups
        if dups:
            result["issues"].append(f"Duplicate task IDs in checkpoint: {dups}")

        # Convert defaultdicts to regular dicts for JSON serialization
        result["error_categories"] = dict(result["error_categories"])
        result["error_types"] = dict(result["error_types"])
        result["status_counts"] = dict(result["status_counts"])

    except Exception as e:
        result["issues"].append(f"Failed to parse checkpoint: {e}")
        result["error_categories"] = {}
        result["error_types"] = {}
        result["status_counts"] = {}

    return result


def audit_raw_tasks(experiment_dir: str) -> dict:
    raw_dir = os.path.join(experiment_dir, "raw_tasks")
    result = {
        "raw_tasks_dir": raw_dir,
        "exists": os.path.exists(raw_dir),
        "total_files": 0,
        "outcomes": defaultdict(int),
        "has_generated_code": 0,
        "has_attempts": 0,
        "has_execution": 0,
        "has_tests": 0,
        "has_verification": 0,
        "has_traceback": 0,
        "has_error_diagnostic": 0,
        "missing_task_ids": [],
        "per_task": [],
        "issues": []
    }
    if not result["exists"]:
        result["issues"].append("raw_tasks directory missing")
        return result

    files = [f for f in os.listdir(raw_dir) if f.endswith(".json")]
    result["total_files"] = len(files)

    for fname in sorted(files):
        fpath = os.path.join(raw_dir, fname)
        try:
            with open(fpath, "r") as f:
                raw = json.load(f)

            outcome = classify_raw_task(raw)
            result["outcomes"][outcome] += 1

            has_code = bool(raw.get("generated_code") or (raw.get("feedback_record") or {}).get("final_code"))
            has_attempts = raw.get("attempts_used") is not None or bool((raw.get("feedback_record") or {}).get("attempts"))
            has_exec = raw.get("execution") is not None
            has_tests = raw.get("tests") is not None
            has_verif = raw.get("verification") is not None
            has_tb = bool(raw.get("traceback") or (raw.get("error_diagnostic") or {}).get("traceback"))
            has_diag = raw.get("error_diagnostic") is not None

            if has_code: result["has_generated_code"] += 1
            if has_attempts: result["has_attempts"] += 1
            if has_exec: result["has_execution"] += 1
            if has_tests: result["has_tests"] += 1
            if has_verif: result["has_verification"] += 1
            if has_tb: result["has_traceback"] += 1
            if has_diag: result["has_error_diagnostic"] += 1

            result["per_task"].append({
                "task_id": raw.get("task_id", fname),
                "task_index": raw.get("task_index"),
                "outcome": outcome,
                "success": raw.get("success"),
                "status": raw.get("status"),
                "error_type": raw.get("error_type"),
                "error_message": raw.get("error_message"),
                "error_stage": raw.get("error_stage"),
                "has_generated_code": has_code,
                "has_attempts": has_attempts,
                "has_execution": has_exec,
                "has_tests": has_tests,
                "has_verification": has_verif,
                "has_traceback": has_tb,
                "runtime_ms": raw.get("runtime_ms") or (raw.get("timing") or {}).get("total_ms"),
                "timestamp": raw.get("timestamp")
            })

        except Exception as e:
            result["issues"].append(f"Failed to parse {fname}: {e}")

    result["outcomes"] = dict(result["outcomes"])
    return result


def audit_feedback(experiment_dir: str, successful_task_ids: set) -> dict:
    path = os.path.join(experiment_dir, "feedback.json")
    result = {
        "feedback_path": path,
        "exists": os.path.exists(path),
        "feedback_count": 0,
        "matched_to_successful": 0,
        "unmatched": [],
        "issues": []
    }
    if not result["exists"]:
        return result

    try:
        with open(path, "r") as f:
            records = json.load(f)
        result["feedback_count"] = len(records)
        matched = sum(1 for r in records if r.get("feedback_id") in successful_task_ids
                      or r.get("task") is not None)
        result["matched_to_successful"] = matched
    except Exception as e:
        result["issues"].append(f"Failed to parse feedback: {e}")

    return result


def compute_summary(checkpoint: dict, raw_tasks: dict, dataset: dict) -> dict:
    total = dataset.get("task_count", 0) or checkpoint.get("total_records", 0)
    outcomes = raw_tasks.get("outcomes", {})
    return {
        "total_tasks_in_dataset": total,
        "tasks_with_records": checkpoint.get("total_records", 0),
        "outcomes": outcomes,
        "success_true": checkpoint.get("success_true", 0),
        "success_false": checkpoint.get("success_false", 0),
        "success_null": checkpoint.get("success_null", 0),
        "infrastructure_failures": outcomes.get(OUTCOME_INFRA_FAILURE, 0),
        "unresolved": outcomes.get(OUTCOME_UNRESOLVED, 0),
        "model_successes": outcomes.get(OUTCOME_MODEL_SUCCESS, 0),
        "model_failures": outcomes.get(OUTCOME_MODEL_FAILURE, 0),
        "verification_failures": outcomes.get(OUTCOME_VERIFICATION_FAILURE, 0),
        "is_complete": checkpoint.get("total_records", 0) == total and total > 0,
        "all_resolved": checkpoint.get("success_null", 0) == 0
    }


def generate_markdown_report(audit: dict) -> str:
    summary = audit["summary"]
    dataset = audit["dataset"]
    manifest = audit["manifest"]
    checkpoint = audit["checkpoint"]
    raw_tasks = audit["raw_tasks"]
    feedback = audit["feedback"]
    ts = audit["audit_timestamp"]

    lines = [
        f"# LITE-CODER Forensic Audit Report",
        f"",
        f"**Experiment:** `{manifest.get('experiment_id', 'unknown')}`  ",
        f"**Mode:** `{manifest.get('mode', 'unknown')}`  ",
        f"**Model:** `{manifest.get('model', 'unknown')}`  ",
        f"**Audit Generated:** {ts}  ",
        f"",
        f"---",
        f"",
        f"## 1. Dataset",
        f"",
        f"| Field | Value |",
        f"|---|---|",
        f"| Path | `{dataset.get('dataset_path', 'N/A')}` |",
        f"| Exists | {dataset.get('exists')} |",
        f"| Task Count | {dataset.get('task_count', 0)} |",
        f"| SHA256 | `{dataset.get('sha256', '')}` |",
        f"| Duplicate IDs | {dataset.get('duplicate_ids', [])} |",
    ]
    if dataset.get("issues"):
        lines += [f"", f"**Issues:** {'; '.join(dataset['issues'])}"]

    lines += [
        f"",
        f"---",
        f"",
        f"## 2. Experiment Manifest",
        f"",
        f"| Field | Value |",
        f"|---|---|",
        f"| Experiment ID | `{manifest.get('experiment_id')}` |",
        f"| Mode | `{manifest.get('mode')}` |",
        f"| Model | `{manifest.get('model')}` |",
        f"| Seed | `{manifest.get('seed')}` |",
        f"| Deterministic | `{manifest.get('deterministic')}` |",
        f"| Benchmark Size | `{manifest.get('benchmark_size')}` |",
        f"| Dataset SHA256 | `{manifest.get('dataset_sha256')}` |",
        f"| Memory Enabled | `{manifest.get('memory_enabled')}` |",
        f"| Strategy Learning | `{manifest.get('strategy_learning_enabled')}` |",
        f"| LoRA Enabled | `{manifest.get('lora_enabled')}` |",
    ]
    if manifest.get("issues"):
        lines += [f"", f"**Issues:** {'; '.join(manifest['issues'])}"]

    lines += [
        f"",
        f"---",
        f"",
        f"## 3. Checkpoint",
        f"",
        f"| Field | Count |",
        f"|---|---|",
        f"| Total Records | {checkpoint.get('total_records', 0)} |",
        f"| Unique Task IDs | {checkpoint.get('unique_task_ids', 0)} |",
        f"| success=True | {checkpoint.get('success_true', 0)} |",
        f"| success=False | {checkpoint.get('success_false', 0)} |",
        f"| success=null | {checkpoint.get('success_null', 0)} |",
    ]
    if checkpoint.get("status_counts"):
        lines += [f"", f"**Status Counts:**", f""]
        for st, cnt in checkpoint["status_counts"].items():
            lines.append(f"- `{st}`: {cnt}")
    if checkpoint.get("error_categories"):
        lines += [f"", f"**Error Categories:**", f""]
        for ec, cnt in checkpoint["error_categories"].items():
            lines.append(f"- `{ec}`: {cnt}")
    if checkpoint.get("error_types"):
        lines += [f"", f"**Error Types:**", f""]
        for et, cnt in checkpoint["error_types"].items():
            lines.append(f"- `{et}`: {cnt}")
    if checkpoint.get("issues"):
        lines += [f"", f"**Issues:** {'; '.join(checkpoint['issues'])}"]

    lines += [
        f"",
        f"---",
        f"",
        f"## 4. Raw Task Records",
        f"",
        f"| Field | Count |",
        f"|---|---|",
        f"| Total Files | {raw_tasks.get('total_files', 0)} |",
        f"| Has Generated Code | {raw_tasks.get('has_generated_code', 0)} |",
        f"| Has Attempts | {raw_tasks.get('has_attempts', 0)} |",
        f"| Has Execution | {raw_tasks.get('has_execution', 0)} |",
        f"| Has Tests | {raw_tasks.get('has_tests', 0)} |",
        f"| Has Verification | {raw_tasks.get('has_verification', 0)} |",
        f"| Has Traceback (infra errors) | {raw_tasks.get('has_traceback', 0)} |",
        f"| Has Error Diagnostic | {raw_tasks.get('has_error_diagnostic', 0)} |",
    ]

    outcomes = raw_tasks.get("outcomes", {})
    if outcomes:
        lines += [f"", f"**Outcome Breakdown:**", f""]
        for k, v in sorted(outcomes.items()):
            lines.append(f"- `{k}`: {v}")

    if raw_tasks.get("issues"):
        lines += [f"", f"**Issues:** {'; '.join(raw_tasks['issues'])}"]

    lines += [
        f"",
        f"---",
        f"",
        f"## 5. Feedback",
        f"",
        f"| Field | Value |",
        f"|---|---|",
        f"| Feedback File Exists | {feedback.get('exists')} |",
        f"| Feedback Count | {feedback.get('feedback_count', 0)} |",
    ]
    if feedback.get("issues"):
        lines += [f"", f"**Issues:** {'; '.join(feedback['issues'])}"]

    lines += [
        f"",
        f"---",
        f"",
        f"## 6. Summary",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Dataset Size | {summary.get('total_tasks_in_dataset', 0)} |",
        f"| Tasks Executed | {summary.get('tasks_with_records', 0)} |",
        f"| MODEL_SUCCESS | **{summary.get('model_successes', 0)}** |",
        f"| MODEL_FAILURE | {summary.get('model_failures', 0)} |",
        f"| INFRASTRUCTURE_FAILURE | {summary.get('infrastructure_failures', 0)} |",
        f"| VERIFICATION_FAILURE | {summary.get('verification_failures', 0)} |",
        f"| UNRESOLVED | {summary.get('unresolved', 0)} |",
        f"| Is Complete Run | {summary.get('is_complete')} |",
        f"| All Resolved | {summary.get('all_resolved')} |",
        f"",
        f"---",
        f"",
        f"## 7. Per-Task Detail",
        f"",
        f"| # | Task ID | Outcome | Success | Has Code | Has Exec | Has Tests | Error Type | Runtime (ms) |",
        f"|---|---|---|---|---|---|---|---|---|",
    ]

    for t in raw_tasks.get("per_task", []):
        lines.append(
            f"| {t.get('task_index', '-')} | `{t.get('task_id', '?')}` "
            f"| {t.get('outcome', '?')} "
            f"| {t.get('success')} "
            f"| {'✓' if t.get('has_generated_code') else '✗'} "
            f"| {'✓' if t.get('has_execution') else '✗'} "
            f"| {'✓' if t.get('has_tests') else '✗'} "
            f"| `{t.get('error_type') or '-'}` "
            f"| {t.get('runtime_ms', '-')} |"
        )

    return "\n".join(lines)


def run_audit(experiment_dir: str, dataset_path: Optional[str] = None, output_dir: Optional[str] = None) -> dict:
    if not os.path.isdir(experiment_dir):
        print(f"ERROR: Experiment directory not found: {experiment_dir}")
        sys.exit(1)

    output_dir = output_dir or experiment_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"LITE-CODER Forensic Audit")
    print(f"Experiment: {experiment_dir}")
    print(f"{'='*60}\n")

    # Try to find dataset path from manifest if not given
    if not dataset_path:
        manifest_path = os.path.join(experiment_dir, "experiment_manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    m = json.load(f)
                dataset_path = m.get("dataset_path")
            except Exception:
                pass

    dataset_audit    = audit_dataset(dataset_path)
    manifest_audit   = audit_manifest(experiment_dir)
    checkpoint_audit = audit_checkpoint(experiment_dir)
    raw_tasks_audit  = audit_raw_tasks(experiment_dir)
    feedback_audit   = audit_feedback(experiment_dir, set())
    summary          = compute_summary(checkpoint_audit, raw_tasks_audit, dataset_audit)

    audit = {
        "audit_timestamp": datetime.now().isoformat(),
        "experiment_dir": os.path.abspath(experiment_dir),
        "dataset": dataset_audit,
        "manifest": manifest_audit,
        "checkpoint": checkpoint_audit,
        "raw_tasks": raw_tasks_audit,
        "feedback": feedback_audit,
        "summary": summary
    }

    # ---- Write JSON report ----
    json_path = os.path.join(output_dir, "audit_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=4, default=str)
    print(f"[OK] JSON audit report: {json_path}")

    # ---- Write CSV report ----
    csv_path = os.path.join(output_dir, "audit_report.csv")
    per_task = raw_tasks_audit.get("per_task", [])
    if per_task:
        fieldnames = list(per_task[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(per_task)
        print(f"[OK] CSV audit report:  {csv_path}")

    # ---- Write Markdown report ----
    md_path = os.path.join(output_dir, "audit_report.md")
    md = generate_markdown_report(audit)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[OK] Markdown report:   {md_path}")

    # ---- Print summary ----
    print(f"\n{'='*60}")
    print(f"AUDIT SUMMARY")
    print(f"{'='*60}")
    print(f"  Dataset size      : {summary['total_tasks_in_dataset']}")
    print(f"  Executed records  : {summary['tasks_with_records']}")
    print(f"  MODEL_SUCCESS     : {summary['model_successes']}")
    print(f"  MODEL_FAILURE     : {summary['model_failures']}")
    print(f"  INFRA_FAILURE     : {summary['infrastructure_failures']}")
    print(f"  VERIFICATION_FAIL : {summary['verification_failures']}")
    print(f"  UNRESOLVED        : {summary['unresolved']}")
    print(f"  Is complete run   : {summary['is_complete']}")
    print(f"  All resolved      : {summary['all_resolved']}")
    print(f"{'='*60}\n")

    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LITE-CODER Forensic Audit Script")
    parser.add_argument("experiment_dir", help="Path to the experiment directory")
    parser.add_argument("--dataset", default=None, help="Path to dataset JSON (optional override)")
    parser.add_argument("--out", default=None, help="Output directory for reports (defaults to experiment_dir)")
    args = parser.parse_args()

    run_audit(args.experiment_dir, dataset_path=args.dataset, output_dir=args.out)
