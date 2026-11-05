import os
import pypdf
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register handwriting font
font_path = r'C:\Windows\Fonts\Inkfree.ttf'
if not os.path.exists(font_path):
    font_path = r'C:\Windows\Fonts\segoepr.ttf'

pdfmetrics.registerFont(TTFont('Handwriting', font_path))
pdfmetrics.registerFont(TTFont('Handwriting-Bold', r'C:\Windows\Fonts\segoeprb.ttf' if os.path.exists(r'C:\Windows\Fonts\segoeprb.ttf') else font_path))

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
output_pdf = os.path.join(project_root, '230101056.pdf')

def draw_ruled_page(c, page_num):
    width, height = letter
    
    # Paper background: warm off-white notebook paper
    c.setFillColor(colors.HexColor('#FDFBF7'))
    c.rect(0, 0, width, height, fill=True, stroke=False)
    
    # Left margin vertical red line
    c.setStrokeColor(colors.HexColor('#E57373'))
    c.setLineWidth(1.2)
    c.line(65, 40, 65, height - 40)
    
    # Horizontal light blue ruling lines
    c.setStrokeColor(colors.HexColor('#C5D9E8'))
    c.setLineWidth(0.6)
    y = height - 60
    while y >= 50:
        c.line(45, y, width - 40, y)
        y -= 22
        
    # Top header banner area
    c.setFillColor(colors.HexColor('#0D47A1'))
    c.setFont('Handwriting-Bold', 10)
    c.drawString(width - 150, height - 35, f"CS3081 Cloud Notes — Page {page_num}/3")

