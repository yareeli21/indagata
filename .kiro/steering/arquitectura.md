---
inclusion: manual
---

# Informe Técnico de Arquitectura — Indagata
**Fecha:** Agosto 2026  
**Rol:** Arquitecto de Software Senior  
**Objetivo final:** Convertir el sistema en una plataforma educativa RAG para centralización y consulta de información educativa.

---

## 1. Estado actual del sistema

**Indagata** es un monolito web con renderizado server-side (FastAPI + Jinja2 + PostgreSQL + Ollama local). Su propósito actual es gestionar el ciclo de vida de instrumentos de recolección de datos educativos (encuestas, entrevistas, pruebas estandarizadas), con un pipeline asistido por LLM para limpiar y enriquecer metadatos antes de vectorizarlos.

Stack actual:
- **Backend:** Python 3.12, FastAPI, SQLAlchemy (psycopg3), Pydantic v2
- **Frontend:** Jinja2 templates + CSS variables + JS vanilla (sin framework)
- **Base de datos:** PostgreSQL 16 (schema `tt_rag`)
- **LLM:** Ollama local (httpx síncrono, sin streaming)
- **Vectorización:** ChromaDB + LangChain instalados pero **sin implementar**
- **Infraestructura:** Docker Compose (3 servicios: postgres, ollama, fastapi)

---

## 2. Módulos existentes y qué problema resuelven

| Módulo | Archivos | Qué resuelve |
|---|---|---|
| **Auth** | `routers/login.py`, `services/login_service.py`, `core/security.py` | Login/logout con cookies httponly, hash bcrypt |
| **Catálogo KPIs** | `routers/kpis.py`, `services/kpi_service.py`, `models/kpi.py` | Visualización de 50 KPIs educativos con umbrales y fórmulas |
| **Catálogo instrumentos** | `routers/instrumentos.py`, `services/instrumento_service.py`, `models/instrumento.py` | Listado y filtro por tipo de los instrumentos ya procesados |
| **Pipeline de carga** | `routers/cargar.py` + 4 servicios | Ingesta de archivos → limpieza automática (stub) → chat limpieza con Ollama → metadatos base (Pydantic) → metadatos enriquecidos con Ollama |
| **Chat IA** | `routers/chat.py` | Pantalla de consulta RAG — actualmente retorna mockup hardcodeado |
| **Config** | `core/config.py` | Centraliza todas las variables de entorno con pydantic-settings |
| **Ollama client** | `core/ollama_client.py` | Wrapper HTTP síncrono hacia `/api/chat` de Ollama |
| **Base de datos** | `postgres/init/01_schema.sql`, `02_seed.sql` | Esquema completo con 10 tablas, 50 KPIs y ~90 variables seed |

---

## 3. Deuda técnica detectada

### Crítica
- **Sin autenticación real en rutas protegidas.** La cookie `usuario_id` se setea pero ningún middleware valida su presencia. Cualquier URL es accesible sin login. `SECRET_KEY` existe pero no se usa para firmar nada.
- **Endpoint `/chat/consultar` es un mockup.** Retorna una respuesta hardcodeada. ChromaDB y LangChain están instalados pero sin ningún código escrito.
- **`limpieza_service.aplicar_limpieza_automatica` es un stub.** Solo avanza el estado; no procesa datos. El clasificador de columnas (`clasificador.py`) está referenciado pero no existe.

### Significativa
- **Ollama client es síncrono y bloquea.** Una sola llamada a Ollama (timeout 120s) bloquea el event loop de FastAPI entero. Debe ser async con httpx.
- **8 tablas del esquema SQL sin usar.** `raw_data`, `pregunta_kpi`, `documento_vectorizado`, `rag_log`, `instituciones`, `variable`, `valor_variable`, `prompt` están definidas pero ningún router ni servicio las toca.
- **Lógica de presentación en el servicio.** `instrumento_service._preparar_instrumentos()` genera códigos visuales (ENC-001) y slugs CSS. Pertenece a la capa de template, no al servicio.
- **JS de pipeline en el template HTML.** El JavaScript que orquesta el flujo completo de carga (modales, historial de chat, llamadas encadenadas) vive en el bloque `js_extra` de `cargar_instrumento.html`. Difícil de mantener y probar.

### Menor
- `base.js` solo contiene un `console.log`. No aporta nada.
- Los códigos de catálogo (ENC-001) se generan en runtime en Python, no están persistidos. Si se necesitan como referencia estable, deben guardarse en BD.
- No hay manejo de errores consistente: algunos endpoints retornan JSON, otros redirigen, otros lanzan 500 sin capturar.

---

## 4. Qué debe conservarse

- **Esquema de base de datos completo** (`01_schema.sql`): está bien diseñado, cubre todo el dominio incluyendo vectorización, logs RAG y trazabilidad. Es la pieza más madura del sistema.
- **Seed data** (`02_seed.sql`): los 50 KPIs y ~90 variables son valor de negocio real.
- **Pipeline de metadatos** (`metadatos_service.py`, `metadatos_enriquecidos_service.py`): la lógica de dos niveles (base + enriquecidos) está bien pensada y los schemas Pydantic son sólidos.
- **Config centralizada** (`core/config.py`): patrón correcto con pydantic-settings.
- **Sistema de diseño CSS** (`base.css`): paleta, componentes y layout son coherentes y funcionales.
- **Arquitectura de templates** (`base.html` + páginas): la estructura Jinja2 con sidebar condicional es adecuada para el alcance del proyecto.
- **Prompts del LLM** en `limpieza_service` y `metadatos_enriquecidos_service`: son prompts bien construidos con contexto del instrumento y marcadores de estado (`[LIMPIEZA_LISTA]`, `[METADATOS_LISTOS]`).

