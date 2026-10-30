"""
app/contract.py
===============
Structured TaskContract representation and contract-enforcement validation for LITE-Coder.
Ensures that the user's intended entry point, parameter specification, and requirements
survive planning, code generation, and autonomous self-repair without degradation.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any, Dict
import ast
import re

@dataclass
class StructuredConstraint:
    category: str  # "ordering", "boundary", "cardinality", "precision", "immutability", "field_requirement"
    description: str
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Requirement:
    text: str
    category: str = "general"
    is_deterministically_verifiable: bool = False
    constraint: Optional[StructuredConstraint] = None

@dataclass
class TaskContract:
    task_prompt: str
    entry_point: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    structured_requirements: List[Requirement] = field(default_factory=list)
    authoritative_tests: List[str] = field(default_factory=list)
    inferred_tests: List[str] = field(default_factory=list)

    @property
    def expected_params(self) -> List[str]:
        return self.parameters

    @classmethod
    def create_from_prompt(cls, prompt: str, authoritative_tests: Optional[List[str]] = None) -> "TaskContract":
        """
        Safely extracts target entry point, parameters, and requirements from the user prompt.
        Avoids brittle keyword sniffing (e.g. 'sort' -> 'sort_list').
        """
        entry_point = None
        parameters: List[str] = []
        authoritative = list(authoritative_tests) if authoritative_tests else []

        # 1. Pattern: "The intended entry point is: func_name(arg1, arg2)"
        m = re.search(r"(?:intended\s+entry\s*point|entry\s*point(?:\s*is)?)\s*:?\s*[`'\"]?([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\((.*?)\))?[`'\"]?", prompt, re.IGNORECASE)
        if m and m.group(1):
            entry_point = m.group(1)
            if m.group(2):
                parameters = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]

        # 2. Pattern: "def func_name(arg1, arg2):"
        if not entry_point:
            m = re.search(r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)", prompt)
            if m and m.group(1):
                entry_point = m.group(1)
                parameters = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]

        # 3. Pattern: "function/method called/named `func_name(arg1, arg2)`"
        if not entry_point:
            m = re.search(r"(?:function|method)\s+(?:called\s+|named\s+)?['`\"]?([a-zA-Z_][a-zA-Z0-9_]*)['`\"]?\s*(?:\((.*?)\))?", prompt, re.IGNORECASE)
            if m and m.group(1):
                fn = m.group(1)
                if fn.lower() not in ("called", "named", "a", "the", "python", "function", "method"):
                    entry_point = fn
                    if m.group(2):
                        parameters = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]

        # 4. Pattern: "(write|implement|create|define) [a] [python] [function/method] [called/named] func_name(arg1, arg2)"
        # Note: 'function' and 'method' keywords are explicitly OPTIONAL!
        if not entry_point:
            m = re.search(
                r"(?:write|implement|create|define)\s+(?:a\s+)?(?:python\s+)?(?:function\s+|method\s+)?(?:called\s+|named\s+)?['`\"]?([a-zA-Z_][a-zA-Z0-9_]*)['`\"]?\s*\((.*?)\)",
                prompt,
                re.IGNORECASE
            )
            if m and m.group(1):
                fn = m.group(1)
                if fn.lower() not in ("a", "the", "python", "function", "method", "program", "code"):
                    entry_point = fn
                    if m.group(2):
                        parameters = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]

        # 5. Pattern: Bare func_name(params): at line start or prompt start
        if not entry_point:
            m = re.search(r"(?:^|\n)\s*(?:implement|write|create|define)?\s*[`'\"]?([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*:", prompt, re.IGNORECASE)
            if m and m.group(1):
                fn = m.group(1)
                if fn.lower() not in ("if", "for", "while", "with", "print", "return", "assert", "class", "lambda"):
                    entry_point = fn
                    if m.group(2):
                        parameters = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]

        # 6. Fallback to authoritative tests if entry_point still unconfirmed
        if not entry_point and authoritative:
            for t_line in authoritative:
                m = re.search(r"assert\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", t_line)
                if m and m.group(1):
                    entry_point = m.group(1)
                    break

        # Filter out common invalid token captures
        if entry_point and entry_point.lower() in ("a", "the", "python", "function", "method", "program", "code", "if", "for", "while", "with"):
            entry_point = None

        # Extract requirements
        requirements = cls._extract_requirements(prompt)
        structured_reqs = cls._parse_structured_requirements(requirements, parameters)

        return cls(
            task_prompt=prompt,
            entry_point=entry_point,
            parameters=parameters,
            requirements=requirements,
            structured_requirements=structured_reqs,
            authoritative_tests=authoritative
        )

    @staticmethod
    def _parse_structured_requirements(requirements: List[str], parameters: List[str]) -> List[Requirement]:
        """
        Parses raw requirements into structured, task-agnostic representations.
        Only designates a requirement as deterministically verifiable if the constraint
        can be unambiguously parsed and checked via property testing or AST analysis.
        """
        parsed = []
        for req in requirements:
            req_lower = req.lower()
            constraint = None
            category = "general"
            is_verifiable = False

            # 1. Ordering and tie-breaking constraints
            m_order = re.search(r"\b(?:sort|sorted|order|ordered)\b.*?\b(descending|ascending|desc|asc)\b", req_lower)
            m_tie = re.search(r"\b(?:alphabetical|lexicographical|secondary)\s+tie[- ]break\b|\b(?:tie[- ]break|break\s+ties|breaking\s+ties)\b", req_lower)
            m_preserve = re.search(r"\b(?:same|equal)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b.*?(?:preserve|keep|maintain)\b.*?(?:original\s+input\s+order|input\s+order)\b.*?(?:determining|for)?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+order", req_lower)
            if not m_preserve:
                m_preserve = re.search(r"\b(?:preserve|keep|maintain)\b.*?(?:original\s+input\s+order|input\s+order)\b.*?(?:determining|for)?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+order", req_lower)

            if m_preserve:
                key = m_preserve.group(1) if m_preserve.lastindex >= 2 else "start"
                fld = m_preserve.group(2) if m_preserve.lastindex >= 2 else (m_preserve.group(1) if m_preserve.lastindex >= 1 else "title")
                category = "ordering"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="ordering",
                    description=req,
                    params={
                        "condition": f"equal_{key}",
                        "ordering": "original_input_order",
                        "field": fld
                    }
                )

            elif m_order or m_tie:
                direction = "descending" if (m_order and "desc" in m_order.group(1)) else ("ascending" if m_order else None)
                tie_break = "alphabetical" if (m_tie and "alphabetical" in req_lower) else ("lexicographical" if m_tie else None)

                # Extract primary sort key if explicitly named in requirement:
                # e.g., "sort by price descending", "sort products by id ascending", "sort by average descending"
                primary_key = None
                m_key = re.search(r"\b(?:sort|order)(?:\s+[a-zA-Z0-9_]+)?\s+by\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", req_lower)
                if not m_key:
                    m_key = re.search(r"\b(?:sort|order)(?:\s+[a-zA-Z0-9_]+)?\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:descending|ascending|desc|asc)\b", req_lower)
                if m_key:
                    cand_k = m_key.group(1).strip()
                    if cand_k not in ("in", "the", "a", "an", "all", "each", "and", "by", "descending", "ascending", "desc", "asc", "reverse"):
                        primary_key = cand_k

                # Extract tie-break key if explicitly named:
                # e.g., "breaking ties by product_name", "break ties by name alphabetically", "tie-break by name"
                tie_key = None
                m_tkey = re.search(r"\b(?:tie[- ]break|breaking\s+ties|break\s+ties)\b.*?\b(?:by|on)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", req_lower)
                if not m_tkey:
                    m_tkey = re.search(r"\b(?:by|on)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b.*?\b(?:alphabetical|lexicographical|tie[- ]break)\b", req_lower)
                if m_tkey:
                    cand_tk = m_tkey.group(1).strip()
                    if cand_tk not in ("in", "the", "a", "an", "all", "when", "equal", "both", "alphabetical", "lexicographical"):
                        tie_key = cand_tk
                elif "alphabetical" in req_lower and "name" in req_lower:
                    m_name = re.search(r"\b([a-zA-Z_]*name[a-zA-Z0-9_]*)\b", req_lower)
                    if m_name:
                        tie_key = m_name.group(1)

                category = "ordering"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="ordering",
                    description=req,
                    params={
                        "direction": direction,
                        "primary_key": primary_key,
                        "tie_break": tie_break,
                        "tie_key": tie_key
                    }
                )

            # 2. Boundary condition: e.g. "if n <= 0, return []" or touch at boundary must not merge
            elif re.search(r"\b(?:touch(?:ing)?\s+at\s+(?:a\s+)?boundary|adjacent\b).*?(?:not\s+(?:be\s+)?merged|remain\s+separate|never\s+merge)", req_lower):
                category = "boundary"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="boundary",
                    description=req,
                    params={
                        "type": "ordering/boundary",
                        "condition": "next_start == current_end",
                        "expected_behavior": "do_not_merge",
                        "behavior": "do_not_merge"
                    }
                )

            elif re.search(r"\b(?:if\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|<|==)\s*(-?\d+)\b.*?return\s*(\[\]|\{\}|None|0|False|""|'')", req, re.IGNORECASE):
                m_b = re.search(r"\b(?:if\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|<|==)\s*(-?\d+)\b.*?return\s*(\[\]|\{\}|None|0|False|""|'')", req, re.IGNORECASE)
                p_name, op, thresh, ret_val = m_b.groups()
                ret_parsed = None
                try:
                    ret_parsed = ast.literal_eval(ret_val)
                except Exception:
                    ret_parsed = [] if "[]" in ret_val else None

                category = "boundary"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="boundary",
                    description=req,
                    params={
                        "param_name": p_name,
                        "operator": op,
                        "threshold": int(thresh),
                        "expected_return": ret_parsed
                    }
                )

            # 3. Overlap condition: e.g. "overlap when next meeting's start time is strictly less than current end"
            elif re.search(r"\boverlap\b.*?(?:strictly\s+less\s+than|<)", req_lower):
                category = "overlap"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="overlap",
                    description=req,
                    params={
                        "condition": "next_start < current_end",
                        "behavior": "merge",
                        "expected_behavior": "merge"
                    }
                )

            # 4. Invalid input condition: e.g. "end <= start are invalid and must be ignored"
            elif re.search(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|<|==|>=|>)\s*([a-zA-Z_][a-zA-Z0-9_]*)\b.*?(?:invalid|malformed|corrupt|error).*?(?:ignored?|skip|discard(?:ed)?|dropped?)", req_lower) or \
                 re.search(r"(?:invalid|skip|ignore|discard)\b.*?\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|<|==|>=|>)\s*([a-zA-Z_][a-zA-Z0-9_]*)", req_lower):
                m_inv = re.search(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|<|==|>=|>)\s*([a-zA-Z_][a-zA-Z0-9_]*)\b.*?(?:invalid|malformed|corrupt|error).*?(?:ignored?|skip|discard(?:ed)?|dropped?)", req_lower)
                if not m_inv:
                    m_inv = re.search(r"(?:invalid|skip|ignore|discard)\b.*?\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|<|==|>=|>)\s*([a-zA-Z_][a-zA-Z0-9_]*)", req_lower)
                lhs, op, rhs = m_inv.group(1), m_inv.group(2), m_inv.group(3)
                category = "validation"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="validation",
                    description=req,
                    params={
                        "condition": f"{lhs} {op} {rhs}",
                        "behavior": "ignore",
                        "expected_behavior": "ignore"
                    }
                )

            # 5. Cardinality limit: e.g. "return top n", "maximum of k"
            elif re.search(r"\breturn\s+(?:the\s+)?(?:top|first|at most|maximum of)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", req_lower) or \
                 re.search(r"\b(?:length|size|count)\s*(?:<=|at most)\s*([a-zA-Z_][a-zA-Z0-9_]*)\b", req_lower):
                m_c = re.search(r"\breturn\s+(?:the\s+)?(?:top|first|at most|maximum of)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", req_lower)
                if not m_c:
                    m_c = re.search(r"\b(?:length|size|count)\s*(?:<=|at most)\s*([a-zA-Z_][a-zA-Z0-9_]*)\b", req_lower)
                k_param = m_c.group(1)
                category = "cardinality"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="cardinality",
                    description=req,
                    params={"max_length_param": k_param}
                )

            # 6. Numerical precision: e.g. "round to 2 decimals"
            elif re.search(r"\bround(?:ing|ed|s)?\b.*?\bto\s+(?:exactly\s+)?(\d+)\s+decimals?\b", req_lower) or \
                 re.search(r"\b(\d+)\s+decimal\s+places?\b", req_lower):
                m_p = re.search(r"\bround(?:ing|ed|s)?\b.*?\bto\s+(?:exactly\s+)?(\d+)\s+decimals?\b", req_lower)
                if not m_p:
                    m_p = re.search(r"\b(\d+)\s+decimal\s+places?\b", req_lower)
                dec = int(m_p.group(1))
                category = "precision"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="precision",
                    description=req,
                    params={"max_decimals": dec}
                )

            # 7. Immutability: e.g. "do not mutate the input", "original meeting dictionaries must not be modified"
            elif re.search(r"\b(?:do\s+not|never|must\s+not|not)\s+(?:be\s+)?(?:modified|mutated|altered|changed)\b|\bimmutable\b|\binput\s+mutation\b|\bnewly\s+created\b", req_lower):
                category = "immutability"
                is_verifiable = True
                if any(w in req_lower for w in ("dictionaries", "dicts", "objects", "items", "elements", "original")):
                    target = "original_input_objects"
                else:
                    target = "input"
                constraint = StructuredConstraint(
                    category="immutability",
                    description=req,
                    params={
                        "mutation_allowed": False,
                        "target": target
                    }
                )

            # 8. Field / schema requirement: e.g. "output dictionaries containing {name, average}"
            elif re.search(r"(?:output|return)\s+(?:dictionaries|dicts|objects)\s+(?:containing|with)\s*(?:\{|\()?\s*([a-zA-Z0-9_,\s]+)(?:\}|\))?", req_lower):
                m_f = re.search(r"(?:output|return)\s+(?:dictionaries|dicts|objects)\s+(?:containing|with)\s*(?:\{|\()?\s*([a-zA-Z0-9_,\s]+)(?:\}|\))?", req_lower)
                fields = [f.strip() for f in m_f.group(1).split(",") if f.strip()]
                category = "field_requirement"
                is_verifiable = True
                constraint = StructuredConstraint(
                    category="field_requirement",
                    description=req,
                    params={"fields": fields}
                )

            # 9. General natural-language requirement (cannot be deterministically verified)
            else:
                category = "general"
                is_verifiable = False
                constraint = None

            parsed.append(Requirement(
                text=req,
                category=category,
                is_deterministically_verifiable=is_verifiable,
                constraint=constraint
            ))

        # Cross-requirement enrichment for composite constraints (e.g. separate sort and tie-break bullet points)
        composite_ordering = {
            "direction": None,
            "primary_key": None,
            "tie_break": None,
            "tie_key": None
        }
        for item in parsed:
            if item.constraint and item.constraint.category == "ordering":
                p = item.constraint.params
                for k in ("direction", "primary_key", "tie_break", "tie_key"):
                    if p.get(k) and not composite_ordering[k]:
                        composite_ordering[k] = p[k]

        if any(composite_ordering.values()):
            for item in parsed:
                if item.constraint and item.constraint.category == "ordering":
                    for k in ("direction", "primary_key", "tie_break", "tie_key"):
                        if composite_ordering[k] and not item.constraint.params.get(k):
                            item.constraint.params[k] = composite_ordering[k]

        return parsed

    @staticmethod
    def _extract_requirements(prompt: str) -> List[str]:
        requirements = []
        lines = prompt.split("\n")
        in_req_section = False
        current_req_lines = []

        stop_section_pattern = re.compile(
            r"(?i)^(?:example|examples|input|output|note|notes|usage|test\s+cases|sample|sample\s+input|sample\s+output|explanation)\s*:"
        )

        def flush_current():
            if current_req_lines:
                full_req = " ".join(current_req_lines).strip()
                full_req = re.sub(r"\s+", " ", full_req)
                if len(full_req) > 3 and not stop_section_pattern.match(full_req):
                    requirements.append(full_req)
                current_req_lines.clear()

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if entering requirements section
            if re.match(r"(?i)^(?:requirements|rules|constraints|specifications?)\s*:", stripped):
                flush_current()
                in_req_section = True
                continue

            # Check if section ends (e.g. Example:, Input:, Output:)
            if in_req_section and (stop_section_pattern.match(stripped) or stripped.startswith(("```", '"""', "'''"))):
                flush_current()
                in_req_section = False
                continue

            # Check for primary bullet or numbered item
            num_bullet = re.match(r"^(\d+[\.\)]|\-|\*|\•)\s*(.+)", stripped)
            if num_bullet:
                flush_current()
                bullet_text = num_bullet.group(2).strip()
                if not stop_section_pattern.match(bullet_text):
                    current_req_lines.append(bullet_text)
            elif in_req_section:
                # Continuation line of current requirement or indented sub-point
                if stripped.lower() in ("for example:", "example:", "input:", "output:"):
                    continue
                sub_bullet = re.match(r"^(?:\-|\*)\s*(.+)", stripped)
                if sub_bullet:
                    current_req_lines.append(sub_bullet.group(1).strip())
                elif len(stripped) > 0 and not stripped.startswith(("```", '"""', "'''")):
                    current_req_lines.append(stripped)

        flush_current()
        return requirements

    def format_contract_instruction(self) -> str:
        """Formats the contract for injection into generation and repair prompts."""
        if not self.entry_point:
            return ""

        params_str = ", ".join(self.parameters) if self.parameters else ""
        reqs_str = ""
        if self.requirements:
            reqs_str = "CRITICAL REQUIREMENTS TO PRESERVE:\n" + "\n".join(f"- {r}" for r in self.requirements) + "\n"

        return f"""
CRITICAL TASK CONTRACT:
Target Entry Point: def {self.entry_point}({params_str})
{reqs_str}
STRICT CONTRACT RULES:
- You MUST implement and expose the required entry point '{self.entry_point}'.
- Do NOT replace or reduce this program to an isolated helper function.
- All auxiliary functions must directly serve the primary entry point '{self.entry_point}'.
- Fix the reported issue while strictly preserving previously satisfied requirements.
"""


