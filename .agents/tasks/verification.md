# Verification — indagata backend microservices

All work was performed in the MAIN repo tree
`c:\Users\yarel\Documents\indagata\indagata` on branch
`refactorizacion-microservicios`, as DECIDED in `.agents/tasks/plan.md`
(Option B). `git worktree list` confirms there is no separate checkout —
`.worktrees/fix-microservices` holds only `.agents/`; the real
`services/`, `shared/`, `docker-compose.yml`, and
`infrastructure/docker/` live in the main tree. All compose commands were
run from the main tree root with `-f docker-compose.yml`. Infra
(postgres, redis, chromadb, ollama) and api-gateway were left running.

`shared/` was NOT modified. Every fix changed service
code/requirements/Dockerfiles to match `shared`.

Final `docker compose -f docker-compose.yml ps` (all six services Up, none restarting):

```
indagata_analysis_service       | running | Up | 0.0.0.0:8002->8002/tcp
indagata_api_gateway            | running | Up (healthy) | 0.0.0.0:8000->8000/tcp
indagata_instrument_service     | running | Up | 0.0.0.0:8001->8001/tcp
indagata_metadata_service       | running | Up | 0.0.0.0:8003->8003/tcp
indagata_storage_service        | running | Up | 0.0.0.0:8004->8004/tcp
indagata_visualization_service  | running | Up | 0.0.0.0:8005->8005/tcp
(infra) indagata_postgres (healthy), indagata_redis (healthy),
        indagata_chromadb, indagata_ollama — all Up, untouched
```

Health responses (via `Invoke-WebRequest http://localhost:<port>/health`):

```
8000 -> 200 {"status":"ok","service":"api-gateway"}
8001 -> 200 {"status":"ok","service":"instrument-service"}
8002 -> 200 {"status":"ok","service":"analysis-service"}
8003 -> 200 {"status":"ok","service":"metadata-service","version":"1.0.0"}
8004 -> 200 {"status":"ok","service":"storage-service"}
8005 -> 200 {"status":"ok","service":"visualization-service"}
```

---

## 1. api-gateway (reference, no edits)

Already built and healthy on 8000; used as the known-good pattern. Not
modified. `ps` shows `indagata_api_gateway ... Up (healthy)`;
`/health` -> `{"status":"ok","service":"api-gateway"}`.

## 2. instrument-service — port 8001

**Was wrong:** code imports `from shared.auth import ...`;
`shared/auth/jwt_handler.py` does `from jose import ...` and
`shared/auth/password.py` uses `passlib`, but the service
`requirements.txt` pinned neither -> container crash-looped
(`Restarting`, `ModuleNotFoundError: No module named 'jose'`).

**Changed:** `services/instrument-service/requirements.txt` — added, to
match api-gateway:
- `python-jose[cryptography]==3.3.0`
- `passlib[bcrypt]==1.7.4`
- `bcrypt==4.0.1`

No code change. Dockerfile already had the `/usr/local/bin` COPY.

**Commands:**
```
docker compose -f docker-compose.yml build instrument-service
docker compose -f docker-compose.yml up -d instrument-service
docker compose -f docker-compose.yml ps
docker compose -f docker-compose.yml logs instrument-service --tail 20
```
**Build:** installed `python-jose-3.3.0 passlib-1.7.4 bcrypt-4.0.1`
(+ cryptography/ecdsa/rsa) — `Successfully installed ...`.
**Key log lines:**
```
🚀 instrument-service listo. RAW_PATH=/app/storage/raw
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```
**Final status:** running (Up). `/health` -> `200 {"status":"ok","service":"instrument-service"}`.

## 3. metadata-service — port 8003

**Was wrong:** three issues:
(a) `main.py` lifespan did `from db.database import init_db` (bare
top-level `db`, no such package) -> `No module named 'db'`;
(b) `routers/metadata.py` did
`from shared.schemas.responses import DublinCoreMetadata, InstrumentResponse`
— `shared/schemas/responses.py` does not exist and the names were
imported-but-unused;
(c) `email-validator is not installed` warning from loading
`shared.schemas.usuario` (pydantic `EmailStr`).
Also a stale EMPTY `services/metadata-service/shared/` folder (untracked)
existed alongside the real `/app/shared`.

**Changed:**
- `services/metadata-service/main.py`: replaced the misleading
  `sys.path.insert(0, .../shared)` with the api-gateway pattern (prepend
  REPO ROOT only when `./shared` is absent); changed the init import to
  `from shared.db.database import init_db` (that module re-exports
  `init_db` from `shared.db.session`).
- `services/metadata-service/routers/metadata.py`: removed the
  nonexistent `from shared.schemas.responses import ...` line (kept
  `from shared.db.database import get_db`).
- `services/metadata-service/requirements.txt`: added
  `email-validator==2.1.0` (matches api-gateway).
- Removed the empty stale `services/metadata-service/shared/` directory
  (it was not tracked by git and contained no files) so the service relies
  solely on the root `shared/` copied to `/app/shared`.

**Commands:**
```
docker compose -f docker-compose.yml build metadata-service
docker compose -f docker-compose.yml up -d metadata-service
docker compose -f docker-compose.yml logs metadata-service --tail 25
docker compose -f docker-compose.yml logs metadata-service | Select-String "routers registered|No module|email-validator|Failed to import|Traceback"
```
**Key log lines:**
```
main - INFO - ✅ All routers registered
main - INFO - ✅ Database initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8003 (Press CTRL+C to quit)
```
No `No module named 'db'`, no `email-validator is not installed`, no
`Failed to import routers`, no traceback.
**Final status:** running (Up). `/health` ->
`200 {"status":"ok","service":"metadata-service","version":"1.0.0"}`.

