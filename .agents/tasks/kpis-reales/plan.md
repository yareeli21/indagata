# Plan de implementación — Integración de KPIs reales (kpis-reales)

Fuente de verdad: `design.md` (autoritativo) + `requirements.md` (criterios de aceptación).
Este plan sigue el diseño sección por sección. Todas las rutas son **absolutas** y viven dentro
del worktree `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales` (rama `kpis-reales`).
El cwd del agente ejecutor es el workspace principal, NO el worktree: usa siempre rutas absolutas.

## Hechos del entorno (verificados durante la exploración)

- El CSV `infrastructure/postgres/seed/kpis_ampliados.csv` existe SOLO en el árbol principal del
  repo; **todavía NO está dentro del worktree**. Hay que copiarlo/versionarlo antes del seed (§6).
- `git status` del worktree: limpio salvo `.agents/tasks/kpis-reales/` (artefactos de planificación).
- **No existe infraestructura de tests** en el proyecto: no hay `pytest.ini`/`pyproject` con pytest
  en `analysis-service`, ni runner de tests en `pixel-perfect-pixel` (`package.json` no tiene script
  `test`; solo `dev`, `build`, `build:dev`, `preview`, `lint`, `format`). El diseño pide tests unit;
  se añade un `pytest` mínimo para las funciones puras (ver ítem 10) ya que la guía exige crear la
  infra estándar cuando no existe. La verificación de regresión fuerte es el **loop de runtime**
  (reseed→reindex→endpoint) de un paso posterior, con recreación de volúmenes.
- Build del frontend: `npm run build` (vite build). Type-check puro disponible vía
  `npx tsc -p tsconfig.json` (`noEmit: true`). TS en modo `strict` con `exactOptionalPropertyTypes`
  y `noUncheckedIndexedAccess`: cuidado al quitar campos opcionales y al mapear.
- Deps analysis-service en `services/analysis-service/requirements.txt` (fastapi, sqlalchemy 2.x,
  pydantic 2.x, chromadb-client, sentence-transformers). Guard de rutas = `UsuarioActual`
  (`dependencies.py`), patrón `AUTH_DEV_MODE`.
- `main.py` importa hoy `from app.vectorization.routers import espacio, health, vectorizacion` y
  registra 3 routers. `POST /vectorizacion/kpis/reindex` ya existe en `vectorizacion.py` (no colisiona
  con el nuevo `GET /vectorizacion/kpis/catalogo`).

## Orden de ejecución vinculante (runtime, para el paso de verificación posterior)

Diseño §1.4 y §3.5: **reseed → desplegar código nuevo → reindex inmediato**. En pruebas, la ÚNICA
vía soportada de re-seed de forma es **recrear los volúmenes**:
`docker compose down -v && docker compose up -d` (baja Postgres **y** Chroma a la vez para que
`01_schema.sql` cree la forma nueva y no sobreviva ninguna colección `kpis` con la clave de metadato
vieja `nombre_kpi`). El `DROP TABLE ... CASCADE` manual queda DESACONSEJADO (rompería las FKs de las
tablas hijas → viola CA-3). Tras levantar: `docker compose exec analysis-service python
scripts/seed_kpis.py`, luego `POST /vectorizacion/kpis/reindex`.

Este orden NO se ejecuta durante la implementación de código (los ítems 1–12 dejan el repo buildable
sin runtime). Se ejecuta en el paso de verificación de runtime, que registra evidencia en
`verification.md`.

## Evidencia que debe registrar el implementador

En cada commit y en `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\.agents\tasks\kpis-reales\verification.md`:
- Los comandos exactos ejecutados y su salida resumida (build de frontend, py_compile/pytest, import
  checks).
- Para el paso de runtime: la secuencia `down -v`/`up -d`, salida de `seed_kpis.py` (`n_insertados`),
  `SELECT COUNT(*) FROM tt_rag.kpi` (= conteo real del CSV), respuesta de `reindex` (`n_kpis`),
  conteo de puntos de la colección `kpis`, y una muestra que confirme `document == texto_contexto_rag_vectorial`.
- El reviewer debe poder leer `verification.md` SIN re-ejecutar las suites.

---

## Pasos ordenados por dependencia

- [ ] 1. Versionar el CSV dentro del worktree.
      Copiar `kpis_ampliados.csv` del árbol principal a la misma ruta dentro del worktree para que
      `seed_kpis.py` lo consuma (§6, §1.3). No modificar su contenido.
      Archivos: crear `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\infrastructure\postgres\seed\kpis_ampliados.csv`
      (copia byte a byte del original en el árbol principal).
      Verify: leer el archivo copiado y confirmar 56 líneas (1 cabecera + 55 datos) y las 8 columnas
      exactas en la cabecera. `git -C <worktree> status` muestra el CSV como nuevo versionable.

