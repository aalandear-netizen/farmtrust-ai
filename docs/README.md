# FarmTrust AI

**AI-powered agricultural trust scoring and financial inclusion platform.**

FarmTrust AI bridges the credit gap for smallholder farmers in India by computing a data-driven trust score using satellite imagery, weather data, market prices, and repayment history — enabling banks, insurers, and government bodies to make informed lending decisions.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                │
│   React Native App (iOS/Android)    Next.js Web Dashboard (Bank)    │
└─────────────────┬───────────────────────────────┬───────────────────┘
                  │ HTTPS / JWT                    │ HTTPS / JWT
┌─────────────────▼───────────────────────────────▼───────────────────┐
│                   FastAPI Gateway (port 8000)                        │
│  Auth · Farmer · TrustScore · Loan · Insurance · Market · Gov · Audit│
└──────┬──────────────────────────────┬───────────────────────────────┘
       │ SQLAlchemy (async)            │ HTTP
┌──────▼──────┐  ┌──────────────┐  ┌──▼──────────────────────────────┐
│  PostgreSQL  │  │    Redis     │  │   ML Service (port 8001)         │
│  + PostGIS  │  │  (cache)     │  │   Temporal Fusion Transformer    │
│  + Timescale│  └──────────────┘  └─────────────────────────────────┘
└─────────────┘
       │
┌──────▼──────┐
│    Kafka    │  (audit, notifications, trust-score-updates)
└─────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker ≥ 24 and Docker Compose ≥ 2
- Python 3.11+
- Node.js 20+

### 1. Clone and configure

```bash
git clone https://github.com/aalandear-netizen/farmtrust-ai.git
cd farmtrust-ai
cp .env.example .env    # edit with your secrets
```

### 2. Start all services

```bash
docker compose up -d
```

### 3. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Access the services

| Service | URL |
|---|---|
| API docs (Swagger) | http://localhost:8000/docs |
| Web dashboard | http://localhost:3000 |
| Grafana monitoring | http://localhost:3001 (admin/farmtrust) |
| Prometheus | http://localhost:9090 |

---

## 📁 Project Structure

```
farmtrust-ai/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py           # Application entry point
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── database.py       # SQLAlchemy async engine
│   │   ├── models/           # ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── routers/          # 8 API service modules
│   │   ├── middleware/       # Auth (JWT)
│   │   └── utils/            # Redis cache helpers
│   ├── alembic/              # Database migrations
│   ├── tests/                # Pytest test suite
│   └── Dockerfile
│
├── ml/                       # AI/ML pipeline
│   ├── models/
│   │   └── tft.py            # Temporal Fusion Transformer
│   ├── features/
│   │   └── feature_engineering.py
│   ├── serving/
│   │   └── serve.py          # FastAPI ML microservice
│   └── tests/
│
├── mobile/                   # React Native (Expo) app
│   └── src/
│       ├── components/       # TrustGauge, etc.
│       ├── screens/          # DashboardScreen, etc.
│       ├── services/         # API client
│       └── store/            # Zustand state
│
├── web/                      # Next.js bank dashboard
│   └── src/
│       ├── pages/            # Next.js pages
│       ├── components/       # Reusable UI
│       └── services/         # API client
│
├── infrastructure/
│   ├── k8s/                  # Kubernetes manifests
│   ├── scripts/              # DB init SQL
│   └── prometheus.yml
│
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions CI/CD
│
├── docker-compose.yml
└── docs/
```

---

## 🔑 API Services

| Service | Prefix | Description |
|---|---|---|
| Auth | `/api/v1/auth` | JWT authentication |
| Farmers | `/api/v1/farmers` | Farmer CRUD |
| Trust Scores | `/api/v1/trust-scores` | AI scoring |
| Loans | `/api/v1/loans` | Loan applications |
| Insurance | `/api/v1/insurance` | Crop insurance (PMFBY) |
| Market | `/api/v1/market` | Mandi prices + listings |
| Government | `/api/v1/government` | Schemes & subsidies |
| Audit | `/api/v1/audit` | Compliance logs |
| Notifications | `/api/v1/notifications` | Push/in-app notifications |

---

## 🤖 Trust Score Model

The trust score is computed by a **Temporal Fusion Transformer (TFT)** that considers:

| Data Source | Features |
|---|---|
| Satellite (Sentinel-2) | NDVI, EVI, soil moisture, crop health |
| Weather API | Temperature, rainfall, humidity, anomalies |
| Market Data | Mandi prices, volatility, trends |
| Financial History | Loan repayments, KCC utilisation |
| Farm Profile | Size, crop diversity, KYC status |

Scores range from **0–100** and map to grades **AAA** (≥90) → **D** (<30), similar to credit rating agencies.

---

## 🧪 Running Tests

```bash
# Backend
cd backend && pip install -r requirements.txt
pytest tests/ -v --cov=app

# ML
cd ml && pip install torch numpy pandas scikit-learn pytest
pytest tests/ -v

# Web
cd web && npm ci
npm test
```

---

## 🔧 Environment Variables

See `.env.example` for all required variables. Key settings:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing secret (≥32 chars) |
| `ML_SERVICE_URL` | URL of ML inference microservice |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers |

---

## 📄 License

MIT License – see `LICENSE` for details.
