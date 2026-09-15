import re
import ast

def is_code_valid(code: str):
    if not code.strip():
        return False
    try:
        ast.parse(code)
        return True
    except Exception:
        return False

def extract_code(text: str):
    matches = re.findall(r'```(?:python)?\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if matches:
        return max(matches, key=len).strip()
    
    lines = text.split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("def ", "class ", "import ", "from ", "@")) or ("=" in stripped and not stripped.startswith("#")):
            start_idx = i
            break
            
    code_lines = lines[start_idx:]
    for end_idx in range(len(code_lines), 0, -1):
        candidate = "\n".join(code_lines[:end_idx])
        if is_code_valid(candidate):
            return candidate.strip()
            
    return text.strip()

print("TEST 1")
print(extract_code("def foo():\n    return 1\n\nThis is a test."))

print("\nTEST 2")
print(extract_code("Here is the code:\n```python\ndef foo():\n    return 1\n```\nExplanation."))

print("\nTEST 3")
print(extract_code("```\nimport os\ndef bar(): pass\n```"))
