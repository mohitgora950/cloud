import os
import sys
import subprocess
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKER_SCRIPT = os.path.join(BASE_DIR, "worker", "worker.py")
COMMANDS_PATH = os.path.join(BASE_DIR, "data", "commands_pool.jsonl")
PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "teacher_prompt.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "datasets", "teacher")

os.makedirs(OUTPUT_DIR, exist_ok=True)

shard_count = int(sys.argv[1]) if len(sys.argv) > 1 else 2
teacher_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:11434/api/generate"
s3_endpoint = sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:8333"

print(f"Launching {shard_count} parallel workers...")
processes = []
for i in range(shard_count):
    env = os.environ.copy()
    env["SHARD_INDEX"] = str(i)
    env["SHARD_COUNT"] = str(shard_count)
    env["TEACHER_URL"] = teacher_url
    env["S3_ENDPOINT"] = s3_endpoint
    env["COMMANDS_PATH"] = COMMANDS_PATH
    env["PROMPT_PATH"] = PROMPT_PATH
    env["OUTPUT_DIR"] = OUTPUT_DIR
    
    log_file = os.path.join(OUTPUT_DIR, f"worker-{i}.log")
    lf = open(log_file, "a", encoding="utf-8")
    p = subprocess.Popen([sys.executable, "-u", WORKER_SCRIPT], env=env, stdout=lf, stderr=lf)
    processes.append((i, p, lf))
    print(f"Started Worker {i} with PID {p.pid}, logging to {log_file}")

# Monitor progress
try:
    while True:
        alive = sum(1 for _, p, _ in processes if p.poll() is None)
        # Count lines in shards
        counts = []
        for i in range(shard_count):
            sf = os.path.join(OUTPUT_DIR, f"shard-{i}.jsonl")
            if os.path.exists(sf):
                with open(sf, "r", encoding="utf-8") as f:
                    counts.append(sum(1 for _ in f))
            else:
                counts.append(0)
        print(f"Workers alive: {alive}/{shard_count} | Shard counts: {counts} | Total: {sum(counts)}/3000")
        if alive == 0:
            break
        time.sleep(10)
finally:
    for _, _, lf in processes:
        lf.close()

print("All workers finished!")