## 4. analysis-service — port 8002

**Was wrong:** `requirements.txt` pinned `langchain==0.3.0`,
`langchain-ollama==0.1.0`, `langchain-community==0.1.0` — the 0.1.0
community/ollama packages are incompatible with langchain 0.3.x, so
`pip install` could not resolve. None of the three is imported anywhere
in `app/**` (code uses only `sentence_transformers` and `chromadb`, both
lazy).

**Changed:** `services/analysis-service/requirements.txt` — removed the
three unused langchain lines. Kept the imported, compatible pins:
`chromadb==0.5.0` and `sentence-transformers==3.0.0` (plus the existing
fastapi/uvicorn/sqlalchemy/psycopg/pydantic stack). Dockerfile already
had `g++`, `libgomp1`, and the `/usr/local/bin` COPY.

**Commands:**
```
docker compose -f docker-compose.yml build analysis-service   # ran to completion as a background job
docker compose -f docker-compose.yml up -d analysis-service
docker compose -f docker-compose.yml ps analysis-service
docker compose -f docker-compose.yml logs analysis-service --tail 50
```
**Build:** completed with NO pip resolver/conflict error (the removed
langchain lines were the only incompatibility). Final image
`indagata-analysis-service:latest` ~9.94GB (includes torch via
sentence-transformers). The embedding model
(`paraphrase-multilingual-mpnet-base-v2`) is loaded lazily on first
vectorization call, so startup is immediate and clean.
**Key log lines:**
```
🚀 analysis-service listo. Chroma=chromadb:8000 modelo=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8002 (Press CTRL+C to quit)
```
**Final status:** running (Up). `/health` -> `200 {"status":"ok","service":"analysis-service"}`.

## 5. storage-service — port 8004

**Was wrong:** no `main.py` existed, but
`Dockerfile.storage-service` ends with `CMD ["uvicorn", "main:app", ...]`
-> could not start. The Dockerfile was ALSO missing
`COPY --from=base /usr/local/bin /usr/local/bin` (so `uvicorn` would be
absent from the final image). `requirements.txt` pinned
chromadb/langchain-chroma/sentence-transformers, none used by a stub and
`langchain-chroma==0.1.0` risks conflict with `chromadb==0.5.0`.

**Changed:**
- Created `services/storage-service/main.py`: a health-only FastAPI stub
  in the api-gateway style — `app = FastAPI(...)`, `GET /health` ->
  `{"status":"ok","service":"storage-service"}`, clearly marked as a STUB
  pending real implementation. No business logic.
- `infrastructure/docker/Dockerfile.storage-service`: added
  `COPY --from=base /usr/local/bin /usr/local/bin` right after the
  site-packages COPY.
- `services/storage-service/requirements.txt`: trimmed to the minimal
  stub set `fastapi==0.115.6`, `uvicorn[standard]==0.30.0`,
  `pydantic==2.9.0`, `pydantic-settings==2.5.0`, `python-dotenv==1.0.1`.

**Commands:**
```
docker compose -f docker-compose.yml build storage-service
docker compose -f docker-compose.yml up -d storage-service
docker compose -f docker-compose.yml logs storage-service --tail 12
```
**Key log lines:**
```
🚀 storage-service listo (stub health-only).
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8004 (Press CTRL+C to quit)
```
**Final status:** running (Up). `/health` -> `200 {"status":"ok","service":"storage-service"}`.

## 6. visualization-service — port 8005

**Was wrong:** same as storage — no `main.py` but
`CMD ["uvicorn", "main:app", ...]`. `requirements.txt` also pinned
`langchain==0.3.0` + `langchain-community==0.1.0` (incompatible, breaks
the build) plus pandas/sqlalchemy/psycopg, none imported by a stub.

**Changed:**
- Created `services/visualization-service/main.py`: health-only FastAPI
  stub mirroring item 5 — `GET /health` ->
  `{"status":"ok","service":"visualization-service"}`, clearly marked as
  a STUB. No business logic.
- `services/visualization-service/requirements.txt`: trimmed to the
  minimal stub set (`fastapi==0.115.6`, `uvicorn[standard]==0.30.0`,
  `pydantic==2.9.0`, `pydantic-settings==2.5.0`, `python-dotenv==1.0.1`);
  dropped langchain/langchain-community/pandas/sqlalchemy/psycopg.
- Dockerfile already had the `/usr/local/bin` COPY — no change.

**Commands:**
```
docker compose -f docker-compose.yml build visualization-service
docker compose -f docker-compose.yml up -d visualization-service
docker compose -f docker-compose.yml logs visualization-service --tail 12
```
**Key log lines:**
```
🚀 visualization-service listo (stub health-only).
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8005 (Press CTRL+C to quit)
```
**Final status:** running (Up). `/health` -> `200 {"status":"ok","service":"visualization-service"}`.

## 7. Full-stack integration

All six service containers Up simultaneously with the four infra
containers; none restarting (see the `ps` table above). Each `/health`
returns its `{"status":"ok","service":...}`. `frontend` is out of scope
and was not built.

## Notes

- Already-applied fixes kept: `psycopg[binary]==3.2.3` across
  requirements; `COPY --from=base /usr/local/bin /usr/local/bin` in all
  five Python Dockerfiles (added the one missing from storage-service).
- No `shared/` edit was required.
- Requirement trims (analysis/storage/visualization) removed only deps no
  current code imports. If langchain is added later, use a mutually
  compatible 0.3.x set (langchain 0.3.x + langchain-community 0.3.x +
  langchain-ollama 0.2.x); the 0.1.x pins were the incompatibility.
- Throwaway artifact `.agents/tasks/analysis_build.log` (background build
  log) was deleted after verification.
