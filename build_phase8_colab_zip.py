#!/usr/bin/env python3
"""
LITE-Coder Phase 8 Colab Package Builder
Generates LITE_CODER_PHASE8_COLAB.zip and its SHA256 verification manifest.
"""

import os
import sys
import zipfile
import hashlib
import json
import tempfile
import shutil

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
ZIP_OUTPUT_NAME = "LITE_CODER_PHASE8_COLAB.zip"
ZIP_OUTPUT_PATH = os.path.join(REPO_ROOT, ZIP_OUTPUT_NAME)
MANIFEST_PATH = os.path.join(REPO_ROOT, "colab", "COLAB_PACKAGE_MANIFEST.json")

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def should_include(rel_path: str) -> bool:
    norm = rel_path.replace("\\", "/")

    # Exclusions
    if norm.startswith(".git/") or "/.git/" in norm or norm == ".git":
        return False
    if "__pycache__" in norm or norm.endswith(".pyc"):
        return False
    if ".pytest_cache" in norm:
        return False
    if norm.startswith("models/") or "/models/" in norm:
        return False
    if norm.startswith("venv/") or norm.startswith(".venv/"):
        return False
    if norm.endswith(".zip"):
        return False
    if norm.startswith("experiments/") and not norm.startswith("experiments/LITE_CODER_JOURNAL_DEMO"):
        return False
    if norm.startswith("scratch/"):
        return False
    if norm.startswith("LITE_CODER_Q1_") or norm.startswith("LITE-CODER_Q1_"):
        return False
    if norm.startswith("eval_results_phase") and not norm.startswith("eval_results_phase7c") and not norm.startswith("eval_results_phase8"):
        return False

    # Inclusions
    if norm.startswith("app/"):
        return True
    if norm.startswith("eval_dataset_v2/"):
        return True
    if norm.startswith("tests/"):
        return True
    if norm.startswith("colab/"):
        return True
    if norm.startswith("eval_results_phase7c/"):
        return True
    if norm in (
        "requirements.txt",
        "config.json",
        "README.md",
        "PHASE7C_MULTIREPO_BENCHMARK_REPORT.md",
        "PHASE7C_EXPERIMENTAL_INTEGRITY_AUDIT.md",
        "PHASE8_ARCHITECTURE_REPORT.md",
        "PHASE8_EXPERIMENT_PLAN.md",
        "build_phase8_colab_zip.py"
    ):
        return True

    return False

def build_package():
    print("=" * 80)
    print("BUILDING LITE-CODER PHASE 8 COLAB PACKAGE")
    print("=" * 80)

    # 1. Collect files to include
    files_to_pack = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Prune excluded directories early
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache", "venv", ".venv", "models", "scratch")]
        for f in files:
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, REPO_ROOT)
            if should_include(rel_p):
                files_to_pack.append((full_p, rel_p))

    files_to_pack.sort(key=lambda x: x[1])
    print(f"Total files identified for inclusion: {len(files_to_pack)}")

    # 2. Build Manifest
    manifest_entries = []
    total_size = 0
    for full_p, rel_p in files_to_pack:
        size = os.path.getsize(full_p)
        total_size += size
        sha = compute_sha256(full_p)
        manifest_entries.append({
            "path": rel_p.replace("\\", "/"),
            "size_bytes": size,
            "sha256": sha
        })

    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    manifest_data = {
        "package_name": "LITE-Coder Phase 8 Autonomous Engineering Package",
        "version": "1.0.0",
        "total_files": len(manifest_entries),
        "total_uncompressed_bytes": total_size,
        "files": manifest_entries
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"Manifest written to: {MANIFEST_PATH}")

    # Re-include manifest in files to pack
    files_to_pack = [(full, rel) for full, rel in files_to_pack if rel.replace("\\", "/") != "colab/COLAB_PACKAGE_MANIFEST.json"]
    files_to_pack.append((MANIFEST_PATH, "colab/COLAB_PACKAGE_MANIFEST.json"))
    files_to_pack.sort(key=lambda x: x[1])

    # 3. Create ZIP archive
    if os.path.exists(ZIP_OUTPUT_PATH):
        os.remove(ZIP_OUTPUT_PATH)

    with zipfile.ZipFile(ZIP_OUTPUT_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for full_p, rel_p in files_to_pack:
            zf.write(full_p, rel_p)

    zip_size_bytes = os.path.getsize(ZIP_OUTPUT_PATH)
    zip_size_mb = zip_size_bytes / (1024 * 1024)
    zip_sha256 = compute_sha256(ZIP_OUTPUT_PATH)

    print(f"\nPackage generated: {ZIP_OUTPUT_PATH}")
    print(f"Size: {zip_size_mb:.2f} MB ({zip_size_bytes} bytes)")
    print(f"SHA256: {zip_sha256}")

    # 4. Verification: Extract test
    print("\nVerifying package integrity by extracting into temporary sandbox...")
    with tempfile.TemporaryDirectory() as test_dir:
        with zipfile.ZipFile(ZIP_OUTPUT_PATH, "r") as zf:
            zf.extractall(test_dir)

        # Verify key files exist
        assert os.path.exists(os.path.join(test_dir, "app", "engineering_loop.py"))
        assert os.path.exists(os.path.join(test_dir, "app", "multi_file_orchestrator.py"))
        assert os.path.exists(os.path.join(test_dir, "app", "repair_memory.py"))
        assert os.path.exists(os.path.join(test_dir, "app", "strategy_selector.py"))
        assert os.path.exists(os.path.join(test_dir, "colab", "run_phase8_colab.py"))
        assert os.path.exists(os.path.join(test_dir, "eval_dataset_v2", "manifest.json"))
        assert os.path.exists(os.path.join(test_dir, "tests", "test_phase8_architecture.py"))
        print("Verification PASSED: All essential modules and tests intact.")

    return {
        "zip_path": ZIP_OUTPUT_PATH,
        "size_bytes": zip_size_bytes,
        "sha256": zip_sha256,
        "total_files": len(files_to_pack)
    }

if __name__ == "__main__":
    build_package()
