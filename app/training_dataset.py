import json
import os
import hashlib
from typing import List, Dict

MEMORY_FILE = "data/repair_memory.json"
DATASET_DIR = "data/dataset"

def validate_training_experience(memory: Dict) -> bool:
    """Quality filtering layer"""
    if not memory.get("success"):
        return False
        
    verification = memory.get("verification", {})
    if not (verification.get("syntax_passed") and 
            verification.get("safety_passed") and 
            verification.get("execution_passed") and 
            verification.get("tests_passed")):
        return False
        
    error_type = memory.get("error_type", "")
    if "SecurityViolation" in error_type or "TimeoutError" in error_type:
        return False
        
    if not memory.get("error_message") or not memory.get("broken_code") or not memory.get("successful_fix"):
        return False
        
    return True

def generate_fingerprint(task: str, broken_code: str, error_message: str) -> str:
    """Deterministic fingerprint for deduplication"""
    raw = f"{task}|{broken_code}|{error_message}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def build_training_example(memory: Dict) -> Dict:
    """Format compatible with Qwen code repair training"""
    return {
        "text": f"Fix this Python code:\n\n{memory['broken_code']}\n\nError:\n{memory['error_message']}\n\nCorrect Code:\n{memory['successful_fix']}\n",
        "fingerprint": generate_fingerprint(memory["task"], memory["broken_code"], memory["error_message"]),
        "raw_task": memory["task"],
        "raw_broken_code": memory["broken_code"],
        "raw_error_message": memory["error_message"],
        "raw_successful_fix": memory["successful_fix"],
        "raw_tests": memory.get("tests", "")
    }

def build_dataset() -> Dict:
    """Build train, validation, and test splits from memory"""
    if not os.path.exists(MEMORY_FILE):
        return {"train": [], "val": [], "test": [], "stats": {}}
        
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memories = json.load(f)
        
    unique_examples = {}
    rejected = 0
    
    for mem in memories:
        if validate_training_experience(mem):
            example = build_training_example(mem)
            fp = example["fingerprint"]
            if fp not in unique_examples:
                unique_examples[fp] = example
        else:
            rejected += 1
            
    examples = list(unique_examples.values())
    
    # Deterministic dataset splitting (80% train, 10% val, 10% test)
    # Sort by fingerprint for deterministic splits across runs
    examples.sort(key=lambda x: x["fingerprint"])
    
    total = len(examples)
    if total < 3:
        train_set = examples
        val_set = []
        test_set = examples
    else:
        train_end = int(total * 0.8)
        val_end = int(total * 0.9)
        train_set = examples[:train_end]
        val_set = examples[train_end:val_end]
        test_set = examples[val_end:]
    
    os.makedirs(DATASET_DIR, exist_ok=True)
    with open(os.path.join(DATASET_DIR, "train.json"), "w", encoding="utf-8") as f:
        json.dump(train_set, f, indent=4)
    with open(os.path.join(DATASET_DIR, "val.json"), "w", encoding="utf-8") as f:
        json.dump(val_set, f, indent=4)
    with open(os.path.join(DATASET_DIR, "test.json"), "w", encoding="utf-8") as f:
        json.dump(test_set, f, indent=4)
        
    stats = {
        "total_memories": len(memories),
        "rejected_count": rejected,
        "accepted_unique_count": total,
        "train_count": len(train_set),
        "val_count": len(val_set),
        "test_count": len(test_set)
    }
    
    with open(os.path.join(DATASET_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
        
    return {
        "train": train_set,
        "val": val_set,
        "test": test_set,
        "stats": stats
    }
