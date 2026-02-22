from __future__ import annotations

import time
from collections.abc import Callable

from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, public_paths: set[str] | None = None):
        super().__init__(app)
        self.public_paths = public_paths or set()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path in self.public_paths:
            return await call_next(request)
        if path.startswith("/static") or path in {"/app.js"}:
            return await call_next(request)

        # expire
        exp = request.session.get("exp")
        if exp is not None:
            try:
                if int(exp) < int(time.time()):
                    request.session.clear()
            except (TypeError, ValueError):
                request.session.clear()

        if not request.session.get("user"):
            if path == "/" or not path.startswith("/api/"):
                return RedirectResponse(url="/login", status_code=302)
            return Response(status_code=401, content="Not authenticated")

        return await call_next(request)
