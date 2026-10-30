import ast

text = r'''def match_path(pattern: str, path: str) -> Tuple[bool, Dict[str, str]]:
    """\n    Matches a URL pattern like '/users/<id>/profile' against '/users/42/profile'.\n    Returns (matched, params_dict).\n    """\n    regex_pattern = "^"
    parts = pattern.strip("/").split("/")
    param_names = []
    
    for part in parts:
        if part.startswith("<") and part.endswith(">") and "-" in part:
            param_name = part[1:-1]
            param_names.append(param_name)
            # Use \w+ which includes hyphens like 'hello-world-2026'
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
'''
try:
    tree = ast.parse(text)
    print("Parsed successfully!")
except Exception as e:
    print("ast.parse error:", type(e), e)
