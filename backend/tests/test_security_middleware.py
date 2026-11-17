from fastapi.testclient import TestClient
from app.main import app


def test_security_headers_and_request_id():
    response = TestClient(app).get("/health/live", headers={"X-Request-ID": "trace-123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "trace-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_untrusted_request_id_is_replaced():
    response = TestClient(app).get("/health/live", headers={"X-Request-ID": "<script>"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] != "<script>"
    assert response.headers["x-request-id"]
