import os
import json
import time
import subprocess
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VAL_FILE = os.path.join(BASE_DIR, "data", "validation.jsonl")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
PRED_FILE = os.path.join(RESULTS_DIR, "untrained_predictions.jsonl")
REPORT_FILE = os.path.join(RESULTS_DIR, "untrained_validation.json")

os.makedirs(RESULTS_DIR, exist_ok=True)

print("Loading untrained EleutherAI/pythia-70m...")
tokenizer = AutoTokenizer.from_pretrained("EleutherAI/pythia-70m")
model = AutoModelForCausalLM.from_pretrained("EleutherAI/pythia-70m")
model.eval()

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

with open(VAL_FILE, "r", encoding="utf-8") as f:
    val_items = [json.loads(line) for line in f if line.strip()]

print(f"Evaluating untrained Pythia on {len(val_items)} validation items...")
out_f = open(PRED_FILE, "w", encoding="utf-8")

for idx, item in enumerate(val_items):
    cid = item["id"]
    cmd_text = item["text"]
    prompt = f"Command: {cmd_text}\nJSON:"
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=40,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=False
        )
    raw_pred = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    out_f.write(json.dumps({"id": cid, "prediction": raw_pred}) + "\n")
    if (idx + 1) % 25 == 0:
        print(f"[{idx+1}/{len(val_items)}] {cid}: {raw_pred[:40]}")

out_f.close()
print("Evaluation complete. Scoring with score.py...")

score_cmd = [
    sys.executable,
    os.path.join(BASE_DIR, "tools", "score.py"),
    PRED_FILE,
    VAL_FILE,
    "--out",
    REPORT_FILE
]
subprocess.run(score_cmd)
print(f"Report written to {REPORT_FILE}")

