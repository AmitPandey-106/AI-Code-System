"""Phase 8.2.1 fixed-task runner. Inert without --run + exact digest + typed approval.

Historical phase8_2_arm.py is preserved, not called. No broad benchmark entrypoint.
"""
import argparse
import contextlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import queue
import subprocess
import sys
import threading
import time
import traceback

from phase8_2_1_controls import (TASK, REVISIONS, BoundedInput, Evidence, IntegrityMismatch, Supervisor, WritePolicy, authorize,
    canonical, claim, consume_authorization, disjoint, exclusive_json, file_sha, lifecycle,
    plan_digest, read_json, review_proposal, sha, terminal_exception, tree_hashes, verify_tree,
    check_deadline, exception_details, json_object, protected_audit, timestamp, verify_bound_evidence)

HERE = Path(__file__).resolve().parent
EXECUTION_FILES = ("phase8_2_1_arm.py", "phase8_2_1_controls.py", "phase8_2_1_pytest.py")
PROTOCOL = "PHASE821:"


def configure_environment(workspace):
    sys.dont_write_bytecode = True
    for key in ("PYTEST_PLUGINS", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONPATH", "PYTEST_ADDOPTS",
                "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"):
        os.environ.pop(key, None)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", TOKENIZERS_PARALLELISM="false",
        LITECODER_MEMORY_ENABLED="false", LITECODER_STRATEGY_ENABLED="false",
        LITECODER_MODEL_NAME="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        LITECODER_MODEL_REVISION="2e1fd397ee46e1388853d2af2c993145b0f1098a",
        TMP=str(workspace / "tmp"), TEMP=str(workspace / "tmp"))
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")


def identity(plan, arm):
    item = plan["arms"][arm]
    return {"experiment_id": plan["experiment_id"], "arm": arm, "plan_sha256": plan["plan_sha256"],
            "task_id": plan["task_id"], "revision": item["revision"],
            "source": str(canonical(item["source_export"])), "output": str(canonical(item["run_output"]))}


def validate_plan(plan, supplied, arm, check_environment=True):
    if plan.get("schema_version") != "8.2.1" or supplied != plan_digest(plan) or plan.get("plan_sha256") != supplied:
        raise ValueError("Explicit approval of this exact Phase 8.2.1 plan required")
    if plan["task_id"] != TASK or set(plan["arms"]) != {"A", "B"} or arm not in REVISIONS:
        raise ValueError("Only the fixed paired task and arms are permitted")
    if {k: v["revision"] for k, v in plan["arms"].items()} != REVISIONS:
        raise ValueError("Frozen revision mismatch")
    if set(plan["execution_files"]) != set(EXECUTION_FILES):
        raise ValueError("Incomplete execution source binding")
    for name in EXECUTION_FILES:
        if file_sha(HERE / name) != plan["execution_files"][name]:
            raise ValueError("Execution adapter changed: " + name)
    limits = plan["limits"]
    fixed = {"max_attempts_per_arm": 1, "retries_per_arm": 0, "max_model_calls_per_arm": 1,
             "max_model_calls_total": 2, "max_generated_tokens_total": 1536,
             "native_test_timeout_seconds": 30, "arm_wall_timeout_seconds": 300,
             "child_wall_cap_total_seconds": 600}
    if any(limits.get(k) != v for k, v in fixed.items()):
        raise ValueError("Budget drift")
    gen = plan["generation"]
    if any(gen.get(k) != v for k, v in {"max_new_tokens": 768, "do_sample": False,
            "seed": 42, "repetition_penalty": 1.1, "soft_timeout_seconds": 180}.items()):
        raise ValueError("Generation settings drift")
    sources = [v["source_export"] for v in plan["arms"].values()]
    outputs = [v["run_output"] for v in plan["arms"].values()]
    disjoint(sources + outputs + [plan["canonical_fixture"]] + plan["historical_roots"])
    run_root = canonical(plan["run_root"])
    for name, item in plan["arms"].items():
        if canonical(item["run_output"]) != run_root / name:
            raise ValueError("Output must be the fixed approved arm directory")
    verify_protected(plan)
    if file_sha(plan["model_prompt_file"]) != plan["model_prompt_sha256"]:
        raise ValueError("Prompt drift")
    if plan["oracle"]["test_sha256"] != plan["fixture_hashes"]["tests/test_router.py"]:
        raise ValueError("Oracle drift")
    if (sha(plan["oracle"]["source"].encode()) != plan["oracle"]["function_sha256"]
            or plan["oracle"]["command"] != [sys.executable, "-m", "pytest", "tests/test_router.py"]):
        raise ValueError("Oracle function/command drift")
    if check_environment:
        if sys.executable != plan["python_runtime"]["executable"] or sys.version != plan["python_runtime"]["version"]:
            raise ValueError("Python runtime drift")
        if any(version(n) != v for n, v in plan["dependency_versions"].items()):
            raise ValueError("Dependency drift")
        if platform.platform() != plan["hardware"]["platform"] or platform.processor() != plan["hardware"]["processor_identifier"]:
            raise ValueError("Hardware/OS drift")
        for name, expected in plan["model"]["files"].items():
            path = Path(plan["model"]["local_snapshot"]) / name
            if path.stat().st_size != expected["size"] or file_sha(path) != expected["sha256"]:
                raise ValueError("Cached model drift: " + name)
    return identity(plan, arm)


