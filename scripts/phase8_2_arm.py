"""One frozen arm: model-free probe by default; explicit approved-plan gate for runs.

This is experiment infrastructure, not an agent feature. It never changes frozen
source. The common loader adapter compensates for baseline's missing revision pin.
"""
import argparse
import hashlib
import importlib.util
from importlib.metadata import version
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time
import traceback

_OWNED_OUTPUT = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plan_digest(plan):
    return sha(json.dumps({k: v for k, v in plan.items() if k != "plan_sha256"}, sort_keys=True,
                          separators=(",", ":")).encode())


def check_approval(plan, supplied):
    digest = plan_digest(plan)
    if plan.get("plan_sha256") != digest or supplied != digest:
        raise ValueError("Model execution requires explicit approval of this exact plan SHA256")
    return digest


def snapshot(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file()}


def classify_outcome(status, oracle, approved, review_rejected, oracle_unchanged, changed):
    tests = status.get("test_results") or {}
    if not oracle_unchanged:
        return "inconclusive_oracle_changed"
    if review_rejected:
        return "inconclusive_review_rejected"
    if status.get("failure_category") in ("model_generation_failure", "environment_failure", "internal_orchestration_error", "timeout") or tests.get("timeout") or tests.get("status") in ("error", "missing_executable", "invalid_directory"):
        return "inconclusive_execution_error"
    if oracle.get("exit_code") not in (0, 1):
        return "inconclusive_oracle_execution"
    if approved and changed and oracle.get("passed") is True and status.get("state") == "completed":
        return "functional_success"
    return "functional_failure"


def common_task_prompt(task, root):
    context = "\n\n".join("FILE: " + rel + "\n" + (root / rel).read_text(encoding="utf-8")
                             for rel in task.target_files)
    return task.prompt + "\n\nSOURCE SNAPSHOT (read-only context):\n" + context


def independent_oracle(task, root, status, timeout=30):
    """Unchanged frozen oracle; add a common outer timeout/environment only."""
    original = subprocess.run
    def bounded(argv, **kwargs):
        if argv != [sys.executable, "-m", "pytest", "tests/test_router.py"]:
            raise ValueError("Unexpected oracle command")
        kwargs["timeout"] = timeout
        kwargs["shell"] = False
        return original(argv, **kwargs)
    subprocess.run = bounded
    try:
        return task.acceptance_fn(str(root), status)
    finally:
        subprocess.run = original


def configure_environment():
    sys.dont_write_bytecode = True
    # Frozen baseline resolves a pytest executable from PATH; candidate launches
    # sys.executable. Bind both to this same venv rather than an ambient pytest.
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    for key in ("PYTEST_PLUGINS", "PYTHONSTARTUP", "PYTHONINSPECT", "LD_PRELOAD", "LD_LIBRARY_PATH"):
        os.environ.pop(key, None)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1",
                      PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="-p no:cacheprovider",
                      PYTHONDONTWRITEBYTECODE="1", LITECODER_MEMORY_ENABLED="false",
                      LITECODER_STRATEGY_ENABLED="false", LITECODER_MODEL_NAME="Qwen/Qwen2.5-Coder-1.5B-Instruct",
                      LITECODER_MODEL_REVISION="2e1fd397ee46e1388853d2af2c993145b0f1098a")