- [ ] 2. Redefinir el esquema de `tt_rag.kpi` (§1.1).
      Reemplazar el bloque `CREATE TABLE IF NOT EXISTS kpi (...)` por `kpi_id SERIAL PRIMARY KEY` + las
      8 columnas snake_case en español (`nombre` NOT NULL, 6 metadatos nullable,
      `texto_contexto_rag_vectorial` NOT NULL). No tocar las tablas hijas ni sus FKs.
      Archivos: `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\infrastructure\postgres\init\01_schema.sql`
      Verify: lint SQL manual (leer el bloque) y confirmar que las FKs de `kpi_variable`,
      `kpi_inferido`, `valor_variable_inferido`, `kpi_inferido_chunk` siguen referenciando `kpi(kpi_id)`
      sin cambios. La validez efectiva se comprueba en el paso de runtime (recrear volumen).

- [ ] 3. Reescribir el modelo ORM `KPI` (§2).
      Las 8 columnas `Mapped`/`mapped_column` exactamente como §2 (`nombre`, 6 nullable,
      `texto_contexto_rag_vectorial`), `__repr__` usando `self.nombre`.
      Archivos: `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\shared\models\kpi.py`
      Verify: `python -c "from shared.models.kpi import KPI; print([c.name for c in KPI.__table__.columns])"`
      desde `services/analysis-service` (con `shared` en sys.path) imprime las 8 columnas nuevas.

- [ ] 4. Reescribir los schemas Pydantic compartidos (§2.1).
      `KPIBase/KPICreate/KPIUpdate/KPIRead` a los 8 campos nuevos, `KPIRead` con
      `ConfigDict(from_attributes=True)` + `kpi_id: int`, docstring veraz. NO cambiar nombres
      exportados ni `shared/schemas/__init__.py`.
      Archivos: `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\shared\schemas\kpi.py`
      Verify: `python -c "from shared.schemas import KPIBase, KPICreate, KPIUpdate, KPIRead; print(KPIRead.model_fields.keys())"`
      resuelve e imprime los 9 campos (`kpi_id` + 8).

- [ ] 5. Añadir `delete_collection` idempotente al cliente Chroma (§3.2).
      Nueva función `delete_collection(name, *, client=None)` que llama `cli.delete_collection(name)` y
      traga la excepción si la colección no existe. Mantener el patrón de inyección de `client`.
      Archivos: `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\services\analysis-service\app\vectorization\core\chroma_client.py`
      Verify: `python -c "from app.vectorization.core import chroma_client; print(hasattr(chroma_client,'delete_collection'))"`
      desde `services/analysis-service` → `True`.

- [ ] 6. Reescribir `kpi_indexer.py` (§3.1, §3.2).
      `build_kpi_text(kpi)` devuelve SOLO `kpi.texto_contexto_rag_vectorial or ""`. Nueva función pura
      `build_kpi_metadata(kpi)` con los 6 escalares sin `None` (fallback `""`, metadato `nombre` no
      `nombre_kpi`). Migrar `reindex_kpis(db, *, client=None)`: `cli = client or get_client()`,
      `delete_collection(nombre, client=cli)`, `get_or_create_collection(nombre, client=cli)`, luego
      `upsert`. Conservar `ids = [str(k.kpi_id)]`, documento = texto RAG, mismo modelo/coseno.
      Archivos: `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\services\analysis-service\app\vectorization\core\kpi_indexer.py`
      Depende de: ítems 3 y 5.
      Verify: `python -c "import app.vectorization.core.kpi_indexer as m; import inspect; print('client' in inspect.signature(m.reindex_kpis).parameters and 'collection' not in inspect.signature(m.reindex_kpis).parameters)"`
      → `True`. El build de arranque (ítem 9) confirma import global.

