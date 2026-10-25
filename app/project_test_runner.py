"""Narrow pytest command policy; repository tests still require trusted execution."""
import collections
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from app.process_control import ProcessTree
from app.file_transaction import safe_path


class ProjectTestRunner:
    def __init__(self):
        self.allowed_commands = ["pytest", "python -m pytest"]
        self.default_timeout = 30
        self.max_output_length = 10000

    def _arguments(self, command):
        if isinstance(command, str):
            if any(c in command for c in (";", "&", "|", "<", ">", "`", "$", "\n", "\r", "\0")):
                raise ValueError("shell syntax is prohibited")
            args = shlex.split(command)
        elif isinstance(command, (list, tuple)) and all(isinstance(a, str) for a in command):
            args = list(command)
        else:
            raise ValueError("expected command string or argv")
        if not args:
            raise ValueError("empty command")
        if args[0] in ("pytest", "pytest.exe"):
            args = args[1:]
        elif args[:3] in (["python", "-m", "pytest"], ["python3", "-m", "pytest"], ["python.exe", "-m", "pytest"]):
            args = args[3:]
        else:
            raise ValueError("executable/module not allowlisted")
        simple = {"-q", "-qq", "-v", "-vv", "-s", "-x", "--exitfirst", "--disable-warnings",
                  "--no-header", "--no-summary", "--strict-markers"}
        takes_value = {"-k", "-m", "--maxfail", "--tb"}
        positionals = []
        i = 0
        while i < len(args):
            arg = args[i]
            if any(c in arg for c in (";", "&", "|", "<", ">", "`", "$", "\n", "\r", "\0")):
                raise ValueError("unsafe token")
            if arg in simple:
                i += 1
                continue
            key, separator, value = arg.partition("=")
            if key in takes_value:
                if not separator:
                    i += 1
                    if i >= len(args):
                        raise ValueError("option value missing")
                    value = args[i]
                if key == "--maxfail" and not re.fullmatch(r"[1-9][0-9]{0,2}", value):
                    raise ValueError("invalid maxfail")
                if key == "--tb" and value not in ("auto", "long", "short", "line", "native", "no"):
                    raise ValueError("invalid traceback style")
                if key in ("-k", "-m") and not re.fullmatch(r"[A-Za-z0-9_ .():+\\/-]{1,300}", value):
                    raise ValueError("invalid selection expression")
            elif arg.startswith("-"):
                raise ValueError("option not allowlisted")
            else:
                path = arg.split("::", 1)[0].replace("\\", "/")
                if not path or path.startswith("/") or ":" in path or ".." in path.split("/"):
                    raise ValueError("test path must remain in repository")
                if not re.fullmatch(r"[A-Za-z0-9_ ./\\-]+(?:\:\:[A-Za-z0-9_\[\].-]+)*", arg):
                    raise ValueError("invalid test node")
                positionals.append(path)
            i += 1
        return args, positionals

    def _is_approved(self, command):
        try:
            self._arguments(command)
            return True
        except (ValueError, TypeError):
            return False

    is_command_allowed = _is_approved

    def run_tests(self, repo_root, command, timeout=None, cancel_event=None):
        started = time.monotonic()
        def result(status, output="", error=None, code=-1):
            return {"success": status == "success", "status": status, "output": output,
                    "error": error, "exit_code": code, "timeout": status == "timeout",
                    "duration_ms": int((time.monotonic() - started) * 1000)}
        if not os.path.isdir(repo_root):
            return result("invalid_directory", error=f"Invalid repository root: {repo_root}")
        repo_root = str(Path(repo_root).resolve())
        try:
            args, paths = self._arguments(command)
            for rel in paths:
                if rel not in (".", "./"):
                    safe_path(repo_root, rel.rstrip("/"))
        except (ValueError, OSError) as exc:
            return result("unapproved_command", error=f"SecurityViolation: {exc}")
        if shutil.which("pytest") is None:
            return result("missing_executable", error="ExecutionError: pytest executable not found")
        timeout = self.default_timeout if timeout is None else min(max(float(timeout), 0.1), 600)
        bootstrap = "import sys,pytest; root=sys.argv.pop(1); sys.path.insert(0,root); raise SystemExit(pytest.main(sys.argv[1:]))"
        process = tree = None
        captured = collections.deque()
        length = 0
        truncated = False
        with tempfile.TemporaryDirectory(prefix="litecoder-tests-") as temp:
            ini = Path(temp) / "pytest.ini"
            ini.write_text("[pytest]\n", encoding="utf-8")
            env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "COMSPEC", "LANG", "LC_ALL") if key in os.environ}
            env.update({"PATH": os.path.dirname(sys.executable) + os.pathsep + os.path.join(os.environ.get("SystemRoot", "/usr"), "System32"),
                        "TEMP": temp, "TMP": temp, "TMPDIR": temp, "HOME": temp,
                        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
                        "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"})
            argv = [sys.executable, "-I", "-u", "-B", "-c", bootstrap, repo_root,
                    "-c", str(ini), "--rootdir", repo_root, "--confcutdir", repo_root,
                    "-p", "no:cacheprovider", *args]
            def drain():
                nonlocal length, truncated
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        return
                    captured.append(chunk)
                    length += len(chunk)
                    while length > self.max_output_length and captured:
                        excess = length - self.max_output_length
                        first = captured.popleft()
                        if len(first) > excess:
                            captured.appendleft(first[excess:])
                            length -= excess
                        else:
                            length -= len(first)
                        truncated = True
            try:
                if cancel_event is not None and cancel_event.is_set():
                    return result("cancelled", error="Cancelled before test launch")
                process = subprocess.Popen(argv, cwd=repo_root, env=env, shell=False,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    start_new_session=os.name != "nt",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                tree = ProcessTree(process)
                reader = threading.Thread(target=drain, daemon=True)
                reader.start()
                status = None
                while process.poll() is None:
                    if cancel_event is not None and cancel_event.is_set():
                        status = "cancelled"
                        break
                    if time.monotonic() - started >= timeout:
                        status = "timeout"
                        break
                    try:
                        process.wait(timeout=0.05)
                    except subprocess.TimeoutExpired:
                        pass
                tree.stop()
                reader.join(5)
                if reader.is_alive():
                    raise RuntimeError("Output reader did not terminate")
                process.stdout.close()
                output = b"".join(captured).decode("utf-8", errors="replace")
                if truncated:
                    output = "... [OUTPUT TRUNCATED] ...\n" + output
                status = status or ("success" if process.returncode == 0 else "failed")
                return result(status, output, None if status == "success" else f"Test execution {status}", process.returncode)
            except Exception as exc:
                if tree is not None:
                    tree.stop()
                elif process is not None:
                    process.kill()
                    process.wait(timeout=5)
                return result("error", error=f"ExecutionError: {exc}")


project_test_runner = ProjectTestRunner()
