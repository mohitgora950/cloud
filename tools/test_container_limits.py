import os
import sys
import json
import time
import requests
import subprocess

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results_dir = os.path.join(base_dir, "results")
os.makedirs(results_dir, exist_ok=True)
evidence_file = os.path.join(results_dir, "container_memory.txt")

# Read sample commands from validation.jsonl
val_path = os.path.join(base_dir, "data", "validation.jsonl")
commands = []
with open(val_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            commands.append(json.loads(line)["text"])

commands = (commands * 2)[:50]

print("=== Sending 50 sequential requests to container (1 CPU, 1 GiB Limit) ===")
latencies = []
memory_samples = []

for i, cmd in enumerate(commands):
    t0 = time.time()
    try:
        res = requests.post("http://localhost:8000/parse", json={"text": cmd}, timeout=30)
        status = res.status_code
    except Exception as e:
        status = f"Err: {e}"
    dur = time.time() - t0
    latencies.append(dur)

    # Sample docker stats
    stats_proc = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", "parser-limit-test"], capture_output=True, text=True)
    mem_str = stats_proc.stdout.strip()
    memory_samples.append(mem_str)

    if (i + 1) % 10 == 0 or (i + 1) == 50:
        print(f"Request {i+1}/50: status={status}, latency={dur:.2f}s, memory={mem_str}")

# Check container exit code
inspect_proc = subprocess.run(["docker", "inspect", "parser-limit-test", "--format", "{{.State.OOMKilled}} {{.State.Status}}"], capture_output=True, text=True)
inspect_out = inspect_proc.stdout.strip()

print(f"\nContainer inspection: OOMKilled/Status = {inspect_out}")
oom_killed = "true" in inspect_out.lower()
print(f"50 requests completed. OOM Killed: {oom_killed}")

# Save evidence to results/container_memory.txt
with open(evidence_file, "w", encoding="utf-8") as f:
    f.write("=== Task 3: 50 Sequential Requests Under Resource Limits (1 CPU, 1 GiB) ===\n")
    f.write(f"Container: parser-limit-test\n")
    f.write(f"Limits: --cpus 1 -m 1g\n")
    f.write(f"OOMKilled: {oom_killed}\n")
    f.write(f"Inspect State: {inspect_out}\n\n")
    f.write("--- Request Progress & Memory Samples ---\n")
    for idx, (lat, mem) in enumerate(zip(latencies, memory_samples)):
        f.write(f"Req {idx+1:02d}: latency={lat:.3f}s, memory_usage={mem}\n")
    f.write(f"\nFinal Memory Reading: {memory_samples[-1]}\n")

print(f"Evidence written to {evidence_file}")
