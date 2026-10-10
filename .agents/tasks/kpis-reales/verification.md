# Verificación — FEAT-001 (kpis-reales)

Entorno: Windows + PowerShell. Python 3.14.2, SQLAlchemy 2.0.49, pydantic 2.13.3.
Todas las rutas bajo el worktree `.worktrees/kpis-reales`. No se ejecutó runtime
(docker/seed/reindex): esa verificación corresponde a un paso posterior.

## CSV versionado en el worktree

- Copia byte a byte del CSV del árbol principal al worktree
  (`infrastructure/postgres/seed/kpis_ampliados.csv`).
- SHA256 origen == destino: `874948DDC03F6EB997A2A85EF962CDF99338A8E35DF114D69FE4452C55421FAA` (match=True).
- Conteo de líneas del origen: **56** (1 cabecera + 55 filas de datos).
- Cabecera leída (8 columnas, orden exacto): `KPI, Polaridad_Rendimiento,
  Tipo_Objetivo_Estrategico, Formula_Metrica_Calculo, Descripcion_Ampliada_Educativa,
  Comportamiento_Direccional_y_Causalidad, Razon_Estrategica_y_Decisiones,
  Texto_Contexto_RAG_Vectorial`.

## py_compile del script de seed

Comando (desde `services/analysis-service`):

```
python -m py_compile scripts/seed_kpis.py
```

Salida: exit code 0 (compila sin error).

## Columnas del ORM

```
python -c "from shared.models.kpi import KPI; print([c.name for c in KPI.__table__.columns])"
```

Salida (9 columnas = kpi_id + 8 nuevas):

```
['kpi_id', 'nombre', 'polaridad_rendimiento', 'tipo_objetivo_estrategico',
 'formula_metrica_calculo', 'descripcion_ampliada_educativa',
 'comportamiento_direccional_causalidad', 'razon_estrategica_decisiones',
 'texto_contexto_rag_vectorial']
```

## Schemas Pydantic compartidos

```
python -c "from shared.schemas import KPIBase, KPICreate, KPIUpdate, KPIRead; print(sorted(KPIRead.model_fields.keys()))"
```

Salida (9 campos, sin ImportError de los nombres KPI):

```
['comportamiento_direccional_causalidad', 'descripcion_ampliada_educativa',
 'formula_metrica_calculo', 'kpi_id', 'nombre', 'polaridad_rendimiento',
 'razon_estrategica_decisiones', 'texto_contexto_rag_vectorial',
 'tipo_objetivo_estrategico']
```

Nota de entorno: el paquete `shared/schemas/__init__.py` importa `usuario` (usa
`EmailStr`), por lo que al correr el check hace falta `email-validator` presente
en el entorno (pydantic 2.13 lo exige de forma perezosa). Se instaló localmente
solo para ejecutar la verificación; **no** se añadió a `requirements-dev.txt`
(que, por diseño, solo lista `pytest`). Es una brecha de entorno preexistente,
ajena a los cambios de KPI de esta feature.

## pytest de leer_kpis_csv

```
pip install -r requirements-dev.txt   # pytest
python -m pytest tests/test_seed_kpis.py -q
```

Salida:

```
....                                                                     [100%]
4 passed in 1.15s
```

Casos cubiertos: caso feliz (2 filas), cabecera incorrecta (aborta),
`KPI` vacío (aborta), `Texto_Contexto_RAG_Vectorial` vacío (aborta).

## CREATE TABLE kpi (01_schema.sql)

Bloque redefinido a `kpi_id SERIAL PRIMARY KEY` + las 8 columnas snake_case
(§1.1), con `nombre` y `texto_contexto_rag_vectorial` NOT NULL. Las tablas
hijas `kpi_variable`, `kpi_inferido`, `valor_variable_inferido` y
`kpi_inferido_chunk` y sus FKs a `kpi(kpi_id)` no se tocaron (CA-3).

---

# Verificación — FEAT-002 (kpis-reales)

