# Esquema de Base de Datos — Indagata (schema `tt_rag`)

> **Qué es este documento:** resumen de las tablas de PostgreSQL que el backend **usa
> realmente** (a través de los modelos ORM en `api/models/models_instrumentos.py`), para qué
> sirve cada una y cómo se relacionan.
> **Fuente:** `api/models/models_instrumentos.py` (verificado en código). Todas las tablas viven
> en el schema `tt_rag`.
> **Fecha:** 2026-09-20

---

## 1. Vista general

`InstrumentoProcesado` es la **tabla central (agregado raíz)**: casi todas las demás apuntan a ella
por FK y se borran en cascada con ella. Alrededor giran dos grupos:

- **Catálogo maestro (persistente, se consulta):** `usuarios`, `kpi`.
- **Operacional (por instrumento, se crea/borra):** `metadatos_dc`, `etl_propuesta`,
  `metadatos_enriquecidos`, `kpi_inferido`, `permiso_instrumento`, `pipeline_ingesta_log`,
  `improvement_opportunity`.

```
                 usuarios ──1:N── permiso_instrumento ──N:1──┐
                                                              │
     kpi ──1:N── kpi_inferido ──N:1──────────────────────────┤
                                                              │
                                    ┌─────────────────────────▼─────────────────────────┐
                                    │            instrumento_procesado (RAÍZ)            │
                                    └─────────────────────────┬─────────────────────────┘
       metadatos_dc ──1:1───────────────────────────────────┤
       metadatos_enriquecidos ──1:1─────────────────────────┤
       etl_propuesta ──1:N──────────────────────────────────┤
       pipeline_ingesta_log ──1:N───────────────────────────┤
       improvement_opportunity ──1:N────────────────────────┘
```

---

## 2. Tablas y para qué se usan

### `usuarios` (catálogo, solo lectura en este módulo)
Propietarios de los instrumentos. Este módulo solo la **lee** (para resolver el nombre del creador
y validar propiedad); no crea usuarios.
- PK: `usuario_id`. Columnas: `usuario` (único), `password_hash`, `creado_en`.

### `kpi` (catálogo maestro)
Catálogo de indicadores educativos (fórmulas, umbrales, dirección deseada). La API lo consulta;
no lo gestiona. Es el catálogo contra el que el SIS **infiere** KPIs (no inventa fuera de él).
- PK: `kpi_id`. Columnas: `nombrekpi`, `descripcion`, `direccion_deseada`, `formula`, umbrales, `unidad`, `activo`.

### `instrumento_procesado` — RAÍZ
Registro maestro de cada instrumento cargado. Controla el **estado del pipeline** y guarda las
**rutas de artefactos** generados.
- PK: `instrumento_id`.
- Columnas clave: `nombre`, `tipo_instrumento` (encuesta/entrevista/prueba_estandarizada),
  `estado` (pendiente → metadata_registrado → etl_pendiente_limpieza → etl_pendiente_enriquecimiento
  → etl_aprobado), `plataforma`, y rutas: `ruta_archivo` (original), `ruta_json` (consolidado),
  `ruta_sav`, `ruta_texto_limpio`, `ruta_codebook`. Fechas: `creado_en`, `fecha_procesamiento`.
- CheckConstraints sobre `tipo_instrumento` y `estado`.

### `metadatos_dc` (1:1 con el instrumento)
Los 13 campos **Dublin Core** del instrumento (título, creador, materia, descripción, etc.).
Contexto documental que alimenta el consolidado.
- PK: `metadatos_id`. FK: `instrumento_id` (ON DELETE CASCADE, UNIQUE → 1:1).
- Nota: `dc_subject` se guarda como JSON array serializado en un `Text`.

### `etl_propuesta` (1:N con el instrumento)
Las **propuestas del SIS** para el usuario: transformaciones de limpieza, metadatos enriquecidos y
KPIs sugeridos, con su decisión (`estado_decision`: pendiente/aceptada/rechazada).
- PK: `propuesta_id`. FK: `instrumento_id` (CASCADE).
- CheckConstraints sobre `tipo` y `estado_decision`.

### `metadatos_enriquecidos` (1:1 con el instrumento)
Los metadatos semánticos **aprobados** (constructo/rol/tags por variable), en un campo `JSONB`.
Insumo del RAG.
- PK: `enriquecido_id`. FK: `instrumento_id` (CASCADE, UNIQUE → 1:1).

