import os
import sys

# Configure threading and OpenMP BEFORE importing torch
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"
os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
os.environ["KMP_BLOCKTIME"] = "0"

import json
import yaml
import time
import hashlib
import argparse
import torch
torch.set_flush_denormal(True)
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForCausalLM, get_linear_schedule_with_warmup
import boto3

def compute_dir_sha256(directory):
    """Compute sha256 of all files in directory, formatted standard sha256sum style."""
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

class CommandDataset(Dataset):
    def __init__(self, items, tokenizer, max_length=64):
        self.encodings = []
        for item in items:
            text = item["text"]
            t_json = item["teacher_json"]
            json_str = json.dumps(t_json) if isinstance(t_json, dict) else str(t_json)
            prompt = f"Command: {text}\nJSON: "
            full_text = f"{prompt}{json_str}<|endoftext|>"
            prompt_len = len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
            enc = tokenizer(
                full_text,
                truncation=True,
                max_length=max_length,
                padding="max_length",
                return_tensors="pt"
            )
            input_ids = enc.input_ids.squeeze(0)
            attention_mask = enc.attention_mask.squeeze(0)
            labels = input_ids.clone()
            labels[attention_mask == 0] = -100
            labels[:prompt_len] = -100
            self.encodings.append({
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "labels": labels
            })

    def __len__(self):
        return len(self.encodings)

    def __getitem__(self, idx):
        return self.encodings[idx]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="training/config.yaml")
    parser.add_argument("--data", default="datasets/v1/train.jsonl")
    parser.add_argument("--output-dir", default="models/v1")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--subset", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--s3-endpoint", default=os.environ.get("S3_ENDPOINT", "http://127.0.0.1:8333"))
    args = parser.parse_args()

    # Read config.yaml
    config_path = args.config
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    seed = args.seed if args.seed is not None else cfg.get("seed", 42)
    lr = float(cfg.get("learning_rate", 5e-4))
    # Support SUBSET from env or arg
    subset = args.subset
    if subset is None and "SUBSET" in os.environ:
        try:
            subset = int(os.environ["SUBSET"])
        except:
            pass

    batch_size = int(cfg.get("batch_size", 16))
    if args.epochs is not None:
        num_epochs = args.epochs
    elif subset is not None:
        num_epochs = 1
    else:
        num_epochs = int(cfg.get("num_epochs", 3))
    max_seq_len = int(cfg.get("max_seq_length", 64))

    print(f"=== Starting Pythia-70m Training ({args.version}) ===", flush=True)
    print(f"Seed: {seed}, Epochs: {num_epochs}, LR: {lr}, Batch: {batch_size}, MaxLen: {max_seq_len}, Subset: {subset}", flush=True)

    # Set seed and CPU threads
    torch.manual_seed(seed)
    torch.set_num_threads(4)

    # Load data
    data_path = args.data
    if not os.path.exists(data_path):
        data_path = os.path.join(os.path.dirname(__file__), "..", "datasets", "v1", "train.jsonl")
    if not os.path.exists(data_path):
        print(f"train.jsonl not found at {data_path}, checking S3...", flush=True)
        try:
            s3 = boto3.client("s3", endpoint_url=args.s3_endpoint, aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
            os.makedirs(os.path.dirname(data_path), exist_ok=True)
            s3.download_file("datasets", "v1/train.jsonl", data_path)
        except Exception as e:
            print(f"Could not fetch from S3: {e}", flush=True)

    records = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Task rule: "Use no more than 1,500 training examples: the first 1,500 records in the cleaned dataset."
    records = records[:1500]
    if subset is not None:
        records = records[:subset]
        print(f"Training on SUBSET of {len(records)} records.", flush=True)
    else:
        print(f"Training on {len(records)} records.", flush=True)

    # Load tokenizer and model
    model_name = "EleutherAI/pythia-70m"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name)

    device = torch.device("cpu")
    model.to(device)

    print(f"Building dataset of {len(records)} records (max_seq_len={max_seq_len})...", flush=True)
    t_ds0 = time.time()
    dataset = CommandDataset(records, tokenizer, max_length=max_seq_len)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    print(f"Dataset ready in {time.time()-t_ds0:.2f}s ({len(dataloader)} batches per epoch).", flush=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    total_steps = len(dataloader) * num_epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=int(total_steps * 0.1), num_training_steps=total_steps)

    loss_history = []
    loss_csv_path = os.path.join(os.path.dirname(__file__), "loss.csv")

    model.train()
    start_train_time = time.time()
    print(f"Starting training loop: {num_epochs} epochs...", flush=True)
    for epoch in range(1, num_epochs + 1):
        total_loss = 0.0
        start_time = time.time()
        for b_idx, batch in enumerate(dataloader):
            t_b0 = time.time()
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            t_fwd = time.time() - t_b0
            t_b1 = time.time()
            loss.backward()
            t_bwd = time.time() - t_b1
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()
            t_tot = time.time() - t_b0
            print(f"  Epoch {epoch}/{num_epochs} [Batch {b_idx+1}/{len(dataloader)}] Loss: {loss.item():.4f} (fwd: {t_fwd:.2f}s, bwd: {t_bwd:.2f}s, total: {t_tot:.2f}s)", flush=True)

        avg_loss = total_loss / max(len(dataloader), 1)
        epoch_dur = time.time() - start_time
        print(f"Epoch {epoch}/{num_epochs} - Avg Loss: {avg_loss:.4f} ({epoch_dur:.2f}s)", flush=True)
        loss_history.append((epoch, avg_loss))

    total_training_dur = time.time() - start_train_time
    print(f"Total training time: {total_training_dur:.2f}s", flush=True)

    # Save training/loss.csv
    with open(loss_csv_path, "w", encoding="utf-8") as f:
        f.write("epoch,loss\n")
        for ep, l in loss_history:
            f.write(f"{ep},{l:.4f}\n")
    print(f"Saved loss history to {loss_csv_path}", flush=True)

    # Save model and tokenizer to output directory
    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"Saved model and tokenizer to {out_dir}", flush=True)

    # Save model.sha256
    sha_content = compute_dir_sha256(out_dir)
    sha_file = os.path.join(out_dir, "model.sha256")
    with open(sha_file, "w", encoding="utf-8") as f:
        f.write(sha_content)
    print(f"Saved SHA-256 checksums to {sha_file}", flush=True)

    # Upload to S3 bucket models under models/v1/ or models/v2/
    try:
        s3 = boto3.client("s3", endpoint_url=args.s3_endpoint, aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
        prefix = f"models/{args.version}/"
        for fname in os.listdir(out_dir):
            fpath = os.path.join(out_dir, fname)
            if os.path.isfile(fpath):
                s3.upload_file(fpath, "models", f"{prefix}{fname}")
        print(f"Uploaded model artefacts to S3 bucket 'models' under {prefix}", flush=True)
    except Exception as e:
        print(f"Warning: S3 upload failed: {e}", flush=True)

    print(f"=== Completed Training {args.version} successfully ===", flush=True)

if __name__ == "__main__":
    main()
