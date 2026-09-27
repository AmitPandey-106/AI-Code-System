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

def format_repair_prompt(broken_code: str, error_message: str) -> str:
    """Canonical repair prompt matching inference distribution in app.model.fix_code"""
    return (
        "You are an expert Python debugger.\n\n"
        "Fix the Python code carefully.\n"
        "STRICT RULES:\n"
        "- Return executable Python code\n"
        "- Avoid syntax issues\n"
        "- Preserve intended functionality\n\n"
        "IMPORTANT:\n"
        "- Return ONLY executable Python code\n"
        "- NO explanations\n"
        "- NO markdown\n"
        "- NO comments\n"
        "- Return the FULL, COMPLETE corrected Python program.\n"
        "- Do NOT return a patch, diff, isolated replacement line, or partial snippet.\n"
        "- The returned code will replace the entire previous program and must be independently executable.\n\n"
        "CURRENT PROBLEM:\n"
        "BROKEN CODE:\n"
        f"{broken_code}\n\n"
        "ERROR:\n"
        f"{error_message}\n\n"
        "Return corrected executable Python code:\n"
    )

def build_training_example(memory: Dict) -> Dict:
    """Format compatible with Qwen code repair training with aligned prompt distribution"""
    prompt = format_repair_prompt(memory["broken_code"], memory["error_message"])
    completion = f"\n{memory['successful_fix']}\n"
    return {
        "prompt": prompt,
        "completion": completion,
        "text": f"{prompt}{completion}",
        "fingerprint": generate_fingerprint(memory["task"], memory["broken_code"], memory["error_message"]),
        "raw_task": memory["task"],
        "raw_broken_code": memory["broken_code"],
        "raw_error_message": memory["error_message"],
        "raw_successful_fix": memory["successful_fix"],
        "raw_tests": memory.get("tests", "")
    }

def build_dataset(
    memory_file: str = None,
    dataset_dir: str = None,
    last_trained_count: int = 0,
    replay_size: int = None,
    replay_strategy: str = None
) -> Dict:
    """
    Build train, validation, and test splits from memory with Experience Replay.
    Combines newly arrived verified repair experiences with replayed previously verified experiences.
    """
    from app.config import config
    target_mem_file = memory_file or MEMORY_FILE
    target_dataset_dir = dataset_dir or DATASET_DIR
    r_size = replay_size if replay_size is not None else config.get("LORA_REPLAY_SIZE", 4)
    r_strat = replay_strategy if replay_strategy is not None else config.get("LORA_REPLAY_STRATEGY", "all")

    if not os.path.exists(target_mem_file):
        return {"train": [], "val": [], "test": [], "stats": {}, "replay_examples": []}
        
    with open(target_mem_file, "r", encoding="utf-8") as f:
        memories = json.load(f)
        
    unique_examples = {}
    rejected = 0
    
    # Maintain temporal insertion order of memories
    for mem in memories:
        if validate_training_experience(mem):
            example = build_training_example(mem)
            fp = example["fingerprint"]
            if fp not in unique_examples:
                unique_examples[fp] = example
        else:
            rejected += 1
            
    all_examples = list(unique_examples.values())
    total_accepted = len(all_examples)

    # Partition into previous (replayed) and newly arrived experiences
    if 0 < last_trained_count <= total_accepted:
        prev_pool = all_examples[:last_trained_count]
        new_pool = all_examples[last_trained_count:]
    else:
        prev_pool = []
        new_pool = all_examples

    # Sample replay experiences
    replayed_examples = []
    if prev_pool and r_size > 0:
        if r_strat == "recent":
            replayed_examples = prev_pool[-r_size:]
        elif r_strat == "uniform":
            step = max(1, len(prev_pool) // r_size)
            replayed_examples = [prev_pool[i] for i in range(0, len(prev_pool), step)][:r_size]
        else:  # "all" or default
            replayed_examples = prev_pool[:r_size] if len(prev_pool) > r_size else list(prev_pool)

    # Mark replay metadata on examples
    for ex in replayed_examples:
        ex["is_replay"] = True
    for ex in new_pool:
        ex["is_replay"] = False

    # Composite training pool: new experiences + replayed experiences
    composite_train_pool = new_pool + replayed_examples

    # Deterministic sorting by fingerprint for reproducible batches
    composite_train_pool.sort(key=lambda x: x["fingerprint"])
    
    total = len(composite_train_pool)
    if total < 3:
        train_set = composite_train_pool
        val_set = []
        test_set = composite_train_pool
    else:
        train_end = int(total * 0.8)
        val_end = int(total * 0.9)
        train_set = composite_train_pool[:train_end]
        val_set = composite_train_pool[train_end:val_end]
        test_set = composite_train_pool[val_end:]
    
    os.makedirs(target_dataset_dir, exist_ok=True)
    with open(os.path.join(target_dataset_dir, "train.json"), "w", encoding="utf-8") as f:
        json.dump(train_set, f, indent=4)
    with open(os.path.join(target_dataset_dir, "val.json"), "w", encoding="utf-8") as f:
        json.dump(val_set, f, indent=4)
    with open(os.path.join(target_dataset_dir, "test.json"), "w", encoding="utf-8") as f:
        json.dump(test_set, f, indent=4)
        
    stats = {
        "total_memories": len(memories),
        "rejected_count": rejected,
        "accepted_unique_count": total_accepted,
        "new_examples_count": len(new_pool),
        "replay_examples_count": len(replayed_examples),
        "replay_strategy": r_strat,
        "replay_size": r_size,
        "train_count": len(train_set),
        "val_count": len(val_set),
        "test_count": len(test_set)
    }
    
    with open(os.path.join(target_dataset_dir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
        
    return {
        "train": train_set,
        "val": val_set,
        "test": test_set,
        "stats": stats,
        "replay_examples": replayed_examples,
        "new_examples": new_pool
    }
