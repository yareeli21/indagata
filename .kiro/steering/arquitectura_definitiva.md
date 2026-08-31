---
inclusion: manual
---

# Arquitectura Definitiva — Indagata
## Plataforma Inteligente RAG para Información Educativa

**Versión:** 1.0  
**Fecha:** Agosto 2026  
**Tipo de documento:** Arquitectura objetivo definitiva (pre-implementación)

---

## 1. Gap Analysis

Comparación directa entre la visión del proyecto y el estado actual del repositorio.

### 1.1 Pipeline de procesamiento

| Etapa | Visión | Estado actual | Brecha |
|---|---|---|---|
| 1. Recepción y almacenamiento | Archivo original con trazabilidad | Implementado (guarda en `storage/raw`) | Parcial: no registra hash MD5, no guarda en `raw_data` |
| 2. Metadatos básicos | ISO 15836 (Dublin Core) | Implementado (`MetadatosBase` Pydantic, 14 campos) | Parcial: no está alineado explícitamente con Dublin Core, faltan campos como `dc:identifier`, `dc:coverage` |
| 3. Limpieza por tipo | LLM + reglas específicas + validación humana | Chat asistido funcional; limpieza automática es stub | Medio: el chat funciona, las reglas por tipo no existen |
| 4. Estandarización | Metadatos generales + específicos por tipo | Solo metadatos generales implementados | Medio: faltan metadatos específicos por tipo de instrumento |
| 5. Inferencia de KPIs | KPIs detectados + métricas + evidencia | No implementado. Tabla `pregunta_kpi` existe pero vacía | **Ausente** |
| 6. JSON canónico | Estructura completa (meta + trazabilidad + KPIs + chunking) | `MetadatosCompletos` parcial, sin KPIs ni información de chunking | **Ausente** |
| 7. Generación de chunks enriquecidos | Enriched Chunking con metadatos + KPIs | No implementado | **Ausente** |
| 8. Indexación vectorial | ChromaDB con metadatos ricos | Instalado pero cero código escrito | **Ausente** |
| 9. Disponibilidad RAG | Recuperación semántica funcional | Endpoint `/chat/consultar` es mockup | **Ausente** |

### 1.2 Consulta RAG

| Funcionalidad | Visión | Estado actual | Brecha |
|---|---|---|---|
| Consulta en lenguaje natural | Respuestas con evidencia recuperada | Mockup hardcodeado | **Ausente** |
| Mostrar fuentes utilizadas | Trazabilidad hasta instrumento original | No implementado | **Ausente** |
| Chunks como evidencia | Mostrar fragmentos recuperados | No implementado | **Ausente** |
| Log de consultas | Auditoría en `rag_log` | Tabla existe, servicio ausente | **Ausente** |

### 1.3 KPIs y dashboards

| Funcionalidad | Visión | Estado actual | Brecha |
|---|---|---|---|
| Visualización de KPIs | Dashboard con tendencias, filtros | Lista estática de 50 KPIs (tarjetas HTML) | **Mínimo** |
| Análisis por periodo | Gráficas temporales | No implementado | **Ausente** |
| Análisis por institución | Filtro institucional | No implementado | **Ausente** |
| Análisis por tipo de instrumento | Filtro transversal | No implementado | **Ausente** |
| KPIs inferidos por instrumento | Vinculación instrumento → KPI | No implementado | **Ausente** |

### 1.4 Frontend

| Funcionalidad | Visión | Estado actual | Brecha |
|---|---|---|---|
| Tecnología | React moderno | Jinja2 + JS vanilla | **Reconstruir** |
| Gestión de instrumentos | CRUD completo + descarga original | Carga y catálogo básico; sin descarga | Parcial |
| Proceso de limpieza | UI paso a paso con validación humana | Chat modal funcional pero sin indicador de progreso claro | Parcial |
| Validación de metadatos | Formulario guiado por tipo | Formulario genérico único | Parcial |
| Consulta semántica | Interfaz RAG con fuentes | Pantalla vacía con mockup | **Reconstruir** |
| Dashboards | Gráficas interactivas | Inexistente | **Ausente** |
| Administración de usuarios | CRUD usuarios + roles | Solo admin con seed data | **Ausente** |

### 1.5 Seguridad

