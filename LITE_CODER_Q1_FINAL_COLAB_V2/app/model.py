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

import json

_base_model = None
_model = None
_tokenizer = None
_loaded_adapter_id = None

def reload_model():
    global _model, _base_model, _loaded_adapter_id
    _model = None
    _base_model = None
    _loaded_adapter_id = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def check_and_reload_adapter():
    global _loaded_adapter_id, _model
    from app.config import config
    
    if not config.get("LORA_ENABLED"):
        if _loaded_adapter_id is not None:
            reload_model()
        return
        
    meta_path = "models/adapters/active/metadata.json"
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                disk_id = json.load(f).get("adapter_id")
            if disk_id and disk_id != _loaded_adapter_id:
                reload_model()
        except Exception:
            pass
    elif _loaded_adapter_id is not None:
        reload_model()

def get_model():
    global _base_model, _model, _tokenizer, _loaded_adapter_id
    from app.config import config

    if _base_model is None or _tokenizer is None:
        tokenizer = AutoTokenizer.from_pretrained(base_model_name)

        if torch.cuda.is_available():
            selected_dtype = torch.float16
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                torch_dtype=selected_dtype,
                device_map="auto"
            )
        else:
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                torch_dtype=torch.float32
            )

        _base_model = base_model
        _tokenizer = tokenizer

    if _model is None:
        ACTIVE_ADAPTER_PATH = os.path.abspath("models/adapters/active")
        
        if config.get("LORA_ENABLED"):
            meta_path = os.path.join(ACTIVE_ADAPTER_PATH, "metadata.json")
            config_path = os.path.join(ACTIVE_ADAPTER_PATH, "adapter_config.json")
            weights_st = os.path.join(ACTIVE_ADAPTER_PATH, "adapter_model.safetensors")
            weights_bin = os.path.join(ACTIVE_ADAPTER_PATH, "adapter_model.bin")
            has_weights = (os.path.exists(weights_st) and os.path.getsize(weights_st) > 0) or \
                          (os.path.exists(weights_bin) and os.path.getsize(weights_bin) > 0)

            if os.path.exists(ACTIVE_ADAPTER_PATH) and os.path.exists(config_path) and has_weights:
                try:
                    model = PeftModel.from_pretrained(_base_model, ACTIVE_ADAPTER_PATH)
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                _loaded_adapter_id = json.load(f).get("adapter_id", "active_unknown")
                        except Exception:
                            _loaded_adapter_id = "active_unknown"
                    else:
                        _loaded_adapter_id = "active_unknown"
                except Exception as e:
                    print(f"[MODEL ERROR] Failed loading active adapter from {ACTIVE_ADAPTER_PATH}: {e}")
                    model = _base_model
                    _loaded_adapter_id = None
            else:
                model = _base_model
                _loaded_adapter_id = None
        else:
            model = _base_model
            _loaded_adapter_id = None
            
        _model = model
        
    return _model, _tokenizer

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

def extract_code(text: str, required_entry_point: str = None):
    import re
    # 1. Try standard markdown code fences
    matches = re.findall(r'```(?:python|py)?\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    valid_matches = [m.strip() for m in matches if is_code_valid(clean_generated_code(m.strip()), required_entry_point)]
    if valid_matches:
        return max(valid_matches, key=len)
    elif matches:
        return max(matches, key=len).strip()
    
    # 2. Check if text starts after an open code fence and ends with a closing fence
    fence_end = re.search(r'^(.*?)\n```', text, re.DOTALL)
    if fence_end:
        cand = fence_end.group(1).strip()
        if is_code_valid(cand, required_entry_point):
            return cand

    # 3. Fallback to AST shrink method
    lines = text.split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("def ", "class ", "import ", "from ", "@", "if __name__")) or ("=" in stripped and not stripped.startswith(("#", "//"))):
            start_idx = i
            break
            
    code_lines = lines[start_idx:]
    for end_idx in range(len(code_lines), 0, -1):
        candidate = "\n".join(code_lines[:end_idx])
        if is_code_valid(candidate, required_entry_point):
            return candidate.strip()
            
    return text.strip()


