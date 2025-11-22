from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.correlation import CorrelationIdMiddleware


def test_correlation_id_header_propagation():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/echo")
    def echo():
        return {"ok": True}

    client = TestClient(app)
    # generated
    r1 = client.get("/echo")
    assert r1.status_code == 200
    assert "X-Request-ID" in r1.headers
    # propagated
    custom_id = "req-123"
    r2 = client.get("/echo", headers={"X-Request-ID": custom_id})
    assert r2.status_code == 200
    assert r2.headers.get("X-Request-ID") == custom_id


