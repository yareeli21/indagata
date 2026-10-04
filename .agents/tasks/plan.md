# Implementation Plan — Fix indagata backend microservices

Goal: every buildable service (api-gateway + the five others) builds, starts, and stays healthy under Docker Compose on ports 8000–8005.

## Working tree (DECIDED — Option B)

Operate DIRECTLY in the MAIN repo working tree:

```
c:\Users\yarel\Documents\indagata\indagata        (branch: refactorizacion-microservicios)
```

This branch holds the real microservices code (`services/`, `shared/`, `infrastructure/docker/`, `docker-compose.yml`) plus today's already-applied fixes (psycopg `3.2.3` in all requirements.txt; `COPY --from=base /usr/local/bin /usr/local/bin` in all 5 Python Dockerfiles) as uncommitted changes. Do NOT touch the `.worktrees/fix-microservices` worktree — it is on the old monolith layout and is being discarded. Do NOT reset/move branch history. At finalize, keep the fixes on `refactorizacion-microservicios`; do NOT rebase/merge onto `main`.

All compose commands run from the main tree root with the microservices compose file (never `docker-compose.yaml`):

```
docker compose -f docker-compose.yml <cmd>
```

Infra (`indagata_postgres`, redis, chromadb, ollama) and api-gateway are already UP/healthy — leave them running; do not recreate infra volumes. Rebuild api-gateway only if a `shared/` change forces it (this plan requires no `shared/` change).

## Confirmed conventions (from the known-good api-gateway)

- Shared-import convention: ALWAYS absolute `from shared.xxx import ...`. `shared/` is COPY'd to `/app/shared` and WORKDIR is `/app`, so `shared` resolves as a top-level package in the container. For local runs each `main.py` prepends the repo root to `sys.path` only when `./shared` is absent. There is NO top-level `db`/`models`/`schemas` package — importing those bare names is the bug.
- Each service installs its OWN `services/<name>/requirements.txt`; `shared/requirements.txt` is NOT installed by the service Dockerfiles. So any service whose code imports `shared.auth` must itself pin `python-jose[cryptography]` and `passlib[bcrypt]`/`bcrypt`, and any service importing `shared.schemas` must pin `email-validator` (`shared/schemas/usuario.py` uses pydantic `EmailStr`).
- api-gateway reference pins (match these): `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1`, `email-validator==2.1.0`, `psycopg[binary]==3.2.3`, `fastapi==0.115.6`, `uvicorn[standard]==0.30.0`, `pydantic==2.9.0`.
- Dockerfile pattern: multi-stage; the final stage must contain BOTH `COPY --from=base /usr/local/lib/python3.12/site-packages ...` AND `COPY --from=base /usr/local/bin /usr/local/bin`.
- Health endpoint shape across services: `GET /health` → `{"status": "ok", "service": "<name>"}`.

## Do NOT touch `shared/`

`shared/` is intended-correct (prior workflow approved it; see `shared/.agents/tasks/review.json`). Every fix below changes SERVICE code/requirements/Dockerfiles to match `shared`, never the reverse. No `shared/` edit is required.

---

- [ ] 1. api-gateway — regression baseline (no edits).
      Known-good reference; do not modify. Confirm it still builds/runs before changing the others.
      Files: none.
      Verify: `docker compose -f docker-compose.yml up -d --build api-gateway`; `docker compose -f docker-compose.yml ps` shows `indagata_api_gateway` healthy; `curl http://localhost:8000/health` → `{"status":"ok","service":"api-gateway"}`.

- [ ] 2. instrument-service — add the auth deps that `shared.auth` requires.
      Root cause (confirmed): `services/instrument-service/app/dependencies.py`, `app/services/delete_service.py`, `app/routers/{upload,delete}.py` import `from shared.auth import ...`; `shared/auth/jwt_handler.py` does `from jose import ...` and `shared/auth/password.py` uses `passlib`. The service `requirements.txt` pins neither → container crash-loops with `ModuleNotFoundError: No module named 'jose'`. Add `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1` (match api-gateway). No code change — imports already correct. `Dockerfile.instrument-service` already has the `/usr/local/bin` COPY.
      Files: `services/instrument-service/requirements.txt`
      Verify: `docker compose -f docker-compose.yml up -d --build instrument-service`; `docker compose -f docker-compose.yml logs --tail=50 instrument-service` shows Uvicorn startup, no `ModuleNotFoundError`; `ps` shows it Up; `curl http://localhost:8001/health` → `{"status":"ok","service":"instrument-service"}`.

