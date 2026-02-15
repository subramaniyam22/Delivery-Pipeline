from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if request.url.path.startswith("/previews/"):
            allowed = []
            if settings.FRONTEND_URL:
                allowed.append(settings.FRONTEND_URL)
            allowed.extend(settings.cors_origins_list)
            allowed = [origin for origin in allowed if origin]
            frame_ancestors = " ".join(["'self'"] + sorted(set(allowed)))
            if "X-Frame-Options" in response.headers:
                del response.headers["X-Frame-Options"]
            # Allow axe-core from CDN for template validation (Playwright injects it)
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data: https:; "
                "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline'; "
                f"frame-ancestors {frame_ancestors}"
            )
        else:
            response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data: https:; "
                "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            )
        return response
