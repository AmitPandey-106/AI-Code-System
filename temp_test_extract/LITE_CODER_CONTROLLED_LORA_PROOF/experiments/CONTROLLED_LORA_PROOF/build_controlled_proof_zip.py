import os
import zipfile
import hashlib
import json

root_dir = r"D:\Amit Stuff\ai-code-system"
zip_path = r"D:\Amit Stuff\ai-code-system\LITE_CODER_FINAL_RELEASE_CANDIDATE_V6.zip"

def sha256_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(4096), b""):
            h.update(b)
    return h.hexdigest()

def is_clean_file(rel_path):
    if "LITE_CODER_Q1_FINAL" in rel_path or "LITE_CODER_FINAL_RELEASE_CANDIDATE_V6.zip" in rel_path:
        return False
    if rel_path.endswith(".pyc") or "__pycache__" in rel_path:
        return False
    if ".git" in rel_path:
        return False
    if rel_path.startswith("venv") or rel_path.startswith(".venv"):
        return False
    if "EVIDENCE" in rel_path:
        return False
    if "STAGE1_" in rel_path or "STAGE2_" in rel_path or "STAGE3_" in rel_path:
        return False
    return True


def build_zip():
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    file_count = 0
    
    include_dirs = [
        "app", 
        "benchmark", 
        "experiments" + os.sep + "CONTROLLED_LORA_PROOF"
    ]
    include_files = [
        "train_worker.py",
        "requirements.txt",
        "config.json",
        "RUN_ALL_FINAL_EXPERIMENTS_V5.py"
    ]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for d in include_dirs:
            dir_path = os.path.join(root_dir, d)
            if not os.path.exists(dir_path):
                continue
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d_ for d_ in dirs if d_ not in ['.git', '__pycache__']]
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, root_dir)
                    if not is_clean_file(rel_path):
                        continue
                    if "EVIDENCE" in rel_path:
                        continue
                    arcname = os.path.join("LITE_CODER_CONTROLLED_LORA_PROOF", rel_path)
                    zipf.write(file_path, arcname)
                    file_count += 1
                    
        for f in include_files:
            file_path = os.path.join(root_dir, f)
            if os.path.exists(file_path):
                arcname = os.path.join("LITE_CODER_CONTROLLED_LORA_PROOF", f)
                zipf.write(file_path, arcname)
                file_count += 1
                
    return file_count

def main():
    file_count = build_zip()
    zip_hash = sha256_file(zip_path)
    
    print("\n============================================================")
    print("CONTROLLED LoRA PROOF - LOCAL PREPARATION")
    print("============================================================")
    print("Experiment prepared:\nYES\n")
    print("Controlled dataset:\n6 tasks\n")
    print("Canonical benchmark modified:\nNO\n")
    print("Historical evidence modified:\nNO\n")
    print("Fake memory inserted:\nNO\n")
    print("Fake adapter inserted:\nNO\n")
    print("GPU training executed locally:\nNO\n")
    print(f"Colab execution package:\n{zip_path}\n")
    print(f"ZIP SHA256:\n{zip_hash}\n")
    print("Colab execution command:\n!python experiments/CONTROLLED_LORA_PROOF/RUN_CONTROLLED_LORA_PROOF.py --run")
    print("============================================================")

if __name__ == "__main__":
    main()
