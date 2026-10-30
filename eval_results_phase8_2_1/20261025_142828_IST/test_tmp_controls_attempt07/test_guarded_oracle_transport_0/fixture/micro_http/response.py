import json
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
