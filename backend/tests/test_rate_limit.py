from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from app.rate_limit import limiter, rate_limit_exceeded_handler


def test_rate_limit_exceeded_returns_429():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/limited")
    @limiter.limit("1/minute")
    def limited(request: Request):
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/limited").status_code == 200
    response = client.get("/limited")
    assert response.status_code == 429
    body = response.json()
    assert body["error_code"] == "RATE_LIMIT_EXCEEDED"