- [ ] 7. Reconciliar los lectores de metadatos/columnas viejas en analysis-service (§3.3, §3.4).
      Cambios coherentes del renombre `nombre_kpi→nombre` y retarget de `categoria`/`ambito`:
      - `kpi_search.py`: `KpiMatch` → `kpi_id, nombre, polaridad_rendimiento, tipo_objetivo_estrategico,
        score`; `search_kpis` lee `meta.get("nombre")`, `meta.get("polaridad_rendimiento")`,
        `meta.get("tipo_objetivo_estrategico")`.
      - `schemas/vectorizacion.py`: `PropuestaKPI` renombra `nombre_kpi→nombre`, elimina
        `categoria`/`ambito`, añade `polaridad_rendimiento`/`tipo_objetivo_estrategico` (`str | None`);
        `KpiAgregado` renombra `nombre_kpi→nombre`.
      - `proposal_service.py`: construir `PropuestaKPI(kpi_id=m.kpi_id, nombre=m.nombre,
        polaridad_rendimiento=m.polaridad_rendimiento,
        tipo_objetivo_estrategico=m.tipo_objetivo_estrategico, score=m.score)`.
      - `enrichment_service.py`: `kpis[d.kpi_id].nombre` (en vez de `.nombre_kpi`), `KpiAgregado(...,
        nombre=...)`, y clave del JSON `inferred_kpis` → `{"kpi_id","nombre","score"}`.
      - `routers/espacio.py` `_label_for` rama `kpis`: `meta.get("nombre")`.
      Archivos (todos absolutos bajo el worktree):
      `services\analysis-service\app\vectorization\core\kpi_search.py`,
      `services\analysis-service\app\vectorization\schemas\vectorizacion.py`,
      `services\analysis-service\app\vectorization\services\proposal_service.py`,
      `services\analysis-service\app\vectorization\services\enrichment_service.py`,
      `services\analysis-service\app\vectorization\routers\espacio.py`
      Depende de: ítem 6 (metadato `nombre`).
      Verify: `python -m py_compile` sobre los 5 archivos → sin error; grep de control confirma 0
      apariciones de `nombre_kpi`, `.categoria`, `.ambito` en estos archivos (el grep es solo apoyo; la
      verificación real es el arranque del ítem 9).

- [ ] 8. Reconciliar el visor read-only `chroma-viewer` (§3.3).
      `_label_for` rama `kpis`: `meta.get("nombre")` en vez de `meta.get("nombre_kpi")`. NO tocar el
      visor scratch `.agents/tasks/chroma-viz/scratch/viewer/app.py`.
      Archivos: `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\infrastructure\chroma-viewer\app.py`
      Verify: `python -m py_compile` del archivo → sin error.

- [ ] 9. Añadir el `KpiCatalogoDTO`, el router de catálogo y registrarlo en main (§4).
      - En `schemas/vectorizacion.py`: añadir `KpiCatalogoDTO` (8 campos string, §4.2).
      - Nuevo router `routers/kpis.py`: `GET /vectorizacion/kpis/catalogo` → `list[KpiCatalogoDTO]`,
        guard `UsuarioActual`, `db.query(KPI).order_by(KPI.kpi_id).all()`, mapeo con `or ""` en los 6
        nullable (NO en `id`/`nombre`), `try/except SQLAlchemyError` → 500 con `logger.exception`.
      - `main.py` DOS ediciones: añadir `kpis` al import
        (`from app.vectorization.routers import espacio, health, kpis, vectorizacion`) **y**
        `app.include_router(kpis.router)`.
      Archivos: `services\analysis-service\app\vectorization\schemas\vectorizacion.py` (si no se tocó el
      DTO en el ítem 7, añadir aquí), `services\analysis-service\app\vectorization\routers\kpis.py`
      (nuevo), `services\analysis-service\main.py`.
      Depende de: ítems 3, 7.
      Verify (arranque = regresión fuerte de todo el backend): desde `services/analysis-service` con
      deps instaladas, `python -c "import main; print([r.path for r in main.app.routes if 'kpis/catalogo' in r.path])"`
      imprime `/vectorizacion/kpis/catalogo` sin `NameError`. Confirma además que todos los routers
      cargan (ítems 5–8 integrados).

- [ ] 10. Crear el script de re-seed `seed_kpis.py` + función pura `leer_kpis_csv` y tests unit (§1.3, §1.5).
      Script en `services/analysis-service/scripts/seed_kpis.py` análogo a `seed_demo.py`
      (`parents[3]` = raíz del worktree; ruta por defecto
      `parents[3]/infrastructure/postgres/seed/kpis_ampliados.csv`, override por `KPIS_CSV_PATH`).
      Función pura `leer_kpis_csv(path) -> list[dict]` (csv.DictReader, utf-8-sig, valida cabecera=8
      columnas en orden, `KPI` no vacío, `Texto_Contexto_RAG_Vectorial` no vacío; recuenta filas, no
      hardcodea 55). `main()`: en una transacción `TRUNCATE tt_rag.kpi RESTART IDENTITY CASCADE` + insert
      en orden; commit/rollback; exit codes 2/3/4 según §1.3; log `n_insertados`. Añadir tests pytest de
      la función pura con fixtures CSV (cabecera mala, campo vacío, caso feliz) — crear
      `services/analysis-service/tests/test_seed_kpis.py` y `requirements-dev.txt` con `pytest` (no
      existe infra de tests hoy).
      Archivos: `services\analysis-service\scripts\seed_kpis.py` (nuevo),
      `services\analysis-service\tests\test_seed_kpis.py` (nuevo),
      `services\analysis-service\requirements-dev.txt` (nuevo, con `pytest`).
      Depende de: ítem 3 (modelo), ítem 1 (CSV presente para prueba de integración posterior).
      Verify: desde `services/analysis-service`, `pip install -r requirements-dev.txt` y
      `python -m pytest tests/test_seed_kpis.py -q` → tests de `leer_kpis_csv` pasan. (El TRUNCATE/insert
      real se ejerce en el paso de runtime.)