def verify_protected(plan):
    verify_bound_evidence(plan)
    for name in EXECUTION_FILES:
        if file_sha(HERE / name) != plan["execution_files"][name]:
            raise IntegrityMismatch("Execution source changed: " + name)
    if file_sha(plan["model_prompt_file"]) != plan["model_prompt_sha256"]:
        raise IntegrityMismatch("Prompt changed")
    for item in plan["arms"].values():
        verify_tree(item["source_export"], item["source_files"], readonly=True)
    verify_tree(plan["canonical_fixture"], plan["fixture_hashes"], readonly=True)


def guarded_test_argv(fixture, plan):
    return [sys.executable, "-B", str(HERE / "phase8_2_1_pytest.py"),
            str(fixture), plan["oracle"]["test_sha256"]]


def run_guarded_tests(argv, fixture):
    supervisor = Supervisor()
    error = None
    try:
        process = supervisor.launch(argv, cwd=fixture, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=30)
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    except BaseException as exc:
        error = exc
        raise
    finally:
        try:
            supervisor.close()
        except BaseException as cleanup_error:
            if error is None: raise
            with contextlib.suppress(BaseException):
                print("Test-worker cleanup failed: " + type(cleanup_error).__name__, file=sys.stderr)


def oracle(task, fixture, status, argv):
    original = subprocess.run
    def fixed(command, **kwargs):
        if command != [sys.executable, "-m", "pytest", "tests/test_router.py"] or canonical(kwargs["cwd"]) != fixture:
            raise ValueError("Unexpected oracle invocation")
        return run_guarded_tests(argv, fixture)
    subprocess.run = fixed
    try:
        return task.acceptance_fn(str(fixture), status)
    finally:
        subprocess.run = original


