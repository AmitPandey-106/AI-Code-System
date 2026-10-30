import os
import json
import glob

print("==================================")
print("EXPERIMENTS")
print("==================================")
for manifest in glob.glob("experiments/**/experiment_manifest.json", recursive=True):
    with open(manifest, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"File: {manifest}")
        print(json.dumps(data, indent=2))
        
print("==================================")
print("BENCHMARK TASK COUNTS")
print("==================================")
dirs = glob.glob("experiments/*", recursive=False)
for d in dirs:
    if os.path.isdir(d) and os.path.exists(os.path.join(d, "raw_tasks")):
        tasks = glob.glob(f"{d}/raw_tasks/*.json")
        success = 0
        total = len(tasks)
        attempts = []
        for t in tasks:
            with open(t, "r") as f:
                t_data = json.load(f)
                if t_data.get("success"):
                    success += 1
                if "attempts_used" in t_data and t_data["attempts_used"] is not None:
                    attempts.append(t_data["attempts_used"])
        avg_attempts = sum(attempts)/len(attempts) if attempts else 0
        print(f"Dir: {d}, Total Tasks: {total}, Success: {success}, Avg Attempts: {avg_attempts:.2f}")

print("==================================")
print("MEMORY & RETRIEVAL")
print("==================================")
for mem in glob.glob("experiments/**/repair_memory.json", recursive=True):
    with open(mem, "r") as f:
        try:
            m_data = json.load(f)
            print(f"Memory: {mem}, records: {len(m_data)}")
        except:
            pass

print("==================================")
print("DRAFT PAPER CLAIMS")
print("==================================")
with open("LITE_Coder_Q1_Draft.md", "r", encoding="utf-8") as f:
    print(f.read())
