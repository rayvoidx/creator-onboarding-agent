from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.rate_limit import RateLimitMiddleware


def create_app(max_requests: int = 2, window_seconds: int = 60) -> TestClient:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def test_rate_limit_in_memory_blocks_after_threshold():
    client = create_app(max_requests=2, window_seconds=60)

    r1 = client.get("/ping")
    assert r1.status_code == 200
    assert r1.headers.get("X-RateLimit-Limit") == "2"

    r2 = client.get("/ping")
    assert r2.status_code == 200
    assert r2.headers.get("X-RateLimit-Remaining") in {"0", "1"}

    r3 = client.get("/ping")
    assert r3.status_code == 429
    assert r3.json().get("error") == "Too many requests"


