# Implementation Plan — Fase 1: Login JWT real + Espacio vectorial

Scope: (A) wire frontend login to the real api-gateway JWT backend; (B) add a read-only vector-space endpoint in analysis-service; (C) add a Spanish vector-space visualization screen in the frontend fed by it.

Edit location: worktree `c:\Users\yarel\Documents\indagata\indagata\.worktrees\fase1-login-vectores`.
Verify location: the live stack runs from the MAIN tree `c:\Users\yarel\Documents\indagata\indagata` (docker compose, curl, bun). Windows/PowerShell: use `;` to chain, not `&&`.

## Design decisions (grounded in the code I read)

1. **Chart library — reuse recharts (no new dependency).** `pixel-perfect-pixel/package.json` already lists `recharts ^2.15.4`, and `src/features/kpis/GraficasKpi.tsx` already renders recharts charts through `@/components/ui/chart` (`ChartContainer`) with colors from CSS tokens `var(--chart-1..5)`. The scatter screen uses recharts `ScatterChart`/`Scatter` with the same token-based colors. No `bun add` needed.

2. **Gateway vs direct :8002 — call analysis-service directly.** `services/api-gateway/proxy/proxy.py` only defines hardcoded `/instruments/upload` and `/instruments/{id}` routes and wraps responses in `{status_code, body}` (not a transparent proxy); `main.py` includes only the auth router, no `/vectorizacion/*`. Adding a correct transparent proxy is non-trivial and the task forbids changing gateway behavior unless trivial. So the frontend calls analysis-service directly at `VITE_ANALYSIS_URL` (default `http://localhost:8002`). analysis-service CORS is `allow_origins=["*"]` (`services/analysis-service/main.py`), so browser calls from the dev server work. Login still goes through the gateway at `VITE_API_URL` (default `http://localhost:8000`).

3. **UsuarioRead → Usuario mapping.** Backend `UsuarioRead` (`shared/schemas/usuario.py`): `{usuario_id:int, nombre:str, email:str, rol:str|null, fecha_registro}`. Frontend `Usuario` (`src/types/index.ts`): `{id:string, usuario:string, nombre:string, rol:"Investigador"|"Administrador", investigadorId:string}`. Map (NO change to the `Usuario` type): `id = String(usuario_id)`; `nombre = nombre`; `usuario = email`; `rol`: `"administrador" -> "Administrador"`, `"investigador" -> "Investigador"` (case-insensitive; default `"Investigador"` if null/unknown); `investigadorId = String(usuario_id)`. The login response is `TokenResponse` = `{access_token, token_type:"bearer", usuario: UsuarioRead}` (`services/api-gateway/app/auth/schemas.py`).

4. **Login form collects email.** `src/routes/login.tsx` currently collects a username (`ana`/`admin`); the backend expects an email. Change the first field to `type="email"` labeled "Correo electrónico", update the demo-access hint text to the seeded emails (`admin@indagata.local` / `investigador@indagata.local`), and keep everything in Spanish. `AuthContext.entrar(usuario, contrasena)` and `iniciarSesion(usuario, contrasena)` signatures stay; `usuario` now carries the email string.

5. **scikit-learn for PCA.** The scratch viewer uses `sklearn.decomposition.PCA`. `sentence-transformers==3.0.0` (in `services/analysis-service/requirements.txt`) pulls scikit-learn transitively, so `import sklearn` should already work in the container. Verify at implementation time (step 5); only if it fails, add `scikit-learn` to that requirements file and rebuild — the single allowed backend dependency.

6. **Backend bind-mount / verification sync.** docker-compose mounts `./services/analysis-service:/app` from the MAIN tree, so the running container executes the MAIN tree's code, not the worktree's. Commits land in the worktree branch; for live verification, copy the new/changed backend files into the MAIN tree, then restart only analysis-service. This is a verification-only sync (do NOT commit to main, do NOT touch other services).

7. **Only `auth` is de-mocked.** `client.ts` keeps `simularRed`; `carga.ts`, `instrumentos.ts`, `chat.ts`, `investigaciones.ts`, `kpis.ts` stay mocked. New `espacio.ts` is the only other real HTTP consumer.

## Part A — Real login (JWT)