| Aspecto | Visión | Estado actual | Brecha |
|---|---|---|---|
| Autenticación | Sesiones seguras | Cookie sin firmar, sin middleware de validación | **Crítico** |
| Autorización | Rutas protegidas | Ninguna ruta está protegida | **Crítico** |
| Roles de usuario | Investigador / Docente / Admin | Solo `admin` en seed | **Ausente** |

---

## 2. Componentes que deben conservarse

Estos componentes están bien diseñados y representan trabajo real que no debe descartarse.

### Esquema de base de datos
`postgres/init/01_schema.sql` es la pieza más madura del proyecto. Las 10 tablas cubren correctamente el dominio completo: instrumentos, vectorización, logs RAG, KPIs, variables, instituciones y versionado de prompts. Se conserva íntegro con extensiones menores.

### Seed data
`postgres/init/02_seed.sql` — 50 KPIs educativos con fórmulas, umbrales y dirección deseada. ~90 variables estandarizadas. Son valor de dominio real, costoso de regenerar.

### Pipeline de metadatos base
`services/metadatos_service.py` y `schemas/metadatos.py` — La validación Pydantic de metadatos Nivel 1 (14 campos) y la lógica de dos niveles (base + enriquecidos) es correcta. Se extiende, no se reemplaza.

### Prompts del LLM
Los system prompts en `limpieza_service.py` y `metadatos_enriquecidos_service.py` están bien construidos: incluyen contexto del instrumento, instrucciones concretas y marcadores de estado. Se mantienen como base para el sistema de versionado de prompts.

### Configuración centralizada
`core/config.py` con pydantic-settings es el patrón correcto. Se extiende con nuevas variables.

### Seguridad de contraseñas
`core/security.py` con bcrypt es correcto y suficiente para el backend de autenticación.

### Servicio de KPIs
`services/kpi_service.py` y `models/kpi.py` — consulta correcta y modelo bien tipado. Se extiende para incluir KPIs inferidos por instrumento.

### Infraestructura Docker
`docker-compose.yaml` y `Dockerfile` son una base funcional. Se extiende con el servicio React y los workers de procesamiento.

---

## 3. Componentes que deben refactorizarse

Existen pero necesitan cambios estructurales importantes para alcanzar la visión.

### `core/ollama_client.py`
De httpx síncrono a `httpx.AsyncClient` con soporte de streaming SSE. El bloqueo síncrono actual es incompatible con un sistema que procesará múltiples instrumentos y servirá consultas RAG concurrentes.

### `routers/cargar.py` + `services/cargar_service.py`
El pipeline de carga actual es lineal y síncrono. Debe refactorizarse para:
- Separar la recepción del archivo del procesamiento (que pasa a ser asíncrono o en background).
- Incorporar las nuevas etapas: inferencia de KPIs y generación de JSON canónico.
- Usar `BackgroundTasks` de FastAPI para las etapas de procesamiento pesado.

### `services/metadatos_enriquecidos_service.py`
Debe incorporar lógica específica por tipo de instrumento. La estructura actual es genérica. Se bifurca en metadatos específicos para encuestas, entrevistas y pruebas estandarizadas.

### `services/limpieza_service.py`
La limpieza automática debe implementarse con pandas. El chat asistido debe añadir un mecanismo explícito de validación humana cuando la confianza del LLM es baja (basado en los marcadores de respuesta del LLM).

### Autenticación (`routers/login.py`, `services/login_service.py`)
Migrar de cookie simple a JWT firmado con `python-jose`. Añadir:
- Dependency `get_current_user` inyectable en cada router.
- Soporte de roles (`admin`, `investigador`, `docente`).
- Middleware que proteja todas las rutas excepto `/login`.

### Modelos ORM (`models/instrumento.py`)
El modelo `InstrumentoProcesado` debe añadir:
- Columna `codigo` persistido (ej. `ENC-001`).
- Columna `ruta_original` para descarga del archivo original.
- Relación ORM con `KpiInferido` (tabla `pregunta_kpi`).

### Esquema de base de datos — extensiones menores
Agregar a `instrumento_procesado`: `codigo VARCHAR(20) UNIQUE`, `ruta_original TEXT`.  
Agregar a `usuarios`: columna `rol VARCHAR(20) DEFAULT 'investigador'`.

---

## 4. Componentes que deben reconstruirse desde cero

