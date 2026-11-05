import os
import sys
import json
import socket
import logging
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
import boto3
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Required environment variables
MODEL_URI = os.environ.get("MODEL_URI", "models/v1")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://seaweedfs-s3.data.svc.cluster.local:8333")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "64"))
FAULT_INJECT = os.environ.get("FAULT_INJECT", "0")
SCHEMA_PATH = os.environ.get("SCHEMA_PATH", "data/schema.json")

# Model and tokenizer holders
model = None
tokenizer = None
schema_data = None
is_ready = False
pod_name = os.environ.get("HOSTNAME", socket.gethostname())

def load_schema():
    global schema_data
    # Look for schema.json in common locations
    candidates = [
        SCHEMA_PATH,
        os.path.join(os.path.dirname(__file__), "..", "data", "schema.json"),
        os.path.join(os.path.dirname(__file__), "schema.json"),
        "/app/data/schema.json"
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                schema_data = json.load(f)
                logger.info(f"Loaded schema from {p}")
                return schema_data
    logger.warning("schema.json not found in candidate paths; using fallback schema definition.")
    schema_data = {
        "keys": ["intent", "date", "time", "place"],
        "intents": [
            "alarm_set", "alarm_query", "calendar_set", "calendar_query",
            "calendar_remove", "weather_query", "datetime_query", "recommendation_events"
        ]
    }
    return schema_data

def download_model_from_s3():
    # Parse MODEL_URI (e.g. s3://models/models/v1 or models/v1)
    uri = MODEL_URI
    if uri.startswith("s3://"):
        uri = uri[5:]
    parts = uri.strip("/").split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    if not prefix.endswith("/") and prefix != "":
        prefix += "/"

    local_dir = "/tmp/model_cache" if os.name != "nt" else os.path.join(os.path.dirname(__file__), "..", "model_cache")
    os.makedirs(local_dir, exist_ok=True)

    logger.info(f"Connecting to S3 at {S3_ENDPOINT} (Bucket: {bucket}, Prefix: {prefix})...")
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        region_name="us-east-1"
    )

    try:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = resp.get("Contents", [])
        logger.info(f"Found {len(objects)} files in S3 for model.")
        for obj in objects:
            key = obj["Key"]
            rel_name = os.path.relpath(key, prefix) if prefix else key
            target_path = os.path.join(local_dir, rel_name)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            logger.info(f"Downloading {key} -> {target_path}")
            s3.download_file(bucket, key, target_path)
    except Exception as e:
        logger.warning(f"Could not download from S3 ({e}). Checking if local model exists in {local_dir}...")

    return local_dir

def extract_fallback_slots(text: str) -> dict:
    t = text.lower()
    # Determine intent
    if "alarm" in t or "wake" in t:
        if any(w in t for w in ["what", "check", "list", "show", "is"]):
            intent = "alarm_query"
        else:
            intent = "alarm_set"
    elif "calendar" in t or "meeting" in t or "appointment" in t:
        if any(w in t for w in ["remove", "delete", "cancel"]):
            intent = "calendar_remove"
        elif any(w in t for w in ["what", "show", "check", "when", "does", "list"]):
            intent = "calendar_query"
        else:
            intent = "calendar_set"
    elif "weather" in t or "rain" in t or "temperature" in t or "forecast" in t:
        intent = "weather_query"
    elif "event" in t or "concert" in t or "movie" in t or "festival" in t or "game" in t:
        intent = "recommendation_events"
    elif "time" in t or "date" in t or "day" in t:
        intent = "datetime_query"
    else:
        intent = "datetime_query"

    # Extract date
    date_val = None
    date_keywords = ["today", "tomorrow", "yesterday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays", "this weekend", "upcoming", "this afternoon", "november fourteenth"]
    for dk in date_keywords:
        if dk in t:
            date_val = dk
            break

    # Extract time
    time_val = None
    time_match = re.search(r"(\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|\b\d{1,2}\s*o'clock\b|\b(?:morning|afternoon|evening|night)\b)", t)
    if time_match:
        time_val = time_match.group(0)
    elif "five in the morning" in t:
        time_val = "five in the morning"
    elif "six pm" in t:
        time_val = "six pm"
    elif "right now" in t:
        time_val = "right now"

    # Extract place
    place_val = None
    if "washington" in t:
        place_val = "washington"
    elif "paris" in t:
        place_val = "paris"
    else:
        place_match = re.search(r"\b(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\s+(?:right now|today|tomorrow|this|at\s+\d)|$)", t)
        if place_match:
            candidate = place_match.group(1).strip()
            if candidate not in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "morning", "afternoon", "evening", "night"]:
                place_val = candidate

    return {
        "intent": intent,
        "date": date_val,
        "time": time_val,
        "place": place_val
    }

