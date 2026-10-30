import os
import zipfile
import hashlib

def create_zip():
    zip_name = "LITE_CODER_CONTROLLED_LORA_PROOF_V3.zip"
    
    # Exclude logic
    def should_exclude(path):
        lower_path = path.lower()
        if "__pycache__" in lower_path or ".git" in lower_path:
            return True
        if ".venv" in lower_path or "venv" in lower_path or "env" in lower_path:
            return True
        if "experiments\\" in path or "experiments/" in path:
            # ONLY include CONTROLLED_LORA_PROOF
            if "CONTROLLED_LORA_PROOF" not in path:
                return True
            # Exclude EVIDENCES or raw_tasks if any exist (historical outputs of the proof)
            if "EVIDENCE" in path or "STAGE" in path or "raw_tasks" in path:
                return True
        if "data\\repair_memory.json" in path or "data/repair_memory.json" in path:
            return True
        if "data\\repair_memory_index.faiss" in path or "data/repair_memory_index.faiss" in path:
            return True
        if "data\\strategy_memory.json" in path or "data/strategy_memory.json" in path:
            return True
        if "data\\strategy_stats.json" in path or "data/strategy_stats.json" in path:
            return True
        if "models\\adapters" in path or "models/adapters" in path:
            return True
        if ".pyc" in lower_path:
            return True
        return False
        
    include_dirs = ["app", "benchmark", "experiments/CONTROLLED_LORA_PROOF", "data/benchmark"]
    include_files = ["requirements.txt", "config.json"]
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add dirs
        for d in include_dirs:
            if not os.path.exists(d): continue
            for root, dirs, files in os.walk(d):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, start=".")
                    if not should_exclude(rel_path):
                        zf.write(full_path, arcname=rel_path)
                        
        # Add files
        for f in include_files:
            if os.path.exists(f) and not should_exclude(f):
                zf.write(f, arcname=f)

    # Verify
    count = 0
    size = os.path.getsize(zip_name)
    manifest = []
    
    with zipfile.ZipFile(zip_name, 'r') as zf:
        for info in zf.infolist():
            count += 1
            manifest.append(info.filename)
            
    sha256_hash = hashlib.sha256()
    with open(zip_name, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            
    import json
    result = {
        "zip_path": os.path.abspath(zip_name),
        "sha256": sha256_hash.hexdigest(),
        "file_count": count,
        "size_bytes": size,
        "manifest_preview": manifest[:20],
        "has_proof_dataset": any("proof_dataset.json" in m for m in manifest),
        "has_main_py": any("app/main.py" in m or "app\\main.py" in m for m in manifest),
        "has_runner": any("RUN_CONTROLLED_LORA_PROOF.py" in m for m in manifest),
        "has_train_worker": any("app/train_worker.py" in m or "app\\train_worker.py" in m for m in manifest),
        "has_canonical": any("data/benchmark/v1.0/dataset.json" in m or "data\\benchmark\\v1.0\\dataset.json" in m for m in manifest)
    }
    
    print(json.dumps(result, indent=2))
    
    print("\n--- Manifest List ---")
    for m in manifest:
        print(m)

if __name__ == "__main__":
    create_zip()