### Frontend completo
El frontend en Jinja2 + JS vanilla debe reemplazarse con React. La razón no es tecnológica sino funcional: los dashboards interactivos, el flujo de pipeline paso a paso con validación humana, y la interfaz de chat RAG con fuentes son imposibles de mantener de forma sostenible en HTML + JS vanilla. Se construye como una SPA desacoplada que consume la API de FastAPI.

### `routers/chat.py` — Módulo RAG
El router actual retorna un hardcode. Debe reconstruirse desde cero como un módulo RAG real:
- Recepción de pregunta + filtros opcionales (tipo, institución, periodo).
- Generación de embedding de consulta.
- Recuperación de chunks desde ChromaDB con metadatos.
- Construcción del prompt RAG con contexto recuperado.
- Llamada async a Ollama.
- Retorno de respuesta + chunks fuente + metadatos de trazabilidad.
- Registro en `rag_log`.

### Módulo de vectorización (nuevo)
`services/vectorizacion_service.py` — No existe ninguna línea. Debe construirse completo:
- Leer el JSON canónico del instrumento.
- Aplicar Enriched Chunking (ver sección 5 para definición detallada).
- Generar embeddings con `sentence-transformers`.
- Indexar en ChromaDB con metadatos ricos.
- Registrar en `documento_vectorizado`.

### Módulo de inferencia de KPIs (nuevo)
`services/kpi_inferencia_service.py` — No existe. Debe construirse:
- Recibir el instrumento procesado (preguntas + metadatos).
- Usar el LLM para mapear cada pregunta/sección a KPIs del catálogo.
- Calcular `score_inferencia` (0-1).
- Guardar en `pregunta_kpi`.

### JSON canónico (nuevo)
`services/json_canonico_service.py` — No existe. Estructura de salida unificada para todos los instrumentos (ver sección 5).

### Módulo de dashboards (nuevo)
`routers/dashboard.py` + `services/dashboard_service.py` — No existe. Consultas agregadas sobre `valor_variable`, `kpi`, `instrumento_procesado` y `rag_log` para alimentar las visualizaciones.

### Módulo de administración de usuarios (nuevo)
`routers/usuarios.py` + `services/usuario_service.py` — CRUD completo de usuarios con roles.

---

## 5. Arquitectura objetivo recomendada

### 5.1 Visión general de capas

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND — React SPA                         │
│                                                                   │
│  /login   /instrumentos   /cargar   /chat   /dashboard   /admin  │
│                                                                   │
│  Vite + React 18 + React Router + TanStack Query                 │
│  Recharts (dashboards)  │  Tailwind CSS                          │
└──────────────────────────────────┬──────────────────────────────┘
                                   │ HTTPS + JWT Bearer Token
┌──────────────────────────────────▼──────────────────────────────┐
│                     BACKEND — FastAPI (Python 3.12)              │
│                                                                   │
│  Routers:                                                         │
│  /auth  /instrumentos  /cargar  /rag  /kpis  /dashboard  /admin  │
│                                                                   │
│  Middleware: JWT validation  │  CORS  │  Error handlers           │
└──────────────┬───────────────────────────────┬───────────────────┘
               │                               │
    ┌──────────▼──────────┐       ┌────────────▼───────────┐
    │   SERVICE LAYER      │       │   BACKGROUND WORKERS   │
    │                      │       │                        │
    │  PipelineService     │       │  limpieza_worker       │
    │  MetadatosService    │       │  kpi_inferencia_worker │
    │  LimpiezaService     │       │  vectorizacion_worker  │
    │  KpiInferenciaService│       │                        │
    │  JsonCanonicoService │       │  (FastAPI BackgroundTasks
    │  VectorizacionService│       │   o Celery para prod)  │
    │  RAGService          │       └────────────────────────┘
    │  DashboardService    │
    │  OllamaClient(async) │
    └──────┬───────────────┘
           │
    ┌──────▼───────────────────────────────────────────┐
    │               PERSISTENCE LAYER                   │
    │                                                   │
    │  PostgreSQL 16          ChromaDB (local)          │
    │  (SQLAlchemy ORM)       (langchain-chroma)        │
    │                                                   │
    │  Schema: tt_rag         Collections:              │
    │  - instrumento_procesado  - instrumentos_edu     │
    │  - raw_data             Metadatos por chunk:      │
    │  - kpi + pregunta_kpi   - instrumento_id         │
    │  - variable + valor     - tipo_instrumento       │
    │  - documento_vectorizado - kpis_asociados        │
    │  - rag_log              - periodo + institucion  │
    │  - prompt               - tipo_chunk             │
    │  - usuarios             - dc_*  (Dublin Core)    │
    │  - instituciones        - score_relevancia       │
    └──────────────────────────────────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │       STORAGE (volúmenes)    │
    │                             │
    │  /storage/raw   — originales│
    │  /storage/json  — canónicos │
    │  /storage/sav   — SPSS      │
    │  /chromadb/data — vectores  │
    └─────────────────────────────┘
