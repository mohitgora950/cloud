import os
import sys
import time
import subprocess
import requests

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results_dir = os.path.join(base_dir, "results")
os.makedirs(results_dir, exist_ok=True)
evidence_file = os.path.join(results_dir, "fault_inject_evidence.txt")

print("=== Starting FAULT_INJECT Verification Container ===")
# Remove any existing fault container
subprocess.run(["docker", "rm", "-f", "parser-fault-test"], capture_output=True)

# Run container with FAULT_INJECT=1
run_cmd = [
    "docker", "run", "-d",
    "--name", "parser-fault-test",
    "-p", "8001:8000",
    "--cpus", "1",
    "-m", "1g",
    "-e", "FAULT_INJECT=1",
    "-e", "MODEL_URI=models/v1",
    "-e", "S3_ENDPOINT=http://host.docker.internal:8333",
    "command-parser:v1"
]
subprocess.run(run_cmd, check=True)

# Wait for service readiness
print("Waiting for parser-fault-test to become ready on port 8001...")
ready = False
for _ in range(30):
    try:
        r = requests.get("http://localhost:8001/readyz", timeout=2)
        if r.status_code == 200:
            ready = True
            break
    except:
        pass
    time.sleep(1)

if not ready:
    print("Warning: parser-fault-test did not return readyz=200 in 30s")

# Test /parse with FAULT_INJECT=1
print("Sending test request to http://localhost:8001/parse ...")
payload = {"text": "set an alarm for 7am"}
res = requests.post("http://localhost:8001/parse", json=payload, timeout=10)

print(f"Status Code: {res.status_code}")
print(f"Response Body: {res.text}")

# Get container logs
logs = subprocess.run(["docker", "logs", "--tail", "20", "parser-fault-test"], capture_output=True, text=True).stdout

# Cleanup
subprocess.run(["docker", "rm", "-f", "parser-fault-test"], capture_output=True)

# Save evidence
with open(evidence_file, "w", encoding="utf-8") as f:
    f.write("=== Task 3: Fault Injection Verification (FAULT_INJECT=1) ===\n")
    f.write(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
    f.write(f"Endpoint: POST http://localhost:8001/parse\n")
    f.write(f"Payload: {payload}\n")
    f.write(f"HTTP Status: {res.status_code}\n")
    f.write(f"Response Body: {res.text}\n\n")
    f.write("--- Container Logs ---\n")
    f.write(logs)

print(f"Evidence written to {evidence_file}")

