import json
import os
import re
import time
import requests
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'benchmarks',
    bootstrap_servers=os.getenv('KAFKA_BROKER', 'kafka:9092'),
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    group_id='ingest-worker'
)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

AUTH_TOKEN = os.getenv('AUTH_TOKEN', 'dev-token')

for msg in consumer:
    payload = msg.value
    text = json.dumps(payload)
    if EMAIL_RE.search(text) or SSN_RE.search(text):
      payload.setdefault('metrics', {})['pii_flagged'] = True

    url = f"{os.getenv('PROFILES_URL', 'http://profiles:4000')}/models/{payload['model_id']}/benchmarks"
    wait = 1
    for _ in range(5):
      try:
        requests.post(url, json=payload, timeout=5, headers={'authorization': f'Bearer {AUTH_TOKEN}', 'x-user-role': 'auditor'}).raise_for_status()
        break
      except Exception:
        time.sleep(wait)
        wait *= 2
