"""Deterministic controls only: no arm, coding model, generated patch or network."""
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import copy
import threading
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase8_2_1_controls as controls
import phase8_2_1_arm as runner


def context(output):
    return {"experiment_id": "control-test", "arm": "A", "plan_sha256": "a" * 64,
            "task_id": controls.TASK, "revision": controls.REVISIONS["A"],
            "source": "fixed-source", "output": str(output)}


def evidence(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    return controls.Evidence(tmp_path, context(tmp_path))


def bind_test_evidence(plan, tmp_path):
    """Synthetic evidence only; never repairs or rebinds a historical plan."""
    root = tmp_path / "bound_evidence"; root.mkdir()
    manifest = {str(ROOT / name): controls.file_sha(ROOT / name) for name in controls.BOUND_SOURCES}
    tested = {str(ROOT / name): controls.file_sha(ROOT / name) for name in controls.TESTED_SOURCES}
    counts = {"tests": 1, "passed": 1, "failures": 0, "errors": 0, "skipped": 0}
    controls.exclusive_json(root / "source_hash_manifest.json", manifest)
    controls.exclusive_json(root / "test_results.json", {
        "final_suites": {name: counts for name in controls.REQUIRED_SUITES},
        "commands": {"controls": {"exit_code": 0, "source_hashes": tested}}})
    plan.update(evidence_output=str(root), preflight_control_test_count=1,
        deterministic_test_results_sha256=controls.file_sha(root / "test_results.json"),
        source_hash_manifest_sha256=controls.file_sha(root / "source_hash_manifest.json"),
        preparation_source_sha256=manifest[str(ROOT / "scripts/phase8_2_1_prepare.py")],
        adapter_sha256=manifest[str(ROOT / "scripts/phase8_2_1_arm.py")])
    return root


def signed_plan(tmp_path):
    """Small synthetic plan uses fixed task/revisions and current control hashes."""
    old = json.loads((ROOT / "eval_results_phase8_2/20261025_131337_IST/experiment_plan.json").read_text())
    old.update(schema_version="8.2.1", experiment_id="control-test", run_root=str(tmp_path / "runs"),
               canonical_fixture=str(tmp_path / "master"), historical_roots=[str(tmp_path / "history")],
               execution_files={n: controls.file_sha(ROOT / "scripts" / n) for n in runner.EXECUTION_FILES},
               model_prompt_file=str(tmp_path / "prompt.txt"), model_prompt_sha256=controls.sha(b"prompt"))
    (tmp_path / "runs").mkdir()
    (tmp_path / "history").mkdir()
    (tmp_path / "master").mkdir()
    (tmp_path / "prompt.txt").write_bytes(b"prompt")
    (tmp_path / "master/x").write_bytes(b"fixture")
    old["fixture_hashes"] = {"x": controls.sha(b"fixture"), "tests/test_router.py": "a" * 64}
    (tmp_path / "master/tests").mkdir()
    (tmp_path / "master/tests/test_router.py").write_bytes(b"test")
    old["fixture_hashes"]["tests/test_router.py"] = controls.sha(b"test")
    old["oracle"]["test_sha256"] = controls.sha(b"test")
    for arm in ("A", "B"):
        source = tmp_path / ("source_" + arm); source.mkdir()
        (source / "x.py").write_bytes(b"frozen")
        old["arms"][arm].update(source_export=str(source), source_files={"x.py": {"sha256": controls.sha(b"frozen")}},
                                 run_output=str(tmp_path / "runs" / arm))
    for tree in [tmp_path / "master", tmp_path / "source_A", tmp_path / "source_B"]:
        for p in tree.rglob("*"):
            if p.is_file(): p.chmod(stat.S_IREAD)
    bind_test_evidence(old, tmp_path)
    old["plan_sha256"] = controls.plan_digest(old)
    return old


def test_default_and_public_child_are_inert(tmp_path):
    for args in ([], ["--child"], ["--internal-worker"], ["--run"]):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/phase8_2_1_arm.py"), *args],
                                input="", capture_output=True, text=True, timeout=10)
        assert result.returncode != 0
    assert not list(tmp_path.iterdir())


def test_direct_child_without_authorization_rejected_before_import(tmp_path):
    plan = signed_plan(tmp_path)
    path = tmp_path / "plan.json"; path.write_text(json.dumps(plan))
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/phase8_2_1_arm.py"),
        "--internal-worker", "--plan", str(path), "--arm", "A"], input="{}\n",
        capture_output=True, text=True, timeout=10)
    assert result.returncode != 0 and "authorization rejected" in result.stderr
    assert not (tmp_path / "runs/A").exists()
    assert "torch" not in result.stderr


