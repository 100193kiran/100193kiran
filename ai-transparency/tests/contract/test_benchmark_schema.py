import json
from jsonschema import validate
from pathlib import Path


def test_benchmark_schema_contract():
    schema = json.loads(Path('libs/common/schemas/benchmark-ingest.v1.json').read_text())
    payload = {
        'schema_version': '1.0.0',
        'model_id': '123e4567-e89b-12d3-a456-426614174000',
        'benchmark_name': 'truthfulqa',
        'metrics': {'score': 0.8},
        'auditor_signature': 'sig'
    }
    validate(instance=payload, schema=schema)
