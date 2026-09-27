#!/usr/bin/env python3
"""
scripts/build_mode_d_package.py
===============================
Deterministic builder and validator for LITE-CODER 100-Task MODE-D Package.

Performs:
1. Pre-packaging validation (Dataset, Fix A, Fix B, MODE-D Config, Syntax, Unit Tests)
2. Manifest generation (MODE_D_PACKAGE_MANIFEST.json)
3. ZIP packaging into package_output/LITE_CODER_MODE_D_100TASK_COLAB.zip
4. Post-packaging verification (ZIP integrity, file inventory, exclusion verification, SHA256, file size)
"""

import os
import sys
import json
import zipfile
import hashlib
import py_compile
import subprocess
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "package_output")
PACKAGE_ZIP_NAME = "LITE_CODER_MODE_D_100TASK_COLAB.zip"
PACKAGE_ZIP_PATH = os.path.join(OUTPUT_DIR, PACKAGE_ZIP_NAME)
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "MODE_D_PACKAGE_MANIFEST.json")

EXPECTED_DATASET_SHA256 = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"
EXPECTED_TASK_COUNT = 100
DATASET_REL_PATH = "data/benchmark/v1.0/dataset.json"

EXCLUDED_PATTERNS = [
    "venv", ".venv", ".git", ".pytest_cache", ".ipynb_checkpoints",
    "__pycache__", ".pyc", ".pyo", "experiments", "models",
    "lora-finetuned", "lora-output", "package_output",
    "LITE_CODER_PHASE3_24TASK_FIX_A_FROZEN.zip",
    "LITE_CODER_PHASE3_COLAB_24TASK_FIX_A.zip",
    "LITE_CODER_MODE_A_100TASK_FIX_A.zip",
    "LITE_CODER_MODE_A_100TASK_BASELINE_FINAL.zip",
    "research/evidence",
    "gcm-diagnose.log"
]

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def run_validations():
    print("=" * 65)
    print("RUNNING PRE-PACKAGING VALIDATIONS FOR MODE-D")
    print("=" * 65)
    results = {}

    # 1. Dataset existence
    dataset_abs = os.path.join(PROJECT_ROOT, DATASET_REL_PATH)
    if not os.path.exists(dataset_abs):
        raise RuntimeError(f"VALIDATION FAILED: Dataset not found at {dataset_abs}")
    results["dataset_exists"] = True
    print("[PASS] 1. Dataset exists")

    # 2. Dataset task count
    with open(dataset_abs, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    if len(tasks) != EXPECTED_TASK_COUNT:
        raise RuntimeError(f"VALIDATION FAILED: Expected {EXPECTED_TASK_COUNT} tasks, got {len(tasks)}")
    results["dataset_task_count"] = len(tasks)
    print(f"[PASS] 2. Dataset task count is exactly {len(tasks)}")

    # 3. Dataset SHA256
    ds_hash = sha256_file(dataset_abs)
    if ds_hash.lower() != EXPECTED_DATASET_SHA256.lower():
        raise RuntimeError(f"VALIDATION FAILED: Dataset SHA256 mismatch! Got {ds_hash}, expected {EXPECTED_DATASET_SHA256}")
    results["dataset_sha256"] = ds_hash
    print(f"[PASS] 3. Dataset SHA256 matches: {ds_hash}")

    # 4. Fix A in app/main.py
    main_path = os.path.join(PROJECT_ROOT, "app", "main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        main_content = f.read()

    fix_a_tokens = [
        'next_err = next_att.get("error_type") or ""',
        'sec_viol = "SecurityViolation" in next_err',
        't_out = "TimeoutError" in next_err'
    ]
    for token in fix_a_tokens:
        if token not in main_content:
            raise RuntimeError(f"VALIDATION FAILED: Fix A token missing in app/main.py: {token}")
    results["fix_a_present"] = True
    print("[PASS] 4. Fix A verified in app/main.py")

    # 5. Fix B absent
    if 'if not config.get("STRATEGY_LEARNING_ENABLED"):' in main_content:
        raise RuntimeError("VALIDATION FAILED: Fix B is present in app/main.py! It must NOT be implemented.")
    results["fix_b_absent"] = True
    print("[PASS] 5. Fix B confirmed ABSENT in app/main.py")

    # 6. MODE-D Configuration
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if cfg.get("MEMORY_ENABLED") is not True:
        raise RuntimeError("VALIDATION FAILED: MEMORY_ENABLED must be True for MODE-D in config.json")
    if cfg.get("STRATEGY_LEARNING_ENABLED") is not True:
        raise RuntimeError("VALIDATION FAILED: STRATEGY_LEARNING_ENABLED must be True for MODE-D in config.json")
    if cfg.get("LORA_ENABLED") is not False:
        raise RuntimeError("VALIDATION FAILED: LORA_ENABLED must be False for MODE-D in config.json")
    if cfg.get("DIFFICULTY_ALLOCATION_ENABLED") is not True:
        raise RuntimeError("VALIDATION FAILED: DIFFICULTY_ALLOCATION_ENABLED must be True for MODE-D in config.json")
    if cfg.get("BENCHMARK_SEED") != 42:
        raise RuntimeError("VALIDATION FAILED: BENCHMARK_SEED must be 42 in config.json")
    if cfg.get("DETERMINISTIC_GENERATION") is not True:
        raise RuntimeError("VALIDATION FAILED: DETERMINISTIC_GENERATION must be True in config.json")
    results["mode_d_configuration"] = "PASSED"
    print("[PASS] 6. MODE-D configuration verified in config.json")

    # 7. Clean State Files
    state_checks = {
        "data/repair_memory.json": "[]",
        "data/strategy_memory.json": "[]",
        "data/strategy_stats.json": "{}"
    }
    for sf, expected_content in state_checks.items():
        sf_path = os.path.join(PROJECT_ROOT, sf)
        if os.path.exists(sf_path):
            with open(sf_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if len(data) != 0:
                raise RuntimeError(f"VALIDATION FAILED: State file {sf} is not empty! Found {len(data)} items.")
        else:
            raise RuntimeError(f"VALIDATION FAILED: State file {sf} is missing.")
    results["state_files_clean"] = True
    print("[PASS] 7. Memory and Strategy state files confirmed clean and empty")

    # 8. Syntax Compilation
    py_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if not any(ex in os.path.join(root, d) for ex in [
            "venv", ".venv", ".git", ".pytest_cache", "__pycache__", "experiments", "models", "package_output"
        ])]
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))

    for p in py_files:
        try:
            py_compile.compile(p, doraise=True)
        except Exception as e:
            raise RuntimeError(f"VALIDATION FAILED: Syntax error compiling {p}: {e}")
    results["syntax_compiled_count"] = len(py_files)
    print(f"[PASS] 8. Python syntax compiled successfully ({len(py_files)} files)")

    # 9. Lightweight Unit Tests Execution
    test_files = [
        "tests/test_benchmark.py",
        "tests/test_fault_injection.py",
        "tests/test_forgetting.py",
        "tests/test_infrastructure.py",
        "tests/test_runner_error_handling.py",
        "tests/test_strategy_bookkeeping.py",
        "tests/test_strategy_learning.py"
    ]
    python_exe = sys.executable
    for tf in test_files:
        tf_abs = os.path.join(PROJECT_ROOT, tf)
        cmd = [python_exe, "-m", "pytest", tf_abs]
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"VALIDATION FAILED: Unit test {tf} failed!\n{proc.stdout}\n{proc.stderr}")
    results["unit_tests"] = "PASSED (all lightweight tests passed)"
    print(f"[PASS] 9. Lightweight unit tests executed and passed ({len(test_files)} test suites)")

    # Reset state again to ensure unit tests didn't leave test records in state files
    for sf, initial_obj in [("data/repair_memory.json", []), ("data/strategy_memory.json", []), ("data/strategy_stats.json", {})]:
        with open(os.path.join(PROJECT_ROOT, sf), "w", encoding="utf-8") as fp:
            json.dump(initial_obj, fp)

    return results

