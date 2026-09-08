import subprocess
import uuid
import os
import re
import traceback
import tempfile
import shutil
from app.security import validate_code

EXECUTION_TIMEOUT = 5
EXECUTION_MODE = "sandbox"  # Indicates we are using a controlled directory and restricted environment

# 🔥 CLEAN GENERATED CODE
def clean_code(code: str):
    lines = code.split("\n")
    cleaned = []
    junk_prefixes = [
        "Explanation", "Output:", "Example:", "Expected Output", "Traceback",
        "Error:", "Test Call:", "Test:", "Input:"
    ]
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if any(stripped.lower().startswith(j.lower()) for j in junk_prefixes):
            continue
        cleaned.append(line.rstrip())
    return "\n".join(cleaned).strip()

# 🔥 SMART EXECUTION CALLER
def ensure_execution(code: str):
    if "print(" in code:
        return code
    match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)", code)
    if not match:
        return code

    func_name = match.group(1)
    params = match.group(2).strip()
    param_count = len([p for p in params.split(",") if p.strip()]) if params else 0
    lower_name = func_name.lower()

    if param_count == 0:
        args = ""
    elif param_count == 1:
        if any(k in lower_name for k in ["reverse", "string", "palindrome", "text"]):
            args = "'hello'"
        elif any(k in lower_name for k in ["list", "sort", "array"]):
            args = "[3,1,2]"
        else:
            args = "5"
    elif param_count == 2:
        if any(k in lower_name for k in ["merge", "concat"]):
            args = "[1,2], [3,4]"
        else:
            args = "10, 5"
    else:
        args = ", ".join(["1"] * param_count)

    code += f"\n\nprint({func_name}({args}))"
    return code

# 🚀 MAIN EXECUTOR
def execute_code(code: str, test_code: str = ""):
    # 1. Clean Code
    code = clean_code(code)
    
    # 2. Append tests or auto-execution
    full_code = code
    if test_code:
        full_code = code + "\n\n" + test_code
    elif not "print(" in code and not test_code:
        full_code = ensure_execution(code)

    # 3. Static AST Syntax & Safety Validation
    validation = validate_code(full_code)
    
    if not validation["syntax_passed"] or not validation["safety_passed"]:
        return {
            "success": False,
            "output": "",
            "error": validation["error_message"],
            "verification": validation
        }

    # 4. Controlled Execution Environment
    # We use a temporary directory and minimal environment variables
    with tempfile.TemporaryDirectory() as temp_dir:
        file_name = os.path.join(temp_dir, f"script_{uuid.uuid4().hex}.py")
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(full_code)

        # Minimal environment to isolate from project secrets/paths
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")
        }

        try:
            result = subprocess.run(
                ["python", file_name],
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT,
                env=env,
                cwd=temp_dir
            )

            output = result.stdout.strip()
            error = result.stderr.strip()

            if output == "" and error == "":
                output = "NO_OUTPUT"

            return {
                "success": result.returncode == 0,
                "output": output,
                "error": error,
                "verification": validation
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "TimeoutError: Execution exceeded configured timeout",
                "verification": validation
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": traceback.format_exc(),
                "verification": validation
            }