# Six backend microservices build and run under Docker Compose

The change makes all six indagata backend services (api-gateway, instrument-service, analysis-service, metadata-service, storage-service, visualization-service) build and stay up under `docker-compose.yml`, fixing root causes rather than symptoms. The failures were distinct per service — a missing auth dependency crash-loop, bare-package imports that only resolved locally, an unsatisfiable langchain pin set, and two services with no `main.py` at all — and each is addressed at its source: service `requirements.txt`, service `main.py`, and Dockerfiles, with `shared/` logic left untouched. The work was committed as `52c0040` on `refactorizacion-microservicios` and verified by the coder with build output, `compose ps`, logs, and `/health` responses recorded in `verification.md`.

Watch for: (1) **confirmed** — the commit edits `shared/requirements.txt` (psycopg `3.2.0 → 3.2.3`), a one-line pin bump, even though the plan said "do NOT touch shared/" and the verification note claims "shared/ was NOT modified"; it is a consistency bump, not a logic change, and `shared/requirements.txt` is not installed by the service Dockerfiles, so it is non-blocking. (2) **confirmed** — storage-service and visualization-service are health-only stubs by design; they start and answer `/health` but implement no business logic, which is the agreed scope here.

**Verdict**: APPROVED

## High-level view

The crash-looping services were fixed by aligning each service's own `requirements.txt` with what the `shared` layer actually imports, not by editing `shared`. instrument-service pulls `shared.auth`, which needs `jose`/`passlib`, so those pins were added to match api-gateway. metadata-service had two broken imports — a bare `from db.database` and a `from shared.schemas.responses` that points at a nonexistent module — both corrected, plus `email-validator` added for the `EmailStr` path, and a stale empty `services/metadata-service/shared/` directory removed so only the real `/app/shared` is in play.

analysis-service's build break was an unsatisfiable langchain pin set (`langchain 0.3.0` with `langchain-community/ollama 0.1.0`). Rather than find a compatible 0.3.x trio, the coder removed all three because nothing in `app/**` imports langchain; the only vector deps used are `chromadb` and `sentence-transformers`, which stay. This is the correct root-cause fix, and it deviates from the literal checklist item (which anticipated a compatible langchain set) in the right direction.

storage-service and visualization-service had no `main.py` despite a `CMD uvicorn main:app`; both now ship a minimal health-only FastAPI stub in the api-gateway style, clearly marked STUB, with requirements trimmed to the stub set. storage-service's Dockerfile was also missing the `/usr/local/bin` COPY (so `uvicorn` would be absent from the final image) — that was added, bringing all five Python Dockerfiles to parity.

The one scope deviation is the `shared/requirements.txt` psycopg pin bump. It is harmless and consistent with the "psycopg 3.2.3 everywhere" rule, but it contradicts the verification note's "shared/ was NOT modified" claim and should be acknowledged rather than silently accepted.

<details>
<summary>Issues (2)</summary>

1. **shared/requirements.txt touched** — the commit bumps psycopg `3.2.0 → 3.2.3` in `shared/requirements.txt`, contradicting the plan's "do NOT touch shared/" and the verification note's "shared/ was NOT modified." Non-blocking (pin-only, not installed by service Dockerfiles, consistent with the project-wide psycopg bump) but the verification note should be corrected to reflect it.
2. **storage & visualization are stubs** — both services answer `/health` only and implement no business logic. In-scope and intentional per the plan, but a reviewer should know these are placeholders, not finished services.

</details>

<details>
<summary>Details</summary>

### Fixing imports at the service layer, not in shared

The unifying diagnosis across instrument-service and metadata-service is that each service installs its own `requirements.txt` and must therefore carry every transitive dependency that the `shared` code it imports pulls in — the service Dockerfiles do not install `shared/requirements.txt`. instrument-service imports `shared.auth`, whose `jwt_handler.py` does `from jose import ...` and whose `password.py` uses `passlib`; neither was pinned, so the container crash-looped with `ModuleNotFoundError: No module named 'jose'`. The fix adds `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1` — the same pins api-gateway already uses — with no code change, which is the minimal correct action.

metadata-service had two separate import bugs. Its `main.py` lifespan did `from db.database import init_db` against a bare top-level `db` package that does not exist in the container, which only appeared to work locally because of a `sys.path.insert` pointing *inside* `shared/`. That line is replaced with the api-gateway pattern (prepend the repo root to `sys.path` only when `./shared` is absent) and the import corrected to `from shared.db.database import init_db`. Separately, `routers/metadata.py` imported `from shared.schemas.responses import DublinCoreMetadata, InstrumentResponse` — a module that does not exist and whose names were imported-but-unused — now removed. `email-validator==2.1.0` was added because loading `shared.schemas.usuario` exercises pydantic `EmailStr`. A grep over `services/metadata-service/**/*.py` confirms no bare `db`/`routers`/`models`/`schemas` imports remain, and the stale empty `services/metadata-service/shared/` directory is confirmed gone, so the container resolves `shared` solely from the copied `/app/shared`.

