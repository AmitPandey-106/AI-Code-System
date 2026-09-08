import ast
import random
import traceback

class FaultInjector(ast.NodeTransformer):
    def __init__(self, seed=42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.mutations_applied = []

    def inject(self, code_str: str) -> dict:
        self.mutations_applied = []
        try:
            tree = ast.parse(code_str)
        except SyntaxError:
            return {"success": False, "reason": "Original code syntax error"}
            
        # Collect possible mutation points
        class NodeVisitor(ast.NodeVisitor):
            def __init__(self):
                self.operators = []
                self.compares = []
                
            def visit_BinOp(self, node):
                self.operators.append(node)
                self.generic_visit(node)
                
            def visit_Compare(self, node):
                self.compares.append(node)
                self.generic_visit(node)
                
        visitor = NodeVisitor()
        visitor.visit(tree)
        
        candidates = visitor.operators + visitor.compares
        if not candidates:
            return {"success": False, "reason": "No mutable nodes found"}
            
        target = self.rng.choice(candidates)
        
        # Apply mutation
        if isinstance(target, ast.BinOp):
            old_op = type(target.op)
            replacements = {
                ast.Add: ast.Sub(), ast.Sub: ast.Add(),
                ast.Mult: ast.Div(), ast.Div: ast.Mult()
            }
            if old_op in replacements:
                new_op = replacements[old_op]
                self.mutations_applied.append({
                    "type": "LOGICAL_OPERATOR_MUTATION",
                    "original": old_op.__name__,
                    "mutated": type(new_op).__name__,
                    "location": getattr(target, 'lineno', -1)
                })
                target.op = new_op
                
        elif isinstance(target, ast.Compare):
            if len(target.ops) == 1:
                old_op = type(target.ops[0])
                replacements = {
                    ast.Eq: ast.NotEq(), ast.NotEq: ast.Eq(),
                    ast.Lt: ast.Gt(), ast.Gt: ast.Lt(),
                    ast.LtE: ast.GtE(), ast.GtE: ast.LtE()
                }
                if old_op in replacements:
                    new_op = replacements[old_op]
                    self.mutations_applied.append({
                        "type": "LOGICAL_OPERATOR_MUTATION",
                        "original": old_op.__name__,
                        "mutated": type(new_op).__name__,
                        "location": getattr(target, 'lineno', -1)
                    })
                    target.ops[0] = new_op

        if not self.mutations_applied:
            return {"success": False, "reason": "No suitable mutation found"}
            
        ast.fix_missing_locations(tree)
        try:
            mutated_code = ast.unparse(tree)
        except Exception as e:
            return {"success": False, "reason": f"ast unparse failed: {str(e)}"}
            
        return {
            "success": True,
            "mutated_code": mutated_code,
            "fault": self.mutations_applied[0]
        }

def calculate_complexity(code_str: str) -> dict:
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return {}
    
    loc = len([line for line in code_str.split("\n") if line.strip()])
    func_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    ast_nodes = sum(1 for _ in ast.walk(tree))
    branches = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.If, ast.IfExp, ast.Try, ast.ExceptHandler, ast.For, ast.While)))
    
    return {
        "loc": loc,
        "functions": func_count,
        "ast_nodes": ast_nodes,
        "branches": branches
    }

def validate_mutation(original_code: str, mutated_code: str, expected_tests: list) -> bool:
    """Returns True if original passes and mutated fails."""
    # 1. Test original
    orig_env = {}
    try:
        exec(original_code, orig_env)
        for t in expected_tests:
            exec(t, orig_env)
    except Exception as e:
        print(f"Original failed tests: {e}")
        return False
        
    # 2. Test mutated
    mut_env = {}
    try:
        exec(mutated_code, mut_env)
        for t in expected_tests:
            exec(t, mut_env)
        # If it passed all tests, the mutation didn't break functionality
        return False
    except Exception:
        # Expected to fail
        return True