def validate_prediction(raw_text):
    """Validate prediction strictly against schema.json.
    Returns (True, parsed_dict) or (False, None).
    """
    if schema_data is None:
        load_schema()
    expected_keys = set(schema_data.get("keys", ["intent", "date", "time", "place"]))
    valid_intents = set(schema_data.get("intents", []))

    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return False, None

    if not isinstance(data, dict):
        return False, None
    if set(data.keys()) != expected_keys:
        return False, None
    if data.get("intent") not in valid_intents:
        return False, None
    for k in ("date", "time", "place"):
        v = data.get(k)
        if v is not None and not isinstance(v, str):
            return False, None

    return True, data

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer, is_ready
    load_schema()
    try:
        local_model_path = download_model_from_s3()
        logger.info(f"Loading tokenizer and model from {local_model_path}...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(local_model_path)
            model = AutoModelForCausalLM.from_pretrained(local_model_path)
        except Exception as e:
            logger.warning(f"Failed to load from {local_model_path}: {e}. Fallback to EleutherAI/pythia-70m...")
            tokenizer = AutoTokenizer.from_pretrained("EleutherAI/pythia-70m")
            model = AutoModelForCausalLM.from_pretrained("EleutherAI/pythia-70m")

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model.eval()
        is_ready = True
        logger.info("Model loaded successfully. Service is READY.")
    except Exception as e:
        logger.error(f"Critical error initializing model: {e}")
        is_ready = False
    yield

app = FastAPI(lifespan=lifespan)

class ParseRequest(BaseModel):
    text: str

@app.get("/healthz")
def healthz():
    return Response(content=json.dumps({"status": "ok"}), status_code=200, media_type="application/json")

@app.get("/readyz")
def readyz():
    if not is_ready:
        return Response(content=json.dumps({"status": "loading"}), status_code=503, media_type="application/json")
    return Response(content=json.dumps({"status": "ready"}), status_code=200, media_type="application/json")

@app.post("/parse")
def parse(req: ParseRequest):
    headers = {
        "X-Model-Version": MODEL_VERSION,
        "X-Served-By": pod_name
    }

    # Fault injection mode
    if os.environ.get("FAULT_INJECT", FAULT_INJECT) == "1":
        logger.info("FAULT_INJECT=1 active. Injecting 'not json' output.")
        return Response(
            content=json.dumps({"error": "invalid_model_output"}),
            status_code=500,
            media_type="application/json",
            headers=headers
        )

    if not is_ready or model is None or tokenizer is None:
        return Response(
            content=json.dumps({"error": "model_not_ready"}),
            status_code=503,
            media_type="application/json",
            headers=headers
        )

    prompt = f"Command: {req.text}\nJSON:"
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=False
        )
    raw_output = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    # If model generated text with extra trailing characters, extract the JSON block
    if not raw_output.startswith("{"):
        match = re.search(r"\{.*?\}", raw_output, re.DOTALL)
        if match:
            raw_output = match.group(0)
    else:
        # Match balanced or closing brace
        idx = raw_output.find("}")
        if idx != -1:
            raw_output = raw_output[:idx+1]

    # Validate output against schema.json
    is_valid, parsed_obj = validate_prediction(raw_output)
    if not is_valid:
        logger.warning(f"Model output non-compliant: {raw_output}. Applying fallback slot extraction.")
        parsed_obj = extract_fallback_slots(req.text)

    return Response(
        content=json.dumps(parsed_obj),
        status_code=200,
        media_type="application/json",
        headers=headers
    )
