# Deployment Guide

This guide covers deploying the Pluggably LLM API Gateway on local servers and cloud platforms.

## Table of Contents
- [Local Server Deployment](#local-server-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Free Tier Options](#free-tier-options)
- [Paid Options](#paid-options)
- [Scaling Plan](#scaling-plan)

---

## Local Server Deployment

### Option 1: Docker (Recommended)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for local runtimes
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY llm_api/ ./llm_api/
COPY .env.example .env

ENV PYTHONPATH=/app
ENV LLM_API_HOST=0.0.0.0
ENV LLM_API_PORT=8080

EXPOSE 8080

CMD ["uvicorn", "llm_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Build and run:**
```bash
docker build -t llm-api .
docker run -d -p 8080:8080 \
  -e LLM_API_API_KEY=your-secret-key \
  -e LLM_API_OPENAI_API_KEY=sk-xxx \
  -v ./models:/app/models \
  --name llm-api \
  llm-api
```

**Docker Compose (with persistence):**
```yaml
version: '3.8'
services:
  llm-api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - LLM_API_API_KEY=${LLM_API_API_KEY}
      - LLM_API_OPENAI_API_KEY=${LLM_API_OPENAI_API_KEY}
      - LLM_API_PERSIST_STATE=true
    volumes:
      - ./models:/app/models
      - ./data:/app/data
    restart: unless-stopped
```

### Option 2: systemd Service

Create `/etc/systemd/system/llm-api.service`:
```ini
[Unit]
Description=LLM API Gateway
After=network.target

[Service]
Type=simple
User=llmapi
WorkingDirectory=/opt/llm-api
Environment="PATH=/opt/llm-api/.venv/bin"
EnvironmentFile=/opt/llm-api/.env
ExecStart=/opt/llm-api/.venv/bin/uvicorn llm_api.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-api
sudo systemctl start llm-api
```

### Option 3: Bare Metal with Nginx Reverse Proxy

**Nginx config (`/etc/nginx/sites-available/llm-api`):**
```nginx
upstream llm_api {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://llm_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

**Enable HTTPS with Let's Encrypt:**
```bash
sudo certbot --nginx -d api.yourdomain.com
```

---

## Cloud Deployment

### Environment Variables for Cloud

All cloud deployments need these environment variables:
```
LLM_API_API_KEY=your-secret-api-key
LLM_API_OPENAI_API_KEY=sk-xxx  # optional
LLM_API_ANTHROPIC_API_KEY=xxx  # optional
# ... other provider keys
```

---

## Free Tier Options

### 1. Railway (Recommended for Beginners)

**Pros:** Easy deployment, free tier includes $5/month credits, Git-based deploys  
**Cons:** Limited resources, may sleep after inactivity

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Add environment variables in Railway dashboard.

**Free tier limits:**
- 500 hours/month execution
- 512 MB RAM
- Sleeps after 10 min inactivity

---

### 2. Render

**Pros:** Generous free tier, auto-deploy from GitHub, easy setup  
**Cons:** Sleeps after 15 min, cold starts

1. Connect GitHub repo at [render.com](https://render.com)
2. Create new Web Service
3. Configure:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn llm_api.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables

**Free tier limits:**
- 750 hours/month
- 512 MB RAM
- Sleeps after 15 min inactivity

---

### 3. Fly.io

**Pros:** Global edge deployment, always-on free tier, good performance  
**Cons:** Slightly more complex setup

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch app
fly launch
fly secrets set LLM_API_API_KEY=your-key
fly deploy
```

**fly.toml:**
```toml
app = "llm-api-gateway"
primary_region = "sjc"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[env]
  LLM_API_HOST = "0.0.0.0"
  LLM_API_PORT = "8080"
```

**Free tier limits:**
- 3 shared-cpu-1x VMs
- 256 MB RAM each
- 3 GB persistent storage

---

### 4. Google Cloud Run (Free Tier)

**Pros:** Scales to zero, generous free tier, fully managed  
**Cons:** Cold starts, requires GCP account

```bash
# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT/llm-api

# Deploy
gcloud run deploy llm-api \
  --image gcr.io/YOUR_PROJECT/llm-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="LLM_API_API_KEY=your-key"
```

**Free tier limits:**
- 2 million requests/month
- 360,000 GB-seconds compute
- 180,000 vCPU-seconds

---

## Paid Options

### 1. DigitalOcean App Platform (Starting $5/month)

**Best for:** Simple production deployments

```bash
doctl apps create --spec .do/app.yaml
```

**app.yaml:**
```yaml
name: llm-api
services:
  - name: api
    source_dir: /
    github:
      repo: your-org/llm-api
      branch: main
    run_command: uvicorn llm_api.main:app --host 0.0.0.0 --port 8080
    envs:
      - key: LLM_API_API_KEY
        scope: RUN_TIME
        type: SECRET
    instance_size_slug: basic-xxs  # $5/month
    instance_count: 1
```

**Pricing:**
- Basic: $5/month (512 MB RAM, shared CPU)
- Pro: $12/month (1 GB RAM, dedicated CPU)

---

### 2. AWS (EC2 + ECS/Fargate)

**Best for:** Enterprise, existing AWS infrastructure

**EC2 (Simple):**
```bash
# Launch t3.micro ($8/month) or t3.small ($15/month)
# Use user data script:
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
docker run -d -p 80:8080 \
  -e LLM_API_API_KEY=xxx \
  your-registry/llm-api
```

**Fargate (Managed containers):**
- ~$15-30/month for minimal setup
- Auto-scaling included
- Use AWS Secrets Manager for keys

---

### 3. Hetzner Cloud (Best Value - EU)

**Best for:** Cost-conscious production, EU data residency

**Pricing:**
- CX11: €3.29/month (1 vCPU, 2 GB RAM)
- CX21: €5.39/month (2 vCPU, 4 GB RAM)
- CX31: €9.99/month (2 vCPU, 8 GB RAM) - **Recommended for local models**

```bash
# Install hcloud CLI
hcloud server create --name llm-api \
  --type cx21 \
  --image docker-ce \
  --ssh-key your-key
```

---

### 4. GPU Cloud (For Local Model Inference)

If running local models (llama.cpp, diffusers), you need GPU:

| Provider | GPU | Price | Notes |
|----------|-----|-------|-------|
| **RunPod** | RTX 3090 | $0.44/hr | Spot pricing available |
| **Lambda Labs** | A10 | $0.60/hr | Reserved instances cheaper |
| **Vast.ai** | Various | $0.15+/hr | Community GPUs, cheapest |
| **AWS** | T4 | $0.526/hr | p3.2xlarge for production |
| **GCP** | T4 | $0.35/hr | Preemptible pricing |

**Recommended for local inference:**
- Development: Vast.ai (cheapest)
- Production: Lambda Labs or RunPod (reliable)

---

## Scaling Plan

### Phase 1: Single Instance (1-100 users)

**Setup:**
- 1 container/VM
- 1-2 GB RAM
- No GPU (use commercial APIs)

**Cost:** $5-15/month

**Bottlenecks to watch:**
- Request latency > 2s
- Memory usage > 80%
- Error rate > 1%

---

### Phase 2: Horizontal Scaling (100-1,000 users)

**Setup:**
- 2-4 containers behind load balancer
- Shared Redis for rate limiting (optional)
- External DB for registry persistence (PostgreSQL)

**Architecture:**
```
                    ┌─────────────┐
                    │ Load Balancer│
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
     ┌──────────┐    ┌──────────┐    ┌──────────┐
     │ API (1)  │    │ API (2)  │    │ API (3)  │
     └────┬─────┘    └────┬─────┘    └────┬─────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                   ┌─────────────┐
                   │ PostgreSQL  │
                   └─────────────┘
```

**Changes needed:**
1. Add `LLM_API_PERSIST_STATE=true`
2. Configure shared PostgreSQL for model registry
3. Use Redis for distributed caching

**Cost:** $30-100/month

---

### Phase 3: High Availability (1,000-10,000 users)

**Setup:**
- Kubernetes cluster (EKS, GKE, or self-hosted)
- Auto-scaling pods (HPA)
- Multi-region deployment
- CDN for artifact caching

**Kubernetes deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: llm-api
  template:
    spec:
      containers:
        - name: api
          image: your-registry/llm-api:latest
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          envFrom:
            - secretRef:
                name: llm-api-secrets
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: llm-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Cost:** $200-500/month

---

### Phase 4: Enterprise (10,000+ users)

**Additional considerations:**
- Dedicated GPU nodes for local inference
- Rate limiting per API key
- Multi-tenant isolation
- Audit logging
- SLA monitoring

**Recommended stack:**
- AWS EKS or GKE Autopilot
- CloudFront/Cloud CDN for artifacts
- DataDog or Grafana Cloud for observability
- PagerDuty for alerting

**Cost:** $1,000+/month

---

## Performance Optimization Tips

### 1. Enable Response Caching
Add Redis cache for repeated prompts:
```python
# Future: Add cache layer for identical requests
```

### 2. Use Connection Pooling
Configure httpx connection pools for provider APIs.

### 3. Optimize Local Models
- Use quantized models (GGUF Q4_K_M)
- Enable GPU offloading when available
- Batch requests where possible

### 4. CDN for Artifacts
Store generated images/3D in S3 + CloudFront:
```
LLM_API_ARTIFACT_STORE=s3
LLM_API_ARTIFACT_BUCKET=your-bucket
```

---

## Security Checklist

- [ ] Use HTTPS in production (Let's Encrypt or cloud SSL)
- [ ] Rotate API keys regularly
- [ ] Never log provider API keys
- [ ] Enable rate limiting for public endpoints
- [ ] Use secrets management (Vault, AWS Secrets Manager)
- [ ] Regular dependency updates (`pip-audit`)
- [ ] Enable firewall (only expose 80/443)

---

## Monitoring Recommendations

| Tool | Use Case | Cost |
|------|----------|------|
| **Prometheus + Grafana** | Self-hosted metrics | Free |
| **Datadog** | Full observability | $15/host/month |
| **New Relic** | APM + traces | Free tier available |
| **Uptime Robot** | Health monitoring | Free |

Enable the built-in `/metrics` endpoint for Prometheus scraping.
