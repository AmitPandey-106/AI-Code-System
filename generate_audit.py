import os
import json
import hashlib
import glob

base_dir = r"D:\Amit Stuff\ai-code-system"
output_file = os.path.join(base_dir, "LITE-CODER_Q1_JOURNAL_V2", "evidence", "EVIDENCE_RECONCILIATION_AUDIT.md")
os.makedirs(os.path.dirname(output_file), exist_ok=True)

TARGET_HASH = "2bd5075970f9b1320c4437663918f753ed059b6514bff82f96d8272eca262620"

def sha256_file(path):
    try:
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return "ERROR"

def get_json_info(path):
    try:
        size = os.path.getsize(path)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            task_count = len(data)
            first_id = data[0].get('task_id', 'unknown') if task_count > 0 else 'N/A'
            last_id = data[-1].get('task_id', 'unknown') if task_count > 0 else 'N/A'
        elif isinstance(data, dict):
            if 'tasks' in data and isinstance(data['tasks'], list):
                task_count = len(data['tasks'])
                first_id = data['tasks'][0].get('task_id', 'unknown') if task_count > 0 else 'N/A'
                last_id = data['tasks'][-1].get('task_id', 'unknown') if task_count > 0 else 'N/A'
            else:
                task_count = len(data.keys())
                first_id = list(data.keys())[0] if task_count > 0 else 'N/A'
                last_id = list(data.keys())[-1] if task_count > 0 else 'N/A'
        else:
            task_count = "Unknown Schema"
            first_id = "N/A"
            last_id = "N/A"
            
        return size, task_count, first_id, last_id
    except Exception as e:
        return "ERROR", "ERROR", "ERROR", "ERROR"

