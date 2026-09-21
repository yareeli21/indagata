---
inclusion: manual
---

# Arquitectura — Indagata

**Actualizado:** 2026-09-20
**Estado:** Documento vigente. Consolida y reemplaza a `arquitectura_definitiva.md` e `inspeccion_estructura.md`.
**Complementos:** `modelo_conocimiento.md` y `chunking_strategy.md` (diseño conceptual del RAG principal, futuro).
**Fuente de verdad del backend actual:** `backend/ARCHITECTURE_AUDIT_REPORT.md`.

> ⚠️ Documentos previos (`arquitectura_definitiva.md`, `inspeccion_estructura.md`) describían un
> prototipo anterior (Jinja2 + `routers/login.py`, `routers/chat.py`, `services/limpieza_service.py`,
> cookies sin firmar, etc.) que **ya no corresponde al código actual**. Se consolidaron aquí.

---

## 1. Qué es Indagata

Plataforma para **gestión y consulta de instrumentos de investigación educativa** (encuestas,
entrevistas, pruebas estandarizadas). El objetivo final es una plataforma RAG: los instrumentos se
cargan, se procesan con asistencia LLM hasta producir conocimiento estructurado (JSON consolidado),
y ese conocimiento alimenta un RAG para consulta en lenguaje natural.

Stack real actual:
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (psycopg3), Pydantic v2.
- **Base de datos:** PostgreSQL (schema `tt_rag`).
- **LLM:** Ollama local (HTTP síncrono vía `services/ollama_client.py`).
- **Vectorización / RAG principal:** dependencias (ChromaDB, LangChain, sentence-transformers) declaradas pero **no implementadas** (funcionalidad futura).

---

## 2. Arquitectura del backend (estado real)

Backend en capas + un servicio de dominio complejo aislado (el SIS).

```
routers      → HTTP: endpoints, validación in/out con schemas
   │
dependencies → Autenticación y acceso (hoy en MODO DESARROLLO; JWT preparado, pendiente)
   │
services     → Lógica de negocio del host
   ├── api/services/   → carga, visualización, artefactos, mapeo SIS→BD, extracción
   └── services/       → sis_adapter (acople al SIS) + ollama_client
   │
survey_intelligence/  → SIS: servicio interno de dominio (hexagonal), aislado del framework
   │                    Instrumento → JSON canónico → JSON consolidado
models       → ORM SQLAlchemy (schema tt_rag)
```

### Módulos reales
| Módulo | Ubicación | Rol |
|---|---|---|
| Routers de carga | `api/routers/routers_carga.py` | Wizard: upload → metadata → analyze → approve/cleaning → approve/enrichment |
| Routers de visualización | `api/routers/routers_visualizacion.py` | Catálogo KPIs, listado, detalle, descarga, delete |
| Servicios de carga | `api/services/services_carga.py` + `carga_sis_mapping.py` + `carga_artifacts.py` | Orquestación del wizard, mapeo SIS→BD, generación de artefactos |
| Servicios de visualización | `api/services/services_visualizacion.py` | Consulta y borrado |
| Extracción | `api/services/extraction/` | Módulo unificado de extracción documental (dispatch por formato) |
| SIS | `survey_intelligence/` | Pipeline S1..S10 (incl. entrevistas), contratos, engine, ports, export |
| Acople LLM | `services/sis_adapter.py`, `services/ollama_client.py` | Único punto de acople host↔SIS + cliente Ollama |
| Config | `api/core/config.py` | pydantic-settings desde `.env` |
| BD | `postgres/init/*.sql` | Schema `tt_rag` + seed (KPIs, variables) |

### El SIS (Survey Intelligent System)
Servicio interno de dominio (NO microservicio) con patrón **ports & adapters**. Aislado: no importa
FastAPI ni SQLAlchemy. Se consume solo por `services/sis_adapter.py`. Produce el JSON canónico y el
consolidado; **ahí termina su responsabilidad**. Detalle en `backend/ARCHITECTURE_AUDIT_REPORT.md` y
en `backend/survey_intelligence/pipeline/README.md`.

---

## 3. Componentes que se conservan (valor real)

- **Esquema de BD** (`postgres/init/01_schema.sql`): cubre el dominio completo (instrumentos,
  vectorización, logs RAG, KPIs, variables, trazabilidad). La pieza más madura.
- **Seed data** (`02_seed.sql`): ~50 KPIs educativos con fórmulas/umbrales y ~90 variables. Valor de dominio real.
- **Config centralizada** (`core/config.py`): patrón correcto con pydantic-settings.
- **`core/security.py`** (bcrypt): correcto; se activará con el JWT.
- **Prompts del LLM** dentro del SIS (audit/enrichment/kpi/results/interview): bien construidos.

---

## 4. Deuda técnica y pendientes (estado real, post-refactor)

Tras las refactorizaciones documentadas en `CHANGELOG.md` (Fases A-G), la deuda restante es:
- **Autenticación en MODO DESARROLLO.** `get_current_user` devuelve un usuario fijo; el bloque JWT
  está escrito pero comentado. CORS abierto (`*`). **Pendiente:** activar login real (JWT) + endurecer CORS.
- **Autorización duplicada** entre `dependencies` y `PermissionService` — centralizar al activar el JWT.
- **RAG principal ausente** — ChromaDB/LangChain/embeddings sin implementar (funcionalidad futura).
- **Flecos menores:** `KPI.activo` (bool sobre Integer), docstring de `delete()` que menciona ChromaDB (no-op).

---

## 5. Arquitectura objetivo (visión)

Plataforma educativa RAG donde los usuarios pueden **cargar** instrumentos y procesarlos con el SIS,
**consultar** en lenguaje natural sobre el contenido vectorizado, y **monitorear** KPIs educativos.

```
Instrumento → Extracción → SIS (ETL inteligente) → JSON Canónico → JSON Consolidado
   → [FRONTERA SIS] → RAG Principal → Chunks enriquecidos → Embeddings → Índice → Q&A
```

Principio de frontera: el **SIS produce** conocimiento estructurado; el **RAG principal consume**
ese conocimiento. No se fusionan. Ver `modelo_conocimiento.md` (planos operativo/semántico) y
`chunking_strategy.md` (Intelligent Enriched Chunking) para el diseño conceptual del RAG.

### Componentes futuros (no implementados)
- **Módulo de vectorización:** lee el JSON consolidado, aplica chunking enriquecido, genera embeddings
  (sentence-transformers), indexa en ChromaDB. Estado objetivo `vectorizado`.
- **Módulo RAG de consulta:** embedding de la pregunta → top-K chunks → contexto → Ollama → respuesta con fuentes.
- **Autenticación JWT** + roles.
- **Pipeline de pruebas estandarizadas** en el SIS (reglas psicométricas).

---

## 6. Multi-instrumento (SIS)

Un solo SIS con un orquestador único (`facade.py`) + estrategia por instrumento (`survey_intelligence/pipelines/`, `select_pipeline`):
- **Encuestas** (tabular): implementado (S1..S9 + S8b).
- **Entrevistas** (narrativo): implementado (vía documento + S10: diarización + NLP + consolidado con participantes/turnos/temas).
- **Pruebas estandarizadas:** estrategia esqueleto (vía documento, sin reglas psicométricas aún).

Cómo está organizado y cómo extender: `backend/survey_intelligence/docs/ARQUITECTURA_SIS.md` y `backend/survey_intelligence/docs/GUIA_EXTENSION_INSTRUMENTOS.md`.