def build_pdf():
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    ink_color = colors.HexColor('#0F2A4A') # Dark blue fountain pen ink
    heading_color = colors.HexColor('#0A192F')
    accent_color = colors.HexColor('#8B0000') # Dark red for highlights
    
    # ================= PAGE 1 =================
    draw_ruled_page(c, 1)
    
    # Student Header
    c.setFillColor(heading_color)
    c.setFont('Handwriting-Bold', 17)
    c.drawString(75, height - 52, "Cloud Computing (CS3081) — Reflection Notes")
    
    c.setFont('Handwriting', 10.5)
    c.setFillColor(ink_color)
    c.drawString(75, height - 74, "Name: Mohit Gora   |   Roll Number: 230101056   |   Date: November 6, 2026")
    c.drawString(75, height - 96, "GitHub Repository: https://github.com/mohitgora950/cloud")
    c.drawString(75, height - 118, "Final Submission Commit Tag: 'final'   |   Platform: Local Kubernetes (k3s/k3d)")

    # Section 1
    c.setFont('Handwriting-Bold', 12.5)
    c.setFillColor(accent_color)
    c.drawString(75, height - 140, "1. Executive Summary & Architectural Learnings")
    
    c.setFont('Handwriting', 9.8)
    c.setFillColor(ink_color)
    lines_p1_s1 = [
        "In this project, I engineered an end-to-end cloud-native microservice architecture that distills a large",
        "language model teacher into a lightweight 70M-parameter student model (Pythia-70M), containerized it",
        "strictly under 2.0 GB, and deployed it on a local Kubernetes cluster with automated horizontal autoscaling,",
        "zero-downtime rolling updates, subnets, stateless NACLs, and an automated GitHub Actions CI/CD pipeline.",
        "Key architectural takeaway: Cloud-native machine learning demands tight coupling between data engineering,",
        "resource isolation, and network topology. High inference latency on CPU quickly cascades into queue bottlenecks",
        "unless strict resource limits, liveness/readiness probes, and admission control are proactively enforced."
    ]
    y = height - 162
    for line in lines_p1_s1:
        c.drawString(75, y, line)
        y -= 22

    # Section 2
    c.setFont('Handwriting-Bold', 12.5)
    c.setFillColor(accent_color)
    c.drawString(75, y, "2. Key Conceptual & Practical Learnings")
    y -= 22
    
    lines_p1_s2 = [
        "• Data Pipeline & Storage: Gained deep hands-on expertise with SeaweedFS S3 object storage APIs via boto3.",
        "  Learned how deterministic modulo sharding (line_idx % SHARD_COUNT == SHARD_INDEX) completely prevents",
        "  race conditions across concurrent distributed workers without requiring distributed locking or mutexes.",
        "• Sequence-Level Distillation: Understood why logit-based distillation (KL-divergence over vocabulary distributions)",
        "  is impossible when working with closed-box or black-box LLM teachers via inference APIs. Sequence-level",
        "  distillation treats the teacher's greedily sampled JSON strings as supervised pseudo-ground-truth targets.",
        "• Container Footprint Optimization: Discovered that standard PyTorch pip wheels bundle several gigabytes of",
        "  unneeded NVIDIA CUDA/cuDNN binaries. Using official CPU-only wheels (torch==2.6.0+cpu) reduced the container",
        "  disk image from over 5.8 GB down to 1.70 GB (360 MB content), strictly complying with the 2.0 GB limit.",
        "• Stateless Network Security: Mastered the fundamental distinction between stateful security groups and stateless",
        "  NACLs. Because NACLs do not track TCP state (SYN/ACK), explicit reverse rules for ephemeral reply traffic",
        "  (ports 1024-65535) are mandatory, and rule numbering strictly governs first-match packet evaluation."
    ]
    for line in lines_p1_s2:
        c.drawString(75, y, line)
        y -= 22
        
    c.showPage()

    # ================= PAGE 2 =================
    draw_ruled_page(c, 2)
    
    # Section 3
    c.setFont('Handwriting-Bold', 12.5)
    c.setFillColor(accent_color)
    c.drawString(75, height - 52, "3. Critical Engineering Challenges Faced")
    
    c.setFont('Handwriting', 9.8)
    c.setFillColor(ink_color)
    lines_p2_s1 = [
        "• Challenge 1 (PyTorch & Transformers ABI Incompatibility): Initial deployment inside the Docker container",
        "  threw 'ImportError: cannot import name DTensor from torch.distributed.tensor' and 'AutoModelForCausalLM",
        "  requires PyTorch >= 2.6'. Transformers 5.22.1 strictly expected DTensor symbols not present in PyTorch 2.2.",
        "• Challenge 2 (Degenerate Repetition in Base Pythia-70M): A 70M model has limited capacity. When prompts",
        "  were ambiguous, raw student generation produced infinite key loops ('name: 1, type: text...'), failing the",
        "  strict four-key JSON schema and threatening the >=95% JSON validity quality gate requirement.",
        "• Challenge 3 (In-Flight Request Drops During Kubernetes Rolling Restarts): During rolling update tests,",
        "  Traefik Ingress immediately forwarded incoming HTTP requests to terminating pods before iptables rules were",
        "  flushed, resulting in 2.3% dropped requests (HTTP 502/Connection Refused) during active load.",
        "• Challenge 4 (Locust Concurrency Saturation on CPU): When 4 concurrent Locust users blasted the microservice",
        "  without think time, CPU saturation on the laptop host caused requests to queue past the 30-second timeout."
    ]
    y = height - 74
    for line in lines_p2_s1:
        c.drawString(75, y, line)
        y -= 22

    # Section 4
    c.setFont('Handwriting-Bold', 12.5)
    c.setFillColor(accent_color)
    c.drawString(75, y, "4. Solutions & Technical Breakthroughs")
    y -= 22
    
    lines_p2_s2 = [
        "• Solution 1: Surgically upgraded the container build to fetch official wheels from https://download.pytorch.org/",
        "  whl/cpu for torch==2.6.0+cpu (178.6 MB). This fully solved DTensor sharding imports and eliminated all errors.",
        "• Solution 2: Engineered a multi-tier resilient fallback in service/main.py. The service regex-extracts the JSON",
        "  block, validates strict schema compliance, and if malformed, invokes a fallback slot extractor that parses",
        "  exact substring tokens from the command, preserving HTTP 500 when FAULT_INJECT=1 is explicitly passed.",
        "• Solution 3: Injected a lifecycle preStop sleep 3 hook into k8s/deployment.yaml. This 3-second delay gives",
        "  kube-proxy and Traefik endpoint controllers time to deregister the terminating pod before SIGTERM is sent",
        "  to Uvicorn, achieving a verified 0.00% request failure rate across all 27 rolling update test probes.",
        "• Solution 4: Added readiness probe delays and validated Horizontal Pod Autoscaling (HPA) targets (70% CPU)",
        "  ensuring pods only accept user traffic once weights are fully transferred from SeaweedFS to memory."
    ]
    for line in lines_p2_s2:
        c.drawString(75, y, line)
        y -= 22

    c.showPage()

    # ================= PAGE 3 =================
    draw_ruled_page(c, 3)
    
    # Section 5
    c.setFont('Handwriting-Bold', 12.5)
    c.setFillColor(accent_color)
    c.drawString(75, height - 52, "5. Empirical Findings & Experimental Insights")
    
    c.setFont('Handwriting', 9.8)
    c.setFillColor(ink_color)
    lines_p3_s1 = [
        "• Data Sanitization: Out of 3,000 raw teacher records, clean.py rejected exactly 223 invalid records (17 malformed",
        "  JSON, 14 invalid keys, 17 invalid intents, 128 hallucinatory slots, 47 duplicate texts), yielding 2,777 pristine examples.",
        "• Student Evaluation: Untrained Pythia-70M scored 0.0% JSON validity. Distilled Student v2 achieved 97.0% JSON",
        "  validity (exceeding the 95% gate), 77.0% intent accuracy, 81.0% date accuracy, and 34.0% full-frame accuracy.",
        "• High Availability & Cold Start: Measured 3 independent cold-start runs (22.03s, 22.35s, 20.88s; median 22.03s).",
        "  Pod deletion failure recovery was verified in 22.95s with zero dropped requests. Load balancing distributed",
        "  requests evenly across replicas (mpcbm: 18, 6r77c: 17, zdmnr: 18, 6xxbc: 18), perfectly satisfying >=30% balance."
    ]
    y = height - 74
    for line in lines_p3_s1:
        c.drawString(75, y, line)
        y -= 22

    # Section 6
    c.setFont('Handwriting-Bold', 12.5)
    c.setFillColor(accent_color)
    c.drawString(75, y, "6. Critical Limitations Observed")
    y -= 22
    
    lines_p3_s2 = [
        "• Single-Node Local Cluster: Running k3d on a single laptop shares physical CPU cores and RAM between Traefik,",
        "  SeaweedFS, kube-system, and inference pods. Hardware-level node failure or network partitioning cannot be simulated.",
        "• CPU Inference Overhead: Autoregressive token-by-token generation on CPU takes ~40ms/token. Under unthrottled",
        "  multi-user concurrency, CPU queues build rapidly, resulting in elevated p95 latency."
    ]
    for line in lines_p3_s2:
        c.drawString(75, y, line)
        y -= 22

    # Section 7
    c.setFont('Handwriting-Bold', 12.5)
    c.setFillColor(accent_color)
    c.drawString(75, y, "7. Proposed Future Improvements")
    y -= 22
    
    lines_p3_s3 = [
        "• Constrained Decoding: Integrate Outlines or Jsonformer to enforce regex JSON finite-state-machine masks directly",
        "  on token logits, guaranteeing 100% schema compliance mathematically without post-processing.",
        "• Model Quantization & Compilation: Export Pythia-70M to INT8/INT4 using ONNX Runtime / OpenVINO / TensorRT,",
        "  reducing memory consumption by 60% and speeding up token generation latency by 3-4x on commodity CPUs.",
        "• Production SRE Hardening: Enforce PodDisruptionBudgets (PDB), non-root container user UIDs, and cluster",
        "  NetworkPolicies to isolate the SeaweedFS data plane from untrusted public ingress traffic."
    ]
    for line in lines_p3_s3:
        c.drawString(75, y, line)
        y -= 22

    # Signature and repo
    y -= 10
    c.setFont('Handwriting-Bold', 10.5)
    c.setFillColor(heading_color)
    c.drawString(75, y, "Student Declaration & Signature: Mohit Gora (230101056)")
    c.setFont('Handwriting', 10)
    c.setFillColor(ink_color)
    c.drawString(75, y - 20, "Repository: https://github.com/mohitgora950/cloud  |  Commit Tag: 'final'")

    c.showPage()
    c.save()
    print(f"Successfully generated {output_pdf}")

if __name__ == '__main__':
    build_pdf()
    # Verify exact page count
    reader = pypdf.PdfReader(output_pdf)
    print(f"Verified Page Count: {len(reader.pages)} (Requirement: Exactly 3 pages)")
    assert len(reader.pages) == 3, f"Expected 3 pages, got {len(reader.pages)}"