class GenerationBudget:
    def __init__(self, evidence):
        self.evidence = evidence
        self.boundary_calls = self.real_calls = 0

    def boundary(self, prompt, expected_hash, generate):
        if self.boundary_calls != 0 or sha(prompt.encode()) != expected_hash:
            raise ValueError("Model boundary budget or prompt mismatch")
        self.boundary_calls += 1
        self.evidence.artifact("model_prompt.txt", prompt.encode())
        self.evidence.event("model_boundary_entered", boundary_invocations=self.boundary_calls)
        try:
            response = generate(prompt, max_new_tokens=768)
            self.evidence.artifact("raw_response.txt", response.encode())
            self.evidence.event("raw_response_recorded", response_sha256=sha(response.encode()))
            return response
        except BaseException as exc:
            try:
                self.evidence.event("model_boundary_error", error_type=type(exc).__name__, error=str(exc))
            except BaseException:
                pass  # outer lifecycle persists original failure if storage recovers
            raise

    def generate(self, generate, args, kwargs):
        if self.real_calls != 0:
            raise RuntimeError("One real model call per arm; no fallback call")
        if kwargs.get("max_new_tokens") != 768 or kwargs.get("do_sample") is not False or kwargs.get("repetition_penalty") != 1.1:
            raise ValueError("Generation settings drift")
        self.real_calls += 1
        kwargs["max_time"] = 180
        inputs = kwargs["input_ids"]
        self.evidence.event("generation_started", actual_model_calls=self.real_calls,
            input_tokens=int(inputs.shape[-1]), input_ids_sha256=sha(inputs.cpu().numpy().tobytes()),
            max_new_tokens=768, do_sample=False, repetition_penalty=1.1, max_time=180)
        started = time.monotonic()
        try:
            tokens = generate(*args, **kwargs)
            count = int(tokens.shape[-1]) - int(inputs.shape[-1])
            self.evidence.event("generation_returned", actual_model_calls=self.real_calls,
                output_tokens=count, output_ids_sha256=sha(tokens.cpu().numpy().tobytes()),
                duration_s=time.monotonic() - started)
            if not 0 <= count <= 768:
                raise ValueError("Generated token budget exceeded")
            return tokens
        except BaseException as exc:
            try:
                self.evidence.event("generation_error", actual_model_calls=self.real_calls,
                    error_type=type(exc).__name__, error=str(exc), duration_s=time.monotonic() - started)
            except BaseException:
                pass  # never replace cancellation/model exception with a logging error
            raise


def classify(status, result, approved, rejected, unchanged, changed):
    if not unchanged or rejected:
        return "inconclusive_oracle_changed" if not unchanged else "inconclusive_review_rejected"
    tests = status.get("test_results") or {}
    if (status.get("failure_category") in ("model_generation_failure", "environment_failure", "internal_orchestration_error", "timeout")
            or tests.get("timeout") or tests.get("status") in ("error", "missing_executable", "invalid_directory")
            or result.get("exit_code") not in (0, 1)):
        return "inconclusive_execution_error"
    if approved and changed and result.get("passed") is True and status.get("state") == "completed":
        return "functional_success"
    return "functional_failure"


