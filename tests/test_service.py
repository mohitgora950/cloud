import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

# Ensure service directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(BASE_DIR, "service"))

import main
from main import app, validate_prediction

client = TestClient(app)

def test_healthz():
    """Test 1: GET /healthz returns 200 as long as the process is alive."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"status": "ok"}

def test_schema_validation():
    """Test 2: Schema validation strictly enforces four keys and valid intents."""
    # Valid output
    valid_json = '{"intent": "alarm_set", "date": "tomorrow", "time": "6am", "place": null}'
    ok, parsed = validate_prediction(valid_json)
    assert ok is True
    assert parsed["intent"] == "alarm_set"
    assert parsed["date"] == "tomorrow"

    # Bad JSON
    bad_json = 'not a json string'
    ok, parsed = validate_prediction(bad_json)
    assert ok is False
    assert parsed is None

    # Missing key
    missing_key = '{"intent": "alarm_set", "date": "tomorrow", "time": "6am"}'
    ok, parsed = validate_prediction(missing_key)
    assert ok is False

    # Extra key
    extra_key = '{"intent": "alarm_set", "date": "tomorrow", "time": "6am", "place": null, "extra": 123}'
    ok, parsed = validate_prediction(extra_key)
    assert ok is False

    # Invalid intent
    bad_intent = '{"intent": "unknown_intent", "date": null, "time": null, "place": null}'
    ok, parsed = validate_prediction(bad_intent)
    assert ok is False

def test_fault_injection():
    """Test 3: FAULT_INJECT=1 returns HTTP 500 with {"error": "invalid_model_output"}."""
    os.environ["FAULT_INJECT"] = "1"
    try:
        resp = client.post("/parse", json={"text": "set an alarm for 6am tomorrow"})
        assert resp.status_code == 500
        assert resp.json() == {"error": "invalid_model_output"}
        assert "X-Model-Version" in resp.headers
        assert "X-Served-By" in resp.headers
    finally:
        os.environ["FAULT_INJECT"] = "0"

def test_parse_valid_response():
    """Test 4: Successfully mocked or evaluated parse returns 200 and schema."""
    main.is_ready = True
    # If model is not loaded yet in test env, mock it to produce valid JSON
    class DummyTokenizer:
        eos_token_id = 0
        def __call__(self, text, return_tensors="pt"):
            import torch
            return {"input_ids": torch.tensor([[1, 2, 3]])}
        def decode(self, ids, skip_special_tokens=True):
            return '{"intent": "weather_query", "date": null, "time": null, "place": "paris"}'

    class DummyModel:
        def generate(self, **kwargs):
            import torch
            return torch.tensor([[1, 2, 3, 4]])

    orig_model = main.model
    orig_tok = main.tokenizer
    try:
        if main.model is None:
            main.model = DummyModel()
            main.tokenizer = DummyTokenizer()

        resp = client.post("/parse", json={"text": "what is the weather in paris"})
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"intent", "date", "time", "place"}
        assert data["intent"] in {
            "alarm_set", "alarm_query", "calendar_set", "calendar_query",
            "calendar_remove", "weather_query", "datetime_query", "recommendation_events"
        }
        assert resp.headers.get("X-Model-Version") is not None
        assert resp.headers.get("X-Served-By") is not None
    finally:
        main.model = orig_model
        main.tokenizer = orig_tok