```

### 5.2 Flujo del pipeline de procesamiento completo

```
USUARIO CARGA ARCHIVO
        │
        ▼
[1] Recepción
    - Guardar en /storage/raw
    - Registrar en raw_data (hash MD5, mime, tamaño)
    - Crear instrumento_procesado (estado: "ingresado")
        │
        ▼
[2] Limpieza asistida por LLM          ← estado: "limpio"
    - Limpieza automática (pandas)
    - Chat LLM por tipo de instrumento
    - Validación humana si confianza < umbral
        │
        ▼
[3] Metadatos base ISO 15836           ← estado: "metadatos_base"
    - Formulario guiado por tipo
    - 14 campos Dublin Core
    - Validación Pydantic
        │
        ▼
[4] Metadatos enriquecidos (LLM)       ← estado: "estandarizado"
    - Chat LLM para metadatos específicos por tipo
    - Dimensiones, contexto, limitaciones, subgrupos
        │
        ▼
[5] Inferencia de KPIs (LLM)           ← estado: "kpis_inferidos"
    - Mapeo pregunta → KPI con score
    - Guardado en pregunta_kpi
        │
        ▼
[6] JSON canónico                      ← estado: "json_generado"
    - Compilar meta + trazabilidad + KPIs + chunking info
    - Guardar en /storage/json/{id}.json
        │
        ▼
[7] Vectorización                      ← estado: "vectorizado"
    - Enriched Chunking
    - Embeddings (sentence-transformers)
    - Indexación en ChromaDB
    - Registro en documento_vectorizado
        │
        ▼
DISPONIBLE PARA CONSULTA RAG
```

Estados del instrumento (columna `estado`):
`ingresado → limpio → metadatos_base → estandarizado → kpis_inferidos → json_generado → vectorizado → error`

### 5.3 JSON canónico — Estructura

```json
{
  "schema_version": "1.0",
  "instrumento_id": 42,
  "codigo": "ENC-042",
  "trazabilidad": {
    "hash_md5": "...",
    "nombre_original": "encuesta_desercion_2024.xlsx",
    "fecha_carga": "2024-03-15T10:00:00",
    "ruta_original": "/storage/raw/...",
    "usuario_carga": "admin"
  },
  "dublin_core": {
    "dc_title": "...",
    "dc_creator": "...",
    "dc_subject": [...],
    "dc_description": "...",
    "dc_publisher": "...",
    "dc_date": "2024",
    "dc_type": "Dataset",
    "dc_format": "xlsx",
    "dc_identifier": "IND-ENC-042",
    "dc_language": "es",
    "dc_coverage": "...",
    "dc_rights": "..."
  },
  "especifico": {
    "tipo": "encuesta",
    "poblacion": "...",
    "n_preguntas": 45,
    "escala": "Likert 1-5",
    "dimensiones": [...]
  },
  "kpis_inferidos": [
    {
      "kpi_id": 3,
      "nombre_kpi": "Tasa de Deserción",
      "preguntas_relacionadas": ["P12", "P13"],
      "score_inferencia": 0.87,
      "evidencia": "..."
    }
  ],
  "para_chunking": {
    "resumen": "...",
    "hallazgos_principales": [...],
    "unidades_semanticas": [
      {
        "id": "chunk_001",
        "tipo": "dimension",
        "titulo": "Dimensión: Satisfacción académica",
        "contenido": "...",
        "preguntas": [...],
        "kpis": [3, 7]
      }
    ]
  }
}
```

### 5.4 Enriched Chunking — Estrategia

Cada chunk que se indexa en ChromaDB contiene:

**Contenido textual:**
- Texto semántico de la unidad (sección, dimensión, hallazgo o resumen).

**Metadatos por chunk (filtros ChromaDB):**

| Campo | Propósito |
|---|---|
| `instrumento_id` | Trazabilidad al instrumento fuente |
| `tipo_instrumento` | encuesta / entrevista / prueba |
| `tipo_chunk` | resumen / hallazgo / unidad_semantica |
| `kpis_ids` | Lista de KPI IDs asociados (filtro semántico) |
| `periodo` | Para filtros temporales en dashboards |
| `institucion_id` | Para filtros institucionales |
| `dc_language` | Para filtros de idioma |
| `score_relevancia` | Calculado durante indexación |
| `codigo_instrumento` | ENC-042 (referencia legible) |

**Tipos de chunk por instrumento:**
- `resumen_instrumento` — 1 por instrumento. Descripción global con todos los metadatos Dublin Core.
- `sintesis_hallazgo` — 1-5 por instrumento. Hallazgos principales detectados por el LLM.
- `unidad_semantica` — N por instrumento. Secciones, dimensiones o grupos de preguntas semánticamente cohesivos.

### 5.5 Organización de ChromaDB

Una sola colección: `instrumentos_edu`.

Justificación: una colección única permite consultas transversales entre tipos de instrumentos, que es el caso de uso principal. Los filtros por `tipo_instrumento`, `kpis_ids`, `periodo` e `institucion_id` en los metadatos de los chunks permiten búsquedas acotadas sin necesidad de múltiples colecciones.

Para producción con > 100k chunks: evaluar colecciones por tipo de instrumento con búsqueda federada, pero no es necesario para el alcance del proyecto de titulación.

### 5.6 Flujo RAG

```
Pregunta del usuario + filtros opcionales
        │
        ▼
