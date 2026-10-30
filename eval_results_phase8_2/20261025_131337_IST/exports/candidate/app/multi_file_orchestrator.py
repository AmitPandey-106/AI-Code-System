"""Bounded sequential engineering with explicit per-proposal approval."""
import ast
import difflib
import os
import threading
import uuid
from pathlib import Path
from app.engineering_loop import EngineeringSession, EngineeringState as S
from app.file_transaction import FileTransaction, RepositoryLease, safe_path, digest
from app.project_test_runner import project_test_runner


class MultiFileOrchestrationResult:
    def __init__(self, success, task_prompt, target_files, completed_files, failed_file=None,
                 error=None, rolled_back=False, step_results=None, **evidence):
        self.success, self.task_prompt = success, task_prompt
        self.target_files, self.completed_files = target_files, completed_files
        self.failed_file, self.error, self.rolled_back = failed_file, error, rolled_back
        self.step_results = step_results or []
        self.evidence = evidence

    def to_dict(self):
        return {k: v for k, v in vars(self).items() if k != "evidence"} | self.evidence


class MultiFileEngineeringOrchestrator:
    def __init__(self, repo_root, test_command, fallback_enabled=None, repo_index_enabled=None,
                 prompt_example_enabled=None, memory_enabled=None, strategy_enabled=None,
                 storage_dir=None, approval_callback=None, targeted_commands=None, max_files=8, verifier=None):
        self.repo_root = os.path.realpath(repo_root)
        self.test_command = test_command
        self.options = dict(fallback_enabled=fallback_enabled, repo_index_enabled=repo_index_enabled,
            prompt_example_enabled=prompt_example_enabled, memory_enabled=memory_enabled,
            strategy_enabled=strategy_enabled, storage_dir=storage_dir)
        self.approval_callback = approval_callback
        self.verifier = verifier
        self.targeted_commands = targeted_commands or {}
        self.max_files = min(max(1, max_files), 20)
        self._cancel = threading.Event()
        self._active = None
        self._running = threading.Lock()

    def cancel(self):
        self._cancel.set()
        if self._active:
            self._active.cancel()

    def _plan(self, target_files):
        if not target_files or len(target_files) > self.max_files:
            raise ValueError("PlanError: empty plan or file budget exceeded")
        targets = [p.replace("\\", "/") for p in target_files]
        if len(set(targets)) != len(targets):
            raise ValueError("PlanError: duplicate targets")
        modules = {str(Path(p).with_suffix("")).replace("\\", ".").replace("/", "."): p for p in targets}
        dependencies = {p: set() for p in targets}
        for rel in targets:
            path = safe_path(self.repo_root, rel)
            if path.exists() and rel.endswith(".py"):
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
                for node in ast.walk(tree):
                    imports = ([node.module] if isinstance(node, ast.ImportFrom) else
                               [a.name for a in node.names] if isinstance(node, ast.Import) else [])
                    dependencies[rel].update(modules[m] for m in imports if m in modules and modules[m] != rel)
        ordered = []
        remaining = set(targets)
        while remaining:
            ready = sorted(p for p in remaining if not (dependencies[p] & remaining))
            if not ready:
                # Cycles have no topological order; make the deterministic fallback visible.
                ready = [min(remaining)]
            ordered.extend(ready)
            remaining.difference_update(ready)
        return ordered, {k: sorted(v) for k, v in dependencies.items()}

    def execute_plan(self, task_prompt, target_files):
        steps, completed, sessions = [], [], []
        tx = None
        failed_file = None
        final_tests = verification = None
        final_diff = ""
        dependencies = {}
        mutation_count = 0
        lease = RepositoryLease(self.repo_root, "multi-" + str(uuid.uuid4()))
        if not self._running.acquire(blocking=False):
            return MultiFileOrchestrationResult(False, task_prompt, target_files, [], error="Orchestrator already running")
        try:
            targets, dependencies = self._plan(target_files)
            if self.approval_callback is None:
                raise ValueError("ApprovalRequired: supply an explicit per-proposal approval callback")
            for command in [self.test_command, *self.targeted_commands.values()]:
                if not project_test_runner.is_command_allowed(command):
                    raise ValueError("SecurityViolation: test command not approved")
            if not set(self.targeted_commands).issubset(targets):
                raise ValueError("PlanError: targeted test references an unplanned file")
            if not lease.acquire():
                raise ValueError("Repository reserved by another transaction")
            tx = FileTransaction(self.repo_root, targets)
            for i, target in enumerate(targets):
                failed_file = target
                if self._cancel.is_set():
                    raise ValueError("Cancelled")
                tx.verify()
                session = EngineeringSession(
                    f"{task_prompt}\nCURRENT STEP: {i+1}/{len(targets)}\nTARGET FILE TO EDIT: {target}\nModify ONLY {target}.",
                    self.repo_root, self.test_command, eager_policy_check=True,
                    allowed_targets=[target], **self.options)
                sessions.append(session)
                self._active = session
                session._lease = lease
                session.step()
                status = session.get_status()
                steps.append({"file": target, "status": status, "patch": session.current_diff,
                              "patch_hash": session.current_patch_hash, "fallback_used": session.fallback_used})
                if status["state"] != S.AWAITING_APPROVAL:
                    raise ValueError(f"Step failed: {status['error_message']}")
                if self.approval_callback(status) is not True:
                    raise ValueError("ApprovalRejected")
                if self._cancel.is_set():
                    raise ValueError("Cancelled")
                tx.verify()
                if not session.approve(status["current_patch_hash"]):
                    raise ValueError(f"Application failed: {session.error_message}")
                tx.adopt({k: digest(v) for k, v in session._transaction.expected.items()} | {k: digest(v) for k, v in tx.expected.items() if k != target})
                tx.created_dirs.extend(session._transaction.created_dirs)
                mutation_count += 1
                completed.append(target)
                if target in self.targeted_commands:
                    result = project_test_runner.run_tests(self.repo_root, self.targeted_commands[target], cancel_event=self._cancel)
                    steps[-1]["targeted_tests"] = result
                    if not result["success"]:
                        raise ValueError(f"Targeted tests failed: {result}")
            failed_file = "final_verification"
            final_tests = project_test_runner.run_tests(self.repo_root, self.test_command, cancel_event=self._cancel)
            if not final_tests["success"]:
                raise ValueError(f"Final tests failed: {final_tests['error']}")
            tx.verify()
            verification = (self.verifier(self.repo_root, {"state": S.VERIFYING, "step_results": steps}) if self.verifier
                            else project_test_runner.run_tests(self.repo_root, self.test_command, cancel_event=self._cancel))
            if not verification["success"] or self._cancel.is_set():
                raise ValueError("Independent verification failed or cancelled")
            tx.verify()
            final_diff = "".join("".join(difflib.unified_diff((tx.original[rel] or b"").decode("utf-8").splitlines(True),
                (tx.expected[rel] or b"").decode("utf-8").splitlines(True), fromfile="a/"+rel, tofile="b/"+rel)) for rel in targets)
            for session in sessions:
                session.current_test_results = final_tests
                session.verification_results = verification
                session._transition(S.TESTING)
                session._transition(S.VERIFYING)
                session._record_learning(True)
                session._transaction = None
                session._transition(S.COMPLETED)
            for step, session in zip(steps, sessions):
                step["status"] = session.get_status()
            return MultiFileOrchestrationResult(True, task_prompt, targets, completed,
                step_results=steps, final_diff=final_diff, test_results=final_tests,
                verification_results=verification, dependencies=dependencies, mutation_count=mutation_count)
        except Exception as exc:
            rolled_back = tx.rollback() if tx else False
            errors = tx.rollback_errors if tx else []
            for session in sessions:
                session._transaction = None  # Outer transaction owns cleanup and evidence.
                session._fail("rollback_failure" if errors else "multi_file_failure", str(exc))
            for step, session in zip(steps, sessions):
                step["status"] = session.get_status()
            return MultiFileOrchestrationResult(False, task_prompt, target_files, completed,
                failed_file=failed_file, error=str(exc), rolled_back=rolled_back, step_results=steps,
                rollback_errors=errors, test_results=final_tests, verification_results=verification,
                final_diff=final_diff, dependencies=dependencies, mutation_count=mutation_count,
                original_hashes={k: digest(v) for k, v in tx.original.items()} if tx else {})
        finally:
            self._active = None
            lease.release()
            self._running.release()
