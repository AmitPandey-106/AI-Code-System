import json
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from app.executor import execute_code

def evaluate_model_on_test_set(base_model_name: str, adapter_path: str, test_file: str):
    """Evaluates a specific model (base + adapter) on the independent test set."""
    if not os.path.exists(test_file):
        return {"error": "Test set not found."}
        
    with open(test_file, "r", encoding="utf-8") as f:
        test_data = json.load(f)
        
    if len(test_data) == 0:
        return {"error": "Test set is empty."}
        
    print(f"Loading base model {base_model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float32,
        device_map="auto"
    )
    
    if adapter_path and os.path.exists(adapter_path):
        print(f"Loading adapter {adapter_path}...")
        model = PeftModel.from_pretrained(base_model, adapter_path)
    else:
        print("Using base model directly (no adapter).")
        model = base_model
        
    model.eval()
    
    metrics = {
        "total": len(test_data),
        "syntax_success": 0,
        "safety_success": 0,
        "execution_success": 0
    }
    
    for item in test_data:
        broken = item["raw_broken_code"]
        error = item["raw_error_message"]
        
        prompt = f"You are an expert Python debugger.\n\nFix the Python code carefully.\nSTRICT RULES:\n- Return executable Python code\n- Avoid syntax issues\n- Preserve intended functionality\n\nIMPORTANT:\n- Return ONLY executable Python code\n- NO explanations\n- NO markdown\n- NO comments\n\nCURRENT PROBLEM:\nBROKEN CODE:\n{broken}\n\nERROR:\n{error}\n\nReturn corrected executable Python code:\n"
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs, max_new_tokens=300, do_sample=True, temperature=0.2, top_p=0.95, repetition_penalty=1.1,
                eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id
            )
        full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
        generated = full_output.replace(prompt, "").strip()
        
        # Clean
        lines = generated.split("\n")
        cleaned = []
        for line in lines:
            if line.strip().startswith("```"): continue
            cleaned.append(line.rstrip())
        code = "\n".join(cleaned).strip()
        
        tests = item.get("raw_tests", "")
        test_lines = [t.strip() for t in tests.split("\n") if t.strip()]
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
                wrapper.append(f"    test_results['passed'] += 1")
                
        wrapper.append("except AssertionError as e:")
        wrapper.append("    test_results['failed'] += 1")
        wrapper.append("    test_results['success'] = False")
        wrapper.append("except Exception as e:")
        wrapper.append("    test_results['errors'] += 1")
        wrapper.append("    test_results['success'] = False")
        
        wrapper.append("print('___TEST_RESULTS___')")
        wrapper.append("print(json.dumps(test_results))")
        
        safe_test_script = "\n".join(wrapper)
        
        exec_res = execute_code(code, test_code=safe_test_script)
        
        if exec_res.get("verification", {}).get("syntax_passed"):
            metrics["syntax_success"] += 1
        if exec_res.get("verification", {}).get("safety_passed"):
            metrics["safety_success"] += 1
        if exec_res["success"] and "___TEST_RESULTS___" in exec_res["output"]:
            json_str = exec_res["output"].split("___TEST_RESULTS___")[-1].strip()
            try:
                results = json.loads(json_str)
                if results.get("success"):
                    metrics["execution_success"] += 1
            except:
                pass
            
    # Free VRAM
    del model
    del base_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    return metrics