@pytest.mark.parametrize("change", ["task", "revision", "output", "overlap", "digest", "code", "budget"])
def test_arbitrary_or_drifted_plan_parameters_fail_closed(tmp_path, change):
    plan = signed_plan(tmp_path)
    if change == "task": plan["task_id"] = "arbitrary"
    if change == "revision": plan["arms"]["A"]["revision"] = "0" * 40
    if change == "output": plan["arms"]["A"]["run_output"] = str(tmp_path / "other")
    if change == "overlap": plan["arms"]["A"]["run_output"] = plan["canonical_fixture"]
    if change == "code": plan["execution_files"]["phase8_2_1_arm.py"] = "0" * 64
    if change == "budget": plan["limits"]["max_model_calls_per_arm"] = 2
    plan["plan_sha256"] = controls.plan_digest(plan)
    if change == "digest": plan["plan_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        runner.validate_plan(plan, plan["plan_sha256"], "A", check_environment=False)


@pytest.mark.parametrize("failure", ["missing", "stale", "token", "task", "revision", "output", "pid", "parent", "replay", "malformed"])
def test_internal_authorization_is_one_use_and_bound(tmp_path, failure):
    out = tmp_path / "A"; ctx = context(out)
    owner = controls.claim(out, ctx)
    token = controls.authorize(out, owner, 123, lifetime=30)
    expected = dict(ctx)
    now = None
    if failure == "missing": token = ""
    if failure == "stale": now = 10**20
    if failure == "token": token = "f" * 64
    if failure in ("task", "revision", "output"):
        expected[{"task": "task_id", "revision": "revision", "output": "output"}[failure]] = "arbitrary"
    if failure == "malformed": token = None
    kwargs = dict(pid=124 if failure == "pid" else 123,
                  parent_pid=999 if failure == "parent" else os.getpid(), now=now)
    if failure == "replay":
        controls.consume_authorization(out, expected, token, **kwargs)
    with pytest.raises(PermissionError, match="authorization rejected"):
        controls.consume_authorization(out, expected, token, **kwargs)


def test_valid_authorization_does_not_log_token(tmp_path):
    out = tmp_path / "A"; ctx = context(out)
    owner = controls.claim(out, ctx); token = controls.authorize(out, owner, 123)
    assert controls.consume_authorization(out, ctx, token, pid=123, parent_pid=os.getpid())["run_id"] == owner["run_id"]
    assert all(token not in p.read_text() for p in (out / "control").iterdir())


def test_parent_approval_precedes_claim_and_supervision(tmp_path, monkeypatch):
    path = tmp_path / "plan.json"; plan = {"plan_sha256": "a" * 64}
    path.write_text(json.dumps(plan)); output = tmp_path / "A"
    monkeypatch.setattr(runner, "validate_plan", lambda *a, **k: context(output))
    starts = []
    def supervisor(): starts.append(True); raise AssertionError("must not start")
    with pytest.raises(PermissionError, match="approval"):
        runner.run_parent(path, "a" * 64, "A", confirm=lambda _: "", supervisor_factory=supervisor)
    assert not starts and not output.exists()


def test_existing_output_is_not_overwritten(tmp_path, monkeypatch):
    path = tmp_path / "plan.json"; path.write_text('{"plan_sha256":"a"}')
    output = tmp_path / "A"; output.mkdir(); marker = output / "prior.json"; marker.write_bytes(b"original")
    monkeypatch.setattr(runner, "validate_plan", lambda *a, **k: context(output))
    with pytest.raises(FileExistsError): runner.run_parent(path, "a", "A")
    with pytest.raises(FileExistsError): controls.claim(output, context(output))
    assert marker.read_bytes() == b"original" and list(output.iterdir()) == [marker]


def test_checkpoint_precedes_review_and_patch_apply(tmp_path):
    ev = evidence(tmp_path); policy = SimpleNamespace(patch_approved=False)
    session = SimpleNamespace(current_diff="fixed proposal", current_patch_hash=controls.sha(b"fixed proposal"))
    applied = []
    def approve(**kwargs):
        assert policy.patch_approved
        applied.append(kwargs); return True
    session.approve = approve; session.reject = lambda: pytest.fail("unexpected reject")
    initial = {"passed": False, "exit_code": 1}
    ctx = {"fixture_hashes": {"file": "hash"}, "prompt_sha256": "prompt", "initial_oracle": initial}
    def request(checkpoint, proposal):
        assert not applied and not policy.patch_approved
        saved = [json.loads(p.read_text()) for p in tmp_path.glob("event_*.json")]
        assert checkpoint in saved
        assert checkpoint["initial_oracle"] == initial and checkpoint["task_id"] == controls.TASK
        assert (tmp_path / "proposed_patch.txt").read_bytes() == b"fixed proposal"
        return session.current_patch_hash
    assert controls.review_proposal(session, ev, policy, ctx, request)
    assert len(applied) == 1


def test_rejected_patch_cannot_unlock_fixture(tmp_path):
    ev = evidence(tmp_path); policy = SimpleNamespace(patch_approved=False); rejected = []
    s = SimpleNamespace(current_diff="proposal", current_patch_hash=controls.sha(b"proposal"),
        approve=lambda **k: pytest.fail("must not apply"), reject=lambda: rejected.append(True))
    assert not controls.review_proposal(s, ev, policy, {}, lambda *a: "")
    assert rejected and not policy.patch_approved
    assert len(list(tmp_path.glob("event_*.json"))) == 2


@pytest.mark.parametrize("exc,expected", [(KeyboardInterrupt(), "cancelled"), (RuntimeError("API failed"), "execution_exception"),
    (TimeoutError("wall limit"), "timeout"), (ChildProcessError("exit 2"), "child_failure"),
    (subprocess.TimeoutExpired("fixed", 30), "timeout")])
def test_terminal_states_preserve_original_exception_and_prior_evidence(tmp_path, exc, expected):
    ev = evidence(tmp_path); ev.artifact("raw_response.txt", b"prior bytes")
    with pytest.raises(type(exc)) as caught:
        with controls.lifecycle(ev): raise exc
    assert caught.value is exc
    assert json.loads((tmp_path / "terminal.json").read_text())["status"] == expected
    assert (tmp_path / "raw_response.txt").read_bytes() == b"prior bytes"
    before = controls.tree_hashes(tmp_path)
    ev.finalize("timeout", error="second timeout")
    ev.finalize("completed", functional_repair=True)
    assert controls.tree_hashes(tmp_path) == before


def test_storage_failure_does_not_swallow_cancellation(tmp_path, monkeypatch):
    ev = evidence(tmp_path); exc = KeyboardInterrupt()
    monkeypatch.setattr(ev, "finalize", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(KeyboardInterrupt) as caught:
        with controls.lifecycle(ev): raise exc
    assert caught.value is exc


def test_cross_arm_and_protected_writes_rejected_in_real_guarded_child(tmp_path):
    own, other, protected, ev = [tmp_path / n for n in ("A", "B", "frozen", "evidence")]
    for p in (own, other, protected, ev): p.mkdir()
    (own / "fixture/micro_http").mkdir(parents=True)
    (own / "fixture/micro_http/router.py").write_text("frozen fixture")
    for p in (other / "x.txt", protected / "x.txt", ev / "existing.json"): p.write_text("untouched")
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tests/phase8_2_1_control_child.py"),
        "policy", str(own), str(protected), str(other), str(ev)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert set(json.loads(result.stdout).values()) == {"rejected"}
    assert all(Path(p).read_bytes() == b for p, b in before.items())
    assert (own / "own.txt").read_text() == "allowed"


def test_path_traversal_and_overlap_are_rejected(tmp_path):
    with pytest.raises(ValueError): controls.canonical(tmp_path / "A/../B/file")
    with pytest.raises(ValueError): controls.disjoint([tmp_path / "A", tmp_path / "A/nested"])
    with pytest.raises(ValueError): controls.canonical(tmp_path / "file:stream")


def test_hardlink_alias_rejected(tmp_path):
    target = tmp_path / "target"; target.write_text("original")
    alias = tmp_path / "alias"; os.link(target, alias)
    with pytest.raises(ValueError, match="Hardlink"): controls.canonical(alias)
    assert target.read_text() == "original"


def test_symlink_alias_rejected_where_supported(tmp_path):
    target = tmp_path / "target"; target.mkdir()
    alias = tmp_path / "alias"
    try: alias.symlink_to(target, target_is_directory=True)
    except OSError as exc: pytest.skip("OS does not permit test symlink: " + str(exc))
    with pytest.raises(ValueError, match="alias"): controls.canonical(alias / "file")


def test_frozen_hashes_and_modes_remain_unchanged(tmp_path):
    plan = signed_plan(tmp_path)
    roots = [Path(v["source_export"]) for v in plan["arms"].values()] + [Path(plan["canonical_fixture"])]
    before = {str(r): controls.tree_hashes(r) for r in roots}
    runner.validate_plan(plan, plan["plan_sha256"], "A", check_environment=False)
    policy = controls.WritePolicy(tmp_path / "runs/A")
    for r in roots:
        with pytest.raises(PermissionError): policy.check(next(p for p in r.rglob("*") if p.is_file()))
        assert controls.tree_hashes(r) == before[str(r)]
    runner.verify_protected(plan)


def test_supervisor_owns_fixed_dummy_process_before_it_runs(tmp_path):
    supervisor = controls.Supervisor()
    assert os.name != "nt" or supervisor.job
    try:
        process = supervisor.launch([sys.executable, "-B", str(ROOT / "tests/phase8_2_1_control_child.py"), "ready"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert process.stdout.readline().strip() == "READY"
    finally: supervisor.close()
    supervisor.close()
    assert process.poll() is not None


def test_one_model_boundary_call_and_raw_error_preserved(tmp_path):
    ev = evidence(tmp_path); budget = runner.GenerationBudget(ev); calls = []
    def fake(prompt, **kwargs): calls.append(kwargs); return "unparseable fixed response"
    assert budget.boundary("prompt", controls.sha(b"prompt"), fake) == "unparseable fixed response"
    with pytest.raises(ValueError): budget.boundary("prompt", controls.sha(b"prompt"), fake)
    assert calls == [{"max_new_tokens": 768}]
    assert (tmp_path / "raw_response.txt").read_text() == "unparseable fixed response"


def test_real_generate_budget_is_pre_call_and_rejects_769(tmp_path):
    budget = runner.GenerationBudget(evidence(tmp_path))
    class Tensor:
        shape = (1, 3)
        def cpu(self): return self
        def numpy(self): return self
        def tobytes(self): return b"fixed token ids"
    calls = []
    def fake(**kwargs):
        calls.append(True)
        events = [json.loads(p.read_text()) for p in tmp_path.glob("event_*.json")]
        assert any(e["status"] == "generation_started" and e["actual_model_calls"] == 1 for e in events)
        return Tensor()
    kwargs = dict(input_ids=Tensor(), max_new_tokens=769, do_sample=False, repetition_penalty=1.1)
    with pytest.raises(ValueError): budget.generate(fake, (), kwargs)
    assert not calls and budget.real_calls == 0
    kwargs["max_new_tokens"] = 768
    budget.generate(fake, (), kwargs)
    with pytest.raises(RuntimeError): budget.generate(fake, (), kwargs)
    assert len(calls) == 1 and budget.real_calls == 1


def test_oracle_and_review_required_for_success():
    done = {"state": "completed"}
    assert runner.classify(done, {"passed": False, "exit_code": 1}, True, False, True, True) == "functional_failure"
    assert runner.classify(done, {"passed": True, "exit_code": 0}, True, False, True, True) == "functional_success"
    assert runner.classify(done, {"passed": True, "exit_code": 0}, False, True, True, True) == "inconclusive_review_rejected"


def test_python_network_and_subprocess_guards_are_fail_closed(tmp_path):
    policy = controls.WritePolicy(tmp_path)
    for event, args in (("socket.connect", (None, ("example.invalid", 443))),
                        ("socket.getaddrinfo", ("example.invalid", 443)),
                        ("subprocess.Popen", ("python", ["python", "arbitrary"], None, None))):
        with pytest.raises(PermissionError): policy.audit(event, args)


@pytest.mark.parametrize("mode", ["complete", "cancel", "timeout", "child_failure", "cleanup_failure", "post_audit_cancel",
    "empty_interrupt", "audit_read_error", "review_deadline", "invalid_review", "late_review", "silent_deadline", "watchdog_failure"])
def test_parent_supervision_authorization_and_terminal_audit_with_fixed_double(tmp_path, monkeypatch, mode):
    plan = signed_plan(tmp_path)
    path = tmp_path / "plan.json"; path.write_text(json.dumps(plan))
    original_validate = runner.validate_plan
    monkeypatch.setattr(runner, "validate_plan", lambda p, s, a: original_validate(p, s, a, check_environment=False))
    output = tmp_path / "runs/A"
    before = {n: controls.tree_hashes(tmp_path / n) for n in ("source_A", "source_B", "master")}
    order = []
    closed = threading.Event()
    fast_modes = {"review_deadline", "silent_deadline", "watchdog_failure"}
    if mode in fast_modes:
        original_timer = threading.Timer
        monkeypatch.setattr(runner.threading, "Timer", lambda interval, fn: original_timer(.05, fn))
    interrupted = KeyboardInterrupt("fixed cancellation")
    if mode in ("post_audit_cancel", "empty_interrupt", "audit_read_error"):
        original_verify = runner.verify_protected
        calls = []
        def verify(p):
            calls.append(True)
            if len(calls) > 1:
                if mode == "empty_interrupt": raise KeyboardInterrupt()
                if mode == "audit_read_error": raise OSError()
                raise interrupted
            return original_verify(p)
        monkeypatch.setattr(runner, "verify_protected", verify)
    class Process:
        pid = 123
        stdin = io.StringIO()
        def poll(self): return 1 if closed.is_set() else None
        def wait(self, timeout=None): return 7 if mode == "child_failure" else 0
    class FakeSupervisor:
        def __init__(self):
            assert (output / "control/owner.json").exists()
            order.append("supervision")
        def launch(self, argv, **kwargs):
            assert order == ["approval", "supervision"]
            assert not (output / "control/authorization.json").exists()
            order.append("launch")
            child_ev = controls.Evidence(output / "evidence", runner.identity(plan, "A"))
            patch = "fixed review text"; patch_hash = controls.sha(patch.encode())
            child_ev.artifact("proposed_patch.txt", patch.encode())
            cp = child_ev.event("awaiting_patch_review", proposal_sha256=patch_hash,
                fixture_hashes=plan["fixture_hashes"], prompt_sha256=plan["model_prompt_sha256"],
                initial_oracle={"passed": False, "exit_code": 1})
            child_ev.finalize("completed", actual_model_calls=0, functional_repair=None)
            process = Process()
            if mode == "timeout":
                class TimedOut:
                    def __iter__(self): raise subprocess.TimeoutExpired("fixed dummy", 300)
                process.stdout = TimedOut()
            elif mode == "silent_deadline":
                def stall():
                    assert closed.wait(2)
                    return
                    yield "unreachable"
                process.stdout = stall()
            else:
                process.stdout = io.StringIO(runner.PROTOCOL + json.dumps({"kind": "patch_review", "checkpoint": cp, "proposal": patch}) + "\n")
            return process
        def close(self):
            order.append("closed")
            closed.set()
            if mode in ("cleanup_failure", "watchdog_failure"): raise OSError("fixed cleanup failure")
    def confirm(prompt, **kwargs):
        if not order:
            order.append("approval"); return plan["plan_sha256"]
        assert (output / "control/authorization.json").exists()
        assert "launch" in order
        if mode in ("cancel", "empty_interrupt"): raise interrupted
        if mode == "invalid_review": return ""
        if mode == "late_review": kwargs["stop"].set()
        if mode in ("review_deadline", "watchdog_failure"):
            read_fd, write_fd = os.pipe()
            try:
                with os.fdopen(read_fd, "rb", buffering=0) as stream:
                    return controls.BoundedInput(stream)(prompt, **kwargs)
            finally:
                os.close(write_fd)
        return controls.sha(b"fixed review text")  # inert double; no patch/session exists
    if mode == "complete":
        runner.run_parent(path, plan["plan_sha256"], "A", confirm=confirm, supervisor_factory=FakeSupervisor)
    else:
        expected = {"cancel": KeyboardInterrupt, "timeout": subprocess.TimeoutExpired,
                    "child_failure": ChildProcessError, "cleanup_failure": OSError,
                    "post_audit_cancel": KeyboardInterrupt, "empty_interrupt": KeyboardInterrupt,
                    "audit_read_error": OSError, "review_deadline": TimeoutError, "invalid_review": PermissionError,
                    "late_review": TimeoutError, "silent_deadline": TimeoutError, "watchdog_failure": TimeoutError}[mode]
        with pytest.raises(expected) as caught:
            runner.run_parent(path, plan["plan_sha256"], "A", confirm=confirm, supervisor_factory=FakeSupervisor)
        if mode in ("cancel", "post_audit_cancel", "empty_interrupt"): assert caught.value is interrupted
    terminal = json.loads((output / "control/terminal.json").read_text())
    assert terminal["status"] == {"complete": "completed", "cancel": "cancelled", "timeout": "timeout",
                                 "child_failure": "child_failure", "cleanup_failure": "integrity_or_cleanup_failure",
                                 "post_audit_cancel": "cancelled", "empty_interrupt": "cancelled",
                                 "audit_read_error": "integrity_or_cleanup_failure", "review_deadline": "timeout",
                                 "invalid_review": "execution_exception", "late_review": "timeout",
                                 "silent_deadline": "timeout", "watchdog_failure": "timeout"}[mode]
    audits = [json.loads(p.read_text()) for p in (output / "control").glob("event_*.json")]
    final = next(e for e in audits if e["status"] == "post_run_audit")
    assert final["protected_after_verified"] is (mode not in ("post_audit_cancel", "empty_interrupt", "audit_read_error"))
    if mode in ("empty_interrupt", "audit_read_error"):
        assert final["protected_audit"]["error"]["message"] == ""
        assert final["protected_audit"]["error"]["error_type"] == ("KeyboardInterrupt" if mode == "empty_interrupt" else "OSError")
        assert final["protected_audit_status"] == ("interrupted" if mode == "empty_interrupt" else "read_error")
    if mode in fast_modes | {"invalid_review", "late_review", "cancel", "empty_interrupt"}:
        assert not any(e["status"] == "patch_confirmation_dispatched" for e in audits)
    if mode == "watchdog_failure":
        assert any(e["stage"] == "watchdog_cleanup" for e in final["cleanup_errors"])
    assert final["actual_model_calls_started"] == 0
    assert order[-1] == "closed" and not (tmp_path / "runs/B").exists()
    assert all(controls.tree_hashes(tmp_path / n) == values for n, values in before.items())


def test_guarded_oracle_transport_reproduces_canonical_slug_assertion(tmp_path):
    # Copies trusted, pre-existing canonical bytes only; never starts an arm.
    old = ROOT / "eval_results_phase8_2/20261025_131337_IST"
    plan = json.loads((old / "experiment_plan.json").read_text())
    fixture = tmp_path / "fixture"; fixture.mkdir(); (tmp_path / "tmp").mkdir()
    source = old / "arms/A/probe_native_pinned/fixture"
    for rel in plan["fixture_hashes"]:
        p = fixture / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((source / rel).read_bytes())
    before = controls.tree_hashes(fixture)
    result = runner.run_guarded_tests(runner.guarded_test_argv(fixture, plan), fixture)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 failed, 1 passed" in result.stdout and "test_slug_with_hyphen" in result.stdout, result.stderr
    assert controls.tree_hashes(fixture) == before == plan["fixture_hashes"]


@pytest.mark.skipif(os.name != "nt", reason="Windows path aliases only")
@pytest.mark.parametrize("name", ["NUL", "file.", "file ", "COM1.txt"])
def test_windows_device_and_trailing_aliases_rejected(tmp_path, name):
    with pytest.raises(ValueError, match="alias"):
        controls.canonical(tmp_path / name)


def test_model_exception_keeps_error_and_no_second_call(tmp_path):
    ev = evidence(tmp_path); budget = runner.GenerationBudget(ev); exc = RuntimeError("fixed model API exception")
    def fail(*a, **k): raise exc
    with pytest.raises(RuntimeError) as caught:
        budget.boundary("prompt", controls.sha(b"prompt"), fail)
    assert caught.value is exc
    with pytest.raises(ValueError): budget.boundary("prompt", controls.sha(b"prompt"), fail)
    events = [json.loads(p.read_text()) for p in tmp_path.glob("event_*.json")]
    assert any(e["status"] == "model_boundary_error" and e["error"] == str(exc) for e in events)


def test_second_arm_rejects_cancelled_prior_terminal(tmp_path, monkeypatch):
    plan = signed_plan(tmp_path)
    path = tmp_path / "plan.json"; path.write_text(json.dumps(plan))
    original_validate = runner.validate_plan
    monkeypatch.setattr(runner, "validate_plan", lambda p, s, a: original_validate(p, s, a, check_environment=False))
    confirmations = []
    def declined(_): confirmations.append(True); return ""
    with pytest.raises(PermissionError, match="Arm A terminal"):
        runner.run_parent(path, plan["plan_sha256"], "B", confirm=declined)
    assert not confirmations and not (tmp_path / "runs/B").exists()
    # A cancelled first arm cannot reach B's approval or ownership gate.
    out = tmp_path / "runs/A"; ctx = runner.identity(plan, "A")
    controls.claim(out, ctx)
    controls.Evidence(out / "control", ctx).finalize("cancelled", functional_repair=None)
    with pytest.raises(PermissionError, match="Arm A terminal"):
        runner.run_parent(path, plan["plan_sha256"], "B", confirm=declined)
    assert not confirmations and not (tmp_path / "runs/B").exists()


def test_launch_cleanup_failure_preserves_original_exception(monkeypatch):
    exc = RuntimeError("fixed launch failure")
    supervisor = controls.Supervisor()
    original_close = supervisor.close
    def fail_launch(*a, **k): raise exc
    def fail_close(): raise OSError("fixed secondary cleanup error")
    monkeypatch.setattr(controls.subprocess, "Popen", fail_launch)
    monkeypatch.setattr(supervisor, "close", fail_close)
    try:
        with pytest.raises(RuntimeError) as caught: supervisor.launch(["fixed dummy"])
        assert caught.value is exc
    finally: original_close()


def test_testworker_timeout_survives_secondary_cleanup_error(tmp_path, monkeypatch):
    exc = subprocess.TimeoutExpired("fixed dummy", 30)
    class FakeSupervisor:
        def launch(self, *a, **k):
            def communicate(**kwargs): raise exc
            return SimpleNamespace(communicate=communicate)
        def close(self): raise OSError("fixed cleanup failure")
    monkeypatch.setattr(runner, "Supervisor", FakeSupervisor)
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        runner.run_guarded_tests(["fixed dummy"], tmp_path)
    assert caught.value is exc


@pytest.mark.parametrize("boundary", [True, False])
def test_generation_error_logging_failure_cannot_replace_cancellation(tmp_path, monkeypatch, boundary):
    ev = evidence(tmp_path); budget = runner.GenerationBudget(ev); exc = KeyboardInterrupt("fixed cancellation")
    original_event = ev.event
    def event(status, **kwargs):
        if status in ("model_boundary_error", "generation_error"): raise OSError("secondary evidence failure")
        return original_event(status, **kwargs)
    monkeypatch.setattr(ev, "event", event)
    def fail(*a, **k): raise exc
    class Tensor:
        shape = (1, 1)
        def cpu(self): return self
        def numpy(self): return self
        def tobytes(self): return b"fixed ids"
    with pytest.raises(KeyboardInterrupt) as caught:
        with controls.lifecycle(ev):
            if boundary: budget.boundary("prompt", controls.sha(b"prompt"), fail)
            else: budget.generate(fail, (), dict(input_ids=Tensor(), max_new_tokens=768, do_sample=False, repetition_penalty=1.1))
    assert caught.value is exc
    assert json.loads((tmp_path / "terminal.json").read_text())["status"] == "cancelled"


# --- Phase E4 Regression Tests (AUTH-01 through AUTH-07) ---


def _write_auth_child_helper(path):
    code = """
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import phase8_2_1_controls as controls

output = Path(sys.argv[2])
expected = json.loads(sys.argv[3])
now_override = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] != "None" else None

line = sys.stdin.readline(8192)
token = json.loads(line)["authorization"]
owner = controls.consume_authorization(output, expected, token, now=now_override)
print(f"AUTH_OK_PID:{os.getpid()}", flush=True)
"""
    path.write_text(code.strip(), encoding="utf-8")


def test_auth01_direct_worker_launch_fails_closed(tmp_path):
    """AUTH-01: Direct worker launch without private pipe / token fails closed."""
    plan = signed_plan(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/phase8_2_1_arm.py"),
                            "--internal-worker", "--plan", str(plan_path), "--arm", "A"],
                            input="", capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert "PermissionError" in result.stderr or "authorization rejected" in result.stderr
    assert not (tmp_path / "runs/A").exists()


def test_auth02_windows_venv_trampoline_handshake_success(tmp_path):
    """AUTH-02: Real subprocess launch via venv launcher under Job Object succeeds."""
    child_py = tmp_path / "child_auth.py"
    _write_auth_child_helper(child_py)
    output = tmp_path / "runs/A"; output.parent.mkdir(parents=True, exist_ok=True)
    ctx = {"experiment_id": "test_auth02", "arm": "A", "task_id": controls.TASK}
    owner = controls.claim(output, ctx)

    supervisor = controls.Supervisor()
    argv = [sys.executable, "-B", str(child_py), str(ROOT / "scripts"), str(output), json.dumps(ctx), "None"]
    proc = supervisor.launch(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    token = controls.authorize(output, owner, proc.pid)
    proc.stdin.write(json.dumps({"authorization": token}) + "\n")
    proc.stdin.flush()
    stdout, stderr = proc.communicate(timeout=10)
    supervisor.close()

    assert proc.returncode == 0, f"Child failed: {stderr}"
    assert "AUTH_OK_PID:" in stdout
    consumed_file = output / "control/authorization_consumed.json"
    assert consumed_file.exists()
    consumed = json.loads(consumed_file.read_text(encoding="utf-8"))
    assert consumed["run_id"] == owner["run_id"]
    if os.name == "nt":
        assert consumed["windows_trampoline"] is True
        assert consumed["launcher_pid"] == proc.pid
        assert consumed["parent_pid"] == os.getpid()
        assert consumed["authentication_path"] == "windows_verified_trampoline"


def test_auth03_tampered_parent_or_child_identity_rejected(tmp_path):
    """AUTH-03: Tampered parent/child PID in authorization record fails closed."""
    child_py = tmp_path / "child_auth.py"
    _write_auth_child_helper(child_py)
    output = tmp_path / "runs/A"; output.parent.mkdir(parents=True, exist_ok=True)
    ctx = {"experiment_id": "test_auth03", "arm": "A", "task_id": controls.TASK}
    owner = controls.claim(output, ctx)

    supervisor = controls.Supervisor()
    argv = [sys.executable, "-B", str(child_py), str(ROOT / "scripts"), str(output), json.dumps(ctx), "None"]
    proc = supervisor.launch(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    token = controls.authorize(output, owner, proc.pid)

    # Tamper parent_pid to an unrelated PID
    auth_path = output / "control/authorization.json"
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    auth["parent_pid"] = 999999
    auth_path.write_text(json.dumps(auth), encoding="utf-8")

    proc.stdin.write(json.dumps({"authorization": token}) + "\n")
    proc.stdin.flush()
    stdout, stderr = proc.communicate(timeout=10)
    supervisor.close()

    assert proc.returncode != 0
    assert not (output / "control/authorization_consumed.json").exists()


def test_auth04_trampoline_outside_job_object_rejected(tmp_path):
    """AUTH-04: Worker spawned outside supervisory Job Object fails closed."""
    child_py = tmp_path / "child_auth.py"
    _write_auth_child_helper(child_py)
    output = tmp_path / "runs/A"; output.parent.mkdir(parents=True, exist_ok=True)
    ctx = {"experiment_id": "test_auth04", "arm": "A", "task_id": controls.TASK}
    owner = controls.claim(output, ctx)

    # Spawn directly without Supervisor (outside Job Object)
    argv = [sys.executable, "-B", str(child_py), str(ROOT / "scripts"), str(output), json.dumps(ctx), "None"]
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    token = controls.authorize(output, owner, proc.pid, job_name="Local\\FakeJobNonExistent_9999")
    proc.stdin.write(json.dumps({"authorization": token}) + "\n")
    proc.stdin.flush()
    stdout, stderr = proc.communicate(timeout=10)
    proc.kill()

    assert proc.returncode != 0
    assert not (output / "control/authorization_consumed.json").exists()


def test_auth05_expired_and_reused_token_rejected(tmp_path):
    """AUTH-05: Expired token (>30s) and second consumption attempt are rejected."""
    child_py = tmp_path / "child_auth.py"
    _write_auth_child_helper(child_py)
    output = tmp_path / "runs/A"; output.parent.mkdir(parents=True, exist_ok=True)
    ctx = {"experiment_id": "test_auth05", "arm": "A", "task_id": controls.TASK}
    owner = controls.claim(output, ctx)

    # 1. Test expired token
    supervisor = controls.Supervisor()
    argv = [sys.executable, "-B", str(child_py), str(ROOT / "scripts"), str(output), json.dumps(ctx), str(10**20)]
    proc = supervisor.launch(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    token = controls.authorize(output, owner, proc.pid)
    proc.stdin.write(json.dumps({"authorization": token}) + "\n")
    proc.stdin.flush()
    stdout, stderr = proc.communicate(timeout=10)
    supervisor.close()
    assert proc.returncode != 0
    assert not (output / "control/authorization_consumed.json").exists()

    # 2. Test replay attempt
    consumed_file = output / "control/authorization_consumed.json"
    controls.exclusive_json(consumed_file, {"run_id": owner["run_id"]})
    supervisor2 = controls.Supervisor()
    argv2 = [sys.executable, "-B", str(child_py), str(ROOT / "scripts"), str(output), json.dumps(ctx), "None"]
    proc2 = supervisor2.launch(argv2, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc2.stdin.write(json.dumps({"authorization": token}) + "\n")
    proc2.stdin.flush()
    stdout2, stderr2 = proc2.communicate(timeout=10)
    supervisor2.close()
    assert proc2.returncode != 0


def test_auth06_forged_context_or_token_hash_mismatch(tmp_path):
    """AUTH-06: Altered token hash or context field mismatch fails closed."""
    child_py = tmp_path / "child_auth.py"
    _write_auth_child_helper(child_py)
    output = tmp_path / "runs/A"; output.parent.mkdir(parents=True, exist_ok=True)
    ctx = {"experiment_id": "test_auth06", "arm": "A", "task_id": controls.TASK}
    owner = controls.claim(output, ctx)

    supervisor = controls.Supervisor()
    argv = [sys.executable, "-B", str(child_py), str(ROOT / "scripts"), str(output), json.dumps(ctx), "None"]
    proc = supervisor.launch(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    token = controls.authorize(output, owner, proc.pid)

    # Tamper token_sha256 in authorization.json
    auth_path = output / "control/authorization.json"
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    auth["token_sha256"] = "0" * 64
    auth_path.write_text(json.dumps(auth), encoding="utf-8")

    proc.stdin.write(json.dumps({"authorization": token}) + "\n")
    proc.stdin.flush()
    stdout, stderr = proc.communicate(timeout=10)
    supervisor.close()

    assert proc.returncode != 0
    assert not (output / "control/authorization_consumed.json").exists()


def test_auth07_worker_crash_and_timeout_cleanup(tmp_path):
    """AUTH-07: Worker timeout triggers Job Object termination and clean shutdown."""
    child_py = tmp_path / "sleep_child.py"
    child_py.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    supervisor = controls.Supervisor()
    argv = [sys.executable, "-B", str(child_py)]
    proc = supervisor.launch(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(0.5)
    supervisor.close()  # Terminate entire Job Object tree
    code = proc.wait(timeout=5)
    assert code is not None


def test_popen01_authorized_windows_string_command_accepted(tmp_path):
    """POPEN-01: Authorized Windows string-form command line generated by subprocess.list2cmdline is accepted."""
    sub_argv = [sys.executable, "-B", str(tmp_path / "pytest.py"), str(tmp_path / "fixture"), "a" * 64]
    policy = controls.WritePolicy(tmp_path, subprocess_argv=sub_argv)
    win_cmd = subprocess.list2cmdline(sub_argv)

    # Accepted with executable=None (standard Popen behavior on Windows)
    policy.audit("subprocess.Popen", (None, win_cmd, str(tmp_path), None))

    # Accepted with explicit executable matching sub_argv[0]
    policy.audit("subprocess.Popen", (sub_argv[0], win_cmd, str(tmp_path), None))


def test_popen02_altered_windows_command_rejected(tmp_path):
    """POPEN-02: Altered Windows command line is rejected fail-closed."""
    sub_argv = [sys.executable, "-B", str(tmp_path / "pytest.py"), str(tmp_path / "fixture"), "a" * 64]
    policy = controls.WritePolicy(tmp_path, subprocess_argv=sub_argv)
    win_cmd = subprocess.list2cmdline(sub_argv)

    # Added argument
    with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
        policy.audit("subprocess.Popen", (None, win_cmd + " --unauthorized-flag", str(tmp_path), None))

    # Changed test target
    altered_argv = [sys.executable, "-B", str(tmp_path / "pytest.py"), str(tmp_path / "fixture"), "b" * 64]
    with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
        policy.audit("subprocess.Popen", (None, subprocess.list2cmdline(altered_argv), str(tmp_path), None))


def test_popen03_arbitrary_executable_or_command_rejected(tmp_path):
    """POPEN-03: Arbitrary executable or command is rejected."""
    sub_argv = [sys.executable, "-B", str(tmp_path / "pytest.py"), str(tmp_path / "fixture"), "a" * 64]
    policy = controls.WritePolicy(tmp_path, subprocess_argv=sub_argv)
    win_cmd = subprocess.list2cmdline(sub_argv)

    # Mismatched executable redirect
    with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
        policy.audit("subprocess.Popen", ("cmd.exe", win_cmd, str(tmp_path), None))

    # Arbitrary command string
    with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
        policy.audit("subprocess.Popen", (None, "powershell.exe -Command Get-Process", str(tmp_path), None))

    # Arbitrary sequence
    with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
        policy.audit("subprocess.Popen", ("malicious.exe", ["malicious.exe"], None, None))


def test_popen04_posix_sequence_form_authorized_accepted(tmp_path):
    """POPEN-04: POSIX sequence-form authorized arguments remain accepted."""
    sub_argv = [sys.executable, "-B", str(tmp_path / "pytest.py"), str(tmp_path / "fixture"), "a" * 64]
    policy = controls.WritePolicy(tmp_path, subprocess_argv=sub_argv)

    # List sequence
    policy.audit("subprocess.Popen", (None, list(sub_argv), str(tmp_path), None))

    # Tuple sequence
    policy.audit("subprocess.Popen", (None, tuple(sub_argv), str(tmp_path), None))

    # Explicit matching executable
    policy.audit("subprocess.Popen", (sub_argv[0], list(sub_argv), str(tmp_path), None))


def test_popen05_unsupported_argument_types_and_absent_auth_fail_closed(tmp_path):
    """POPEN-05: Unsupported argument types and absent authorization fail closed."""
    sub_argv = [sys.executable, "-B", str(tmp_path / "pytest.py"), str(tmp_path / "fixture"), "a" * 64]

    # Absent authorization (subprocess_argv is None)
    no_auth_policy = controls.WritePolicy(tmp_path, subprocess_argv=None)
    with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
        no_auth_policy.audit("subprocess.Popen", (None, subprocess.list2cmdline(sub_argv), str(tmp_path), None))
    with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
        no_auth_policy.audit("subprocess.Popen", (None, sub_argv, str(tmp_path), None))

    # Unsupported argument types
    auth_policy = controls.WritePolicy(tmp_path, subprocess_argv=sub_argv)
    for invalid_cmd in (12345, None, {"command": "args"}, object()):
        with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
            auth_policy.audit("subprocess.Popen", (None, invalid_cmd, str(tmp_path), None))

    # Truncated args tuple
    with pytest.raises(PermissionError, match="Only the fixed guarded pytest worker may launch"):
        auth_policy.audit("subprocess.Popen", (None,))


def test_popen06_live_windows_subprocess_popen_audit_integration(tmp_path):
    """POPEN-06: Live subprocess.Popen execution under active sys.audit on Windows."""
    child_script = tmp_path / "audit_test_child.py"
    child_code = """
import sys, subprocess, os
sys.path.insert(0, os.environ["CONTROLS_DIR"])
from phase8_2_1_controls import WritePolicy

test_cmd = [sys.executable, "-c", "print('AUDIT_OK')"]
policy = WritePolicy(sys.argv[1], subprocess_argv=test_cmd)
sys.addaudithook(policy.audit)

# Authorized execution must succeed
proc = subprocess.Popen(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, _ = proc.communicate(timeout=10)
assert proc.returncode == 0
assert "AUDIT_OK" in stdout

# Unauthorized execution must be blocked by the audit hook
try:
    subprocess.Popen([sys.executable, "-c", "print('SHOULD_FAIL')"])
    sys.exit(2)
except PermissionError:
    pass

sys.exit(0)
"""
    child_script.write_text(child_code, encoding="utf-8")
    env = dict(os.environ, CONTROLS_DIR=str(ROOT / "scripts"))
    proc = subprocess.Popen([sys.executable, "-B", str(child_script), str(tmp_path)],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(timeout=15)
    assert proc.returncode == 0, f"Child failed: {stderr}\\n{stdout}"


def test_devnull01_legitimate_devnull_open_accepted(tmp_path):
    """DEVNULL-01: Legitimate os.devnull open operations (e.g. dill/torch probing) are accepted."""
    policy = controls.WritePolicy(tmp_path)

    # Mode 'r+b' (flags: O_RDWR) as used by dill._dill.get_file_type
    policy.audit("open", (os.devnull, "r+", os.O_RDWR))

    # Mode 'w' (flags: O_WRONLY | O_CREAT) discard sink
    policy.audit("open", (os.devnull, "w", os.O_WRONLY | os.O_CREAT))


def test_devnull02_ordinary_writes_outside_workspace_remain_denied(tmp_path):
    """DEVNULL-02: Ordinary writes outside workspace remain strictly denied."""
    policy = controls.WritePolicy(tmp_path)
    outside_file = tmp_path.parent / "escape_attempt.txt"

    with pytest.raises(PermissionError, match="Write outside owned arm workspace"):
        policy.audit("open", (str(outside_file), "w", os.O_WRONLY | os.O_CREAT))

    with pytest.raises(PermissionError, match="Write outside owned arm workspace"):
        policy.audit("open", (str(outside_file), "r+", os.O_RDWR))


def test_devnull03_lookalike_paths_denied(tmp_path):
    """DEVNULL-03: Lookalike paths and aliases are denied; only canonical os.devnull is permitted."""
    policy = controls.WritePolicy(tmp_path)

    for lookalike in ("nul.txt", "NUL.DAT", "nul_file", tmp_path.parent / "nul.txt"):
        with pytest.raises((PermissionError, ValueError)):
            policy.audit("open", (str(lookalike), "w", os.O_WRONLY | os.O_CREAT))


def test_devnull04_non_open_operations_on_devnull_denied(tmp_path):
    """DEVNULL-04: Non-open operations (remove, truncate, chmod, rename) on os.devnull remain denied."""
    policy = controls.WritePolicy(tmp_path)

    with pytest.raises(PermissionError, match="Write outside owned arm workspace"):
        policy.audit("os.remove", (os.devnull,))

    with pytest.raises(PermissionError, match="Write outside owned arm workspace"):
        policy.audit("os.truncate", (os.devnull,))

    with pytest.raises(PermissionError, match="Write outside owned arm workspace"):
        policy.audit("os.chmod", (os.devnull, 0o777))

    with pytest.raises(PermissionError, match="Write outside owned arm workspace"):
        policy.audit("os.rename", (os.devnull, str(tmp_path / "renamed")))


def test_devnull05_live_dill_torch_import_under_audit_hook(tmp_path):
    """DEVNULL-05: Live dill and torch import succeeds under active WritePolicy audit hook on Windows."""
    tmp_dir = tmp_path / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    child_script = tmp_path / "devnull_import_child.py"
    child_code = """
import sys, os
sys.path.insert(0, os.environ["CONTROLS_DIR"])
from phase8_2_1_controls import WritePolicy

policy = WritePolicy(sys.argv[1])
sys.addaudithook(policy.audit)

# dill import opens os.devnull in 'r+b' mode; must succeed
import dill
import torch
print("IMPORT_OK")

# Unauthorized open outside workspace must still be blocked
outside_file = os.path.join(os.path.dirname(sys.argv[1]), "unauthorized.txt")
try:
    open(outside_file, "w")
    sys.exit(2)
except PermissionError:
    pass

sys.exit(0)
"""
    child_script.write_text(child_code, encoding="utf-8")
    env = dict(os.environ, CONTROLS_DIR=str(ROOT / "scripts"), TMP=str(tmp_dir), TEMP=str(tmp_dir))
    proc = subprocess.Popen([sys.executable, "-B", str(child_script), str(tmp_path)],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(timeout=25)
    assert proc.returncode == 0, f"Child failed: {stderr}\n{stdout}"
    assert "IMPORT_OK" in stdout


@pytest.mark.parametrize("case", ["matching", "test_mismatch", "manifest_mismatch", "missing_results", "missing_manifest",
    "missing_test_digest", "missing_manifest_digest", "bad_digest", "invalid_json", "array", "duplicate", "nan", "utf8",
    "missing_entry", "extra_entry", "bad_source_digest", "wrong_source_hash", "missing_tested_source", "bad_counts",
    "boolean_count", "failed_tests", "missing_suite", "bad_command", "contradictory_preparer", "source_read_error"])
def test_controller_binding_fail_closed_before_ownership(tmp_path, monkeypatch, case):
    plan = signed_plan(tmp_path)
    root = Path(plan["evidence_output"])
    results = root / "test_results.json"; manifest_path = root / "source_hash_manifest.json"
    manifest = controls.read_json(manifest_path); tests = controls.read_json(results)
    raw = None
    if case == "test_mismatch": plan["deterministic_test_results_sha256"] = "0" * 64
    elif case == "manifest_mismatch": plan["source_hash_manifest_sha256"] = "0" * 64
    elif case == "missing_results": results.unlink()
    elif case == "missing_manifest": manifest_path.unlink()
    elif case == "missing_test_digest": del plan["deterministic_test_results_sha256"]
    elif case == "missing_manifest_digest": del plan["source_hash_manifest_sha256"]
    elif case == "bad_digest": plan["source_hash_manifest_sha256"] = "xyz"
    elif case in ("invalid_json", "array", "duplicate", "nan", "utf8"):
        raw = {"invalid_json": b"{", "array": b"[]", "duplicate": b'{"x":1,"x":2}',
               "nan": b'{"x":NaN}', "utf8": b"\xff"}[case]
    elif case == "missing_entry": manifest.pop(next(iter(manifest)))
    elif case == "extra_entry": manifest[str(tmp_path / "foreign")] = "a" * 64
    elif case == "bad_source_digest": manifest[str(ROOT / "tests/test_phase8_2_1_hardening.py")] = "xyz"
    elif case == "wrong_source_hash": manifest[str(ROOT / "tests/test_phase8_2_1_hardening.py")] = "0" * 64
    elif case == "missing_tested_source": tests["commands"]["controls"]["source_hashes"].pop(next(iter(manifest)))
    elif case == "bad_counts": tests["final_suites"][controls.REQUIRED_SUITES[0]]["passed"] = 2
    elif case == "boolean_count": tests["final_suites"][controls.REQUIRED_SUITES[0]]["tests"] = True
    elif case == "failed_tests": tests["final_suites"][controls.REQUIRED_SUITES[0]].update(tests=2, failures=1)
    elif case == "missing_suite": tests["final_suites"].pop(controls.REQUIRED_SUITES[0])
    elif case == "bad_command": tests["commands"]["controls"]["exit_code"] = True
    elif case == "contradictory_preparer": plan["preparation_source_sha256"] = "0" * 64
    elif case == "source_read_error":
        original = controls.file_sha
        def fail(path):
            if Path(path) == ROOT / "tests/test_phase8_2_1_hardening.py": raise OSError()
            return original(path)
        monkeypatch.setattr(controls, "file_sha", fail)
    if case in ("missing_entry", "extra_entry", "bad_source_digest", "wrong_source_hash") or raw is not None:
        manifest_path.write_bytes(raw if raw is not None else json.dumps(manifest).encode())
        plan["source_hash_manifest_sha256"] = controls.sha(manifest_path.read_bytes())
    if case in ("missing_tested_source", "bad_counts", "boolean_count", "failed_tests", "missing_suite", "bad_command"):
        results.write_text(json.dumps(tests))
        plan["deterministic_test_results_sha256"] = controls.sha(results.read_bytes())
    plan["plan_sha256"] = controls.plan_digest(plan)
    if case == "matching":
        controls.verify_bound_evidence(plan)
        assert runner.validate_plan(plan, plan["plan_sha256"], "A", check_environment=False)["arm"] == "A"
        return
    path = tmp_path / "synthetic-plan.json"; path.write_text(json.dumps(plan))
    validate = runner.validate_plan
    monkeypatch.setattr(runner, "validate_plan", lambda p, s, a: validate(p, s, a, check_environment=False))
    def forbidden(*a, **k): pytest.fail("Evidence rejection must precede approval/ownership/launch")
    monkeypatch.setattr(runner, "claim", forbidden)
    with pytest.raises((ValueError, OSError, KeyError)):
        runner.run_parent(path, plan["plan_sha256"], "A", confirm=forbidden, supervisor_factory=forbidden)
    assert not (tmp_path / "runs/A").exists()


@pytest.mark.parametrize("kind,status", [(None, "verified"), ("mismatch", "mismatch"),
    ("interrupt", "interrupted"), ("read", "read_error")])
def test_controller_integrity_outcomes(tmp_path, kind, status):
    path = tmp_path / "protected.txt"; path.write_bytes(b"before")
    expected = {"protected.txt": controls.sha(b"before")}
    if kind == "mismatch": path.write_bytes(b"after")
    def verify():
        if kind == "interrupt": raise KeyboardInterrupt()
        if kind == "read": raise OSError()
        controls.verify_tree(tmp_path, expected)
    result = controls.protected_audit(verify)
    assert result["status"] == status and result["verified"] is (kind is None)
    if kind in ("interrupt", "read"):
        assert result["error"]["message"] == ""
        assert result["error"]["error_type"] == ("KeyboardInterrupt" if kind == "interrupt" else "OSError")
        assert result["error"]["repr"] and result["error"]["traceback"]


def write_completed_a(plan, category="functional_failure", change=None, missing_worker=False):
    output = Path(plan["arms"]["A"]["run_output"])
    controls.claim(output, runner.identity(plan, "A"))
    success = category == "functional_success"
    worker = dict(runner.identity(plan, "A"), status="completed", classification=category, functional_repair=success,
        initial_oracle={"passed": False, "exit_code": 1}, final_oracle={"passed": success, "exit_code": 0 if success else 1},
        oracle_files_unchanged=True, proposal_approved=success, session={"state": "completed" if success else "failed"})
    parent = dict(runner.identity(plan, "A"), status="completed", protected_after_verified=True,
        protected_audit_status="verified", cleanup_errors=[], worker_terminal=worker,
        termination={"process_exit_code": 0, "process_exit_observed_at": controls.timestamp(),
                     "job_active_processes": 0, "job_closed_at": controls.timestamp()})
    if change: change(parent, worker)
    if not missing_worker: controls.exclusive_json(output / "evidence/terminal.json", worker)
    controls.exclusive_json(output / "control/terminal.json", parent)


@pytest.mark.parametrize("case", ["success", "failure", "cancelled", "timeout", "inconclusive", "missing_worker",
    "missing_audit", "audit_failed", "cleanup_error", "unknown", "worker_rejected", "foreign_worker", "foreign_parent",
    "embedded_drift", "bad_oracle", "boolean_exit", "oracle_changed", "contradictory_outcome", "malformed_worker",
    "missing_termination", "worker_still_active", "failed_passing_completed", "unapproved_success"])
def test_controller_arm_b_prerequisite(tmp_path, case):
    plan = signed_plan(tmp_path)
    def change(parent, worker):
        if case in ("cancelled", "timeout", "unknown"): parent["status"] = case
        elif case == "inconclusive": worker["classification"] = "inconclusive_execution_error"
        elif case == "missing_audit": parent.pop("protected_after_verified")
        elif case == "audit_failed": parent["protected_audit_status"] = "interrupted"
        elif case == "cleanup_error": parent["cleanup_errors"] = [{"error_type": "OSError"}]
        elif case == "worker_rejected": worker["status"] = "review_rejected"
        elif case == "foreign_worker": worker["plan_sha256"] = "0" * 64
        elif case == "foreign_parent": parent["revision"] = controls.REVISIONS["B"]
        elif case == "embedded_drift": parent["worker_terminal"] = dict(worker, status="other")
        elif case == "bad_oracle": worker["final_oracle"]["exit_code"] = 2
        elif case == "boolean_exit": worker["final_oracle"]["exit_code"] = True
        elif case == "oracle_changed": worker["oracle_files_unchanged"] = False
        elif case == "contradictory_outcome": worker["functional_repair"] = True
        elif case == "missing_termination": parent.pop("termination")
        elif case == "worker_still_active": parent["termination"]["process_exit_code"] = 259
        elif case == "failed_passing_completed":
            worker["session"]["state"] = "completed"; worker["final_oracle"] = {"passed": True, "exit_code": 0}
        elif case == "unapproved_success": worker["proposal_approved"] = False
    write_completed_a(plan, "functional_success" if case in ("success", "unapproved_success") else "functional_failure", change,
                      missing_worker=case == "missing_worker")
    if case == "malformed_worker":
        (Path(plan["arms"]["A"]["run_output"]) / "evidence/terminal.json").write_bytes(b'[]')
    if case in ("success", "failure"):
        runner.require_completed_arm_a(plan)
    else:
        with pytest.raises(PermissionError, match="Arm A terminal"):
            runner.require_completed_arm_a(plan)
    assert not (tmp_path / "runs/B").exists()


@pytest.mark.parametrize("case", ["shared_lines", "no_input", "eof", "oversized", "non_ascii", "cancel", "late", "text_mode_cr"])
def test_controller_native_input_pipe(case, monkeypatch):
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "rb", buffering=0)
    try:
        if case == "text_mode_cr" and os.name == "nt":
            import msvcrt
            msvcrt.setmode(read_fd, os.O_TEXT)
        reader = controls.BoundedInput(stream)
        if case == "shared_lines":
            os.write(write_fd, b"first\r\nsecond\n")
            assert reader("", deadline=time.monotonic() + 1) == "first"
            assert reader("", deadline=time.monotonic() + 1) == "second"
            return
        if case == "eof": os.close(write_fd); write_fd = None
        elif case == "oversized": os.write(write_fd, b"a" * 129 + b"\n")
        elif case == "non_ascii": os.write(write_fd, b"\xff\n")
        elif case == "cancel": os.write(write_fd, b"\x03")
        elif case == "text_mode_cr": os.write(write_fd, b"abc\r")
        elif case == "late":
            def late(timeout): time.sleep(.04); return "\n"
            monkeypatch.setattr(reader, "_poll_character", late)
        expected = {"no_input": TimeoutError, "eof": EOFError, "oversized": PermissionError,
                    "non_ascii": UnicodeError, "cancel": KeyboardInterrupt, "late": TimeoutError,
                    "text_mode_cr": TimeoutError}[case]
        started = time.monotonic()
        with pytest.raises(expected): reader("", deadline=started + .03)
        assert time.monotonic() - started < 1
    finally:
        stream.close()
        if write_fd is not None: os.close(write_fd)


def test_controller_input_rejects_disk_stream(tmp_path):
    path = tmp_path / "input.txt"; path.write_bytes(b"0" * 64 + b"\n")
    with path.open("rb") as stream:
        with pytest.raises(PermissionError): controls.BoundedInput(stream)


@pytest.mark.skipif(os.name != "nt", reason="Native Windows input dispatch")
@pytest.mark.parametrize("case", ["editing", "cancel", "eof", "extended"])
def test_controller_windows_console_key_dispatch(case):
    # Scripted keys exercise the native-console branch without touching the user's console.
    values = iter({"editing": "ab\bc\r", "cancel": "\x03", "eof": "\x1a", "extended": "\xe0"}[case])
    reader = object.__new__(controls.BoundedInput)
    reader.console = True
    reader.msvcrt = SimpleNamespace(kbhit=lambda: True, getwch=lambda: next(values))
    if case == "editing": assert reader("", deadline=time.monotonic() + 1) == "ac"
    else:
        with pytest.raises({"cancel": KeyboardInterrupt, "eof": EOFError, "extended": PermissionError}[case]):
            reader("", deadline=time.monotonic() + 1)


@pytest.mark.skipif(os.name != "nt", reason="Native Windows API errors")
def test_controller_windows_pipe_api_error():
    import ctypes
    read_fd, write_fd = os.pipe()
    with os.fdopen(read_fd, "rb", buffering=0) as stream:
        try:
            reader = controls.BoundedInput(stream)
            def fail(*args): ctypes.set_last_error(5); return 0
            reader.kernel = SimpleNamespace(PeekNamedPipe=fail)
            with pytest.raises(OSError): reader("", deadline=time.monotonic() + 1)
        finally: os.close(write_fd)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job containment")
def test_controller_job_closes_worker_and_descendant():
    import ctypes
    import queue
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]; kernel.OpenProcess.restype = w.HANDLE
    kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]; kernel.WaitForSingleObject.restype = w.DWORD
    kernel.CloseHandle.argtypes = [w.HANDLE]
    supervisor = controls.Supervisor(); handles = []
    code = "import subprocess,sys,os,time; p=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(30)'],creationflags=subprocess.CREATE_NO_WINDOW); print(os.getpid(),p.pid,flush=True); time.sleep(30)"
    process = supervisor.launch([sys.executable, "-B", "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ready = queue.Queue()
    thread = threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True); thread.start()
    try:
        pids = [int(value) for value in ready.get(timeout=5).split()]
        assert len(pids) == 2
        for pid in pids:
            handle = kernel.OpenProcess(0x100000 | 0x1000, False, pid)
            assert handle; handles.append(handle)
        result = supervisor.close()
        assert result["job_active_processes"] == 0 and result["process_exit_code"] is not None
        assert result["job_empty_observed_at"] and result["process_exit_observed_at"]
        assert all(kernel.WaitForSingleObject(handle, 0) == 0 for handle in handles)
        assert supervisor.close()["process_exit_code"] == result["process_exit_code"]
    finally:
        supervisor.close(); thread.join(timeout=1)
        for handle in handles: kernel.CloseHandle(handle)
        process.stdout.close(); process.stderr.close()


@pytest.mark.parametrize("arrival,stop,alive", [(.999, False, True), (1.0, False, True),
    (1.001, False, True), (.999, True, True), (.999, False, False)])
def test_controller_input_deadline_boundary(monkeypatch, arrival, stop, alive):
    now = [0.0]; flag = threading.Event(); running = [True]
    monkeypatch.setattr(controls, "time", SimpleNamespace(monotonic=lambda: now[0]))
    reader = object.__new__(controls.BoundedInput); reader.console = False
    values = iter("a" * 64 + "\n")
    def poll(timeout):
        value = next(values)
        if value == "\n":
            now[0] = arrival; running[0] = alive
            if stop: flag.set()
        return value
    reader._poll_character = poll
    if arrival < 1 and not stop and alive:
        assert reader("", deadline=1, stop=flag, alive=lambda: running[0]) == "a" * 64
    else:
        with pytest.raises(TimeoutError if arrival >= 1 or stop else ChildProcessError):
            reader("", deadline=1, stop=flag, alive=lambda: running[0])


@pytest.mark.skipif(os.name != "nt", reason="Checked Windows cleanup APIs")
@pytest.mark.parametrize("operation", ["CloseHandle", "TerminateJobObject", "QueryInformationJobObject"])
def test_controller_native_cleanup_errors_are_not_success(monkeypatch, operation):
    import ctypes
    supervisor = controls.Supervisor()
    try:
        with monkeypatch.context() as m:
            def fail(*args): ctypes.set_last_error(5); return 0
            m.setattr(supervisor.kernel, operation, fail)
            with pytest.raises(OSError): supervisor.close()
            if operation == "CloseHandle":
                assert supervisor.job is not None  # preserve ownership so cleanup can retry
                assert supervisor.termination["job_close_error"]["error_type"]
            else:
                assert supervisor.job is None  # independent checked close still runs
    finally:
        supervisor.close()
    assert supervisor.job is None


@pytest.mark.skipif(os.name != "nt", reason="Native controller/Job/pipe integration")
@pytest.mark.parametrize("mode", ["timeout", "cancel", "valid", "malformed", "eof"])
def test_controller_native_parent_cleanup(tmp_path, monkeypatch, mode):
    """The launched child is inert Python transport code, never the experiment worker."""
    plan = signed_plan(tmp_path)
    path = tmp_path / "synthetic-plan.json"; path.write_text(json.dumps(plan))
    output = tmp_path / "runs/A"
    original_validate = runner.validate_plan
    monkeypatch.setattr(runner, "validate_plan", lambda p, s, a: original_validate(p, s, a, check_environment=False))
    original_timer = threading.Timer
    monkeypatch.setattr(runner.threading, "Timer", lambda interval, fn: original_timer(1.5, fn))
    proposal = "inert native controller transport fixture"
    patch_hash = controls.sha(proposal.encode())
    instances = []
    class InertSupervisor(controls.Supervisor):
        def __init__(self): super().__init__(); instances.append(self)
        def launch(self, ignored_experiment_argv, **kwargs):
            ev = controls.Evidence(output / "evidence", runner.identity(plan, "A"))
            ev.artifact("proposed_patch.txt", proposal.encode())
            cp = ev.event("awaiting_patch_review", proposal_sha256=patch_hash)
            if mode == "valid": ev.finalize("completed", actual_model_calls=0, functional_repair=None)
            request = runner.PROTOCOL + json.dumps({"kind": "patch_review", "checkpoint": cp, "proposal": proposal})
            code = ("import subprocess,sys,json,time; "
                "p=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(30)'], "
                "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW); "
                "sys.stdin.readline(); print(" + repr(request) + ",flush=True); "
                "answer=json.loads(sys.stdin.readline()); "
                "sys.exit(0 if answer.get('patch_sha256')==" + repr(patch_hash) + " else 2)")
            return super().launch([sys.executable, "-B", "-c", code], **kwargs)
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "rb", buffering=0)
    reader = controls.BoundedInput(stream)
    def confirm(prompt, **kwargs):
        nonlocal write_fd
        if not kwargs: return plan["plan_sha256"]
        if mode == "cancel": os.write(write_fd, b"\x03")
        elif mode == "valid": os.write(write_fd, patch_hash.encode() + b"\n")
        elif mode == "malformed": os.write(write_fd, b"not-an-approval\n")
        elif mode == "eof": os.close(write_fd); write_fd = None
        return reader(prompt, **kwargs)
    try:
        if mode == "valid":
            runner.run_parent(path, plan["plan_sha256"], "A", confirm=confirm, supervisor_factory=InertSupervisor)
        else:
            with pytest.raises({"timeout": TimeoutError, "cancel": KeyboardInterrupt,
                                "malformed": PermissionError, "eof": EOFError}[mode]):
                runner.run_parent(path, plan["plan_sha256"], "A", confirm=confirm, supervisor_factory=InertSupervisor)
        records = [controls.read_json(p) for p in (output / "control").glob("event_*.json")]
        audit = next(e for e in records if e["status"] == "post_run_audit")
        assert audit["protected_audit_status"] == "verified" and audit["cleanup_errors"] == []
        termination = audit["termination"]
        assert termination["job_active_processes"] == 0 and termination["job_closed_at"]
        assert termination["process_exit_code"] is not None and termination["process_exit_observed_at"]
        assert len(termination["member_exits"]) >= 1  # includes the still-running dummy descendant
        assert all(e["state"] in ("exited", "already_gone") for e in termination["member_exits"].values())
        assert any(e["status"] == "patch_confirmation_dispatched" for e in records) is (mode == "valid")
        terminal = controls.read_json(output / "control/terminal.json")
        assert terminal["status"] == {"timeout": "timeout", "cancel": "cancelled", "valid": "completed",
                                      "malformed": "execution_exception", "eof": "execution_exception"}[mode]
        if mode != "valid": assert terminal["phase"] == "patch_review"
        assert not (tmp_path / "runs/B").exists()
    finally:
        stream.close()
        if write_fd is not None: os.close(write_fd)
        for instance in instances: instance.close()
