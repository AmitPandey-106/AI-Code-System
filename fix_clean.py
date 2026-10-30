with open("experiments/CONTROLLED_LORA_PROOF/build_controlled_proof_zip.py", "r") as f:
    code = f.read()

import re
new_clean = """def is_clean_file(rel_path):
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
"""
code = re.sub(r'def is_clean_file\(rel_path\):.*?return True', new_clean, code, flags=re.DOTALL)

with open("experiments/CONTROLLED_LORA_PROOF/build_controlled_proof_zip.py", "w") as f:
    f.write(code)
print("Fixed is_clean_file")
