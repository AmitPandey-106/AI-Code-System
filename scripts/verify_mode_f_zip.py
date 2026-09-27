import zipfile

zip_path = "package_output/LITE_CODER_MODE_F_100TASK.zip"
zf = zipfile.ZipFile(zip_path)
names = sorted(zf.namelist())
print("Total entries in ZIP:", len(names))

for idx, name in enumerate(names):
    info = zf.getinfo(name)
    print(f"{idx+1:2d}. {name} ({info.file_size:,} bytes)")

# 1. Dataset is included
assert "data/benchmark/v1.0/dataset.json" in names, "Dataset missing!"

# 2. Scripts included
assert "scripts/colab_mode_f_setup.py" in names, "scripts/colab_mode_f_setup.py missing!"
assert "scripts/run_mode_f_100.py" in names, "scripts/run_mode_f_100.py missing!"

# 3. app/main.py contains Fix A and Linux-safe subprocess handling
main_py = zf.read("app/main.py").decode("utf-8")
assert 'next_err = next_att.get("error_type") or ""' in main_py, "Fix A missing in app/main.py!"
assert 'getattr(subprocess, "CREATE_NEW_CONSOLE", 0)' in main_py, "Linux-safe CREATE_NEW_CONSOLE missing!"
assert 'getattr(subprocess, "DETACHED_PROCESS", 0)' in main_py, "Linux-safe DETACHED_PROCESS missing!"

# 4. Fix B is absent
strategy_record_body = main_py.split("def record_strategy_outcomes")[1].split("def generate")[0]
assert "if not config.get" not in strategy_record_body, "Fix B bypass guard present in record_strategy_outcomes!"

# 5. benchmark/ablation.py contains canonical MODE-F
ablation_py = zf.read("benchmark/ablation.py").decode("utf-8")
assert 'elif mode == "MODE_F":' in ablation_py, "MODE_F missing in benchmark/ablation.py!"
assert 'config.set("LORA_ENABLED", True)' in ablation_py, "LORA_ENABLED True missing for MODE_F in benchmark/ablation.py!"
assert 'config.set("MEMORY_ENABLED", True)' in ablation_py, "MEMORY_ENABLED True missing for MODE_F in benchmark/ablation.py!"
assert 'config.set("STRATEGY_LEARNING_ENABLED", True)' in ablation_py, "STRATEGY_LEARNING_ENABLED True missing for MODE_F in benchmark/ablation.py!"
assert 'config.set("DIFFICULTY_ALLOCATION_ENABLED", True)' in ablation_py, "DIFFICULTY_ALLOCATION_ENABLED True missing for MODE_F in benchmark/ablation.py!"

print("\nALL VERIFICATION CHECKS INSIDE ZIP PASSED SUCCESSFULLY!")
