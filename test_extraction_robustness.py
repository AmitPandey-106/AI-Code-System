from app.model import extract_code

def test_extraction_robustness():
    # TEST 1: Plain Python output
    code1 = "def concat(a, b):\n    return a + b\n"
    assert extract_code(code1) == "def concat(a, b):\n    return a + b"
    
    # TEST 2: Python fenced with ```python
    code2 = "```python\ndef concat(a, b):\n    return a + b\n```"
    assert extract_code(code2) == "def concat(a, b):\n    return a + b"
    
    # TEST 3: Generic ``` fence
    code3 = "```\ndef concat(a, b):\n    return a + b\n```"
    assert extract_code(code3) == "def concat(a, b):\n    return a + b"
    
    # TEST 4: Python fence followed by conversational explanation
    code4 = "```python\ndef concat(a, b):\n    return a + b\n```\nThis fixes the issue by returning the concatenation directly."
    assert extract_code(code4) == "def concat(a, b):\n    return a + b"
    
    # TEST 5: Conversational text before Python fence
    code5 = "Here is the code:\n```python\ndef concat(a, b):\n    return a + b\n```"
    assert extract_code(code5) == "def concat(a, b):\n    return a + b"
    
    # TEST 6: Valid multi-function program
    code6 = "def helper():\n    pass\n\ndef concat(a, b):\n    return a + b"
    assert extract_code(code6) == "def helper():\n    pass\n\ndef concat(a, b):\n    return a + b"
    
    # TEST 7: Valid imports/classes/constants
    code7 = "import math\n\nMAX_LEN = 10\n\nclass Concatenator:\n    def concat(self, a, b):\n        return a + b\n"
    assert extract_code(code7) == "import math\n\nMAX_LEN = 10\n\nclass Concatenator:\n    def concat(self, a, b):\n        return a + b"
    
    # TEST 8: Invalid generated Python is rejected
    # AST will fail, it should return the stripped text and let is_code_valid reject it later
    code8 = "This is not python code\ndef foo():\nreturn 1"
    res = extract_code(code8)
    from app.model import is_code_valid
    assert not is_code_valid(res)
    
    print("ALL EXTRACTION TESTS PASSED!")

if __name__ == "__main__":
    test_extraction_robustness()
