import boto3
import os

endpoint = os.environ.get("S3_ENDPOINT", "http://127.0.0.1:8333")
s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1"
)

# 1. Create buckets
buckets = ["datasets", "models"]
existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
print("Existing buckets:", existing)

for b in buckets:
    try:
        s3.create_bucket(Bucket=b)
        print(f"Created bucket '{b}'")
    except Exception as e:
        print(f"Bucket '{b}' already exists or status: {e}")

# 2. Upload commands_pool.jsonl
src_path = os.path.join(os.path.dirname(__file__), "..", "data", "commands_pool.jsonl")
if os.path.exists(src_path):
    s3.upload_file(src_path, "datasets", "commands_pool.jsonl")
    print("Uploaded commands_pool.jsonl to datasets bucket")
else:
    print(f"File not found: {src_path}")

# Verify
resp = s3.list_objects_v2(Bucket="datasets")
print("Objects in datasets:", [o["Key"] for o in resp.get("Contents", [])])
resp = s3.list_objects_v2(Bucket="models")
print("Objects in models:", [o["Key"] for o in resp.get("Contents", [])])