- [ ] 3. metadata-service — fix broken imports and add email-validator.
      Three confirmed root causes:
      (a) `services/metadata-service/main.py`: `from db.database import init_db` (bare top-level `db`) → `from shared.db.database import init_db` (that module re-exports `init_db` from `shared.db.session`). Remove the misleading `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))` line (it points INSIDE `shared/`, which is what makes bare `db`/`routers` look importable locally yet fail in Docker). If a local-run fallback is wanted, mirror api-gateway: prepend the REPO ROOT to `sys.path` only when `./shared` is absent.
      (b) `services/metadata-service/routers/metadata.py`: `from shared.schemas.responses import DublinCoreMetadata, InstrumentResponse` — `shared/schemas/responses.py` does NOT exist and the names are imported-but-unused (endpoints use `dict`/`response_model=dict`). Remove that import line.
      (c) The `email-validator is not installed` warning comes from loading `shared.schemas` → `shared/schemas/usuario.py` (`EmailStr`). Add `email-validator==2.1.0` (match api-gateway).
      Notes: `services/metadata-service/models.py` is empty and not on any import path (routers import `services.dc_manager`/`services.enrichment_engine`, which use `shared.models.*` correctly) — leave or delete, not required. No `services/metadata-service/shared/` duplicate folder exists in this tree — do not create one.
      Files: `services/metadata-service/main.py`, `services/metadata-service/routers/metadata.py`, `services/metadata-service/requirements.txt`
      Verify: `docker compose -f docker-compose.yml up -d --build metadata-service`; `docker compose -f docker-compose.yml logs --tail=60 metadata-service` shows `✅ Database initialized`, `✅ All routers registered`, no `No module named 'db'`, no `email-validator is not installed`; `ps` shows it Up; `curl http://localhost:8003/health` → `{"status":"ok","service":"metadata-service","version":"1.0.0"}`.

- [ ] 4. analysis-service — remove the unused, incompatible langchain stack.
      Root cause (confirmed by grep over `services/analysis-service/app/**`): code imports ONLY `sentence_transformers` (lazy, `app/vectorization/core/embeddings.py`) and `chromadb` (lazy, `app/vectorization/core/chroma_client.py`). No `langchain`/`langchain_ollama`/`langchain_community` import anywhere. The pinned `langchain==0.3.0`, `langchain-ollama==0.1.0`, `langchain-community==0.1.0` are unused and unsatisfiable together (community/ollama 0.1.0 predate and conflict with langchain 0.3.x), breaking `pip install`. Fix: DELETE those three lines; keep `chromadb==0.5.0` and `sentence-transformers==3.0.0` (both imported). `Dockerfile.analysis-service` already has `g++`, `libgomp1`, and the `/usr/local/bin` COPY.
      Future note: if real langchain usage is added later, the compatible set is `langchain==0.3.x` + `langchain-community==0.3.x` + `langchain-ollama==0.2.x` (0.1.x are NOT compatible with 0.3). Not needed now.
      Files: `services/analysis-service/requirements.txt`
      Verify (build is the real test): `docker compose -f docker-compose.yml build analysis-service` completes with no pip resolver/conflict error. Then `docker compose -f docker-compose.yml up -d analysis-service`; allow several minutes on first start (sentence-transformers downloads the embedding model, several hundred MB — expected). `docker compose -f docker-compose.yml logs --tail=80 analysis-service` shows `🚀 analysis-service listo` and Uvicorn serving; `curl http://localhost:8002/health` → `{"status":"ok","service":"analysis-service"}`.