### analysis-service: removing dead langchain instead of pinning around it

The build break was `langchain==0.3.0` pinned alongside `langchain-ollama==0.1.0` and `langchain-community==0.1.0`; the 0.1.x community/ollama packages predate and conflict with langchain 0.3.x, so pip could not resolve. A grep for `import langchain` / `from langchain` across `services/analysis-service/**/*.py` returns nothing — the stack was dead weight. Removing all three lines (rather than hunting for a compatible 0.3.x trio) is the right root-cause fix; the remaining vector deps, `chromadb==0.5.0` and `sentence-transformers==3.0.0`, are the only ones the code actually imports (both lazily). The verification note records a clean build with no resolver error and a `9.94GB` image (torch via sentence-transformers), with the embedding model loaded lazily on first vectorization so startup is immediate.

This is where the implementation diverges from checklist item 3, which anticipated "a mutually-compatible 0.3.x set." That expectation was based on langchain being needed; since it is not imported anywhere, deletion is the correct outcome and leaves no unsatisfiable pins behind.

### Two stubs that build and answer /health

storage-service and visualization-service each had only a `requirements.txt` and no `main.py`, yet their Dockerfiles end with `CMD ["uvicorn", "main:app", ...]`, so neither could start. Each now has a `main.py` mirroring api-gateway: a `FastAPI` app, a lifespan logger, permissive CORS, and `GET /health` returning `{"status":"ok","service":"<name>"}`, with a docstring explicitly marking the file a STUB pending real implementation. Requirements are trimmed to the minimal stub set, which also drops visualization-service's own incompatible `langchain 0.3.0 + langchain-community 0.1.0` pins and storage-service's unused `langchain-chroma 0.1.0` (a chromadb 0.5.0 conflict risk). A reviewer should treat these as placeholders: they occupy ports 8004/8005 and pass health checks, but carry no persistence or visualization logic yet.

### Scope deviation: shared/requirements.txt

The commit changes `shared/requirements.txt` (`psycopg[binary]==3.2.0 → 3.2.3`). The plan says "Do NOT touch `shared/`" and the verification note asserts "shared/ was NOT modified," so the diff and the note disagree. The change itself is benign — a pin bump matching the project-wide `psycopg 3.2.3` convention, and `shared/requirements.txt` is not installed by any service Dockerfile — so it cannot affect the running services. It is a documentation accuracy issue, not a functional one: the verification note should be corrected to acknowledge the one-line shared change.

### Evidence quality

Per the review mandate I did not re-run builds or compose. The claims in the verification note line up with the committed diff on every point I spot-checked: no langchain imports in analysis-service, no bare `db`/`routers`/`models`/`schemas` imports left in metadata-service, the stale `services/metadata-service/shared/` folder gone, and the analysis-service requirements reduced to chromadb + sentence-transformers. The note records per-service failure, exact lines changed, startup log lines (`Application startup complete`, `Uvicorn running on ...`), `/health` 200s, and a combined `compose ps` with all six service containers Up (api-gateway healthy). Evidence is present for all six services, so there is no missing-evidence gap to reject on.

</details>

<details>
<summary>File map</summary>

- `services/instrument-service/requirements.txt` — add jose/passlib/bcrypt auth pins; psycopg → 3.2.3
- `services/metadata-service/main.py` — fix `shared.db.database` import, replace bad sys.path insert with repo-root fallback
- `services/metadata-service/routers/metadata.py` — drop nonexistent `shared.schemas.responses` import
- `services/metadata-service/requirements.txt` — add email-validator; psycopg → 3.2.3
- `services/analysis-service/requirements.txt` — remove unused incompatible langchain trio; psycopg → 3.2.3
- `services/storage-service/main.py` — new health-only FastAPI stub
- `services/storage-service/requirements.txt` — trim to minimal stub set
- `infrastructure/docker/Dockerfile.storage-service` — add missing `/usr/local/bin` COPY
- `services/visualization-service/main.py` — new health-only FastAPI stub
- `services/visualization-service/requirements.txt` — trim to minimal stub set
- `infrastructure/docker/Dockerfile.{analysis,api-gateway,instrument,metadata,visualization}-service` — add `/usr/local/bin` COPY (parity)
- `services/api-gateway/requirements.txt` — psycopg → 3.2.3 (reference service, pin bump only)
- `shared/requirements.txt` — psycopg → 3.2.3 (scope deviation, non-blocking)

Full diff: `git show 52c0040` on branch `refactorizacion-microservicios`.

</details>
