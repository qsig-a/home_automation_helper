import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.main import PayloadSizeLimitMiddleware

@pytest.fixture
def client_with_middleware():
    app = FastAPI()
    # Set a small upload size limit for testing
    app.add_middleware(PayloadSizeLimitMiddleware, max_upload_size=10)

    @app.post("/test")
    async def test_endpoint(request: Request):
        body = await request.body()
        return {"size": len(body)}

    return TestClient(app)

def test_payload_size_limit_invalid_content_length_small_payload(client_with_middleware):
    """Test that an invalid Content-Length (ValueError) falls back to stream tracking, which succeeds if the payload is small."""
    response = client_with_middleware.post("/test", content=b"123", headers={"Content-Length": "invalid"})
    assert response.status_code == 200
    assert response.json() == {"size": 3}

def test_payload_size_limit_invalid_content_length_large_payload(client_with_middleware):
    """Test that an invalid Content-Length (ValueError) falls back to stream tracking, which fails with 413 if the payload is large."""
    response = client_with_middleware.post("/test", content=b"12345678901", headers={"Content-Length": "invalid"})
    assert response.status_code == 413
    assert response.json() == {"detail": "Payload Too Large. Limit is 1MB."}

def test_payload_size_limit_valid_large_content_length(client_with_middleware):
    """Test that a valid Content-Length larger than max_upload_size is caught early."""
    response = client_with_middleware.post("/test", content=b"12345678901", headers={"Content-Length": "11"})
    assert response.status_code == 413
    assert response.json() == {"detail": "Payload Too Large. Limit is 1MB."}

def test_payload_size_limit_valid_small_content_length(client_with_middleware):
    """Test that a valid Content-Length smaller than max_upload_size succeeds."""
    response = client_with_middleware.post("/test", content=b"123", headers={"Content-Length": "3"})
    assert response.status_code == 200
    assert response.json() == {"size": 3}

def test_payload_size_limit_missing_content_length_small_payload(client_with_middleware):
    """Test that missing Content-Length falls back to stream tracking, which succeeds if small."""
    # We remove the Content-Length header to simulate missing
    response = client_with_middleware.post("/test", content=b"123")
    assert response.status_code == 200
    assert response.json() == {"size": 3}
