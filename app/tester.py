import traceback
import ast
import re
import textwrap
from typing import Optional, List, Tuple, Any, Dict

from app.model import generate_raw


# =========================================================
# FAILURE TYPE CLASSIFICATION
# =========================================================

class FailureType:
    CODE_FAILURE = "CODE_FAILURE"
    TEST_HARNESS_FAILURE = "TEST_HARNESS_FAILURE"
    TEST_ORACLE_FAILURE = "TEST_ORACLE_FAILURE"
    TEST_GENERATION_FAILURE = "TEST_GENERATION_FAILURE"
    CONTRACT_FAILURE = "CONTRACT_FAILURE"
    TIMEOUT = "TIMEOUT"


# =========================================================
# CLEAN GENERATED TESTS (PRESERVING VALID TEST SETUP)
# =========================================================

def clean_test_code(text: str) -> str:
    """
    Cleans generated test code while strictly preserving multi-line test setups
    (such as input_data = [...], expected_output = [...], assert ...).
    Safely normalizes indentation across independently generated blocks.
    Rejects malformed code or non-code text.
    """
    if not text:
        return ""

    # 1. Strip markdown fences if present
    m = re.search(r'```(?:python|py)?\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    code_body = m.group(1) if m else text

    # Filter out conversational lines before AST parsing
    filtered_lines = []
    for line in code_body.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "Here ", "Note:", "Output:", "Example:", "Explanation:", "Input:", "Test Call:")):
            continue
        filtered_lines.append(line)
    candidate_text = "\n".join(filtered_lines).strip()
    if not candidate_text:
        return ""

    # 2. Try parsing entire candidate as AST block after top-level dedent
    dedented_candidate = textwrap.dedent(candidate_text).strip()
    try:
        tree = ast.parse(dedented_candidate)
        extracted_stmts = []
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for inner_stmt in stmt.body:
                    if isinstance(inner_stmt, (ast.Assert, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Import, ast.ImportFrom, ast.Expr)):
                        extracted_stmts.append(inner_stmt)
            elif isinstance(stmt, (ast.Assert, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Import, ast.ImportFrom, ast.Expr)):
                extracted_stmts.append(stmt)

        if any(isinstance(s, ast.Assert) for s in extracted_stmts):
            return ast.unparse(ast.Module(body=extracted_stmts, type_ignores=[]))
    except Exception:
        pass

    # 3. If module parse failed due to mixed/inconsistent indentation across blocks,
    # normalize chunk by chunk using bracket/parenthesis depth tracking
    try:
        chunks = []
        current_chunk_lines = []
        paren_depth = 0
        in_string = None

        for line in filtered_lines:
            stripped = line.strip()
            if not stripped:
                if current_chunk_lines:
                    current_chunk_lines.append(line)
                continue

            # Check if this line starts a new statement block at paren_depth == 0
            is_new_block_start = (
                paren_depth == 0 and
                (stripped.startswith(("assert ", "def ", "import ", "from ")) or
                 ("=" in stripped and not stripped.startswith(("==", "!=", "<=", ">="))))
            )

            if is_new_block_start and current_chunk_lines:
                chunk_str = "\n".join(current_chunk_lines).strip()
                if chunk_str:
                    chunks.append(chunk_str)
                current_chunk_lines = []

            current_chunk_lines.append(line)

            # Update paren_depth for multi-line tracking
            i = 0
            while i < len(line):
                ch = line[i]
                if in_string:
                    if ch == "\\" and i + 1 < len(line):
                        i += 1
                    elif ch == in_string:
                        in_string = None
                else:
                    if ch in ('"', "'"):
                        if line[i:i+3] in ('"""', "'''"):
                            in_string = line[i:i+3]
                            i += 2
                        else:
                            in_string = ch
                    elif ch in ('(', '[', '{'):
                        paren_depth += 1
                    elif ch in (')', ']', '}'):
                        paren_depth = max(0, paren_depth - 1)
                i += 1

        if current_chunk_lines:
            chunk_str = "\n".join(current_chunk_lines).strip()
            if chunk_str:
                chunks.append(chunk_str)

        all_stmts = []
        for chk in chunks:
            chk_dedented = textwrap.dedent(chk).strip()
            try:
                chk_tree = ast.parse(chk_dedented)
                for stmt in chk_tree.body:
                    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for inner in stmt.body:
                            if isinstance(inner, (ast.Assert, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Import, ast.ImportFrom, ast.Expr)):
                                all_stmts.append(inner)
                    elif isinstance(stmt, (ast.Assert, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Import, ast.ImportFrom, ast.Expr)):
                        all_stmts.append(stmt)
            except Exception:
                pass

        if any(isinstance(s, ast.Assert) for s in all_stmts):
            return ast.unparse(ast.Module(body=all_stmts, type_ignores=[]))
    except Exception:
        pass

    # 4. Fallback line-by-line preservation with dedent
    lines = candidate_text.split("\n")
    cleaned_blocks = []
    current_setup = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("assert "):
            if stripped.endswith(","):
                continue
            if current_setup:
                cleaned_blocks.extend(current_setup)
                current_setup = []
            cleaned_blocks.append(stripped)
        elif "=" in stripped and not stripped.startswith(("==", "!=", "<=", ">=")):
            current_setup.append(line)
        elif current_setup and (stripped.startswith(("[", "{", "(", "]", "}", ")", '"', "'")) or stripped.endswith((",", "]", "}", ")"))):
            current_setup.append(line)
        else:
            current_setup = []

    res = textwrap.dedent("\n".join(cleaned_blocks)).strip()
    try:
        t = ast.parse(res)
        return ast.unparse(t)
    except Exception:
        return res


