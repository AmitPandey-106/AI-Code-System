"""Prepare a fingerprinted paired experiment; contains no model execution path."""
import argparse
import hashlib
from importlib.metadata import distributions, version
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BASELINE = "9ef57511e0e25d58d0f1318e9d73ccb58465ec44"
CANDIDATE = "920c01aa0d510aa281092e6b55e4ce02b31e584e"
MODEL_REVISION = "2e1fd397ee46e1388853d2af2c993145b0f1098a"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase8_2_arm import plan_digest


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def collect_environment(snapshot):
    import psutil
    import torch
    packages = {dist.metadata["Name"]: dist.version for dist in distributions() if dist.metadata["Name"]}
    critical = {name: version(name) for name in ("torch", "transformers", "peft", "accelerate", "numpy", "pytest", "safetensors")}
    files = {}
    for path in sorted(snapshot.iterdir()):
        if path.is_file():
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            files[path.name] = {"sha256": h.hexdigest(), "size": path.stat().st_size}
    required = {"config.json", "tokenizer_config.json", "tokenizer.json", "generation_config.json", "model.safetensors"}
    if not required.issubset(files) or any(files[p]["size"] == 0 for p in required):
        raise ValueError("Pinned model cache is incomplete; do not download without approval")
    return {"python": sys.version, "python_executable": sys.executable, "platform": platform.platform(),
        "processor_identifier": platform.processor(), "logical_cpus": psutil.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False), "memory_total_bytes": psutil.virtual_memory().total,
        "memory_available_bytes": psutil.virtual_memory().available, "torch_runtime": torch.__version__,
        "cuda_available": torch.cuda.is_available(), "torch_default_threads": torch.get_num_threads(),
        "cpu_marketing_name": None, "cpu_name_lookup_note": "Win32_Processor CIM query was denied; processor identifier and core counts are directly observed instead.",
        "critical_dependencies": critical, "installed_packages": packages,
        "model_cache": {"snapshot": str(snapshot), "revision": MODEL_REVISION, "files": files},
        "model_weights_loaded": False, "llm_generate_calls": 0,
        "executable_code_risk": "Canonical local benchmark tests are trusted executable Python; neither pytest nor process ownership is an OS sandbox."}


def runner_no_execution(output):
    command = [sys.executable, str(ROOT / "colab_phase8_1/run_targeted.py")]
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=30, shell=False)
    (output / "targeted_runner_no_execution.stdout.txt").write_text(result.stdout, encoding="utf-8")
    (output / "targeted_runner_no_execution.stderr.txt").write_text(result.stderr, encoding="utf-8")
    listing = json.loads(result.stdout) if result.returncode == 0 else {}
    if result.returncode or listing.get("model_calls") != 0 or "task_01_router_slug_param" not in listing.get("tasks", []):
        raise ValueError("Targeted runner listing failed")
    # A second invocation substitutes a fail-closed app.model before executing the
    # same default CLI. A generation attempt would raise and fail this check.
    bootstrap = '''import sys,types,runpy,json,contextlib,io
sys.path.insert(0,sys.argv[1])
blocked=[]
stub=types.ModuleType("app.model")
def forbidden(*args,**kwargs):
 blocked.append(True);raise AssertionError("LLM calls forbidden")
stub.generate_raw=forbidden;stub.get_model=forbidden
sys.modules["app.model"]=stub
script=sys.argv[2];sys.argv=[script]
with contextlib.redirect_stdout(io.StringIO()) as captured:runpy.run_path(script,run_name="__main__")
print(json.dumps({"blocked_attempts":len(blocked),"listing":json.loads(captured.getvalue())}))
'''
    guarded = subprocess.run([sys.executable, "-c", bootstrap, str(ROOT), command[1]],
                             cwd=ROOT, text=True, capture_output=True, timeout=30, shell=False)
    if guarded.returncode:
        raise RuntimeError(guarded.stderr)
    guarded_result = json.loads(guarded.stdout)
    assert guarded_result["blocked_attempts"] == 0
    return {"argv": command, "cwd": str(ROOT), "exit_code": result.returncode,
        "duration_s": time.monotonic() - started, "listing": listing,
        "guarded_repeat": guarded_result, "real_llm_calls": 0,
        "limitation": "Original no-execution mode emits a task list, not a paired protocol. Phase 8.2 creates that protocol separately; original runner is unchanged."}


