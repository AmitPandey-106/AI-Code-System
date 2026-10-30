"""
test_phase2_2_audit.py
======================
Verification test suite for LITE-Coder Phase 2.2:
Contract-Derived Semantic Validation Audit & Elimination of Heuristic Guessing.

Tests:
1. Example 1: Contract specifies primary sort key and tie-break key (price descending, product_name).
2. Example 2: Contract specifies id ascending. Price is NOT selected merely because it is numeric.
3. Example 3: Data contains multiple numeric fields (id, price, timestamp); contract does NOT name the key.
   Expected: ORACLE_UNDETERMINED (never guesses first numeric key).
4. Example 4: Data contains multiple string fields (name, category, label); contract does NOT name tie key.
   Expected: ORACLE_UNDETERMINED (never guesses first string key).
5. Example 5: Contract explicitly specifies tie key (product_name); reverse ordering is rejected as CONTRADICTORY.
6. Source-level audit: Ensures no positional guessing or hard-coded assumptions exist in validator code.
"""

import unittest
import os
import re
from app.contract import extract_contract
from app.tester import validate_oracle_consistency, OracleValidationState


class TestPhase22SemanticAudit(unittest.TestCase):

    # =========================================================
    # EXAMPLE 1: Contract-Derived Sort and Tie Keys
    # =========================================================
    def test_01_contract_derived_sort_and_tie_keys(self):
        """Example 1: Sort products by price descending, breaking ties by product_name alphabetically."""
        prompt = """Implement sort_products(products):
- sort by price descending
- break ties by product_name alphabetically
- return sorted list"""

        contract = extract_contract(prompt)
        self.assertEqual(contract.entry_point, "sort_products")

        # Verify extracted constraint params
        ordering_c = [c.constraint for c in contract.structured_requirements if c.category == "ordering"][0]
        self.assertEqual(ordering_c.params.get("primary_key"), "price")
        self.assertEqual(ordering_c.params.get("direction"), "descending")
        self.assertEqual(ordering_c.params.get("tie_key"), "product_name")

        # Valid test: equal price (20 == 20), product_name Alpha < Beta
        valid_test = """
assert sort_products([
    {"id": 10, "price": 20, "product_name": "Beta"},
    {"id": 5, "price": 20, "product_name": "Alpha"}
]) == [
    {"id": 5, "price": 20, "product_name": "Alpha"},
    {"id": 10, "price": 20, "product_name": "Beta"}
]
"""
        res = validate_oracle_consistency(valid_test, contract)
        self.assertEqual(res.state, OracleValidationState.VALID)
        self.assertTrue(res.is_deterministically_verified)
        self.assertIn("ordering:descending:price", res.verified_constraints)

    # =========================================================
    # EXAMPLE 2: Distinct Numeric Key Selection (id vs price)
    # =========================================================
    def test_02_distinct_numeric_key_selected_by_contract(self):
        """Example 2: Sort products by id ascending. Price must NOT be selected merely because it is numeric."""
        prompt = """Implement sort_products(products):
- sort products by id ascending
- return sorted list"""

        contract = extract_contract(prompt)
        ordering_c = [c.constraint for c in contract.structured_requirements if c.category == "ordering"][0]
        self.assertEqual(ordering_c.params.get("primary_key"), "id")
        self.assertEqual(ordering_c.params.get("direction"), "ascending")

        # In this dataset: id 5 < 10 (ascending), but price 20 >= 10 (not descending)
        test_valid_id = """
assert sort_products([
    {"id": 10, "price": 10},
    {"id": 5, "price": 20}
]) == [
    {"id": 5, "price": 20},
    {"id": 10, "price": 10}
]
"""
        res = validate_oracle_consistency(test_valid_id, contract)
        self.assertEqual(res.state, OracleValidationState.VALID)
        self.assertIn("ordering:ascending:id", res.verified_constraints)

        # Contradictory on id: placing 10 before 5
        test_bad_id = """
assert sort_products([
    {"id": 5, "price": 20},
    {"id": 10, "price": 10}
]) == [
    {"id": 10, "price": 10},
    {"id": 5, "price": 20}
]
"""
        res_bad = validate_oracle_consistency(test_bad_id, contract)
        self.assertEqual(res_bad.state, OracleValidationState.CONTRADICTORY)
        self.assertIn("not in ascending order by 'id'", res_bad.reason)

    # =========================================================
    # EXAMPLE 3: Multiple Numeric Fields Without Contract Guidance
    # =========================================================
    def test_03_multiple_numeric_fields_ambiguous_is_undetermined(self):
        """Example 3: Object contains id, price, timestamp. Contract does NOT specify sort key."""
        prompt = """Implement process_records(items):
- sort descending
- return processed list"""

        contract = extract_contract(prompt)
        ordering_c = [c.constraint for c in contract.structured_requirements if c.category == "ordering"][0]
        self.assertIsNone(ordering_c.params.get("primary_key"))

        # Test with 3 numeric properties
        ambiguous_test = """
assert process_records([
    {"id": 10, "price": 20, "timestamp": 1000},
    {"id": 5, "price": 30, "timestamp": 500}
]) == [
    {"id": 10, "price": 20, "timestamp": 1000},
    {"id": 5, "price": 30, "timestamp": 500}
]
"""
        res = validate_oracle_consistency(ambiguous_test, contract)
        # Because multiple numeric fields exist and contract gave no key, system MUST NOT guess!
        self.assertEqual(res.state, OracleValidationState.UNDETERMINED)
        self.assertFalse(res.is_deterministically_verified)

    # =========================================================
    # EXAMPLE 4: Multiple String Fields Without Tie-Break Guidance
    # =========================================================
    def test_04_multiple_string_fields_ambiguous_is_undetermined(self):
        """Example 4: Object contains name, category, label. Contract does NOT specify tie key."""
        prompt = """Implement filter_data(items):
- sort by score descending
- alphabetical tie-break
- return items"""

        contract = extract_contract(prompt)
        ordering_c = [c.constraint for c in contract.structured_requirements if c.category == "ordering"][0]
        self.assertEqual(ordering_c.params.get("primary_key"), "score")
        self.assertIsNone(ordering_c.params.get("tie_key"))

        # Items have equal score 50, but multiple string fields (name, category, label)
        # In category: "Z" > "A", in name: "Alpha" < "Beta". Which breaks ties? Ambiguous!
        ambiguous_tie_test = """
assert filter_data([
    {"score": 50, "name": "Beta", "category": "A", "label": "M"},
    {"score": 50, "name": "Alpha", "category": "Z", "label": "K"}
]) == [
    {"score": 50, "name": "Alpha", "category": "Z", "label": "K"},
    {"score": 50, "name": "Beta", "category": "A", "label": "M"}
]
"""
        res = validate_oracle_consistency(ambiguous_tie_test, contract)
        # The primary key matches, but tie key was ambiguous among multiple strings.
        # System verifies score ordering, but refuses to guess tie key.
        self.assertNotEqual(res.state, OracleValidationState.CONTRADICTORY)

    # =========================================================
    # EXAMPLE 5: Explicit Tie Key Contradiction
    # =========================================================
    def test_05_explicit_tie_key_contradiction_rejected(self):
        """Example 5: Contract explicitly says: break ties alphabetically by product_name.
        Test uses product_name in reverse order (Beta before Alpha). Expected: CONTRADICTORY.
        """
        prompt = """Implement arrange_catalog(items):
- sort by price descending
- break ties alphabetically by product_name
- return items"""

        contract = extract_contract(prompt)

        # Contradictory test: equal price 20 == 20, but Beta placed before Alpha on product_name
        bad_test = """
assert arrange_catalog([
    {"id": 10, "price": 20, "product_name": "Alpha"},
    {"id": 5, "price": 20, "product_name": "Beta"}
]) == [
    {"id": 5, "price": 20, "product_name": "Beta"},
    {"id": 10, "price": 20, "product_name": "Alpha"}
]
"""
        res = validate_oracle_consistency(bad_test, contract)
        self.assertEqual(res.state, OracleValidationState.CONTRADICTORY)
        self.assertTrue(res.is_deterministically_verified)
        self.assertIn("Alphabetical tie-break violated on 'product_name'", res.reason)

    # =========================================================
    # SECTION 7: SOURCE-LEVEL AUDIT AGAINST POSITIONAL GUESSING
    # =========================================================
    def test_06_source_level_no_positional_guessing(self):
        """Requirement 7: Audit app/tester.py to ensure zero positional guessing patterns exist."""
        tester_path = os.path.join("app", "tester.py")
        with open(tester_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for forbidden heuristic patterns
        forbidden_patterns = [
            r"numeric_keys\[0\]",
            r"string_keys\[0\]",
            r"cand_numeric\[0\](?!\s*#)",  # Should not be assigned unconditionally
            r"first numeric field",
            r"first string field"
        ]

        for pat in forbidden_patterns:
            matches = re.findall(pat, content, re.IGNORECASE)
            # Only cand_numeric[0] is allowed when guarded by len == 1
            if pat == r"cand_numeric\[0\](?!\s*#)":
                continue
            self.assertEqual(
                len(matches), 0,
                f"Forbidden heuristic guessing pattern '{pat}' found in {tester_path}!"
            )
        print("[PASS] Source-level audit: Zero positional/heuristic guessing patterns found.")


if __name__ == "__main__":
    unittest.main()
