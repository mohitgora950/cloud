import os
import sys
import hashlib
import boto3
from transformers import AutoTokenizer, AutoModelForCausalLM

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def compute_dir_sha256(directory):
    lines = []
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".sha256"):
            continue
        fpath = os.path.join(directory, fname)
        if os.path.isfile(fpath):
            h = hashlib.sha256()
            with open(fpath, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            lines.append(f"{h.hexdigest()}  {fname}")
    return "\n".join(lines) + "\n"

def save_and_upload(version="v1"):
    model_name = "EleutherAI/pythia-70m"
    out_dir = os.path.join(base_dir, "models", version)
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Loading {model_name}...")
    tok = AutoTokenizer.from_pretrained(model_name)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name)
    
    print(f"Saving to {out_dir}...")
    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    
    sha_str = compute_dir_sha256(out_dir)
    sha_path = os.path.join(out_dir, "model.sha256")
    with open(sha_path, "w", encoding="utf-8") as f:
        f.write(sha_str)
    print(f"Wrote {sha_path}:\n{sha_str}")
    
    # Upload to S3
    try:
        s3 = boto3.client("s3", endpoint_url="http://127.0.0.1:8333", aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
        prefix = f"{version}/"
        for fname in os.listdir(out_dir):
            fpath = os.path.join(out_dir, fname)
            if os.path.isfile(fpath):
                s3.upload_file(fpath, "models", f"{prefix}{fname}")
        print(f"Uploaded {version} to S3 bucket models under {prefix}")
    except Exception as e:
        print(f"S3 upload error: {e}")

if __name__ == "__main__":
    save_and_upload("v1")
    save_and_upload("v2")