def validate_plan_against_contract(plan_text: str, contract: Optional[TaskContract]) -> Tuple[bool, List[str]]:
    """
    Validates whether the generated plan accounts for critical requirements
    extracted in TaskContract. Returns (is_valid, missing_requirements).
    """
    if not contract or not contract.requirements:
        return True, []

    lower_plan = plan_text.lower()
    missing = []
    stop_words = {
        'return', 'each', 'from', 'their', 'when', 'that', 'with', 'must',
        'should', 'valid', 'list', 'data', 'input', 'records', 'containing',
        'called', 'named', 'value', 'values', 'item', 'items'
    }

    # First check structured requirements if present
    structured = getattr(contract, "structured_requirements", [])
    for s_req in structured:
        c = s_req.constraint
        if not c:
            continue
        cat = c.category
        if cat == "ordering":
            if not any(k in lower_plan for k in ["sort", "order", "descending", "ascending", "tie-break", "tie break", "alphabetical"]):
                missing.append(s_req.text)
        elif cat == "boundary":
            if not any(k in lower_plan for k in ["<=", "<= 0", "<=0", "negative", "zero"]):
                missing.append(s_req.text)
        elif cat == "precision":
            if not any(k in lower_plan for k in ["round", "decimal"]):
                missing.append(s_req.text)
        elif cat == "immutability":
            if not any(k in lower_plan for k in ["mutate", "mutation", "copy", "immutab"]):
                missing.append(s_req.text)

    for req in contract.requirements:
        if req in missing:
            continue
        req_lower = req.lower()
        words = [w for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', req_lower) if len(w) >= 4 and w not in stop_words]
        if words and not any(w in lower_plan for w in words):
            missing.append(req)

    # If 2 or more requirements are missing, plan is lossy
    if len(missing) >= 2 or (len(contract.requirements) > 0 and len(missing) > len(contract.requirements) * 0.25):
        return False, missing
    return True, missing


def extract_contract(prompt: str, authoritative_tests: Optional[List[str]] = None) -> TaskContract:
    """Convenience function to extract a TaskContract from a prompt."""
    return TaskContract.create_from_prompt(prompt, authoritative_tests=authoritative_tests)


def format_contract_instruction(contract: Optional[TaskContract]) -> str:
    """Convenience function to format contract instructions for model prompts."""
    if not contract:
        return ""
    return contract.format_contract_instruction()


def validate_code_against_contract(code: str, contract: Optional[TaskContract]) -> Tuple[bool, Optional[str]]:
    """
    Validates code syntax and verifies that the required entry point and parameters
    defined in TaskContract are present and conforming in the AST.
    """
    if not code or not code.strip():
        return False, "ContractViolation: Empty code generated."

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"SyntaxError: {str(e)}"
    except Exception as e:
        return False, f"ParseError: {str(e)}"

    if not contract or not contract.entry_point:
        return True, None

    # Search for matching function definition
    target_func = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == contract.entry_point:
                target_func = node
                break

    if target_func is None:
        return False, f"ContractViolation: Required entry point '{contract.entry_point}' is missing from generated code."

    # Validate parameter count if parameters were specified in contract
    if contract.parameters:
        expected_count = len(contract.parameters)
        total_args = len(target_func.args.args)
        num_defaults = len(target_func.args.defaults)
        min_args = total_args - num_defaults
        has_varargs = target_func.args.vararg is not None

        if has_varargs and expected_count >= min_args:
            pass
        elif not (min_args <= expected_count <= total_args):
            defined_params = [a.arg for a in target_func.args.args]
            return False, (
                f"ContractViolation: Entry point '{contract.entry_point}' expected {expected_count} parameter(s) "
                f"({', '.join(contract.parameters)}), but was defined with {len(defined_params)} ({', '.join(defined_params)})."
            )

    # Validate missing return statement for functions required to produce output
    req_texts = " ".join(contract.requirements).lower() if contract.requirements else ""
    requires_return = any(w in req_texts for w in ("return", "output", "result", "schedule", "average", "top", "calculate", "find", "merge")) or bool(getattr(contract, "structured_requirements", []))
    if requires_return:
        has_return = any(isinstance(n, (ast.Return, ast.Yield, ast.YieldFrom)) for n in ast.walk(target_func))
        if not has_return:
            return False, f"ContractViolation: Entry point '{contract.entry_point}' has no return statement or was truncated."

    # Validate input immutability if contract enforces immutability
    structured_reqs = getattr(contract, "structured_requirements", [])
    has_immutability = (
        any(getattr(r, "constraint", None) and r.constraint.category == "immutability" for r in structured_reqs)
        or any(re.search(r"\b(?:do\s+not|never|must\s+not|not)\s+(?:be\s+)?(?:modified|mutated|altered|changed)\b|\bimmutable\b", req, re.I) for req in (contract.requirements or []))
    )
    if has_immutability:
        param_names = set(a.arg for a in target_func.args.args)
        mutating_methods = {"sort", "reverse", "clear", "append", "extend", "pop", "insert", "remove"}
        for node in ast.walk(target_func):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id in param_names:
                    if node.func.attr in mutating_methods:
                        return False, (
                            f"ContractViolation: In-place mutation detected on input parameter '{node.func.value.id}'. "
                            f"Method '{node.func.attr}()' violates required immutability."
                        )
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                        if target.value.id in param_names:
                            return False, (
                                f"ContractViolation: In-place item mutation detected on input parameter '{target.value.id}'. "
                                f"Modifying '{target.value.id}[...]' violates required immutability."
                            )
            elif isinstance(node, ast.Delete):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                        if target.value.id in param_names:
                            return False, (
                                f"ContractViolation: Deletion detected on input parameter '{target.value.id}'. "
                                f"Deleting from '{target.value.id}' violates required immutability."
                            )

    return True, None
