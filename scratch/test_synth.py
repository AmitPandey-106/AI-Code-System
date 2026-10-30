import ast
import os
import tempfile
from eval_dataset_v2.tasks import ALL_TASKS
from app.engineering_loop import EngineeringSession

text = '''```python
def match_path(pattern: str, path: str) -> Tuple[bool, Dict[str, str]]:
    regex_pattern = "^"
    return True, {}
```'''

with tempfile.TemporaryDirectory() as td:
    ALL_TASKS[0].setup_fn(td)
    s = EngineeringSession('prompt', td, 'pytest', fallback_enabled=True)
    res = s._synthesize_single_function_fallback(text)
    print('res:', repr(res))
    if not res:
        # Step through manually to see where it failed
        cleaned = text.strip().replace("```python", "").replace("```", "").strip()
        print("cleaned:", cleaned)
        tree = ast.parse(cleaned)
        fns = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        print("fns:", fns)
        target_fn_name = fns[0].name
        print("target_fn_name:", target_fn_name)
        matching_files = []
        for root, dirs, files in os.walk(td):
            for f in files:
                if f.endswith(".py"):
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, td).replace("\\", "/")
                    with open(full_p, "r", encoding="utf-8") as py_f:
                        file_src = py_f.read()
                    file_tree = ast.parse(file_src)
                    for node in file_tree.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_fn_name:
                            matching_files.append((rel_p, full_p, node, file_src))
        print("matching_files:", matching_files)
