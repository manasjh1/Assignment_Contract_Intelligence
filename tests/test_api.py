from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """Verify the API is running"""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"