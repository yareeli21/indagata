---
inclusion: manual
---

# Inspección de Estructura — Indagata
**Fecha:** Agosto 2026  
**Tipo:** Revisión crítica de coherencia estructural

---

## Lo que existe ahora mismo

```
indagata/
├── .kiro/
│   ├── specs/
│   │   └── modelo-conocimiento-rag/
│   │       ├── requirements.md
│   │       └── design.md
│   └── steering/
│       ├── arquitectura.md
│       ├── arquitectura_definitiva.md
│       ├── chunking_strategy.md
│       └── modelo_conocimiento.md
│
├── backend/
│   └── app/
│       ├── core/
│       │   ├── config.py
│       │   ├── ollama_client.py
│       │   └── security.py
│       ├── database/
│       │   ├── base.py
│       │   └── database.py
│       ├── models/
│       │   ├── instrumento.py
│       │   ├── kpi.py
│       │   └── usuario.py
│       ├── routers/
│       │   ├── cargar.py
│       │   ├── chat.py
│       │   ├── instrumentos.py
│       │   ├── kpis.py
│       │   └── login.py
│       ├── schemas/
│       │   └── metadatos.py
│       ├── services/
│       │   ├── cargar_service.py
│       │   ├── instrumento_service.py
│       │   ├── kpi_service.py
│       │   ├── limpieza_service.py
│       │   ├── login_service.py
│       │   ├── metadatos_enriquecidos_service.py
│       │   └── metadatos_service.py
│       └── main.py
│
├── frontend/
│   ├── landing/
│   ├── static/
│   └── templates/
│
├── postgres/
│   └── init/
│
└── storage/
    ├── data/
    ├── json/
    ├── raw/
    ├── sav/
    └── temp/
```

---

## Problemas de coherencia que veo

### 1. La documentación tiene más capas que el código

En `.kiro/steering` hay cuatro archivos de documentación:
- `arquitectura.md` — análisis inicial
- `arquitectura_definitiva.md` — visión objetivo
- `chunking_strategy.md` — estrategia de chunking
- `modelo_conocimiento.md` — modelo semántico

Y en `.kiro/specs` hay una spec con requirements + design.

**El problema:** `chunking_strategy.md` y `modelo_conocimiento.md` ya fueron absorbidos y superados por la spec. Son documentos intermedios del proceso de diseño, no referencias vivas. Si alguien los lee hoy, tienen información que ya fue refinada en la spec pero sin la actualización final. Están generando ruido.

Propuesta: reducir steering a **un solo archivo de referencia** que apunte a la spec.

---

### 2. `storage/data/` no sabe qué es

La carpeta `storage/` tiene: `raw/`, `json/`, `sav/`, `temp/` — todas con sentido claro. Pero tiene también `data/` sin propósito definido en ningún documento. No está referenciada en `config.py` según el análisis previo, y tampoco en el design.

Es un directorio huérfano. O se le da un rol explícito o se elimina para no generar confusión.

---

### 3. `frontend/landing/` es un misterio

El frontend tiene `templates/` y `static/` que son coherentes con el stack Jinja2 actual. Pero tiene también una carpeta `landing/` que no aparece referenciada en ningún router de FastAPI ni en ningún documento de arquitectura. No se sabe si es una página de marketing, una versión anterior, o algo planificado que nunca se conectó.

Si no tiene uso activo, genera ruido en la estructura y confusión para cualquiera que explore el proyecto.

---

### 4. Los nombres de los routers y servicios mezclan idiomas de forma inconsistente

El código mezcla español e inglés sin un criterio claro:

| Archivo | Idioma |
|---|---|
| `cargar.py` | Español |
| `chat.py` | Inglés |
| `instrumentos.py` | Español |
| `kpis.py` | Inglés (sigla) |
| `login.py` | Inglés |
| `cargar_service.py` | Español |
| `instrumento_service.py` | Español |
| `kpi_service.py` | Mixto |
| `limpieza_service.py` | Español |
| `metadatos_service.py` | Español |

Esto no es un error grave pero sí una señal de que el proyecto creció sin una convención establecida. Para un proyecto de titulación que alguien más va a revisar, la consistencia importa.

---

### 5. `schemas/` tiene un solo archivo real

`schemas/metadatos.py` existe. `schemas/__init__.py` existe. Eso es todo.

La spec define que debe crearse `schemas/semantico.py` con todos los modelos Pydantic para el plano semántico. Ese archivo no existe todavía, lo que significa que los schemas actuales están desacoplados del modelo de conocimiento definido. Hay un `__init__.py` vacío que no exporta nada útil.

---

### 6. `models/` solo tiene 3 modelos de los 7 que existen en la BD

El schema SQL (`01_schema.sql`) define 10 tablas. Los modelos ORM existentes cubren solo 3:
- `instrumento.py` → `instrumento_procesado` ✓
- `kpi.py` → `kpi` ✓
- `usuario.py` → `usuarios` ✓

Faltan en ORM:
- `raw_data` → no tiene modelo
- `documento_vectorizado` → no tiene modelo
- `pregunta_kpi` → no tiene modelo
- `prompt` → no tiene modelo
- `instituciones` → no tiene modelo
- `variable` / `valor_variable` → no tienen modelo

La BD tiene el diseño completo. El código solo ve el 30% de ella. El `models/` promete más de lo que entrega.

---

### 7. `postgres/init/` no tiene migraciones

Solo tiene `01_schema.sql` y `02_seed.sql`. No hay subdirectorio `migrations/` que la spec define como lugar para `02_knowledge_model.sql`.

