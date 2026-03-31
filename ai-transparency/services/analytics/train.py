import pandas as pd
from sklearn.linear_model import LogisticRegression
import joblib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / 'data' / 'hallucination_labels.csv'
MODEL_PATH = BASE_DIR / 'models' / 'hallucination_model.pkl'


def train_model() -> None:
    df = pd.read_csv(DATA_PATH)
    X = df[['feature1', 'feature2']]
    y = df['label']
    model = LogisticRegression()
    model.fit(X, y)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)


if __name__ == '__main__':
    train_model()
    print('trained')
