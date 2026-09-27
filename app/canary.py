import json
import traceback
from typing import Dict, List, Optional
import torch
from app.executor import execute_code
from app.training_dataset import format_repair_prompt

# Deterministic Canary Evaluation Suite
# Covers core Python primitives susceptible to negative transfer:
# 1. Parity logic (is_even) - prime vulnerability observed in MODE-F Trained
# 2. Numerical bounds logic (in_range)
# 3. Basic arithmetic logic (add)
CANARY_SUITE = [
    {
        "task_id": "CANARY_PARITY_001",
        "name": "is_even",
        "broken_code": "def is_even(n):\n    return n % 2 != 0\n",
        "error_message": "assert is_even(2) == True failed",
        "tests": "assert is_even(2) == True\nassert is_even(3) == False\nassert is_even(0) == True\nassert is_even(-2) == True\nassert is_even(101) == False"
    },
    {
        "task_id": "CANARY_RANGE_002",
        "name": "in_range",
        "broken_code": "def in_range(val, min_val, max_val):\n    return val > min_val and val < max_val\n",
        "error_message": "assert in_range(1, 1, 10) == True failed",
        "tests": "assert in_range(5, 1, 10) == True\nassert in_range(1, 1, 10) == True\nassert in_range(10, 1, 10) == True\nassert in_range(0, 1, 10) == False\nassert in_range(11, 1, 10) == False"
    },
    {
        "task_id": "CANARY_ARITH_003",
        "name": "add",
        "broken_code": "def add(a, b):\n    return a - b\n",
        "error_message": "assert add(2, 3) == 5 failed",
        "tests": "assert add(2, 3) == 5\nassert add(0, 0) == 0\nassert add(-5, 5) == 0\nassert add(10, -2) == 8"
    }
]

def format_canary_test_script(test_code_str: str) -> str:
    test_lines = [t.strip() for t in test_code_str.split("\n") if t.strip()]
    total_tests = len(test_lines)
    
    wrapper = [
        "import json",
        "import traceback",
        f"test_results = {{'total': {total_tests}, 'passed': 0, 'failed': 0, 'errors': 0, 'message': 'All tests passed', 'success': True}}",
        "try:"
    ]
    
    if total_tests == 0:
        wrapper.append("    pass")
    else:
        for t in test_lines:
            wrapper.append(f"    {t}")
            wrapper.append("    test_results['passed'] += 1")
            
    wrapper.append("except AssertionError as e:")
    wrapper.append("    test_results['failed'] += 1")
    wrapper.append("    test_results['success'] = False")
    wrapper.append("    test_results['message'] = 'Assertion failed: ' + str(e)")
    wrapper.append("except Exception as e:")
    wrapper.append("    test_results['errors'] += 1")
    wrapper.append("    test_results['success'] = False")
    wrapper.append("    test_results['message'] = str(e)")
    
    wrapper.append("print('___TEST_RESULTS___')")
    wrapper.append("print(json.dumps(test_results))")
    
    return "\n".join(wrapper)

def clean_generated_code(generated_text: str, prompt: str) -> str:
    code = generated_text.replace(prompt, "").strip()
    lines = code.split("\n")
    cleaned = []
    in_code_block = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```python") or stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        cleaned.append(line.rstrip())
        
    return "\n".join(cleaned).strip()

def evaluate_canary_gate(
    model,
    tokenizer,
    canary_suite: Optional[List[Dict]] = None,
    threshold: float = 1.0
) -> Dict:
    """
    Evaluates candidate model against canary suite before promotion.
    Returns detailed pass/fail report and canary metrics.
    """
    suite = canary_suite or CANARY_SUITE
    total = len(suite)
    passed_count = 0
    task_results = []
    
    print(f"[CANARY GATE] Evaluating candidate adapter on {total} deterministic canary tasks...")
    
    model.eval()
    for task in suite:
        tid = task.get("task_id", "CANARY_UNKNOWN")
        name = task.get("name", "unknown")
        broken_code = task.get("broken_code", "")
        error_message = task.get("error_message", "")
        tests = task.get("tests", "")
        
        prompt = format_repair_prompt(broken_code, error_message)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,  # Deterministic evaluation
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id
            )
            
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        candidate_code = clean_generated_code(full_text, prompt)
        
        # Test candidate code
        test_script = format_canary_test_script(tests)
        exec_res = execute_code(candidate_code, test_code=test_script)
        
        task_passed = False
        err_msg = None
        
        if exec_res.get("success") and "___TEST_RESULTS___" in exec_res.get("output", ""):
            json_str = exec_res["output"].split("___TEST_RESULTS___")[-1].strip()
            try:
                res_data = json.loads(json_str)
                if res_data.get("success") and res_data.get("failed", 0) == 0 and res_data.get("errors", 0) == 0:
                    task_passed = True
                else:
                    err_msg = res_data.get("message", "Test assertion failed")
            except Exception as parse_err:
                err_msg = f"Failed to parse test output: {parse_err}"
        else:
            err_msg = exec_res.get("error", "Execution failed")
            
        if task_passed:
            passed_count += 1
            print(f"[CANARY GATE]   Task {tid} ({name}): PASSED")
        else:
            print(f"[CANARY GATE]   Task {tid} ({name}): FAILED -> {err_msg}")
            
        task_results.append({
            "task_id": tid,
            "name": name,
            "passed": task_passed,
            "error": err_msg,
            "generated_code_snippet": candidate_code[:120].replace("\n", " ") if candidate_code else ""
        })
        
    success_rate = passed_count / total if total > 0 else 0.0
    gate_passed = success_rate >= threshold
    
    print(f"[CANARY GATE] Result: {passed_count}/{total} passed ({success_rate*100:.1f}%). Required threshold: {threshold*100:.1f}%. Gate Passed: {gate_passed}")
    
    return {
        "gate_passed": gate_passed,
        "canary_tasks_count": total,
        "canary_passed_count": passed_count,
        "canary_failed_count": total - passed_count,
        "canary_success_rate": round(success_rate, 4),
        "threshold": threshold,
        "task_results": task_results
    }
