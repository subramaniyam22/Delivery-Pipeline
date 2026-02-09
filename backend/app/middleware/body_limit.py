from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int = None):
        super().__init__(app)
        self.max_bytes = max_bytes or settings.MAX_UPLOAD_SIZE

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Payload too large"},
                    )
            except ValueError:
                pass
        if not content_length:
            total = 0
            body = bytearray()
            async for chunk in request.stream():
                total += len(chunk)
                if total > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Payload too large"},
                    )
                body.extend(chunk)
            request._body = bytes(body)
        return await call_next(request)
