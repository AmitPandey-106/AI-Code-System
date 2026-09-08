import ast

def validate_code(code: str):
    """
    Validates code syntax and checks for security violations based on AST.
    Returns:
        dict: {
            "syntax_passed": bool,
            "safety_passed": bool,
            "error_message": str,
            "error_type": str
        }
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "syntax_passed": False,
            "safety_passed": False,
            "error_message": f"SyntaxError: {str(e)}",
            "error_type": "SyntaxError"
        }
    except Exception as e:
        return {
            "syntax_passed": False,
            "safety_passed": False,
            "error_message": f"ParseError: {str(e)}",
            "error_type": "ParseError"
        }
        
    # Safety Check Policy
    restricted_imports = {"os", "subprocess", "socket", "shutil", "ctypes", "sys", "pty", "urllib", "requests"}
    restricted_calls = {"eval", "exec", "open", "compile", "__import__"}
    
    class SecurityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.violations = []
            
        def visit_Import(self, node):
            for alias in node.names:
                if alias.name.split('.')[0] in restricted_imports:
                    self.violations.append(f"Restricted import: {alias.name}")
            self.generic_visit(node)
            
        def visit_ImportFrom(self, node):
            if node.module and node.module.split('.')[0] in restricted_imports:
                self.violations.append(f"Restricted import from: {node.module}")
            self.generic_visit(node)
            
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id in restricted_calls:
                self.violations.append(f"Restricted function call: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in {"system", "run", "Popen", "spawn", "execute"}:
                    self.violations.append(f"Restricted attribute call: {node.func.attr}")
            self.generic_visit(node)

    visitor = SecurityVisitor()
    visitor.visit(tree)
    
    if visitor.violations:
        return {
            "syntax_passed": True,
            "safety_passed": False,
            "error_message": "SecurityViolation: " + "; ".join(visitor.violations),
            "error_type": "SecurityViolation"
        }
        
    return {
        "syntax_passed": True,
        "safety_passed": True,
        "error_message": "",
        "error_type": None
    }
