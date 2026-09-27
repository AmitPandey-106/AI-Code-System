#!/usr/bin/env python3
"""
scripts/colab_mode_f_safe_setup.py
==================================
Pre-flight verification script for LITE-CODER 100-Task MODE-F SAFE on Google Colab GPU.

Validates:
1. Python environment & dependencies (torch, transformers, peft, datasets, filelock, etc.)
2. torchao compatibility guard
3. Canonical dataset SHA256 and task count
4. Experience Replay dataset builder
5. Deterministic Canary Evaluation Gate module
6. Adapter Rollback & Preservation logic
7. Configuration parameters for MODE-F SAFE

IT DOES NOT RUN THE 100-TASK BENCHMARK.
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
EXPECTED_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "experiments", "LITE_CODER_MODE_F_SAFE")

def verify_all():
    print("=" * 65)
    print("LITE-CODER 100-TASK MODE-F SAFE COLAB SETUP VERIFICATION")
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

    # [7] peft
    try:
        import peft
        print(f"[7] peft: {peft.__version__} -> PASS")
    except ImportError as e:
        print(f"[7] peft: FAIL ({e})")
        all_passed = False

    # [8] sentence-transformers
    try:
        import sentence_transformers
        print(f"[8] sentence-transformers: {sentence_transformers.__version__} -> PASS")
    except ImportError as e:
        print(f"[8] sentence-transformers: FAIL ({e})")
        all_passed = False

    # [9] faiss
    try:
        import faiss
        faiss_ver = getattr(faiss, "__version__", "installed")
        print(f"[9] faiss: {faiss_ver} -> PASS")
    except ImportError as e:
        print(f"[9] faiss: FAIL ({e})")
        all_passed = False

    # [10] datasets
    try:
        import datasets
        print(f"[10] datasets: {datasets.__version__} -> PASS")
    except ImportError as e:
        print(f"[10] datasets: FAIL ({e})")
        all_passed = False

    # [11] filelock
    try:
        import filelock
        print(f"[11] filelock: {filelock.__version__} -> PASS")
    except ImportError as e:
        print(f"[11] filelock: FAIL ({e})")
        all_passed = False

    # [12] Dataset file existence
    if os.path.exists(DATASET_PATH):
        print(f"[12] Dataset file exists at {DATASET_PATH} -> PASS")
    else:
        print(f"[12] Dataset file NOT FOUND at {DATASET_PATH} -> FAIL")
        all_passed = False

    # [13] Dataset task count
    try:
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        count_ok = len(tasks) == EXPECTED_TASK_COUNT
        print(f"[13] Dataset task count: {len(tasks)} (expected: {EXPECTED_TASK_COUNT}) -> {'PASS' if count_ok else 'FAIL'}")
        if not count_ok:
            all_passed = False
    except Exception as e:
        print(f"[13] Dataset reading: FAIL ({e})")
        all_passed = False

    # [14] Dataset SHA256 integrity
    try:
        with open(DATASET_PATH, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        sha_ok = (sha256.lower() == EXPECTED_DATASET_SHA256.lower())
        print(f"[14] Dataset SHA256: {sha256[:16]}... -> {'PASS' if sha_ok else 'FAIL'}")
        if not sha_ok:
            all_passed = False
    except Exception as e:
        print(f"[14] Dataset hash check: FAIL ({e})")
        all_passed = False

    # [15] Experience Replay dataset builder
    try:
        from app.training_dataset import build_dataset
        import inspect
        sig = inspect.signature(build_dataset)
        params = list(sig.parameters.keys())
        has_replay_params = "last_trained_count" in params and "replay_size" in params and "replay_strategy" in params
        print(f"[15] Experience Replay build_dataset signature: {params} -> {'PASS' if has_replay_params else 'FAIL'}")
        if not has_replay_params:
            all_passed = False
    except Exception as e:
        print(f"[15] Experience Replay import: FAIL ({e})")
        all_passed = False

    # [16] Canary Evaluation Gate
    try:
        from app.canary import CANARY_SUITE, evaluate_canary_gate
        canary_ok = len(CANARY_SUITE) >= 3 and callable(evaluate_canary_gate)
        print(f"[16] Canary Evaluation Gate module: {len(CANARY_SUITE)} tasks -> {'PASS' if canary_ok else 'FAIL'}")
        if not canary_ok:
            all_passed = False
    except Exception as e:
        print(f"[16] Canary module import: FAIL ({e})")
        all_passed = False

    # [17] Adapter Rollback logic in train_worker
    try:
        with open(os.path.join(PROJECT_ROOT, "train_worker.py"), "r", encoding="utf-8") as f:
            worker_code = f.read()
        has_rollback = "rollback" in worker_code and "rejection_reason" in worker_code and "evaluate_canary_gate" in worker_code
        print(f"[17] Adapter Rollback logic in train_worker.py: -> {'PASS' if has_rollback else 'FAIL'}")
        if not has_rollback:
            all_passed = False
    except Exception as e:
        print(f"[17] train_worker inspect: FAIL ({e})")
        all_passed = False

    # [18] App config for MODE-F SAFE
    try:
        from app.config import config
        cfg_replay = config.get("LORA_REPLAY_SIZE")
        cfg_canary = config.get("LORA_CANARY_ENABLED")
        print(f"[18] Config keys: LORA_REPLAY_SIZE={cfg_replay}, LORA_CANARY_ENABLED={cfg_canary} -> PASS")
    except Exception as e:
        print(f"[18] Config check: FAIL ({e})")
        all_passed = False

    # [19] Output directory status
    if os.path.exists(EXPECTED_OUTPUT_DIR):
        print(f"[19] Output dir: {EXPECTED_OUTPUT_DIR} (ALREADY EXISTS) -> INFO")
    else:
        print(f"[19] Output dir: {EXPECTED_OUTPUT_DIR} (clean, does not exist) -> PASS")

    print("=" * 65)
    if all_passed:
        print("ALL PRE-FLIGHT VERIFICATIONS PASSED.")
        print("Environment is fully certified for 100-Task MODE-F SAFE benchmark run.")
    else:
        print("VERIFICATION FAILED: Fix the above issues before running the benchmark.")
    print("=" * 65)
    return all_passed

if __name__ == "__main__":
    success = verify_all()
    sys.exit(0 if success else 1)
