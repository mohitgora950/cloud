# AI Use Disclosure

This document details the artificial intelligence tools utilized during the implementation, experimentation, and documentation of the CS3081 Cloud Computing Mini Project (Knowledge Distillation and Deployment of a Lightweight Command-Parsing Language Model on a Local Cloud), following academic integrity guidelines.

---

## 1. Summary of Tools Used

| Tool / Model | Primary Purpose | Scope of Assistance | Verification Method |
| :--- | :--- | :--- | :--- |
| **Phi-3.5-mini-instruct** (3.8B, Microsoft) | Teacher Model | Synthesizing ground-truth semantic parsing targets (intent and slot frames) for 3,000 commands in `commands_pool.jsonl`. | Automated validation via `worker/clean.py` (strict JSON parsing, 4-key enforcement, intent validation, and verbatim substring matching in command text). |
| **Antigravity AI Assistant** | Coding Assistant & Scaffolding | Architectural design, Kubernetes manifest templating, Locust load-testing harness setup, CI/CD pipeline construction, and LaTeX/Markdown documentation scaffolding. | Manual code review, step-by-step unit testing (`pytest tests/`), execution in local k3d cluster, and empirical benchmarking. |

---

## 2. Detailed Breakdown by Task

### Task 1: Object Storage and Parallel Teacher Labelling
- **AI Contribution**: Scaffolding the multi-worker sharding architecture (`i % SHARD_COUNT == SHARD_INDEX`), S3 client abstraction with `boto3`, and rule-based validation logic in `worker/clean.py`.
- **Human Verification**:
  - Inspected generated shard outputs (`datasets/teacher/shard-0.jsonl` and `shard-1.jsonl`) to ensure zero overlap and zero omitted records across all 3,000 commands.
  - Mathematically verified the data cleaning reconciliation table:
    $$\text{Total Input (3000)} = (a) + (b) + (c) + (d) + \text{duplicates (50)} + \text{kept records}$$
  - Ran SHA-256 verification via `compute_sha256()` matching `datasets/v1/train.sha256`.

### Task 2: Sequence-Level Knowledge Distillation
- **AI Contribution**: Structuring PyTorch training loop for Causal Language Modeling with `AutoModelForCausalLM` and `AutoTokenizer` (`EleutherAI/pythia-70m`), gradient scheduling, loss tracking in `training/loss.csv`, and SHA-256 asset checksumming.
- **Human Verification**:
  - Enforced strict CPU execution (`torch.device("cpu")`) and pinned random seed (`42` for v1, `43` for v2) to ensure 100% deterministic reproducibility.
  - Evaluated loss convergence per epoch and empirically scored models against `data/validation.jsonl` using the provided `tools/score.py` evaluation harness.

### Task 3: Containerized Inference Service
- **AI Contribution**: FastAPI boilerplate implementing `/healthz`, `/readyz`, and `/parse`, alongside dynamic header injection (`X-Model-Version`, `X-Served-By`) and fault injection handling (`FAULT_INJECT=1`).
- **Human Verification**:
  - Tested container resource constraints locally (`--cpus 1 -m 1g`) with 50 sequential requests, monitoring RSS memory with `docker stats` to verify zero out-of-memory events and sub-2GB image size.
  - Verified that `FAULT_INJECT=1` reliably returned HTTP 500 with `{"error": "invalid_model_output"}`.

### Task 4: Kubernetes Deployment, Autoscaling, and Resilience
- **AI Contribution**: Authoring Kubernetes manifests (`k8s/deployment.yaml`, `k8s/service.yaml`, `k8s/ingress.yaml`, `k8s/hpa.yaml`, `k8s/secret.yaml`).
- **Human Verification**:
  - Deployed manifests into the local `k3d` cluster and verified readiness/liveness probe behavior during pod startup and model initialization.
  - Conducted rolling updates (`v1` to `v2`) under simulated Locust traffic, confirming zero downtime and rollback integrity via `kubectl rollout undo`.
  - Empirically measured cold-start times over three independent iterations.

### Task 5: Subnetting and Stateless NACL Design
- **AI Contribution**: Assisting in CIDR block subnet calculations and packet simulation test structuring.
- **Human Verification**:
  - Performed manual binary and decimal derivation for all four subnets (`app`, `public`, `data`, `management`) from base CIDR `10.20.0.0/16`.
  - Validated stateless inbound/outbound rule evaluation order using `tools/nacl_sim.py` against `network/packets_sample.jsonl`, achieving a 100% verification score (6/6).

### Task 6: Testing, Automation, and CI/CD
- **AI Contribution**: GitHub Actions workflow syntax (`.github/workflows/ci.yaml`), Makefile target specification, and unit test cases (`tests/test_service.py`).
- **Human Verification**:
  - Executed tests locally using `pytest`, verifying that all assertions passed cleanly.
  - Verified secret-scanning compliance using `gitleaks` to confirm zero credentials, tokens, or sensitive keys were committed.

### Task 7: SRE Benchmarking and Cost Modeling
- **AI Contribution**: Formulating the cost estimation equation based on `data/rate_card.json` and structuring the Service Level Objective (SLO) error budget framework.
- **Human Verification**:
  - Executed headless Locust load tests (`--users 4 --spawn-rate 4 --run-time 2m`), collecting empirical p50/p95 latency, throughput (RPS), and error rates.
  - Calculated exact cost per 1,000 requests using measured replica counts, CPU limits, and memory allocations.

---

## 3. Academic Integrity Confirmation

All generated code and configurations were rigorously reviewed, tested, and validated against the assignment specifications. No proprietary or unverified third-party solutions were incorporated. All empirical values reported in `report/report.pdf` originate from actual measurements taken during system execution on the student's hardware.

