STRATEGIES = {
    "DIRECT_REPAIR": {
        "id": "DIRECT_REPAIR",
        "description": "Attempt a direct correction using the detected error.",
        "prompt": "Repair the detected error directly. Preserve the existing implementation wherever possible.",
        "applicable_errors": ["SyntaxError", "NameError", "AttributeError", "IndentationError"]
    },
    "EXPERIENCE_GUIDED_REPAIR": {
        "id": "EXPERIENCE_GUIDED_REPAIR",
        "description": "Retrieve similar verified repairs and use them as guidance.",
        "prompt": "Use the verified previous repair experiences as guidance. Do not copy blindly. Apply the pattern to the current problem.",
        "applicable_errors": ["TypeError", "ValueError", "KeyError", "IndexError", "AssertionError"]
    },
    "TEST_GUIDED_REPAIR": {
        "id": "TEST_GUIDED_REPAIR",
        "description": "Use generated/available tests and failure information to guide the repair.",
        "prompt": "Use the observed test failures to identify the behavioral defect before modifying the code. Focus on edge cases.",
        "applicable_errors": ["AssertionError", "RuntimeError"]
    },
    "MINIMAL_PATCH": {
        "id": "MINIMAL_PATCH",
        "description": "Prefer the smallest possible modification to the broken code.",
        "prompt": "Make the smallest change necessary to correct the failure. Do not rewrite the entire logic.",
        "applicable_errors": ["SyntaxError", "IndexError", "KeyError"]
    },
    "STRUCTURAL_REPAIR": {
        "id": "STRUCTURAL_REPAIR",
        "description": "Reason about the affected function/class/module structure before producing the repair.",
        "prompt": "Analyze the affected function/class structure before producing the corrected implementation. Ensure robust design.",
        "applicable_errors": ["NameError", "TypeError", "AttributeError", "TimeoutError"]
    },
    "ALTERNATIVE_REPAIR": {
        "id": "ALTERNATIVE_REPAIR",
        "description": "If previous repair attempts failed, deliberately generate an alternative solution.",
        "prompt": "Previous repair strategies failed. Produce a materially different repair approach. Rethink the algorithm completely.",
        "applicable_errors": ["TimeoutError", "AssertionError"]
    }
}

# Baseline Mapping (Rule-Based Fallback)
BASELINE_MAPPING = {
    "SyntaxError": ["DIRECT_REPAIR", "MINIMAL_PATCH"],
    "TypeError": ["EXPERIENCE_GUIDED_REPAIR", "STRUCTURAL_REPAIR"],
    "ValueError": ["EXPERIENCE_GUIDED_REPAIR", "TEST_GUIDED_REPAIR"],
    "NameError": ["DIRECT_REPAIR", "STRUCTURAL_REPAIR"],
    "AttributeError": ["DIRECT_REPAIR", "STRUCTURAL_REPAIR"],
    "IndexError": ["MINIMAL_PATCH", "EXPERIENCE_GUIDED_REPAIR"],
    "KeyError": ["MINIMAL_PATCH", "EXPERIENCE_GUIDED_REPAIR"],
    "AssertionError": ["TEST_GUIDED_REPAIR", "EXPERIENCE_GUIDED_REPAIR", "ALTERNATIVE_REPAIR"],
    "TimeoutError": ["ALTERNATIVE_REPAIR", "STRUCTURAL_REPAIR"],
    "SecurityViolation": ["MINIMAL_PATCH", "DIRECT_REPAIR"]
}

def get_baseline_strategies(error_type: str) -> list:
    return BASELINE_MAPPING.get(error_type, ["DIRECT_REPAIR", "TEST_GUIDED_REPAIR"])

def get_strategy_prompt(strategy_id: str) -> str:
    return STRATEGIES.get(strategy_id, STRATEGIES["DIRECT_REPAIR"])["prompt"]
