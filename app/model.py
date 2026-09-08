from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
import ast
import re

# =========================================================
# MODEL LOADING
# =========================================================

base_model_name = "Qwen/Qwen2.5-Coder-1.5B"
import os

tokenizer = AutoTokenizer.from_pretrained(base_model_name)

if torch.cuda.is_available():
    selected_device = "cuda"
    selected_dtype = torch.float16
    gpu_name = torch.cuda.get_device_name(0)
    print(f"CUDA is available.")
    print(f"GPU Name: {gpu_name}")
    print(f"Selected device: {selected_device}")
    print(f"Selected dtype: {selected_dtype}")
    
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=selected_dtype,
        device_map="auto"
    )
else:
    print("CUDA is NOT available. CPU inference is being used.")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float32,
        device_map="auto"
    )

# Active adapter paths
ACTIVE_ADAPTER_PATH = "models/adapters/active"
LEGACY_ADAPTER_PATH = "lora-finetuned"

if os.path.exists(ACTIVE_ADAPTER_PATH):
    model = PeftModel.from_pretrained(base_model, ACTIVE_ADAPTER_PATH)
    print("Active LoRA adapter loaded successfully.")
elif os.path.exists(LEGACY_ADAPTER_PATH):
    model = PeftModel.from_pretrained(base_model, LEGACY_ADAPTER_PATH)
    print("Legacy LoRA adapter loaded successfully.")
else:
    model = base_model
    print("No LoRA adapter found. Using base model.")

from app.config import config


# =========================================================
# CLEAN GENERATED CODE
# =========================================================

def clean_generated_code(code: str):

    lines = code.split("\n")

    cleaned = []

    junk_prefixes = [
        "Explanation",
        "Output:",
        "Example:",
        "Expected Output",
        "Test Call:",
        "Test:",
        "Input:",
        "Python Code:",
        "Fixed Code:",
        "Corrected Code:",
        "Code:",
        "Error:",
        "Traceback"
    ]

    for line in lines:

        stripped = line.strip()

        # remove markdown
        if stripped.startswith("```"):
            continue

        # remove junk labels
        if any(
            stripped.lower().startswith(j.lower())
            for j in junk_prefixes
        ):
            continue

        cleaned.append(line.rstrip())

    return "\n".join(cleaned).strip()


# =========================================================
# EXTRACT CODE
# =========================================================

def extract_code(text: str):

    text = text.replace("```python", "")
    text = text.replace("```", "")

    lines = text.split("\n")

    collected = []

    started = False

    for line in lines:

        stripped = line.strip()

        # detect start
        if stripped.startswith((
            "def ",
            "class ",
            "import ",
            "from ",
            "arr ",
            "nums ",
            "if __name__"
        )):
            started = True

        if not started:
            continue

        # stop garbage
        if stripped.startswith((
            "Explanation",
            "Example",
            "Output",
            "Expected",
            "Traceback",
            "Error:"
        )):
            break

        collected.append(line.rstrip())

    return "\n".join(collected).strip()


# =========================================================
# VALIDATE PYTHON USING AST
# =========================================================

def is_code_valid(code: str):

    if not code.strip():
        return False

    try:
        ast.parse(code)
        return True

    except Exception:
        return False


# =========================================================
# GENERATE RAW OUTPUT
# =========================================================

def get_input_device(model_obj):
    """Helper to safely determine the correct input device for the model."""
    try:
        return next(model_obj.parameters()).device
    except Exception:
        return model_obj.device if hasattr(model_obj, 'device') else torch.device('cpu')

def generate_raw(prompt):

    target_device = get_input_device(model)
    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to(target_device)

    with torch.no_grad():
        from app.config import config
        
        # If LORA_ENABLED is False and we have a PEFT model, disable it for this generation
        if not config.get("LORA_ENABLED") and hasattr(model, "disable_adapter"):
            with model.disable_adapter():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=300,
                    do_sample=True,
                    temperature=0.2,
                    top_p=0.95,
                    repetition_penalty=1.1,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.eos_token_id
                )
        else:
            outputs = model.generate(
                **inputs,
                max_new_tokens=300,
                do_sample=True,
                temperature=0.2,
                top_p=0.95,
                repetition_penalty=1.1,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id
            )

    full_output = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True
    )

    generated = full_output.replace(prompt, "").strip()

    return generated


# =========================================================
# MAIN CODE GENERATION
# =========================================================

def generate_code(user_prompt):
    
    # ==============================================
    # STEP 1: GENERATE PLAN
    # ==============================================

    plan = generate_plan(user_prompt)
    
    print("\n========== GENERATED PLAN ==========")
    print(plan)
    print("====================================\n")

    # ==============================================
    # STEP 2: BUILD PROMPT
    # ==============================================

    formatted_prompt = f"""
You are an expert Python software engineer.

Your task is to generate HIGH-QUALITY executable Python programs.

STRICT RULES:
- Return ONLY valid Python code
- NO explanations
- NO markdown
- NO comments
- NO pseudo code
- Generate COMPLETE runnable programs
- Include required imports
- Include variable definitions if needed
- Include function calls if needed
- Include print statements for final output
- Code must execute successfully
- Avoid syntax errors
- Avoid placeholders
- Avoid unfinished code
- Avoid input() calls
- Use proper Python syntax and indentation
- Prefer clean and efficient solutions

IMPORTANT:
The generated code MUST run directly without modifications.

PLAN:
{plan}

TASK:
{user_prompt}

Generate complete executable Python program:
"""

    # ==============================================
    # STEP 3: RETRY GENERATION
    # ==============================================

    for attempt in range(3):

        generated = generate_raw(formatted_prompt)

        code = extract_code(generated)

        code = clean_generated_code(code)

        if is_code_valid(code): 
            return code

    return ""