Cuando se implemente el design, la migración necesita un lugar claro. Si se pone directo en `init/`, se ejecuta al crear el contenedor desde cero pero no en contenedores existentes. Para un entorno de desarrollo que ya tiene la BD corriendo, eso es un problema.

---

### 8. No hay `tests/`

La spec define 5 archivos de tests. No existe ningún directorio `tests/` en el proyecto. No hay `pytest.ini`, `conftest.py`, ni nada relacionado.

Para un proyecto de titulación, la ausencia total de tests es un punto débil técnico. No tiene que ser cobertura completa, pero tener los tests de invariantes de chunking y el test de integración del pipeline es parte del argumento académico.

---

## Lo que está bien y no debe tocarse

**La separación `backend/` + `frontend/` + `postgres/` + `storage/`** es correcta y limpia. No mezcla capas.

**La convención `router → service → model`** está bien aplicada en lo que existe. Cada router delega a un service, cada service usa modelos ORM. Es consistente y fácil de seguir.

**`storage/` con subdirectorios por tipo** (`raw/`, `json/`, `sav/`, `temp/`) es exactamente lo que el design necesita. Está listo.

**`core/`** con `config.py`, `ollama_client.py` y `security.py` tiene buen criterio de agrupación. Todo lo que es transversal al sistema vive ahí.

**`postgres/init/`** con SQL declarativo es el patrón correcto para Docker. El schema está bien escrito.

---

## Propuesta de estructura objetivo

```
indagata/
├── .kiro/
│   ├── specs/
│   │   └── modelo-conocimiento-rag/
│   │       ├── requirements.md
│   │       ├── design.md
│   │       └── tasks.md            ← pendiente de generar
│   └── steering/
│       └── proyecto.md             ← UN solo archivo: contexto + convenciones + apunta a la spec
│
├── backend/
│   └── app/
│       ├── core/
│       │   ├── config.py
│       │   ├── ollama_client.py    ← migrar a async
│       │   ├── embeddings_client.py ← nuevo
│       │   └── security.py
│       ├── database/
│       │   ├── base.py
│       │   └── database.py
│       ├── models/
│       │   ├── instrumento.py      ← añadir codigo, schema_version, ruta_original
│       │   ├── kpi.py
│       │   ├── usuario.py
│       │   └── conocimiento.py     ← nuevo: RawData, DocumentoVectorizado, PreguntaKpi, Prompt
│       ├── routers/
│       │   ├── login.py
│       │   ├── instrumentos.py
│       │   ├── cargar.py
│       │   ├── pipeline.py         ← nuevo
│       │   ├── rag.py              ← nuevo (reemplaza chat.py)
│       │   └── kpis.py
│       ├── schemas/
│       │   ├── metadatos.py
│       │   └── semantico.py        ← nuevo: todos los modelos del plano semántico
│       ├── services/
│       │   ├── login_service.py
│       │   ├── instrumento_service.py
│       │   ├── cargar_service.py
│       │   ├── limpieza_service.py
│       │   ├── metadatos_service.py
│       │   ├── metadatos_enriquecidos_service.py
│       │   ├── kpi_service.py
│       │   ├── kpi_inferencia_service.py   ← nuevo
│       │   ├── json_canonico_service.py    ← nuevo
│       │   ├── chunking_service.py         ← nuevo
│       │   ├── vectorizacion_service.py    ← nuevo
│       │   └── rag_service.py              ← nuevo
│       └── main.py
│
├── frontend/
│   ├── static/
│   └── templates/
│
├── postgres/
│   └── init/
│       ├── 01_schema.sql
│       ├── 02_seed.sql
│       └── 03_knowledge_model.sql  ← migración nueva, numerada
│
├── storage/
│   ├── json/
│   ├── raw/
│   ├── sav/
│   └── temp/
│
└── tests/
    ├── conftest.py
    ├── test_chunking_invariants.py
    ├── test_chroma_metadata.py
    ├── test_json_canonico.py
    ├── test_rag_service.py
    └── test_pipeline_integration.py
```

---

## Acciones concretas antes de implementar

| Acción | Urgencia | Por qué |
|---|---|---|
| Eliminar o consolidar steering files redundantes | Media | `chunking_strategy.md` y `modelo_conocimiento.md` tienen información superada por la spec |
| Aclarar o eliminar `frontend/landing/` | Baja | Genera confusión; si no tiene uso activo, fuera |
| Aclarar o eliminar `storage/data/` | Baja | Directorio sin propósito documentado |
| Crear `tests/` con `conftest.py` vacío | Alta | Hace explícito que los tests son parte del proyecto |
| Renombrar migración a `03_knowledge_model.sql` | Media | Más claro que un subdirectorio `migrations/` separado |
| Decidir convención de idioma en nombres de archivo | Media | Español completo o inglés completo, no los dos |
| Generar `tasks.md` en la spec | Alta | Sin tasks, el design no puede ejecutarse de forma estructurada |

---

## Veredicto

La estructura **tiene lógica**. El problema no es incoherencia radical — el problema es **acumulación**: cuatro archivos de steering que deberían ser uno, un frontend con una carpeta fantasma, una BD con 10 tablas pero solo 3 modelos en código, y ningún directorio de tests.

El proyecto está en una fase de transición entre "prototipo de exploración" y "plataforma con arquitectura definida". La spec que generamos hace la transición formal. Ahora la estructura de archivos necesita ponerse al día con esa definición.

El riesgo concreto: si alguien (un revisor, un asesor, tú mismo en tres semanas) abre el proyecto, va a ver `steering/` con cuatro documentos que dicen cosas distintas y no va a saber cuál es la referencia actual. Eso no transmite confianza técnica.

La solución es simple: consolidar, limpiar lo que no tiene uso, y que la estructura de carpetas cuente la misma historia que la spec.