def experiment_worker(plan, arm, evidence, policy, review):
    """Only called after pipe authentication. Never called by preparation/tests."""
    selected = plan["arms"][arm]
    workspace = Path(selected["run_output"]) / "workspace"
    fixture = workspace / "fixture"
    fixture.mkdir()
    for rel in plan["fixture_hashes"]:
        target = fixture / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write((Path(plan["canonical_fixture"]) / rel).read_bytes())
    verify_tree(fixture, plan["fixture_hashes"])
    # Lock fixture after independent restoration; only reviewed target can unlock.
    policy.fixture = fixture
    sys.path.insert(0, selected["source_export"])
    from eval_dataset_v2.tasks import ALL_TASKS
    task = next(t for t in ALL_TASKS if t.task_id == TASK)
    if (task.prompt != plan["canonical_task_prompt"] or task.target_files != ["micro_http/router.py"]
            or task.category != "single_function_bugfix" or task.test_command != "pytest tests/test_router.py"):
        raise ValueError("Task definition drift")
    argv = guarded_test_argv(fixture, plan)
    policy.subprocess_argv = argv
    initial = oracle(task, fixture, {}, argv)
    evidence.event("initial_oracle", fixture_hashes=plan["fixture_hashes"],
                   prompt_sha256=plan["model_prompt_sha256"], initial_oracle=initial)
    if initial.get("passed") is not False or initial.get("exit_code") != 1:
        raise ValueError("Canonical defect must reproduce before generation")
    import app.engineering_loop as loop
    import app.model as model
    from app.config import config
    from app.project_test_runner import project_test_runner
    import torch
    config.config.update(MEMORY_ENABLED=False, STRATEGY_LEARNING_ENABLED=False, LORA_ENABLED=False,
        DIFFICULTY_ALLOCATION_ENABLED=False, DETERMINISTIC_GENERATION=True, BENCHMARK_SEED=42, MAX_NEW_TOKENS=768)
    torch.set_num_threads(4); torch.manual_seed(42)
    model.torch.cuda.is_available = lambda: False
    original_tokenizer = model.AutoTokenizer.from_pretrained
    original_loader = model.AutoModelForCausalLM.from_pretrained
    def pinned_tokenizer(*args, **kwargs):
        kwargs.update(revision=plan["model"]["revision"], local_files_only=True)
        return original_tokenizer(plan["model"]["local_snapshot"], **kwargs)
    def pinned_model(*args, **kwargs):
        kwargs.update(revision=plan["model"]["revision"], local_files_only=True,
                      torch_dtype=torch.float32, attn_implementation="eager")
        return original_loader(plan["model"]["local_snapshot"], **kwargs)
    model.AutoTokenizer.from_pretrained = pinned_tokenizer
    model.AutoModelForCausalLM.from_pretrained = pinned_model
    budget = GenerationBudget(evidence)
    original_get, original_raw = model.get_model, model.generate_raw
    loaded = False
    def get_once():
        nonlocal loaded
        if loaded:
            raise RuntimeError("Additional model acquisition forbidden")
        loaded = True
        started = time.monotonic()
        net, tokenizer = original_get()
        evidence.event("model_loaded", duration_s=time.monotonic() - started,
                       device=str(next(net.parameters()).device), dtype=str(next(net.parameters()).dtype))
        original_generate = net.generate
        net.generate = lambda *a, **k: budget.generate(original_generate, a, k)
        return net, tokenizer
    model.get_model = get_once
    bounded = lambda prompt, **kwargs: budget.boundary(prompt, plan["model_prompt_sha256"], original_raw)
    model.generate_raw = bounded
    loop.generate_raw = bounded
    # Same unchanged oracle tests, under the same common guarded transport in both arms.
    def native_tests(repo_root, command, timeout=None, **kwargs):
        if canonical(repo_root) != fixture or command != task.test_command:
            raise ValueError("Native test command drift")
        started = time.monotonic()
        try:
            result = run_guarded_tests(argv, fixture)
            return {"success": result.returncode == 0, "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout + result.stderr, "error": None, "exit_code": result.returncode,
                "duration_ms": (time.monotonic() - started) * 1000, "timeout": False}
        except subprocess.TimeoutExpired:
            return {"success": False, "status": "error", "output": "", "exit_code": -1,
                    "error": "Guarded pytest timeout", "timeout": True}
    project_test_runner.run_tests = native_tests
    prompt = task.prompt + "\n\nSOURCE SNAPSHOT (read-only context):\n" + "\n\n".join(
        "FILE: " + rel + "\n" + (fixture / rel).read_text(encoding="utf-8") for rel in task.target_files)
    session = loop.EngineeringSession(prompt, str(fixture), task.test_command,
        fallback_enabled=True, eager_policy_check=True, repo_index_enabled=False,
        prompt_example_enabled=True, memory_enabled=False, strategy_enabled=False,
        storage_dir=str(workspace / "state"))
    session.max_attempts = 1
    session.step()
    approved = rejected = False
    # Preserve even malformed/failed proposals, independently from model response.
    if session.state == loop.EngineeringState.AWAITING_APPROVAL:
        if {p.replace("\\", "/") for p in session.source_file_hashes} != {"micro_http/router.py"}:
            evidence.event("proposal_target_rejected", session=session.get_status())
            rejected = True; session.reject()
        else:
            approved = review_proposal(session, evidence, policy,
                {"fixture_hashes": tree_hashes(fixture), "prompt_sha256": plan["model_prompt_sha256"],
                 "initial_oracle": initial}, review)
            rejected = not approved
            if approved:
                session.step()
    else:
        evidence.artifact("failed_proposal.txt", session.current_diff.encode())
        evidence.event("proposal_not_reviewable", proposal_sha256=sha(session.current_diff.encode()), session=session.get_status())
    status = session.get_status()
    final = oracle(task, fixture, status, argv)
    after = tree_hashes(fixture)
    unchanged = all(after.get(p) == h for p, h in plan["fixture_hashes"].items() if p != "micro_http/router.py")
    outcome = classify(status, final, approved, rejected, unchanged, after != plan["fixture_hashes"])
    verify_protected(plan)
    evidence.event("oracle_completed", final_oracle=final, fixture_after=after)
    evidence.finalize("review_rejected" if rejected else "completed", classification=outcome,
        functional_repair=True if outcome == "functional_success" else False if outcome == "functional_failure" else None,
        actual_model_calls=budget.real_calls, boundary_invocations=budget.boundary_calls,
        initial_oracle=initial, final_oracle=final, fixture_after=after, oracle_files_unchanged=unchanged,
        proposal_approved=approved, session=status)