- [ ] 5. storage-service — create a minimal real FastAPI app and fix its Dockerfile.
      Root cause: ONLY `requirements.txt` (no `main.py`) but `Dockerfile.storage-service` ends with `CMD ["uvicorn", "main:app", ...]` → cannot start. Create `services/storage-service/main.py` in the style of `services/api-gateway/main.py`: a `FastAPI(...)` instance named `app`, `GET /health` → `{"status": "ok", "service": "storage-service"}`, with a docstring clearly marking it a STUB to be fleshed out. No business logic. Also fix `infrastructure/docker/Dockerfile.storage-service`: it is MISSING `COPY --from=base /usr/local/bin /usr/local/bin` (present in all other service Dockerfiles) — add it right after the site-packages COPY so `uvicorn` exists in the final image. Trim `services/storage-service/requirements.txt` (currently chromadb/langchain-chroma/sentence-transformers, none used by a stub and langchain-chroma==0.1.0 may conflict with chromadb==0.5.0) to the minimal stub set: `fastapi==0.115.6`, `uvicorn[standard]==0.30.0`, `pydantic==2.9.0`, `pydantic-settings==2.5.0`, `python-dotenv==1.0.1`. (Service does not import `shared`.)
      Files: create `services/storage-service/main.py`; edit `infrastructure/docker/Dockerfile.storage-service`; edit `services/storage-service/requirements.txt`
      Verify: `docker compose -f docker-compose.yml up -d --build storage-service`; `ps` shows `indagata_storage_service` Up; `curl http://localhost:8004/health` → `{"status":"ok","service":"storage-service"}`; logs show Uvicorn on 8004, no import error.

- [ ] 6. visualization-service — create a minimal real FastAPI app and clean requirements.
      Root cause: same as storage — ONLY `requirements.txt` (no `main.py`) but `CMD ["uvicorn", "main:app", ...]`. Its `requirements.txt` also pins `langchain==0.3.0` + `langchain-community==0.1.0` (incompatible) which breaks the build, and nothing imports them. Create `services/visualization-service/main.py` mirroring item 5 (health → `{"status":"ok","service":"visualization-service"}`, clearly marked STUB). Trim `requirements.txt` to the minimal stub set (`fastapi==0.115.6`, `uvicorn[standard]==0.30.0`, `pydantic==2.9.0`, `pydantic-settings==2.5.0`, `python-dotenv==1.0.1`); drop `langchain`, `langchain-community`, `pandas`, `sqlalchemy`, `psycopg` until real code needs them. `Dockerfile.visualization-service` already has the `/usr/local/bin` COPY — no Dockerfile change.
      Files: create `services/visualization-service/main.py`; edit `services/visualization-service/requirements.txt`
      Verify: `docker compose -f docker-compose.yml up -d --build visualization-service`; `ps` shows `indagata_visualization_service` Up; `curl http://localhost:8005/health` → `{"status":"ok","service":"visualization-service"}`; logs show Uvicorn on 8005, no import/resolver error.

- [ ] 7. Full-stack integration verification.
      Bring up all buildable services together; confirm none crash-loop. Infra stays as-is.
      Files: none.
      Verify: from the main tree root, `docker compose -f docker-compose.yml up -d --build api-gateway instrument-service analysis-service metadata-service storage-service visualization-service`; wait for analysis-service model download; `docker compose -f docker-compose.yml ps` shows all six service containers Up (api-gateway healthy). `curl` 8000,8001,8002,8003,8004,8005 `/health` — each returns its `{"status":"ok","service":...}`. Spot-check `docker compose -f docker-compose.yml logs --tail=30 <svc>` per service for no repeating restart/traceback. `frontend` is OUT of scope — do not build or block on it.

## Finalize guidance

Leave the fixes on branch `refactorizacion-microservicios` (committed or uncommitted per the finalize step's choice). Do NOT rebase or merge onto `main`. If the finalize step is written to rebase onto `main`, SKIP that — the user wants the fixes to stay on `refactorizacion-microservicios`.

## Notes / assumptions

- `frontend` is outside scope (backend microservices only).
- No `shared/` edits needed; every fix is in service requirements/code/Dockerfiles.
- Requirement trims (analysis/storage/visualization) remove only deps no current code imports; re-add with compatible pins if later features need them (langchain 0.3.x line per item 4).
- Keep the already-applied fixes (psycopg 3.2.3 everywhere; `/usr/local/bin` COPY in Dockerfiles) — item 5 only ADDS the one missing from storage.
