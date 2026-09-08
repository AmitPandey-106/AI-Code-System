import json
import os

MEMORY_FILE = "data/repair_memory.json"

def inspect_memory():
    if not os.path.exists(MEMORY_FILE):
        print("No memory file found.")
        return
        
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memories = json.load(f)
        
    print("========================================")
    print(f"Total Memories: {len(memories)}")
    print("========================================")
    
    for i, mem in enumerate(memories):
        print(f"\nMemory {i+1}:")
        print(f"  ID:          {mem.get('memory_id')}")
        print(f"  Task:        {mem.get('task')}")
        print(f"  Error Type:  {mem.get('error_type')}")
        print(f"  Attempts:    {mem.get('repair_attempts')}")
        print(f"  Success:     {mem.get('success')}")
        print("-" * 40)

if __name__ == "__main__":
    inspect_memory()
