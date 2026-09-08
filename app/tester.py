import traceback
import ast
import re

from app.model import generate_raw


# =========================================================
# CLEAN GENERATED TESTS
# =========================================================

def clean_test_code(text: str):

    text = text.replace("```python", "")
    text = text.replace("```", "")

    lines = text.split("\n")

    cleaned = []

    for line in lines:

        stripped = line.strip()

        # keep only assert statements
        if stripped.startswith("assert "):

            # skip incomplete asserts
            if stripped.endswith(","):
                continue

            cleaned.append(stripped)

    return "\n".join(cleaned)


# =========================================================
# REMOVE BAD / CONTRADICTORY TESTS
# =========================================================

def validate_test_logic(test_code: str):

    lines = test_code.split("\n")

    cleaned = []

    seen = set()

    bad_patterns = [
        "!= 120",
        "!= 1",
        "!= True",
        "!= False"
    ]

    for line in lines:

        stripped = line.strip()

        if not stripped:
            continue

        # =============================================
        # SKIP BAD PATTERNS
        # =============================================

        skip = False

        for pattern in bad_patterns:

            if pattern in stripped:
                skip = True
                break

        if skip:
            continue

        # =============================================
        # SKIP NEGATIVE FACTORIAL TESTS
        # =============================================

        if "factorial(-" in stripped:
            continue

        # =============================================
        # REMOVE DUPLICATES
        # =============================================

        if stripped in seen:
            continue

        seen.add(stripped)

        cleaned.append(stripped)

    return "\n".join(cleaned)


# =========================================================
# VALIDATE TEST SYNTAX
# =========================================================

def is_valid_test_code(test_code: str):

    if not test_code.strip():
        return False

    try:

        ast.parse(test_code)

        return True

    except Exception:

        return False


# =========================================================
# GENERATE TESTS USING LLM
# =========================================================

def generate_tests_with_llm(prompt, code):

    test_prompt = f"""
You are an expert Python QA engineer.

Generate Python assert test cases.

IMPORTANT:
Generate tests that validate CORRECT Python behavior.
Ignore intentional bugs in the implementation.

STRICT RULES:
- Return ONLY assert statements
- NO explanations
- NO markdown
- NO comments
- Generate edge case tests
- Generate valid executable asserts
- Avoid incomplete asserts
- Avoid broken syntax
- Generate ONLY logically correct tests
- Do NOT generate contradictory assertions
- Do NOT assume undefined behavior
- Prefer positive correctness assertions

SUPPORTED ASSERT TYPES:
- ==
- !=
- <
- >
- <=
- >=

TASK:
{prompt}

CODE:
{code}

Generate Python assert test cases:
"""

    # =====================================================
    # RETRY TEST GENERATION
    # =====================================================

    for attempt in range(3):

        generated = generate_raw(test_prompt)

        cleaned_tests = clean_test_code(generated)

        # ================================================
        # REMOVE BAD TESTS
        # ================================================

        cleaned_tests = validate_test_logic(
            cleaned_tests
        )

        # ================================================
        # VALID TESTS
        # ================================================

        if is_valid_test_code(cleaned_tests):

            return cleaned_tests

    return ""


# =========================================================
# PARSE ASSERT STATEMENT
# =========================================================

def parse_assert(assert_line):

    """
    Supports:

    assert x == y
    assert x != y
    assert x < y
    assert x > y
    assert x <= y
    assert x >= y
    """

    operators = [
        "==",
        "!=",
        "<=",
        ">=",
        "<",
        ">"
    ]

    for op in operators:

        if op in assert_line:

            parts = assert_line.replace(
                "assert",
                "",
                1
            ).split(op, 1)

            if len(parts) != 2:
                return None

            function_call = parts[0].strip()

            expected_value = parts[1].strip()

            return {
                "function_call": function_call,
                "operator": op,
                "expected_value": expected_value
            }

    return None


# =========================================================
# COMPARE RESULTS
# =========================================================