def junit(path):
    suites = list(ET.parse(path).getroot().iter("testsuite"))
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    totals["duration_s"] = sum(float(s.attrib.get("time", 0)) for s in suites)
    return totals


def prepare(output):
    output = output.resolve()
    probes = {arm: read(output / f"arms/{arm}/probe/probe.json") for arm in ("A", "B")}
    if probes["A"]["prompt_sha256"] != probes["B"]["prompt_sha256"] or probes["A"]["fixture_hashes"] != probes["B"]["fixture_hashes"]:
        raise ValueError("Cross-arm prompt or fixture mismatch; controlled experiment is blocked")
    if any(p["real_model_calls"] != 0 or not p["fixture_unchanged"] for p in probes.values()):
        raise ValueError("Probe modified fixtures or invoked a real model")
    validation_root = output / "exports/candidate/eval_results_phase8_1"
    validation = {name: junit(validation_root / (name + ".xml")) for name in ("final_integration", "isolated_strategy_regression")}
    if any(s["failures"] or s["errors"] or s["skipped"] for s in validation.values()):
        raise ValueError("Deterministic validation gate did not pass")
    snapshot = (ROOT / ".hf_cache/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/snapshots" / MODEL_REVISION).resolve()
    env = collect_environment(snapshot)
    write_new(output / "environment_manifest.json", env)
    runner = runner_no_execution(output)
    write_new(output / "runner_preflight.json", runner)
    arms = {}
    for arm, label, revision in (("A", "baseline", BASELINE), ("B", "candidate", CANDIDATE)):
        export = read(output / (label + "_export_manifest_complete.json"))
        assert export["revision"] == revision
        arms[arm] = {"revision": revision, "source_export": str(output / "exports" / label),
            "source_files": export["files"], "run_output": str(output / "arms" / arm / "actual_run")}
    dataset_tree = subprocess.check_output(["git", "rev-parse", BASELINE + ":eval_dataset_v2"], cwd=ROOT, text=True).strip()
    assert dataset_tree == subprocess.check_output(["git", "rev-parse", CANDIDATE + ":eval_dataset_v2"], cwd=ROOT, text=True).strip()
    task_source = (output / "exports/candidate/eval_dataset_v2/tasks.py").read_bytes()
    import ast
    tree = ast.parse(task_source)
    oracle = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "eval_task_01")
    oracle_source = "\n".join(task_source.decode().splitlines()[oracle.lineno - 1:oracle.end_lineno]) + "\n"
    order = ["A", "B"]
    random.Random(20261025).shuffle(order)
    adapter = ROOT / "scripts/phase8_2_arm.py"
    plan = {"schema_version": 1, "status": "AWAITING_HUMAN_APPROVAL", "model_backed_comparison_executed": False,
        "task_id": "task_01_router_slug_param", "category": probes["A"]["category"],
        "canonical_task_prompt": probes["A"]["canonical_task_prompt"],
        "selection_rationale": "Pure-standard-library single-function router defect; frozen oracle checks normal IDs and hyphenated slugs. Both fixtures freshly reproduce one pass and one assertion failure.",
        "arms": arms, "execution_order": order, "order_seed": 20261025,
        "dataset_git_tree": dataset_tree, "dataset_module_sha256": sha(task_source),
        "oracle": {"qualified_name": "eval_dataset_v2.tasks.eval_task_01", "function_sha256": sha(oracle_source.encode()),
            "source": oracle_source, "test_file": "tests/test_router.py", "test_sha256": probes["A"]["fixture_hashes"]["tests/test_router.py"],
            "command": [sys.executable, "-m", "pytest", "tests/test_router.py"], "timeout_seconds": 30,
            "policy": "Unchanged frozen oracle with common outer timeout and environment; test bytes must remain unchanged."},
        "fixture_hashes": probes["A"]["fixture_hashes"], "model_prompt_sha256": probes["A"]["prompt_sha256"],
        "model_prompt_file": str(output / "common_model_prompt.txt"),
        "input_tokens": "Not measured before approval; exact chat/tokenized input IDs will be captured during actual generation.",
        "model": {"name": "Qwen/Qwen2.5-Coder-1.5B-Instruct", "revision": MODEL_REVISION,
                  "local_snapshot": str(snapshot), "files": env["model_cache"]["files"]},
        "hardware": {"backend": "local Transformers/PyTorch CPU", "device": "cpu", "dtype": "float32",
            "attention_implementation": "eager", "torch_threads": 4, "processor_identifier": env["processor_identifier"],
            "logical_cpus": env["logical_cpus"], "physical_cpus": env["physical_cpus"], "platform": env["platform"],
            "gpu_used": False, "cpu_marketing_name": None},
        "dependency_versions": env["critical_dependencies"], "torch_runtime": env["torch_runtime"],
        "generation": {"seed": 42, "do_sample": False, "repetition_penalty": 1.1, "max_new_tokens": 768,
            "soft_timeout_seconds": 180, "chat_template": "same pinned tokenizer and same frozen system message in both arms"},
        "limits": {"max_attempts_per_arm": 1, "retries_per_arm": 0, "max_model_calls_per_arm": 1,
            "max_model_calls_total": 2, "max_generated_tokens_total": 1536, "native_test_timeout_seconds": 30,
            "arm_wall_timeout_seconds": 300, "child_wall_cap_total_seconds": 600,
            "note": "Child wall limit includes patch review; pre-child confirmation and hash checks are separate. Timeouts are inconclusive infrastructure outcomes."},
        "components": {"memory_enabled": False, "strategy_enabled": False, "lora_enabled": False,
            "repo_index_enabled": False, "prompt_example_enabled": True, "fallback_enabled": True, "eager_policy_check": True},
        "experimental_controls": ["Identical canonical task, fixture bytes, raw prompt and tokenizer/system template",
            "Same environment, model cache hashes, CPU, precision, threads, greedy settings, budgets and independent oracle",
            "Both frozen implementations run in separate processes with separate source/config/state/fixture/output directories",
            "Common read-only source snapshot in task context replaces arm-dependent retrieval; no per-arm prompt tuning",
            "A common loader wrapper pins both arms to cached immutable weights because baseline ignores the revision environment variable"],
        "approval_gate": {"run_flag": "--run", "approved_digest_argument": "--approved-plan-sha256",
            "human_plan_confirmation": "Exact digest typed before launching the supervised child",
            "proposal_confirmation": "Each produced patch needs its own reviewer hash; only micro_http/router.py may be edited",
            "current_authorization": "NOT_GRANTED; preparing this file is not approval"},
        "acceptance": {"functional_success": "Explicitly approved applied change; unchanged oracle/test bytes; independent frozen oracle exit 0; framework completed; target bytes differ from failing fixture",
            "functional_failure": "Within-budget parse/validation failure, or applied repair fails independent assertion tests",
            "inconclusive": "Environment/import/model/cache error, timeout, missing/rejected reviewer confirmation, prompt/fixture/source drift",
            "separate_metrics": ["independent functional outcome", "framework state", "patch validity", "approval decision", "rollback integrity", "calls and tokens", "load/inference/tests/review latency"]},
        "network_required": False, "downloads_permitted": False,
        "cost": {"paid_api_or_gpu_spend": "None: local cached CPU execution; no metered service", "electricity_and_wall_time_cost": "Not estimated; limits above are caps, not performance predictions"},
        "adapter_sha256": sha(adapter.read_bytes()), "evidence_output": str(output),
        "limitations": ["One task and one attempt per arm do not establish general repair accuracy, retry benefits or learning benefits",
            "Retrieval is deliberately disabled to keep prompts identical; this is a controlled repair-pipeline comparison, not a complete default-configuration benchmark",
            "Actual weight loading, generation, token counts, approved patch application and paired functional outcomes have not been tested in this phase",
            "Canonical tests execute trusted local Python; pytest/process restrictions are not an OS sandbox",
            "CPU marketing name lookup was denied; observed processor identifier/core counts are recorded"]}
    plan["plan_sha256"] = plan_digest(plan)
    (output / "common_model_prompt.txt").write_bytes((output / "arms/A/probe/model_prompt.txt").read_bytes())
    write_new(output / "experiment_plan.json", plan)
    write_new(output / "fresh_validation_summary.json", validation)
    print(json.dumps({"status": plan["status"], "plan_sha256": plan["plan_sha256"], "task_id": plan["task_id"],
                      "execution_order": order, "real_llm_calls": 0, "output": str(output)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args().output)
