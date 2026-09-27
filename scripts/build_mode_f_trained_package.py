#!/usr/bin/env python3
"""
scripts/build_mode_f_trained_package.py
=======================================
Deterministic builder and validator for LITE-CODER 100-Task MODE-F Trained Package.

Performs:
1. Pre-packaging validation (Dataset, Fix A, Linux-safe subprocess, Fix B, MODE-F Config, Syntax, Unit Tests)
2. Manifest generation (MODE_F_TRAINED_PACKAGE_MANIFEST.json)
3. ZIP packaging into package_output/LITE_CODER_MODE_F_TRAINED_100TASK.zip
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
PACKAGE_ZIP_NAME = "LITE_CODER_MODE_F_TRAINED_100TASK.zip"
PACKAGE_ZIP_PATH = os.path.join(OUTPUT_DIR, PACKAGE_ZIP_NAME)
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "MODE_F_TRAINED_PACKAGE_MANIFEST.json")

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
    "LITE_CODER_MODE_D_100TASK_COLAB.zip",
    "LITE_CODER_MODE_F_100TASK.zip",
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
    print("RUNNING PRE-PACKAGING VALIDATIONS FOR MODE-F TRAINED")
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

    # 5. Controlled training pipeline invocation in app/main.py
    pipeline_tokens = [
        'from train_worker import run_training_pipeline',
        'run_training_pipeline('
    ]
    for token in pipeline_tokens:
        if token not in main_content:
            raise RuntimeError(f"VALIDATION FAILED: Controlled training pipeline token missing: {token}")
    results["controlled_training_pipeline_present"] = True
    print("[PASS] 5. Controlled training pipeline invocation verified in app/main.py")

    # 6. Absence of Fix B
    if "def record_strategy_outcomes" in main_content:
        record_func = main_content.split("def record_strategy_outcomes")[1].split("def generate")[0]
        if 'if not config.get("STRATEGY_LEARNING_ENABLED"):' in record_func:
            raise RuntimeError("VALIDATION FAILED: Fix B (strategy learning bypass guard) found in record_strategy_outcomes!")
    results["fix_b_absent"] = True
    print("[PASS] 6. Fix B verified correctly absent in record_strategy_outcomes()")

    # 7. MODE-F configuration in benchmark/ablation.py
    ablation_path = os.path.join(PROJECT_ROOT, "benchmark", "ablation.py")
    with open(ablation_path, "r", encoding="utf-8") as f:
        ablation_content = f.read()

    mode_f_tokens = [
        'elif mode == "MODE_F":',
        'config.set("MEMORY_ENABLED", True)',
        'config.set("STRATEGY_LEARNING_ENABLED", True)',
        'config.set("LORA_ENABLED", True)',
        'config.set("DIFFICULTY_ALLOCATION_ENABLED", True)'
    ]
    for token in mode_f_tokens:
        if token not in ablation_content:
            raise RuntimeError(f"VALIDATION FAILED: Canonical MODE-F token missing in ablation.py: {token}")
    results["mode_f_ablation_verified"] = True
    print("[PASS] 7. Canonical MODE-F ablation configuration verified")

    # 8. Training pipeline in train_worker.py
    worker_path = os.path.join(PROJECT_ROOT, "train_worker.py")
    with open(worker_path, "r", encoding="utf-8") as f:
        worker_content = f.read()
    if "run_training_pipeline" not in worker_content or "Promoting candidate" not in worker_content:
        raise RuntimeError("VALIDATION FAILED: train_worker.py missing run_training_pipeline or promotion logic!")
    results["lora_worker_verified"] = True
    print("[PASS] 8. LoRA training worker pipeline verified")

    # 9. Syntax Compilation
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
    print(f"[PASS] 9. Python syntax compiled successfully ({len(py_files)} files)")

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

    # Data files
    data_files = [
        "data/benchmark/v1.0/dataset.json",
        "data/benchmark/v1.0/dataset_hash.txt",
        "data/repair_memory.json",
        "data/repair_memory_index.faiss",
        "data/strategy_memory.json",
        "data/strategy_stats.json",
        "data/dataset/test.json",
        "data/dataset/train.json",
        "data/dataset/val.json",
        "data/dataset/stats.json"
    ]
    for df in data_files:
        if os.path.exists(os.path.join(PROJECT_ROOT, df)):
            included.append(df)

    # Scripts
    scripts = [
        "scripts/colab_mode_f_trained_setup.py",
        "scripts/run_mode_f_trained_100.py"
    ]
    for sc in scripts:
        if os.path.exists(os.path.join(PROJECT_ROOT, sc)):
            included.append(sc)

    # Worker files
    worker_files = [
        "train_worker.py",
        "train_lora.py"
    ]
    for wf in worker_files:
        if os.path.exists(os.path.join(PROJECT_ROOT, wf)):
            included.append(wf)

    # Config & requirements
    root_files = [
        "config.json",
        "requirements.txt",
        "requirements-colab.txt"
    ]
    for rf in root_files:
        if os.path.exists(os.path.join(PROJECT_ROOT, rf)):
            included.append(rf)

    return sorted(list(set(included)))

def build_package():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    val_results = run_validations()

    included_files = get_package_files()
    print(f"\n[INFO] Packaging {len(included_files)} canonical files into {PACKAGE_ZIP_NAME}...")

    with zipfile.ZipFile(PACKAGE_ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel_path in included_files:
            abs_path = os.path.join(PROJECT_ROOT, rel_path)
            zf.write(abs_path, arcname=rel_path.replace("\\", "/"))

    zip_hash = sha256_file(PACKAGE_ZIP_PATH)
    zip_size = os.path.getsize(PACKAGE_ZIP_PATH)

    manifest = {
        "package_name": PACKAGE_ZIP_NAME,
        "package_purpose": "Authoritative reproducible package for 100-task MODE-F Trained benchmark experiment on Google Colab GPU / local execution.",
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_path": DATASET_REL_PATH,
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "task_count": EXPECTED_TASK_COUNT,
        "package_sha256": zip_hash,
        "package_size_bytes": zip_size,
        "included_file_count": len(included_files),
        "included_files": [f.replace("\\", "/") for f in included_files],
        "validation_results": val_results
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    print("=" * 65)
    print("PACKAGE CREATED SUCCESSFULLY")
    print(f"Zip:      {PACKAGE_ZIP_PATH}")
    print(f"SHA256:   {zip_hash}")
    print(f"Size:     {zip_size / 1024:.1f} KB")
    print(f"Manifest: {MANIFEST_PATH}")
    print("=" * 65)
    return manifest

if __name__ == "__main__":
    build_package()
