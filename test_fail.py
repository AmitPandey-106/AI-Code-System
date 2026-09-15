from app.model import generate_raw, extract_code, is_code_valid
from app.config import config

def test_generation():
    config.set("DETERMINISTIC_GENERATION", True)
    
    prompt = """
You are an expert Python debugger.

STRATEGY:
Use the observed test failures to identify the behavioral defect before modifying the code. Focus on edge cases.

STRICT RULES:
- Return executable Python code
- Avoid syntax issues
- Preserve intended functionality

IMPORTANT:
- Return ONLY executable Python code
- NO explanations
- NO markdown
- NO comments
- Return the FULL, COMPLETE corrected Python program.
- Do NOT return a patch, diff, isolated replacement line, or partial snippet.
- The returned code will replace the entire previous program and must be independently executable.

CURRENT PROBLEM:
BROKEN CODE:
def concat(a, b):
    return a + " " + b

print(concat("Hello", "World"))

ERROR:
Test Failed
Traceback (most recent call last):
  File "C:\\Users\\T14s\\AppData\\Local\\Temp\\tmpi9ofyk4q\\script_067168dcedcc43f699d72795540854bd.py", line 10, in <module>
    assert concat('a', 'b') == 'ab'
AssertionError


Return corrected executable Python code:
"""
    raw = generate_raw(prompt)
    print("=== RAW ===")
    print(raw)
    print("=== EXTRACTED ===")
    extracted = extract_code(raw)
    print(extracted)
    print("=== IS VALID ===")
    print(is_code_valid(extracted))

if __name__ == "__main__":
    test_generation()
