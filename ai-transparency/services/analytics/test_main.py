from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

def test_predict():
    response = client.post('/predict_hallucination', json={'feature1':0.2,'feature2':0.3})
    assert response.status_code == 200
    assert 'hallucination_probability' in response.json()
