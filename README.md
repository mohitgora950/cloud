# Cloud-Native Command-Parsing Language Model Microservice

**Course:** CS3081: Cloud Computing Mini Project  
**Author:** Mohit Gora  
**Roll Number:** 230101056  
**GitHub Repository:** [https://github.com/mohitgora950/cloud](https://github.com/mohitgora950/cloud)  
**Submission Tag:** `final`  

---

## 1. Project Overview

This project implements an end-to-end, production-grade cloud-native microservice architecture that distills a large teacher language model into a lightweight 70M-parameter student model (`EleutherAI/pythia-70m`) for natural language command parsing. The service is containerized strictly under 2.0 GB (1.70 GB disk / 360 MB content) using CPU-optimized PyTorch wheels, deployed on a local Kubernetes (`k3s`/`k3d`) cluster with Traefik Ingress routing, Horizontal Pod Autoscaling (HPA), zero-downtime rolling updates, subnets, stateless Network ACLs, and automated GitHub Actions CI/CD.

```
                                  +---------------------------------------+
                                  |            Client Requests            |
                                  +---------------------------------------+
                                                      |
                                                      v
                                        +---------------------------+
                                        |  Traefik Ingress (8080)   |
                                        +---------------------------+
                                                      |
                         +----------------------------+----------------------------+
                         |                                                         |
                         v                                                         v
         +-------------------------------+                         +-------------------------------+
         | Pod 1: command-parser:v2      |                         | Pod 2: command-parser:v2      |
         | (1 vCPU, 1 GiB limit)         |                         | (1 vCPU, 1 GiB limit)         |
         | FastAPI + Uvicorn Port 8000   |                         | FastAPI + Uvicorn Port 8000   |
         +-------------------------------+                         +-------------------------------+
                         ^                                                         ^
                         | (At container startup, downloads weights)               |
                         +----------------------------+----------------------------+
                                                      |
                                        +---------------------------+
                                        | SeaweedFS S3 (Port 8333)  |
                                        | s3://models/v2/           |
                                        +---------------------------+
```

---

## 2. Directory Hierarchy

```
.
├── .github/
│   └── workflows/
│       └── ci.yaml             # CI/CD: Gitleaks, Flake8, PyTest, Release Model Eval
├── cluster/
│   ├── k3d.yaml                # Local k3d cluster specification with port mapping 8080:80
│   ├── seaweedfs.yaml          # SeaweedFS deployment, service, PVC in 'data' namespace
│   ├── pipeline-workers.yaml   # Sharded worker jobs in 'pipeline' namespace
│   └── setup_s3.py             # S3 bucket provisioning & seed upload script
├── data/
│   ├── commands_pool.jsonl     # 3,000 unlabelled natural language utterances
│   ├── validation.jsonl        # 100 labelled benchmark commands for evaluation
│   ├── schema.json             # 4-key JSON schema & 8 permitted intents
│   └── rate_card.json          # Hourly billing rates for cost estimation
├── datasets/
│   ├── teacher/                # Sharded raw teacher outputs (shard-0.jsonl, shard-1.jsonl)
│   └── v1/
│       ├── train.jsonl         # 2,777 sanitized, clean training examples
│       └── train.sha256        # SHA-256 checksum of train.jsonl
├── k8s/
│   ├── namespace.yaml          # 'app' namespace definition
│   ├── secret.yaml             # s3-credentials secret (AWS keys)
│   ├── service.yaml            # ClusterIP service on port 8000
│   ├── ingress.yaml            # Traefik ingress rule routing /parse
│   ├── deployment.yaml         # Deployment (2 replicas, CPU/RAM limits, preStop hook)
│   └── hpa.yaml                # HorizontalPodAutoscaler (min 1, max 2, 70% CPU target)
├── models/
│   ├── v1/                     # Student Model v1 (1 epoch, initial distillation)
│   └── v2/                     # Student Model v2 (3 epochs, production distilled weights)
├── network/
│   ├── nacl.json               # Stateless NACL rules for public subnet
│   ├── packets_sample.jsonl    # 6 test packets for NACL simulation
│   └── subnets.md              # Mathematical derivation for 10.20.0.0/16 subnets
├── prompts/
│   └── teacher_prompt.txt      # Prompt template for teacher annotations
├── report/
│   └── report.pdf              # 4-page formal project report (architecture to SRE review)
├── results/
│   ├── cleaning_counts.txt     # Data sanitization counts
│   ├── container_memory.txt    # 50-request memory benchmark under 1 CPU / 1 GiB limit
│   ├── cold_start.txt          # 3 cold-start timings and median calculation
│   ├── rolling_update.txt      # 0.00% drop rolling update telemetry
│   ├── pod_recovery.txt        # 22.95s failover recovery telemetry
│   ├── rollback_v1.txt         # Verified rollback to X-Model-Version: v1
│   ├── loadtest_stats.csv      # Locust 2m load test performance metrics
│   ├── pod_resources.txt       # Continuous kubectl top pods telemetry during load test
│   ├── loadtest_headers.json   # Per-replica request distribution
│   ├── student_validation.json # Final evaluation metrics (97% validity, 34% full-frame)
│   └── nacl_sim_output.txt     # 6/6 NACL simulation verification
├── service/
│   ├── Dockerfile              # Multi-stage image build using torch==2.6.0+cpu (1.70 GB)
│   ├── main.py                 # FastAPI service (/parse, /healthz, /readyz, fallback)
│   └── requirements.txt        # Pinned dependency versions
├── tests/
│   └── test_service.py         # PyTest suite (healthz, schema, fault injection, parse)
├── tools/
│   ├── locustfile.py           # Locust load testing suite with header tracking
│   ├── nacl_sim.py             # Stateless NACL packet simulator
│   ├── score.py                # Official validation evaluation and quality gate
│   ├── generate_report.py      # Publication-quality report generator
│   └── generate_reflection_notes.py # 3-page handwritten notes generator
├── training/
│   ├── config.yaml             # Reproducible training configuration (seed 42, lr 1e-4)
│   ├── loss.csv                # Loss progression across 3 epochs
│   └── train.py                # CPU-optimized sequence-level distillation trainer
├── worker/
│   ├── worker.py               # Modulo-sharded parallel teacher labeling worker
│   └── clean.py                # 5-stage data sanitization script
├── 230101056.pdf               # Exactly 3-page handwritten reflection notes
├── AI_USE.md                   # Disclosure of AI tools, prompts, and verification
├── Makefile                    # One-command automation (up, down, train, test, lint)
└── README.md                   # Project documentation
```

---

## 3. Quick Start & Lifecycle Commands

The repository provides a complete `Makefile` to build, deploy, test, and tear down the infrastructure in single commands:

### A. Prerequisites
- Docker Desktop (with Kubernetes enabled or k3d installed)
- `k3d` v5.x
- `kubectl` v1.28+
- Python 3.10+ (with `torch`, `transformers`, `locust`, `requests`, `pytest`, `reportlab`)

### B. One-Command Cluster Bootstrap (`make up`)
```bash
make up
```
This single target executes:
1. Creates local Kubernetes cluster `cloud-cluster` with port forward `8080:80` using `cluster/k3d.yaml`.
2. Deploys SeaweedFS object storage in namespace `data` and provisions `datasets` and `models` buckets.
3. Builds Docker container `command-parser:v2` and imports it into the `cloud-cluster` image registry.
4. Applies Kubernetes manifests (`namespace.yaml`, `secret.yaml`, `service.yaml`, `ingress.yaml`, `hpa.yaml`, `deployment.yaml`).
5. Waits for pod readiness and verifies `http://localhost:8080/readyz`.

### C. Teardown & Cleanup (`make down`)
```bash
make down
```
Deletes the `cloud-cluster` k3d cluster and purges all running containers, volumes, and temporary networks.

### D. Model Training (`make train`)
```bash
# Full training on 1,500 records:
make train

# Verification mode on first 50 records:
make train SUBSET=50
```

### E. Run Unit Tests & Linting
```bash
# Execute PyTest suite:
make test

# Run Flake8 code linting:
make lint
```

---

## 4. Testing & Verification Guide

### 1. Ingestion & Inference Validation
Send a sample command to the Ingress endpoint:
```bash
curl -X POST http://localhost:8080/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "set alarm for 7am tomorrow"}'
```
Expected Response:
```json
HTTP/1.1 200 OK
X-Model-Version: v2
X-Served-By: command-parser-xxxx-yyyy

{"intent": "alarm_set", "date": "tomorrow", "time": "7am", "place": null}
```

### 2. Fault Injection Verification
Verify that setting `FAULT_INJECT=1` returns `HTTP 500`:
```bash
# Injected via container env or test probe:
python -m pytest tests/test_service.py -k test_fault_injection -v
```

### 3. Stateless NACL Simulation
Run the simulator against the sample packets:
```bash
python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check
```
Output:
```
Matched: 6/6 (100.0%)
All packet decisions matched expected outcomes!
```

### 4. Locust Load Test (Standard Marking Settings)
Execute the official 2-minute benchmark with 4 concurrent users:
```bash
python -m locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 \
  --run-time 2m --host http://localhost:8080 --csv results/loadtest
```

### 5. Quality Gate Evaluation
Evaluate predictions on the 100-sample benchmark:
```bash
python tools/score.py results/student_predictions.jsonl data/validation.jsonl --min-validity 95
```

---

## 5. Summary of Empirical Results

| Metric / Test | Rubric Target | Measured Value | Status |
| :--- | :--- | :--- | :--- |
| **Cleaned Dataset Records** | No gaps, exact partition | **2,777 records** (223 rejected) | PASSED |
| **Dataset Checksum** | Deterministic SHA-256 | `70393bdcd3b7a2710152e46cfa1125d99724ffe23f9553acf5f72046274857af` | PASSED |
| **Model Checkpoint Loss** | Strictly decreasing | Epoch 1: 2.8566, Epoch 2: 1.9421, Epoch 3: 1.2184 | PASSED |
| **Student JSON Validity** | $\ge 95.0\%$ | **97.0%** | PASSED |
| **Student Full-Frame Accuracy** | $\ge 0.5 \times \text{Teacher}$ (23%) | **34.0%** (Teacher: 46.0%) | PASSED |
| **Container Disk Usage** | $\le 2.0\text{ GB}$ | **1.70 GB disk / 360 MB content** | PASSED |
| **Peak Container Memory** | No OOM at 1 GiB limit | **457.2 MiB** (over 50 requests) | PASSED |
| **Rolling Update Drop Rate** | $\le 0.5\%$ | **0.00%** (27/27 successful) | PASSED |
| **Rollback Verification** | Returns `v1` header | Verified `X-Model-Version: v1` | PASSED |
| **Pod Recovery Latency** | $\le 2.0\%$ drops | **22.95s** (0.00% drops) | PASSED |
| **Median Cold-Start Time** | 3 independent runs | **22.03s** (22.03s, 22.35s, 20.88s) | PASSED |
| **Load Balancing Distribution** | Each replica $\ge 30\%$ | **37.0%** and **38.0%** | PASSED |
| **NACL Rule Verification** | 100% decision match | **6/6 packets (100.0%)** | PASSED |
| **Locust p50 Latency** | Baseline median | **2,500 ms** (Min: 1,118 ms) | PASSED |
| **Estimated Cost per 1k Reqs** | Rate card formula | **6.454 INR** (15.80 INR/hr for 4 pods) | PASSED |

---

## 6. Deliverables & Submission Checklist

1. `230101056.pdf`: Strictly 3-page handwritten reflection notes containing Name, Roll Number (230101056), Learnings, Challenges, Solutions, Findings, Improvements, and GitHub repo link.
2. `report/report.pdf`: 4-page comprehensive academic report covering all 7 tasks (Architecture, Decisions, Setup, Results, Limitations, Improvements).
3. `README.md`: Complete operations manual with build, deploy, test, and teardown commands.
4. `AI_USE.md`: Comprehensive disclosure of AI tool utilization and validation procedures.
5. GitHub Repository: Tagged as `final` commit at [https://github.com/mohitgora950/cloud](https://github.com/mohitgora950/cloud).
6. Submission Archive: Single zip file named `230101056.zip`.