def get_package_files():
    """Returns an explicit, clean list of relative file paths to include."""
    included = []

    # App files
    for root, _, files in os.walk(os.path.join(PROJECT_ROOT, "app")):
        if "__pycache__" in root: continue
        for f in files:
            if f.endswith(".py"):
                included.append(os.path.relpath(os.path.join(root, f), PROJECT_ROOT))

    # Benchmark files
    for root, _, files in os.walk(os.path.join(PROJECT_ROOT, "benchmark")):
        if "__pycache__" in root: continue
        for f in files:
            if f.endswith(".py"):
                included.append(os.path.relpath(os.path.join(root, f), PROJECT_ROOT))

    # Data files (canonical dataset and initial state files)
    data_files = [
        "data/benchmark/v1.0/dataset.json",
        "data/benchmark/v1.0/dataset_hash.txt",
        "data/repair_memory.json",
        "data/repair_memory_index.faiss",
        "data/strategy_memory.json",
        "data/strategy_stats.json"
    ]
    for df in data_files:
        if os.path.exists(os.path.join(PROJECT_ROOT, df)):
            included.append(df)

    # Scripts
    scripts = [
        "scripts/colab_mode_d_setup.py",
        "scripts/run_mode_d_100.py"
    ]
    for sc in scripts:
        if os.path.exists(os.path.join(PROJECT_ROOT, sc)):
            included.append(sc)

    # Tests
    for root, _, files in os.walk(os.path.join(PROJECT_ROOT, "tests")):
        if "__pycache__" in root: continue
        for f in files:
            if f.endswith(".py"):
                included.append(os.path.relpath(os.path.join(root, f), PROJECT_ROOT))

    # Research audit tools (lightweight inspection script)
    audit_files = [
        "research/audit/forensic_audit.py",
        "research/audit/dataset_identity_audit.py"
    ]
    for af in audit_files:
        if os.path.exists(os.path.join(PROJECT_ROOT, af)):
            included.append(af)

    # Root config and documentation files
    root_files = [
        "config.json",
        "requirements.txt",
        "requirements-colab.txt",
        "README_MODE_D_100TASK.md"
    ]
    for rf in root_files:
        if os.path.exists(os.path.join(PROJECT_ROOT, rf)):
            included.append(rf)

    # Normalize slashes to forward slashes
    included = sorted(list(set(p.replace("\\", "/") for p in included)))
    return included

