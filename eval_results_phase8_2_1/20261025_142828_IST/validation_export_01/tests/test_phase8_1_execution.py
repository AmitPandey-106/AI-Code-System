import hashlib
import json
import os
import threading
import time
from pathlib import Path
import pytest
import app.file_transaction as files
from app.patch_engine import PatchEngine
from app.project_test_runner import ProjectTestRunner
from test_phase8_1_patches import patch


@pytest.mark.parametrize("command", ["pytest -p evil", "pytest -pevil", "pytest -c config.ini",
    "pytest -oaddopts=evil", "pytest --rootdir=..", "pytest --basetemp=../data",
    "pytest --junitxml=../outside.xml", "pytest --collect-only", "pytest --version",
    "C:/evil/pytest.exe", "python -m evil/pytest", "pytest ../tests", "pytest && echo hi"])
def test_narrow_command_policy(command):
    assert not ProjectTestRunner().is_command_allowed(command)


def test_structured_windows_argv_and_poisoned_environment(tmp_path, monkeypatch):
    runner = ProjectTestRunner()
    sub = tmp_path / "test folder"
    sub.mkdir()
    (sub / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    (tmp_path / "evil.py").write_text("raise RuntimeError('PLUGIN EXECUTED')\n")
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -p evil\n")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-p evil")
    monkeypatch.setenv("PYTEST_PLUGINS", "evil")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    result = runner.run_tests(str(tmp_path), ["python", "-m", "pytest", "test folder\\test_ok.py", "-q"])
    assert result["success"], result
    assert not runner.is_command_allowed("pytest -p evil")


def test_real_first_write_then_second_failure_restores_bytes(tmp_path, monkeypatch):
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_bytes(b"VALUE = 0\r\n"); b.write_bytes(b"VALUE = 0\n")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    hashes = {k: hashlib.sha256(v).hexdigest() for k, v in before.items()}
    original = files.atomic_write
    observed = []
    def fail_second(path, data, mode=None):
        if path.name == "b.py":
            observed.append(a.read_bytes())
            raise OSError("controlled failure after A changed")
        original(path, data, mode)
    monkeypatch.setattr(files, "atomic_write", fail_second)
    result = PatchEngine(str(tmp_path)).apply_patch(patch("a.py", "VALUE = 0", "VALUE = 1") + patch("b.py", "VALUE = 0", "VALUE = 2"))
    assert observed == [b"VALUE = 1\r\n"]
    assert not result["success"] and result["rolled_back"]
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.iterdir()} == hashes


def test_rollback_refuses_external_edits(tmp_path):
    (tmp_path / "a.py").write_bytes(b"A=0\n")
    tx = files.FileTransaction(str(tmp_path), ["a.py"])
    tx.write("a.py", b"A=1\n")
    (tmp_path / "a.py").write_bytes(b"# user work\n")
    assert not tx.rollback()
    assert "refusing to overwrite" in tx.rollback_errors[0]
    assert (tmp_path / "a.py").read_bytes() == b"# user work\n"


def test_cancel_owns_test_descendants(tmp_path):
    marker = tmp_path / "running"
    child = tmp_path / "child_survived"
    child_code = f"import time; from pathlib import Path; time.sleep(2); Path({str(child)!r}).write_text('alive')"
    (tmp_path / "test_wait.py").write_text(
        "import subprocess,sys,time\nfrom pathlib import Path\n"
        "def test_wait():\n"
        f"    subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
        f"    Path({str(marker)!r}).write_text('ready')\n"
        "    time.sleep(30)\n")
    event = threading.Event()
    results = []
    worker = threading.Thread(target=lambda: results.append(ProjectTestRunner().run_tests(str(tmp_path), "pytest test_wait.py", cancel_event=event)))
    worker.start()
    deadline = time.monotonic() + 10
    while not marker.exists() and time.monotonic() < deadline:
        event.wait(0.02)
    assert marker.exists()
    event.set()
    worker.join(10)
    assert not worker.is_alive()
    assert results[0]["status"] == "cancelled", results
    time.sleep(2.2)
    assert not child.exists()
