# 🚀 Indagata Microservices - Quick Start

## Prerequisites

- Docker & Docker Compose (>= 20.10)
- 4GB RAM minimum (8GB+ recommended)
- GPU (optional, recommended for Ollama)

## Setup

### 1. Clone and Navigate
```bash
cd /path/to/indagata
```

### 2. Create Environment File
```bash
cp .env.example .env
# Edit .env with your settings (SECRET_KEY, passwords, etc.)
```

### 3. Reorganize Code (One-time)

If migrating from monolith, follow [MICROSERVICES_GUIDE.md](./MICROSERVICES_GUIDE.md):

```bash
# Create service directories
mkdir -p services/{api-gateway,instrument-service,analysis-service,metadata-service,storage-service,visualization-service}

# Move your current backend code into appropriate services
# See MICROSERVICES_GUIDE.md for detailed mapping
```

### 4. Build Images
```bash
docker compose build
```

*First build: ~5-10 minutes (Python dependencies, base images)*

### 5. Start Services
```bash
docker compose up -d
```

### 6. Verify All Services Are Running
```bash
docker compose ps
```

Expected output:
```
CONTAINER ID   IMAGE                             STATUS
xyz            indagata_postgres                 Up (healthy)
xyz            indagata_ollama                   Up
xyz            indagata_chromadb                 Up
xyz            indagata_redis                    Up
xyz            indagata_api_gateway              Up
xyz            indagata_instrument_service       Up
xyz            indagata_analysis_service         Up
xyz            indagata_metadata_service         Up
xyz            indagata_storage_service          Up
xyz            indagata_visualization_service    Up
xyz            indagata_frontend                 Up
```

### 7. Initialize Database

```bash
# Run database migrations
docker compose exec postgres psql -U postgres -d indagata_db -f /migrations/01-create-tables.sql

# (Or if using Alembic)
docker compose exec api-gateway alembic upgrade head
```

### 8. Access the App

- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **API (ReDoc):** http://localhost:8000/redoc
- **Ollama API:** http://localhost:11434
- **ChromaDB API:** http://localhost:8001

---

## Common Commands

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api-gateway
docker compose logs -f analysis-service

# Last 100 lines, follow
docker compose logs --tail=100 -f postgres
```

### Enter Container

```bash
docker compose exec api-gateway bash
docker compose exec postgres psql -U postgres -d indagata_db
```

### Restart Service

```bash
docker compose restart api-gateway
docker compose restart analysis-service
```

### Stop All

```bash
docker compose down
```

### Rebuild After Code Changes

```bash
# Rebuild specific service
docker compose build api-gateway

# Rebuild all
docker compose build

# Then restart
docker compose up -d
```

### Clean Everything (⚠️ Removes volumes)

```bash
docker compose down -v
```

---

## Service Health Checks

### API Gateway
```bash
curl http://localhost:8000/health
```

### Individual Services
```bash
curl http://localhost:8001/health  # instrument-service
curl http://localhost:8002/health  # analysis-service
curl http://localhost:8003/health  # metadata-service
curl http://localhost:8004/health  # storage-service
curl http://localhost:8005/health  # visualization-service
```

### Database
```bash
docker compose exec postgres pg_isready -U postgres
```

### Ollama
```bash
curl http://localhost:11434/api/tags
```

---

## Troubleshooting

### PostgreSQL Won't Start
```bash
docker compose logs postgres
docker compose down -v postgres
docker compose up -d postgres
```

### Ollama Out of Memory
Add to `docker-compose.yml` under `ollama` service:
```yaml
deploy:
  resources:
    limits:
      memory: 8g
```

### Services Can't Find Each Other
- Check network: `docker network ls`
- Verify DNS: `docker compose exec api-gateway ping instrument-service`

### Port Already in Use
Change in `.env` or `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Host:Container
```

### Slow Builds
- Increase Docker resources (Memory, CPUs)
- Use `.dockerignore` to exclude unnecessary files
- Cache base images: `docker pull python:3.12-slim`

---

## Production Deployment

### 1. Update .env
```bash
DEBUG=false
APP_ENV=production
SECRET_KEY=<generate-secure-key>
POSTGRES_PASSWORD=<strong-password>
```

### 2. Use Docker Compose Override
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Create `docker-compose.prod.yml`:
```yaml
version: '3.9'

services:
  postgres:
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  api-gateway:
    restart: always
    environment:
      DEBUG: "false"

  # ... other services with restart: always
```

### 3. Use Kubernetes (Advanced)

```bash
# Convert compose to Kubernetes manifests
docker compose convert > k8s-manifest.yaml

# Apply to cluster
kubectl apply -f k8s-manifest.yaml
```

---

## Architecture Diagram

```
┌────────────────────────────────┐
│    Frontend (React/Vite)       │ :3000
│    http://localhost:3000       │
└────────────┬───────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│   API Gateway (FastAPI)                │ :8000
│   http://localhost:8000                │
│   - Authentication                     │
│   - Rate Limiting                      │
│   - Request Routing                    │
└────────────┬───────────────────────────┘
             │
   ┌─────────┼─────────┬──────────┬──────────┐
   │         │         │          │          │
   ↓         ↓         ↓          ↓          ↓
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ :8001│ │ :8002│ │ :8003│ │ :8004│ │ :8005│
│Instr │ │ Anal │ │ Meta │ │ Stor │ │ Vis  │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
   │         │       │        │        │
   └─────────┼───────┼────────┼────────┘
             │       │        │
             ↓       ↓        ↓
        ┌──────────────────────────────┐
        │   PostgreSQL             │
        │   :5432                      │
        └──────────────────────────────┘

        ┌──────────────────────────────┐
        │   Ollama (LLM)               │
        │   :11434                     │
        └──────────────────────────────┘

        ┌──────────────────────────────┐
        │   ChromaDB (Vector DB)       │
        │   :8001                      │
        └──────────────────────────────┘

        ┌──────────────────────────────┐
        │   Redis (Cache)              │
        │   :6379                      │
        └──────────────────────────────┘
```

---

## Next Steps

- [ ] Reorganize code into services (see MICROSERVICES_GUIDE.md)
- [ ] Copy `requirements.txt` from each service (or create new ones per service)
- [ ] Update service `main.py` files with actual business logic
- [ ] Test locally with `docker compose up`
- [ ] Set up CI/CD (GitHub Actions, GitLab CI, etc.)
- [ ] Deploy to Docker Swarm or Kubernetes
- [ ] Set up monitoring (Prometheus, Grafana, ELK stack)

---

## Support

- Docker Docs: https://docs.docker.com
- Compose: https://docs.docker.com/compose
- FastAPI: https://fastapi.tiangolo.com
- PostgreSQL: https://www.postgresql.org/docs

---

**Happy containerizing! 🐳**
