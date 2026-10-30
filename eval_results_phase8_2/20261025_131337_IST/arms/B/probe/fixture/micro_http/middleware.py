from typing import Callable, Any
from micro_http.request import Request
from micro_http.response import Response

class BaseMiddleware:
    def process_request(self, request: Request) -> Optional[Response]:
        return None

    def process_response(self, request: Request, response: Response) -> Response:
        return response
