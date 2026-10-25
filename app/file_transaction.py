"""Validated, byte-exact transactions shared by sessions and patch application.

Atomic replacement is per file. A multi-file failure restores earlier writes;
this is not a crash-recovery journal or a sandbox for executable tests.
"""
import hashlib
import ntpath
import os
import stat
import tempfile
import threading
from pathlib import Path


def safe_path(root, relative):
    if not isinstance(relative, str) or not relative or ntpath.isabs(relative):
        raise ValueError(f"SecurityViolation: unsafe path {relative!r}")
    parts = relative.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") or ":" in p or p.endswith((" ", ".")) for p in parts):
        raise ValueError(f"SecurityViolation: unsafe path {relative!r}")
    if any(p.lower() in (".git", ".agents", ".codex", ".env") for p in parts):
        raise ValueError(f"SecurityViolation: protected path {relative!r}")
    if any(ntpath.splitext(p)[0].upper() in {
        "CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)],
        *[f"LPT{i}" for i in range(1, 10)]} for p in parts):
        raise ValueError(f"SecurityViolation: reserved path {relative!r}")
    base = Path(root).resolve(strict=True)
    target = base.joinpath(*parts)
    resolved = target.resolve()
    if base not in resolved.parents:
        raise ValueError(f"SecurityViolation: path escapes repository: {relative!r}")
    cursor = target
    while cursor != base:
        if cursor.is_symlink() or (cursor.exists() and cursor.resolve() != cursor):
            raise ValueError(f"SecurityViolation: symlink/reparse path {relative!r}")
        cursor = cursor.parent
    if target.exists() and (not target.is_file() or target.stat().st_nlink > 1):
        raise ValueError(f"SecurityViolation: not a regular independent file: {relative!r}")
    return target


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else ""


def read_bytes(path):
    return path.read_bytes() if path.exists() else None


def atomic_write(path, data, mode=None):
    fd, tmp = tempfile.mkstemp(prefix=".litecoder-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


_owners = {}
_owner_lock = threading.Lock()


class RepositoryLease:
    """Nonblocking in-process reservation across mutation/testing, not inference."""
    def __init__(self, root, owner):
        self.key = os.path.normcase(os.path.realpath(root))
        self.owner = owner

    def acquire(self):
        with _owner_lock:
            if self.key in _owners and _owners[self.key] != self.owner:
                return False
            _owners[self.key] = self.owner
            return True

    def release(self):
        with _owner_lock:
            if _owners.get(self.key) == self.owner:
                del _owners[self.key]


class FileTransaction:
    def __init__(self, root, targets, expected_hashes=None):
        self.root = str(Path(root).resolve(strict=True))
        self.original = {}
        self.expected = {}
        self.modes = {}
        self.created_dirs = []
        self.rollback_errors = []
        for rel in targets:
            rel = rel.replace("\\", "/")
            if rel in self.original:
                raise ValueError(f"DuplicateTarget: {rel}")
            path = safe_path(self.root, rel)
            data = read_bytes(path)
            if expected_hashes is not None and (
                rel not in expected_hashes or digest(data) != expected_hashes[rel]
            ):
                raise ValueError(f"StaleSourceError: File '{rel}' changed after proposal.")
            self.original[rel] = data
            self.expected[rel] = data
            self.modes[rel] = stat.S_IMODE(path.stat().st_mode) if path.exists() else None

    def verify(self):
        for rel, expected in self.expected.items():
            if read_bytes(safe_path(self.root, rel)) != expected:
                raise ValueError(f"StaleSourceError: File '{rel}' changed during transaction.")

    def write(self, rel, data):
        rel = rel.replace("\\", "/")
        if rel not in self.original:
            raise ValueError(f"UnplannedTarget: {rel}")
        self.verify()
        path = safe_path(self.root, rel)
        missing = []
        parent = path.parent
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        for directory in reversed(missing):
            directory.mkdir()
            self.created_dirs.append(directory)
        atomic_write(path, data, self.modes[rel])
        self.expected[rel] = data

    def adopt(self, expected_hashes):
        """Record writes performed by a nested validated patch engine."""
        for rel in self.expected:
            current = read_bytes(safe_path(self.root, rel))
            if rel not in expected_hashes or digest(current) != expected_hashes[rel]:
                raise ValueError(f"StaleSourceError: {rel} changed after application")
            self.expected[rel] = current

    def rollback(self):
        self.rollback_errors = []
        for rel, original in reversed(list(self.original.items())):
            try:
                path = safe_path(self.root, rel)
                current = read_bytes(path)
                if current == original:
                    continue
                if current != self.expected[rel]:
                    raise ValueError("concurrent edit; refusing to overwrite")
                if original is None:
                    path.unlink()
                else:
                    atomic_write(path, original, self.modes[rel])
                if read_bytes(path) != original:
                    raise OSError("restored bytes do not match snapshot")
            except Exception as exc:
                self.rollback_errors.append(f"RollbackFailure: {rel}: {exc}")
        for directory in reversed(self.created_dirs):
            try:
                directory.rmdir()
            except OSError:
                if directory.exists() and not any(directory.iterdir()):
                    self.rollback_errors.append(f"RollbackFailure: directory {directory}")
        return not self.rollback_errors