- [ ] 1. Add a real HTTP layer + token store to `src/api/client.ts`, keeping `simularRed`.
      Add: `API_URL` (`import.meta.env.VITE_API_URL ?? "http://localhost:8000"`) and `ANALYSIS_URL` (`import.meta.env.VITE_ANALYSIS_URL ?? "http://localhost:8002"`); an in-memory + `localStorage` token store (`guardarToken`, `leerToken`, `borrarToken`, key e.g. `"indagata.token"`); a `pedir<T>(url, { method, body, auth })` fetch helper that sets `Content-Type: application/json`, attaches `Authorization: Bearer <token>` when `auth` is true and a token exists, parses JSON, and throws an `Error` (Spanish message) on non-2xx — map HTTP 401 to the message `"Usuario o contraseña incorrectos"`.
      Files: `pixel-perfect-pixel/src/api/client.ts`
      Verify: `cd pixel-perfect-pixel; bun run build` succeeds (step 4 runs the full build; this step just must compile — no type errors).

- [ ] 2. Rewrite ONLY the body of `iniciarSesion` in `src/api/auth.ts` to call the real backend.
      POST `{API_URL}/auth/login` with `{ email, password }` (the `usuario` arg is the email). On success store `access_token` via the token store and return the mapped `Usuario` (decision 3). On 401 reject with `new Error("Usuario o contraseña incorrectos")`. Remove the `CUENTAS` mock. Keep the exported signature `iniciarSesion(usuario, contrasena): Promise<Usuario>`.
      Files: `pixel-perfect-pixel/src/api/auth.ts`
      Verify: covered by step 4 build + step 11 browser login.

- [ ] 3. Adapt the login form to collect an email (Spanish, minimal).
      In `src/routes/login.tsx` change the first input to `type="email"`, `placeholder="Correo electrónico"`, `autoComplete="username"`; rename the state to reflect email but keep passing it as the first arg to `entrar(...)`. Update the demo-access hint to the seeded emails (`admin@indagata.local`, `investigador@indagata.local`). Do not change `AuthContext`'s API.
      Files: `pixel-perfect-pixel/src/routes/login.tsx`
      Verify: covered by step 4 build + step 11 browser login.

- [ ] 4. Build the frontend to confirm Part A compiles.
      Files: (none)
      Verify: `cd pixel-perfect-pixel; bun install; bun run build` — completes with no TypeScript/build errors.

## Part B — analysis-service read-only vector-space endpoint

- [ ] 5. Create the vector-space router reusing the scratch viewer's PCA logic via the existing chroma client.
      New file `services/analysis-service/app/vectorization/routers/espacio.py`: `APIRouter(prefix="/vectorizacion", tags=["vectorizacion-espacio"])` with `GET /espacio` depending on `UsuarioActual` (from `app.vectorization.dependencies`, mirroring the other vectorization routes so `AUTH_DEV_MODE` resolves DEV_USER_ID). Use `get_client()` + `get_or_create_collection(name)` from `app.vectorization.core.chroma_client`; for each of `["kpis", "summary_instrument"]` call `collection.get(include=["embeddings","metadatas","documents"])`, collect embeddings/ids/metadatas/documents, build a label with the same precedence as the scratch viewer `_label_for` (`kpis` -> `nombre_kpi`|doc|id; else `titulo`|`Título`|`nombre_archivo`|`id_instrumento`|id). Stack all embeddings into one array, run `sklearn.decomposition.PCA(n_components=2)` (fall back to 1 component if <2 points/dims), and return `{"puntos":[{"x","y","coleccion","label","id"}...], "colecciones":{"kpis":n,"summary_instrument":m}}`. Read-only, no writes. Wrap gather in try/except returning HTTP 502 with the error message (as the scratch viewer does).
      Files: `services/analysis-service/app/vectorization/routers/espacio.py`
      Verify: `python -c "import sklearn; from sklearn.decomposition import PCA"` inside the analysis-service container (step 7 confirms end-to-end). If that import fails, add `scikit-learn` to `services/analysis-service/requirements.txt` and note a rebuild is required.

- [ ] 6. Register the new router in analysis-service's app.
      In `services/analysis-service/main.py` import `espacio` alongside `health, vectorizacion` from `app.vectorization.routers` and add `app.include_router(espacio.router)`.
      Files: `services/analysis-service/main.py`
      Verify: covered by step 7 (service starts and serves the route).

- [ ] 7. Sync backend files to the MAIN tree and restart analysis-service, then verify the endpoint.
      Copy `espacio.py` and the edited `main.py` (and `requirements.txt` if changed) from the worktree into the MAIN tree's `services/analysis-service` (verification-only; do NOT commit to main). If `requirements.txt` changed, rebuild: from MAIN tree `docker compose -f docker-compose.yml build analysis-service`. Then `docker compose -f docker-compose.yml up -d analysis-service` (or `restart analysis-service` if only mounted code changed).
      Files: (MAIN tree copies of the above — not committed)
      Verify: from MAIN tree `curl.exe http://localhost:8002/vectorizacion/espacio` returns JSON with `~51` points total and `colecciones` ≈ `{"kpis":~30,"summary_instrument":21}`; HTTP 200.

