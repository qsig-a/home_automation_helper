from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from app.main import app, get_vestaboard_connector
import time

def override_get_vestaboard_connector():
    mock_conn = AsyncMock()
    mock_conn.send_message = AsyncMock(return_value=None)
    return mock_conn

app.dependency_overrides[get_vestaboard_connector] = override_get_vestaboard_connector

client = TestClient(app)

def run():
    # Send first request (should succeed)
    r1 = client.post("/message", json={"message": "Test"})
    assert r1.status_code == 200, f"Expected 200, got {r1.status_code}: {r1.text}"

    # Send second request immediately (should fail with 429)
    r2 = client.post("/message", json={"message": "Test"})
    assert r2.status_code == 429, f"Expected 429, got {r2.status_code}: {r2.text}"
    print("Rate limiting test passed! Got 429 as expected.")

if __name__ == "__main__":
    run()