def worker(source, output, task_id, plan=None, arm=None):
    global _OWNED_OUTPUT
    source, output = Path(source).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    _OWNED_OUTPUT = output
    configure_environment()
    os.chdir(output)
    sys.path.insert(0, str(source))
    from eval_dataset_v2.tasks import ALL_TASKS
    task = next(t for t in ALL_TASKS if t.task_id == task_id)
    if task.task_id != "task_01_router_slug_param" or task.category != "single_function_bugfix":
        raise ValueError("This controlled adapter supports only the reviewed canonical router task")
    fixture = output / "fixture"
    fixture.mkdir()
    task.setup_fn(str(fixture))
    initial = snapshot(fixture)
    before_oracle = independent_oracle(task, fixture, {})
    if before_oracle.get("passed") is not False or before_oracle.get("exit_code") != 1:
        raise ValueError("Fixture must reproduce the independent assertion failure before generation")
    prompt_task = common_task_prompt(task, fixture)
    import app.engineering_loop as loop
    import app.model as model
    from app.config import config
    from app.project_test_runner import project_test_runner
    config.config.update(MEMORY_ENABLED=False, STRATEGY_LEARNING_ENABLED=False, LORA_ENABLED=False,
                         DIFFICULTY_ALLOCATION_ENABLED=False, DETERMINISTIC_GENERATION=True,
                         BENCHMARK_SEED=42, MAX_NEW_TOKENS=768)
    project_test_runner.default_timeout = 30
    session = loop.EngineeringSession(prompt_task, str(fixture), task.test_command, fallback_enabled=True,
        eager_policy_check=True, repo_index_enabled=False, prompt_example_enabled=True,
        memory_enabled=False, strategy_enabled=False, storage_dir=str(output / "state"))
    session.max_attempts = 1
    generation = {"boundary_invocations": 0, "real_generate_calls": 0}
    prompt_path = output / "model_prompt.txt"
    if plan is None:
        def forbidden_load(*args, **kwargs):
            raise AssertionError("Model loading forbidden during preflight")
        model.get_model = forbidden_load
        def probe(prompt):
            generation["boundary_invocations"] += 1
            prompt_path.write_bytes(prompt.encode())
            return "PHASE8_2_NO_MODEL_PROBE"
        loop.generate_raw = probe
        session.step()
        evidence = {"mode": "model_free_probe", "real_model_calls": 0,
            "boundary_invocations": generation["boundary_invocations"], "model_loader_blocked": True,
            "task_id": task.task_id, "category": task.category, "canonical_task_prompt": task.prompt,
            "test_command": task.test_command, "targets": task.target_files,
            "fixture_hashes": initial, "fixture_unchanged": snapshot(fixture) == initial,
            "initial_independent_oracle": before_oracle, "prompt_sha256": sha(prompt_path.read_bytes()),
            "session_probe_state": session.state, "note": "Sentinel output is not an actual model result or functional repair."}
        (output / "probe.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        return evidence

    # This branch is unreachable in a preflight invocation and is not exercised
    # with a real model until human approval of the complete paired plan.
    expected = plan["arms"][arm]
    if initial != plan["fixture_hashes"]:
        raise ValueError("Starting fixture drift")
    import torch
    torch.set_num_threads(plan["hardware"]["torch_threads"])
    torch.manual_seed(plan["generation"]["seed"])
    model.torch.cuda.is_available = lambda: False
    original_tokenizer = model.AutoTokenizer.from_pretrained
    original_model = model.AutoModelForCausalLM.from_pretrained
    local_snapshot = plan["model"]["local_snapshot"]
    def pinned_tokenizer(*args, **kwargs):
        kwargs.update(revision=plan["model"]["revision"], local_files_only=True)
        return original_tokenizer(local_snapshot, **kwargs)
    def pinned_model(*args, **kwargs):
        kwargs.update(revision=plan["model"]["revision"], local_files_only=True,
                      torch_dtype=torch.float32, attn_implementation="eager")
        return original_model(local_snapshot, **kwargs)
    model.AutoTokenizer.from_pretrained = pinned_tokenizer
    model.AutoModelForCausalLM.from_pretrained = pinned_model
    original_get = model.get_model
    original_raw = model.generate_raw
    def measured_get():
        started = time.monotonic()
        net, tokenizer = original_get()
        generation["load_duration_s"] = time.monotonic() - started
        original_generate = net.generate
        def measured_generate(*args, **kwargs):
            if generation["real_generate_calls"] >= 1:
                raise RuntimeError("Model call budget exceeded")
            if kwargs.get("max_new_tokens") != 768 or kwargs.get("do_sample") is not False or kwargs.get("repetition_penalty") != 1.1:
                raise ValueError("Generation settings drift")
            generation["real_generate_calls"] += 1
            kwargs["max_time"] = plan["generation"]["soft_timeout_seconds"]
            generation["settings"] = {k: kwargs.get(k) for k in ("max_new_tokens", "do_sample", "repetition_penalty", "max_time", "eos_token_id", "pad_token_id")}
            generation["device"] = str(next(net.parameters()).device)
            generation["dtype"] = str(next(net.parameters()).dtype)
            generation["input_tokens"] = int(kwargs["input_ids"].shape[-1])
            generation["input_ids_sha256"] = sha(kwargs["input_ids"].cpu().numpy().tobytes())
            generation["generation_started"] = True
            (output / "generation_evidence.json").write_text(json.dumps(generation, indent=2))
            started = time.monotonic()
            try:
                tokens = original_generate(*args, **kwargs)
                generation["output_tokens"] = int(tokens.shape[-1]) - generation["input_tokens"]
                generation["output_ids_sha256"] = sha(tokens.cpu().numpy().tobytes())
                return tokens
            finally:
                generation["inference_duration_s"] = time.monotonic() - started
                (output / "generation_evidence.json").write_text(json.dumps(generation, indent=2))
        net.generate = measured_generate
        return net, tokenizer
    model.get_model = measured_get
    def controlled_generate(prompt):
        if sha(prompt.encode()) != plan["model_prompt_sha256"]:
            raise ValueError("Prompt drift; refusing model execution")
        generation["boundary_invocations"] += 1
        prompt_path.write_bytes(prompt.encode())
        response = original_raw(prompt, max_new_tokens=plan["generation"]["max_new_tokens"])
        (output / "raw_response.txt").write_bytes(response.encode())
        return response
    loop.generate_raw = controlled_generate
    started = time.monotonic()
    session.step()
    review_seconds = 0
    approved = False
    review_rejected = False
    if session.state == loop.EngineeringState.AWAITING_APPROVAL:
        if {p.replace("\\", "/") for p in session.source_file_hashes} != set(task.target_files):
            session.reject()
        else:
            (output / "proposed_patch.txt").write_bytes(session.current_diff.encode())
            print(session.current_diff, flush=True)
            review_start = time.monotonic()
            answer = input(f"Review this patch. Type its SHA256 to approve ({session.current_patch_hash}): ")
            review_seconds = time.monotonic() - review_start
            if answer.strip() == session.current_patch_hash:
                approved = session.approve(expected_patch_hash=session.current_patch_hash)
                if approved:
                    session.step()
            else:
                review_rejected = True
                session.reject()
    status = session.get_status()
    final_oracle = independent_oracle(task, fixture, status)
    after = snapshot(fixture)
    oracle_unchanged = all(after.get(p) == h for p, h in initial.items() if p.startswith("tests/"))
    classification = classify_outcome(status, final_oracle, approved, review_rejected, oracle_unchanged, after != initial)
    result = {"arm": arm, "source_revision": expected["revision"], "plan_sha256": plan["plan_sha256"],
        "task_id": task_id, "generation": generation, "proposal_approved": approved,
        "initial_oracle": before_oracle, "final_oracle": final_oracle, "oracle_files_unchanged": oracle_unchanged,
        "fixture_before": initial, "fixture_after": after, "session": status,
        "classification": classification,
        "functional_repair": True if classification == "functional_success" else (False if classification == "functional_failure" else None),
        "duration_s": time.monotonic() - started, "review_duration_s": review_seconds}
    (output / "run_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-id", default="task_01_router_slug_param")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--arm", choices=["A", "B"])
    parser.add_argument("--approved-plan-sha256")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.source, args.output = args.source.resolve(), args.output.resolve()
    if args.output.exists():
        parser.error("Output already exists; refusing to overwrite experiment evidence")
    plan = None
    if args.run:
        if not args.plan or not args.arm:
            parser.error("Execution requires a paired plan, arm and explicit approved plan digest")
        plan = json.loads(args.plan.read_text())
        check_approval(plan, args.approved_plan_sha256)
        if sha(Path(__file__).read_bytes()) != plan["adapter_sha256"]:
            raise ValueError("Experiment adapter changed after approval plan preparation")
        if args.task_id != plan["task_id"]:
            raise ValueError("Task differs from approved plan")
        if any(version(name) != expected for name, expected in plan["dependency_versions"].items()):
            raise ValueError("Dependency environment changed since preparation")
        if platform.platform() != plan["hardware"]["platform"] or platform.processor() != plan["hardware"]["processor_identifier"]:
            raise ValueError("Hardware/OS identifier drift")
        selected = plan["arms"][args.arm]
        if args.source.resolve() != Path(selected["source_export"]).resolve() or args.output.resolve() != Path(selected["run_output"]).resolve():
            raise ValueError("Arm source/output must match the approved plan")
        for name, entry in selected["source_files"].items():
            if sha((args.source / name).read_bytes()) != entry["sha256"]:
                raise ValueError("Frozen source drift: " + name)
        for name, entry in plan["model"]["files"].items():
            if sha((Path(plan["model"]["local_snapshot"]) / name).read_bytes()) != entry["sha256"]:
                raise ValueError("Cached model drift: " + name)
        if not args.child:
            if input("Confirm model execution by typing the approved plan SHA256: ").strip() != plan["plan_sha256"]:
                raise ValueError("Reviewer did not confirm execution")
            process_module = Path(plan["arms"]["B"]["source_export"]) / "app/process_control.py"
            spec = importlib.util.spec_from_file_location("phase82_process_control", process_module)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], "--child"],
                                       start_new_session=os.name != "nt")
            try:
                tree = module.ProcessTree(process)
            except Exception:
                process.kill()
                process.wait(timeout=5)
                raise
            try:
                code = process.wait(timeout=plan["limits"]["arm_wall_timeout_seconds"])
            except subprocess.TimeoutExpired:
                tree.stop()
                args.output.mkdir(parents=True, exist_ok=True)
                (args.output / "termination.json").write_text(json.dumps({"status": "arm_timeout",
                    "actual_model_calls": "consult generation_evidence; not inferred", "functional_repair": None}))
                code = 124
            finally:
                tree.stop()
            raise SystemExit(code)
    try:
        result = worker(args.source, args.output, args.task_id, plan, args.arm)
        print(json.dumps({"mode": "actual_run" if args.run else "model_free_probe",
                          "artifact": str(args.output), "real_model_calls": result.get("real_model_calls", result.get("generation", {}).get("real_generate_calls"))}))
    except Exception:
        if _OWNED_OUTPUT == args.output and args.output.is_dir():
            (args.output / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
            if args.run:
                evidence = args.output / "generation_evidence.json"
                (args.output / "run_error.json").write_text(json.dumps({"status": "execution_exception",
                    "functional_repair": None, "generation": json.loads(evidence.read_text()) if evidence.exists() else None,
                    "traceback": traceback.format_exc()}, indent=2), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
