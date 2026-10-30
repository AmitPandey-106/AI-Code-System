import os
import hashlib
from typing import Dict, Any, List, Optional
from app.engineering_loop import EngineeringSession, EngineeringState
from app.project_test_runner import project_test_runner

class MultiFileOrchestrationResult:
    def __init__(
        self,
        success: bool,
        task_prompt: str,
        target_files: List[str],
        completed_files: List[str],
        failed_file: Optional[str] = None,
        error: Optional[str] = None,
        rolled_back: bool = False,
        step_results: Optional[List[Dict[str, Any]]] = None
    ):
        self.success = success
        self.task_prompt = task_prompt
        self.target_files = target_files
        self.completed_files = completed_files
        self.failed_file = failed_file
        self.error = error
        self.rolled_back = rolled_back
        self.step_results = step_results or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "task_prompt": self.task_prompt,
            "target_files": self.target_files,
            "completed_files": self.completed_files,
            "failed_file": self.failed_file,
            "error": self.error,
            "rolled_back": self.rolled_back,
            "step_results": self.step_results
        }

class MultiFileEngineeringOrchestrator:
    """
    Coordinates multi-file repair tasks sequentially:
    1. Creates an atomic transaction snapshot of target repository files before any mutation.
    2. Sequentially executes single-file engineering sessions per target file.
    3. Verifies patch validity and file constraints after each step.
    4. Runs full native regression test suite upon completion of all file edits.
    5. If any step fails or tests regress, executes an atomic rollback restoring initial snapshot.
    """
    def __init__(
        self,
        repo_root: str,
        test_command: str,
        fallback_enabled: Optional[bool] = None,
        repo_index_enabled: Optional[bool] = None,
        prompt_example_enabled: Optional[bool] = None,
        memory_enabled: Optional[bool] = None,
        strategy_enabled: Optional[bool] = None,
        storage_dir: Optional[str] = None
    ):
        self.repo_root = os.path.abspath(repo_root)
        self.test_command = test_command
        self.fallback_enabled = fallback_enabled
        self.repo_index_enabled = repo_index_enabled
        self.prompt_example_enabled = prompt_example_enabled
        self.memory_enabled = memory_enabled
        self.strategy_enabled = strategy_enabled
        self.storage_dir = storage_dir

    def _create_snapshot(self, target_files: List[str]) -> Dict[str, Optional[bytes]]:
        """Takes a byte-level snapshot of all target files."""
        snapshot: Dict[str, Optional[bytes]] = {}
        for rel_path in target_files:
            norm_rel = os.path.normpath(rel_path).replace("\\", "/")
            full_path = os.path.join(self.repo_root, norm_rel)
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    snapshot[norm_rel] = f.read()
            else:
                snapshot[norm_rel] = None
        return snapshot

    def _rollback(self, snapshot: Dict[str, Optional[bytes]]):
        """Restores repository state exactly to initial snapshot."""
        for norm_rel, content in snapshot.items():
            full_path = os.path.join(self.repo_root, norm_rel)
            if content is None:
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except Exception:
                        pass
            else:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "wb") as f:
                    f.write(content)

    def execute_plan(
        self,
        task_prompt: str,
        target_files: List[str]
    ) -> MultiFileOrchestrationResult:
        if not target_files:
            return MultiFileOrchestrationResult(
                success=False,
                task_prompt=task_prompt,
                target_files=[],
                completed_files=[],
                error="No target files specified for multi-file orchestration."
            )

        # 1. Take transaction snapshot
        snapshot = self._create_snapshot(target_files)
        completed_files: List[str] = []
        step_results: List[Dict[str, Any]] = []

        # 2. Sequential execution
        for i, target_file in enumerate(target_files):
            step_prompt = (
                f"{task_prompt}\n\n"
                f"CURRENT STEP: File {i + 1} of {len(target_files)}\n"
                f"TARGET FILE TO EDIT: {target_file}\n"
                f"Modify ONLY {target_file}. Do not include changes for other files in this step."
            )

            session = EngineeringSession(
                task_prompt=step_prompt,
                repo_root=self.repo_root,
                test_command=self.test_command,
                fallback_enabled=self.fallback_enabled,
                eager_policy_check=True,
                repo_index_enabled=self.repo_index_enabled,
                prompt_example_enabled=self.prompt_example_enabled,
                memory_enabled=self.memory_enabled,
                strategy_enabled=self.strategy_enabled,
                storage_dir=self.storage_dir
            )

            # Step session to generate proposal
            session.step()
            status = session.get_status()

            if status["state"] != EngineeringState.AWAITING_APPROVAL:
                # Step failed to produce a valid approved patch
                self._rollback(snapshot)
                return MultiFileOrchestrationResult(
                    success=False,
                    task_prompt=task_prompt,
                    target_files=target_files,
                    completed_files=completed_files,
                    failed_file=target_file,
                    error=f"Step failed for {target_file}: {status.get('error_message', 'Validation failed')}",
                    rolled_back=True,
                    step_results=step_results
                )

            # Apply step patch
            approved = session.approve()
            if not approved:
                self._rollback(snapshot)
                return MultiFileOrchestrationResult(
                    success=False,
                    task_prompt=task_prompt,
                    target_files=target_files,
                    completed_files=completed_files,
                    failed_file=target_file,
                    error=f"Failed to apply patch for {target_file}: {session.error_message}",
                    rolled_back=True,
                    step_results=step_results
                )

            completed_files.append(target_file)
            step_results.append({
                "file": target_file,
                "patch": session.current_diff,
                "patch_hash": session.current_patch_hash,
                "fallback_used": session.fallback_used
            })

        # 3. Final verification across all changes
        test_res = project_test_runner.run_tests(self.repo_root, self.test_command)
        if not test_res.get("success"):
            # Tests failed after all files were edited -> atomic rollback
            self._rollback(snapshot)
            return MultiFileOrchestrationResult(
                success=False,
                task_prompt=task_prompt,
                target_files=target_files,
                completed_files=completed_files,
                failed_file="final_verification",
                error=f"Final tests failed: {test_res.get('error', 'Test failure')}",
                rolled_back=True,
                step_results=step_results
            )

        # 4. Success!
        return MultiFileOrchestrationResult(
            success=True,
            task_prompt=task_prompt,
            target_files=target_files,
            completed_files=completed_files,
            rolled_back=False,
            step_results=step_results
        )
