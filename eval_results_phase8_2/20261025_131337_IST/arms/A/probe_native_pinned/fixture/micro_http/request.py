import json
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
