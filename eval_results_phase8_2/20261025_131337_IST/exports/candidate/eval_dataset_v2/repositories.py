import os
import shutil

# ==============================================================================
# REPOSITORY 1: micro_http (Lightweight HTTP service library)
# License: MIT License
# ==============================================================================

MICRO_HTTP_LICENSE = """MIT License

Copyright (c) 2026 micro_http contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

def setup_micro_http_repo(repo_root: str):
    pkg_dir = os.path.join(repo_root, "micro_http")
    tests_dir = os.path.join(repo_root, "tests")
    os.makedirs(pkg_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)

    with open(os.path.join(repo_root, "LICENSE"), "w", encoding="utf-8") as f:
        f.write(MICRO_HTTP_LICENSE)

    with open(os.path.join(pkg_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write('"""micro_http: Lightweight HTTP routing and request parsing."""\n__version__ = "0.1.0"\n')

    # micro_http/router.py
    with open(os.path.join(pkg_dir, "router.py"), "w", encoding="utf-8") as f:
        f.write('''import re
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
            # BUG: uses \\w+ which excludes hyphens like 'john-doe'
            regex_pattern += r"/(\\w+)"
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
''')

    # micro_http/request.py
    with open(os.path.join(pkg_dir, "request.py"), "w", encoding="utf-8") as f:
        f.write('''import json
from typing import Dict, Any, Optional

class Request:
    def __init__(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, body: str = ""):
        self.method = method.upper()
        self.path = path
        self.headers = headers or {}
        self.body = body
        self.state: Dict[str, Any] = {}

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieves header value with case-insensitivity.
        BUG: Does not normalize hyphens to underscores or vice versa.
        """
        lower_name = name.lower()
        for k, v in self.headers.items():
            if k.lower() == lower_name:
                return v
        return default

    def json(self) -> Dict[str, Any]:
        if not self.body:
            return {}
        return json.loads(self.body)
''')

    # micro_http/response.py
    with open(os.path.join(pkg_dir, "response.py"), "w", encoding="utf-8") as f:
        f.write('''import json
from typing import Dict, Any, Optional

STATUS_PHRASES = {
    200: "OK",
    201: "Created",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error"
}

def get_status_phrase(code: int) -> str:
    """Returns canonical HTTP reason phrase for a given status code."""
    return STATUS_PHRASES.get(code, "Unknown")

class Response:
    def __init__(self, body: str = "", status_code: int = 200, headers: Optional[Dict[str, str]] = None):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.cookies: Dict[str, str] = {}

    def set_cookie(self, key: str, value: str, httponly: bool = False, samesite: Optional[str] = None):
        """
        Sets a cookie header.
        BUG: formats httponly as 'HttpOnly=True' and samesite in arbitrary casing.
        """
        cookie_parts = [f"{key}={value}"]
        if httponly:
            cookie_parts.append(f"HttpOnly={httponly}")
        if samesite:
            cookie_parts.append(f"SameSite={samesite.lower()}")
        self.cookies[key] = "; ".join(cookie_parts)

    def json(self, data: Any) -> "Response":
        self.headers["Content-Type"] = "application/json"
        self.body = json.dumps(data)
        return self
''')

    # micro_http/middleware.py
    with open(os.path.join(pkg_dir, "middleware.py"), "w", encoding="utf-8") as f:
        f.write('''from typing import Callable, Any
from micro_http.request import Request
from micro_http.response import Response

class BaseMiddleware:
    def process_request(self, request: Request) -> Optional[Response]:
        return None

    def process_response(self, request: Request, response: Response) -> Response:
        return response
