#!/usr/bin/env python3
"""
scripts/colab_mode_f_trained_setup.py
=====================================
Pre-flight verification script for LITE-CODER 100-Task MODE-F Trained on Google Colab GPU.

This script validates the complete environment, dataset integrity, and configuration.
IT DOES NOT RUN THE BENCHMARK.
"""

import sys
import os
import hashlib
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

EXPECTED_DATASET_SHA256 = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"
EXPECTED_TASK_COUNT = 100
DATASET_PATH = os.path.join(PROJECT_ROOT, "data", "benchmark", "v1.0", "dataset.json")
EXPECTED_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "experiments", "LITE_CODER_100TASK_MODE_F_TRAINED")

def verify_all():
    print("=" * 65)
    print("LITE-CODER 100-TASK MODE-F TRAINED COLAB SETUP VERIFICATION")
    print("=" * 65)
    all_passed = True

    # [1] Python version
    py_ver = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 10)
    print(f"[1] Python Version: {py_ver} -> {'PASS' if py_ok else 'FAIL (requires >=3.10)'}")
    if not py_ok:
        all_passed = False

    # [2] PyTorch version
    try:
        import torch
        torch_ver = torch.__version__
        print(f"[2] PyTorch Version: {torch_ver} -> PASS")
    except ImportError as e:
        print(f"[2] PyTorch: FAIL ({e})")
        all_passed = False
        torch = None

    # [3] CUDA availability
    cuda_avail = torch.cuda.is_available() if torch else False
    print(f"[3] CUDA Available: {cuda_avail} -> {'PASS (GPU)' if cuda_avail else 'INFO (CPU fallback/local)'}")

    # [4] GPU name
    if cuda_avail:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[4] GPU Name: {gpu_name} ({gpu_mem:.1f} GB VRAM) -> PASS")
    else:
        print("[4] GPU Name: N/A (Running on CPU)")

    # [5] transformers
    try:
        import transformers
        print(f"[5] transformers: {transformers.__version__} -> PASS")
    except ImportError as e:
        print(f"[5] transformers: FAIL ({e})")
        all_passed = False

    # [6] accelerate
    try:
        import accelerate
        print(f"[6] accelerate: {accelerate.__version__} -> PASS")
    except ImportError as e:
        print(f"[6] accelerate: FAIL ({e})")
        all_passed = False

    # [7] peft (CRITICAL for MODE-F LoRA fine-tuning and adapter loading)
    try:
        import peft
        print(f"[7] peft: {peft.__version__} -> PASS")
    except ImportError as e:
        print(f"[7] peft: FAIL ({e})")
        all_passed = False

    # [8] sentence-transformers (CRITICAL for MODE-F memory embedding)
    try:
        import sentence_transformers
        print(f"[8] sentence-transformers: {sentence_transformers.__version__} -> PASS")
    except ImportError as e:
        print(f"[8] sentence-transformers: FAIL ({e})")
        all_passed = False

    # [9] faiss (CRITICAL for MODE-F repair experience indexing)
    try:
        import faiss
        faiss_ver = getattr(faiss, "__version__", "installed")
        print(f"[9] faiss: {faiss_ver} -> PASS")
    except ImportError as e:
        print(f"[9] faiss: FAIL ({e})")
        all_passed = False

    # [10] Dataset SHA256
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "rb") as f:
            ds_hash = hashlib.sha256(f.read()).hexdigest()
        hash_ok = (ds_hash.lower() == EXPECTED_DATASET_SHA256.lower())
        print(f"[10] Dataset Hash: {ds_hash} -> {'PASS' if hash_ok else 'FAIL (hash mismatch)'}")
        if not hash_ok:
            all_passed = False
    else:
        print(f"[10] Dataset: FAIL (not found at {DATASET_PATH})")
        all_passed = False

    # [11] Dataset task count == 100
    ds_data = []
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            ds_data = json.load(f)
        task_count = len(ds_data)
        count_ok = (task_count == EXPECTED_TASK_COUNT)
        print(f"[11] Dataset Task Count == 100: {task_count} -> {'PASS' if count_ok else 'FAIL'}")
        if not count_ok:
            all_passed = False
    else:
        all_passed = False

    # [12] MODE-F configuration
    from app.config import config
    from benchmark.ablation import apply_ablation_mode
    apply_ablation_mode("MODE_F")
    mode_f_ok = (
        config.get("MEMORY_ENABLED") is True
        and config.get("STRATEGY_LEARNING_ENABLED") is True
        and config.get("LORA_ENABLED") is True
        and config.get("DIFFICULTY_ALLOCATION_ENABLED") is True
        and config.get("DETERMINISTIC_GENERATION") is True
        and config.get("BENCHMARK_SEED") == 42
    )
    print(f"[12] MODE-F Configuration: {'PASS' if mode_f_ok else 'FAIL'}")
    if not mode_f_ok:
        all_passed = False

    # [13] Fix A present
    main_path = os.path.join(PROJECT_ROOT, "app", "main.py")
    if os.path.exists(main_path):
        with open(main_path, "r", encoding="utf-8") as f:
            main_code = f.read()
        fix_a_found = (
            'next_err = next_att.get("error_type") or ""' in main_code
            and 'sec_viol = "SecurityViolation" in next_err' in main_code
            and 't_out = "TimeoutError" in next_err' in main_code
        )
        print(f"[13] Fix A in app/main.py: {'PASS (Found)' if fix_a_found else 'FAIL (Missing)'}")
        if not fix_a_found:
            all_passed = False
    else:
        print("[13] Fix A: FAIL (app/main.py missing)")
        all_passed = False

    # [14] Fix B absent, unless MODE-F explicitly requires it
    fix_b_found = 'if not config.get("STRATEGY_LEARNING_ENABLED"):' in main_code if os.path.exists(main_path) else False
    print(f"[14] Fix B Absent in app/main.py: {'PASS (Correctly Absent)' if not fix_b_found else 'FAIL (Fix B is present)'}")
    if fix_b_found:
        all_passed = False

    # [15] Base model
    from app.model import base_model_name
    print(f"[15] Base Model: '{base_model_name}' (MODE-F LoRA enabled=True) -> PASS")

    # [16] Output directory is clean
    if os.path.exists(EXPECTED_OUTPUT_DIR):
        print(f"[16] Output Directory: INFO ({os.path.relpath(EXPECTED_OUTPUT_DIR, PROJECT_ROOT)} already exists)")
    else:
        print(f"[16] Output Directory: PASS ({os.path.relpath(EXPECTED_OUTPUT_DIR, PROJECT_ROOT)} clean for MODE-F Trained run)")

    # [17] Exact task count == 100
    print(f"[17] Exact Task Count == 100: {len(ds_data)} == 100 -> {'PASS' if len(ds_data) == 100 else 'FAIL'}")
    if len(ds_data) != 100:
        all_passed = False

    # [18] Exact task IDs and uniqueness
    task_ids = [t.get("task_id") for t in ds_data]
    unique_ids = set(task_ids)
    ids_ok = (len(task_ids) == 100 and len(unique_ids) == 100 and all(tid.startswith("TASK_") for tid in task_ids))
    print(f"[18] Exact Task IDs and Uniqueness: 100 unique valid IDs -> {'PASS' if ids_ok else 'FAIL'}")
    if not ids_ok:
        all_passed = False

    # [19] Required dependencies
    req_deps = ["torch", "transformers", "accelerate", "peft", "safetensors", "sentence_transformers", "faiss", "numpy", "fastapi", "pydantic", "psutil"]
    missing_deps = []
    for d in req_deps:
        try:
            __import__(d)
        except ImportError:
            missing_deps.append(d)
    print(f"[19] Required Dependencies: {'PASS (All present)' if not missing_deps else f'FAIL (Missing: {missing_deps})'}")
    if missing_deps:
        all_passed = False

    # [20] MODE-F Specific Dependencies (datasets, filelock)
    mode_f_deps = ["datasets", "filelock"]
    missing_mode_f_deps = []
    for d in mode_f_deps:
        try:
            __import__(d)
        except ImportError:
            missing_mode_f_deps.append(d)
    print(f"[20] MODE-F Specific Dependencies (datasets, filelock): {'PASS (All present)' if not missing_mode_f_deps else f'FAIL (Missing: {missing_mode_f_deps})'}")
    if missing_mode_f_deps:
        all_passed = False

    # [21] LoRA Worker & Trainer Verification
    try:
        from train_worker import run_training_pipeline
        print("[21] LoRA Training Worker Pipeline: PASS (run_training_pipeline importable)")
    except Exception as e:
        print(f"[21] LoRA Training Worker: FAIL ({e})")
        all_passed = False

    print("=" * 65)
    if all_passed:
        print("READY FOR 100-TASK MODE-F TRAINED RUN")
    else:
        print("VERIFICATION FAILED")
    print("=" * 65)
    return all_passed

if __name__ == "__main__":
    success = verify_all()
    sys.exit(0 if success else 1)
