"""Stdlib execution controls. Python audit hooks are not an OS security boundary."""
import contextlib
import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import sys
import threading
import time
import traceback
import uuid

TASK = "task_01_router_slug_param"
REVISIONS = {"A": "9ef57511e0e25d58d0f1318e9d73ccb58465ec44",
             "B": "920c01aa0d510aa281092e6b55e4ce02b31e584e"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan_digest(plan):
    return sha(json.dumps({k: v for k, v in plan.items() if k != "plan_sha256"},
                          sort_keys=True, separators=(",", ":")).encode())


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def json_object(raw, label="JSON"):
    """Evidence is strict JSON: duplicate keys and non-finite values fail closed."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(label + ": duplicate key " + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError(label + ": invalid constant " + value)
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError(label + ": object required")
    return value


def read_json(path):
    return json_object(Path(path).read_bytes(), str(path))


BOUND_SOURCES = ("scripts/phase8_2_1_arm.py", "scripts/phase8_2_1_controls.py",
    "scripts/phase8_2_1_pytest.py", "scripts/phase8_2_1_prepare.py",
    "tests/test_phase8_2_1_hardening.py", "tests/phase8_2_1_control_child.py")
TESTED_SOURCES = BOUND_SOURCES + ("scripts/phase8_2_arm.py", "scripts/phase8_2_preflight.py",
                                "tests/test_phase8_2_preflight.py")
REQUIRED_SUITES = ("phase8_1_integration", "phase8_1_strategy", "phase8_2_and_8_2_1_controls")


def digest_value(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Malformed SHA256 digest")
    return value


def verify_bound_evidence(plan):
    """Verify the approved bytes and their structure, never a replacement artifact.

    This check is mandatory even when expensive environment checks are disabled.
    Hashing and JSON parsing use the same read, avoiding a second-read substitution.
    """
    root = canonical(plan["evidence_output"])
    objects = {}
    for field, name in (("deterministic_test_results_sha256", "test_results.json"),
                        ("source_hash_manifest_sha256", "source_hash_manifest.json")):
        expected = digest_value(plan[field])
        raw = canonical(root / name).read_bytes()
        if sha(raw) != expected:
            raise IntegrityMismatch(name + ": bound evidence SHA256 mismatch")
        objects[name] = json_object(raw, name)
    project = Path(__file__).resolve().parents[1]
    required = {str(project / name) for name in BOUND_SOURCES}
    allowed = {str(project / name) for name in TESTED_SOURCES}
    manifest = objects["source_hash_manifest.json"]
    if set(manifest) != required:
        raise ValueError("Incomplete or unexpected source manifest entries")
    if (plan.get("preparation_source_sha256") != manifest[str(project / "scripts/phase8_2_1_prepare.py")]
            or plan.get("adapter_sha256") != manifest[str(project / "scripts/phase8_2_1_arm.py")]
            or any(plan.get("execution_files", {}).get(Path(name).name) != manifest[str(project / name)]
                   for name in BOUND_SOURCES[:3])):
        raise ValueError("Contradictory execution/preparation source bindings")
    for name, expected in manifest.items():
        if file_sha(canonical(name)) != digest_value(expected):
            raise IntegrityMismatch("Bound source changed: " + name)
    results = objects["test_results.json"]
    suites = results.get("final_suites")
    if not isinstance(suites, dict) or set(suites) != set(REQUIRED_SUITES):
        raise ValueError("Malformed required suite manifest")
    for counts in suites.values():
        if not isinstance(counts, dict) or any(type(counts.get(k)) is not int or counts[k] < 0
                for k in ("tests", "passed", "failures", "errors", "skipped")):
            raise ValueError("Malformed test counts")
        if (counts["tests"] <= 0 or counts["passed"] <= 0 or counts["failures"] or counts["errors"]
                or counts["tests"] != sum(counts[k] for k in ("passed", "failures", "errors", "skipped"))):
            raise ValueError("Failed or inconsistent required tests")
    commands = results.get("commands")
    command = commands.get("controls") if isinstance(commands, dict) else None
    if not isinstance(command, dict) or type(command.get("exit_code")) is not int or command["exit_code"] != 0:
        raise ValueError("Missing successful controls command")
    tested = command.get("source_hashes")
    if (not isinstance(tested, dict) or not required <= set(tested) or set(tested) - allowed
            or any(tested.get(name) != expected for name, expected in manifest.items())):
        raise ValueError("Incomplete or inconsistent tested-source bindings")
    for name, expected in tested.items():
        if file_sha(canonical(name)) != digest_value(expected):
            raise IntegrityMismatch("Tested source changed: " + name)
    count = plan.get("preflight_control_test_count")
    if type(count) is not int or count != suites[REQUIRED_SUITES[-1]]["passed"]:
        raise ValueError("Control test count differs from bound evidence")


class IntegrityMismatch(ValueError):
    """A completed comparison detected different bytes, entries or file modes."""


def exception_details(stage, exc):
    return {"stage": stage, "error_type": type(exc).__name__, "message": str(exc),
            "repr": repr(exc), "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))}


def protected_audit(verify):
    """False means unverified; only an IntegrityMismatch proves a mismatch."""
    try:
        verify()
        return {"status": "verified", "verified": True, "error": None}
    except BaseException as exc:
        status = ("mismatch" if isinstance(exc, IntegrityMismatch) else "interrupted"
                  if isinstance(exc, KeyboardInterrupt) else "read_error")
        return {"status": status, "verified": False, "error": exception_details("protected_verification", exc),
                "exception": exc}


def check_deadline(deadline, stop=None, alive=None):
    if (stop is not None and stop.is_set()) or (deadline is not None and time.monotonic() >= deadline):
        raise TimeoutError("Active worker/review deadline expired")
    if alive is not None and not alive():
        raise ChildProcessError("Worker exited before review decision")


class BoundedInput:
    """Main-thread console/pipe input; no abandoned thread can read a later approval.

    Only terminal and pipe descriptors are supported. Disk/custom streams fail
    closed. Both initial confirmation and review use this reader, so TextIOWrapper
    prefetch cannot hide bytes from readiness checks. Polls are at most 20 ms.
    """
    def __init__(self, stream=None):
        self.stream = sys.stdin if stream is None else stream
        self.fd = self.stream.fileno()
        self.console = False
        if os.name == "nt":
            import ctypes
            import msvcrt
            from ctypes import wintypes as w
            self.msvcrt = msvcrt
            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.handle = w.HANDLE(msvcrt.get_osfhandle(self.fd))
            self.kernel.GetFileType.argtypes = [w.HANDLE]
            self.kernel.GetFileType.restype = w.DWORD
            self.kernel.GetConsoleMode.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
            self.kernel.GetConsoleMode.restype = w.BOOL
            self.kernel.PeekNamedPipe.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD,
                ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD)]
            self.kernel.PeekNamedPipe.restype = w.BOOL
            kind = self.kernel.GetFileType(self.handle)
            mode = w.DWORD()
            if kind == 2 and self.kernel.GetConsoleMode(self.handle, ctypes.byref(mode)):
                self.console = True
            elif kind == 3:
                # CRT text mode can block on a trailing CR while looking for LF,
                # even after PeekNamedPipe reports one available byte.
                self.msvcrt.setmode(self.fd, os.O_BINARY)
            else:
                raise PermissionError("Bounded confirmation requires a Windows console or pipe")
        else:
            import stat
            mode = os.fstat(self.fd).st_mode
            if not (os.isatty(self.fd) or stat.S_ISFIFO(mode)):
                raise PermissionError("Bounded confirmation requires a terminal or pipe")

    def _poll_character(self, timeout):
        if os.name == "nt":
            if self.console:
                if self.msvcrt.kbhit():
                    value = self.msvcrt.getwch()
                    if value in ("\x00", "\xe0"):
                        raise PermissionError("Extended console input is not a confirmation")
                    return value
            else:
                import ctypes
                from ctypes import wintypes as w
                available = w.DWORD()
                if not self.kernel.PeekNamedPipe(self.handle, None, 0, None, ctypes.byref(available), None):
                    error = ctypes.get_last_error()
                    if error in (109, 233):
                        raise EOFError("Confirmation pipe closed")
                    raise ctypes.WinError(error)
                if available.value:
                    raw = os.read(self.fd, 1)
                    if not raw:
                        raise EOFError("Confirmation pipe closed")
                    return raw.decode("ascii", errors="strict")
            time.sleep(timeout)
            return None
        import select
        ready, _, _ = select.select([self.fd], [], [], timeout)
        if not ready:
            return None
        raw = os.read(self.fd, 1)
        if not raw:
            raise EOFError("Confirmation input closed")
        return raw.decode("ascii", errors="strict")

    def __call__(self, prompt, *, deadline=None, stop=None, alive=None):
        print(prompt, end="", flush=True)
        line = []
        while True:
            check_deadline(deadline, stop, alive)
            delay = .02 if deadline is None else min(.02, max(0, deadline - time.monotonic()))
            value = self._poll_character(delay)
            check_deadline(deadline, stop, alive)
            if value is None:
                continue
            if value == "\x03":
                raise KeyboardInterrupt()
            if value in ("\x04", "\x1a"):
                raise EOFError("Confirmation input closed")
            if value in ("\n", "\r") and (self.console or value == "\n"):
                if self.console:
                    print(flush=True)
                return "".join(line).rstrip("\r")
            if self.console and value == "\b":
                if line:
                    line.pop(); print("\b \b", end="", flush=True)
                continue
            if len(line) >= 128 or (value not in "\r" and (len(value) != 1 or ord(value) < 32 or ord(value) > 126)):
                raise PermissionError("Malformed or oversized confirmation")
            line.append(value)
            if self.console:
                print(value, end="", flush=True)


def canonical(path):
    """Reject traversal, reparse points, ADS, hardlink aliases and short aliases."""
    path = Path(path)
    if ".." in path.parts or any(":" in p for p in path.parts[1:]):
        raise ValueError("Unsafe path traversal or alternate stream")
    reserved = {"CON", "PRN", "AUX", "NUL", *("COM" + str(i) for i in range(1, 10)),
                *("LPT" + str(i) for i in range(1, 10))}
    if os.name == "nt" and any(p.rstrip(" .") != p or p.split(".")[0].upper() in reserved
                                for p in path.parts[1:]):
        raise ValueError("Windows device or trailing-dot/space alias forbidden")
    absolute = Path(os.path.abspath(path))
    for component in (absolute, *absolute.parents):
        if component.exists() or component.is_symlink():
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Path alias/reparse point forbidden")
            if component.is_file() and info.st_nlink != 1:
                raise ValueError("Hardlink alias forbidden")
    resolved = absolute.resolve()
    if os.path.normcase(str(resolved)) != os.path.normcase(str(absolute)):
        raise ValueError("Noncanonical path alias forbidden")
    return resolved


def within(path, root):
    return path == root or root in path.parents


def disjoint(paths):
    paths = [canonical(p) for p in paths]
    if any(within(a, b) or within(b, a) for i, a in enumerate(paths) for b in paths[i + 1:]):
        raise ValueError("Protected/output paths overlap")
    return paths


def exclusive(path, data):
    path = canonical(path)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def exclusive_json(path, value):
    exclusive(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def tree_hashes(root):
    root = canonical(root)
    return {p.relative_to(root).as_posix(): file_sha(canonical(p))
            for p in sorted(root.rglob("*")) if p.is_file()}


def verify_tree(root, expected, readonly=False):
    expected = {k: v["sha256"] if isinstance(v, dict) else v for k, v in expected.items()}
    if tree_hashes(root) != expected:
        raise IntegrityMismatch("Protected tree hash mismatch: " + str(root))
    if readonly and any(p.stat().st_mode & stat.S_IWUSR for p in Path(root).rglob("*") if p.is_file()):
        raise IntegrityMismatch("Protected file is writable: " + str(root))


class Evidence:
    """Every artifact is exclusive. A terminal record has one immutable winner.

    A power loss can leave a partial exclusive file; readers fail closed on JSON
    errors. We never truncate, repair or replace that file in place.
    """
    def __init__(self, root, context):
        self.root = canonical(root)
        self.context = context

    def artifact(self, name, data):
        if Path(name).name != name:
            raise ValueError("Evidence names must be basenames")
        exclusive(self.root / name, data)

    def event(self, status, **details):
        record = dict(self.context, status=status, timestamp=timestamp(), **details)
        exclusive_json(self.root / ("event_" + uuid.uuid4().hex + ".json"), record)
        return record

    def finalize(self, status, **details):
        path = self.root / "terminal.json"
        record = dict(self.context, status=status, timestamp=timestamp(), **details)
        try:
            exclusive_json(path, record)
            return record
        except FileExistsError:
            return read_json(path)


def claim(output, context):
    output = canonical(output)
    output.mkdir(exist_ok=False)  # parent must already exist; never create arbitrary parents
    for name in ("control", "evidence", "workspace"):
        (output / name).mkdir()
    owner = dict(context, run_id=uuid.uuid4().hex, parent_pid=os.getpid(), created=timestamp())
    exclusive_json(output / "control/owner.json", owner)
    return owner


def authorize(output, owner, child_pid, lifetime=30, job_name=None):
    token = secrets.token_hex(32)
    if job_name is None and os.name == "nt":
        job_name = getattr(Supervisor, "_active_job_name", None)
    record = dict(owner, child_pid=child_pid, expires=time.time() + lifetime,
                  token_sha256=sha(token.encode()), supervised=True)
    if job_name:
        record["job_name"] = job_name
    exclusive_json(Path(output) / "control/authorization.json", record)
    return token


def get_process_parent_pid(pid):
    """Query parent PID using Toolhelp32 snapshot. Fails closed if process not found."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes as w
    TH32CS_SNAPPROCESS = 0x00000002
    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", w.DWORD),
            ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
            ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
            ("szExeFile", ctypes.c_char * 260)
        ]
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = w.HANDLE
    kernel32.Process32First.argtypes = [w.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    kernel32.Process32First.restype = w.BOOL
    kernel32.Process32Next.argtypes = [w.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    kernel32.Process32Next.restype = w.BOOL
    kernel32.CloseHandle.argtypes = [w.HANDLE]

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == w.HANDLE(-1).value or not snapshot:
        return None
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    try:
        if not kernel32.Process32First(snapshot, ctypes.byref(pe)):
            return None
        while True:
            if pe.th32ProcessID == pid:
                return pe.th32ParentProcessID
            if not kernel32.Process32Next(snapshot, ctypes.byref(pe)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return None


def get_process_creation_time(pid):
    """Return 64-bit FILETIME creation timestamp of PID, or None if inaccessible."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes as w
    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", w.DWORD), ("dwHighDateTime", w.DWORD)]
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel32.OpenProcess.restype = w.HANDLE
    kernel32.GetProcessTimes.argtypes = [w.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME),
                                        ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
    kernel32.GetProcessTimes.restype = w.BOOL
    kernel32.CloseHandle.argtypes = [w.HANDLE]
    h = kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    try:
        c, e, k, u = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if kernel32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
            return (c.dwHighDateTime << 32) | c.dwLowDateTime
        return None
    finally:
        kernel32.CloseHandle(h)


def verify_in_job_object(job_name=None):
    """Verify caller is in an active Job Object, and if job_name given, in that exact job."""
    if os.name != "nt":
        return True
    import ctypes
    from ctypes import wintypes as w
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
    kernel32.IsProcessInJob.restype = w.BOOL
    in_any = w.BOOL()
    if not kernel32.IsProcessInJob(kernel32.GetCurrentProcess(), None, ctypes.byref(in_any)) or not in_any.value:
        return False
    if job_name:
        kernel32.OpenJobObjectW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
        kernel32.OpenJobObjectW.restype = w.HANDLE
        kernel32.CloseHandle.argtypes = [w.HANDLE]
        hJob = kernel32.OpenJobObjectW(0x0004, False, job_name)
        if not hJob:
            return False
        try:
            in_spec = w.BOOL()
            if not kernel32.IsProcessInJob(kernel32.GetCurrentProcess(), hJob, ctypes.byref(in_spec)) or not in_spec.value:
                return False
        finally:
            kernel32.CloseHandle(hJob)
    return True


def consume_authorization(output, expected, token, *, pid=None, parent_pid=None, now=None):
    """One-use local pipe capability, bound to parent/child and complete run identity."""
    try:
        if not isinstance(token, str) or len(token) != 64:
            raise ValueError()
        owner = read_json(Path(output) / "control/owner.json")
        auth = read_json(Path(output) / "control/authorization.json")
        for key, value in expected.items():
            if owner.get(key) != value or auth.get(key) != value:
                raise ValueError()
        if (auth.get("run_id") != owner.get("run_id") or auth.get("supervised") is not True
                or not (0 < auth["expires"] - (time.time() if now is None else now) <= 30)
                or not hmac.compare_digest(auth["token_sha256"], sha(token.encode()))):
            raise ValueError()

        actual_pid = os.getpid() if pid is None else pid
        actual_ppid = os.getppid() if parent_pid is None else parent_pid

        direct_match = (auth.get("child_pid") == actual_pid
                        and auth.get("parent_pid") == actual_ppid)

        windows_trampoline = False
        launcher_pid = None
        grandparent_pid = None

        if direct_match:
            if os.name == "nt" and auth.get("job_name"):
                if not verify_in_job_object(auth["job_name"]):
                    raise ValueError("Process not in intended Job Object")
        elif os.name == "nt" and pid is None and parent_pid is None:
            launcher_pid = actual_ppid
            if launcher_pid == auth.get("child_pid"):
                grandparent_pid = get_process_parent_pid(launcher_pid)
                if grandparent_pid == auth.get("parent_pid"):
                    t_worker = get_process_creation_time(actual_pid)
                    t_stub = get_process_creation_time(launcher_pid)
                    t_runner = get_process_creation_time(grandparent_pid)
                    if t_runner and t_stub and t_worker and (t_runner <= t_stub <= t_worker):
                        if verify_in_job_object(auth.get("job_name")):
                            windows_trampoline = True

        if not (direct_match or windows_trampoline):
            raise ValueError("Process identity or ancestry verification failed")

        auth_record = {
            "authentication_path": "windows_verified_trampoline" if windows_trampoline else "direct",
            "job_name": auth.get("job_name"),
            "launcher_pid": launcher_pid if windows_trampoline else actual_pid,
            "parent_pid": grandparent_pid if windows_trampoline else actual_ppid,
            "run_id": owner["run_id"],
            "timestamp": timestamp(),
            "windows_trampoline": windows_trampoline,
            "worker_pid": actual_pid
        }
        exclusive_json(Path(output) / "control/authorization_consumed.json", auth_record)
        return owner
    except (OSError, ValueError, KeyError, TypeError):
        raise PermissionError("Internal worker authorization rejected") from None


class WritePolicy:
    """Ordinary Python writes restricted to one owned workspace + exclusive evidence.

    Never a hostile-code sandbox: native extensions and the owning OS account can
    bypass Python audit hooks. No filesystem or network isolation claim is made.
    """
    def __init__(self, workspace, evidence=None, fixture=None, subprocess_argv=None):
        self.workspace = canonical(workspace)
        self.evidence = canonical(evidence) if evidence else None
        self.fixture = canonical(fixture) if fixture else None
        self.patch_approved = False
        self.subprocess_argv = subprocess_argv

    def check(self, path, exclusive_only=False):
        if isinstance(path, int):
            return  # already-open stdio/pipe/temp descriptors; no new path opened
        path = canonical(os.fsdecode(path))
        if self.evidence and within(path, self.evidence):
            if not exclusive_only:
                raise PermissionError("Evidence writes must be exclusive")
            return
        if not within(path, self.workspace):
            raise PermissionError("Write outside owned arm workspace")
        if self.fixture and within(path, self.fixture):
            target = self.fixture / "micro_http/router.py"
            temporary = path.parent == target.parent and path.name.startswith(".litecoder-")
            if not self.patch_approved or not (path == target or temporary):
                raise PermissionError("Fixture locked until explicit patch approval; target only")

    def audit(self, event, args):
        if event == "open":
            path, mode, flags = args
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                if not isinstance(path, int) and canonical(os.fsdecode(path)) == canonical(os.devnull):
                    return  # canonical OS null-device discard sink; required for library import type probing (e.g. dill/torch)
                self.check(path, exclusive_only=bool(flags & os.O_EXCL))
        elif event in ("os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.utime", "os.truncate"):
            if event == "os.mkdir" and self.fixture and self.patch_approved:
                path = canonical(args[0])
                if path.is_dir() and within(path, self.fixture):
                    return  # baseline calls makedirs(exist_ok=True) for existing target parents
            self.check(args[0])
        elif event == "os.rename":
            self.check(args[0]); self.check(args[1])
        elif event in ("os.symlink", "os.link"):
            raise PermissionError("Aliases forbidden in arm")
        elif event in ("socket.connect", "socket.connect_ex", "socket.bind", "socket.getaddrinfo"):
            raise PermissionError("Network requests forbidden by Python audit policy")
        elif event in ("os.system", "os.exec", "os.posix_spawn", "pty.spawn"):
            raise PermissionError("Unapproved process launch")
        elif event == "subprocess.Popen":
            if self.subprocess_argv is None or len(args) < 2:
                raise PermissionError("Only the fixed guarded pytest worker may launch")
            if args[0] is not None and args[0] != self.subprocess_argv[0]:
                raise PermissionError("Only the fixed guarded pytest worker may launch")
            cmd = args[1]
            if isinstance(cmd, str):
                if cmd != subprocess.list2cmdline(self.subprocess_argv):
                    raise PermissionError("Only the fixed guarded pytest worker may launch")
            elif isinstance(cmd, (list, tuple)):
                if list(cmd) != list(self.subprocess_argv):
                    raise PermissionError("Only the fixed guarded pytest worker may launch")
            else:
                raise PermissionError("Only the fixed guarded pytest worker may launch")


class Supervisor:
    """Job created before launch, suspended Windows child attached before resume.

    POSIX children start a new process group; trusted worker waits for authorization
    on its private pipe. Windows job close kills descendants. This owns lifetimes,
    not filesystem permissions.
    """
    _active_job_name = None

    def __init__(self, name=None):
        self.lock = threading.RLock()
        self.process = None
        self.job = None
        self.job_name = None
        self.termination = {"process_exit_code": None, "job_active_processes": None}
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes as w
            class Basic(ctypes.Structure):
                _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                            ("flags", w.DWORD), ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t),
                            ("active", w.DWORD), ("affinity", ctypes.c_size_t), ("priority", w.DWORD),
                            ("scheduling", w.DWORD)]
            class IO(ctypes.Structure):
                _fields_ = [(n, ctypes.c_uint64) for n in ("ro", "wo", "oo", "rt", "wt", "ot")]
            class Extended(ctypes.Structure):
                _fields_ = [("basic", Basic), ("io", IO), ("process_mem", ctypes.c_size_t),
                            ("job_mem", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                            ("peak_job", ctypes.c_size_t)]
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
            kernel.CreateJobObjectW.restype = w.HANDLE
            kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
            kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
            kernel.CloseHandle.argtypes = [w.HANDLE]
            kernel.CloseHandle.restype = w.BOOL
            kernel.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
            kernel.TerminateJobObject.restype = w.BOOL
            kernel.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                         w.DWORD, ctypes.POINTER(w.DWORD)]
            kernel.QueryInformationJobObject.restype = w.BOOL
            kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
            kernel.OpenProcess.restype = w.HANDLE
            kernel.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
            kernel.IsProcessInJob.restype = w.BOOL
            kernel.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
            kernel.TerminateProcess.restype = w.BOOL
            kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
            kernel.WaitForSingleObject.restype = w.DWORD
            kernel.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
            kernel.GetExitCodeProcess.restype = w.BOOL
            class Accounting(ctypes.Structure):
                _fields_ = [(n, ctypes.c_int64) for n in ("user", "kernel", "period_user", "period_kernel")] + [
                    (n, w.DWORD) for n in ("faults", "total", "active", "terminated")]
            self.accounting_type = Accounting
            self.kernel = kernel
            self.job_name = name or ("Local\\LiteCoder_Job_" + uuid.uuid4().hex)
            self.job = kernel.CreateJobObjectW(None, self.job_name)
            Supervisor._active_job_name = self.job_name
            info = Extended(); info.basic.flags = 0x2000
            if not self.job or not kernel.SetInformationJobObject(self.job, 9, ctypes.byref(info), ctypes.sizeof(info)):
                self.close()
                raise OSError("Cannot establish worker job")

    def launch(self, argv, **kwargs):
        try:
            self.process = subprocess.Popen(argv, start_new_session=os.name != "nt",
                creationflags=(0x4 | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0, **kwargs)
            if os.name == "nt":
                import ctypes
                from ctypes import wintypes as w
                if not self.kernel.AssignProcessToJobObject(self.job, w.HANDLE(int(self.process._handle))):
                    raise OSError("Cannot attach suspended worker to job")
                resume = ctypes.WinDLL("ntdll").NtResumeProcess
                resume.argtypes = [w.HANDLE]; resume.restype = ctypes.c_long
                if resume(w.HANDLE(int(self.process._handle))) != 0:
                    raise OSError("Cannot resume supervised worker")
            return self.process
        except BaseException:
            try:
                self.close()
            except BaseException as cleanup_error:
                with contextlib.suppress(BaseException):
                    print("Launch cleanup failed: " + type(cleanup_error).__name__, file=sys.stderr)
            raise

    def close(self):
        deadline = time.monotonic() + 5
        if not self.lock.acquire(timeout=5):
            raise TimeoutError("Supervisor cleanup lock deadline expired")
        try:
            return self._close(deadline)
        finally:
            self.lock.release()

    def _job_pids(self, deadline):
        import ctypes
        from ctypes import wintypes as w
        capacity = 16
        while capacity <= 4096:
            class Pids(ctypes.Structure):
                _fields_ = [("assigned", w.DWORD), ("listed", w.DWORD), ("pids", ctypes.c_size_t * capacity)]
            info = Pids()
            ok = self.kernel.QueryInformationJobObject(self.job, 3, ctypes.byref(info), ctypes.sizeof(info), None)
            if ok and info.listed == info.assigned:
                return list(info.pids[:info.listed])
            if not ok and ctypes.get_last_error() != 234:
                raise ctypes.WinError(ctypes.get_last_error())
            if time.monotonic() >= deadline:
                raise TimeoutError("Job enumeration deadline expired")
            capacity = max(capacity * 2, int(info.assigned))
        raise RuntimeError("Job process enumeration exceeds containment limit")

    def _drain_job(self, deadline):
        """Retain member handles before termination; job counters are not exit barriers.

        Verify membership after OpenProcess to reject PID reuse. Stop members using
        their retained handles, collecting newly spawned descendants on each pass.
        The Job and its kill-on-close guard remain in place throughout cleanup.
        """
        import ctypes
        from ctypes import wintypes as w
        handles = {}
        observed = self.termination.setdefault("member_exits", {})
        try:
            while True:
                pids = self._job_pids(deadline)
                for pid in pids:
                    if pid in handles:
                        continue
                    handle = self.kernel.OpenProcess(0x100000 | 0x1000 | 0x1, False, pid)
                    if not handle:
                        if ctypes.get_last_error() == 87:  # process object already destroyed
                            observed[str(pid)] = {"state": "already_gone", "observed_at": timestamp()}
                            continue
                        raise ctypes.WinError(ctypes.get_last_error())
                    member = w.BOOL()
                    ok = self.kernel.IsProcessInJob(handle, self.job, ctypes.byref(member))
                    if not ok or not member.value:
                        error = ctypes.get_last_error()
                        if not self.kernel.CloseHandle(handle):
                            raise ctypes.WinError(ctypes.get_last_error())
                        if not ok:
                            raise ctypes.WinError(error)
                        continue  # PID was reused by a process outside this Job; never terminate it
                    handles[pid] = handle
                for handle in handles.values():
                    state = self.kernel.WaitForSingleObject(handle, 0)
                    if state == 258:
                        if not self.kernel.TerminateProcess(handle, 1) and ctypes.get_last_error() != 5:
                            raise ctypes.WinError(ctypes.get_last_error())
                    elif state != 0:
                        raise ctypes.WinError(ctypes.get_last_error())
                if not pids:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError("Job member shutdown deadline expired")
                time.sleep(.005)
            for pid, handle in handles.items():
                wait_ms = max(0, int((deadline - time.monotonic()) * 1000))
                result = self.kernel.WaitForSingleObject(handle, wait_ms)
                if result == 258:
                    raise TimeoutError("Job member exit was not observed before cleanup deadline")
                if result != 0:
                    raise ctypes.WinError(ctypes.get_last_error())
                code = w.DWORD()
                if not self.kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                    raise ctypes.WinError(ctypes.get_last_error())
                observed[str(pid)] = {"state": "exited", "exit_code": int(code.value), "observed_at": timestamp()}
        finally:
            for handle in handles.values():
                if not self.kernel.CloseHandle(handle):
                    self.termination.setdefault("member_handle_errors", []).append(
                        exception_details("member_handle_close", ctypes.WinError(ctypes.get_last_error())))
            if self.termination.get("member_handle_errors") and sys.exc_info()[0] is None:
                raise OSError("Failed to close Job member observation handles")

    def _close(self, deadline):
        error = None
        if self.job:
            import ctypes
            try:
                self.termination["termination_requested_at"] = timestamp()
                self._drain_job(deadline)
                if not self.kernel.TerminateJobObject(self.job, 1):
                    raise ctypes.WinError(ctypes.get_last_error())
                while True:
                    info = self.accounting_type()
                    if not self.kernel.QueryInformationJobObject(self.job, 1, ctypes.byref(info), ctypes.sizeof(info), None):
                        raise ctypes.WinError(ctypes.get_last_error())
                    self.termination["job_active_processes"] = int(info.active)
                    if not info.active:
                        self.termination["job_empty_observed_at"] = timestamp()
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Job descendants did not terminate within cleanup deadline")
                    time.sleep(.01)
            except BaseException as exc:
                error = exc
            finally:
                # Even if observation failed, retain the independent whole-Job kill
                # and checked last-handle close. Never report observation as success.
                if error is not None and not self.kernel.TerminateJobObject(self.job, 1):
                    self.termination["fallback_termination_error"] = exception_details(
                        "fallback_job_termination", ctypes.WinError(ctypes.get_last_error()))
                if self.kernel.CloseHandle(self.job):
                    self.job = None
                    self.termination["job_closed_at"] = timestamp()
                else:
                    close_error = ctypes.WinError(ctypes.get_last_error())
                    self.termination["job_close_error"] = exception_details("job_close", close_error)
                    if error is None:
                        error = close_error  # retain handle so a later close can retry
        if self.job is None and getattr(Supervisor, "_active_job_name", None) == self.job_name:
            Supervisor._active_job_name = None
        if self.process:
            try:
                self.termination["process_pid"] = self.process.pid
                if os.name != "nt":
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(self.process.pid, signal.SIGKILL)
                elif self.process.poll() is None:
                    self.process.kill()
                code = self.process.wait(timeout=max(0, deadline - time.monotonic()))
                self.termination["process_exit_code"] = code
                self.termination.setdefault("process_exit_observed_at", timestamp())
            except BaseException as exc:
                if error is None:
                    error = exc
        if error is not None:
            raise error
        return dict(self.termination)


def terminal_exception(exc):
    if isinstance(exc, KeyboardInterrupt):
        return "cancelled"
    if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)):
        return "timeout"
    if isinstance(exc, ChildProcessError):
        return "child_failure"
    return "execution_exception"


@contextlib.contextmanager
def lifecycle(evidence, **details):
    """Preserve the original BaseException even if evidence storage also fails."""
    try:
        yield details
    except BaseException as exc:
        try:
            evidence.finalize(terminal_exception(exc), error_type=type(exc).__name__,
                              traceback=traceback.format_exc(), functional_repair=None, **details)
        except BaseException as storage_error:
            with contextlib.suppress(BaseException):
                print("Terminal evidence persistence failed: " + type(storage_error).__name__, file=sys.stderr)
        raise


def review_proposal(session, evidence, policy, context, request):
    """A durable checkpoint precedes the request, and any possible fixture write."""
    proposal = session.current_diff.encode()
    patch_hash = sha(proposal)
    if patch_hash != session.current_patch_hash:
        raise ValueError("Proposal hash mismatch")
    evidence.artifact("proposed_patch.txt", proposal)
    checkpoint = evidence.event("awaiting_patch_review", **context, proposal_sha256=patch_hash)
    answer = request(checkpoint, proposal.decode())
    approved = isinstance(answer, str) and hmac.compare_digest(answer.strip(), patch_hash)
    evidence.event("patch_review_decision", proposal_sha256=patch_hash, approved=approved)
    if not approved:
        session.reject()
        return False
    policy.patch_approved = True
    return bool(session.approve(expected_patch_hash=patch_hash))
