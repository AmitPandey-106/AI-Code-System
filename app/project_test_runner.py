import subprocess
import os
import time
import shutil
from typing import Dict, Any, List, Optional
import shlex

class ProjectTestRunner:
    def __init__(self):
        # Explicit command policy: Only allow these commands to run.
        self.allowed_commands = [
            "pytest",
            "python -m pytest"
        ]
        self.default_timeout = 30
        self.max_output_length = 10000

    def _is_approved(self, command: str) -> bool:
        cmd_str = command.strip()
        for allowed in self.allowed_commands:
            if cmd_str.startswith(allowed):
                return True
        return False

    def is_command_allowed(self, command: str) -> bool:
        """Public check to determine if a test command satisfies allowlist policy."""
        return self._is_approved(command)

    def _truncate_output(self, text: str) -> str:
        if not text:
            return ""
        if len(text) > self.max_output_length:
            half = self.max_output_length // 2
            return text[:half] + "\n\n... [OUTPUT TRUNCATED] ...\n\n" + text[-half:]
        return text

    def run_tests(self, repo_root: str, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Runs native project tests in the specified repository root.
        """
        repo_root = os.path.abspath(repo_root)
        
        # 1. Validation
        if not os.path.isdir(repo_root):
            return {
                "success": False,
                "error": f"Invalid repository root: {repo_root}",
                "output": "",
                "exit_code": -1,
                "duration_ms": 0,
                "timeout": False,
                "status": "invalid_directory"
            }

        if not self._is_approved(command):
            return {
                "success": False,
                "error": f"SecurityViolation: Command not approved: {command}",
                "output": "",
                "exit_code": -1,
                "duration_ms": 0,
                "timeout": False,
                "status": "unapproved_command"
            }

        # Check if pytest is available
        executable = shlex.split(command)[0]
        if executable == "pytest" and shutil.which("pytest") is None:
             return {
                "success": False,
                "error": "ExecutionError: 'pytest' executable not found.",
                "output": "",
                "exit_code": -1,
                "duration_ms": 0,
                "timeout": False,
                "status": "missing_executable"
            }
            
        timeout = timeout or self.default_timeout
        start_time = time.time()

        try:
            # We use shell=False for security, parse the command with shlex
            args = shlex.split(command)
            resolved_exec = shutil.which(args[0])
            if resolved_exec:
                args[0] = resolved_exec
            result = subprocess.run(
                args,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            stdout = self._truncate_output(result.stdout)
            stderr = self._truncate_output(result.stderr)
            
            combined_output = stdout
            if stderr:
                combined_output += "\n--- STDERR ---\n" + stderr
                
            success = (result.returncode == 0)
            
            return {
                "success": success,
                "output": combined_output,
                "error": None if success else "Tests failed or exited with non-zero status.",
                "exit_code": result.returncode,
                "duration_ms": duration_ms,
                "timeout": False,
                "status": "success" if success else "failed"
            }

        except subprocess.TimeoutExpired as e:
            duration_ms = int((time.time() - start_time) * 1000)
            stdout = self._truncate_output(e.stdout if e.stdout else "")
            stderr = self._truncate_output(e.stderr if e.stderr else "")
            
            combined_output = stdout
            if stderr:
                combined_output += "\n--- STDERR ---\n" + stderr
                
            return {
                "success": False,
                "error": f"TimeoutError: Execution exceeded {timeout} seconds",
                "output": combined_output,
                "exit_code": -1,
                "duration_ms": duration_ms,
                "timeout": True,
                "status": "timeout"
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": f"ExecutionError: {str(e)}",
                "output": "",
                "exit_code": -1,
                "duration_ms": duration_ms,
                "timeout": False,
                "status": "error"
            }

project_test_runner = ProjectTestRunner()
