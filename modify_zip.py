with open("experiments/CONTROLLED_LORA_PROOF/build_controlled_proof_zip.py", "r") as f:
    code = f.read()

code = code.replace("LITE_CODER_CONTROLLED_LORA_PROOF.zip", "LITE_CODER_FINAL_RELEASE_CANDIDATE_V6.zip")

with open("experiments/CONTROLLED_LORA_PROOF/build_controlled_proof_zip.py", "w") as f:
    f.write(code)
print("Modified zip script")