''')


# ==============================================================================
# REPOSITORY 2: task_flow (DAG workflow engine)
# License: Apache License 2.0
# ==============================================================================

TASK_FLOW_LICENSE = """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

Copyright 2026 task_flow contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

def setup_task_flow_repo(repo_root: str):
    pkg_dir = os.path.join(repo_root, "task_flow")
    tests_dir = os.path.join(repo_root, "tests")
    os.makedirs(pkg_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)

    with open(os.path.join(repo_root, "LICENSE"), "w", encoding="utf-8") as f:
        f.write(TASK_FLOW_LICENSE)

    with open(os.path.join(pkg_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write('"""task_flow: Directed Acyclic Graph Task Workflow Engine."""\n__version__ = "0.2.0"\n')

    # task_flow/task.py
    with open(os.path.join(pkg_dir, "task.py"), "w", encoding="utf-8") as f:
        f.write('''import time
from typing import Callable, Any, Optional

class TaskStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class Task:
    def __init__(self, name: str, fn: Callable, retries: int = 0):
        self.name = name
        self.fn = fn
        self.retries = retries
        self.status = TaskStatus.PENDING
        self.result: Any = None
        self.error: Optional[str] = None
        self.failure_count = 0
        self.next_retry_delay = 0.0

    def record_failure(self, error_msg: str, base_delay: float = 1.0):
        """
        Records task execution failure.
        BUG: Fails to increment failure_count and uses linear instead of exponential backoff.
        """
        self.status = TaskStatus.FAILED
        self.error = error_msg
        # Linear bug instead of base_delay * (2 ** self.failure_count)
        self.next_retry_delay = base_delay * self.failure_count

    def execute(self, *args, **kwargs) -> Any:
        self.status = TaskStatus.RUNNING
        try:
            self.result = self.fn(*args, **kwargs)
            self.status = TaskStatus.SUCCESS
            return self.result
        except Exception as e:
            self.record_failure(str(e))
            raise
''')

    # task_flow/graph.py
    with open(os.path.join(pkg_dir, "graph.py"), "w", encoding="utf-8") as f:
        f.write('''from typing import Dict, List, Optional, Set
from task_flow.task import Task, TaskStatus

def find_cycle(adj: Dict[str, List[str]]) -> Optional[List[str]]:
    """
    Detects cycle in adjacency graph.
    BUG: Returns True or None, instead of returning the ordered cycle list [node, ..., node].
    """
    visited = set()
    rec_stack = set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.remove(node)
        return False

    for n in adj:
        if n not in visited:
            if dfs(n):
                return True  # BUG: should return cycle path
    return None

class TaskGraph:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.dependencies: Dict[str, Set[str]] = {}

    def add_task(self, task: Task, dependencies: Optional[List[str]] = None):
        self.tasks[task.name] = task
        self.dependencies[task.name] = set(dependencies or [])

    def get_runnable_tasks(self) -> List[Task]:
        """
        Returns list of tasks ready for execution.
        BUG: Returns tasks if dependencies are merely in tasks dict, not requiring SUCCESS.
        """
        runnable = []
        for name, task in self.tasks.items():
            if task.status == TaskStatus.PENDING:
                deps = self.dependencies.get(name, set())
                # BUG: checks status != FAILED instead of all == SUCCESS
                all_satisfied = all(self.tasks[d].status != TaskStatus.FAILED for d in deps if d in self.tasks)
                if all_satisfied:
                    runnable.append(task)
        return runnable
''')

    # task_flow/executor.py
    with open(os.path.join(pkg_dir, "executor.py"), "w", encoding="utf-8") as f:
        f.write('''from typing import Dict, Any
from task_flow.graph import TaskGraph
from task_flow.task import TaskStatus

class SequentialExecutor:
    def __init__(self, graph: TaskGraph):
        self.graph = graph

    def run_all(self) -> Dict[str, Any]:
        results = {}
        while True:
            runnable = self.graph.get_runnable_tasks()
            if not runnable:
                break
            for task in runnable:
                try:
                    res = task.execute()
                    results[task.name] = res
                except Exception as e:
                    results[task.name] = None
        return results
''')

    # task_flow/context.py
    with open(os.path.join(pkg_dir, "context.py"), "w", encoding="utf-8") as f:
        f.write('''from typing import Dict, Any, Optional