Entorno: Windows + PowerShell. Intérprete `.venv` del árbol principal
(`c:\Users\yarel\Documents\indagata\indagata\.venv`), Python 3.14.2, con
`requirements.txt` de analysis-service efectivamente instalado (fastapi 0.115.6,
sqlalchemy 2.0.52, pydantic 2.13.5, chromadb-client, sentence-transformers, numpy;
`email-validator` presente por la brecha preexistente de `shared/schemas/usuario`).
Todas las rutas bajo el worktree. No se ejecutó runtime (docker/seed/reindex).

## py_compile de los 10 archivos

Comando (desde `services/analysis-service`):

```
python -m py_compile \
  app/vectorization/core/chroma_client.py \
  app/vectorization/core/kpi_indexer.py \
  app/vectorization/core/kpi_search.py \
  app/vectorization/services/proposal_service.py \
  app/vectorization/services/enrichment_service.py \
  app/vectorization/routers/espacio.py \
  app/vectorization/routers/kpis.py \
  app/vectorization/schemas/vectorizacion.py \
  main.py \
  ../../infrastructure/chroma-viewer/app.py
```

Salida: exit code 0 (los 10 compilan sin error).

## Firma de reindex_kpis (seam de inyección migrado a client)

```
python -c "import app.vectorization.core.kpi_indexer as m, inspect; s=inspect.signature(m.reindex_kpis).parameters; print('client' in s and 'collection' not in s)"
```

Salida:

```
True
```

(`reindex_kpis(db, *, client=None)`; ya no acepta `collection=`.)

## Arranque del backend (import + include_router + todos los routers cargan)

```
python -c "import main; print([r.path for r in main.app.routes if 'kpis/catalogo' in r.path])"
```

Salida:

```
['/vectorizacion/kpis/catalogo']
```

Arranque limpio, sin `NameError`: confirma el import de `kpis` en main.py, su
`include_router`, el DTO `KpiCatalogoDTO` y que no hay colisión con el
`POST /vectorizacion/kpis/reindex` existente.

## Reconciliación de lectores (grep manual tras los cambios)

- `kpi_indexer.py`: `build_kpi_text` devuelve solo `texto_contexto_rag_vectorial`
  (o `""`); nueva `build_kpi_metadata` pura con los 6 escalares y clave `nombre`;
  `reindex_kpis` hace `delete_collection` + `get_or_create_collection` antes del
  upsert.
- `kpi_search.py`: `KpiMatch` → `kpi_id, nombre, polaridad_rendimiento,
  tipo_objetivo_estrategico, score`; lee `meta.get("nombre"/...)`.
- `proposal_service.py`: `PropuestaKPI(nombre, polaridad_rendimiento,
  tipo_objetivo_estrategico, ...)`.
- `enrichment_service.py`: `kpis[...].nombre` y clave `inferred_kpis` con `nombre`.
- `espacio.py` y `infrastructure/chroma-viewer/app.py`: `_label_for` rama `kpis`
  lee `meta.get("nombre")`.
- `schemas/vectorizacion.py`: `PropuestaKPI` sin `categoria`/`ambito`;
  `KpiAgregado.nombre`; nueva `KpiCatalogoDTO` (8 campos string).
- Ningún archivo vivo lee ya `nombre_kpi`/`.categoria`/`.ambito`.

---

# Verificación — FEAT-003 (kpis-reales)

Entorno: Windows + PowerShell. Node vía `npm`. Todas las rutas bajo el worktree
`.worktrees/kpis-reales/pixel-perfect-pixel`. El frontend NO tiene runner de tests:
la verificación es el build de TypeScript (vite + tsc por tsconfig noEmit).

## Instalación de dependencias

`pixel-perfect-pixel` no versiona `package-lock.json`, así que `npm ci` no aplica;
se usó `npm install` (vía alternativa documentada en context.json / FEAT-003):

```
npm install
```

Salida resumida: `added 399 packages, and audited 400 packages ... found 0 vulnerabilities`
(exit code 0). Warnings de deprecación de terceros (tsconfck, recharts, eslint),
ajenos a esta feature.

## Build de TypeScript (CA-9)

