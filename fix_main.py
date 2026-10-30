import re
with open("app/main.py", "r") as f:
    main_code = f.read()

main_code = re.sub(
    r'if "PROOF_T10" in str\(req\.task_id\):',
    r'if str(req.task_id).strip() == "PROOF_T10":',
    main_code
)
for i in range(1, 10):
    main_code = re.sub(
        rf'elif "PROOF_T{i}" in str\(req\.task_id\):',
        rf'elif str(req.task_id).strip() == "PROOF_T{i}":',
        main_code
    )

with open("app/main.py", "w") as f:
    f.write(main_code)
print("Fixed app/main.py")
