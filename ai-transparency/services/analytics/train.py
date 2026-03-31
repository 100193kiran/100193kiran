import pandas as pd
from sklearn.linear_model import LogisticRegression
import joblib
from pathlib import Path

df = pd.read_csv('data/hallucination_labels.csv')
X = df[['feature1', 'feature2']]
y = df['label']
model = LogisticRegression()
model.fit(X, y)
Path('models').mkdir(exist_ok=True)
joblib.dump(model, 'models/hallucination_model.pkl')
print('trained')
