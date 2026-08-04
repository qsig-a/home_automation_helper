import asyncio
import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from app.middleware.security import SecurityHeadersMiddleware

def test_security_headers_applied():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/")
    def read_root():
        return {"Hello": "World"}

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    headers = response.headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-XSS-Protection"] == "1; mode=block"
    assert headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert headers["Content-Security-Policy"] == "default-src 'none'"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert headers["Server"] == "hidden"
    assert headers["Permissions-Policy"] == "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
    assert headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert headers["Cross-Origin-Embedder-Policy"] == "require-corp"

def test_server_header_is_overwritten():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/")
    def read_root():
        return Response(content="Hello", headers={"Server": "uvicorn", "Other-Header": "value"})

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200

    server_headers = [v for k, v in response.headers.multi_items() if k.lower() == "server"]
    assert len(server_headers) == 1
    assert server_headers[0] == "hidden"

    assert response.headers["Other-Header"] == "value"

@pytest.mark.asyncio
async def test_non_http_scope():
    async def dummy_app(scope, receive, send):
        assert scope["type"] == "websocket"
        await send({"type": "websocket.accept"})

    middleware = SecurityHeadersMiddleware(dummy_app)

    scope = {"type": "websocket"}
    async def receive():
        return {}

    messages = []
    async def send(message):
        messages.append(message)

    await middleware(scope, receive, send)

    assert len(messages) == 1
    assert messages[0]["type"] == "websocket.accept"
