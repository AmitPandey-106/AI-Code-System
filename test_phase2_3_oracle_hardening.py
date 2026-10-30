"""
test_phase2_3_oracle_hardening.py
=================================
Regression test suite for Phase 2.3:
Test Oracle Generation + Contract Extraction Hardening.

Covers:
1. Multiline test setup with indentation.
2. Test candidate containing nested function calls.
3. Test candidate with multiple assertions.
4. Test candidate with setup variables used later.
5. Invalid indentation must produce TEST_GENERATION_FAILURE.
6. Undefined test variables must produce TEST_HARNESS_FAILURE / TEST_GENERATION_FAILURE.
7. Valid multiline tests must NOT be discarded.
8. Complete semantic extraction from boundary conditions.
9. Complete semantic extraction from invalid-input conditions.
10. Complete semantic extraction from ordering requirements.
11. Complete semantic extraction from immutability requirements.
12. No task-specific literals or heuristics in production code.
13. Exact reproduction: schedule_meetings prompt end-to-end regression.
"""

import unittest
import ast
import re
from app.contract import extract_contract, TaskContract, Requirement, StructuredConstraint
from app.tester import (
    clean_test_code,
    validate_test_variables,
    validate_oracle_consistency,
    OracleValidationState,
    OracleValidationResult,
    FailureType,
    run_tests
)


