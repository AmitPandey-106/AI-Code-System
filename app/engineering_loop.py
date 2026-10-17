import os
import uuid
import time
import hashlib
import threading
import copy
import ast
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.repo_index import get_repo_indexer
from app.patch_engine import PatchEngine
from app.project_test_runner import project_test_runner
from app.model import generate_raw

class EngineeringState:
    RECEIVED = "received"
    PLANNING = "planning"
    PATCH_PROPOSED = "patch_proposed"
    AWAITING_APPROVAL = "awaiting_approval"
    PATCH_APPLIED = "patch_applied"
    TESTING = "testing"
    DIAGNOSING = "diagnosing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class EngineeringSession:
    def __init__(
        self,
        task_prompt: str,
        repo_root: str,
        test_command: str,
        fallback_enabled: Optional[bool] = None,
        eager_policy_check: Optional[bool] = None
    ):
        self.session_id = str(uuid.uuid4())
        self.task_prompt = task_prompt
        self.repo_root = os.path.abspath(repo_root)
        self.test_command = test_command
        self.state = EngineeringState.RECEIVED

        from app.config import config
        if fallback_enabled is not None:
            self.fallback_enabled = fallback_enabled
        else:
            self.fallback_enabled = (
                os.environ.get("LITECODER_FALLBACK_SYNTHESIZER", "").lower() == "true" or
                config.get("FALLBACK_SYNTHESIZER_ENABLED", False)
            )

        if eager_policy_check is not None:
            self.eager_policy_check = eager_policy_check
        else:
            self.eager_policy_check = (
                os.environ.get("LITECODER_EAGER_POLICY_CHECK", "").lower() == "true" or
                config.get("EAGER_POLICY_CHECK_ENABLED", False)
            )

        self.max_attempts = 3
        self.current_attempt = 1
        self.history: List[Dict[str, Any]] = []

        self.current_plan = ""
        self.current_diff = ""
        self.current_patch_hash = ""
        self.source_file_hashes: Dict[str, str] = {}
        self.current_test_results = None
        self.current_diagnosis = ""
        self.last_syntax_error = ""
        self.error_message = ""
        self.failure_category = "none"
        self.policy_event: Optional[Dict[str, Any]] = None

        self._lock = threading.Lock()
        self._cancelled = False

        # Eager command authorization validation at session creation
        if self.eager_policy_check and self.test_command and not project_test_runner.is_command_allowed(self.test_command):
            self.state = EngineeringState.FAILED
            self.failure_category = "policy_rejection"
            self.policy_event = {
                "event": "unapproved_command_rejected",
                "stage": "session_init",
                "command": self.test_command,
                "status": "unapproved_command",
                "error": f"SecurityViolation: Command not approved: {self.test_command}"
            }
            self.error_message = f"SecurityViolation: Command not approved: {self.test_command}"
            self._record_history()

    def get_status(self) -> Dict[str, Any]:
        """Thread-safe snapshot of session status."""
        with self._lock:
            return {
                "session_id": self.session_id,
                "state": self.state,
                "attempt": self.current_attempt,
                "history": copy.deepcopy(self.history),
                "error_message": self.error_message,
                "failure_category": self.failure_category,
                "policy_event": copy.deepcopy(self.policy_event) if self.policy_event else None,
                "last_syntax_error": self.last_syntax_error,
                "current_diff": self.current_diff,
                "current_patch_hash": self.current_patch_hash,
                "test_results": copy.deepcopy(self.current_test_results) if self.current_test_results else None
            }

    def _compute_file_hash(self, rel_path: str) -> str:
        abs_path = os.path.abspath(os.path.join(self.repo_root, rel_path))
        if not os.path.exists(abs_path):
            return "__non_existent__"
        try:
            with open(abs_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return "__read_error__"

    def step(self) -> str:
        """
        Executes bounded state transitions.
        Supports bounded retries for malformed patch output within max_attempts.
        """
        while True:
            with self._lock:
                if self._cancelled or self.state == EngineeringState.CANCELLED:
                    return EngineeringState.CANCELLED
                if self.state in (EngineeringState.COMPLETED, EngineeringState.FAILED, EngineeringState.AWAITING_APPROVAL):
                    return self.state

                if self.state == EngineeringState.RECEIVED:
                    self.state = EngineeringState.PLANNING

                current_state = self.state

            # --- State: PLANNING ---
            if current_state == EngineeringState.PLANNING:
                try:
                    plan, patch = self._do_planning()
                    with self._lock:
                        if self._cancelled:
                            self.state = EngineeringState.CANCELLED
                            return self.state

                        if not patch:
                            if self.current_attempt < self.max_attempts:
                                self.current_attempt += 1
                                self.last_syntax_error = "Model response contained no parseable SEARCH/REPLACE blocks or unified diff."
                                self._record_history()
                                continue  # Retry planning
                            else:
                                self.state = EngineeringState.FAILED
                                self.failure_category = "malformed_patch_syntax"
                                self.error_message = f"Budget exhausted. Malformed patch syntax (failed to generate SEARCH/REPLACE or valid unified diff) after {self.max_attempts} attempts."
                                self._record_history()
                                return self.state

                        self.current_plan = plan
                        self.current_diff = patch
                        self.state = EngineeringState.PATCH_PROPOSED
                except Exception as e:
                    with self._lock:
                        self.state = EngineeringState.FAILED
                        self.failure_category = "model_generation_failure"
                        self.error_message = f"Planning failed with exception: {str(e)}"
                        self._record_history()
                        return self.state

            # --- State: PATCH_PROPOSED ---
            elif current_state == EngineeringState.PATCH_PROPOSED:
                try:
                    success, errors, hashes = self._do_patch_validation()
                    with self._lock:
                        if self._cancelled:
                            self.state = EngineeringState.CANCELLED
                            return self.state

                        if not success:
                            err_str = "; ".join(errors)
                            if self.current_attempt < self.max_attempts:
                                self.current_attempt += 1
                                self.last_syntax_error = f"Patch validation failed: {err_str}"
                                self.state = EngineeringState.PLANNING
                                self._record_history()
                                continue  # Retry planning with specific syntax feedback
                            else:
                                self.state = EngineeringState.FAILED
                                self.failure_category = "malformed_patch_syntax"
                                self.error_message = f"Budget exhausted. Patch validation failed after {self.max_attempts} attempts: {err_str}"
                                self._record_history()
                                return self.state

                        # Syntax validation passed
                        self.last_syntax_error = ""
                        self.current_patch_hash = hashlib.sha256(self.current_diff.encode("utf-8")).hexdigest()
                        self.source_file_hashes = hashes

                        self.state = EngineeringState.AWAITING_APPROVAL
                        self._record_history()
                        return self.state
                except Exception as e:
                    with self._lock:
                        self.state = EngineeringState.FAILED
                        self.failure_category = "patch_validation_failure"
                        self.error_message = f"Patch validation error: {str(e)}"
                        self._record_history()
                        return self.state

            # --- State: PATCH_APPLIED ---
            elif current_state == EngineeringState.PATCH_APPLIED:
                with self._lock:
                    self.state = EngineeringState.TESTING

            # --- State: TESTING ---
            elif current_state == EngineeringState.TESTING:
                try:
                    test_res = self._do_testing()
                    with self._lock:
                        if self._cancelled:
                            self.state = EngineeringState.CANCELLED
                            return self.state
                        self.current_test_results = test_res

                        # Explicit security policy check
                        if test_res.get("status") == "unapproved_command":
                            self.state = EngineeringState.FAILED
                            self.failure_category = "policy_rejection"
                            self.policy_event = {
                                "event": "unapproved_command_rejected",
                                "command": self.test_command,
                                "status": "unapproved_command",
                                "error": test_res.get("error")
                            }
                            self.error_message = f"SecurityViolation: {test_res.get('error')}"
                            self._record_history()
                            return self.state

                        if test_res.get("success"):
                            self.state = EngineeringState.COMPLETED
                            self._record_history()
                            return self.state
                        else:
                            if self.current_attempt >= self.max_attempts:
                                self.state = EngineeringState.FAILED
                                self.failure_category = "test_failure"
                                self.error_message = f"Budget exhausted. Tests failed after {self.max_attempts} attempts."
                                self._record_history()
                                return self.state
                            else:
                                self.state = EngineeringState.DIAGNOSING
                                self._record_history()
                except Exception as e:
                    with self._lock:
                        self.state = EngineeringState.FAILED
                        self.failure_category = "test_failure"
                        self.error_message = f"Testing execution error: {str(e)}"
                        self._record_history()
                        return self.state

            # --- State: DIAGNOSING ---
            elif current_state == EngineeringState.DIAGNOSING:
                try:
                    diag = self._do_diagnosing()
                    with self._lock:
                        if self._cancelled:
                            self.state = EngineeringState.CANCELLED
                            return self.state
                        self.current_diagnosis = diag
                        self.current_attempt += 1
                        self.state = EngineeringState.PLANNING
                except Exception as e:
                    with self._lock:
                        self.state = EngineeringState.FAILED
                        self.failure_category = "model_generation_failure"
                        self.error_message = f"Diagnosis error: {str(e)}"
                        self._record_history()
                        return self.state

        return self.state

    def approve(self, expected_patch_hash: Optional[str] = None) -> bool:
        """
        Applies proposed patch with strict verification:
        1. Must be in AWAITING_APPROVAL state.
        2. If expected_patch_hash is given, must match current_patch_hash.
        3. Target files on disk must match the snapshot hashes recorded when patch was proposed.
        """
        with self._lock:
            if self.state != EngineeringState.AWAITING_APPROVAL:
                return False

            if expected_patch_hash and expected_patch_hash != self.current_patch_hash:
                self.error_message = f"PatchHashMismatch: Expected {expected_patch_hash}, got {self.current_patch_hash}"
                return False

            # Verify target files are not stale
            for rel_path, expected_hash in self.source_file_hashes.items():
                current_hash = self._compute_file_hash(rel_path)
                if current_hash != expected_hash:
                    self.state = EngineeringState.FAILED
                    self.failure_category = "stale_source"
                    self.error_message = f"StaleSourceError: File '{rel_path}' was modified on disk after patch was proposed."
                    self._record_history()
                    return False

            # Apply patch atomically
            engine = PatchEngine(self.repo_root)
            res = engine.apply_patch(self.current_diff, dry_run=False, expected_hashes=self.source_file_hashes)
            if not res["success"]:
                self.state = EngineeringState.FAILED
                self.failure_category = "patch_application_failure"
                self.error_message = f"Patch application failed after approval: {res['errors']}"
                self._record_history()
                return False

            self.state = EngineeringState.PATCH_APPLIED
            self._record_history()
            return True

    def reject(self) -> bool:
        with self._lock:
            if self.state == EngineeringState.AWAITING_APPROVAL:
                self.state = EngineeringState.CANCELLED
                self.failure_category = "cancelled"
                self.error_message = "User rejected proposed patch."
                self._record_history()
                return True
        return False

    def cancel(self):
        with self._lock:
            self._cancelled = True
            self.state = EngineeringState.CANCELLED
            self.failure_category = "cancelled"
            self.error_message = "Cancelled by user."
            self._record_history()

    def _record_history(self):
        self.history.append({
            "attempt": self.current_attempt,
            "state": self.state,
            "plan": self.current_plan,
            "diff": self.current_diff,
            "patch_hash": self.current_patch_hash,
            "diagnosis": self.current_diagnosis,
            "last_syntax_error": self.last_syntax_error,
            "test_results": self.current_test_results,
            "failure_category": self.failure_category,
            "policy_event": self.policy_event,
            "error_message": self.error_message,
            "timestamp": time.time()
        })

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
                return synthesized

        return ""

    def _synthesize_single_function_fallback(self, text: str) -> str:
        """
        Conservative fallback synthesizer for single-function Python replacements:
        1. Only active if self.fallback_enabled is True.
        2. Parses Python code fences conservatively.
        3. Uses AST to identify exactly one function definition.
        4. Scans the repository for an explicit, unambiguous match in existing Python files.
        5. Extracts the exact original source lines using AST node positions.
        6. Rejects ambiguous, multi-function, or multi-file matches.
        7. Synthesizes a valid SEARCH/REPLACE block.
        8. Does NOT execute generated code.
        """
        if not getattr(self, "fallback_enabled", False):
            return ""

        code_blocks = re.findall(r"```(?:python)?\s*\n(.*?)\n```", text, flags=re.DOTALL)
        if not code_blocks:
            return ""

        candidate_ast = None
        candidate_code = None
        for block in code_blocks:
            cleaned = block.strip()
            if not cleaned:
                continue
            try:
                tree = ast.parse(cleaned)
                fns = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                non_trivial = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
                if len(fns) == 1 and len(non_trivial) == 1:
                    candidate_ast = fns[0]
                    candidate_code = cleaned
                    break
            except Exception:
                continue

        if not candidate_ast or not candidate_code:
            return ""

        target_fn_name = candidate_ast.name

        matching_files = []
        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "__pycache__", "data")]
            for f in files:
                if f.endswith(".py"):
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, self.repo_root).replace("\\", "/")
                    try:
                        with open(full_p, "r", encoding="utf-8") as py_f:
                            file_src = py_f.read()
                        file_tree = ast.parse(file_src)
                        for node in ast.walk(file_tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_fn_name:
                                matching_files.append((rel_p, full_p, node, file_src))
                    except Exception:
                        continue

        if len(matching_files) != 1:
            return ""

        rel_path, full_path, target_node, file_source = matching_files[0]
        source_lines = file_source.splitlines()
        start_line = target_node.lineno - 1
        end_line = getattr(target_node, "end_lineno", None)
        if end_line is None or end_line > len(source_lines):
            return ""

        original_fn_lines = source_lines[start_line:end_line]
        original_fn_text = "\n".join(original_fn_lines)

        synthesized = f"FILE: {rel_path}\n<<<<<<< SEARCH\n{original_fn_text}\n=======\n{candidate_code}\n>>>>>>> REPLACE\n"
        return synthesized

    def _do_planning(self):
        indexer = get_repo_indexer(self.repo_root)
        search_query = self.task_prompt
        if self.current_diagnosis:
            search_query += f" {self.current_diagnosis}"

        context_results = indexer.search(search_query, top_k=3)
        context_str = ""
        if context_results:
            context_str = "REPOSITORY CONTEXT:\n"
            for r in context_results:
                context_str += f"File: {r['rel_path']}\n{r.get('snippet', '')}\n\n"

        prompt = f"{context_str}\n\nTASK:\n{self.task_prompt}"
        if self.current_diagnosis:
            prompt += f"\n\nPREVIOUS TEST FAILURE DIAGNOSIS:\n{self.current_diagnosis}"

        if self.last_syntax_error:
            prompt += f"\n\nPREVIOUS PATCH VALIDATION ERROR:\n{self.last_syntax_error}\nEnsure SEARCH block exactly matches the target file."

        prompt += """

INSTRUCTIONS:
You must output your code change using explicit SEARCH/REPLACE blocks.
Do NOT wrap the patch in markdown code fences (like ```python or ```diff).
Do NOT include explanations, markdown headers, or conversational prose.
The SEARCH block must be an exact, character-for-character copy of lines from the target file.

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

        response = generate_raw(prompt)
        patch = self._extract_patch(response)
        return response, patch

    def _do_patch_validation(self):
        engine = PatchEngine(self.repo_root)
        res = engine.apply_patch(self.current_diff, dry_run=True)
        return res["success"], res.get("errors", []), res.get("source_file_hashes", {})

    def _do_testing(self):
        return project_test_runner.run_tests(self.repo_root, self.test_command)

    def _do_diagnosing(self):
        prompt = f"Test execution failed.\n\nCommand: {self.test_command}\nStatus: {self.current_test_results.get('status')}\nExit Code: {self.current_test_results.get('exit_code')}\n\nOUTPUT:\n{self.current_test_results.get('output')}\n\nDiagnose the failure in one concise paragraph."
        return generate_raw(prompt)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, EngineeringSession] = {}
        self._manager_lock = threading.Lock()

    def start_session(
        self,
        task_prompt: str,
        repo_root: str,
        test_command: str,
        fallback_enabled: Optional[bool] = None,
        eager_policy_check: Optional[bool] = None
    ) -> str:
        session = EngineeringSession(
            task_prompt,
            repo_root,
            test_command,
            fallback_enabled=fallback_enabled,
            eager_policy_check=eager_policy_check
        )
        with self._manager_lock:
            self.sessions[session.session_id] = session
        session.step()
        return session.session_id

    def get_session(self, session_id: str) -> Optional[EngineeringSession]:
        with self._manager_lock:
            return self.sessions.get(session_id)

engineering_manager = SessionManager()