---

## 5. Qué debe refactorizarse

| Qué | Hacia dónde |
|---|---|
| `core/ollama_client.py` — httpx síncrono | Cambiar a `httpx.AsyncClient` con `await` |
| Auth por cookie sin firma | Implementar JWT firmado con `SECRET_KEY` vía `python-jose`. Añadir dependency `get_current_user` que valide el token en cada router protegido |
| `instrumento_service._preparar_instrumentos()` | Mover lógica de presentación al template Jinja2 con un filtro o función de contexto |
| JS inline en `cargar_instrumento.html` | Extraer a `/static/js/pipeline_carga.js` como módulo ES6 |
| `limpieza_service.aplicar_limpieza_automatica` | Implementar clasificador de columnas con pandas (inferencia de dtype + normalización básica) |
| Manejo de errores | Definir handlers globales en `main.py` para HTTPException y Exception genérica con respuesta JSON consistente |

---

## 6. Qué debe eliminarse

- `frontend/static/js/base.js` — no tiene contenido útil. Eliminar o convertirlo en el entry point del módulo JS.
- El mockup hardcodeado en `routers/chat.py` — reemplazar, no parchear.
- Las rutas GET `/` en `main.py` que retornan JSON informativo — en producción no aportan valor y exponen información del sistema.

---

## 7. Arquitectura objetivo

### Visión
Plataforma educativa RAG donde los usuarios pueden:
1. **Cargar** instrumentos educativos y procesarlos con asistencia LLM.
2. **Consultar** en lenguaje natural sobre el contenido de los instrumentos vectorizados.
3. **Monitorear** KPIs educativos vinculados a variables estandarizadas.

### Capas propuestas

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND (Jinja2)                  │
│  login │ cargar │ catálogo │ chat-IA │ KPIs          │
└────────────────────┬────────────────────────────────┘
                     │ HTTP (FastAPI)
┌────────────────────▼────────────────────────────────┐
│                  API LAYER (Routers)                  │
│  auth  │  instrumentos  │  rag  │  kpis              │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                 SERVICE LAYER                         │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ PipelineService│ │  RAGService  │  │ KpiService │ │
│  │ (carga+meta) │  │(query+chunks)│  │            │ │
│  └──────┬───────┘  └──────┬───────┘  └────────────┘ │
│         │                 │                           │
│  ┌──────▼───────┐  ┌──────▼───────┐                 │
│  │VectorizaciónSvc│ │ OllamaClient │                 │
│  │(LangChain+   │  │  (async)     │                 │
│  │  ChromaDB)   │  └──────────────┘                 │
│  └──────────────┘                                    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              PERSISTENCE LAYER                        │
│   PostgreSQL (SQLAlchemy)  │  ChromaDB (vectores)    │
└─────────────────────────────────────────────────────┘
```

### Nuevos servicios a crear (prioridad de implementación)

**P1 — Desbloquean el RAG core:**
1. `services/vectorizacion_service.py` — recibe un `instrumento_id`, lee el archivo, lo chunquea con LangChain `RecursiveCharacterTextSplitter`, genera embeddings con `sentence-transformers` (modelo `paraphrase-multilingual-MiniLM-L12-v2`), guarda en ChromaDB y registra en `documento_vectorizado`. Avanza estado a "vectorizado".
2. `services/rag_service.py` — recibe una pregunta, genera embedding de consulta, busca top-K chunks en ChromaDB, construye el contexto y llama a Ollama. Guarda en `rag_log`.

**P2 — Seguridad mínima viable:**
3. Middleware de autenticación JWT en todos los routers excepto `/login`.

**P3 — Funcionalidades de valor educativo:**
4. `services/kpi_inferencia_service.py` — usa `pregunta_kpi` para mapear preguntas del instrumento a KPIs usando el LLM con score de confianza. Usa la tabla `prompt` para versionar el prompt.
5. `services/variable_service.py` — gestiona la carga de valores históricos en `valor_variable` para tracking de KPIs en el tiempo.

### Flujo RAG objetivo

```
Usuario escribe pregunta
        │
        ▼
 Generar embedding (sentence-transformers)
        │
        ▼
 Buscar top-5 chunks en ChromaDB
 (filtrar opcionalmente por tipo de instrumento)
        │
        ▼
 Construir prompt con contexto recuperado
 + metadatos del instrumento (título, institución, periodo)
        │
        ▼
 Llamar a Ollama (async, con streaming opcional)
        │
        ▼
 Retornar respuesta + chunks fuente + metadata
 Guardar en rag_log
```

### Estado pipeline completo (incluyendo vectorización)

```
ingresado → limpio → estandarizado → vectorizado → error
   ↑            ↑            ↑              ↑
 carga      metadatos   metadatos       ChromaDB
            base        enriquecidos    + rag_log
```

---

## 8. Resumen de decisiones

| Decisión | Justificación |
|---|---|
| Mantener monolito FastAPI + Jinja2 | El alcance no justifica microservicios. La complejidad de RAG está en los servicios, no en la distribución. |
| ChromaDB local (no Pinecone/Weaviate) | Ya instalado, sin costo, suficiente para el volumen educativo esperado. Coherente con la filosofía local de Ollama. |
| sentence-transformers multilingüe | El contenido es en español. `paraphrase-multilingual-MiniLM-L12-v2` tiene buen balance velocidad/calidad para español sin GPU. |
| Mantener esquema SQL actual | Está bien diseñado y cubre el dominio completo. El esfuerzo de re-diseño no está justificado. |
| JWT en cookies httponly | Mantiene la UX actual (no SPA), añade seguridad real sin cambiar el flujo de navegación. |
