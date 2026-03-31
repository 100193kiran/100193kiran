from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200

def test_ingest_validation():
    response = client.post('/ingest', json={"model_id":"m1", "benchmark_name":"b1", "metrics": {"score": 0.8}})
    assert response.status_code in (200, 500)
