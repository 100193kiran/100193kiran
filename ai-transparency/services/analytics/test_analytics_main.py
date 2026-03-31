from pathlib import Path
import importlib.util
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("analytics_main", Path(__file__).with_name("main.py"))
analytics_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analytics_main)

def test_predict():
    with TestClient(analytics_main.app) as client:
        response = client.post('/predict_hallucination', json={'feature1':0.2,'feature2':0.3})
    assert response.status_code == 200
    assert 'hallucination_probability' in response.json()