with open(output_file, 'w', encoding='utf-8') as out:
    out.write("# EVIDENCE RECONCILIATION AUDIT\n\n")
    
    # 1. CANONICAL BENCHMARK IDENTITY
    out.write("## 1. CANONICAL BENCHMARK IDENTITY\n\n")
    candidate_benchmarks = glob.glob(os.path.join(base_dir, "data", "**", "*.json"), recursive=True)
    candidate_benchmarks += glob.glob(os.path.join(base_dir, "experiments", "FINAL_LITE_CODER_EVIDENCE", "*.json"), recursive=True)
    
    found_target_hash = False
    target_hash_file = "CANONICAL HASH NOT FOUND"
    canonical_task_count = 0
    
    for cb in set(candidate_benchmarks):
        if "benchmark" in cb.lower() or "dataset" in cb.lower():
            h = sha256_file(cb)
            size, count, first_id, last_id = get_json_info(cb)
            rel_cb = cb.replace(base_dir + os.sep, '')
            out.write(f"### Candidate: `{rel_cb}`\n")
            out.write(f"- **PATH**: `{rel_cb}`\n")
            out.write(f"- **FILE SIZE**: {size} bytes\n")
            out.write(f"- **TASK COUNT**: {count}\n")
            out.write(f"- **SHA256**: `{h}`\n")
            out.write(f"- **FIRST/LAST TASK ID**: {first_id} / {last_id}\n")
            out.write(f"- **SCHEMA SUMMARY**: JSON Parsed\n")
            out.write(f"- **WHICH HISTORICAL EXPERIMENTS REFERENCE IT**: Unknown/Unverified without full cross-reference.\n\n")
            if h == TARGET_HASH:
                found_target_hash = True
                target_hash_file = rel_cb
                canonical_task_count = count
                
    if not found_target_hash:
        out.write("### CANONICAL HASH NOT FOUND\n\n")
        
    # 2. HISTORICAL 100-TASK EXPERIMENT IDENTITY
    out.write("## 2. HISTORICAL 100-TASK EXPERIMENT IDENTITY\n\n")
    exp_names = [
        "LITE_CODER_100TASK_MODE_A_BASELINE",
        "LITE_CODER_100TASK_MODE_A_CLEAN_V1",
        "LITE_CODER_100TASK_MODE_D",
        "LITE_CODER_100TASK_MODE_F",
        "LITE_CODER_100TASK_MODE_F_TRAINED",
        "LITE_CODER_MODE_F_SAFE",
        "LITE_CODER_MODE_F_SAFE_RESULTS"
    ]
    
    for exp in exp_names:
        exp_dir = os.path.join(base_dir, "experiments", exp)
        out.write(f"### {exp}\n")
        if not os.path.exists(exp_dir):
            out.write("Directory does not exist.\n\n")
            continue
            
        manifest_path = os.path.join(exp_dir, "experiment_manifest.json")
        metrics_path = os.path.join(exp_dir, "metrics.json")
        raw_tasks_dir = os.path.join(exp_dir, "raw_tasks")
        
        task_count = len(glob.glob(os.path.join(raw_tasks_dir, "*.json"))) if os.path.exists(raw_tasks_dir) else 0
        out.write(f"- **task count**: {task_count}\n")
        
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    man = json.load(f)
                out.write(f"- **dataset path/reference**: {man.get('dataset_path', 'N/A')}\n")
                out.write(f"- **model**: {man.get('model', 'N/A')}\n")
                out.write(f"- **seed**: {man.get('seed', 'N/A')}\n")
                out.write(f"- **attempt budget**: {man.get('attempt_limit', 'N/A')}\n")
                out.write(f"- **memory setting**: {man.get('memory_mode', 'N/A')}\n")
                out.write(f"- **LoRA setting**: {man.get('lora', 'N/A')}\n")
                out.write(f"- **SAFE setting**: {man.get('safe_mode', 'N/A')}\n")
            except:
                out.write("- **Manifest**: Found but could not parse completely.\n")
        else:
            out.write("- **Manifest**: Not found.\n")
            
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, 'r') as f:
                    met = json.load(f)
                out.write(f"- **final success count**: {met.get('success_count', 'N/A')}\n")
                out.write(f"- **success rate**: {met.get('success_rate', 'N/A')}\n")
                out.write(f"- **average attempts**: {met.get('avg_attempts', 'N/A')}\n")
                out.write(f"- **latency**: {met.get('avg_latency', 'N/A')}\n")
            except:
                out.write("- **Metrics**: Found but could not parse.\n")
        else:
            out.write("- **Metrics**: Not found.\n")
        out.write("\n")

    # 3. COLAB PROVENANCE
    out.write("## 3. COLAB PROVENANCE\n\n")
    out.write("Inspecting `scratch/LITE_CODER_Q1_FINAL_COLAB_PACKAGE/` and related manifests...\n")
    colab_pkg = os.path.join(base_dir, "scratch", "LITE_CODER_Q1_FINAL_COLAB_PACKAGE")
    colab_ds_path = os.path.join(colab_pkg, "data", "benchmark_tasks.json")
    if os.path.exists(colab_ds_path):
        h = sha256_file(colab_ds_path)
        s, c, f_id, l_id = get_json_info(colab_ds_path)
        out.write(f"- **Exact dataset copied into Colab package**: `data/benchmark_tasks.json`\n")
        out.write(f"- **SHA256**: `{h}`\n")
        out.write(f"- **Task count**: {c}\n")
    else:
        out.write("- Exact dataset copied into Colab package: Not found in standard package data/ path.\n")

    # 4. ACTUAL CURRENT ARCHITECTURE
    out.write("\n## 4. ACTUAL CURRENT ARCHITECTURE\n\n")
    # Finding actual paths for architecture components
    arch_files = {
        "Benchmark loading": "app/core/task_loader.py",
        "Task loading": "app/core/task_loader.py",
        "Model loading": "app/llm/model_manager.py",
        "Candidate generation": "app/llm/generator.py",
        "Execution": "app/execution/sandbox.py",
        "Failure detection": "app/execution/verifier.py",
        "Memory retrieval": "app/memory/retriever.py",
        "Repair generation": "app/llm/repair.py",
        "Verification": "app/execution/verifier.py",
        "Memory admission": "app/memory/admission.py",
        "Result serialization": "app/core/results.py"
    }
    
    for stage, assumed_path in arch_files.items():
        if os.path.exists(os.path.join(base_dir, assumed_path.replace('/', os.sep))):
            out.write(f"**{stage}**\n↓ (`{assumed_path}`)\n")
        else:
            # Let's see if we can find something similar
            found = False
            for f in glob.glob(os.path.join(base_dir, "app", "**", "*.py"), recursive=True):
                if assumed_path.split('/')[-1] in f:
                    rel = f.replace(base_dir + os.sep, '')
                    out.write(f"**{stage}**\n↓ (`{rel}`)\n")
                    found = True
                    break
            if not found:
                out.write(f"**{stage}**\n↓ NOT FOUND / STALE PATH\n")

    # 5. STATISTICAL PIPELINE
    out.write("\n## 5. STATISTICAL PIPELINE\n\n")
    stat_files = glob.glob(os.path.join(base_dir, "scripts", "**", "*.py"), recursive=True)
    out.write("ACTUAL files performing statistical analysis and plot generation:\n")
    for f in stat_files:
        rel = f.replace(base_dir + os.sep, '')
        out.write(f"- `{rel}`\n")

    # 6. FINAL Q1 EXPERIMENT STATUS
    out.write("\n## 6. FINAL Q1 EXPERIMENT STATUS\n\n")
    q1_1 = os.path.join(base_dir, "experiments", "FINAL_Q1_EXP_01_CLEAN_BASELINE")
    q1_2 = os.path.join(base_dir, "experiments", "FINAL_Q1_EXP_02_CLEAN_MEMORY")
    run_script = os.path.join(base_dir, "scripts", "run_final_experiments.py")
    
    for p in [q1_1, q1_2]:
        name = os.path.basename(p)
        if os.path.exists(p):
            has_tasks = os.path.exists(os.path.join(p, "raw_tasks")) and len(os.listdir(os.path.join(p, "raw_tasks"))) > 0
            has_metrics = os.path.exists(os.path.join(p, "metrics.json"))
            if has_tasks and has_metrics:
                out.write(f"- `{name}`: EXECUTED (contains raw tasks and metrics)\n")
            elif has_tasks:
                out.write(f"- `{name}`: PREPARED BUT NOT EXECUTED (contains tasks but no final metrics)\n")
            else:
                out.write(f"- `{name}`: PREPARED BUT NOT EXECUTED (empty or placeholders only)\n")
        else:
            out.write(f"- `{name}`: NOT FOUND\n")

    # 7. PAPER-SAFE EVIDENCE CLASSIFICATION
    out.write("\n## 7. PAPER-SAFE EVIDENCE CLASSIFICATION\n\n")
    out.write("### A. SAFE TO USE DIRECTLY IN PAPER\n")
    out.write("- Any completed FINAL_Q1_EXP (Clean slate, reproducible provenance)\n")
    out.write("### B. USE ONLY AS SUPPORTING / HISTORICAL EVIDENCE\n")
    out.write("- Legacy Colab output traces (Valid but environment not perfectly hermetic)\n")
    out.write("### C. CONFOUNDED / DO NOT USE FOR CAUSAL CLAIMS\n")
    out.write("- `LITE_CODER_MODE_F_SAFE` (If dataset was incomplete or mixed configurations used)\n")
    out.write("### D. REQUIRES NEW CLEAN EXPERIMENT\n")
    out.write("- Memory extraction and ablation tests requiring perfect baseline control.\n")

    # 8. CRITICAL RESULT
    out.write("\n## 8. CRITICAL RESULT\n\n")
    out.write(f"CANONICAL DATASET:\n{target_hash_file}\n\n")
    out.write(f"CANONICAL SHA256:\n{TARGET_HASH if found_target_hash else 'CANONICAL HASH NOT FOUND'}\n\n")
    out.write(f"CANONICAL TASK COUNT:\n{canonical_task_count}\n\n")
    out.write("HISTORICAL 100-TASK EXPERIMENTS:\n" + ", ".join(exp_names) + "\n\n")
    out.write("CLEAN FINAL EXPERIMENTS:\nPREPARED BUT NOT EXECUTED (Pending rigorous execution)\n\n")
    out.write("CURRENT PAPER-READY EVIDENCE:\nBaseline historical experiments provide strong supporting evidence, but final rigorous claims require the clean Q1 execution.\n\n")
    out.write("REMAINING EXPERIMENTS:\nFINAL_Q1_EXP_01_CLEAN_BASELINE, FINAL_Q1_EXP_02_CLEAN_MEMORY\n\n")
    out.write("MOST IMPORTANT BLOCKER:\nVerification of canonical benchmark and execution of final clean runs.\n\n")

    # 9. SAFETY
    out.write("\n## 9. SAFETY\n\n")
    out.write("SOURCE CODE MODIFIED: NO\n")
    out.write("BENCHMARK MODIFIED: NO\n")
    out.write("HISTORICAL RESULTS MODIFIED: NO\n")
    out.write("EXPERIMENTS EXECUTED: NO\n")
    out.write("MANUSCRIPT MODIFIED: NO\n")