Generar embedding de la pregunta
(sentence-transformers: paraphrase-multilingual-MiniLM-L12-v2)
        │
        ▼
Búsqueda en ChromaDB: top-8 chunks
Filtros opcionales: tipo_instrumento, kpi_id, periodo, institucion_id
        │
        ▼
Re-ranking de chunks (por relevancia + diversidad de fuentes)
        │
        ▼
Construir prompt RAG:
  [System]: Eres un asistente educativo. Responde SOLO con la evidencia proporcionada.
  [Context]: {chunks seleccionados con metadatos}
  [Question]: {pregunta del usuario}
        │
        ▼
Llamada async a Ollama (streaming SSE)
        │
        ▼
Retornar:
  - respuesta (streamed)
  - chunks fuente con metadatos (instrumento, tipo, KPIs)
  - instrumentos originales referenciados
  - session_id para historial
        │
        ▼
Registrar en rag_log (pregunta, contexto, respuesta, latencia, modelo)
```

---

## 6. Roadmap de implementación por fases

### Fase 1 — Fundación segura (2 semanas)
Hacer que lo que existe funcione correctamente.

- [ ] Implementar autenticación JWT con `python-jose`. Middleware de validación en todos los routers.
- [ ] Añadir roles a `usuarios` (admin, investigador, docente).
- [ ] Migrar `ollama_client.py` a async.
- [ ] Implementar manejo global de errores en `main.py`.
- [ ] Completar `limpieza_service`: clasificador de columnas con pandas por tipo de instrumento.
- [ ] Persistir `codigo` en `instrumento_procesado`. Añadir `ruta_original`.
- [ ] Endpoint de descarga del archivo original.
- [ ] Activar uso de tabla `raw_data` en el servicio de carga.

### Fase 2 — Pipeline completo backend (3 semanas)
Construir las etapas que faltan del pipeline en el backend.

- [ ] Ampliar `MetadatosBase` a metadatos específicos por tipo (encuesta / entrevista / prueba).
- [ ] Alinear campos explícitamente con Dublin Core (renombrar a `dc_*`).
- [ ] `services/kpi_inferencia_service.py` — inferencia LLM + guardado en `pregunta_kpi`.
- [ ] `services/json_canonico_service.py` — compilar y guardar JSON canónico en `/storage/json/`.
- [ ] `services/vectorizacion_service.py` — Enriched Chunking + embeddings + ChromaDB + `documento_vectorizado`.
- [ ] Actualizar estados del pipeline: añadir `kpis_inferidos` y `json_generado`.
- [ ] Sistema de versionado de prompts usando tabla `prompt`.

### Fase 3 — RAG funcional (2 semanas)
Reemplazar el mockup con un RAG real.

- [ ] Reconstruir `routers/chat.py` como módulo RAG completo.
- [ ] `services/rag_service.py` con búsqueda semántica, re-ranking y construcción de prompt.
- [ ] Soporte de streaming SSE desde Ollama al cliente.
- [ ] Registro de consultas en `rag_log`.
- [ ] Endpoints de historial de consultas por usuario.
- [ ] Filtros de consulta: por tipo, institución, periodo, KPI.

### Fase 4 — Dashboards (2 semanas)
Visualización de KPIs e indicadores educativos.

- [ ] `services/dashboard_service.py` — agregaciones sobre `valor_variable`, `kpi`, `instrumento_procesado`.
- [ ] Endpoints para: KPIs por instrumento, tendencias temporales, distribución por tipo, actividad de consultas.
- [ ] Módulo de instituciones: CRUD de `instituciones`, vinculación con instrumentos.
- [ ] Módulo de variables: carga de `valor_variable` para tracking histórico.

### Fase 5 — Frontend React (3 semanas)
Reconstruir el frontend como SPA.

- [ ] Setup: Vite + React 18 + TypeScript + React Router + TanStack Query + Tailwind CSS.
- [ ] Páginas: Login, Catálogo de instrumentos, Cargar instrumento (pipeline paso a paso), Chat RAG con fuentes, Dashboard KPIs, Administración de usuarios.
- [ ] Componente de pipeline de carga: stepper visual con cada etapa, validación humana integrada.
- [ ] Componente de chat RAG: streaming de respuesta, panel lateral de fuentes con trazabilidad.
- [ ] Dashboards: gráficas con Recharts (tendencias, distribución, actividad).
- [ ] Visualización y descarga de instrumentos originales.

### Fase 6 — Calidad y cierre de titulación (1 semana)
- [ ] Pruebas de integración del pipeline completo.
- [ ] Evaluación de calidad RAG: métricas de relevancia de chunks recuperados.
- [ ] Documentación técnica de la API (FastAPI auto-docs + README).
- [ ] Demostración con 5-10 instrumentos reales procesados de extremo a extremo.

---

## 7. Priorización técnica

### Crítico — Bloqueante para cualquier demostración

1. **Vectorización y RAG real** — Sin esto, el proyecto no demuestra su propósito central. Es la única funcionalidad que diferencia este sistema de un simple gestor documental.
2. **Autenticación JWT** — Sin esto, el sistema no es presentable académicamente desde el punto de vista de seguridad.
3. **JSON canónico** — Es la representación de conocimiento del sistema. Sin él no hay chunking enriquecido ni RAG de calidad.

### Importante — Diferenciadores para titulación

4. **Inferencia de KPIs** — Vincula instrumentos con indicadores educativos reales. Es el aporte más original del sistema desde el dominio educativo.
5. **Metadatos específicos por tipo** — Da profundidad al sistema. Sin esto, todos los instrumentos se tratan igual independientemente de si son encuestas o pruebas estandarizadas.
6. **Pipeline completo end-to-end funcional** — Poder demostrar las 9 etapas con un instrumento real es el requisito mínimo de una defensa.

### Deseable — Fortalece la propuesta

7. **Dashboards** — Visualización de KPIs e indicadores. Impacto visual en la presentación.
8. **Frontend React** — Experiencia de usuario profesional. Importante para la impresión en la defensa.
9. **Streaming en el chat RAG** — Mejor experiencia de usuario. Técnicamente no es difícil una vez que el RAG base funciona.

### Opcional — Si hay tiempo

10. Roles de usuario diferenciados.
11. Evaluación automática de calidad RAG (RAGAS o similar).
12. Búsqueda federada multi-colección en ChromaDB.

---

## 8. Riesgos de arquitectura

### Riesgo 1 — Rendimiento de Ollama en procesamiento masivo (Alto)
El pipeline llama a Ollama en al menos 3 etapas por instrumento (limpieza, metadatos enriquecidos, inferencia KPIs). Si se procesan varios instrumentos en paralelo, la GPU/CPU puede saturarse.

**Mitigación:** Procesar las etapas LLM de forma secuencial por instrumento usando `BackgroundTasks`. Para producción, usar Celery con una cola que limite la concurrencia de llamadas a Ollama.

### Riesgo 2 — Calidad del RAG en español (Medio)
El modelo de embeddings y el LLM deben rendir bien en español. Modelos generalistas pueden producir respuestas imprecisas con terminología educativa especializada.

**Mitigación:** Usar `paraphrase-multilingual-MiniLM-L12-v2` para embeddings (probado en español). Para el LLM, comparar `llama3.1` con `mistral` en Ollama con un conjunto de preguntas de prueba antes de elegir el modelo final.

### Riesgo 3 — Complejidad del Enriched Chunking (Medio)
El chunking enriquecido requiere que el LLM identifique unidades semánticas dentro del instrumento. Si el instrumento es muy heterogéneo o mal estructurado, los chunks pueden ser de baja calidad, degradando el RAG.

**Mitigación:** Definir plantillas de chunking por tipo de instrumento. Para encuestas: chunking por dimensión/sección. Para entrevistas: chunking por pregunta guía. Para pruebas estandarizadas: chunking por área de competencia.

### Riesgo 4 — Migración de Jinja2 a React en paralelo (Bajo-Medio)
Mantener el backend Jinja2 mientras se construye el frontend React puede generar deuda de duplicación. 

**Mitigación:** La migración a React no debe ser gradual (mezclando Jinja2 y React). Debe ser una sustitución completa en la Fase 5. Hasta esa fase, el frontend Jinja2 sirve como MVP funcional para desarrollo y pruebas.

### Riesgo 5 — Alcance del proyecto de titulación (Alto)
El roadmap tiene 13 semanas de trabajo. Un proyecto de titulación tiene restricciones de tiempo reales.

**Mitigación:** La demostración mínima viable para titulación requiere Fases 1, 2 y 3 completas (7 semanas) y al menos los dashboards básicos. React puede mantenerse en Jinja2 mejorado si el tiempo no alcanza. El criterio de éxito es: poder cargar un instrumento real, procesarlo en las 9 etapas y consultarlo en lenguaje natural con trazabilidad a la fuente.

---

## 9. Recomendaciones para titulación

### Sobre el alcance
Demostrar el pipeline completo end-to-end con 5-10 instrumentos reales es más valioso que tener 100 instrumentos con un pipeline incompleto. La profundidad importa más que el volumen.

### Sobre los KPIs
El catálogo de 50 KPIs es un activo diferenciador. Conectarlos con evidencia documental real (instrumentos procesados) es el aporte más original del sistema. Priorizar la inferencia de KPIs sobre los dashboards.

### Sobre el RAG
La calidad del RAG debe poder medirse. Preparar un conjunto de 10-15 preguntas de evaluación con respuestas esperadas. Documentar las métricas de relevancia (top-K recall) en el informe de titulación. Esto transforma el sistema de "una demo" a "un experimento con resultados".

### Sobre la base de datos vectorial
La decisión de usar una sola colección en ChromaDB debe justificarse en el informe. Documentar: qué metadatos se indexan por chunk, por qué esa granularidad, y qué estrategia de filtrado se usa para consultas acotadas por tipo de instrumento o KPI.

### Sobre el stack tecnológico
- FastAPI + PostgreSQL + ChromaDB + Ollama + sentence-transformers es un stack académicamente sólido y justificable.
- Todos los componentes son open source, lo que hace el proyecto reproducible.
- Ollama local elimina costos y dependencias externas, lo que es importante para un proyecto académico.

### Sobre el informe
Documentar explícitamente:
1. Por qué Enriched Chunking vs chunking simple (citar literatura sobre RAG con metadatos enriquecidos).
2. Por qué ChromaDB vs alternativas (Pinecone, Weaviate, pgvector).
3. La alineación con ISO 15836 (Dublin Core) como decisión de estandarización consciente.
4. El pipeline de 9 etapas como contribución metodológica al dominio educativo.

---

## Resumen ejecutivo

| Aspecto | Estado actual | Estado objetivo |
|---|---|---|
| Pipeline | 4/9 etapas | 9/9 etapas |
| RAG | Mockup | Funcional con trazabilidad |
| Seguridad | Sin autenticación real | JWT + roles |
| KPIs | Catálogo estático | Inferidos por instrumento |
| Dashboards | Inexistentes | KPIs + tendencias + filtros |
| Frontend | Jinja2 + JS vanilla | React SPA |
| Vectorización | 0% implementado | ChromaDB + Enriched Chunking |
| JSON canónico | Parcial (sin KPIs) | Estructura completa |
| Tiempo estimado | — | 13 semanas (Fases 1-5) |
| MVP para titulación | — | 7 semanas (Fases 1-3) |