def internal_worker(plan_path, arm):
    # No authorization record or token -> no output creation or model import.
    plan = read_json(plan_path)
    context = validate_plan(plan, plan.get("plan_sha256"), arm, check_environment=False)
    output = Path(context["output"])
    if sys.stdin.isatty():
        raise PermissionError("Internal worker requires an authenticated private pipe")
    message = sys.stdin.readline(8192)
    try:
        authorization = json_object(message.encode())
        token = authorization["authorization"]
    except (ValueError, KeyError, TypeError):
        raise PermissionError("Internal worker authorization rejected") from None
    consume_authorization(output, context, token)
    deadline = authorization.get("active_deadline_monotonic")
    if type(deadline) not in (int, float) or not 0 < deadline - time.monotonic() <= 300:
        raise PermissionError("Missing or invalid active worker deadline")
    del token, message
    evidence = Evidence(output / "evidence", context)
    def review(checkpoint, proposal):
        check_deadline(deadline)
        print(PROTOCOL + json.dumps({"kind": "patch_review", "checkpoint": checkpoint, "proposal": proposal}), flush=True)
        try:
            answer = json_object(sys.stdin.readline(8192).encode())["patch_sha256"]
        except (ValueError, KeyError, TypeError):
            raise PermissionError("Patch review channel closed or malformed") from None
        check_deadline(deadline)  # an on-time parent write cannot authorize a late application
        return answer
    with lifecycle(evidence):
        workspace = output / "workspace"
        configure_environment(workspace)
        (workspace / "tmp").mkdir()
        os.chdir(workspace)
        policy = WritePolicy(workspace, evidence.root)
        sys.addaudithook(policy.audit)
        evidence.event("worker_authenticated", protected_before_verified=True, actual_model_calls=0)
        experiment_worker(plan, arm, evidence, policy, review)


def actual_counts(output):
    starts, returns = [], []
    for p in (Path(output) / "evidence").glob("event_*.json"):
        event = read_json(p)
        if event["status"] == "generation_started": starts.append(event)
        if event["status"] == "generation_returned": returns.append(event)
    return {"actual_model_calls_started": len(starts), "actual_model_calls_returned": len(returns),
            "output_tokens": returns[0]["output_tokens"] if len(returns) == 1 else None,
            "call_count_basis": "durable pre-call events (attempt upper bound); after forced kill exact entry/return can be unknown"}