# =========================================================
# VALIDATE PYTHON USING AST
# =========================================================

def is_code_valid(code: str, required_entry_point: str = None):

    if not code or not code.strip():
        return False

    try:
        tree = ast.parse(code)
        if not tree.body:
            return False

        if required_entry_point:
            has_entry = False
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == required_entry_point:
                    has_entry = True
                    break
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if getattr(target, "id", None) == required_entry_point:
                            has_entry = True
                            break
            if not has_entry:
                return False

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

def generate_raw(prompt, max_new_tokens=None, temperature=None):
    model, tokenizer = get_model()

    target_device = get_input_device(model)
    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to(target_device)

    with torch.no_grad():
        from app.config import config
        
        deterministic = config.get("DETERMINISTIC_GENERATION", False)
        token_limit = max_new_tokens or config.get("MAX_NEW_TOKENS", 768)
        
        generation_kwargs = {
            "max_new_tokens": token_limit,
            "repetition_penalty": 1.1,
            "eos_token_id": tokenizer.eos_token_id,
            "pad_token_id": tokenizer.eos_token_id
        }
        
        if deterministic:
            generation_kwargs["do_sample"] = False
        else:
            generation_kwargs.update({
                "do_sample": True,
                "temperature": temperature if temperature is not None else 0.2,
                "top_p": 0.95
            })
        
        # If LORA_ENABLED is False and we have a PEFT model, disable it for this generation
        if not config.get("LORA_ENABLED") and hasattr(model, "disable_adapter"):
            with model.disable_adapter():
                outputs = model.generate(**inputs, **generation_kwargs)
        else:
            outputs = model.generate(**inputs, **generation_kwargs)

    input_length = inputs["input_ids"].shape[-1]
    generated = tokenizer.decode(
        outputs[0][input_length:],
        skip_special_tokens=True
    ).strip()

    return generated


# =========================================================
# MAIN CODE GENERATION
# =========================================================

def generate_code(user_prompt, approved_plan=None, contract=None):
    
    # ==============================================
    # STEP 1: GENERATE PLAN
    # ==============================================

    if approved_plan:
        plan = approved_plan
    else:
        plan = generate_plan(user_prompt, contract=contract)
    
    print("\n========== GENERATED PLAN ==========")
    print(plan)
    print("====================================\n")

    # ==============================================
    # STEP 2: BUILD PROMPT
    # ==============================================

    contract_instructions = ""
    if contract and hasattr(contract, "format_contract_instruction"):
        contract_instructions = contract.format_contract_instruction()

    formatted_prompt = f"""
You are an expert Python software engineer.

Your task is to generate HIGH-QUALITY executable Python programs.
{contract_instructions}
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

        req_entry = getattr(contract, "entry_point", None) if contract else None

        code = extract_code(generated, required_entry_point=req_entry)

        code = clean_generated_code(code)

        if is_code_valid(code, required_entry_point=req_entry): 
            return code, formatted_prompt

    return "", formatted_prompt


# =========================================================
# FIX CODE
# =========================================================

# =========================================================
# FIX CODE
# =========================================================

def fix_code(original_code, error, retrieved_context="", strategy_prompt="", task_contract=None, attempt_history=None, temperature=None):

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
    # BUILD FIX PROMPT WITH CONTRACT & CUMULATIVE HISTORY
    # =====================================================

    contract_section = ""
    if task_contract:
        if hasattr(task_contract, "format_contract_instruction"):
            contract_section = task_contract.format_contract_instruction()
        elif getattr(task_contract, "task_prompt", None):
            contract_section = f"\nORIGINAL TASK:\n{task_contract.task_prompt}\n"

    history_section = ""
    if attempt_history:
        history_lines = []
        for prev in attempt_history[-3:]:
            att_num = prev.get("attempt", prev.get("attempt_number", "?"))
            prev_err = prev.get("error_type", "") or prev.get("error", "").split("\n")[-1]
            history_lines.append(f"- Attempt {att_num}: Failed with '{prev_err}'")
        if history_lines:
            history_section = "PREVIOUS REPAIR ATTEMPTS IN THIS RUN:\n" + "\n".join(history_lines) + "\nDo NOT repeat previous failed repair strategies or re-introduce earlier errors.\n"

    memory_section = ""
    if retrieved_context:
        memory_section = f"""
