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
def ensure_execution(code: str, contract=None):
    if "print(" in code:
        return code

    func_name = None
    params = ""

    # 1. If TaskContract specifies an entry point, target that specific entry point
    if contract and getattr(contract, "entry_point", None):
        target_fn = contract.entry_point
        match = re.search(rf"def\s+{re.escape(target_fn)}\s*\((.*?)\)", code)
        if match:
            func_name = target_fn
            params = match.group(1).strip()
        else:
            # Do NOT call an arbitrary helper function if required entry point is missing
            return code
    else:
        # Fallback: find the first defined function
        match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)", code)
        if not match:
            return code
        func_name = match.group(1)
        params = match.group(2).strip()

    param_list = [p.strip().split(":")[0].strip() for p in params.split(",") if p.strip()]
    param_count = len(param_list)
    lower_name = func_name.lower()
    lower_params = [p.lower() for p in param_list]

    STR_KEYWORDS = {"s", "str", "string", "text", "sentence", "word", "line", "chars"}
    LIST_KEYWORDS = {"arr", "nums", "lst", "list", "array", "data", "elements", "values", "items"}

    if param_count == 0:
        args = ""
    elif param_count == 1:
        p0 = lower_params[0]
        if any(k in lower_name for k in ["reverse", "string", "palindrome", "text"]) or p0 in STR_KEYWORDS:
            args = "'hello'"
        elif any(k in lower_name for k in ["list", "sort", "array", "average", "avg", "sum", "mean"]) or p0 in LIST_KEYWORDS:
            args = "[10, 20, 30]"
        else:
            args = "5"
    elif param_count == 2:
        if lower_params[1] in ("n", "k", "limit", "count", "top_n", "size"):
            args = "[], 0"
        elif any(k in lower_name for k in ["search", "find", "index", "binary"]) or any(p in LIST_KEYWORDS for p in lower_params):
            args = "[1, 3, 5, 7, 9, 11], 5"
        elif any(k in lower_name for k in ["merge", "concat"]) or all(p in LIST_KEYWORDS for p in lower_params):
            args = "[1, 2], [3, 4]"
        elif any(p in STR_KEYWORDS for p in lower_params):
            args = "'hello', 'l'"
        else:
            args = "10, 5"
    else:
        args = ", ".join(["1"] * param_count)

    code += f"\n\ntry:\n    print({func_name}({args}))\nexcept Exception:\n    pass"
    return code

# 🚀 MAIN EXECUTOR
def execute_code(code: str, test_code: str = "", contract=None):
    # 1. Clean Code
    code = clean_code(code)
    
    # 2. Append tests or auto-execution
    full_code = code
    if test_code:
        full_code = code + "\n\n" + test_code
    elif not "print(" in code and not test_code:
        full_code = ensure_execution(code, contract=contract)

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