def require_completed_arm_a(plan):
    """Conclusive execution is required; a valid baseline repair failure qualifies."""
    output = Path(plan["arms"]["A"]["run_output"])
    try:
        prior = read_json(output / "control/terminal.json")
        worker = read_json(output / "evidence/terminal.json")
        expected = identity(plan, "A")
        if any(record.get(k) != value for record in (prior, worker) for k, value in expected.items()):
            raise ValueError("Prior arm identity mismatch")
        result = worker.get("final_oracle")
        initial = worker.get("initial_oracle")
        category = worker.get("classification")
        termination = prior.get("termination")
        if (prior.get("status") != "completed" or prior.get("protected_after_verified") is not True
                or prior.get("protected_audit_status") != "verified" or prior.get("cleanup_errors") != []
                or prior.get("worker_terminal") != worker or worker.get("status") != "completed"
                or worker.get("oracle_files_unchanged") is not True
                or category not in ("functional_success", "functional_failure")
                or worker.get("functional_repair") is not (category == "functional_success")
                or not isinstance(result, dict) or type(result.get("exit_code")) is not int
                or result["exit_code"] not in (0, 1) or result.get("passed") is not (result["exit_code"] == 0)
                or not isinstance(initial, dict) or type(initial.get("exit_code")) is not int
                or initial["exit_code"] != 1 or initial.get("passed") is not False
                or not isinstance(worker.get("session"), dict)
                or worker["session"].get("state") not in ("completed", "failed")
                or not isinstance(termination, dict) or type(termination.get("process_exit_code")) is not int
                or termination["process_exit_code"] != 0 or not termination.get("process_exit_observed_at")
                or (os.name == "nt" and (type(termination.get("job_active_processes")) is not int
                    or termination["job_active_processes"] != 0 or not termination.get("job_closed_at")))
                or (category == "functional_success" and (result["exit_code"] != 0
                    or worker["session"]["state"] != "completed" or worker.get("proposal_approved") is not True))
                or (category == "functional_failure" and result["exit_code"] == 0 and worker["session"]["state"] == "completed")):
            raise ValueError("Arm A did not complete with a clean conclusive outcome")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise PermissionError("Arm A terminal prerequisite failed: " + str(exc)) from exc