```
npm run build
```

Salida resumida: `✓ built in 5.73s` + `Generated .output/nitro.json` (exit code 0).
Sin errores de TypeScript ni de tipos tras el cableado del catálogo real y la
reconciliación de `carga.ts`.

## Lectura de control

- `grep nombre_kpi|ChartBar` sobre `pixel-perfect-pixel/src/`: solo quedan
  referencias en COMENTARIOS (docstring de `elegirIcono` e `iconos.ts` que explican
  el fallback). Ningún código lee `nombre_kpi` ni emite `ChartBar`.
- `elegirIcono` termina con `return ICONOS_VALIDOS.has(candidato) ? candidato : "BarChart2";`,
  donde `ICONOS_VALIDOS` (importado de `src/features/kpis/iconos.ts`) es el `Set` de
  las 15 claves del mapa `ICONOS` → no puede devolver un nombre fuera del conjunto.
- `getCatalogoKpis` consume `${ANALYSIS_URL}/vectorizacion/kpis/catalogo` con
  `auth: false`, mapea con `mapearKpi`, conserva su firma y degrada a `simularRed(catalogoKpis)`
  solo ante error de red / respuesta vacía.
- `carga.ts`: interfaces locales `PropuestaKPI`/`KpiAgregado` usan `nombre` (sin
  `nombre_kpi`), `PropuestaKPI` ya no tiene `categoria`/`ambito`, y `proponerKpis`/
  `confirmarKpis` (ambas ramas del `.map`) leen `.nombre`. La forma expuesta a las
  pantallas (`KpiSugerido` y `{kpiId,nombreKpi,score?}`) no cambia.

## Nota de implementación

Se tomó la mejora opcional (step 6): se extrajo el mapa `ICONOS` y el set de claves
válidas a `src/features/kpis/iconos.ts`, importado por `TarjetaKpi.tsx`,
`DetalleKpi.tsx` y `src/api/kpis.ts` (`ICONOS_VALIDOS`), evitando duplicar las 15
claves en tres sitios.

---

# Verificación de INTEGRACIÓN entre FEATs (iteración 1)

Entorno: Windows + PowerShell. Backend con `.venv` del árbol principal
(`c:\Users\yarel\Documents\indagata\indagata\.venv`, Python 3.14.2, `requirements.txt`
de analysis-service instalado: fastapi 0.115.6, sqlalchemy 2.0.52, pydantic 2.13.5)
más `requirements-dev.txt` (pytest 9.1.1). Frontend con Node v24.12.0 / npm,
`node_modules` presente. Todas las rutas bajo el worktree `.worktrees/kpis-reales`.
No se ejecutó runtime (docker/seed/reindex): esa verificación es del paso posterior.

## Estado del worktree

- Las tres FEAT ya están commiteadas en `kpis-reales` (`6ecb3e8` FEAT-001,
  `3f3b4aa` FEAT-002, `40810c8` FEAT-003) sobre `origin/pruebas`.
- El CSV `infrastructure/postgres/seed/kpis_ampliados.csv` existe en el worktree
  (56 líneas) y está versionado (`git ls-files` lo lista).

## Backend — py_compile de todos los archivos tocados por FEAT-001/002

```
python -m py_compile \
  app/vectorization/core/chroma_client.py \
  app/vectorization/core/kpi_indexer.py \
  app/vectorization/core/kpi_search.py \
  app/vectorization/services/proposal_service.py \
  app/vectorization/services/enrichment_service.py \
  app/vectorization/routers/espacio.py \
  app/vectorization/routers/kpis.py \
  app/vectorization/schemas/vectorizacion.py \
  main.py scripts/seed_kpis.py \
  ../../infrastructure/chroma-viewer/app.py \
  ../../shared/models/kpi.py ../../shared/schemas/kpi.py
```

Salida: `PYCOMPILE_EXIT=0` (los 13 compilan sin error).

## Backend — arranque con todos los routers cargados

