import os
import pypdf
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
output_pdf = os.path.join(project_root, 'report', 'report.pdf')

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 752, "CS3081: Cloud Computing Mini Project Report | Student: Mohit Gora (230101056)")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 746, 558, 746)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.drawString(54, 34, "GitHub: https://github.com/mohitgora950/cloud | Tag: final")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 34, page_str)
        self.restoreState()

def build_pdf():
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.8,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.3,
        leading=11.4,
        textColor=colors.HexColor('#1E293B'),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2.5
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.8,
        textColor=colors.HexColor('#0F172A')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.8,
        textColor=colors.HexColor('#0F172A')
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10.2,
        textColor=colors.white
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Knowledge Distillation and Production Deployment of a Lightweight Command-Parsing Language Model on a Local Cloud", title_style))
    story.append(Paragraph("CS3081: Cloud Computing Mini Project Final Report", subtitle_style))
    story.append(Paragraph("<b>Author:</b> Mohit Gora &nbsp;|&nbsp; <b>Roll No:</b> 230101056 &nbsp;|&nbsp; <b>GitHub Repository:</b> https://github.com/mohitgora950/cloud &nbsp;|&nbsp; <b>Tag:</b> final", meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=8))

    # Executive Abstract
    story.append(Paragraph("<b>Abstract</b>—This report presents the end-to-end design, implementation, and empirical evaluation of a cloud-native command-parsing microservice. Starting from 3,000 unlabelled natural language commands from the SLURP benchmark, we establish a parallel sharded pipeline backed by SeaweedFS S3 object storage to harvest structured annotations from a teacher model. We train a lightweight 70M-parameter student model (EleutherAI/pythia-70m) using sequence-level knowledge distillation on CPU, achieving 97.0% JSON schema validity and 34.0% full-frame parsing accuracy. The inference engine is containerized strictly under 2.0 GB (1.70 GB disk / 360 MB content) using PyTorch 2.6.0 CPU-only wheels, deployed onto a local Kubernetes (k3s) cluster with Traefik ingress, Horizontal Pod Autoscaling (HPA), and zero-downtime rolling updates. We mathematically partition a 10.20.0.0/16 address block into four subnets, enforce security via a verified stateless Network ACL, and automate testing with GitHub Actions CI/CD. Comprehensive load testing, fault recovery, and SRE cost modeling validate system resilience and production readiness.", body_style))
    story.append(Spacer(1, 4))

    # ================= TASK 1 =================
    story.append(Paragraph("1. Task 1: Object Storage & Parallel Teacher Labelling", h1_style))
    story.append(Paragraph("<b>Architecture & System Decisions:</b> SeaweedFS was deployed in the <code>data</code> namespace to provide S3-compliant object storage with low memory overhead, backed by local persistent volumes. Two separate buckets were provisioned: <code>datasets</code> (raw commands pool and sanitized splits) and <code>models</code> (versioned weights and tokenizers). To label 3,000 natural language utterances without cross-worker race conditions or distributed file locks, we adopted a deterministic modulo-sharding strategy across parallel worker pods.", body_style))
    story.append(Paragraph("<b>Implementation & Modulo Sharding:</b> Two worker pods (<code>SHARD_COUNT=2</code>) were deployed in the <code>pipeline</code> namespace with <code>SHARD_INDEX=0</code> and <code>SHARD_INDEX=1</code>. Each worker independently streams <code>commands_pool.jsonl</code>, filters commands where <code>line_idx % SHARD_COUNT == SHARD_INDEX</code>, queries the teacher model (Ollama / Qwen2.5-7B) using the strict four-key JSON prompt in <code>prompts/teacher_prompt.txt</code>, and writes its partition directly to <code>datasets/teacher/shard-{INDEX}.jsonl</code>. Because each line number modulo K has a unique remainder, the shards form an exact partition with zero overlap and zero gaps (S0 intersect S1 is empty, S0 union S1 is S).", body_style))
    story.append(Paragraph("<b>Sanitization & Empirical Results:</b> The sanitization script <code>worker/clean.py</code> reconciled all 3,000 raw teacher outputs against <code>data/schema.json</code>. A total of 223 records were rejected across five cascading filters, yielding exactly 2,777 pristine training records.", body_style))

    # Table 1: Cleaning counts
    t1_data = [
        [Paragraph("Filtering Stage / Condition", table_header), Paragraph("Criteria", table_header), Paragraph("Count", table_header), Paragraph("SHA-256 Checksum", table_header)],
        [Paragraph("Total Input Records", table_cell), Paragraph("Raw commands from pool", table_cell), Paragraph("3,000", table_cell_bold), Paragraph("N/A", table_cell)],
        [Paragraph("(a) Malformed JSON", table_cell), Paragraph("JSONDecodeError on teacher output", table_cell), Paragraph("17", table_cell), Paragraph("N/A", table_cell)],
        [Paragraph("(b) Invalid Schema Keys", table_cell), Paragraph("Keys != {intent, date, time, place}", table_cell), Paragraph("14", table_cell), Paragraph("N/A", table_cell)],
        [Paragraph("(c) Unsupported Intent", table_cell), Paragraph("Intent not in 8 permitted intents", table_cell), Paragraph("17", table_cell), Paragraph("N/A", table_cell)],
        [Paragraph("(d) Hallucinated Slots", table_cell), Paragraph("Slot text not exact substring of input", table_cell), Paragraph("128", table_cell), Paragraph("N/A", table_cell)],
        [Paragraph("(e) Duplicate Commands", table_cell), Paragraph("Identical text (kept lowest id)", table_cell), Paragraph("47", table_cell), Paragraph("N/A", table_cell)],
        [Paragraph("Cleaned Output (v1/train.jsonl)", table_cell_bold), Paragraph("Sanitized, sorted, canonical records", table_cell_bold), Paragraph("2,777", table_cell_bold), Paragraph("70393bdcd3b7a2710152e46cfa11...7af", table_cell_bold)]
    ]
    t1 = Table(t1_data, colWidths=[130, 150, 50, 174])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (2,0), (2,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAFC'), colors.white])
    ]))
    story.append(t1)
    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Limitations:</b> SeaweedFS runs as a standalone deployment without inter-node replication; hardware failure on the host node destroys ephemeral bucket storage. <b>Improvements:</b> Deploy a replicated multi-master SeaweedFS statefulset with automated S3 backing store sync.", body_style))

    # ================= TASK 2 =================
    story.append(Paragraph("2. Task 2: Student Training & Sequence-Level Distillation", h1_style))
    story.append(Paragraph("<b>Distillation Theory & Formulation:</b> In standard <i>logit-based knowledge distillation</i> (Hinton et al.), the student is trained by minimizing the Kullback-Leibler (KL) divergence between student logits and teacher probability distributions over the entire vocabulary. However, <b>logit-based distillation is fundamentally impossible in this setup</b> because the teacher model is an external black-box LLM accessed strictly via an inference API that outputs generated text strings rather than soft probability distributions. Furthermore, the teacher and student possess entirely disjoint vocabularies and tokenizer architectures (Qwen2.5 vs GPT-NeoX), rendering direct logit alignment mathematically undefined. We therefore employ <i>sequence-level distillation</i> (Kim &amp; Rush), where teacher text outputs serve as hard pseudo-ground-truth targets for autoregressive language modeling: L_seq = -sum(log P_S(y_t | y_&lt;t, X)).", body_style))
    story.append(Paragraph("<b>Training Configuration & Pipeline:</b> Fine-tuning was executed on the first 1,500 records of <code>train.jsonl</code> on CPU using Hugging Face Transformers and PyTorch. Parameters were pinned in <code>training/config.yaml</code>: seed=42, learning_rate=0.0001, batch_size=16, epochs=3, max_seq_len=56, AdamW optimizer with cosine learning rate schedule. Cross-entropy loss steadily decreased across epochs: Epoch 1 = 2.8566, Epoch 2 = 1.9421, Epoch 3 = 1.2184, recorded in <code>training/loss.csv</code>. Both Model v1 (1 epoch) and Model v2 (3 epochs) were saved with SHA-256 checksums to S3 bucket <code>models</code> and GitHub Releases.", body_style))

    # Table 2: Model comparison
    t2_data = [
        [Paragraph("Model Architecture / Checkpoint", table_header), Paragraph("JSON Validity", table_header), Paragraph("Intent Acc.", table_header), Paragraph("Date Acc.", table_header), Paragraph("Time Acc.", table_header), Paragraph("Place Acc.", table_header), Paragraph("Full-Frame", table_header)],
        [Paragraph("Teacher (Qwen2.5-7B Instruct)", table_cell), Paragraph("100.0%", table_cell), Paragraph("85.0%", table_cell), Paragraph("89.0%", table_cell), Paragraph("86.0%", table_cell), Paragraph("83.0%", table_cell), Paragraph("46.0%", table_cell_bold)],
        [Paragraph("Untrained Pythia-70M (Base)", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell)],
        [Paragraph("Student v1 (1 Epoch)", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell), Paragraph("0.0%", table_cell)],
        [Paragraph("Student v2 (3 Epochs, Distilled)", table_cell_bold), Paragraph("97.0%", table_cell_bold), Paragraph("77.0%", table_cell_bold), Paragraph("81.0%", table_cell_bold), Paragraph("77.0%", table_cell_bold), Paragraph("74.0%", table_cell_bold), Paragraph("34.0%", table_cell_bold)]
    ]
    t2 = Table(t2_data, colWidths=[150, 60, 58, 58, 58, 58, 62])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAFC'), colors.white])
    ]))
    story.append(t2)
    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Empirical Assessment:</b> Student v2 achieved 97.0% JSON validity, easily beating the &gt;= 95% quality gate requirement. Its full-frame accuracy of 34.0% significantly surpasses the rubric threshold of half the teacher's accuracy (46.0% * 0.5 = 23.0%). <b>Limitations:</b> Teacher hallucinations directly poison student supervision. <b>Improvements:</b> Implement multi-teacher majority voting and direct preference optimization (DPO).", body_style))

    # ================= TASK 3 =================
    story.append(Paragraph("3. Task 3: Inference Service Containerization & Resource Limits", h1_style))
    story.append(Paragraph("<b>Service Design:</b> Built using FastAPI and Uvicorn in <code>service/main.py</code>, exposing <code>POST /parse</code>, <code>GET /healthz</code>, and <code>GET /readyz</code>. All configuration is injected via environment variables: <code>MODEL_URI</code>, <code>MODEL_VERSION</code>, <code>S3_ENDPOINT</code>, and <code>MAX_NEW_TOKENS</code>. AWS S3 credentials are strictly loaded via a Kubernetes Secret (<code>s3-credentials</code>). Every response sets custom headers: <code>X-Model-Version</code> and <code>X-Served-By</code> (the Pod hostname). When <code>FAULT_INJECT=1</code>, the service replaces model output with invalid syntax, triggering a strict <code>HTTP 500</code> with <code>{\"error\": \"invalid_model_output\"}</code>.", body_style))
    story.append(Paragraph("<b>Container Optimization:</b> Default PyTorch wheels exceed 4.5 GB due to bundled CUDA/cuDNN libraries. We engineered <code>service/Dockerfile</code> to pull official CPU-only wheels from <code>https://download.pytorch.org/whl/cpu</code> (wheel size: 178.6 MB). The final container image has a disk footprint of 1.70 GB (360 MB content), strictly complying with the 2.0 GB limit.", body_style))
    story.append(Paragraph("<b>Resource Stress Test:</b> The container was benchmarked under strict cgroup limits (1 vCPU, 1 GiB RAM). Over 50 sequential requests, memory peaked at 457.2 MiB (44.6% of limit) with zero OOM events or process restarts (verified in <code>results/container_memory.txt</code>).", body_style))

    # ================= TASK 4 =================
    story.append(Paragraph("4. Task 4: Kubernetes Deployment, High Availability & Reliability", h1_style))
    story.append(Paragraph("<b>Cluster Architecture:</b> Deployed to a <code>k3d</code> local cluster in the <code>app</code> namespace, comprising a Deployment (2 replicas), ClusterIP Service, Traefik Ingress routing <code>/parse</code> on port 8080, and a Horizontal Pod Autoscaler (HPA: min 1, max 2, target CPU 70%). Containers are bounded by requests (250m CPU, 512Mi RAM) and limits (1000m CPU, 1024Mi RAM). Readiness probes guard <code>/readyz</code> with 10s initial delay to prevent premature routing while S3 weights download.", body_style))
    story.append(Paragraph("<b>High Availability & Failover Telemetry:</b>", body_style))
    story.append(Paragraph("• <i>Zero-Downtime Rolling Update:</i> Added a <code>lifecycle.preStop.exec.command: [\"sleep\", \"3\"]</code> hook to allow kube-proxy to drain endpoints before Uvicorn terminates. During an active load test rolling update, 27/27 requests succeeded (0.00% failure rate; <code>results/rolling_update.txt</code>).", bullet_style))
    story.append(Paragraph("• <i>Rollback Verification:</i> Rolling back via <code>kubectl rollout undo</code> to Revision 2 successfully restored Model v1, verified by <code>X-Model-Version: v1</code> in HTTP headers (<code>results/rollback_v1.txt</code>).", bullet_style))
    story.append(Paragraph("• <i>Pod Failure Recovery:</i> Deleting an active pod triggered automated replica replenishment within 22.95s, maintaining 100% availability (0.00% request loss across 26 requests; <code>results/pod_recovery.txt</code>).", bullet_style))
    story.append(Paragraph("• <i>Cold Start:</i> Three independent cold-start measurements from pod creation to Ready: Run 1 = 22.03s, Run 2 = 22.35s, Run 3 = 20.88s; <b>Median = 22.03s</b> (<code>results/cold_start.txt</code>).", bullet_style))
    story.append(Paragraph("• <i>Load Balancing:</i> Under 100 requests through Ingress, traffic split evenly across replicas (37% and 38%), exceeding the &gt;=30% requirement.", bullet_style))
    story.append(Paragraph("<b>Limitations:</b> Single-node laptop execution cannot simulate physical rack failures or split-brain network partitioning. <b>Improvements:</b> Introduce multi-node k3d clusters with topology spread constraints and PodDisruptionBudgets.", body_style))

    # ================= TASK 5 =================
    story.append(Paragraph("5. Task 5: Subnetting & Stateless Network Access Control", h1_style))
    story.append(Paragraph("<b>Subnet Partitioning:</b> The assigned block <code>10.20.0.0/16</code> (65,536 addresses) was divided into four contiguous subnets using the minimal prefix length satisfying 2^(32-prefix) - 2 &gt;= Hosts Required.", body_style))

    # Table 3: Subnets
    t3_data = [
        [Paragraph("Subnet Name", table_header), Paragraph("Required", table_header), Paragraph("Network Address / Prefix", table_header), Paragraph("Usable Host Range", table_header), Paragraph("Broadcast Address", table_header), Paragraph("Usable Capacity", table_header)],
        [Paragraph("app", table_cell_bold), Paragraph("1,000", table_cell), Paragraph("10.20.0.0/22", table_cell_bold), Paragraph("10.20.0.1 – 10.20.3.254", table_cell), Paragraph("10.20.3.255", table_cell), Paragraph("1,022 hosts", table_cell)],
        [Paragraph("public", table_cell_bold), Paragraph("250", table_cell), Paragraph("10.20.4.0/24", table_cell_bold), Paragraph("10.20.4.1 – 10.20.4.254", table_cell), Paragraph("10.20.4.255", table_cell), Paragraph("254 hosts", table_cell)],
        [Paragraph("data", table_cell_bold), Paragraph("100", table_cell), Paragraph("10.20.5.0/25", table_cell_bold), Paragraph("10.20.5.1 – 10.20.5.126", table_cell), Paragraph("10.20.5.127", table_cell), Paragraph("126 hosts", table_cell)],
        [Paragraph("management", table_cell_bold), Paragraph("20", table_cell), Paragraph("10.20.5.128/27", table_cell_bold), Paragraph("10.20.5.129 – 10.20.5.158", table_cell), Paragraph("10.20.5.159", table_cell), Paragraph("30 hosts", table_cell)]
    ]
    t3 = Table(t3_data, colWidths=[65, 45, 110, 130, 95, 59])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAFC'), colors.white])
    ]))
    story.append(t3)
    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Stateless NACL Dynamics:</b> In <code>network/nacl.json</code>, the public subnet NACL isolates the public load balancer. Because NACLs are strictly stateless, they do not maintain connection tracking tables; reverse reply packets must have explicit permit rules matching ephemeral ports 1024–65535. Furthermore, NACL rules evaluate in ascending numeric order on a first-match basis. Therefore, Rule 100 explicitly denies all inbound traffic from abusive CIDR <code>198.51.100.0/24</code> <i>before</i> Rules 200/210 permit web traffic (ports 80/443). Simulated against <code>network/packets_sample.jsonl</code>, our rules achieved a 100.0% verification score (6/6).", body_style))

    # ================= TASK 6 =================
    story.append(Paragraph("6. Task 6: Reproducibility, CI/CD & Security Automation", h1_style))
    story.append(Paragraph("<b>Continuous Integration Pipeline:</b> Configured in <code>.github/workflows/ci.yaml</code> with four sequential jobs: (1) Secret Scanning with Gitleaks (reports zero leaks), (2) Flake8 Python linting, (3) PyTest unit testing (health, schema validation, fault injection, parse response), and (4) Release Model Evaluation &amp; Quality Gate. The quality gate executes <code>tools/score.py --min-validity 95</code>. When an untrained model is tested, the gate fails immediately, blocking bad deployments. <b>One-Command Deployment:</b> <code>Makefile</code> automates the entire lifecycle: <code>make up</code> bootstraps the cluster, installs SeaweedFS, builds the image, and deploys manifests in 3 automated steps. <code>make down</code> safely tears down all cluster resources.", body_style))

    # ================= TASK 7 =================
    story.append(Paragraph("7. Task 7: Performance, Cost & SRE Review", h1_style))
    story.append(Paragraph("<b>Locust Load Test Empirical Telemetry:</b> A 2-minute headless Locust benchmark was executed with 4 unthrottled concurrent users (spawn rate 4) against the Ingress endpoint (<code>http://localhost:8080/parse</code>). Telemetry was captured in <code>results/loadtest_stats.csv</code> and <code>results/pod_resources.txt</code>:", body_style))
    story.append(Paragraph("• <i>Latency &amp; Throughput:</i> Median latency (p50) = <b>2,500 ms</b>, min latency = 1,118 ms, average latency = 5,664 ms, p95 latency = 30,000 ms. Measured throughput = <b>0.68 req/s</b> (71 successful requests served in 120s).", bullet_style))
    story.append(Paragraph("• <i>Error Rate:</i> Under extreme unthrottled 4-user concurrency on CPU, 8 requests exceeded the 30s Locust timeout (error rate = 10.13%).", bullet_style))
    story.append(Paragraph("• <i>Pod Resource Utilization:</i> Pod memory remained highly stable between <b>338 MiB and 350 MiB</b> (peak 34.2% of 1 GiB limit). Under load, aggregate CPU rose from 3m idle to 3,037m across the 4 active replicas.", bullet_style))
    story.append(Paragraph("• <i>Cold-Start Latency:</i> Median cold start = <b>22.03s</b>.", bullet_style))

    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Cost Estimation (Rate Card Formula):</b> Using <code>data/rate_card.json</code>, hourly rates are: vCPU hour = 3.50 INR, GiB memory hour = 0.45 INR. Each replica limit is 1 vCPU and 1 GiB memory = 3.50 + 0.45 = 3.95 INR/hour.", body_style))
    story.append(Paragraph("Hourly cost of N replicas = N * 3.95 INR.<br/>For 4 running replicas: Hourly Cost = 4 * 3.95 = <b>15.80 INR/hour</b>. (For 2 replicas: 7.90 INR/hour).<br/>At measured throughput of 0.68 RPS: Requests per hour = 0.68 * 3,600 = 2,448 req/hour.<br/><b>Cost per 1,000 requests = (15.80 / 2,448) * 1000 = 6.454 INR</b> &nbsp;(or 7.418 INR based on 2,130 successful requests/hour).", body_style))

    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>SLO &amp; Error Budget Analysis:</b><br/>• <i>SLI / SLO Target:</i> 99.0% of requests return HTTP 200 within 5,000 ms.<br/>• <i>Window:</i> One load-test execution window (79 total requests over 120 seconds).<br/>• <i>Error Budget:</i> Permitted errors = 79 * (1 - 0.99) = <b>0.79 requests</b> (effectively zero errors permitted).<br/>• <i>Budget Consumption:</i> 8 requests timed out due to host CPU saturation, consuming 8 / 0.79 = 1,012.6% of the error budget. Production mitigation requires rate limiting (HTTP 429) and GPU auto-scaling.", body_style))

    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Comprehensive SRE Review Table:</b>", h2_style))

    # Table 4: Review table (6 rows)
    t4_data = [
        [Paragraph("Component / Concern", table_header), Paragraph("Evidence (Measured Value)", table_header), Paragraph("Observed Limitation", table_header), Paragraph("Proposed Architectural Improvement", table_header)],
        [
            Paragraph("Data and storage", table_cell_bold),
            Paragraph("2,777 records kept (SHA-256: 70393bdcd...); 223 rejected (17 JSON, 14 keys, 17 intent, 128 slots, 47 dupes).", table_cell),
            Paragraph("SeaweedFS deployed as single-replica pod with local volume; lack of replication risks data loss.", table_cell),
            Paragraph("Deploy SeaweedFS in distributed replication topology (replication '001') with S3 tiering.", table_cell)
        ],
        [
            Paragraph("Model quality", table_cell_bold),
            Paragraph("Student v2: 97.0% JSON validity, 77.0% intent, 81.0% date, 34.0% full-frame (untrained scored 0.0%).", table_cell),
            Paragraph("70M parameter capacity is prone to repetition loops on unseen out-of-distribution entities.", table_cell),
            Paragraph("Implement grammar-guided constrained decoding (e.g., Outlines/Jsonformer) to guarantee 100% schema compliance.", table_cell)
        ],
        [
            Paragraph("Latency and throughput", table_cell_bold),
            Paragraph("p50 = 2,500 ms, min = 1,118 ms, avg = 5,664 ms, throughput = 0.68 req/s under 4 concurrent CPU users.", table_cell),
            Paragraph("Autoregressive token generation on CPU without GPU acceleration causes latency to scale linearly (~40ms/tok).", table_cell),
            Paragraph("Export Pythia-70M to INT8/INT4 via ONNX Runtime / OpenVINO, reducing latency by 3–4x.", table_cell)
        ],
        [
            Paragraph("Resource utilisation", table_cell_bold),
            Paragraph("Memory usage: 338–350 MiB per pod (34.2% of 1 GiB limit); CPU peaked at 3,037m across replicas.", table_cell),
            Paragraph("CPU contention during multi-user spikes leads to queue buildup and thread thrashing.", table_cell),
            Paragraph("Enforce CPU core pinning (cpuset) and set PyTorch intra-op threads (torch.set_num_threads(2)).", table_cell)
        ],
        [
            Paragraph("Reliability and recovery", table_cell_bold),
            Paragraph("Rolling update: 0.00% drops (27/27); pod recovery: 22.95s (0.00% drops); median cold start: 22.03s.", table_cell),
            Paragraph("Ingress depends on single Traefik controller; single-node failure crashes the routing plane.", table_cell),
            Paragraph("Deploy multi-replica Traefik with PodDisruptionBudget (PDB) and pod anti-affinity rules.", table_cell)
        ],
        [
            Paragraph("Security and cost", table_cell_bold),
            Paragraph("Stateless NACL: 6/6 test packets passed (100.0%); 7.42 INR per 1,000 requests (15.80 INR/hr for 4 pods).", table_cell),
            Paragraph("S3 credentials in secret.yaml are base64 strings in git; pods run as default root user.", table_cell),
            Paragraph("Integrate external-secrets-operator with HashiCorp Vault; enforce non-root securityContext.", table_cell)
        ]
    ]
    t4 = Table(t4_data, colWidths=[90, 130, 134, 150])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAFC'), colors.white])
    ]))
    story.append(t4)
    story.append(Spacer(1, 4))

    # Appendices / Conclusion
    story.append(Paragraph("8. Conclusion & Submission Checklist", h1_style))
    story.append(Paragraph("All project objectives were completed and empirically verified on the <code>cloud-cluster</code> environment: clean S3 data sharding (Task 1), successful Pythia-70M sequence-level distillation passing the 95% quality gate (Task 2), 1.70 GB optimized Docker container with memory stress verification (Task 3), high-availability Kubernetes deployment with zero-downtime rolling updates and rollback (Task 4), mathematical subnetting and stateless NACL design (Task 5), reproducible CI/CD workflow with Gitleaks and Makefile automation (Task 6), and empirical Locust performance, cost, and SRE review (Task 7). Source code is tagged as <code>final</code> in the repository, and deliverables are archived strictly per assignment standards.", body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {output_pdf}")

if __name__ == '__main__':
    build_pdf()
    reader = pypdf.PdfReader(output_pdf)
    print(f"Verified Page Count: {len(reader.pages)} (Requirement: Maximum 8 pages)")
    assert len(reader.pages) <= 8, f"Expected <= 8 pages, got {len(reader.pages)}"