class TestPhase23OracleHardening(unittest.TestCase):

    # 1. Multiline test setup with indentation
    def test_01_multiline_test_setup_with_indentation(self):
        """Multiline setup blocks with varied indentation must be normalized safely."""
        raw_test = """
    items = [
        {"name": "Alpha", "start": 9, "end": 10},
        {"name": "Beta", "start": 10, "end": 11}
    ]
    expected = [
        {"name": "Alpha", "start": 9, "end": 10},
        {"name": "Beta", "start": 10, "end": 11}
    ]
    assert process_schedule(items) == expected
"""
        cleaned = clean_test_code(raw_test)
        self.assertTrue(bool(cleaned.strip()))
        tree = ast.parse(cleaned)
        self.assertTrue(any(isinstance(node, ast.Assert) for node in tree.body))
        self.assertTrue(any(isinstance(node, ast.Assign) for node in tree.body))

    # 2. Test candidate containing nested function calls
    def test_02_test_candidate_containing_nested_function_calls(self):
        """Nested function calls in assertions and setups must parse and be preserved."""
        raw_test = """
data = sorted([{"val": 3}, {"val": 1}], key=lambda x: x["val"])
assert compute_metrics(data) == [int(round(x["val"])) for x in data]
"""
        cleaned = clean_test_code(raw_test)
        self.assertTrue(bool(cleaned.strip()))
        tree = ast.parse(cleaned)
        self.assertTrue(any(isinstance(node, ast.Assert) for node in tree.body))

    # 3. Test candidate with multiple assertions
    def test_03_test_candidate_with_multiple_assertions(self):
        """Candidate with multiple distinct setups and assertions must preserve all of them."""
        raw_test = """
set1 = [{"title": "A", "start": 1, "end": 2}]
assert merge_blocks(set1) == [{"title": "A", "start": 1, "end": 2}]

set2 = [{"title": "B", "start": 2, "end": 4}, {"title": "C", "start": 3, "end": 5}]
assert merge_blocks(set2) == [{"title": "B + C", "start": 2, "end": 5}]

assert merge_blocks([]) == []
"""
        cleaned = clean_test_code(raw_test)
        tree = ast.parse(cleaned)
        asserts = [node for node in tree.body if isinstance(node, ast.Assert)]
        self.assertEqual(len(asserts), 3)

    # 4. Test candidate with setup variables used later
    def test_04_test_candidate_with_setup_variables_used_later(self):
        """Setup variables defined earlier must be recognized as valid and defined."""
        raw_test = """
shared_input = [{"id": 1, "score": 90}]
res = evaluate_scores(shared_input)
assert len(res) == 1
assert res[0]["score"] == 90
"""
        cleaned = clean_test_code(raw_test)
        valid, err = validate_test_variables(cleaned, allowed_names=["evaluate_scores"])
        self.assertTrue(valid, f"Variables should be valid but got: {err}")

    # 5. Invalid indentation must produce TEST_GENERATION_FAILURE
    def test_05_invalid_indentation_produces_test_generation_failure(self):
        """Malformed indentation that cannot be parsed must yield TEST_GENERATION_FAILURE."""
        broken_code = "assert calculate(1)\n    broken_indent = [1\n  2]"
        res = run_tests(
            prompt="def calculate(x): return x",
            code="def calculate(x): return x",
            authoritative_tests=[broken_code]
        )
        self.assertFalse(res["success"])
        self.assertIn(res["failure_type"], (FailureType.TEST_GENERATION_FAILURE, FailureType.TEST_HARNESS_FAILURE))

    # 6. Undefined test variables must produce TEST_GENERATION_FAILURE / TEST_HARNESS_FAILURE
    def test_06_undefined_test_variables_produces_test_generation_failure(self):
        """Test with undefined variables must fail harness validation and isolate code."""
        bad_test = "assert run_process(undefined_variable_xyz) == expected_output_abc"
        res = run_tests(
            prompt="def run_process(data): return data",
            code="def run_process(data): return data",
            authoritative_tests=[bad_test]
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["failure_type"], FailureType.TEST_HARNESS_FAILURE)

    # 7. Valid multiline tests must NOT be discarded
    def test_07_valid_multiline_tests_not_discarded(self):
        """Valid multiline tests must execute cleanly and succeed on conforming code."""
        code = "def merge_pairs(items):\n    return [{'val': items[0]['val'] + items[1]['val']}] if len(items) == 2 else items\n"
        tests = [
            "raw = [{'val': 10}, {'val': 20}]",
            "assert merge_pairs(raw) == [{'val': 30}]"
        ]
        res = run_tests(
            prompt="def merge_pairs(items): pass",
            code=code,
            authoritative_tests=tests
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["test_summary"]["passed"], 1)

    # 8. Complete semantic extraction from boundary conditions
    def test_08_complete_semantic_extraction_boundary_conditions(self):
        """Boundary touching condition must extract condition and expected behavior."""
        prompt = """
Requirements:
1. Meetings that only touch at a boundary must NOT be merged.
   For example:
       [9, 10] and [10, 11]
   must remain separate.
"""
        contract = extract_contract(prompt)
        self.assertNotIn("For example:", contract.requirements)
        self.assertNotIn("must remain separate.", contract.requirements)

        boundary_constraints = [
            s.constraint for s in contract.structured_requirements
            if s.constraint and s.constraint.category == "boundary"
        ]
        self.assertTrue(len(boundary_constraints) > 0)
        c = boundary_constraints[0]
        self.assertEqual(c.params.get("condition"), "next_start == current_end")
        self.assertEqual(c.params.get("expected_behavior"), "do_not_merge")

    # 9. Complete semantic extraction from invalid-input conditions
    def test_09_complete_semantic_extraction_invalid_input_conditions(self):
        """Invalid input requirement (e.g. end <= start) must extract condition and ignore behavior."""
        prompt = """
Requirements:
1. Intervals with end <= start are invalid and must be ignored.
"""
        contract = extract_contract(prompt)
        validation_constraints = [
            s.constraint for s in contract.structured_requirements
            if s.constraint and s.constraint.category == "validation"
        ]
        self.assertTrue(len(validation_constraints) > 0)
        c = validation_constraints[0]
        self.assertEqual(c.params.get("condition"), "end <= start")
        self.assertEqual(c.params.get("behavior"), "ignore")

    # 10. Complete semantic extraction from ordering requirements
    def test_10_complete_semantic_extraction_ordering_requirements(self):
        """Ordering tie-break and overlap conditions must be extracted with parameters."""
        prompt = """
Requirements:
1. Two meetings overlap when the next meeting's start time is strictly less than the current merged meeting's end time.
2. If multiple meetings have the same start time, preserve their original input order when determining title order.
"""
        contract = extract_contract(prompt)
        overlap_c = [
            s.constraint for s in contract.structured_requirements
            if s.constraint and s.constraint.category == "overlap"
        ]
        self.assertTrue(len(overlap_c) > 0)
        self.assertEqual(overlap_c[0].params.get("condition"), "next_start < current_end")
        self.assertEqual(overlap_c[0].params.get("behavior"), "merge")

        ordering_c = [
            s.constraint for s in contract.structured_requirements
            if s.constraint and s.constraint.category == "ordering" and s.constraint.params.get("condition") == "equal_start"
        ]
        self.assertTrue(len(ordering_c) > 0)
        self.assertEqual(ordering_c[0].params.get("ordering"), "original_input_order")
        self.assertEqual(ordering_c[0].params.get("field"), "title")

    # 11. Complete semantic extraction from immutability requirements
    def test_11_complete_semantic_extraction_immutability_requirements(self):
        """Immutability requirements must extract target and mutation_allowed=False."""
        prompt = """
Requirements:
1. The input list must not be modified.
2. The original meeting dictionaries must not be modified.
"""
        contract = extract_contract(prompt)
        immut_c = [
            s.constraint for s in contract.structured_requirements
            if s.constraint and s.constraint.category == "immutability"
        ]
        self.assertEqual(len(immut_c), 2)
        targets = [c.params.get("target") for c in immut_c]
        self.assertIn("input", targets)
        self.assertIn("original_input_objects", targets)
        for c in immut_c:
            self.assertFalse(c.params.get("mutation_allowed"))

    # 12. No task-specific literals or heuristics in production code
    def test_12_no_task_specific_literals_in_production_code(self):
        """Verify app/contract.py and app/tester.py contain zero task-specific heuristics."""
        forbidden_patterns = [
            r"\bschedule_meetings\b",
            r"\bmeeting\b",
            r"\bmeetings\b",
            r"\binterval\b",
            r"\bintervals\b",
            r"\bstudent\b",
            r"\bstudents\b",
            r"\bBob\b",
            r"\bCharlie\b"
        ]
        for rel_path in ["app/contract.py", "app/tester.py"]:
            with open(rel_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Ignore docstrings/comments and inspect code
            tree = ast.parse(content)
            # Check string constants in AST
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value
                    for pat in forbidden_patterns:
                        self.assertIsNone(
                            re.search(pat, val),
                            f"Task-specific literal matching '{pat}' found in {rel_path}: {val}"
                        )

    # 13. Exact reproduction: schedule_meetings prompt end-to-end regression
    def test_13_exact_reproduction_schedule_meetings(self):
        """Exact schedule_meetings prompt reproduction."""
        prompt = '''Implement the following Python function:

def schedule_meetings(meetings):
    """
    Merge overlapping meetings and return the resulting schedule.

    Each meeting is represented as a dictionary:
        {
            "title": str,
            "start": int,
            "end": int
        }

    Requirements:

    1. Meetings must be ordered by start time before merging.

    2. Two meetings overlap when the next meeting's start time is
       strictly less than the current merged meeting's end time.

    3. Meetings that only touch at a boundary must NOT be merged.
       For example:
           [9, 10] and [10, 11]
       must remain separate.

    4. When overlapping meetings are merged:
       - start = earliest start time
       - end = latest end time
       - title = titles of all merged meetings joined using " + "
         in their original chronological order.

    5. If multiple meetings have the same start time, preserve their
       original input order when determining title order.

    6. Meetings with end <= start are invalid and must be ignored.

    7. The input list must not be modified.

    8. The original meeting dictionaries must not be modified.

    9. The returned meetings must be newly created dictionaries.

    10. Return an empty list when the input contains no valid meetings.

    11. The returned list must be sorted by start time.

    Example:

    Input:
    [
        {"title": "A", "start": 9, "end": 11},
        {"title": "B", "start": 10, "end": 12},
        {"title": "C", "start": 12, "end": 13},
        {"title": "D", "start": 14, "end": 15}
    ]

    Output:
    [
        {"title": "A + B", "start": 9, "end": 12},
        {"title": "C", "start": 12, "end": 13},
        {"title": "D", "start": 14, "end": 15}
    ]
    """
'''
        # A. Contract Extraction Check
        contract = extract_contract(prompt)
        self.assertEqual(contract.entry_point, "schedule_meetings")
        self.assertEqual(contract.parameters, ["meetings"])
        
        # Verify no fragmented garbage requirements
        for req in contract.requirements:
            self.assertNotEqual(req.strip(), "For example:")
            self.assertNotEqual(req.strip(), "Output:")
            self.assertNotEqual(req.strip(), "must remain separate.")
            self.assertNotEqual(req.strip(), "in their original chronological order.")

        # B. Multi-line generated test case that previously caused line 19 unexpected indent
        generated_test = """
meetings = [
    {"title": "A", "start": 9, "end": 11},
    {"title": "B", "start": 10, "end": 12},
    {"title": "C", "start": 12, "end": 13},
    {"title": "D", "start": 14, "end": 15}
]
expected = [
    {"title": "A + B", "start": 9, "end": 12},
    {"title": "C", "start": 12, "end": 13},
    {"title": "D", "start": 14, "end": 15}
]
assert schedule_meetings(meetings) == expected

meetings2 = [
    {"title": "X", "start": 9, "end": 10},
    {"title": "Y", "start": 10, "end": 11}
]
assert schedule_meetings(meetings2) == meetings2
"""
        cleaned = clean_test_code(generated_test)
        # AST parse must pass without SyntaxError: unexpected indent
        ast_tree = ast.parse(cleaned)
        self.assertIsNotNone(ast_tree)

        # C. Oracle Validation Check
        val_res = validate_oracle_consistency(cleaned, contract)
        self.assertIn(val_res.state, (OracleValidationState.VALID, OracleValidationState.UNDETERMINED))

        # D. Execution against a buggy candidate must yield CODE_FAILURE (reaching repair!), not TEST_GENERATION_FAILURE
        buggy_candidate = """
def schedule_meetings(meetings):
    # Buggy candidate that returns meetings without merging
    return [dict(m) for m in meetings if m["end"] > m["start"]]
"""
        res = run_tests(prompt, buggy_candidate, authoritative_tests=[cleaned], contract=contract)
        self.assertFalse(res["success"])
        self.assertEqual(res["failure_type"], FailureType.CODE_FAILURE)
        self.assertIn("AssertionError", res["message"])

        # E. Execution against a correct candidate must succeed
        correct_candidate = """
def schedule_meetings(meetings):
    valid = [dict(m) for m in meetings if m.get("end", 0) > m.get("start", 0)]
    if not valid:
        return []
    # Sort with preservation of original order for equal starts
    indexed = list(enumerate(valid))
    indexed.sort(key=lambda x: (x[1]["start"], x[0]))
    sorted_meetings = [m for _, m in indexed]
    
    merged = []
    for curr in sorted_meetings:
        if not merged:
            merged.append(dict(curr))
        else:
            prev = merged[-1]
            if curr["start"] < prev["end"]:
                prev["end"] = max(prev["end"], curr["end"])
                prev["title"] = prev["title"] + " + " + curr["title"]
            else:
                merged.append(dict(curr))
    return merged
"""
        res_correct = run_tests(prompt, correct_candidate, authoritative_tests=[cleaned], contract=contract)
        self.assertTrue(res_correct["success"])
        self.assertEqual(res_correct["test_summary"]["failed"], 0)


if __name__ == "__main__":
    unittest.main()
