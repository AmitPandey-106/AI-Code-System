"""Model-free Phase 8.2.1 staging/finalization. Never imports the experiment worker.

Use stage once, run deterministic tests separately, then finalize once. All output
artifacts are exclusive; original Phase 8.2 files are input-only.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

from phase8_2_1_controls import (TASK, REVISIONS, BOUND_SOURCES, canonical, exclusive, exclusive_json,
    file_sha, plan_digest, read_json, tree_hashes, verify_tree, verify_bound_evidence)

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "eval_results_phase8_2/20261025_131337_IST"
OLD_DIGEST = "cea4b5a9eaa7b0c763b934f0473ea019efed9d333eeac8f2b82e8adf06c98204"
EXECUTION_FILES = ("phase8_2_1_arm.py", "phase8_2_1_controls.py", "phase8_2_1_pytest.py")


def assert_preserved(output):
    initial = read_json(output / "starting_preservation_manifest.json")
    changed = [n for n, entry in initial["files"].items()
               if not (ROOT / n).is_file() or file_sha(ROOT / n) != entry["sha256"]]
    if changed:
        raise ValueError("Existing user files changed: " + repr(changed))
    return {"starting_file_count": len(initial["files"]), "changed_or_missing": changed,
            "old_plan_digest": initial["old_plan_digest"], "old_actual_runs_exist": {
                arm: (OLD / "arms" / arm / "actual_run").exists() for arm in REVISIONS}}


def readonly_copy(source, destination, expected):
    destination.mkdir(parents=True, exist_ok=False)
    for name, entry in expected.items():
        digest = entry["sha256"] if isinstance(entry, dict) else entry
        source_path = canonical(source / name)
        if file_sha(source_path) != digest:
            raise ValueError("Staging input drift: " + name)
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        exclusive(path, source_path.read_bytes())
        path.chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    verify_tree(destination, expected, readonly=True)


def stage(output):
    plan = read_json(OLD / "experiment_plan.json")
    if plan_digest(plan) != OLD_DIGEST or plan["plan_sha256"] != OLD_DIGEST:
        raise ValueError("Reviewed input plan drift")
    preservation = assert_preserved(output)
    for arm, label in (("A", "baseline"), ("B", "candidate")):
        item = plan["arms"][arm]
        if item["revision"] != REVISIONS[arm]: raise ValueError("Revision drift")
        # Verify bytes against immutable local Git as well as the old export.
        for name, entry in item["source_files"].items():
            import hashlib
            blob = subprocess.check_output(["git", "show", item["revision"] + ":" + name], cwd=ROOT)
            if hashlib.sha256(blob).hexdigest() != entry["sha256"]:
                raise ValueError("Frozen Git/source mismatch")
        readonly_copy(Path(item["source_export"]), output / "exports" / label, item["source_files"])
    readonly_copy(OLD / "arms/A/probe_native_pinned/fixture", output / "canonical_fixture", plan["fixture_hashes"])
    prompt = Path(plan["model_prompt_file"])
    if file_sha(prompt) != plan["model_prompt_sha256"]: raise ValueError("Prompt drift")
    exclusive(output / "common_model_prompt.txt", prompt.read_bytes())
    (output / "common_model_prompt.txt").chmod(stat.S_IREAD)
    (output / "runs").mkdir(exist_ok=False)
    # Hash cached bytes only. No tokenizer/model imports, downloads or inference.
    cached = {}
    for name, entry in plan["model"]["files"].items():
        path = Path(plan["model"]["local_snapshot"]) / name
        cached[name] = {"sha256": file_sha(path), "size": path.stat().st_size}
        if cached[name] != entry: raise ValueError("Cached model drift")
    exclusive_json(output / "staging_manifest.json", {"old_plan_digest": OLD_DIGEST,
        "preservation": preservation, "cached_model_files": cached, "coding_model_loaded": False,
        "coding_model_calls": 0, "experiment_arms_started": 0,
        "protected_trees": {str(p): tree_hashes(p) for p in
            (output / "exports/baseline", output / "exports/candidate", output / "canonical_fixture")}})


def junit(path):
    suites = list(ET.parse(path).getroot().iter("testsuite"))
    total = {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    total["passed"] = total["tests"] - total["failures"] - total["errors"] - total["skipped"]
    return total


def finalize(output, controls_attempt, artifact_dir=None):
    preservation = assert_preserved(output)
    stage_record = read_json(output / "staging_manifest.json")
    for path, hashes in stage_record["protected_trees"].items():
        verify_tree(path, hashes, readonly=True)
    original = read_json(OLD / "experiment_plan.json")
    validation = {"phase8_1_integration": junit(output / "validation_export_01/eval_results_phase8_1/final_integration.xml"),
        "phase8_1_strategy": junit(output / "validation_export_01/eval_results_phase8_1/isolated_strategy_regression.xml"),
        "phase8_2_and_8_2_1_controls": junit(output / (controls_attempt + ".xml"))}
    commands = {"phase8_1": read_json(output / "phase8_1_attempt01_command.json"),
                "controls": read_json(output / (controls_attempt + "_command.json")),
                "phase8_1_integration": read_json(output / "validation_export_01/eval_results_phase8_1/final_integration_command.json"),
                "phase8_1_strategy": read_json(output / "validation_export_01/eval_results_phase8_1/isolated_strategy_regression_command.json")}
    if any(v["failures"] or v["errors"] for v in validation.values()) or any(v.get("exit_code", v.get("returncode")) != 0 for v in commands.values()):
        raise ValueError("Final deterministic validation failed")
    export_unchanged = all(file_sha(output / "validation_export_01" / n) == e["sha256"]
        for n, e in read_json(output / "validation_export_01_manifest.json")["files"].items())
    if not export_unchanged:
        raise ValueError("Regression validation source drift")
    sources = {str(ROOT / name): file_sha(ROOT / name) for name in BOUND_SOURCES}
    tested = commands["controls"]["source_hashes"]
    if any(tested.get(k) != v for k, v in sources.items()):
        raise ValueError("Implementation changed after final controls tests")
    artifacts = canonical(artifact_dir) if artifact_dir else output
    if artifacts != output:
        if output not in artifacts.parents:
            raise ValueError("Final revision artifacts must stay inside the timestamped evidence directory")
        artifacts.mkdir(exist_ok=False)
    exclusive_json(artifacts / "test_results.json", {"final_suites": validation, "commands": commands,
        "controls_attempts": {p.stem: {"counts": junit(p), "command": read_json(p.with_name(p.stem + "_command.json"))}
                              for p in sorted(output.glob("controls_attempt*.xml"))},
        "attempt_logs_preserved": [p.name for p in sorted(output.glob("*attempt*.log"))],
        "coding_model_calls": 0, "experiment_arms_started": 0, "generated_patches_applied": 0})
    exclusive_json(artifacts / "source_hash_manifest.json", sources)
    exclusive_json(artifacts / "protected_file_hash_manifest.json", {
        "before": stage_record["protected_trees"], "after": {p: tree_hashes(Path(p)) for p in stage_record["protected_trees"]},
        "readonly_files_verified": True, "preservation": preservation,
        "validation_export_unchanged": export_unchanged})
    # Create the new plan only after all implementation and regression gates above.
    plan = dict(original)
    for key in ("plan_sha256", "draft_revision", "final_model_free_probes", "preflight_script_sha256"):
        plan.pop(key, None)
    plan.update(schema_version="8.2.1", experiment_id=output.name + ("_" + artifacts.name if artifacts != output else ""), status="AWAITING_INDEPENDENT_REVIEW_AND_EXPLICIT_APPROVAL",
        supersedes_unapproved_plan_sha256=OLD_DIGEST, model_backed_comparison_executed=False,
        evidence_output=str(artifacts), run_root=str(output / "runs"), canonical_fixture=str(output / "canonical_fixture"),
        model_prompt_file=str(output / "common_model_prompt.txt"), adapter_sha256=sources[str(ROOT / "scripts/phase8_2_1_arm.py")],
        execution_files={n: sources[str(ROOT / "scripts" / n)] for n in EXECUTION_FILES},
        preparation_source_sha256=sources[str(ROOT / "scripts/phase8_2_1_prepare.py")],
        historical_roots=[str(ROOT / name) for name in ("eval_results_phase8", "eval_results_phase8_1", "eval_results_phase8_2",
            "experiments", "app", "eval_dataset_v1", "eval_dataset_v2", "scripts", "tests", ".git", ".hf_cache")],
        deterministic_test_results_sha256=file_sha(artifacts / "test_results.json"),
        source_hash_manifest_sha256=file_sha(artifacts / "source_hash_manifest.json"))
    if artifacts != output:
        plan["supersedes_prepared_plan_sha256"] = read_json(output / "experiment_plan.json")["plan_sha256"]
    plan["arms"] = {arm: dict(original["arms"][arm], source_export=str(output / "exports" / label),
        run_output=str(output / "runs" / arm)) for arm, label in (("A", "baseline"), ("B", "candidate"))}
    plan["oracle"] = dict(original["oracle"], transport="Unchanged frozen oracle/assertions via common guarded pytest worker; 30s supervised timeout")
    plan["approval_gate"] = {"run_flag": "--run", "approved_digest_argument": "--approved-plan-sha256",
        "human_plan_confirmation": "Exact digest typed before owning outputs and initializing supervisor/launching worker",
        "internal_worker": "Private pipe capability; one-use SHA256 verifier bound to plan/task/revision/arm/output/run_id/parent PID/child PID; expires in 30s",
        "proposal_confirmation": "Durable complete checkpoint before exact proposal-hash confirmation; target writes remain locked until confirmation",
        "current_authorization": "NOT_GRANTED"}
    plan["preflight_control_test_count"] = validation["phase8_2_and_8_2_1_controls"]["passed"]
    plan["limitations"] += [
        "Python audit hooks reject ordinary writes/network operations; native code or the owning OS account can bypass them. No hardened OS sandbox or network isolation is claimed.",
        "Read-only attributes apply to new exports/master fixture only. Historical exports remain byte-for-byte and attribute-for-attribute untouched.",
        "Private pipe authorization closes accidental CLI bypass; it is not a security boundary against a malicious local user with the same OS rights.",
        "Power loss may leave partial exclusive evidence; readers fail closed. After forced kill, durable pre-call events bound attempts but exact model-entry/return may be unknown.",
        "End-to-end model loading, inference, approval/application and real paired execution remain untested and unexecuted."]
    plan["generation_evidence_policy"] = "Exclusive raw prompt/response/proposal artifacts; durable pre-call and post-call events; rejected/failed candidates retained; no terminal overwrite"
    plan["outcome_record_policy"] = "Distinct cancelled/timeout/child_failure/execution_exception terminals; worker outcome plus parent post-run protected-hash/call audit. Interrupted model entry is not inferred."
    plan["plan_sha256"] = plan_digest(plan)
    verify_bound_evidence(plan)  # final bytes must match before an immutable plan is published
    exclusive_json(artifacts / "experiment_plan.json", plan)
    commands_out = {arm: {"argv": [sys.executable, "-B", str(ROOT / "scripts/phase8_2_1_arm.py"), "--run", "--plan",
        str(artifacts / "experiment_plan.json"), "--arm", arm, "--approved-plan-sha256", plan["plan_sha256"]],
        "requires_typed_digest": True, "executed": False} for arm in ("A", "B")}
    exclusive_json(artifacts / "approval_gated_commands.json", commands_out)
    print(plan["plan_sha256"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["stage", "finalize"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--controls-attempt", default="controls_attempt02")
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    output = canonical(args.output)
    if args.mode == "stage": stage(output)
    else: finalize(output, args.controls_attempt, args.artifact_dir)


if __name__ == "__main__":
    main()