- [ ] 11. Actualizar el README de Postgres (§1.4).
      Nota breve: `init/*.sql` solo corre en volumen nuevo; vía soportada en pruebas = recrear volúmenes
      (`docker compose down -v && docker compose up -d`), luego `seed_kpis.py`, luego reindex. Documentar
      que el DROP manual queda desaconsejado.
      Archivos: `c:\Users\yarel\Documents\indagata\indagata\.worktrees\kpis-reales\infrastructure\postgres\README.md`
      Verify: lectura manual; coherente con §1.4/§3.5.

- [ ] 12. Cablear el frontend (§5).
      - `src/api/kpis.ts`: reescribir el cuerpo de `getCatalogoKpis` (consume
        `${ANALYSIS_URL}/vectorizacion/kpis/catalogo` con `auth:false`; `try/catch` → fallback
        `simularRed(catalogoKpis)`; respuesta vacía → fallback). Añadir `interface KpiCatalogoDTO`,
        `mapearKpi` (mapeo Opción B §5.2), `derivarEtiquetas`, `elegirIcono` con normalización NFD de
        acentos, las 15 ramas y `ICONOS_VALIDOS` (Set de 15 claves) + fallback `BarChart2`. Firma de
        `getCatalogoKpis` sin cambios; `getKpis/getNoticias/getDatosGrafica` quedan en `simularRed`.
      - `src/api/carga.ts`: interfaces locales `PropuestaKPI` (`nombre_kpi→nombre`, quitar
        `categoria?`/`ambito?`) y `KpiAgregado` (`nombre_kpi→nombre`); `proponerKpis` usa `p.nombre`;
        `confirmarKpis` usa `k.nombre` en ambas ramas. La forma expuesta a las pantallas NO cambia.
      - (Opcional) extraer `ICONOS` a `src/features/kpis/iconos.ts` compartido.
      Archivos: `pixel-perfect-pixel\src\api\kpis.ts`, `pixel-perfect-pixel\src\api\carga.ts`
      (opcional `pixel-perfect-pixel\src\features\kpis\iconos.ts`).
      Depende de: ítem 9 (contrato del DTO) y 7 (contrato propuestas/confirmar).
      Verify: desde `pixel-perfect-pixel`, `npm ci` (o `npm install`) y `npm run build` → build sin
      errores de TypeScript (CA-9). Opcional `npx tsc -p tsconfig.json` para type-check puro. Confirmar
      por lectura que ningún `icono` emitido queda fuera de `ICONOS_VALIDOS` (fallback `BarChart2`,
      nunca `ChartBar`).

---

## Verificación de runtime (paso posterior; registrar en verification.md)

Siguiendo el orden vinculante §1.4/§3.5 con recreación de volúmenes:

1. `docker compose down -v && docker compose up -d` (recrea Postgres + Chroma; `01_schema.sql` aplica la
   forma nueva).
2. `docker compose exec analysis-service python scripts/seed_kpis.py` → registrar `n_insertados`.
3. `SELECT COUNT(*) FROM tt_rag.kpi` = conteo real del CSV (55); IDs contiguos 1..N (CA-2); FKs intactas
   (CA-3).
4. `POST /vectorizacion/kpis/reindex` → `200`, `n_kpis` = conteo real; colección `kpis` con exactamente
   ese nº de puntos, `id = str(kpi_id)`, `document == texto_contexto_rag_vectorial` en una muestra
   (CA-4, CA-5).
5. `GET /vectorizacion/kpis/catalogo` → `200`, N items ordenados por `id`, campos poblados (CA-6).
6. `POST /vectorizacion/propuestas` → propuestas con `nombre` de KPIs reales nuevos (CA-8).
7. Build de frontend verde (CA-9).

Toda la evidencia (comandos + salidas resumidas) va a `verification.md` para que el reviewer no
re-ejecute suites.
