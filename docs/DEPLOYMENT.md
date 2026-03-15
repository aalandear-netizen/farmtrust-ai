# Deployment Guide

## Docker Compose (Development / Staging)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your secrets

# 2. Start all services
docker compose up -d --build

# 3. Run migrations
docker compose exec api alembic upgrade head

# 4. (Optional) Load sample data
docker compose exec api python -m scripts.seed

# 5. Verify
curl http://localhost:8000/health
```

## Kubernetes (Production)

### Prerequisites
- `kubectl` configured for your cluster
- Container registry access (GHCR or DockerHub)

### 1. Build and push images

```bash
# API
docker build -t ghcr.io/YOUR_ORG/farmtrust-api:latest ./backend
docker push ghcr.io/YOUR_ORG/farmtrust-api:latest

# ML service
docker build -t ghcr.io/YOUR_ORG/farmtrust-ml:latest ./ml
docker push ghcr.io/YOUR_ORG/farmtrust-ml:latest

# Web
docker build -t ghcr.io/YOUR_ORG/farmtrust-web:latest ./web
docker push ghcr.io/YOUR_ORG/farmtrust-web:latest
```

### 2. Create namespace and secrets

```bash
kubectl create namespace farmtrust

kubectl create secret generic farmtrust-secrets \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=DATABASE_URL='postgresql+asyncpg://...' \
  --from-literal=REDIS_URL='redis://...' \
  -n farmtrust
```

### 3. Deploy

```bash
kubectl apply -f infrastructure/k8s/manifests.yaml
```

### 4. Verify

```bash
kubectl get pods -n farmtrust
kubectl get svc -n farmtrust
kubectl logs -f deployment/farmtrust-api -n farmtrust
```

## CI/CD with GitHub Actions

The CI pipeline (`.github/workflows/ci.yml`) automatically:
1. Runs backend tests + coverage on every PR
2. Runs ML tests and web tests
3. On merge to `main`: builds Docker images and pushes to GHCR
4. Deploys to staging environment

### Required Secrets

| Secret | Description |
|---|---|
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions |
| `KUBE_CONFIG_STAGING` | Base64-encoded kubeconfig for staging cluster |

## Environment Configuration

| Variable | Development | Production |
|---|---|---|
| `DEBUG` | `true` | `false` |
| `DATABASE_URL` | `postgresql+asyncpg://farmtrust:farmtrust@localhost/farmtrust` | Use managed DB (RDS/Cloud SQL) |
| `SECRET_KEY` | `changeme-dev` | Random 64-char string |
| `REDIS_URL` | `redis://localhost:6379/0` | Managed Redis (ElastiCache) |

## Health Checks

| Service | Endpoint |
|---|---|
| API | `GET /health` |
| ML Service | `GET /health` |
| Prometheus | `GET /-/healthy` |
