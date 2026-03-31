from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field, model_validator
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import requests
import json
import os
from typing import Any

app = FastAPI()


class NoopProducer:
    def send(self, *_args, **_kwargs):
        return None

    def flush(self):
        return None


producer: KafkaProducer | NoopProducer = NoopProducer()
INGEST_MODE = os.getenv("INGEST_MODE", "kafka").lower()
PROFILES_URL = os.getenv("PROFILES_URL", "http://profiles:4000")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "dev-token")


class IngestPayload(BaseModel):
    model_id: str = Field(min_length=8)
    benchmark_name: str = Field(min_length=2)
    metrics: dict[str, Any]
    auditor_signature: str | None = None

    @model_validator(mode="after")
    def validate_metrics(self) -> "IngestPayload":
        if not self.metrics:
            raise ValueError("metrics required")
        if "score" in self.metrics:
            score = self.metrics["score"]
            if not isinstance(score, (float, int)):
                raise ValueError("metrics.score must be numeric")
            if not 0 <= float(score) <= 1:
                raise ValueError("metrics.score must be between 0 and 1")
        return self


@app.on_event("startup")
def startup() -> None:
    global producer
    if INGEST_MODE != "kafka":
        return
    try:
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BROKER", "kafka:9092"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            linger_ms=25,
            retries=5,
        )
    except NoBrokersAvailable:
        producer = NoopProducer()


@app.get('/health')
def health():
    return {"status": "ok", "mode": INGEST_MODE}


@app.post('/ingest')
def ingest(payload: IngestPayload, authorization: str | None = Header(default=None)):
    if authorization != f'Bearer {AUTH_TOKEN}':
        raise HTTPException(status_code=401, detail='unauthorized')

    body = payload.model_dump()
    if INGEST_MODE == "direct":
        response = requests.post(
            f"{PROFILES_URL}/models/{payload.model_id}/benchmarks",
            json=body,
            timeout=10,
            headers={'authorization': f'Bearer {AUTH_TOKEN}', 'x-user-role': 'auditor'}
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="profiles forward failed")
        return {"status": "forwarded"}

    producer.send("benchmarks", body)
    producer.flush()
    return {"status": "queued"}
