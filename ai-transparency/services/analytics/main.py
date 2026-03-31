from fastapi import FastAPI
from pydantic import BaseModel
import joblib
from pathlib import Path
from train import train_model

app = FastAPI()
model = None
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / 'models' / 'hallucination_model.pkl'

class Features(BaseModel):
    feature1: float
    feature2: float

@app.on_event('startup')
def startup():
    global model
    if not MODEL_PATH.exists():
        train_model()
    model = joblib.load(MODEL_PATH)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/predict_hallucination')
def predict(features: Features):
    proba = float(model.predict_proba([[features.feature1, features.feature2]])[0][1])
    return {'hallucination_probability': proba}
