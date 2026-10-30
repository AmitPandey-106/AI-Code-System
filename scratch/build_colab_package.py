import os
import shutil
import hashlib
import json
import zipfile
from datetime import datetime

PROJECT_ROOT = r"D:\Amit Stuff\ai-code-system"
STAGING_DIR = os.path.join(PROJECT_ROOT, "scratch", "LITE_CODER_Q1_FINAL_COLAB_PACKAGE")
ZIP_PATH = os.path.join(PROJECT_ROOT, "LITE_CODER_Q1_FINAL_COLAB_PACKAGE.zip")

EXPECTED_BENCHMARK_HASH = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"

def get_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def ignore_pycache(dir, contents):
    return [c for c in contents if c == "__pycache__" or c.endswith(".pyc")]

def build_package():
    print("Starting package build...")
    
    # 1. Hashes
    bench_path = os.path.join(PROJECT_ROOT, "data", "benchmark", "v1.0", "dataset.json")
    runner_path = os.path.join(PROJECT_ROOT, "scripts", "run_final_experiments.py")
    
    bench_hash = get_hash(bench_path)
    runner_hash = get_hash(runner_path)
    
    if bench_hash != EXPECTED_BENCHMARK_HASH:
        print(f"STOP. Benchmark hash mismatch. Expected {EXPECTED_BENCHMARK_HASH}, got {bench_hash}")
        return False

    if os.path.exists(STAGING_DIR):
        shutil.rmtree(STAGING_DIR)
    os.makedirs(STAGING_DIR)

    # 2. Copy allowed directories and files
    shutil.copytree(os.path.join(PROJECT_ROOT, "app"), os.path.join(STAGING_DIR, "app"), ignore=ignore_pycache)
    shutil.copytree(os.path.join(PROJECT_ROOT, "benchmark"), os.path.join(STAGING_DIR, "benchmark"), ignore=ignore_pycache)
    
    os.makedirs(os.path.join(STAGING_DIR, "data", "benchmark", "v1.0"))
    shutil.copy2(bench_path, os.path.join(STAGING_DIR, "data", "benchmark", "v1.0", "dataset.json"))
    
    os.makedirs(os.path.join(STAGING_DIR, "scripts"))
    shutil.copy2(runner_path, os.path.join(STAGING_DIR, "scripts", "run_final_experiments.py"))
    
    for req_file in ["config.json", "requirements-colab.txt"]:
        src = os.path.join(PROJECT_ROOT, req_file)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(STAGING_DIR, req_file))

    # 3. Create RUN_FINAL_Q1_EXPERIMENTS.py
    run_entry_content = f"""#!/usr/bin/env python3
import os
import sys
import hashlib
import subprocess

EXPECTED_BENCHMARK_HASH = "{EXPECTED_BENCHMARK_HASH}"
EXPECTED_RUNNER_HASH = "{runner_hash}"

def get_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def main():
    print("==================================================")
    print(" LITE-CODER Q1 FINAL EXPERIMENT RUNNER")
    print("==================================================")
    
    try:
        import torch
        if not torch.cuda.is_available():
            print("ERROR: CUDA is not available. GPU is required!")
            sys.exit(1)
        print("CUDA: PASSED")
    except ImportError:
        print("ERROR: torch is not installed.")
        sys.exit(1)
        
    bench_hash = get_hash("data/benchmark/v1.0/dataset.json")
    if bench_hash != EXPECTED_BENCHMARK_HASH:
        print("ERROR: Benchmark hash mismatch!")
        sys.exit(1)
    print("Benchmark Hash: PASSED")
        
    runner_hash = get_hash("scripts/run_final_experiments.py")
    if runner_hash != EXPECTED_RUNNER_HASH:
        print("ERROR: Runner hash mismatch!")
        sys.exit(1)
    print("Runner Hash: PASSED")
    
    print("\\nExecuting approved runner...")
    subprocess.run([sys.executable, "scripts/run_final_experiments.py"], check=True)
    
    print("\\nFINAL OUTPUT LOCATIONS:")
    print("  - experiments/FINAL_Q1_EXP_01_CLEAN_BASELINE")
    print("  - experiments/FINAL_Q1_EXP_02_CLEAN_MEMORY")
    print("  - experiments/FINAL_Q1_EXP_01_EXP_02_COMPARISON.md")

if __name__ == "__main__":
    main()
"""
    with open(os.path.join(STAGING_DIR, "RUN_FINAL_Q1_EXPERIMENTS.py"), "w", newline="") as f:
        f.write(run_entry_content)

    # 4. Create setup_colab.sh
    setup_colab_content = """#!/bin/bash
echo "Installing required dependencies for LITE-CODER Colab experiments..."
# Historical environment evidence provided:
pip install torch==2.11.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install transformers==5.16.1
pip install sentence-transformers==5.7.0
pip install faiss-cpu==1.15.1
pip install peft==0.20.0
pip install accelerate>=0.26.0
pip install datasets>=2.14.0 filelock>=3.12.0 pydantic>=2.0.0 fastapi>=0.100.0 psutil>=5.9.0
echo "Setup complete."
"""
    with open(os.path.join(STAGING_DIR, "setup_colab.sh"), "w", newline="") as f:
        f.write(setup_colab_content)

    # 5. Create README_COLAB.md
    readme_content = """# LITE-CODER FINAL Q1 EXPERIMENTS

## INSTRUCTIONS
STEP 1: Upload/extract ZIP.
STEP 2: Open Google Colab.
STEP 3: Enable GPU: Runtime -> Change runtime type -> GPU
STEP 4: Verify: `torch.cuda.is_available()`
STEP 5: Run: `bash setup_colab.sh` (or `!bash setup_colab.sh` in Colab cell)
STEP 6: Run: `python RUN_FINAL_Q1_EXPERIMENTS.py`
STEP 7: Wait for: `FINAL EXPERIMENT PREFLIGHT: PASS`
STEP 8: Verify EXP_01 completion.
STEP 9: Verify EXP_02 starts with:
        Initial memory entries = 0
        Initial FAISS vectors = 0
STEP 10: After completion, collect:
        FINAL_Q1_EXP_01_CLEAN_BASELINE
        FINAL_Q1_EXP_02_CLEAN_MEMORY
        FINAL_Q1_EXP_01_EXP_02_COMPARISON.md

## SAFETY INSTRUCTIONS
- DO NOT upload the original development repository into the experiment runtime.
- DO NOT copy historical `repair_memory.json` into the package.
- DO NOT copy historical FAISS indexes.
- DO NOT manually populate EXP_02 memory.
- DO NOT modify the benchmark.
- DO NOT modify the runner after the GO audit.
- If preflight fails: STOP. Do not bypass the preflight check.

## EXPECTED OUTPUT STRUCTURE
```
experiments/
  FINAL_Q1_EXP_01_CLEAN_BASELINE/
    raw_tasks/
    statistics/
    logs/
    manifest.json
    experiment_manifest.json
    summary.json
    RESULTS.md
  FINAL_Q1_EXP_02_CLEAN_MEMORY/
    raw_tasks/
    statistics/
    logs/
    memory/
    retrieval/
    manifest.json
    experiment_manifest.json
    summary.json
    INITIAL_MEMORY_MANIFEST.json
    FINAL_MEMORY_MANIFEST.json
    RESULTS.md
  FINAL_Q1_EXP_01_EXP_02_COMPARISON.md
```
"""
    with open(os.path.join(STAGING_DIR, "README_COLAB.md"), "w", newline="") as f:
        f.write(readme_content)

    # 6. Create PACKAGE_MANIFEST.md
    manifest_content = f"""# PACKAGE MANIFEST
- Package Name: LITE_CODER_Q1_FINAL_COLAB_PACKAGE
- Creation Timestamp: {datetime.utcnow().isoformat()}Z
- Runner SHA256: {runner_hash}
- Benchmark SHA256: {bench_hash}
- Included Directories: app, benchmark, data/benchmark/v1.0, scripts
- Included Critical Files: run_final_experiments.py, dataset.json, config.json, RUN_FINAL_Q1_EXPERIMENTS.py, setup_colab.sh, README_COLAB.md
- Excluded Historical Artifacts: experiments/, all legacy data/ files, .git, old memory indices
- Python version requirement: >=3.10
- GPU requirement: Required (T4, A100, etc.)
- Dependency versions: PyTorch 2.11.0+cu128, Transformers 5.16.1, Sentence Transformers 5.7.0, FAISS 1.15.1, PEFT 0.20.0
- Expected Output Directories: experiments/FINAL_Q1_EXP_01_CLEAN_BASELINE, experiments/FINAL_Q1_EXP_02_CLEAN_MEMORY
"""
    with open(os.path.join(STAGING_DIR, "PACKAGE_MANIFEST.md"), "w", newline="") as f:
        f.write(manifest_content)

    # 7. Package Integrity Check
    print("Running Package Validation...")
    checks = {
        "runner exists": os.path.exists(os.path.join(STAGING_DIR, "scripts", "run_final_experiments.py")),
        "runner hash recorded": runner_hash is not None,
        "benchmark exists": os.path.exists(os.path.join(STAGING_DIR, "data", "benchmark", "v1.0", "dataset.json")),
        "benchmark hash correct": get_hash(os.path.join(STAGING_DIR, "data", "benchmark", "v1.0", "dataset.json")) == EXPECTED_BENCHMARK_HASH,
        "no repair_memory.json exists": not os.path.exists(os.path.join(STAGING_DIR, "data", "repair_memory.json")),
        "no FAISS memory index exists": not os.path.exists(os.path.join(STAGING_DIR, "data", "repair_memory_index.faiss")),
        "no historical experiment output exists": not os.path.exists(os.path.join(STAGING_DIR, "experiments")),
        "no old MODE_A/D/F/F_SAFE results exist": not os.path.exists(os.path.join(STAGING_DIR, "experiments", "LITE_CODER_100TASK_MODE_A")),
        "required application modules exist": os.path.exists(os.path.join(STAGING_DIR, "app")),
        "requirements exist": os.path.exists(os.path.join(STAGING_DIR, "requirements-colab.txt")),
        "Colab entrypoint exists": os.path.exists(os.path.join(STAGING_DIR, "RUN_FINAL_Q1_EXPERIMENTS.py")),
        "setup script exists": os.path.exists(os.path.join(STAGING_DIR, "setup_colab.sh")),
        "README exists": os.path.exists(os.path.join(STAGING_DIR, "README_COLAB.md")),
        "package manifest exists": os.path.exists(os.path.join(STAGING_DIR, "PACKAGE_MANIFEST.md"))
    }
    
    validation_pass = all(checks.values())
    for k, v in checks.items():
        print(f"[{'X' if v else ' '}] {k}")
        
    if not validation_pass:
        print("STOP. Package validation failed.")
        return False

    print("Creating ZIP file...")
    with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(STAGING_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, STAGING_DIR)
                # Nest under LITE_CODER_Q1_FINAL_COLAB_PACKAGE
                zip_name = os.path.join("LITE_CODER_Q1_FINAL_COLAB_PACKAGE", rel_path)
                zf.write(abs_path, zip_name)
                
    zip_size = os.path.getsize(ZIP_PATH)
    
    print("\\n==================================================")
    print("FINAL SUMMARY")
    print("==================================================")
    print("ZIP CREATED: YES")
    print(f"ZIP PATH:\\n{ZIP_PATH}")
    print(f"ZIP SIZE:\\n{zip_size} bytes")
    print(f"RUNNER SHA256:\\n{runner_hash}")
    print(f"BENCHMARK SHA256:\\n{bench_hash}")
    print("PACKAGE VALIDATION:\\nPASS")
    print("EXPERIMENTS EXECUTED:\\nNO")
    print("HISTORICAL DATA MODIFIED:\\nNO")
    print("SOURCE ALGORITHMS MODIFIED:\\nNO")
    print("BENCHMARK MODIFIED:\\nNO")

if __name__ == "__main__":
    build_package()
