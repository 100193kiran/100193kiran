from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import json
import os

app = FastAPI()
class NoopProducer:
    def send(self, *_args, **_kwargs):
        return None

    def flush(self):
        return None

producer = NoopProducer()

class IngestPayload(BaseModel):
    model_id: str
    benchmark_name: str
    metrics: dict
    auditor_signature: str | None = None

@app.on_event("startup")
def startup() -> None:
    global producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BROKER", "kafka:9092"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
    except NoBrokersAvailable:
        producer = NoopProducer()

@app.get('/health')
def health():
    return {"status": "ok"}

@app.post('/ingest')
def ingest(payload: IngestPayload):
    if not payload.metrics:
        raise HTTPException(status_code=400, detail="metrics required")
    producer.send("benchmarks", payload.model_dump())
    producer.flush()
    return {"status": "queued"}