```
python -c "import main; print('ROUTES:', [r.path for r in main.app.routes if 'kpis/catalogo' in r.path])"
→ ROUTES: ['/vectorizacion/kpis/catalogo']   (EXIT=0, sin NameError)
```

Arranque limpio: confirma que FEAT-002 (import + include_router de `kpis`, el DTO y
el seam `nombre`) integra sin romper los routers de FEAT previas.

## Backend — contratos ORM / schemas / firma (seam FEAT-001 ↔ FEAT-002)

```
python -c "import app.vectorization.core.kpi_indexer as m, inspect; s=inspect.signature(m.reindex_kpis).parameters; print('SIG_OK:', 'client' in s and 'collection' not in s)"
→ SIG_OK: True   (reindex_kpis(db, *, client=None), sin collection=)

python (PYTHONPATH=worktree) -c "from shared.models.kpi import KPI; print('COLS:', [c.name for c in KPI.__table__.columns])"
→ COLS: ['kpi_id','nombre','polaridad_rendimiento','tipo_objetivo_estrategico',
         'formula_metrica_calculo','descripcion_ampliada_educativa',
         'comportamiento_direccional_causalidad','razon_estrategica_decisiones',
         'texto_contexto_rag_vectorial']   (9 columnas = kpi_id + 8)

python -c "from shared.schemas import KPIBase, KPICreate, KPIUpdate, KPIRead; print('FIELDS:', sorted(KPIRead.model_fields.keys()))"
→ FIELDS: 9 campos (kpi_id + los 8 snake_case), sin ImportError
```

## Backend — pytest de las funciones puras (leer_kpis_csv)

```
pip install -r requirements-dev.txt   # pytest 9.1.1
python -m pytest tests/ -q
→ ....  4 passed in 0.57s   (PYTEST_EXIT=0)
```

Casos: caso feliz, cabecera incorrecta (aborta), `KPI` vacío (aborta),
`Texto_Contexto_RAG_Vectorial` vacío (aborta).

## Frontend — build de TypeScript (seam FEAT-002 ↔ FEAT-003)

```
npm run build
→ ✓ built in 1.04s ; Generated .output/nitro.json   (BUILD_EXIT=0)
```

Sin errores de TypeScript tras el cableado del catálogo real y la reconciliación
de `carga.ts`.

## Seam de contrato entre FEATs (lectura de control)

- `git grep nombre_kpi` en backend vivo (`services/analysis-service/app`,
  `infrastructure/chroma-viewer/app.py`, `shared`): solo 1 hit, un docstring de
  `kpi_indexer.py`. Ningún código lee ya `nombre_kpi`.
- `git grep nombre_kpi` en `pixel-perfect-pixel/src`: 0 hits en código.
- `git grep ChartBar` en `pixel-perfect-pixel/src`: solo comentarios de
  `kpis.ts`/`iconos.ts`; el fallback real es `BarChart2`.
- **DTO del catálogo alineado 8-a-8**: la `interface KpiCatalogoDTO` de
  `src/api/kpis.ts` y la clase `KpiCatalogoDTO` de `schemas/vectorizacion.py`
  comparten exactamente los mismos 8 campos string
  (`id, nombre, descripcion_ampliada_educativa, polaridad_rendimiento,
  tipo_objetivo_estrategico, formula_metrica_calculo,
  comportamiento_direccional_causalidad, razon_estrategica_decisiones`).
- **Propuestas/confirmar**: `carga.ts` lee `kpi_id, nombre, score` de
  `PropuestaKPI` y `kpi_id, nombre, score` de `KpiAgregado`, consistente con las
  clases Pydantic homónimas del backend (que además exponen
  `polaridad_rendimiento`/`tipo_objetivo_estrategico`, ignorados sin daño por el
  front). `confirmarKpis` lee `.nombre` en ambas ramas del `.map`.

**Resultado**: las costuras entre FEAT-001/002/003 integran; backend arranca con
todos los routers, los contratos (ORM, schemas, DTO del catálogo, propuestas/
confirmar) están alineados, pytest verde y build del frontend verde. No se
requirió ningún arreglo de costura en esta iteración.