SUPPORTING REPAIR MEMORY (Guidance only - do NOT alter required entry point or task contract):
{retrieved_context}
"""

    target_mention = ""
    if task_contract and getattr(task_contract, "entry_point", None):
        target_mention = f" containing '{task_contract.entry_point}'"

    debug_prompt = f"""
You are an expert Python debugger and software engineer.
{contract_section}
{system_instruction}

{history_section}
{memory_section}
CURRENT PROBLEM:
BROKEN CODE:
{original_code}

ERROR:
{error}

IMPORTANT:
- Return ONLY executable Python code
- NO explanations
- NO markdown
- NO comments
- Avoid placeholders or comments like '# Your solution here'
- Implement the complete working logic
- Return the FULL, COMPLETE corrected Python program{target_mention}.
- Do NOT return a patch, diff, isolated replacement line, or partial snippet.
- The returned code will replace the entire previous program and must be independently executable.
- Preserve all previously satisfied requirements and do not discard the required entry point.

Return corrected executable Python code:
"""

    # =====================================================
    # RETRY FIXING
    # =====================================================

    req_entry = getattr(task_contract, "entry_point", None) if task_contract else None

    # Temperature changes ONLY after repeated candidate
    active_temp = temperature
    if active_temp is None:
        if attempt_history and any(prev.get("is_repeated_candidate") for prev in attempt_history[-1:]):
            active_temp = 0.6
        else:
            active_temp = 0.2

    for attempt in range(3):

        generated = generate_raw(debug_prompt, temperature=active_temp)

        code = extract_code(generated, required_entry_point=req_entry)

        code = clean_generated_code(code)

        if is_code_valid(code, required_entry_point=req_entry):
            return code, debug_prompt

    return "", debug_prompt


def generate_plan(user_prompt, contract=None):
    from app.contract import validate_plan_against_contract

    contract_instructions = ""
    if contract and hasattr(contract, "format_contract_instruction"):
        contract_instructions = contract.format_contract_instruction()
    elif contract and getattr(contract, "entry_point", None):
        contract_instructions = f"\nPRIMARY ENTRY POINT: {contract.entry_point}\n"

    planning_prompt = f"""
You are an expert software architect.

Create a comprehensive step-by-step implementation plan for solving the programming task.
{contract_instructions}
STRICT RULES:
- Return ONLY numbered steps
- NO code
- Address EVERY listed requirement, constraint, edge case, and tie-breaking rule
- Plan must explicitly account for boundary cases (e.g. n <= 0, empty inputs, tie-breaks, invalid data)
- Focus on algorithmic logic

TASK:
{user_prompt}

PLAN:
"""

    generated = generate_raw(planning_prompt)
    # Filter out any hallucinated code blocks to keep plan purely algorithmic
    cleaned_plan = re.sub(r'```(?:python|py)?\s*.*?```', '', generated, flags=re.DOTALL).strip()
    plan_result = cleaned_plan or generated.strip()

    # Plan requirement preservation validation
    if contract:
        is_valid, missing_reqs = validate_plan_against_contract(plan_result, contract)
        if missing_reqs:
            # Systematically preserve requirements by enriching plan with missing contract constraints
            enrichment_steps = []
            start_num = len(re.findall(r'^\d+\.', plan_result, re.M)) + 1
            for idx, req in enumerate(missing_reqs):
                enrichment_steps.append(f"{start_num + idx}. Enforce requirement: {req}.")
            plan_result = plan_result + "\n\nCRITICAL CONTRACT REQUIREMENTS TO ENFORCE:\n" + "\n".join(enrichment_steps)

    return plan_result


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