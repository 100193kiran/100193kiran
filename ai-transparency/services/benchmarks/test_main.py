from pathlib import Path
import importlib.util
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("benchmarks_main", Path(__file__).with_name("main.py"))
benchmarks_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmarks_main)

client = TestClient(benchmarks_main.app)

BASE_PAYLOAD = {
    "model_id": "123e4567-e89b-12d3-a456-426614174000",
    "benchmark_name": "truthfulqa",
    "metrics": {"score": 0.8},
}


def test_health():
    response = client.get('/health')
    assert response.status_code == 200


def test_ingest_validation():
    response = client.post('/ingest', json=BASE_PAYLOAD, headers={'authorization':'Bearer dev-token'})
    assert response.status_code == 200
    assert response.json()["status"] in {"queued", "forwarded"}


def test_ingest_missing_metrics_rejected():
    payload = BASE_PAYLOAD | {"metrics": {}}
    response = client.post('/ingest', json=payload, headers={'authorization':'Bearer dev-token'})
    assert response.status_code == 422


def test_ingest_rejects_out_of_range_score():
    payload = BASE_PAYLOAD | {"metrics": {"score": 2}}
    response = client.post('/ingest', json=payload, headers={'authorization':'Bearer dev-token'})
    assert response.status_code == 422


def test_ingest_unauthorized():
    response = client.post('/ingest', json=BASE_PAYLOAD)
    assert response.status_code == 401