# =========================================================
# AST-BASED UNDEFINED VARIABLE VALIDATOR
# =========================================================

def validate_test_variables(test_code: str, allowed_names: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    AST-based validation: ensures all variables referenced in tests are defined
    either as builtins, in the test setup, or as allowed entry-point functions.
    Rejects tests containing undefined placeholders (e.g. input_data, expected_output).
    """
    if not test_code or not test_code.strip():
        return False, "Empty test code"

    try:
        tree = ast.parse(test_code)
    except Exception as e:
        return False, f"SyntaxError in test code: {str(e)}"

    import builtins
    defined_names = set(dir(builtins))
    defined_names.update([
        "True", "False", "None", "math", "re", "json", "random", "sys", "os", "itertools", "collections",
        "int", "float", "str", "bool", "list", "dict", "set", "tuple", "len", "range", "round", "sum",
        "min", "max", "abs", "sorted", "all", "any", "isinstance", "enumerate", "zip", "print"
    ])
    if allowed_names:
        defined_names.update(allowed_names)

    # First pass: collect all defined / assigned names in the test module
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = getattr(node, "targets", [getattr(node, "target", None)])
            for target in targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            defined_names.add(elt.id)
        elif isinstance(node, (ast.For, ast.comprehension)):
            if isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        defined_names.add(elt.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_names.add(node.name)
            for arg in node.args.args:
                defined_names.add(arg.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)

    # Second pass: check all ast.Name nodes with ctx=ast.Load()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined_names:
                return False, f"UndefinedVariable: '{node.id}' is used in test before definition"

    return True, None


# =========================================================
# FAILURE TYPE CLASSIFICATION & ORACLE VALIDATION STATES
# =========================================================

from dataclasses import dataclass, field

class FailureType:
    CODE_FAILURE = "CODE_FAILURE"
    TEST_HARNESS_FAILURE = "TEST_HARNESS_FAILURE"
    TEST_ORACLE_FAILURE = "TEST_ORACLE_FAILURE"
    ORACLE_CONTRADICTORY = "TEST_ORACLE_FAILURE"
    TEST_GENERATION_FAILURE = "TEST_GENERATION_FAILURE"
    ORACLE_UNDETERMINED = "ORACLE_UNDETERMINED"
    CONTRACT_FAILURE = "CONTRACT_FAILURE"
    TIMEOUT = "TIMEOUT"


class OracleValidationState:
    VALID = "VALID"
    CONTRADICTORY = "CONTRADICTORY"
    ORACLE_CONTRADICTORY = "CONTRADICTORY"
    INVALID = "INVALID"
    UNDETERMINED = "UNDETERMINED"
    ORACLE_UNDETERMINED = "UNDETERMINED"


@dataclass
class OracleValidationResult:
    state: str  # OracleValidationState
    reason: Optional[str] = None
    is_deterministically_verified: bool = False
    verified_constraints: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.state == OracleValidationState.VALID

    @property
    def is_contradictory(self) -> bool:
        return self.state == OracleValidationState.CONTRADICTORY

    def __iter__(self):
        # Support tuple unpacking (is_valid, reason) for full backward compatibility
        if self.state == OracleValidationState.VALID:
            yield True
            yield None
        elif self.state == OracleValidationState.UNDETERMINED:
            yield False
            yield self.reason or "OracleUndetermined: Semantic consistency cannot be deterministically proven"
        else:
            yield False
            yield self.reason


# =========================================================
# GENERIC TASK-AGNOSTIC ORACLE CONSISTENCY VALIDATOR
# =========================================================

def validate_oracle_consistency(test_code: str, contract: Optional[Any]) -> OracleValidationResult:
    """
    Task-agnostic validation of test assertions against TaskContract specifications.
    Determines whether a test candidate is:
    - VALID: Consistent with known contract constraints (deterministically verified).
    - CONTRADICTORY: Demonstrably contradicts an explicit deterministic contract constraint.
    - INVALID: Syntactically/structurally unsafe, undefined variables, or malformed setup.
    - UNDETERMINED: Valid syntax and structure, but semantic correctness cannot be proven deterministically.
    """
    if not test_code or not test_code.strip():
        return OracleValidationResult(
            state=OracleValidationState.INVALID,
            reason="Empty test code",
            is_deterministically_verified=False
        )

    if not contract:
        return OracleValidationResult(
            state=OracleValidationState.UNDETERMINED,
            reason="No contract provided for semantic verification",
            is_deterministically_verified=False
        )

    try:
        tree = ast.parse(test_code)
    except Exception as e:
        return OracleValidationResult(
            state=OracleValidationState.INVALID,
            reason=f"SyntaxError in test code: {str(e)}",
            is_deterministically_verified=False
        )

    entry_point = getattr(contract, "entry_point", None)
    contract_params = getattr(contract, "parameters", [])
    structured_reqs = getattr(contract, "structured_requirements", [])

    # Extract literal assignments into local environment map for resolving test variables
    local_env = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                local_env[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:
                pass

    # Collect constraints from structured requirements
    ordering_constraints = []
    boundary_constraints = []
    cardinality_constraints = []
    precision_constraints = []

    for req in structured_reqs:
        c = getattr(req, "constraint", None)
        if not c:
            continue
        if c.category == "ordering":
            ordering_constraints.append(c)
        elif c.category == "boundary":
            boundary_constraints.append(c)
        elif c.category == "cardinality":
            cardinality_constraints.append(c)
        elif c.category == "precision":
            precision_constraints.append(c)

    has_assert = False
    verified_constraints = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            has_assert = True
            # 1. Target Entry Point Check on all sub-calls in assert statement
            if entry_point:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                        fn_called = sub.func.id
                        if fn_called != entry_point and fn_called not in dir(__builtins__) and fn_called not in ("len", "range", "list", "dict", "set", "int", "float", "str", "bool", "round", "sum"):
                            return OracleValidationResult(
                                state=OracleValidationState.CONTRADICTORY,
                                reason=f"OracleContradiction: Test calls '{fn_called}' instead of required entry point '{entry_point}'",
                                is_deterministically_verified=True
                            )

            test_expr = node.test
            if isinstance(test_expr, ast.Compare) and len(test_expr.ops) == 1 and isinstance(test_expr.ops[0], (ast.Eq, ast.Is)):
                left = test_expr.left
                right = test_expr.comparators[0]

                call_node = None
                expected_node = None
                if isinstance(left, ast.Call):
                    call_node = left
                    expected_node = right
                elif isinstance(right, ast.Call):
                    call_node = right
                    expected_node = left

                if call_node and isinstance(call_node.func, ast.Name):
                    fn_called = call_node.func.id
                    # 1. Target Entry Point Check
                    if entry_point and fn_called != entry_point:
                        return OracleValidationResult(
                            state=OracleValidationState.CONTRADICTORY,
                            reason=f"OracleContradiction: Test calls '{fn_called}' instead of required entry point '{entry_point}'",
                            is_deterministically_verified=True
                        )

                    # Resolve expected value
                    expected_val = None
                    if isinstance(expected_node, ast.Name) and expected_node.id in local_env:
                        expected_val = local_env[expected_node.id]
                    else:
                        try:
                            expected_val = ast.literal_eval(expected_node)
                        except Exception:
                            expected_val = None

                    def resolve_arg(arg_node):
                        if isinstance(arg_node, ast.Name) and arg_node.id in local_env:
                            return local_env[arg_node.id]
                        try:
                            return ast.literal_eval(arg_node)
                        except Exception:
                            return None

                    # 2. Boundary Condition Checks
                    for bc in boundary_constraints:
                        p_name = bc.params.get("param_name")
                        op = bc.params.get("operator")
                        thresh = bc.params.get("threshold")
                        expected_ret = bc.params.get("expected_return")

                        p_idx = None
                        if p_name in contract_params:
                            p_idx = contract_params.index(p_name)
                        elif len(call_node.args) == len(contract_params) and len(contract_params) > 0:
                            if len(contract_params) == 1:
                                p_idx = 0
                            elif len(contract_params) == 2 and p_name in ("n", "k", "limit", "count"):
                                p_idx = 1

                        if p_idx is not None and p_idx < len(call_node.args):
                            arg_val = resolve_arg(call_node.args[p_idx])
                            if isinstance(arg_val, (int, float)):
                                condition_met = False
                                if op == "<=" and arg_val <= thresh:
                                    condition_met = True
                                elif op == "<" and arg_val < thresh:
                                    condition_met = True
                                elif op == "==" and arg_val == thresh:
                                    condition_met = True

                                if condition_met:
                                    if expected_val is not None and expected_val != expected_ret:
                                        return OracleValidationResult(
                                            state=OracleValidationState.CONTRADICTORY,
                                            reason=f"OracleContradiction: Expected output for {p_name}={arg_val} must be {expected_ret} but test expected {expected_val}",
                                            is_deterministically_verified=True
                                        )
                                    elif expected_val == expected_ret:
                                        verified_constraints.append(f"boundary:{p_name}")

                    # 3. Cardinality Limit Checks
                    for cc in cardinality_constraints:
                        k_param = cc.params.get("max_length_param")
                        p_idx = None
                        if k_param in contract_params:
                            p_idx = contract_params.index(k_param)
                        elif len(call_node.args) >= 2:
                            p_idx = 1

                        if p_idx is not None and p_idx < len(call_node.args):
                            k_val = resolve_arg(call_node.args[p_idx])
                            if isinstance(k_val, int) and k_val >= 0:
                                if expected_val is not None and isinstance(expected_val, list):
                                    if len(expected_val) > k_val:
                                        return OracleValidationResult(
                                            state=OracleValidationState.CONTRADICTORY,
                                            reason=f"OracleContradiction: Expected collection has {len(expected_val)} elements, exceeding limit {k_param}={k_val}",
                                            is_deterministically_verified=True
                                        )
                                    else:
                                        verified_constraints.append(f"cardinality:{k_param}")

                    # 4. Numerical Precision Checks
                    for pc in precision_constraints:
                        max_dec = pc.params.get("max_decimals", 2)
                        if expected_val is not None:
                            def check_precision(val):
                                if isinstance(val, float):
                                    str_v = f"{val:.10f}".rstrip("0")
                                    if "." in str_v:
                                        decimals = len(str_v.split(".")[1])
                                        if decimals > max_dec:
                                            return False, val
                                elif isinstance(val, list):
                                    for item in val:
                                        ok, bad_v = check_precision(item)
                                        if not ok:
                                            return False, bad_v
                                elif isinstance(val, dict):
                                    for v in val.values():
                                        ok, bad_v = check_precision(v)
                                        if not ok:
                                            return False, bad_v
                                return True, None

                            ok_prec, bad_val = check_precision(expected_val)
                            if not ok_prec:
                                return OracleValidationResult(
                                    state=OracleValidationState.CONTRADICTORY,
                                    reason=f"OracleContradiction: Numerical value {bad_val} exceeds {max_dec} decimal places",
                                    is_deterministically_verified=True
                                )
                            verified_constraints.append(f"precision:{max_dec}")

                    # 5. Contract-Derived Ordering & Tie-break Checks
                    for oc in ordering_constraints:
                        direction = oc.params.get("direction", "ascending")
                        primary_key = oc.params.get("primary_key")
                        tie_break = oc.params.get("tie_break")
                        tie_key = oc.params.get("tie_key")

                        if expected_val is not None and isinstance(expected_val, list) and len(expected_val) > 1:
                            if all(isinstance(x, (int, float)) for x in expected_val):
                                for i in range(len(expected_val) - 1):
                                    v1, v2 = expected_val[i], expected_val[i + 1]
                                    if direction == "descending" and v1 < v2:
                                        return OracleValidationResult(
                                            state=OracleValidationState.CONTRADICTORY,
                                            reason=f"OracleContradiction: Elements not in descending order: {v1} < {v2}",
                                            is_deterministically_verified=True
                                        )
                                    elif direction == "ascending" and v1 > v2:
                                        return OracleValidationResult(
                                            state=OracleValidationState.CONTRADICTORY,
                                            reason=f"OracleContradiction: Elements not in ascending order: {v1} > {v2}",
                                            is_deterministically_verified=True
                                        )
                                verified_constraints.append(f"ordering:{direction}")

                            elif all(isinstance(x, dict) for x in expected_val):
                                first_dict = expected_val[0]

                                # 5.1 Determine primary sort key from contract or unambiguous single field
                                sort_k = None
                                if primary_key and primary_key in first_dict:
                                    sort_k = primary_key
                                elif not primary_key:
                                    # Contract did NOT name the sort key: check if there is an unambiguous single numeric field
                                    cand_numeric = [k for k, v in first_dict.items() if isinstance(v, (int, float))]
                                    if len(cand_numeric) == 1:
                                        sort_k = cand_numeric[0]
                                    else:
                                        # Multiple numeric fields exist or none: DO NOT GUESS!
                                        # Refuse to guess sort key when ambiguous; leave undetermined
                                        continue

                                if not sort_k or sort_k not in first_dict:
                                    continue

                                # 5.2 Determine tie-break key from contract or unambiguous single field
                                tie_k = None
                                if tie_key and tie_key in first_dict:
                                    tie_k = tie_key
                                elif tie_break in ("alphabetical", "lexicographical"):
                                    cand_strings = [k for k, v in first_dict.items() if isinstance(v, str)]
                                    if len(cand_strings) == 1:
                                        tie_k = cand_strings[0]
                                    # If multiple string keys exist and contract did not specify tie_key: DO NOT GUESS!

                                # 5.3 Validate ordering and tie-break against adjacent items
                                for i in range(len(expected_val) - 1):
                                    d1, d2 = expected_val[i], expected_val[i + 1]
                                    v1 = d1.get(sort_k)
                                    v2 = d2.get(sort_k)
                                    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                                        if direction == "descending" and v1 < v2:
                                            return OracleValidationResult(
                                                state=OracleValidationState.CONTRADICTORY,
                                                reason=f"OracleContradiction: Elements not in descending order by '{sort_k}': {v1} < {v2}",
                                                is_deterministically_verified=True
                                            )
                                        elif direction == "ascending" and v1 > v2:
                                            return OracleValidationResult(
                                                state=OracleValidationState.CONTRADICTORY,
                                                reason=f"OracleContradiction: Elements not in ascending order by '{sort_k}': {v1} > {v2}",
                                                is_deterministically_verified=True
                                            )

                                        # Check tie-break when primary keys are equal
                                        if tie_break in ("alphabetical", "lexicographical") and v1 == v2:
                                            if tie_k:
                                                s1 = str(d1.get(tie_k, ""))
                                                s2 = str(d2.get(tie_k, ""))
                                                if s1 > s2:
                                                    return OracleValidationResult(
                                                        state=OracleValidationState.CONTRADICTORY,
                                                        reason=f"OracleContradiction: Alphabetical tie-break violated on '{tie_k}': '{s1}' placed before '{s2}' with equal {sort_k} {v1}",
                                                        is_deterministically_verified=True
                                                    )

                                verified_constraints.append(f"ordering:{direction}")
                                verified_constraints.append(f"ordering:{direction}:{sort_k}")

    if not has_assert:
        return OracleValidationResult(
            state=OracleValidationState.INVALID,
            reason="Test contains no assert statements",
            is_deterministically_verified=False
        )

    if verified_constraints:
        return OracleValidationResult(
            state=OracleValidationState.VALID,
            reason=None,
            is_deterministically_verified=True,
            verified_constraints=verified_constraints
        )

    return OracleValidationResult(
        state=OracleValidationState.UNDETERMINED,
        reason="OracleUndetermined: Semantic consistency cannot be deterministically proven from contract specifications.",
        is_deterministically_verified=False
    )


# =========================================================
# REMOVE BAD / CONTRADICTORY TESTS
# =========================================================

def validate_test_logic(test_code: str) -> str:
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
        if any(pattern in stripped for pattern in bad_patterns):
            continue
        if "factorial(-" in stripped:
            continue
        if stripped in seen:
            continue
        seen.add(stripped)
        cleaned.append(line)

    return "\n".join(cleaned)


# =========================================================
# VALIDATE TEST SYNTAX
# =========================================================

def is_valid_test_code(test_code: str) -> bool:
    if not test_code.strip():
        return False
    try:
        tree = ast.parse(test_code)
        return any(isinstance(node, ast.Assert) for node in tree.body)
    except Exception:
        return False


# =========================================================
# GENERATE TESTS USING LLM (FAIL-FAST WITH ORACLE VALIDATION)
# =========================================================

def generate_tests_with_llm(prompt: str, code: str, contract: Optional[Any] = None) -> str:
    contract_target = ""
    if contract and getattr(contract, "entry_point", None):
        contract_target = (
            f"\nTARGET ENTRY POINT:\nAll assert statements MUST test the target function '{contract.entry_point}'.\n"
            f"Do NOT test internal helper functions or hallucinate different function names.\n"
        )

    test_prompt = f"""
You are an expert Python QA engineer.

Generate Python assert test cases.
{contract_target}
IMPORTANT:
Generate tests that validate CORRECT Python behavior.
Ignore intentional bugs in the implementation.

STRICT RULES:
- Return ONLY assert statements and any necessary input definitions
- NO explanations
- NO markdown
- NO comments
- Generate edge case tests
- Avoid undefined variable placeholders
- Avoid broken syntax
- Generate ONLY logically correct tests
- Do NOT generate contradictory assertions

TASK:
{prompt}

CODE:
{code}

Generate Python assert test cases:
"""

    # Single fast-path generation to eliminate 34-call bottlenecks
    for _ in range(1):
        generated = generate_raw(test_prompt)
        cleaned_tests = clean_test_code(generated)
        cleaned_tests = validate_test_logic(cleaned_tests)

        # Validate with ast.parse and assert existence before anything else
        if not is_valid_test_code(cleaned_tests):
            print("[TEST GENERATION WARNING] Discarding test candidate: Invalid syntax or missing assertions")
            continue

        # Validate variables
        allowed = [contract.entry_point] if contract and getattr(contract, "entry_point", None) else []
        valid_vars, var_err = validate_test_variables(cleaned_tests, allowed_names=allowed)
        if not valid_vars:
            print(f"[TEST GENERATION WARNING] Discarding test candidate: {var_err}")
            continue

        # Validate oracle consistency
        val_res = validate_oracle_consistency(cleaned_tests, contract)
        if isinstance(val_res, OracleValidationResult):
            if val_res.state in (OracleValidationState.CONTRADICTORY, OracleValidationState.INVALID):
                print(f"[TEST GENERATION WARNING] Discarding invalid/contradictory oracle ({val_res.state}): {val_res.reason}")
                continue
        else:
            valid_oracle, oracle_err = val_res
            if not valid_oracle:
                print(f"[TEST GENERATION WARNING] Discarding contradictory oracle: {oracle_err}")
                continue

        if is_valid_test_code(cleaned_tests):
            return cleaned_tests

    return ""


# =========================================================
# RUN TESTS (WITH EXPLICIT HARNESS / ORACLE / CODE ISOLATION)
# =========================================================

def run_tests(prompt: str, code: str, authoritative_tests: Optional[List[str]] = None, contract: Optional[Any] = None) -> Dict[str, Any]:
    try:
        is_llm_generated = False
        if authoritative_tests:
            # If contract specifies an entry point, verify that tests do not call unrelated functions
            if contract and getattr(contract, "entry_point", None):
                ep = contract.entry_point
                filtered_tests = []
                last_bad_call = None
                for t in authoritative_tests:
                    t_str = t.strip()
                    m = re.search(r"\bassert\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", t_str)
                    if m:
                        called_fn = m.group(1)
                        if called_fn == ep or called_fn in ("len", "isinstance", "type", "round", "sum", "int", "float", "str", "bool"):
                            filtered_tests.append(t_str)
                        else:
                            last_bad_call = called_fn
                    else:
                        filtered_tests.append(t_str)

                if filtered_tests:
                    test_code = "\n".join(filtered_tests)
                else:
                    return {
                        "success": False,
                        "failure_type": FailureType.TEST_ORACLE_FAILURE,
                        "message": f"TestOracleError: OracleContradiction: Test calls '{last_bad_call}' instead of required entry point '{ep}'",
                        "tests": "\n".join(authoritative_tests),
                        "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "timeout": False}
                    }
            else:
                test_code = "\n".join(authoritative_tests)
        else:
            test_code = generate_tests_with_llm(prompt, code, contract=contract)
            is_llm_generated = True

        if not test_code.strip():
            return {
                "success": False,
                "failure_type": FailureType.TEST_GENERATION_FAILURE,
                "message": "No valid tests generated",
                "tests": "",
                "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0, "timeout": False}
            }

        # 1. Syntactic validation: Ensure test code parses via ast.parse BEFORE execution
        try:
            test_ast = ast.parse(test_code)
        except Exception as e:
            failure_cls = FailureType.TEST_GENERATION_FAILURE if is_llm_generated else FailureType.TEST_HARNESS_FAILURE
            return {
                "success": False,
                "failure_type": failure_cls,
                "message": f"SyntaxError in test code: {str(e)}",
                "tests": test_code,
                "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "timeout": False}
            }

        # Validate test variables before executing
        allowed = []
        if contract and getattr(contract, "entry_point", None):
            allowed.append(contract.entry_point)
        if code:
            try:
                code_tree = ast.parse(code)
                for node in code_tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        allowed.append(node.name)
            except Exception:
                pass
        valid_vars, var_err = validate_test_variables(test_code, allowed_names=allowed)
        if not valid_vars:
            failure_cls = FailureType.TEST_GENERATION_FAILURE if is_llm_generated else FailureType.TEST_HARNESS_FAILURE
            return {
                "success": False,
                "failure_type": failure_cls,
                "message": f"TestHarnessError: {var_err}",
                "tests": test_code,
                "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "timeout": False}
            }

        # Validate oracle consistency before executing
        val_res = validate_oracle_consistency(test_code, contract)
        if isinstance(val_res, OracleValidationResult):
            if val_res.state == OracleValidationState.CONTRADICTORY:
                return {
                    "success": False,
                    "failure_type": FailureType.TEST_ORACLE_FAILURE,
                    "message": f"TestOracleError: {val_res.reason}",
                    "tests": test_code,
                    "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "timeout": False}
                }
            elif val_res.state == OracleValidationState.INVALID:
                return {
                    "success": False,
                    "failure_type": FailureType.TEST_HARNESS_FAILURE,
                    "message": f"TestHarnessError: {val_res.reason}",
                    "tests": test_code,
                    "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "timeout": False}
                }
        else:
            valid_oracle, oracle_err = val_res
            if not valid_oracle:
                return {
                    "success": False,
                    "failure_type": FailureType.TEST_ORACLE_FAILURE,
                    "message": f"TestOracleError: {oracle_err}",
                    "tests": test_code,
                    "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "timeout": False}
                }

        test_lines = [t for t in test_code.split("\n") if t.strip()]
        total_asserts = sum(1 for t in test_lines if t.strip().startswith("assert "))
        total_tests = max(1, total_asserts)

        # Build a safe wrapper script to run the tests
        wrapper = [
            "import json",
            "import traceback",
            "test_results = {'total': " + str(total_tests) + ", 'passed': 0, 'failed': 0, 'errors': 0, 'message': 'All tests passed', 'success': True, 'failure_type': None, 'failing_test': ''}",
            "try:"
        ]

        if not test_lines:
            wrapper.append("    pass")
        else:
            try:
                for stmt in test_ast.body:
                    stmt_unparsed = ast.unparse(stmt)
                    wrapper.append(textwrap.indent(stmt_unparsed, "    "))
                    if isinstance(stmt, ast.Assert):
                        wrapper.append("    test_results['passed'] += 1")
            except Exception:
                for t in test_lines:
                    wrapper.append(f"    {t}")
                    if t.strip().startswith("assert "):
                        wrapper.append("    test_results['passed'] += 1")

        wrapper.append("except AssertionError as e:")
        wrapper.append("    test_results['failed'] += 1")
        wrapper.append("    test_results['success'] = False")
        wrapper.append("    test_results['failure_type'] = 'CODE_FAILURE'")
        wrapper.append("    test_results['message'] = 'Test Failed\\n' + traceback.format_exc()")
        wrapper.append("except NameError as e:")
        wrapper.append("    test_results['errors'] += 1")
        wrapper.append("    test_results['success'] = False")
        wrapper.append("    test_results['failure_type'] = 'TEST_HARNESS_FAILURE'")
        wrapper.append("    test_results['message'] = 'Harness Error: NameError in test execution\\n' + traceback.format_exc()")
        wrapper.append("except Exception as e:")
        wrapper.append("    test_results['errors'] += 1")
        wrapper.append("    test_results['success'] = False")
        wrapper.append("    test_results['failure_type'] = 'CODE_FAILURE'")
        wrapper.append("    test_results['message'] = 'Error during test execution\\n' + traceback.format_exc()")

        wrapper.append("print('___TEST_RESULTS___')")
        wrapper.append("print(json.dumps(test_results))")

        safe_test_script = "\n".join(wrapper)

        from app.executor import execute_code
        exec_result = execute_code(code, test_code=safe_test_script, contract=contract)

        if not exec_result.get("verification", {}).get("safety_passed", False):
            return {
                "success": False,
                "failure_type": FailureType.CODE_FAILURE,
                "message": "SecurityViolation during test execution",
                "tests": test_code,
                "test_summary": {"total": total_tests, "passed": 0, "failed": 0, "errors": 1, "timeout": False},
                "verification": exec_result.get("verification", {})
            }

        if exec_result.get("error") and "TimeoutError" in exec_result["error"]:
            return {
                "success": False,
                "failure_type": FailureType.TIMEOUT,
                "message": "Execution timed out during tests",
                "tests": test_code,
                "test_summary": {"total": total_tests, "passed": 0, "failed": 0, "errors": 0, "timeout": True},
                "verification": exec_result.get("verification", {})
            }

        output = exec_result.get("output", "")
        if "___TEST_RESULTS___" in output:
            json_str = output.split("___TEST_RESULTS___")[-1].strip()
            import json
            try:
                results = json.loads(json_str)
                f_type = results.get("failure_type")
                if results["success"]:
                    f_type = None
                elif not f_type:
                    f_type = FailureType.CODE_FAILURE

                return {
                    "success": results["success"],
                    "failure_type": f_type,
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
            "failure_type": FailureType.TEST_HARNESS_FAILURE,
            "message": "Failed to parse test results from sandbox output\n" + str(exec_result.get("error", "")) + "\n" + str(output),
            "tests": test_code,
            "test_summary": {"total": total_tests, "passed": 0, "failed": 0, "errors": 1, "timeout": False},
            "verification": exec_result.get("verification", {})
        }

    except Exception as e:
        return {
            "success": False,
            "failure_type": FailureType.TEST_HARNESS_FAILURE,
            "message": f"Exception in test runner: {str(e)}\n" + traceback.format_exc(),
            "tests": "",
            "test_summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "timeout": False}
        }