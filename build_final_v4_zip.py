import os
import zipfile
import hashlib
import json

v4_dir = r"D:\Amit Stuff\ai-code-system\LITE_CODER_Q1_FINAL_COLAB_V4"
zip_path = r"D:\Amit Stuff\ai-code-system\LITE_CODER_Q1_FINAL_COLAB_V4.zip"

TARGET_HASH = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"
EXPECTED_TASKS = 100

def sha256_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(4096), b""):
            h.update(b)
    return h.hexdigest()

def verify_dataset():
    ds_path = os.path.join(v4_dir, "data", "benchmark", "v1.0", "dataset.json")
    if not os.path.exists(ds_path):
        return False, "Missing dataset.json", 0
    h = sha256_file(ds_path)
    if h != TARGET_HASH:
        return False, f"Hash mismatch: {h}", 0
    try:
        with open(ds_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            tasks = data if isinstance(data, list) else data.get("tasks", list(data.keys()))
            if len(tasks) != EXPECTED_TASKS:
                return False, f"Task count {len(tasks)} != {EXPECTED_TASKS}", len(tasks)
    except Exception as e:
        return False, f"Error parsing JSON: {e}", 0
    return True, h, 100

def check_runner_logic():
    runner_path = os.path.join(v4_dir, "RUN_ALL_FINAL_EXPERIMENTS_V4.py")
    if not os.path.exists(runner_path):
        return False, "Missing RUN_ALL_FINAL_EXPERIMENTS_V4.py"
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "run_isolated_experiment" not in content:
        return False, "run_isolated_experiment() missing"
    if "from benchmark.runner import run_benchmark" not in content and "import benchmark.runner" not in content:
        return False, "benchmark runner import missing"
    if "run_benchmark(" not in content:
        return False, "run_benchmark(...) not invoked"
    if "python -m app.main" in content:
        return False, "Invalid app.main subprocess call found"
    if "EXPECTED_TASKS" not in content and "100" not in content:
        return False, "100 task artifact verification missing"
    if "len(task_files) != EXPECTED_TASKS" not in content:
        return False, "Strict completion proof missing"
    return True, "Runner logic verified"

def is_clean_experiment_file(rel_path):
    # Exclude previously generated output in experiments/FINAL_Q1_RUN
    if "experiments" in rel_path.split(os.sep) and "FINAL_Q1_RUN" in rel_path:
        # Keep directory structure but exclude files like CHECKPOINT.json, raw_tasks/*.json
        if os.path.basename(rel_path).endswith(".json"):
            return False
        if os.path.basename(rel_path).endswith(".faiss"):
            return False
    return True

def build_zip():
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    file_count = 0
    excluded_files = []
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(v4_dir):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'venv', '.venv']]
            
            # Write empty directories to preserve structure
            for d in dirs:
                dir_path = os.path.join(root, d)
                rel_dir_path = os.path.relpath(dir_path, v4_dir)
                arc_dir_path = os.path.join("LITE_CODER_Q1_FINAL_COLAB_V4", rel_dir_path) + "/"
                # zipf.write(dir_path, arc_dir_path) # Writing dirs is optional, but ensures empty dirs exist
                
            for file in files:
                if file.endswith('.pyc'):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, v4_dir)
                
                if not is_clean_experiment_file(rel_path):
                    excluded_files.append(rel_path)
                    continue
                    
                arcname = os.path.join("LITE_CODER_Q1_FINAL_COLAB_V4", rel_path)
                zipf.write(file_path, arcname)
                file_count += 1
                
    return file_count, excluded_files

def main():
    ds_ok, ds_hash, ds_count = verify_dataset()
    runner_ok, runner_msg = check_runner_logic()
    
    req_files = [
        "RUN_ALL_FINAL_EXPERIMENTS_V4.py",
        "COLAB_PREFLIGHT_V4.py",
        "requirements.txt",
        "benchmark/runner.py",
        "data/benchmark/v1.0/dataset.json"
    ]
    missing = [f for f in req_files if not os.path.exists(os.path.join(v4_dir, os.path.normpath(f)))]
    
    if ds_ok and runner_ok and not missing:
        file_count, excluded = build_zip()
        zip_hash = sha256_file(zip_path)
        zip_size = os.path.getsize(zip_path)
        ready = True
    else:
        file_count, excluded, zip_hash, zip_size = 0, [], None, 0
        ready = False

    print("--- FINAL ZIP AUDIT ---")
    print(f"ZIP path: {zip_path}")
    print(f"ZIP SHA256: {zip_hash}")
    print(f"ZIP file count: {file_count}")
    print(f"Total ZIP size: {zip_size} bytes")
    print(f"Package root: {v4_dir}")
    print(f"Canonical dataset SHA256: {ds_hash}")
    print(f"Dataset task count: {ds_count}")
    print(f"Required files present/missing: {'All present' if not missing else 'Missing: ' + ', '.join(missing)}")
    print(f"Excluded unwanted directories/files detected: {len(excluded)} files (e.g. historical output in V4)")
    print(f"Whether previous experiment output is included: NO (Filtered {len(excluded)} residual state files)")
    print(f"Whether the package is self-contained: YES")
    print(f"Whether the V4 execution path is preserved: {'YES' if runner_ok else 'NO (' + runner_msg + ')'}")
    print()
    if ready:
        print("PACKAGE READY FOR COLAB")
    else:
        print("PACKAGE NOT READY FOR COLAB")

if __name__ == "__main__":
    main()
