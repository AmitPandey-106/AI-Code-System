"""Explicit, approval-gated engineering graph. Public Phase 8 states remain valid."""
import ast
import copy
import hashlib
import json
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from app.repo_index import get_repo_indexer
from app.patch_engine import PatchEngine
from app.project_test_runner import project_test_runner
from app.file_transaction import FileTransaction, RepositoryLease, safe_path, digest, read_bytes


def generate_raw(prompt):
    # Keep model dependencies lazy so deterministic engineering works offline.
    from app.model import generate_raw as generate
    return generate(prompt)


class EngineeringState:
    RECEIVED = "received"
    INSPECTING = "inspecting"
    PLANNING = "planning"
    GENERATING = "generating"
    PATCH_PROPOSED = "patch_proposed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPLYING = "applying"
    PATCH_APPLIED = "patch_applied"
    TESTING = "testing"
    DIAGNOSING = "diagnosing"
    RETRY_PLANNING = "retry_planning"
    ROLLING_BACK = "rolling_back"
    VERIFYING = "verifying"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


S = EngineeringState
TERMINAL = {S.COMPLETED, S.FAILED, S.CANCELLED}
TRANSITIONS = {
    S.RECEIVED: {S.INSPECTING}, S.INSPECTING: {S.PLANNING},
    S.PLANNING: {S.GENERATING}, S.GENERATING: {S.PATCH_PROPOSED, S.RETRY_PLANNING},
    S.PATCH_PROPOSED: {S.AWAITING_APPROVAL, S.RETRY_PLANNING},
    S.AWAITING_APPROVAL: {S.APPLYING}, S.APPLYING: {S.PATCH_APPLIED, S.ROLLING_BACK},
    S.PATCH_APPLIED: {S.TESTING, S.ROLLING_BACK},
    S.TESTING: {S.VERIFYING, S.DIAGNOSING, S.ROLLING_BACK},
    S.VERIFYING: {S.COMPLETED, S.DIAGNOSING, S.ROLLING_BACK},
    S.DIAGNOSING: {S.ROLLING_BACK}, S.ROLLING_BACK: {S.RETRY_PLANNING},
    S.RETRY_PLANNING: {S.INSPECTING}, S.CANCELLING: {S.ROLLING_BACK},
}
for _state in list(TRANSITIONS):
    TRANSITIONS[_state].update({S.FAILED, S.CANCELLING, S.CANCELLED})


def setting(explicit, env, key, default=False):
    from app.config import config
    if explicit is not None:
        return bool(explicit)
    if env in os.environ:
        return os.environ[env].lower() in ("true", "1")
    return bool(config.get(key, default))


