"""Run regression suites with isolated cwd/config/runtime storage; never benchmark."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CORE = ["test_patch_engine.py", "test_patch_engine_search_replace.py", "test_phase7b_patch_reliability.py",
        "test_project_test_runner.py", "test_engineering_loop.py", "test_engineering_loop_safety.py",
        "test_engineering_loop_retries.py", "test_phase8_architecture.py", "test_audit_security_boundaries.py",
        "test_repo_index.py", "test_strategy_bookkeeping.py"]


def run_suite(name, files):
    output = ROOT / "eval_results_phase8_1"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phase8-1-validation-") as temp:
        cwd = Path(temp)
        shutil.copy2(ROOT / "config.json", cwd / "config.json")
        overrides = {"STRATEGY_LEARNING_ENABLED": True} if name == "isolated_strategy_regression" else {}
        if overrides:
            fixture_config = json.loads((cwd / "config.json").read_text())
            fixture_config.update(overrides)
            (cwd / "config.json").write_text(json.dumps(fixture_config), encoding="utf-8")
        shutil.copy2(ROOT / "train_worker.py", cwd / "train_worker.py")
        env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", HF_HUB_OFFLINE="1",
                   TRANSFORMERS_OFFLINE="1", PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
        command = [sys.executable, "-m", "pytest", *[str(ROOT / "tests" / f) for f in files],
                   "-q", f"--junitxml={output / (name + '.xml')}"]
        started = time.monotonic()
        with (output / (name + ".log")).open("wb") as stream:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
        record = {"argv": command, "cwd": temp, "environment": {k: env[k] for k in (
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE")},
            "config_sha256": hashlib.sha256((ROOT / "config.json").read_bytes()).hexdigest(),
            "fixture_overrides": overrides,
            "returncode": result.returncode, "duration_s": time.monotonic() - started}
        (output / (name + "_command.json")).write_text(json.dumps(record, indent=2), encoding="utf-8")
        print((output / (name + ".log")).read_text(encoding="utf-8")[-6000:])
        return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["integration", "strategy", "all"], default="all")
    args = parser.parse_args()
    codes = []
    if args.suite in ("integration", "all"):
        codes.append(run_suite("final_integration", CORE + [p.name for p in sorted((ROOT / "tests").glob("test_phase8_1_*.py"))]))
    if args.suite in ("strategy", "all"):
        codes.append(run_suite("isolated_strategy_regression", ["test_strategy_learning.py"]))
    raise SystemExit(max(codes))
