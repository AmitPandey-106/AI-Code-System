from app.executor import execute_code

print("Test 1: Normal Code")
code1 = "def add(a, b):\n    return a + b\n\nprint(add(1, 2))"
res1 = execute_code(code1)
print(res1)

print("\nTest 2: Security Violation (import os)")
code2 = "import os\nos.system('echo dangerous')"
res2 = execute_code(code2)
print(res2)

print("\nTest 3: Security Violation (eval)")
code3 = "eval('1+1')"
res3 = execute_code(code3)
print(res3)

print("\nTest 4: Timeout")
code4 = "while True:\n    pass"
res4 = execute_code(code4)
print(res4)

print("\nTest 5: Syntax Error")
code5 = "def foo()\n    pass"
res5 = execute_code(code5)
print(res5)

print("\nTest 6: With Tests (tester logic simulation)")
test_code = """
import json
test_results = {'total': 1, 'passed': 0, 'failed': 0, 'errors': 0, 'success': True, 'message': 'All tests passed'}
try:
    assert add(1, 2) == 3
    test_results['passed'] += 1
except AssertionError as e:
    test_results['failed'] += 1
    test_results['success'] = False

print('___TEST_RESULTS___')
print(json.dumps(test_results))
"""
res6 = execute_code("def add(a, b):\n    return a + b", test_code=test_code)
print(res6)
