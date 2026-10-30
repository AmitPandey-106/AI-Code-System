import re
from typing import Dict, Any, Optional, Tuple

def match_path(pattern: str, path: str) -> Tuple[bool, Dict[str, str]]:
    """
    Matches a URL pattern like '/users/<id>/profile' against '/users/42/profile'.
    Returns (matched, params_dict).
    """
    regex_pattern = "^"
    parts = pattern.strip("/").split("/")
    param_names = []

    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            param_name = part[1:-1]
            param_names.append(param_name)
            # BUG: uses \w+ which excludes hyphens like 'john-doe'
            regex_pattern += r"/(\w+)"
        else:
            regex_pattern += f"/{re.escape(part)}"
    regex_pattern += "$"

    match = re.match(regex_pattern, path)
    if not match:
        return False, {}

    params = {}
    for name, val in zip(param_names, match.groups()):
        params[name] = val
    return True, params

class Router:
    def __init__(self):
        self.routes = []

    def add_route(self, method: str, pattern: str, handler: Any):
        self.routes.append((method.upper(), pattern, handler))

    def resolve(self, method: str, path: str) -> Optional[Tuple[Any, Dict[str, str]]]:
        for m, pattern, handler in self.routes:
            if m == method.upper():
                matched, params = match_path(pattern, path)
                if matched:
                    return handler, params
        return None
