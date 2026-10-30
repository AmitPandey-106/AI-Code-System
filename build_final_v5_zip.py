import os
import zipfile
import hashlib
import json

root_dir = r"D:\Amit Stuff\ai-code-system"
zip_path = r"D:\Amit Stuff\ai-code-system\LITE_CODER_Q1_FINAL_COLAB_V5.zip"

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
    ds_path = os.path.join(root_dir, "data", "benchmark", "v1.0", "dataset.json")
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

def is_clean_experiment_file(rel_path):
    if rel_path.startswith("experiments"):
        return False
    if rel_path.startswith("models" + os.sep + "adapters" + os.sep + "active") or rel_path.startswith("models" + os.sep + "adapters" + os.sep + "candidates"):
        return False
    if rel_path.startswith("data" + os.sep + "repair_memory") or rel_path.startswith("data" + os.sep + "strategy_"):
        return False
    if rel_path.startswith("data" + os.sep + "feedback"):
        return False
    if rel_path.startswith("lora-"):
        return False
    if rel_path.startswith("scratch"):
        return False
    if rel_path.startswith("package_output"):
        return False
    if "LITE_CODER_Q1_FINAL" in rel_path:
        return False
    if rel_path.endswith(".pyc") or "__pycache__" in rel_path:
        return False
    if ".git" in rel_path:
        return False
    if rel_path.startswith("venv") or rel_path.startswith(".venv"):
        return False
    return True

def build_zip():
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    file_count = 0
    excluded_files = []
    
    # We explicitly include these directories and files
    include_dirs = ["app", "benchmark"]
    include_files = [
        "RUN_ALL_FINAL_EXPERIMENTS_V5.py",
        "COLAB_PREFLIGHT_V5.py",
        "train_worker.py",
        "requirements.txt",
        "README.md",
        "config.json"
    ]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Include data/benchmark/v1.0/dataset.json
        dataset_rel = os.path.join("data", "benchmark", "v1.0", "dataset.json")
        dataset_path = os.path.join(root_dir, dataset_rel)
        if os.path.exists(dataset_path):
            zipf.write(dataset_path, os.path.join("LITE_CODER_Q1_COLAB_FINAL", dataset_rel))
            file_count += 1
            
        for d in include_dirs:
            dir_path = os.path.join(root_dir, d)
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d_ for d_ in dirs if d_ not in ['.git', '__pycache__']]
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, root_dir)
                    if not is_clean_experiment_file(rel_path):
                        excluded_files.append(rel_path)
                        continue
                    arcname = os.path.join("LITE_CODER_Q1_COLAB_FINAL", rel_path)
                    zipf.write(file_path, arcname)
                    file_count += 1
                    
        for f in include_files:
            file_path = os.path.join(root_dir, f)
            if os.path.exists(file_path):
                arcname = os.path.join("LITE_CODER_Q1_COLAB_FINAL", f)
                zipf.write(file_path, arcname)
                file_count += 1
                
    return file_count, excluded_files

def get_zip_manifest(zip_path):
    manifest = []
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            if not info.is_dir():
                content = z.read(info.filename)
                h = hashlib.sha256(content).hexdigest()
                manifest.append({
                    "path": info.filename,
                    "size": info.file_size,
                    "sha256": h
                })
    return manifest

def main():
    ds_ok, ds_hash, ds_count = verify_dataset()
    
    req_files = [
        "RUN_ALL_FINAL_EXPERIMENTS_V5.py",
        "COLAB_PREFLIGHT_V5.py",
        "requirements.txt",
        "benchmark/runner.py",
        "data/benchmark/v1.0/dataset.json",
        "train_worker.py"
    ]
    missing = [f for f in req_files if not os.path.exists(os.path.join(root_dir, os.path.normpath(f)))]
    
    if ds_ok and not missing:
        file_count, excluded = build_zip()
        zip_hash = sha256_file(zip_path)
        zip_size = os.path.getsize(zip_path)
        
        manifest = get_zip_manifest(zip_path)
        with open("V5_PACKAGE_MANIFEST.json", "w") as f:
            json.dump({
                "zip_path": zip_path,
                "zip_sha256": zip_hash,
                "zip_size": zip_size,
                "file_count": file_count,
                "dataset_sha256": ds_hash,
                "dataset_task_count": ds_count,
                "files": manifest
            }, f, indent=4)
        
        print("PACKAGE READY FOR COLAB")
    else:
        print("PACKAGE NOT READY FOR COLAB")
        if missing:
            print("Missing:", missing)
        if not ds_ok:
            print("Dataset failed validation")

if __name__ == "__main__":
    main()
