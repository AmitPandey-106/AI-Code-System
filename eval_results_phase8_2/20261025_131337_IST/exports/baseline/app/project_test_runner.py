import subprocess
import os
import sys
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

    def _validate_pytest_args(self, args: List[str]) -> bool:
        """Validate that pytest arguments do not contain dangerous options or code injection."""
        forbidden_flags = {
            "--pdb",
            "-c",
            "--config-file",
            "-o",
            "--override-ini",
            "--import-mode",
            "--assert"
        }
        i = 0
        while i < len(args):
            arg = args[i]
            # Check exact match or flag prefix
            arg_lower = arg.lower()
            for forbidden in forbidden_flags:
                if arg_lower == forbidden or arg_lower.startswith(f"{forbidden}="):
                    return False
            # Check for shell metacharacters inside individual tokens
            for dangerous in (";", "&", "|", "<", ">", "`", "$", "\n", "\r"):
                if dangerous in arg:
                    return False
            i += 1
        return True

    def _is_approved(self, command: str) -> bool:
        if not command or not isinstance(command, str):
            return False
        cmd_str = command.strip()
        if not cmd_str:
            return False

        # Disallow dangerous shell operators / command chaining / redirects / substitutions
        for dangerous in (";", "&&", "||", "|", "&", "\n", "\r", "`", "$", ">", "<"):
            if dangerous in cmd_str:
                return False

        try:
            tokens = shlex.split(cmd_str)
        except Exception:
            return False

        if not tokens:
            return False

        exe = tokens[0].lower()
        base_exe = os.path.basename(exe)
        if base_exe.endswith(".exe"):
            base_exe = base_exe[:-4]

        # Allowed executables: pytest or python -m pytest
        if base_exe == "pytest":
            return self._validate_pytest_args(tokens[1:])
        elif base_exe in ("python", "python3"):
            if len(tokens) < 3:
                return False
            if tokens[1] != "-m":
                return False
            mod_name = os.path.basename(tokens[2]).lower()
            if mod_name.endswith(".exe"):
                mod_name = mod_name[:-4]
            if mod_name != "pytest":
                return False
            return self._validate_pytest_args(tokens[3:])

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
            base_exe = os.path.basename(args[0]).lower()
            if base_exe.endswith(".exe"):
                base_exe = base_exe[:-4]

            if base_exe in ("python", "python3"):
                resolved_exec = shutil.which(args[0]) or sys.executable
                args[0] = resolved_exec
            else:
                resolved_exec = shutil.which(args[0])
                if resolved_exec:
                    args[0] = resolved_exec

            # Sanitized environment
            clean_env = os.environ.copy()
            for var in (
                "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES",
                "PYTHONSTARTUP", "PYTHONBREAKPOINT", "PYTHONINSPECT"
            ):
                clean_env.pop(var, None)
            clean_env["PYTHONUNBUFFERED"] = "1"
            clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
            
            existing_pp = clean_env.get("PYTHONPATH", "")
            if existing_pp:
                clean_env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{existing_pp}"
            else:
                clean_env["PYTHONPATH"] = repo_root

            result = subprocess.run(
                args,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=clean_env
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