class ExecutionContext:
    def __init__(self):
        self._data: Dict[str, Any] = {}

    def set(self, key: str, value: Any):
        self._data[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self._data.get(key, default)
''')


# ==============================================================================
# REPOSITORY 3: data_synth (Tabular data, statistics & transforms)
# License: BSD 3-Clause License
# ==============================================================================

DATA_SYNTH_LICENSE = """BSD 3-Clause License

Copyright (c) 2026, data_synth contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

def setup_data_synth_repo(repo_root: str):
    pkg_dir = os.path.join(repo_root, "data_synth")
    tests_dir = os.path.join(repo_root, "tests")
    os.makedirs(pkg_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)

    with open(os.path.join(repo_root, "LICENSE"), "w", encoding="utf-8") as f:
        f.write(DATA_SYNTH_LICENSE)

    with open(os.path.join(pkg_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write('"""data_synth: Tabular data analysis and transformation library."""\n__version__ = "0.3.0"\n')

    # data_synth/stats.py
    with open(os.path.join(pkg_dir, "stats.py"), "w", encoding="utf-8") as f:
        f.write('''import math
from typing import List

def compute_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)

def compute_std(values: List[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = compute_mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)

def compute_zscore(values: List[float]) -> List[float]:
    """
    Computes standard scores (z-scores) for a numeric list.
    BUG: Crashes with ZeroDivisionError when variance is zero.
    """
    mean = compute_mean(values)
    std = compute_std(values)
    # BUG: zero std causes ZeroDivisionError
    return [(x - mean) / std for x in values]

def calculate_percentile(values: List[float], p: float) -> float:
    """
    Calculates the p-th percentile (0 <= p <= 100) using nearest rank.
    BUG: nearest rank rounds down rather than using linear interpolation.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    idx = int((p / 100.0) * n)
    idx = max(0, min(idx, n - 1))
    return sorted_vals[idx]
''')

    # data_synth/dataframe.py
    with open(os.path.join(pkg_dir, "dataframe.py"), "w", encoding="utf-8") as f:
        f.write('''from typing import Dict, List, Any, Optional
from data_synth.stats import calculate_percentile, compute_mean

class DataFrame:
    def __init__(self, data: Dict[str, List[Any]]):
        self.data = data
        self.num_rows = len(next(iter(data.values()))) if data else 0

    def get_column(self, col_name: str) -> List[Any]:
        return self.data.get(col_name, [])

    def fill_missing(self, column: str, strategy: str = "mean") -> List[Any]:
        """
        Fills None values in a column.
        BUG: strategy='median' does not filter None before calling calculate_percentile.
        """
        vals = self.data.get(column, [])
        if strategy == "mean":
            valid = [v for v in vals if v is not None]
            fill_val = compute_mean(valid)
        elif strategy == "median":
            # BUG: passes vals with Nones directly into calculate_percentile
            fill_val = calculate_percentile(vals, 50.0)
        else:
            fill_val = 0.0

        return [fill_val if v is None else v for v in vals]
''')

    # data_synth/schema.py
    with open(os.path.join(pkg_dir, "schema.py"), "w", encoding="utf-8") as f:
        f.write('''from typing import Dict, Any, Type

class Field:
    def __init__(self, name: str, data_type: Type):
        self.name = name
        self.data_type = data_type

class Schema:
    def __init__(self, fields: Dict[str, Field]):
        self.fields = fields
''')

    # data_synth/transforms.py
    with open(os.path.join(pkg_dir, "transforms.py"), "w", encoding="utf-8") as f:
        f.write('''from typing import List

def min_max_scale(values: List[float], feature_range: tuple = (0.0, 1.0)) -> List[float]:
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if min_val == max_val:
        return [feature_range[0]] * len(values)
    diff = max_val - min_val
    target_diff = feature_range[1] - feature_range[0]
    return [feature_range[0] + ((x - min_val) / diff) * target_diff for x in values]
''')