### `kpi_inferido` (N:1 con instrumento y con kpi)
Los KPIs **aceptados** que quedan asociados al instrumento, con evidencia y score.
- PK: `kpi_inferido_id`. FK: `instrumento_id` (CASCADE) y `kpi_id` (→ catálogo `kpi`).
- `origen` ∈ (registro_manual, propuesta_etl).

### `permiso_instrumento` (control de acceso)
Define el **propietario** de cada instrumento (escritura/eliminación solo del propietario).
- PK: `permiso_id`. FK: `instrumento_id` (CASCADE) y `usuario_id` (CASCADE).
- `rol` fijo a 'propietario' (CheckConstraint); UNIQUE(instrumento, usuario).

### `pipeline_ingesta_log` (1:N, interno)
Log interno del pipeline (etapas, modelo LLM/embedding, nº de chunks, errores). **Nunca se expone**
por la API.
- PK: `log_id`. FK: `instrumento_id` (CASCADE). `resultado` ∈ (en_proceso, exitoso, error).

### `improvement_opportunity` (1:N con el instrumento)
Las **oportunidades de mejora** emitidas por el SIS (S8): título, descripción, evidencia (`JSONB`),
regla propuesta (`JSONB`), confianza, estado (proposed…).
- PK: `opportunity_id`. FK: `instrumento_id` (CASCADE).
- CheckConstraints sobre `scope` y `estado`.

---

## 3. Relaciones (resumen)

| Relación | Cardinalidad | Borrado | Notas |
|---|---|---|---|
| instrumento_procesado → metadatos_dc | 1:1 | cascade | FK + UNIQUE |
| instrumento_procesado → metadatos_enriquecidos | 1:1 | cascade | FK + UNIQUE |
| instrumento_procesado → etl_propuesta | 1:N | cascade | |
| instrumento_procesado → kpi_inferido | 1:N | cascade | |
| instrumento_procesado → permiso_instrumento | 1:1 (hoy) | cascade | UNIQUE(instrumento, usuario) |
| instrumento_procesado → pipeline_ingesta_log | 1:N | cascade | interno |
| instrumento_procesado → improvement_opportunity | 1:N | cascade | relación por FK; se limpia manualmente en el reanálisis |
| usuarios → permiso_instrumento | 1:N | cascade | |
| kpi → kpi_inferido | 1:N | — | catálogo referenciado |

**Cascada de borrado:** eliminar un `instrumento_procesado` borra en cascada sus metadatos, propuestas,
KPIs inferidos, permisos, logs y (por limpieza explícita del host) sus oportunidades de mejora.
Los catálogos `usuarios` y `kpi` **no** se ven afectados.

---

## 4. Notas honestas / observaciones

- **`improvement_opportunity` es asimétrica en el ORM:** tiene FK al instrumento pero (a diferencia
  de las otras hijas) su borrado se gestiona de forma explícita en el host (`_borrar_analisis_previo`),
  no por `relationship` cascade del agregado raíz. Funciona, pero conviene tenerlo presente.
- **`kpi_inferido` ↔ `kpi`:** hay FK pero la resolución del nombre del KPI se hace vía el
  `relationship KpiInferido.kpi` (añadido en la refactorización) — antes era SQL crudo repetido.
- **Tablas de catálogo NO gestionadas por este módulo:** el schema `tt_rag` incluye además tablas de
  seed como `variable` y `kpi_variable` (relación KPI↔variable) que existen en la BD y aportan datos
  de dominio, pero **este backend no las modela ni las escribe**; solo el catálogo `kpi` se consulta.
- **Vectorización (futuro):** el estado `vectorizado` y las tablas de vectores/logs RAG del diseño
  objetivo (ChromaDB, `documento_vectorizado`, `rag_log`) **no** están implementados; hoy no se usan.

---

## 5. Referencias

- Modelos ORM (fuente de verdad): `api/models/models_instrumentos.py`.
- Constantes de dominio (tipos/estados): `api/core/domain_constants.py`.
- Arquitectura del backend: `../../ARCHITECTURE_AUDIT_REPORT.md`.
- Qué hace el SIS con estos datos: `ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md`.
