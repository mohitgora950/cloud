import os
import sys
import json
import time
import requests
import boto3
from botocore.exceptions import ClientError

def get_s3_client(endpoint):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        region_name="us-east-1"
    )

def main():
    shard_index = int(os.environ.get("SHARD_INDEX", "0"))
    shard_count = int(os.environ.get("SHARD_COUNT", "2"))
    teacher_url = os.environ.get("TEACHER_URL", "http://localhost:11434/api/generate")
    s3_endpoint = os.environ.get("S3_ENDPOINT", "http://127.0.0.1:8333")
    commands_path = os.environ.get("COMMANDS_PATH", "data/commands_pool.jsonl")
    prompt_path = os.environ.get("PROMPT_PATH", "prompts/teacher_prompt.txt")
    out_dir = os.environ.get("OUTPUT_DIR", "datasets/teacher")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"shard-{shard_index}.jsonl")
    s3_key = f"teacher/shard-{shard_index}.jsonl"

    print(f"[Worker {shard_index}/{shard_count}] Starting shard {shard_index} of {shard_count}")
    print(f"Teacher URL: {teacher_url}, S3: {s3_endpoint}")

    # Read prompt template
    if not os.path.exists(prompt_path):
        # Fallback to standard location
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "teacher_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Read commands pool
    if not os.path.exists(commands_path):
        commands_path = os.path.join(os.path.dirname(__file__), "..", "data", "commands_pool.jsonl")
    if not os.path.exists(commands_path):
        # Download from S3 if not found locally
        print(f"Downloading commands_pool.jsonl from S3 datasets bucket...")
        s3 = get_s3_client(s3_endpoint)
        commands_path = "/tmp/commands_pool.jsonl"
        s3.download_file("datasets", "commands_pool.jsonl", commands_path)

    with open(commands_path, "r", encoding="utf-8") as f:
        all_commands = [json.loads(line) for line in f if line.strip()]

    # Filter commands for this shard
    shard_commands = [
        cmd for i, cmd in enumerate(all_commands)
        if i % shard_count == shard_index
    ]
    print(f"[Worker {shard_index}] Assigned {len(shard_commands)} commands out of {len(all_commands)} total.")

    # Check already processed commands for resumption
    processed_ids = set()
    if os.path.exists(out_file):
        with open(out_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line)
                        processed_ids.add(obj["id"])
                    except:
                        pass
        print(f"[Worker {shard_index}] Found {len(processed_ids)} already processed commands.")

    out_f = open(out_file, "a" if processed_ids else "w", encoding="utf-8")

    completed = len(processed_ids)
    for cmd in shard_commands:
        cid = cmd["id"]
        if cid in processed_ids:
            continue
        text = cmd["text"]
        prompt = prompt_template.replace("{command}", text)

        try:
            res = requests.post(teacher_url, json={
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
            raw_reply = res.json().get("response", "").strip()
        except Exception as e:
            print(f"[Worker {shard_index}] Error processing {cid}: {e}")
            raw_reply = "{}"

        row = {"id": cid, "text": text, "teacher_raw": raw_reply}
        out_f.write(json.dumps(row) + "\n")
        out_f.flush()
        completed += 1
        if completed % 50 == 0 or completed == len(shard_commands):
            print(f"[Worker {shard_index}] Processed {completed}/{len(shard_commands)} commands.")

    out_f.close()
    print(f"[Worker {shard_index}] Shard complete. Uploading to S3: datasets/{s3_key}")

    try:
        s3 = get_s3_client(s3_endpoint)
        s3.upload_file(out_file, "datasets", s3_key)
        print(f"[Worker {shard_index}] Uploaded successfully to S3.")
    except Exception as e:
        print(f"[Worker {shard_index}] Warning: S3 upload failed: {e}")

if __name__ == "__main__":
    main()