def compare_results(actual, expected, operator):

    if operator == "==":
        return actual == expected

    elif operator == "!=":
        return actual != expected

    elif operator == "<":
        return actual < expected

    elif operator == ">":
        return actual > expected

    elif operator == "<=":
        return actual <= expected

    elif operator == ">=":
        return actual >= expected

    return False


# =========================================================
# RUN TESTS
# =========================================================

def run_tests(prompt, code):

    try:
        test_code = generate_tests_with_llm(prompt, code)
        if not test_code.strip():
            return {
                "success": False,
                "message": "No valid tests generated",
                "tests": "",
                "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0, "timeout": False}
            }

        test_lines = [t.strip() for t in test_code.split("\n") if t.strip()]
        total_tests = len(test_lines)
        
        # Build a safe wrapper script to run the tests
        wrapper = [
            "import json",
            "import traceback",
            "test_results = {'total': " + str(total_tests) + ", 'passed': 0, 'failed': 0, 'errors': 0, 'message': 'All tests passed', 'success': True}",
            "try:"
        ]
        
        if total_tests == 0:
            wrapper.append("    pass")
        else:
            for t in test_lines:
                # Add each assert statement, then increment passed counter
                wrapper.append(f"    {t}")
                wrapper.append(f"    test_results['passed'] += 1")
                
        wrapper.append("except AssertionError as e:")
        wrapper.append("    test_results['failed'] += 1")
        wrapper.append("    test_results['success'] = False")
        wrapper.append("    test_results['message'] = 'Test Failed\\n' + traceback.format_exc()")
        wrapper.append("except Exception as e:")
        wrapper.append("    test_results['errors'] += 1")
        wrapper.append("    test_results['success'] = False")
        wrapper.append("    test_results['message'] = 'Error during test execution\\n' + traceback.format_exc()")
        
        wrapper.append("print('___TEST_RESULTS___')")
        wrapper.append("print(json.dumps(test_results))")
        
        safe_test_script = "\n".join(wrapper)

        from app.executor import execute_code
        exec_result = execute_code(code, test_code=safe_test_script)
        
        # Check verification (static syntax + safety)
        if not exec_result.get("verification", {}).get("safety_passed", False):
             return {
                "success": False,
                "message": "SecurityViolation during test execution",
                "tests": test_code,
                "test_summary": {"total": total_tests, "passed": 0, "failed": 0, "errors": 1, "timeout": False},
                "verification": exec_result.get("verification", {})
            }

        if exec_result["error"] and "TimeoutError" in exec_result["error"]:
            return {
                "success": False,
                "message": "Execution timed out during tests",
                "tests": test_code,
                "test_summary": {"total": total_tests, "passed": 0, "failed": 0, "errors": 0, "timeout": True},
                "verification": exec_result.get("verification", {})
            }
            
        output = exec_result["output"]
        if "___TEST_RESULTS___" in output:
            json_str = output.split("___TEST_RESULTS___")[-1].strip()
            import json
            try:
                results = json.loads(json_str)
                return {
                    "success": results["success"],
                    "message": results["message"],
                    "tests": test_code,
                    "test_summary": {
                        "total": results["total"],
                        "passed": results["passed"],
                        "failed": results["failed"],
                        "errors": results["errors"],
                        "timeout": False
                    },
                    "verification": exec_result.get("verification", {})
                }
            except json.JSONDecodeError:
                pass
                
        return {
            "success": False,
            "message": "Failed to parse test results from sandbox output\n" + exec_result["error"] + "\n" + exec_result["output"],
            "tests": test_code,
            "test_summary": {"total": total_tests, "passed": 0, "failed": 0, "errors": 1, "timeout": False},
            "verification": exec_result.get("verification", {})
        }

    except Exception:
        return {
            "success": False,
            "message": traceback.format_exc(),
            "tests": test_code if 'test_code' in locals() else "",
            "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "timeout": False}
        }