class EngineeringSession:
    def __init__(self, task_prompt, repo_root, test_command, fallback_enabled=None,
                 eager_policy_check=None, repo_index_enabled=None, prompt_example_enabled=None,
                 memory_enabled=None, strategy_enabled=None, storage_dir=None,
                 max_attempts=3, verifier=None, allowed_targets=None, test_timeout=None):
        self.session_id = str(uuid.uuid4())
        self.task_prompt = task_prompt
        self.repo_root = os.path.realpath(repo_root)
        self.test_command = test_command
        self.state = S.RECEIVED
        self.fallback_enabled = setting(fallback_enabled, "LITECODER_FALLBACK_SYNTHESIZER", "FALLBACK_SYNTHESIZER_ENABLED")
        self.eager_policy_check = setting(eager_policy_check, "LITECODER_EAGER_POLICY_CHECK", "EAGER_POLICY_CHECK_ENABLED")
        self.repo_index_enabled = setting(repo_index_enabled, "LITECODER_REPO_INDEX", "REPO_INDEX_ENABLED", True)
        self.prompt_example_enabled = setting(prompt_example_enabled, "LITECODER_PROMPT_EXAMPLE", "PROMPT_EXAMPLE_ENABLED", True)
        self.memory_enabled = setting(memory_enabled, "LITECODER_MEMORY_ENABLED", "MEMORY_ENABLED")
        self.strategy_enabled = setting(strategy_enabled, "LITECODER_STRATEGY_ENABLED", "STRATEGY_LEARNING_ENABLED")
        from app.config import config
        namespace = hashlib.sha256(json.dumps([self.repo_root, self.test_command,
            os.environ.get("LITECODER_MODEL_NAME") or config.get("MODEL_NAME", "Qwen/Qwen2.5-Coder-1.5B"),
            os.environ.get("LITECODER_MODEL_REVISION") or config.get("MODEL_REVISION"),
            self.fallback_enabled, self.repo_index_enabled, self.prompt_example_enabled,
            self.memory_enabled, self.strategy_enabled], sort_keys=True).encode()).hexdigest()[:24]
        self.storage_dir = os.path.join(storage_dir or "data/engineering", namespace)
        self.max_attempts = max(1, min(int(max_attempts), 10))
        self.current_attempt = 1
        self.history = []
        self.events = []
        self.warnings = []
        self.metrics = {"model_calls": 0, "model_duration_ms": 0, "started_at": time.time()}
        self.current_plan = self.current_diff = self.current_patch_hash = ""
        self.repository_context = ""
        self.edit_plan = {}
        self.source_file_hashes = {}
        self.current_test_results = None
        self.verification_results = None
        self.current_diagnosis = self.last_syntax_error = self.error_message = ""
        self.failure_category = "none"
        self.failure_context = {}
        self.policy_event = None
        self.fallback_used = False
        self.fallback_rejected_reason = ""
        self.selected_strategy = ""
        self.strategy_decision = {}
        self.strategy_history = []
        self.memory_retrieved_count = 0
        self.last_raw_response = ""
        self.rollback_result = None
        self.verifier = verifier
        self.test_timeout = test_timeout
        self.allowed_targets = set(allowed_targets) if allowed_targets is not None else None
        self._lock = threading.RLock()
        self._worker = threading.Lock()
        self._cancel_event = threading.Event()
        self._cancelled = False
        self._transaction = None
        self._lease = RepositoryLease(self.repo_root, self.session_id)
        self._seen_failures = set()
        self._proposal_validated = False
        self._selection_error_type = "test_failure"
        self._record_history()
        if not os.path.isdir(self.repo_root):
            self._fail("environment_failure", "Invalid repository root")
        elif self.eager_policy_check and not project_test_runner.is_command_allowed(test_command):
            self._policy_failure("session_init")

    def _transition(self, target, **event):
        with self._lock:
            if target not in TRANSITIONS.get(self.state, set()):
                raise ValueError(f"Invalid transition: {self.state} -> {target}")
            if target == S.AWAITING_APPROVAL and not self._proposal_validated:
                raise ValueError("Unvalidated proposal cannot reach approval")
            if target == S.COMPLETED and not (self.verification_results or {}).get("success"):
                raise ValueError("Unverified repair cannot complete")
            previous = self.state
            self.state = target
            self.events.append({"from": previous, "to": target, "attempt": self.current_attempt,
                                "timestamp": time.time(), **event})
            self._record_history()

    def get_status(self):
        with self._lock:
            return copy.deepcopy({"session_id": self.session_id, "state": self.state,
                "attempt": self.current_attempt, "max_attempts": self.max_attempts,
                "history": self.history, "events": self.events, "warnings": self.warnings,
                "metrics": self.metrics, "error_message": self.error_message,
                "failure_category": self.failure_category, "failure_context": self.failure_context,
                "policy_event": self.policy_event, "last_syntax_error": self.last_syntax_error,
                "current_plan": self.current_plan, "edit_plan": self.edit_plan, "current_diff": self.current_diff,
                "current_patch_hash": self.current_patch_hash, "fallback_used": self.fallback_used,
                "fallback_rejected_reason": self.fallback_rejected_reason,
                "selected_strategy": self.selected_strategy, "strategy_decision": self.strategy_decision,
                "strategy_history": self.strategy_history, "memory_retrieved_count": self.memory_retrieved_count,
                "test_results": self.current_test_results, "verification_results": self.verification_results,
                "rollback": self.rollback_result, "functional_success": self.state == S.COMPLETED,
                "outcome": "functional_repair" if self.state == S.COMPLETED else
                    ("cancelled" if self.state == S.CANCELLED else
                     ("safe_rejection" if self.failure_category == "policy_rejection" else self.state))})

    def _record_history(self):
        self.history.append(copy.deepcopy({"attempt": self.current_attempt, "state": self.state,
            "plan": self.current_plan, "diff": self.current_diff, "patch_hash": self.current_patch_hash,
            "diagnosis": self.current_diagnosis, "last_syntax_error": self.last_syntax_error,
            "test_results": self.current_test_results, "failure_category": self.failure_category,
            "policy_event": self.policy_event, "error_message": self.error_message, "timestamp": time.time()}))

    def _compute_file_hash(self, rel):
        return digest(read_bytes(safe_path(self.repo_root, rel)))

    def _model_call(self, prompt):
        started = time.monotonic()
        self.metrics["model_calls"] += 1
        try:
            return generate_raw(prompt)
        finally:
            self.metrics["model_duration_ms"] += int((time.monotonic() - started) * 1000)

    def _rollback(self):
        if self._transaction is None:
            self._lease.release()
            return True
        if self.state != S.ROLLING_BACK:
            self._transition(S.ROLLING_BACK)
        tx = self._transaction
        ok = tx.rollback()
        self.rollback_result = {"success": ok, "errors": tx.rollback_errors,
            "original_hashes": {k: digest(v) for k, v in tx.original.items()}}
        if ok:
            self._transaction = None
        self._lease.release()
        return ok

    def _fail(self, category, message):
        if self.state in TERMINAL:
            return
        if not self._rollback():
            category, message = "rollback_failure", str(self.rollback_result)
        self.failure_category, self.error_message = category, message
        self._transition(S.FAILED)

    def _policy_failure(self, stage):
        self.policy_event = {"event": "unapproved_command_rejected", "stage": stage,
            "command": self.test_command, "status": "unapproved_command"}
        self._fail("policy_rejection", f"SecurityViolation: Command not approved: {self.test_command}")

    def _finish_cancel(self):
        if self.state in TERMINAL:
            return
        if not self._rollback():
            self._fail("rollback_failure", str(self.rollback_result))
            return
        self.failure_category = "cancelled"
        self.error_message = "Cancelled by user."
        self._transition(S.CANCELLED)

    def _retry(self, category, message):
        self.failure_category = category
        self.failure_context = {"category": category, "error": message,
            "test_results": self.current_test_results, "changed_files": list(self.source_file_hashes),
            "source_hashes": dict(self.source_file_hashes), "strategies": list(self.strategy_history),
            "attempt": self.current_attempt}
        fingerprint = hashlib.sha256((self.current_diff + message).encode()).hexdigest()
        if self.current_attempt >= self.max_attempts:
            self._fail(category, f"Budget exhausted. {message}")
            return False
        if fingerprint in self._seen_failures:
            self.warnings.append("Repeated failure; remaining attempt budget applies")
        self._seen_failures.add(fingerprint)
        self.last_syntax_error = message
        self._transition(S.RETRY_PLANNING)
        self.current_attempt += 1
        self._proposal_validated = False
        self.fallback_used = False
        self._transition(S.INSPECTING)
        return True

    def step(self):
        if not self._worker.acquire(blocking=False):
            return self.state
        try:
            while self.state not in TERMINAL and self.state != S.AWAITING_APPROVAL:
                if self._cancel_event.is_set():
                    self._finish_cancel()
                    break
                if self.state == S.RECEIVED:
                    self._transition(S.INSPECTING)
                elif self.state == S.INSPECTING:
                    self.repository_context = self._do_inspecting()
                    if self._cancel_event.is_set():
                        continue
                    self._transition(S.PLANNING)
                elif self.state == S.PLANNING:
                    self.current_diff = ""
                    try:
                        plan, patch = self._do_planning()
                    except Exception as exc:
                        self._fail("model_generation_failure", f"Planning failed with exception: {exc}")
                        break
                    if self._cancel_event.is_set():
                        continue
                    self.current_plan, self.current_diff = plan, patch
                    if not patch:
                        self._retry("malformed_patch_syntax", "Model response contained no parseable SEARCH/REPLACE blocks or valid unified diff.")
                        continue
                    self._transition(S.PATCH_PROPOSED)
                elif self.state == S.PATCH_PROPOSED:
                    success, errors, hashes = self._do_patch_validation()
                    if not success and self.fallback_enabled and not self.fallback_used:
                        candidate = self._synthesize_single_function_fallback(self.last_raw_response)
                        if candidate:
                            self.current_diff = candidate
                            success, errors, hashes = self._do_patch_validation()
                            self.fallback_used = success
                    if not success:
                        message = "; ".join(errors)
                        if "SecurityViolation" in message:
                            self._fail("policy_rejection", message)
                        else:
                            category = "syntax_failure" if "SyntaxError" in message else (
                                "source_matching_failure" if "Match" in message or "NotFound" in message else "malformed_patch_syntax")
                            self._retry(category, f"Patch validation failed: {message}")
                        continue
                    self.source_file_hashes = hashes
                    self.edit_plan = {"targets": list(hashes), "source_hashes": dict(hashes),
                        "strategy": self.selected_strategy or "DIRECT_REPAIR", "test_command": self.test_command,
                        "approval_required": True, "attempt": self.current_attempt, "max_attempts": self.max_attempts}
                    self.current_patch_hash = hashlib.sha256(self.current_diff.encode()).hexdigest()
                    self.last_syntax_error = self.error_message = ""
                    self._proposal_validated = True
                    self._transition(S.AWAITING_APPROVAL)
                elif self.state == S.PATCH_APPLIED:
                    self._transition(S.TESTING)
                elif self.state == S.TESTING:
                    self.current_test_results = self._do_testing()
                    if self._cancel_event.is_set():
                        continue
                    result = self.current_test_results
                    if result.get("status") == "unapproved_command":
                        self._policy_failure("testing")
                    elif result.get("success"):
                        self._transition(S.VERIFYING)
                    else:
                        self._record_learning(False)
                        self._transition(S.DIAGNOSING)
                elif self.state == S.VERIFYING:
                    # A fresh invocation plus immutable-source checks, or a caller-supplied oracle.
                    self._transaction.verify()
                    self.verification_results = (self.verifier(self) if self.verifier else self._do_testing())
                    if self._cancel_event.is_set():
                        continue
                    if not self.verification_results.get("success"):
                        self.current_test_results = self.verification_results
                        self._record_learning(False)
                        self._transition(S.DIAGNOSING)
                        continue
                    self._transaction.verify()
                    self.failure_category = "none"
                    self.error_message = ""
                    self._record_learning(True)
                    self._transaction = None
                    self._lease.release()
                    self._transition(S.COMPLETED)
                elif self.state == S.DIAGNOSING:
                    self.current_diagnosis = self._do_diagnosing()
                    result = self.current_test_results or {}
                    category = "timeout" if result.get("timeout") else (
                        "environment_failure" if result.get("status") in ("error", "missing_executable", "invalid_directory") else "test_failure")
                    if not self._rollback():
                        self._fail("rollback_failure", str(self.rollback_result))
                    elif category in ("timeout", "environment_failure"):
                        self._fail(category, self.current_diagnosis)
                    else:
                        self._retry(category, self.current_diagnosis)
                else:
                    self._fail("internal_orchestration_error", f"No handler for state {self.state}")
        except Exception as exc:
            self._fail("stale_source" if "StaleSource" in str(exc) else "internal_orchestration_error", str(exc))
        finally:
            if self._cancel_event.is_set() and self.state not in TERMINAL:
                self._finish_cancel()
            self._worker.release()
        return self.state

    def approve(self, expected_patch_hash=None):
        if not self._worker.acquire(blocking=False):
            return False
        try:
            if self.state != S.AWAITING_APPROVAL or self._cancel_event.is_set():
                return False
            if not self._proposal_validated:
                self.error_message = "Unvalidated proposal cannot be approved"
                return False
            actual = hashlib.sha256(self.current_diff.encode()).hexdigest()
            if actual != self.current_patch_hash or (expected_patch_hash and actual != expected_patch_hash):
                self.error_message = "PatchHashMismatch: proposal changed or approval hash does not match"
                return False
            if not self._lease.acquire():
                self._fail("concurrent_session", "Repository is reserved by another engineering transaction")
                return False
            self._transition(S.APPLYING)
            self._transaction = FileTransaction(self.repo_root, self.source_file_hashes, self.source_file_hashes)
            res = PatchEngine(self.repo_root).apply_patch(self.current_diff, expected_hashes=self.source_file_hashes)
            if res["success"]:
                self._transaction.adopt(res["applied_file_hashes"])
                self._transaction.created_dirs.extend(safe_path(self.repo_root, d + "/.placeholder").parent for d in res.get("created_directories", []))
            if not res["success"]:
                self._fail("patch_application_failure", str(res["errors"]))
                return False
            self._transition(S.PATCH_APPLIED)
            return True
        except Exception as exc:
            self._fail("stale_source" if "StaleSource" in str(exc) else "patch_application_failure", str(exc))
            return False
        finally:
            if self._cancel_event.is_set():
                self._finish_cancel()
            self._worker.release()

    def reject(self):
        if self.state != S.AWAITING_APPROVAL:
            return False
        self.cancel()
        with self._lock:
            self.error_message = "User rejected proposed patch."
            self._record_history()
        return True

    def cancel(self):
        self._cancelled = True
        self._cancel_event.set()
        with self._lock:
            if self.state in TERMINAL:
                return
            self._transition(S.CANCELLING)
        if self._worker.acquire(blocking=False):
            try:
                self._finish_cancel()
            finally:
                self._worker.release()

    def _record_learning(self, success):
        try:
            if self.strategy_enabled and self.selected_strategy:
                from app.strategy_selector import StrategySelector
                StrategySelector(storage_dir=self.storage_dir, enabled=self.strategy_enabled).record_outcome(
                    strategy_id=self.selected_strategy, error_type=self._selection_error_type,
                    task=self.task_prompt, attempt_number=self.current_attempt, success=success,
                    tests_passed=success, execution_passed=success,
                    duration_ms=(self.current_test_results or {}).get("duration_ms", 0),
                    feedback_id=f"{self.session_id}:{self.current_attempt}", security_violation=False,
                    timeout=(self.current_test_results or {}).get("timeout", False))
            if success and self.memory_enabled:
                from app.repair_memory import RepairMemory
                RepairMemory(storage_dir=self.storage_dir, enabled=self.memory_enabled).add_verified_experience(
                    task=self.task_prompt, error_type=self._selection_error_type,
                    error_message=self.current_diagnosis or "verified native repair",
                    broken_code="\n".join((v or b"").decode("utf-8") for v in self._transaction.original.values()),
                    successful_fix=self.current_diff, tests=self.test_command,
                    verification={"passed": True, "native_tests_passed": True, "independent_verification_passed": True},
                    repair_attempts=self.current_attempt,
                    metadata={"session_id": self.session_id, "source_hashes": self.source_file_hashes,
                              "patch_hash": self.current_patch_hash, "fallback_used": self.fallback_used})
        except Exception as exc:
            self.warnings.append(f"Learning persistence failed: {exc}")

    def _extract_patch(self, text: str) -> str:
        """
        Robustly extracts SEARCH/REPLACE blocks or unified diffs from raw model response,
        handling surrounding markdown code fences.
        """
        lines = text.splitlines()

        # Check for SEARCH/REPLACE blocks
        if "<<<<<<< SEARCH" in text:
            extracted_lines = []
            in_block = False
            for line in lines:
                s = line.strip()
                # Strip markdown ticks if wrapping the block
                if s.startswith("```"):
                    continue

                clean_hdr = s.lstrip("#/").strip()
                if (clean_hdr.startswith("FILE:") or clean_hdr.startswith("File:")) and not in_block:
                    fname = clean_hdr[5:].strip().strip("'\"`")
                    if fname.startswith("a/") or fname.startswith("b/"):
                        fname = fname[2:]
                    extracted_lines.append(f"FILE: {fname}")
                elif s == "<<<<<<< SEARCH":
                    in_block = True
                    extracted_lines.append(s)
                elif in_block:
                    extracted_lines.append(line)
                    if s == ">>>>>>> REPLACE":
                        in_block = False
                        extracted_lines.append("")

            res = "\n".join(extracted_lines).strip()
            if res:
                return res + "\n"

        # Fallback to unified diff
        diff_lines = []
        in_diff = False
        for line in lines:
            if line.startswith("```diff") or line.startswith("```patch"):
                in_diff = True
                continue
            elif in_diff and line.startswith("```"):
                in_diff = False
                continue

            if in_diff:
                diff_lines.append(line)
            elif line.startswith("--- a/") or line.startswith("+++ b/") or line.startswith("@@ "):
                in_diff = True
                diff_lines.append(line)

        if diff_lines:
            return "\n".join(diff_lines) + "\n"

        # Fallback synthesizer: only if enabled and no delimiters were produced
        if getattr(self, "fallback_enabled", False):
            synthesized = self._synthesize_single_function_fallback(text)
            if synthesized:
                self.fallback_used = True
                return synthesized

        return ""

    def _synthesize_single_function_fallback(self, text: str) -> str:
        """
        Conservative fallback synthesizer for single-function Python replacements:
        1. Only active if self.fallback_enabled is True.
        2. Parses Python code fences or raw function definitions conservatively.
        3. Uses AST to identify exactly one function definition.
        4. Scans the repository for an explicit, unambiguous match in existing Python files.
        5. Extracts the exact original source lines using AST node positions.
        6. Rejects ambiguous, multi-function, class methods, or multi-file matches.
        7. Synthesizes a valid SEARCH/REPLACE block.
        8. Does NOT execute generated code.
        """
        if not getattr(self, "fallback_enabled", False):
            self.fallback_rejected_reason = "fallback_disabled"
            return ""

        # Supported responses: raw Python or one Python/unlabelled fence, with prose
        # outside a fence. Never select the first of several competing candidates.
        self.fallback_rejected_reason = ""
        fences = re.findall(r"```([^\n`]*)\n(.*?)\n```", text, flags=re.DOTALL)
        code_blocks = [code for lang, code in fences if lang.strip().lower() in ("", "python", "py")]
        if fences and len(code_blocks) != 1:
            self.fallback_rejected_reason = "multiple_candidates_rejected" if code_blocks else "no_python_code_block"
            return ""
        if not fences:
            code_blocks = [text]
        candidate_code = code_blocks[0].strip()
        try:
            tree = ast.parse(candidate_code)
        except SyntaxError:
            self.fallback_rejected_reason = "no_valid_function_ast"
            return ""
        if any(isinstance(n, ast.ClassDef) for n in tree.body):
            self.fallback_rejected_reason = "class_method_rejected"
            return ""
        fns = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if len(fns) != 1:
            self.fallback_rejected_reason = "multiple_functions_rejected" if len(fns) > 1 else "no_valid_function_ast"
            return ""
        if len(tree.body) != 1 or any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                                    for n in ast.walk(fns[0]) if n is not fns[0]):
            self.fallback_rejected_reason = "unsupported_source_structure"
            return ""
        candidate_ast = fns[0]
        target_fn_name = candidate_ast.name

        matching_files = []
        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "__pycache__", "data")]
            for f in files:
                if f.endswith(".py"):
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, self.repo_root).replace("\\", "/")
                    try:
                        safe_path(self.repo_root, rel_p)
                        with open(full_p, "r", encoding="utf-8-sig") as py_f:
                            file_src = py_f.read()
                        file_tree = ast.parse(file_src)
                        # Only accept top-level functions; reject class methods or nested functions
                        for node in file_tree.body:
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_fn_name:
                                matching_files.append((rel_p, full_p, node, file_src))
                    except Exception:
                        continue

        if len(matching_files) == 0:
            self.fallback_rejected_reason = "no_matching_function_in_repo"
            return ""
        elif len(matching_files) > 1:
            self.fallback_rejected_reason = "ambiguous_function_match"
            return ""

        rel_path, full_path, target_node, file_source = matching_files[0]
        source_lines = file_source.splitlines()

        # If candidate code specifies decorators, slice from target function's first decorator
        if target_node.decorator_list:
            start_line = target_node.decorator_list[0].lineno - 1
        else:
            start_line = target_node.lineno - 1

        end_line = getattr(target_node, "end_lineno", None)
        if end_line is None or end_line > len(source_lines) or start_line < 0:
            self.fallback_rejected_reason = "slice_bounds_error"
            return ""

        if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for n in ast.walk(target_node) if n is not target_node):
            self.fallback_rejected_reason = "unsupported_source_structure"
            return ""
        original_fn_lines = source_lines[start_line:end_line]
        original_fn_text = "\n".join(original_fn_lines)

        synthesized = f"FILE: {rel_path}\n<<<<<<< SEARCH\n{original_fn_text}\n=======\n{candidate_code}\n>>>>>>> REPLACE\n"
        self.fallback_rejected_reason = ""
        return synthesized

    def _do_inspecting(self):
        context_str = ""
        if getattr(self, "repo_index_enabled", True):
            try:
                indexer = get_repo_indexer(self.repo_root)
                search_query = self.task_prompt
                if self.current_diagnosis:
                    search_query += f" {self.current_diagnosis}"
                indexer.scan_and_index(semantic=False)
                context_results = indexer.search(search_query, top_k=3)
                if context_results:
                    context_str = "REPOSITORY CONTEXT:\n"
                    for r in context_results:
                        context_str += f"File: {r['rel_path']}\n{r.get('snippet', '')}\n\n"
            except Exception as exc:
                self.warnings.append(f"Repository retrieval failed: {exc}")

        return context_str

    def _do_planning(self):
        context_str = self.repository_context
        memory_context = ""
        if getattr(self, "memory_enabled", False):
            try:
                from app.repair_memory import RepairMemory
                mem = RepairMemory(storage_dir=self.storage_dir, enabled=self.memory_enabled)
                experiences = mem.search_similar_experiences(
                    task=self.task_prompt,
                    error_type=self.failure_category if self.failure_category != "none" else "test_failure",
                    error_message=self.current_diagnosis or "",
                    broken_code=""
                )
                self.warnings.extend(mem.warnings)
                if experiences:
                    self.memory_retrieved_count = len(experiences)
                    best_fix = experiences[0].get("successful_fix") or experiences[0].get("memory", {}).get("successful_fix", "")
                    if best_fix:
                        memory_context = f"\n\nSIMILAR VERIFIED REPAIR EXPERIENCE:\n{best_fix[:350]}"
            except Exception as exc:
                self.warnings.append(f"Memory retrieval failed: {exc}")

        strategy_prompt = ""
        if getattr(self, "strategy_enabled", False):
            try:
                from app.strategy_selector import StrategySelector
                from app.repair_strategy import get_strategy_prompt
                selector = StrategySelector(storage_dir=self.storage_dir, enabled=self.strategy_enabled)
                decision = selector.select_strategy(
                    error_type=self.failure_category if self.failure_category != "none" else "test_failure",
                    attempt_number=self.current_attempt,
                    previous_strategies=getattr(self, "strategy_history", []),
                    memory_available=bool(self.memory_enabled and self.memory_retrieved_count > 0),
                    difficulty="standard"
                )
                self.warnings.extend(selector.warnings)
                self.strategy_decision = decision
                self._selection_error_type = self.failure_category if self.failure_category != "none" else "test_failure"
                self.selected_strategy = decision.get("selected_strategy", "DIRECT_REPAIR")
                if not hasattr(self, "strategy_history"):
                    self.strategy_history = []
                self.strategy_history.append(self.selected_strategy)
                strategy_prompt = f"\n\nSELECTED REPAIR STRATEGY: {self.selected_strategy}\n{get_strategy_prompt(self.selected_strategy)}"
            except Exception as exc:
                self.warnings.append(f"Strategy selection failed: {exc}")
                self.selected_strategy = "DIRECT_REPAIR"

        prompt = f"{context_str}\n\nTASK:\n{self.task_prompt}" if context_str else f"TASK:\n{self.task_prompt}"
        if self.current_diagnosis:
            prompt += f"\n\nPREVIOUS TEST FAILURE DIAGNOSIS:\n{self.current_diagnosis}"

        if self.failure_context:
            prompt += "\n\nSTRUCTURED FAILURE CONTEXT:\n" + json.dumps(self.failure_context)

        if self.last_syntax_error:
            prompt += f"\n\nPREVIOUS PATCH VALIDATION ERROR:\n{self.last_syntax_error}\nEnsure SEARCH block exactly matches the target file."

        if memory_context:
            prompt += memory_context

        if strategy_prompt:
            prompt += strategy_prompt

        if getattr(self, "prompt_example_enabled", True):
            prompt += """

INSTRUCTIONS:
You must output your code change using explicit SEARCH/REPLACE blocks formatted exactly as:
FILE: <relative_path>
<<<<<<< SEARCH
<exact lines to find>
=======
<replacement lines>
>>>>>>> REPLACE

CRITICAL FORMAT RULES:
1. Always include the 'FILE: <relative_path>' line first.
2. The search block must start with '<<<<<<< SEARCH' and end with '======='.
3. The replace block must start with '=======' and end with '>>>>>>> REPLACE'.
4. Do NOT omit '<<<<<<< ', '=======', or '>>>>>>> '. Do NOT write bare 'SEARCH' or 'REPLACE'.
5. Do NOT wrap in markdown fences (like ```).
6. Do NOT include explanations or conversational prose.

EXAMPLE:
FILE: math_utils.py
<<<<<<< SEARCH
def subtract(a, b):
    return a + b
=======
def subtract(a, b):
    return a - b
>>>>>>> REPLACE

Now provide only the SEARCH/REPLACE block for the task above."""
        else:
            prompt += """

INSTRUCTIONS:
Output your code change in SEARCH/REPLACE format.
Provide only the code patch without markdown code fences or conversational prose."""

        self.current_plan = (f"Use repository context and {self.selected_strategy or 'DIRECT_REPAIR'}; "
            f"generate a minimal validated patch, request approval, run {self.test_command!r}, "
            "independently verify and restore bytes on failure.")
        if self._cancel_event.is_set():
            return self.current_plan, ""
        self._transition(S.GENERATING)
        response = self._model_call(prompt)
        self.last_raw_response = response
        patch = self._extract_patch(response)
        return self.current_plan, patch

    def _do_patch_validation(self):
        engine = PatchEngine(self.repo_root)
        targets = engine.extract_target_files(self.current_diff)
        if self.allowed_targets is not None and not set(t.replace("\\", "/") for t in targets).issubset(self.allowed_targets):
            return False, ["SecurityViolation: proposal contains an unplanned target"], {}
        res = engine.apply_patch(self.current_diff, dry_run=True)
        return res["success"], res.get("errors", []), res.get("source_file_hashes", {})

    def _do_testing(self):
        return project_test_runner.run_tests(self.repo_root, self.test_command, timeout=self.test_timeout, cancel_event=self._cancel_event)

    def _do_diagnosing(self):
        result = self.current_test_results or {}
        return json.dumps({"category": result.get("status"), "command": self.test_command,
            "exit_code": result.get("exit_code"), "output": result.get("output", "")[-10000:],
            "error": result.get("error"), "attempt": self.current_attempt,
            "changed_files": list(self.source_file_hashes), "strategies": self.strategy_history})

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self._manager_lock = threading.Lock()
        self._pending = set()

    def dispatch(self, session_id, approve_hash=None):
        session = self.get_session(session_id)
        with self._manager_lock:
            if session_id in self._pending:
                return False
            self._pending.add(session_id)
        def work():
            try:
                if approve_hash is not None and not session.approve(approve_hash):
                    return
                session.step()
            finally:
                with self._manager_lock:
                    self._pending.discard(session_id)
        worker = threading.Thread(target=work, name=f"engineering-{session_id}", daemon=True)
        worker.start()
        return worker

    def start_session(self, task_prompt, repo_root, test_command, fallback_enabled=None,
                      eager_policy_check=None, repo_index_enabled=None, prompt_example_enabled=None,
                      memory_enabled=None, strategy_enabled=None, storage_dir=None, background=False,
                      **options):
        session = EngineeringSession(task_prompt, repo_root, test_command,
            fallback_enabled=fallback_enabled, eager_policy_check=eager_policy_check,
            repo_index_enabled=repo_index_enabled, prompt_example_enabled=prompt_example_enabled,
            memory_enabled=memory_enabled, strategy_enabled=strategy_enabled, storage_dir=storage_dir,
            **options)
        with self._manager_lock:
            self.sessions[session.session_id] = session
        if background:
            self.dispatch(session.session_id)
        else:
            session.step()
        return session.session_id

    def get_session(self, session_id):
        with self._manager_lock:
            return self.sessions.get(session_id)

engineering_manager = SessionManager()
