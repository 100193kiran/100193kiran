from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
import json
import os

app = FastAPI()
producer = None

class IngestPayload(BaseModel):
    model_id: str
    benchmark_name: str
    metrics: dict
    auditor_signature: str | None = None

@app.on_event("startup")
def startup() -> None:
    global producer
    producer = KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKER", "kafka:9092"),
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

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
