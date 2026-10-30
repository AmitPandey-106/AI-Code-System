import ast

def estimate_difficulty(error_type: str, broken_code: str, attempt_number: int, memory_available: bool) -> dict:
    score = 0.0
    reasons = []

    # 1. Error type analysis
    if error_type == "SyntaxError":
        score += 1.0
        reasons.append("Syntax errors are typically easy to fix")
    elif error_type in ["TypeError", "NameError", "AttributeError", "ValueError"]:
        score += 2.0
        reasons.append(f"Standard Python exception ({error_type})")
    elif error_type == "AssertionError":
        score += 3.0
        reasons.append("Test failures require logic changes")
    elif error_type == "TimeoutError":
        score += 4.0
        reasons.append("Infinite loops/timeouts require algorithmic changes")
    else:
        score += 2.5
        reasons.append("Unknown/General error type")

    # 2. Code complexity analysis
    lines = len(broken_code.strip().split("\n"))
    if lines > 30:
        score += 2.0
        reasons.append(f"Long code block ({lines} lines)")
    elif lines > 15:
        score += 1.0
        reasons.append(f"Medium code block ({lines} lines)")
        
    try:
        tree = ast.parse(broken_code)
        num_funcs = sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
        num_classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
        if num_classes > 0:
            score += 1.0
            reasons.append("Object-oriented structure")
        if num_funcs > 1:
            score += 1.0
            reasons.append("Multiple functions involved")
    except Exception:
        pass

    # 3. Trajectory difficulty
    if attempt_number > 1:
        score += (attempt_number - 1) * 1.5
        reasons.append(f"Repeated failures (attempt {attempt_number})")
        
    if not memory_available:
        score += 0.5
        reasons.append("No verified experiences available")

    # Final Classification
    if score <= 3.0:
        level = "EASY"
        budget = 2
    elif score <= 5.5:
        level = "MEDIUM"
        budget = 3
    elif score <= 8.0:
        level = "HARD"
        budget = 4
    else:
        level = "VERY_HARD"
        budget = 5
        
    return {
        "difficulty": level,
        "score": round(score, 2),
        "reasons": reasons,
        "recommended_attempts": budget
    }
