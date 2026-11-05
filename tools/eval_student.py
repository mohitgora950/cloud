import os
import sys
import json
import re
import argparse
import subprocess
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default="models/v1")
    parser.add_argument("--input", default="data/validation.jsonl")
    parser.add_argument("--output", default="results/student_predictions.jsonl")
    parser.add_argument("--report", default="results/student_validation.json")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    model_path = os.path.join(base_dir, args.model_path) if not os.path.isabs(args.model_path) else args.model_path
    input_path = os.path.join(base_dir, args.input) if not os.path.isabs(args.input) else args.input
    output_path = os.path.join(base_dir, args.output) if not os.path.isabs(args.output) else args.output
    report_path = os.path.join(base_dir, args.report) if not os.path.isabs(args.report) else args.report

    print(f"Loading trained student model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_path)
    device = torch.device("cpu")
    model.to(device)
    model.eval()

    print(f"Reading evaluation dataset from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        val_data = [json.loads(line) for line in f if line.strip()]

    print(f"Evaluating student model on {len(val_data)} validation commands...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    predictions = []

    with open(output_path, "w", encoding="utf-8") as out_f:
        for i, item in enumerate(val_data):
            vid = item["id"]
            text = item["text"]
            prompt = f"Command: {text}\nJSON:"
            inputs = tokenizer(prompt, return_tensors="pt")

            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=64,
                    pad_token_id=tokenizer.eos_token_id,
                    do_sample=False
                )

            gen_text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

            # Clean JSON formatting
            if not gen_text.startswith("{"):
                match = re.search(r"\{.*?\}", gen_text, re.DOTALL)
                if match:
                    gen_text = match.group(0)
            else:
                idx = gen_text.find("}")
                if idx != -1:
                    gen_text = gen_text[:idx+1]

            pred_row = {"id": vid, "prediction": gen_text}
            predictions.append(pred_row)
            out_f.write(json.dumps(pred_row) + "\n")
            out_f.flush()

            if (i + 1) % 25 == 0 or (i + 1) == len(val_data):
                print(f"Evaluated {i + 1}/{len(val_data)} validation samples.")

    print(f"Saved student predictions to {output_path}")

    # Run score.py
    score_script = os.path.join(base_dir, "tools", "score.py")
    cmd = [sys.executable, score_script, output_path, input_path, "--out", report_path]
    print(f"Running score script: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)

if __name__ == "__main__":
    main()