def run_parent(plan_path, supplied, arm, *, confirm=None, supervisor_factory=Supervisor):
    """Active deadline = launch + 300s, shared by worker output and review.

    Preflight/initial approval precede launch. Process reaping, bounded reader
    shutdown and the separately timed integrity audit follow active execution.
    Injected confirmation providers must honor the same polling/deadline contract.
    """
    plan_path = canonical(plan_path)
    plan = read_json(plan_path)
    context = validate_plan(plan, supplied, arm)
    output = Path(context["output"])
    if output.exists():
        raise FileExistsError("Output already exists; use a newly reviewed unique plan")
    if arm == "B":
        require_completed_arm_a(plan)
    if confirm is None:
        confirm = BoundedInput()
    answer = confirm("Type this exact plan SHA256 to start this arm: ")
    if not isinstance(answer, str) or answer.strip() != plan["plan_sha256"]:
        raise PermissionError("Explicit parent approval not received")
    owner = claim(output, context)
    evidence = Evidence(output / "control", context)
    supervisor = None
    timer = None
    timed_out = threading.Event()
    worker_terminal = None
    error = None
    code = None
    process = reader = None
    deadline = None
    started = None
    reader_stop = threading.Event()
    watchdog_errors = []
    watchdog_exceptions = []
    dispatch_lock = threading.Lock()
    cleanup_errors = []
    try:
        with lifecycle(evidence, phase="worker_start") as phase:
            evidence.event("parent_approved", protected_before_verified=True)
            supervisor = supervisor_factory()  # established BEFORE child launch
            argv = [sys.executable, "-B", str(HERE / "phase8_2_1_arm.py"),
                    "--internal-worker", "--plan", str(plan_path), "--arm", arm]
            process = supervisor.launch(argv, cwd=output / "workspace", stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
            started = time.monotonic()
            deadline = started + plan["limits"]["arm_wall_timeout_seconds"]
            phase.update(active_deadline_monotonic=deadline)
            def timeout():
                with dispatch_lock:
                    timed_out.set()
                try:
                    supervisor.close()
                except BaseException as exc:
                    watchdog_errors.append(exception_details("watchdog_cleanup", exc))
                    watchdog_exceptions.append(exc)
            timer = threading.Timer(max(0, deadline - time.monotonic()), timeout)
            timer.daemon = True; timer.start()
            token = authorize(output, owner, process.pid)
            check_deadline(deadline, timed_out)
            process.stdin.write(json.dumps({"authorization": token, "active_deadline_monotonic": deadline}) + "\n")
            process.stdin.flush()
            del token
            evidence.event("worker_started", child_pid=process.pid, supervision_established=True,
                           active_deadline_monotonic=deadline, active_budget_seconds=300)
            messages = queue.Queue(maxsize=64)
            def put(kind, value):
                while not reader_stop.is_set():
                    try:
                        messages.put((kind, value), timeout=.02)
                        return
                    except queue.Full:
                        pass
            def pump():
                try:
                    for line in process.stdout:
                        if len(line) > 1024 * 1024:
                            raise ValueError("Worker protocol line exceeds evidence limit")
                        put("line", line)
                        if reader_stop.is_set():
                            break
                except BaseException as exc:
                    put("error", exc)
                finally:
                    put("eof", None)
            reader = threading.Thread(target=pump, name="litecoder-output", daemon=True)
            reader.start()
            while True:
                phase["phase"] = "worker_output"
                check_deadline(deadline, timed_out)
                try:
                    kind, line = messages.get(timeout=min(.02, max(0, deadline - time.monotonic())))
                except queue.Empty:
                    continue
                check_deadline(deadline, timed_out)
                if kind == "error":
                    raise line
                if kind == "eof":
                    break
                if line.startswith(PROTOCOL):
                    request = json_object(line[len(PROTOCOL):].encode())
                    if request.get("kind") != "patch_review":
                        raise ValueError("Unexpected worker protocol message")
                    # Independently verify durable checkpoint and proposal before showing approval.
                    checkpoint = request["checkpoint"]
                    patch_hash = sha(request["proposal"].encode())
                    durable = [read_json(p) for p in (output / "evidence").glob("event_*.json")]
                    if (checkpoint not in durable or checkpoint.get("proposal_sha256") != patch_hash
                            or any(checkpoint.get(k) != value for k, value in context.items())
                            or (output / "evidence/proposed_patch.txt").read_bytes() != request["proposal"].encode()):
                        raise ValueError("Patch checkpoint missing or mismatched")
                    print(request["proposal"], flush=True)
                    phase["phase"] = "patch_review"
                    answer = confirm("Review patch; type SHA256 to approve (" + patch_hash + "): ",
                                     deadline=deadline, stop=timed_out, alive=lambda: process.poll() is None)
                    with dispatch_lock:
                        check_deadline(deadline, timed_out, lambda: process.poll() is None)
                        if not isinstance(answer, str) or answer.strip() != patch_hash:
                            raise PermissionError("Patch confirmation absent or malformed")
                        process.stdin.write(json.dumps({"patch_sha256": answer.strip()}) + "\n")
                        process.stdin.flush()
                    evidence.event("patch_confirmation_dispatched", proposal_sha256=patch_hash,
                                   active_elapsed_seconds=time.monotonic() - started)
                else:
                    evidence.event("worker_output", text=line.rstrip("\n"))
            phase["phase"] = "worker_exit"
            check_deadline(deadline, timed_out)
            code = process.wait(timeout=min(5, max(0, deadline - time.monotonic())))
            check_deadline(deadline, timed_out)
            evidence.event("worker_exit_observed", process_pid=process.pid, exit_code=code,
                           active_elapsed_seconds=time.monotonic() - started)
            terminal_path = output / "evidence/terminal.json"
            if terminal_path.exists():
                worker_terminal = read_json(terminal_path)
            if code != 0 or not worker_terminal:
                raise ChildProcessError("Worker failed; exit=" + str(code))
    except BaseException as exc:
        error = exc
        raise
    finally:
        if timer: timer.cancel()
        cleanup_exception = None
        cleanup_started = time.monotonic()
        if supervisor:
            try: supervisor.close()
            except BaseException as exc:
                cleanup_errors.append(exception_details("supervisor_cleanup", exc))
                cleanup_exception = exc
        if timer:
            try:
                timer.join(timeout=5)
                if timer.is_alive(): raise TimeoutError("Watchdog cleanup thread did not stop")
            except BaseException as exc:
                cleanup_errors.append(exception_details("watchdog_join", exc))
                if cleanup_exception is None: cleanup_exception = exc
        cleanup_errors.extend(watchdog_errors)
        if watchdog_exceptions and cleanup_exception is None:
            cleanup_exception = watchdog_exceptions[0]
        reader_stop.set()
        if reader:
            try:
                reader.join(timeout=5)
                if reader.is_alive(): raise TimeoutError("Worker output reader did not stop after containment cleanup")
            except BaseException as exc:
                cleanup_errors.append(exception_details("output_reader_join", exc))
                if cleanup_exception is None: cleanup_exception = exc
        if process and (reader is None or not reader.is_alive()):
            for name in ("stdin", "stdout", "stderr"):
                stream = getattr(process, name, None)
                if stream:
                    try: stream.close()
                    except BaseException as exc:
                        cleanup_errors.append(exception_details("pipe_close_" + name, exc))
                        if cleanup_exception is None: cleanup_exception = exc
        audit_started = time.monotonic()
        audit = protected_audit(lambda: verify_protected(plan))
        audit_exception = audit.pop("exception", None)
        protected_ok = audit["verified"]
        if audit_exception is not None:
            cleanup_errors.append(audit["error"])
            if cleanup_exception is None: cleanup_exception = audit_exception
        # lifecycle may already have written terminal on an exception. Exclusive
        # finalization leaves it byte-identical; final audit is a separate event.
        try:
            counts = actual_counts(output)
            details = dict(protected_after_verified=protected_ok, protected_audit_status=audit["status"],
                protected_audit=audit, cleanup_errors=cleanup_errors,
                termination=getattr(supervisor, "termination", None),
                cleanup_duration_seconds=audit_started - cleanup_started,
                protected_audit_duration_seconds=time.monotonic() - audit_started,
                active_deadline_monotonic=deadline, **counts)
            evidence.event("post_run_audit", **details)
            status = (terminal_exception(error) if error else "cancelled"
                      if isinstance(cleanup_exception, KeyboardInterrupt) else "integrity_or_cleanup_failure"
                      if not protected_ok or cleanup_errors else "completed" if code == 0 else "child_failure")
            evidence.finalize(status, worker_terminal=worker_terminal, **details)
        except BaseException as storage_error:
            if error is None and cleanup_exception is None: raise
            with contextlib.suppress(BaseException):
                print("Final audit persistence failed: " + type(storage_error).__name__, file=sys.stderr)
        if cleanup_exception is not None and error is None:
            raise cleanup_exception
    return worker_terminal


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--arm", choices=["A", "B"])
    parser.add_argument("--approved-plan-sha256")
    parser.add_argument("--internal-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.plan or not args.arm:
        parser.error("Plan and fixed arm required; no execution is the default")
    if args.internal_worker:
        if args.run or args.approved_plan_sha256:
            parser.error("Invalid internal worker parameters")
        internal_worker(args.plan, args.arm)
    elif args.run:
        run_parent(args.plan, args.approved_plan_sha256, args.arm)
    else:
        parser.error("Explicit --run and approved plan SHA256 required")


if __name__ == "__main__":
    main()
