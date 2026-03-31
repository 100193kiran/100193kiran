from pathlib import Path
import importlib.util
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("benchmarks_main", Path(__file__).with_name("main.py"))
benchmarks_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmarks_main)

client = TestClient(benchmarks_main.app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200

def test_ingest_validation():
    response = client.post('/ingest', json={"model_id":"m1", "benchmark_name":"b1", "metrics": {"score": 0.8}})
    assert response.status_code == 200
    assert response.json()["status"] == "queued"

def test_ingest_missing_metrics_rejected():
    response = client.post('/ingest', json={"model_id":"m1", "benchmark_name":"b1", "metrics": {}})
    assert response.status_code == 400
