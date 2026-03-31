from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import os
from pathlib import Path

app = FastAPI()
model = None

class Features(BaseModel):
    feature1: float
    feature2: float

@app.on_event('startup')
def startup():
    global model
    model_path = Path('models/hallucination_model.pkl')
    if not model_path.exists():
        from train import model as _  # noqa
    model = joblib.load(model_path)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/predict_hallucination')
def predict(features: Features):
    proba = float(model.predict_proba([[features.feature1, features.feature2]])[0][1])
    return {'hallucination_probability': proba}
