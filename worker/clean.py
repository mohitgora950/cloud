import os
import sys
import glob
import json
import hashlib
import boto3

VALID_INTENTS = {
    "alarm_set",
    "alarm_query",
    "calendar_set",
    "calendar_query",
    "calendar_remove",
    "weather_query",
    "datetime_query",
    "recommendation_events"
}

KEYS = {"intent", "date", "time", "place"}

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def clean_data(shard_pattern, output_path, sha_path, s3_endpoint=None):
    files = sorted(glob.glob(shard_pattern))
    if not files:
        # Check if files can be downloaded from S3
        if s3_endpoint:
            print("No local shard files found. Attempting to download from S3...")
            s3 = boto3.client("s3", endpoint_url=s3_endpoint, aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
            resp = s3.list_objects_v2(Bucket="datasets", Prefix="teacher/shard-")
            os.makedirs(os.path.dirname(shard_pattern), exist_ok=True)
            for obj in resp.get("Contents", []):
                fname = os.path.basename(obj["Key"])
                dest = os.path.join(os.path.dirname(shard_pattern), fname)
                s3.download_file("datasets", obj["Key"], dest)
                print(f"Downloaded {obj['Key']} -> {dest}")
            files = sorted(glob.glob(shard_pattern))

    print(f"Reading shard files: {files}")
    raw_records = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    raw_records.append(json.loads(line))

    print(f"Total input records read from shards: {len(raw_records)}")

    # Sort all input records by ID (e.g. C0001, C0002...)
    raw_records.sort(key=lambda r: r["id"])

    count_input = len(raw_records)
    count_a = 0  # not valid JSON
    count_b = 0  # keys not exactly intent, date, time, place
    count_c = 0  # intent not one of the eight
    count_d = 0  # slot neither null nor appears in command
    count_dup = 0  # duplicate commands
    kept_records = []

    seen_texts = {}  # text -> smallest id

    for r in raw_records:
        cid = r["id"]
        text = r.get("text", "")
        raw_str = r.get("teacher_raw", "")

        # (a) Check valid JSON
        try:
            parsed = json.loads(raw_str) if isinstance(raw_str, str) else raw_str
            if not isinstance(parsed, dict):
                count_a += 1
                continue
        except (json.JSONDecodeError, TypeError):
            count_a += 1
            continue

        # (b) Keys must be exactly intent, date, time, and place
        if set(parsed.keys()) != KEYS:
            count_b += 1
            continue

        # (c) Intent must be one of the eight
        if parsed.get("intent") not in VALID_INTENTS:
            count_c += 1
            continue

        # (d) Slot values must be null or appear in text
        slot_fail = False
        norm_text = " " + " ".join(text.strip().lower().split()) + " "
        for k in ("date", "time", "place"):
            v = parsed.get(k)
            if v is not None:
                if not isinstance(v, str):
                    slot_fail = True
                    break
                v_clean = " ".join(v.strip().lower().split())
                if v_clean and v_clean not in norm_text:
                    slot_fail = True
                    break
        if slot_fail:
            count_d += 1
            continue

        # (e) Duplicate command check (keep one with smallest id)
        norm_cmd = " ".join(text.strip().lower().split())
        if norm_cmd in seen_texts:
            count_dup += 1
            continue
        seen_texts[norm_cmd] = cid

        # Keep record
        kept_records.append({
            "id": cid,
            "text": text,
            "teacher_json": parsed
        })

    count_kept = len(kept_records)

    # Verification: input = a + b + c + d + duplicates + kept
    total_reconciled = count_a + count_b + count_c + count_d + count_dup + count_kept
    print("\n--- Cleaning Counts Table ---")
    print(f"Input records:               {count_input}")
    print(f"Rejected (a) Not valid JSON: {count_a}")
    print(f"Rejected (b) Bad keys:       {count_b}")
    print(f"Rejected (c) Bad intent:     {count_c}")
    print(f"Rejected (d) Bad slot text:  {count_d}")
    print(f"Rejected (e) Duplicates:    {count_dup}")
    print(f"Records kept:                {count_kept}")
    print(f"Sum (a+b+c+d+dup+kept):      {total_reconciled}")
    assert total_reconciled == count_input, f"Reconciliation mismatch! {total_reconciled} != {count_input}"

    # Write datasets/v1/train.jsonl
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in kept_records:
            f.write(json.dumps(r) + "\n")

    # Write datasets/v1/train.sha256
    checksum = compute_sha256(output_path)
    with open(sha_path, "w", encoding="utf-8") as f:
        f.write(f"{checksum}  train.jsonl\n")

    print(f"\nWrote cleaned train dataset to {output_path}")
    print(f"Wrote SHA-256 checksum ({checksum}) to {sha_path}")

    # Upload to S3 if endpoint available
    if s3_endpoint:
        try:
            s3 = boto3.client("s3", endpoint_url=s3_endpoint, aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
            s3.upload_file(output_path, "datasets", "v1/train.jsonl")
            s3.upload_file(sha_path, "datasets", "v1/train.sha256")
            print("Uploaded cleaned dataset and checksum to S3 bucket datasets under v1/")
        except Exception as e:
            print(f"Warning: S3 upload failed: {e}")

    return {
        "input": count_input,
        "a": count_a,
        "b": count_b,
        "c": count_c,
        "d": count_d,
        "duplicates": count_dup,
        "kept": count_kept,
        "sha256": checksum
    }

if __name__ == "__main__":
    shard_pat = sys.argv[1] if len(sys.argv) > 1 else "datasets/teacher/shard-*.jsonl"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "datasets/v1/train.jsonl"
    sha_file = sys.argv[3] if len(sys.argv) > 3 else "datasets/v1/train.sha256"
    s3_ep = os.environ.get("S3_ENDPOINT", "http://127.0.0.1:8333")
    clean_data(shard_pat, out_file, sha_file, s3_ep)