# =========================================================
# FIX CODE
# =========================================================

# =========================================================
# FIX CODE
# =========================================================

def fix_code(original_code, error, retrieved_context="", strategy_prompt=""):

    # =====================================================
    # CLASSIFY ERROR
    # =====================================================

    category, error_type, error_message = classify_error(error)

    print(f"\nDetected Error Category: {category}")
    print(f"Detected Specific Error: {error_type}\n")

    # =====================================================
    # SYNTAX ERRORS (Fallback / Category mapping)
    # =====================================================

    if not strategy_prompt:
        if category == "syntax":
            system_instruction = "Focus ONLY on fixing Python syntax issues.\nSTRICT RULES:\n- Fix indentation\n- Fix brackets\n- Fix invalid syntax\n- Keep original logic unchanged"
        elif category == "logic":
            system_instruction = "Focus on fixing logical and algorithmic issues.\nSTRICT RULES:\n- Fix incorrect conditions\n- Fix loops\n- Fix recursion\n- Fix return values\n- Preserve structure where possible"
        elif category == "timeout":
            system_instruction = "Focus on fixing performance and timeout issues.\nSTRICT RULES:\n- Remove infinite loops\n- Optimize recursion\n- Reduce unnecessary computation"
        elif category == "import":
            system_instruction = "Focus on fixing import and dependency issues.\nSTRICT RULES:\n- Add missing imports\n- Remove invalid imports\n- Use standard Python libraries only"
        else:
            system_instruction = "Fix the Python code carefully.\nSTRICT RULES:\n- Return executable Python code\n- Avoid syntax issues\n- Preserve intended functionality"
    else:
        system_instruction = f"STRATEGY:\n{strategy_prompt}\n\nSTRICT RULES:\n- Return executable Python code\n- Avoid syntax issues\n- Preserve intended functionality"

    # =====================================================
    # BUILD FIX PROMPT
    # =====================================================

    memory_section = ""
    if retrieved_context:
        memory_section = f"""
PREVIOUS SUCCESSFUL REPAIR EXPERIENCES:
{retrieved_context}
"""

    debug_prompt = f"""
You are an expert Python debugger.

{system_instruction}

IMPORTANT:
- Return ONLY executable Python code
- NO explanations
- NO markdown
- NO comments
{memory_section}
CURRENT PROBLEM:
BROKEN CODE:
{original_code}

ERROR:
{error}

Return corrected executable Python code:
"""

    # =====================================================
    # RETRY FIXING
    # =====================================================

    for attempt in range(3):

        generated = generate_raw(debug_prompt)

        code = extract_code(generated)

        code = clean_generated_code(code)

        if is_code_valid(code):

            return code

    return ""


def generate_plan(user_prompt):
    
    planning_prompt = f"""
You are an expert software architect.

Create a short step-by-step plan
for solving the programming task.

STRICT RULES:
- Return ONLY numbered steps
- NO code
- Keep steps concise
- Focus on algorithmic logic

TASK:
{user_prompt}

PLAN:
"""

    generated = generate_raw(planning_prompt)

    return generated.strip()


# =========================================================
# CLASSIFY ERRORS
# =========================================================

def classify_error(error: str):

    error_lower = error.lower()
    
    # Try to extract the specific error type and message from the last line of the traceback
    error_type = "UnknownError"
    error_message = error.strip()
    
    if "SecurityViolation" in error:
        error_type = "SecurityViolation"
        error_message = error.split("SecurityViolation:", 1)[-1].strip()
        return "security", error_type, error_message
        
    lines = [line.strip() for line in error.strip().split("\n") if line.strip()]
    if lines:
        last_line = lines[-1]
        # Common Python exception format: "ErrorType: message"
        match = re.match(r"^([a-zA-Z0-9_]+Error):\s*(.*)", last_line)
        if match:
            error_type = match.group(1)
            error_message = match.group(2)
        elif "TimeoutError" in last_line or "TimeoutExpired" in last_line:
            error_type = "TimeoutError"
            error_message = "Execution timed out"
            return "timeout", error_type, error_message
        elif "Test Failed" in error:
            error_type = "AssertionError"
            error_message = "A generated test case failed"
        else:
            # Fallback for syntax errors that might not perfectly match the regex
            for err_kw in ["SyntaxError", "IndentationError", "NameError", "TypeError", 
                          "ValueError", "IndexError", "KeyError", "AttributeError",
                          "ImportError", "ModuleNotFoundError", "ZeroDivisionError", "AssertionError"]:
                if err_kw.lower() in error_lower:
                    error_type = err_kw
                    break

    # Determine category for the fix_code prompt
    category = "general"

    if "syntaxerror" in error_lower or "indentationerror" in error_lower:
        category = "syntax"
    elif any(e in error_lower for e in ["assertionerror", "assertion failed", "indexerror", "typeerror", "valueerror", "keyerror", "nameerror", "attributeerror", "zerodivisionerror"]):
        category = "logic"
    elif "timeoutexpired" in error_lower:
        category = "timeout"
    elif "importerror" in error_lower or "modulenotfounderror" in error_lower:
        category = "import"

    return category, error_type, error_message