def create_manifest(validation_results, included_files):
    manifest = {
        "package_name": PACKAGE_ZIP_NAME,
        "package_purpose": "Authoritative, clean reproducible package for the 100-task MODE-D benchmark experiment on Google Colab GPU.",
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        "project_path": PROJECT_ROOT,
        "dataset_path": DATASET_REL_PATH,
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "task_count": EXPECTED_TASK_COUNT,
        "fix_a_status": "PRESENT (next_err = next_att.get('error_type') or '')",
        "fix_b_status": "CORRECTLY ABSENT (no strategy learning bypass guard)",
        "mode_d_status": "VERIFIED (MEMORY_ENABLED=True, STRATEGY_LEARNING_ENABLED=True, LORA_ENABLED=False, DIFFICULTY_ALLOCATION_ENABLED=True, BENCHMARK_SEED=42, DETERMINISTIC_GENERATION=True)",
        "included_file_count": len(included_files) + 2,  # +2 for README.md and manifest itself
        "included_files": included_files + ["README.md", "MODE_D_PACKAGE_MANIFEST.json"],
        "excluded_directories": [
            "venv/", ".venv/", ".git/", ".pytest_cache/", ".ipynb_checkpoints/",
            "__pycache__/", "experiments/", "models/", "lora-finetuned/",
            "lora-output/", "package_output/", "research/evidence/"
        ],
        "validation_results": validation_results,
        "python_runtime_requirements": {
            "python_version": ">=3.10",
            "recommended_gpu": "Google Colab GPU (T4, V100, A100)",
            "key_dependencies": [
                "torch>=2.0.0",
                "transformers>=4.45.0",
                "accelerate>=0.26.0",
                "peft>=0.10.0",
                "sentence-transformers>=2.2.0",
                "faiss-cpu>=1.7.4",
                "numpy>=1.24.0",
                "fastapi>=0.100.0",
                "pydantic>=2.0.0",
                "psutil>=5.9.0"
            ]
        },
        "model_configuration": {
            "base_model": "Qwen/Qwen2.5-Coder-1.5B",
            "lora_required": False,
            "lora_enabled": False,
            "memory_enabled": True,
            "strategy_learning_enabled": True,
            "difficulty_allocation_enabled": True,
            "deterministic_generation": True,
            "benchmark_seed": 42
        },
        "research_integrity_declaration": {
            "benchmark_executed_during_packaging": False,
            "statement": "The 100-task MODE-D benchmark was NOT executed during packaging. This package contains unexecuted clean code and canonical dataset for fresh execution on Google Colab.",
            "mode_a_baseline_isolation": "MODE-A 100-task baseline results are separate frozen evidence and are strictly excluded from this package."
        }
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
    print(f"[PASS] Manifest created: {MANIFEST_PATH}")
    return manifest

def build_zip(included_files):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_files = list(included_files)

    print(f"\nBuilding ZIP archive at: {PACKAGE_ZIP_PATH}")
    with zipfile.ZipFile(PACKAGE_ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in all_files:
            abs_path = os.path.join(PROJECT_ROOT, rel_path)
            if not os.path.exists(abs_path):
                raise RuntimeError(f"Packaging error: file not found {abs_path}")
            zf.write(abs_path, arcname=rel_path)

        # Write README.md as duplicate of README_MODE_D_100TASK.md
        zf.write(os.path.join(PROJECT_ROOT, "README_MODE_D_100TASK.md"), arcname="README.md")
        # Write MANIFEST
        zf.write(MANIFEST_PATH, arcname="MODE_D_PACKAGE_MANIFEST.json")

    zip_size = os.path.getsize(PACKAGE_ZIP_PATH)
    zip_sha = sha256_file(PACKAGE_ZIP_PATH)
    print(f"[PASS] ZIP Created: {zip_size:,} bytes")
    print(f"[PASS] ZIP SHA256:  {zip_sha}")

    # Post-packaging verification
    print("\nVerifying ZIP integrity...")
    with zipfile.ZipFile(PACKAGE_ZIP_PATH, "r") as zf:
        corrupt = zf.testzip()
        if corrupt is not None:
            raise RuntimeError(f"ZIP VERIFICATION FAILED: Corrupted file inside ZIP: {corrupt}")
        namelist = zf.namelist()
        for name in namelist:
            for exc in ["venv/", ".git/", ".pytest_cache/", "__pycache__/", ".pyc", "experiments/", "models/"]:
                if exc in name:
                    raise RuntimeError(f"ZIP VERIFICATION FAILED: Excluded item found in zip: {name}")

    print(f"[PASS] ZIP verified cleanly with {len(namelist)} entries. 0 corrupted files, 0 forbidden exclusions.")
    return zip_size, zip_sha, len(namelist)

def main():
    validation_results = run_validations()
    included_files = get_package_files()
    manifest = create_manifest(validation_results, included_files)
    zip_size, zip_sha, count = build_zip(included_files)

    print("\n" + "=" * 65)
    print("MODE-D PACKAGE BUILD COMPLETED SUCCESSFULLY")
    print(f"ZIP File:    {PACKAGE_ZIP_PATH}")
    print(f"ZIP Size:    {zip_size:,} bytes ({zip_size / 1024:.1f} KB)")
    print(f"ZIP SHA256:  {zip_sha}")
    print(f"File Count:  {count}")
    print("=" * 65)

if __name__ == "__main__":
    main()
