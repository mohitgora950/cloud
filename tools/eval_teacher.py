import os
import json
import time
import requests
import subprocess
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROMPT_FILE = os.path.join(BASE_DIR, "prompts", "teacher_prompt.txt")
VAL_FILE = os.path.join(BASE_DIR, "data", "validation.jsonl")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
PRED_FILE = os.path.join(RESULTS_DIR, "teacher_predictions.jsonl")
REPORT_FILE = os.path.join(RESULTS_DIR, "teacher_validation.json")

os.makedirs(RESULTS_DIR, exist_ok=True)

with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_template = f.read()

with open(VAL_FILE, "r", encoding="utf-8") as f:
    val_items = [json.loads(line) for line in f if line.strip()]

print(f"Loaded {len(val_items)} validation examples.")

# Check if predictions already exist
existing_preds = {}
if os.path.exists(PRED_FILE):
    with open(PRED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                p = json.loads(line)
                existing_preds[p["id"]] = p["prediction"]
    print(f"Found {len(existing_preds)} existing predictions.")

out_f = open(PRED_FILE, "a" if existing_preds else "w", encoding="utf-8")

count = 0
for idx, item in enumerate(val_items):
    cid = item["id"]
    if cid in existing_preds:
        continue
    cmd_text = item["text"]
    prompt = prompt_template.replace("{command}", cmd_text)
    t0 = time.time()
    try:
        res = requests.post("http://localhost:11434/api/generate", json={
            "model": "phi3.5",
            "prompt": prompt,
            "format": "json",
            "keep_alive": -1,
            "stream": False,
            "options": {
                "temperature": 0,
                "seed": 42,
                "num_predict": 45,
                "num_ctx": 512
            }
        }, timeout=60)
        dur = time.time() - t0
        raw_resp = res.json().get("response", "").strip()
    except Exception as e:
        print(f"Error on {cid}: {e}")
        raw_resp = "{}"

    row = {"id": cid, "prediction": raw_resp}
    out_f.write(json.dumps(row) + "\n")
    out_f.flush()
    count += 1
    if count % 10 == 0 or count == len(val_items) - len(existing_preds):
        print(f"[{idx+1}/{len(val_items)}] ({dur:.2f}s) {cid}: {raw_resp}")

out_f.close()
print("Teacher evaluation complete. Running score.py...")

# Score with score.py
score_cmd = [
    sys.executable,
    os.path.join(BASE_DIR, "tools", "score.py"),
    PRED_FILE,
    VAL_FILE,
    "--out",
    REPORT_FILE
]
subprocess.run(score_cmd, check=True)
print(f"Score report written to {REPORT_FILE}")