## Part C — Frontend vector-space screen

- [ ] 8. Add the vector-space API accessor and shared types.
      New file `src/api/espacio.ts`: `async getEspacioVectorial(): Promise<EspacioVectorial>` calling `GET {ANALYSIS_URL}/vectorizacion/espacio` via the `pedir` helper from `client.ts` (`auth: false` is fine in dev; keep the pattern mock-replaceable). Add types `PuntoVector { x:number; y:number; coleccion:string; label:string; id:string }` and `EspacioVectorial { puntos: PuntoVector[]; colecciones: Record<string, number> }` to `src/types/index.ts`.
      Files: `pixel-perfect-pixel/src/api/espacio.ts`, `pixel-perfect-pixel/src/types/index.ts`
      Verify: covered by step 10 build.

- [ ] 9. Build the "Espacio vectorial" screen and its route under the `_panel` layout.
      New file `src/features/espacio-vectorial/EspacioVectorialPage.tsx`: loads data with `getEspacioVectorial()` in `useEffect`, renders a recharts `ScatterChart` (one `Scatter` series per collection: `kpis` -> `var(--chart-1)`, `summary_instrument` -> `var(--chart-2)`), a legend, a hover `Tooltip` showing `label` + `coleccion` + `id`, and loading/empty/error states in Spanish — follow the structure and token usage of `src/features/kpis/GraficasKpi.tsx` and `KpisPage.tsx` (use `PageHeader`, `ChartContainer`, `var(--chart-*)` tokens, no literal color classes). New route `src/routes/_panel.espacio.tsx` mirroring `_panel.kpis.tsx` (Spanish `head` meta, `component: EspacioVectorialPage`). If a scatter token distinct from `--chart-1/2` is wanted, add it to `src/styles.css` as a semantic token; otherwise reuse existing chart tokens.
      Files: `pixel-perfect-pixel/src/features/espacio-vectorial/EspacioVectorialPage.tsx`, `pixel-perfect-pixel/src/routes/_panel.espacio.tsx` (and `src/styles.css` only if a new token is added)
      Verify: covered by step 10 build + step 11 browser check.

- [ ] 10. Add the two entry points and build.
      Add a sidebar nav item to `src/components/layout/Sidebar.tsx` (`{ to: "/espacio", etiqueta: "Espacio vectorial", icono: <a Lucide icon e.g. ScatterChart/Network> }`). In the upload flow, after a successful save (`UploadWizard.guardar()` currently toasts and navigates to `/instrumentos`), add a visible "Ver espacio vectorial" action shown when ingestion finishes — e.g. render a secondary button on the final step (`paso === 6`) or in the post-save toast action that navigates to `/espacio`. Keep Spanish; use `Button` + `Link`/`navigate`.
      Files: `pixel-perfect-pixel/src/components/layout/Sidebar.tsx`, `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx` (and/or `StepGuardar.tsx`)
      Verify: `cd pixel-perfect-pixel; bun run build` — completes with no errors.

## End-to-end verification

- [ ] 11. Full stack check (dev server + browser) from the worktree frontend against the running MAIN stack.
      From the worktree `pixel-perfect-pixel`: `bun run dev`. In a browser: (a) log in with `admin@indagata.local` / `admin123` and confirm redirect to `/instrumentos`, the token is stored, and a wrong password shows "Usuario o contraseña incorrectos"; (b) open "Espacio vectorial" from the sidebar and confirm the scatter renders ~51 points in two colors with legend + working hover labels; (c) run the upload wizard to the final step and confirm the "Ver espacio vectorial" entry point navigates to the screen.
      Files: (none)
      Verify: all three browser checks pass; `curl.exe http://localhost:8002/vectorizacion/espacio` still returns ~51 points.

## Notes / assumptions

- JSON metadata gaps (`notas_contextuales`, `notas_representativas`) are irrelevant here — this task reads existing Chroma points, it does not re-ingest.
- No microservice other than analysis-service is modified; api-gateway is read-only reference; `pixel-perfect-pixel/.lovable` is untouched; nothing is pushed, merged, rebased, or amended.
- If `import sklearn` fails in the container, the ONLY backend dependency change allowed is adding `scikit-learn` to `services/analysis-service/requirements.txt` (rebuild required) — keep in plan as "verify during implementation".
