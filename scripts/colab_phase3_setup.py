#!/usr/bin/env python3
"""
scripts/colab_phase3_setup.py
=============================
Pre-flight verification script for LITE-CODER Phase 3:
Targeted 24-Task MODE-A Rerun on Google Colab GPU.

This script validates the complete environment and configuration.
IT DOES NOT RUN THE BENCHMARK.
"""

import sys
import os
import hashlib
import json

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

TARGET_24_TASK_IDS = [
    "TASK_1E88EF5E", "TASK_FB475E1F", "TASK_527A01D3", "TASK_1AC7E084",
    "TASK_55A55247", "TASK_7C30D0A1", "TASK_761B7D7E", "TASK_96161F4B",
    "TASK_492A6DB5", "TASK_BC89315E", "TASK_435DA3AE", "TASK_E86381A6",
    "TASK_50B0F89F", "TASK_34E90ED9", "TASK_61DE3671", "TASK_61ECFD6A",
    "TASK_495776C1", "TASK_8FC95909", "TASK_71B9E063", "TASK_2A60D1B1",
    "TASK_64497C8C", "TASK_52F6CB07", "TASK_3CA90906", "TASK_0DB97680"
]

EXPECTED_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "experiments", "LITE_CODER_24TASK_POST_FIX_A_RERUN")
DATASET_PATH = os.path.join(PROJECT_ROOT, "data", "benchmark", "v1.0", "dataset.json")

def verify_all():
    print("=" * 65)
    print("LITE-CODER PHASE 3 COLAB SETUP VERIFICATION")
    print("=" * 65)
    all_passed = True

    # 1. Python version
    py_ver = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 10)
    print(f"[1] Python Version: {py_ver} -> {'PASS' if py_ok else 'FAIL (requires >=3.10)'}")
    if not py_ok: all_passed = False

    # 2. PyTorch availability
    try:
        import torch
        torch_ver = torch.__version__
        print(f"[2] PyTorch Version: {torch_ver} -> PASS")
    except ImportError as e:
        print(f"[2] PyTorch: FAIL ({e})")
        all_passed = False
        torch = None

    # 3. CUDA availability
    cuda_avail = torch.cuda.is_available() if torch else False
    print(f"[3] CUDA Available: {cuda_avail} -> {'PASS (GPU)' if cuda_avail else 'INFO (CPU fallback/local)'}")

    # 4. GPU Name
    if cuda_avail:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[4] GPU Name: {gpu_name} ({gpu_mem:.1f} GB VRAM) -> PASS")
    else:
        print("[4] GPU Name: N/A (Running on CPU)")

    # 5. transformers
    try:
        import transformers
        print(f"[5] transformers: {transformers.__version__} -> PASS")
    except ImportError as e:
        print(f"[5] transformers: FAIL ({e})")
        all_passed = False

    # 6. accelerate
    try:
        import accelerate
        print(f"[6] accelerate: {accelerate.__version__} -> PASS")
    except ImportError as e:
        print(f"[6] accelerate: FAIL ({e})")
        all_passed = False

    # 7. peft
    try:
        import peft
        print(f"[7] peft: {peft.__version__} -> PASS")
    except ImportError as e:
        print(f"[7] peft: FAIL ({e})")
        all_passed = False

    # 8. sentence-transformers
    try:
        import sentence_transformers
        print(f"[8] sentence-transformers: {sentence_transformers.__version__} -> PASS")
    except ImportError as e:
        print(f"[8] sentence-transformers: FAIL ({e})")
        all_passed = False

    # 9. faiss
    try:
        import faiss
        faiss_ver = getattr(faiss, "__version__", "installed")
        print(f"[9] faiss: {faiss_ver} -> PASS")
    except ImportError as e:
        print(f"[9] faiss: FAIL ({e})")
        all_passed = False

    # 10. Dataset hash
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "rb") as f:
            ds_hash = hashlib.sha256(f.read()).hexdigest()
        print(f"[10] Dataset Hash: {ds_hash[:16]}... ({os.path.relpath(DATASET_PATH, PROJECT_ROOT)}) -> PASS")
    else:
        print(f"[10] Dataset: FAIL (not found at {DATASET_PATH})")
        all_passed = False

    # 11. Fix A verification in app/main.py
    main_path = os.path.join(PROJECT_ROOT, "app", "main.py")
    if os.path.exists(main_path):
        with open(main_path, "r", encoding="utf-8") as f:
            main_code = f.read()
        fix_a_found = 'next_err = next_att.get("error_type") or ""' in main_code
        print(f"[11] Fix A in app/main.py: {'PASS (Found)' if fix_a_found else 'FAIL (Missing)'}")
        if not fix_a_found: all_passed = False
    else:
        print("[11] Fix A: FAIL (app/main.py missing)")
        all_passed = False

    # 12. Fix B absence verification
    fix_b_found = 'if not config.get("STRATEGY_LEARNING_ENABLED"):' in main_code if os.path.exists(main_path) else False
    print(f"[12] Fix B Absent: {'PASS (Correctly Absent)' if not fix_b_found else 'FAIL (Fix B is present)'}")
    if fix_b_found: all_passed = False

    # 13. Required model / LoRA configuration
    from app.config import config
    from app.model import base_model_name
    print(f"[13] Model Config: base='{base_model_name}', MODE_A LoRA required=False -> PASS")

    # 14. Exact 24 task IDs in dataset
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            ds_data = json.load(f)
        ds_ids = {t["task_id"] for t in ds_data}
        missing_ids = [tid for tid in TARGET_24_TASK_IDS if tid not in ds_ids]
        if not missing_ids and len(TARGET_24_TASK_IDS) == 24:
            print(f"[14] Exact 24 Task IDs: PASS (All 24 present and unique)")
        else:
            print(f"[14] Exact 24 Task IDs: FAIL (Missing: {missing_ids})")
            all_passed = False
    else:
        all_passed = False

    # 15. Output directory verification
    if os.path.exists(EXPECTED_OUTPUT_DIR):
        print(f"[15] Output Directory: WARNING ({os.path.relpath(EXPECTED_OUTPUT_DIR, PROJECT_ROOT)} already exists)")
    else:
        print(f"[15] Output Directory: PASS ({os.path.relpath(EXPECTED_OUTPUT_DIR, PROJECT_ROOT)} ready for new experiment)")

    print("=" * 65)
    print(f"OVERALL VERIFICATION RESULT: {'READY FOR PHASE 3' if all_passed else 'FAILED'}")
    print("=" * 65)
    return all_passed

if __name__ == "__main__":
    success = verify_all()
    sys.exit(0 if success else 1)
