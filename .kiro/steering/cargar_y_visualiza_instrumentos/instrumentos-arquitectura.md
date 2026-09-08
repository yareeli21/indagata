---
inclusion: manual
---

# Instrumentos de Investigación — Arquitectura del Sistema
**Versión:** 1.2  
**Fecha:** Agosto 2026  
**Alcance:** Ciclo de vida del instrumento, máquina de estados, pipelines, JSON canónico, integración con ChromaDB y RAG (visión superficial)

---

## 1. Principio de diseño central

El sistema distingue entre dos tipos de información sobre un instrumento:

**Información operativa** — sirve para gestionar el ciclo de vida dentro del sistema: rutas de archivos, estados del pipeline, auditoría, trazabilidad técnica. Vive en PostgreSQL.

**Información semántica** — sirve para responder preguntas educativas: qué mide el instrumento, quién lo produce, a quién estudia, qué hallazgos revela. Vive en el JSON canónico.

Estas dos capas no se mezclan. PostgreSQL no almacena metadatos semánticos. El JSON canónico no almacena rutas de archivos ni estados del pipeline.

El JSON canónico nace en el momento en que el pipeline de limpieza termina, dado que los metadatos Dublin Core ya existen desde la carga del instrumento. El JSON **siempre** representa conocimiento real porque los metadatos son obligatorios antes de que el instrumento entre al pipeline.

---

## 2. Ciclo de vida del instrumento

El instrumento pasa por cuatro fases antes de estar disponible para consulta RAG. Cada fase tiene una responsabilidad distinta, actores distintos y artefactos distintos.

```
┌─────────────────────────────────────────────────────────────────┐
│  FASE 1 — INGESTA              Estado: recibido                 │
│  Actor: investigador (usuario)                                  │
│  Requisito: 13 campos Dublin Core obligatorios al cargar        │
│  Artefactos: archivo en storage/raw/ + registro en raw_data     │
│              + metadatos Dublin Core en PostgreSQL              │
│  JSON canónico: NO EXISTE AÚN                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │  Pipeline de limpieza (automático)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 2 — LIMPIEZA TÉCNICA     Estado: limpio                   │
│  Actor: sistema (pipeline de limpieza)                          │
│  Artefactos: storage/data/{id}_limpio.txt                       │
│              (texto limpio — insumo de los pipelines KPI e IEC) │
│  JSON canónico: NO EXISTE AÚN                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │  Pipeline de inferencia KPI
                              │  + Pipeline de estandarización
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 3 — ESTANDARIZACIÓN      Estado: estandarizado            │
│  Actor: sistema (pipeline)                                      │
│  Artefactos: storage/json/{id}.json  ← NACE AQUÍ               │
│              El JSON consolida: metadatos DC + kpis_inferidos[] │
│              + storage/sav/{id}.sav (solo encuestas)            │
└─────────────────────────────┬───────────────────────────────────┘
                              │  Pipeline IEC + embeddings
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 4 — VECTORIZACIÓN        Estado: vectorizado              │
│  Actor: sistema (pipeline)                                      │
│  Artefactos: JSON completo con unidades_semanticas[]            │
│              + chunks en ChromaDB                               │
│              + documento_vectorizado en PostgreSQL              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Máquina de estados

### 3.1 Estados válidos

| Estado | Significado operativo |
|---|---|
| `recibido` | El archivo y los metadatos llegaron al sistema. El pipeline de limpieza está pendiente. |
| `limpio` | El texto fue extraído y limpiado. El texto limpio está disponible en disco para los pipelines. El JSON canónico aún no existe. |
| `estandarizado` | Los pipelines de inferencia KPI y estandarización han concluido. El JSON canónico fue generado con `dublin_core`, `contexto` y `kpis_inferidos[]`. |
| `vectorizado` | Los embeddings fueron generados y están disponibles en ChromaDB para consulta RAG. El JSON está completo con `unidades_semanticas[]`. |
| `error` | Alguna etapa del pipeline falló. El detalle del error está en `instrumento_procesado.error_detalle`. |

### 3.2 Transiciones válidas

```
recibido ──► limpio ──► estandarizado ──► vectorizado
    │            │              │               │
    └────────────┴──────────────┴───────────────┴──► error
                 ▲
                 │  (edición de metadatos o nueva versión del archivo)
                 └── vectorizado / estandarizado ──►
```

| Desde | Hacia | Quién ejecuta | Condición |
|---|---|---|---|
| `recibido` | `limpio` | Pipeline de limpieza (sistema) | Extracción y limpieza del texto completadas. Texto guardado en `storage/data/`. |
| `limpio` | `estandarizado` | Pipeline de estandarización (sistema) | Inferencia KPI completada. JSON canónico generado en `storage/json/`. |
| `estandarizado` | `vectorizado` | Pipeline IEC + embeddings (sistema) | Chunks generados y escritos en ChromaDB |
| Cualquiera | `error` | Cualquier pipeline | Fallo irrecuperable en esa etapa |
| `error` | `recibido` | Administrador | Reintento completo desde ingesta |
| `vectorizado` | `limpio` | Sistema | El investigador editó metadatos |
| `estandarizado` | `limpio` | Sistema | El investigador editó metadatos |
| `limpio` | `recibido` | Sistema | El investigador subió nueva versión del archivo |

### 3.3 Validación de metadatos al cargar

La transición al sistema (creación del instrumento) requiere que los 13 campos Dublin Core obligatorios estén presentes. Esta validación ocurre en el endpoint `POST /instrumentos`, antes de persistir cualquier dato.

| Campo Dublin Core | Por qué es obligatorio |
|---|---|
| `dc_title` | Nombre del instrumento para el ancla semántica y las citas |
| `dc_creator` | Autor del instrumento; parte del ancla semántica |
| `dc_subject` | Temas del instrumento; habilita filtros semánticos en ChromaDB |
| `dc_description` | Descripción del propósito; alimenta el resumen del instrumento en los embeddings |
| `dc_publisher` | Institución responsable; componente del ancla semántica |
| `dc_contributor` | Colaboradores; contexto de atribución |
| `dc_date` | Fecha de aplicación; permite filtros temporales en ChromaDB |
| `dc_type` | Tipo de instrumento (encuesta/entrevista/prueba); determina el pipeline específico |
| `dc_format` | Formato original; trazabilidad y contexto de interpretación |
| `dc_identifier` | Código semántico legible (IND-ENC-042); referencia en citas del RAG |
| `dc_language` | Idioma; filtro de idioma en ChromaDB y elección del modelo de embeddings |
| `dc_coverage` | Población o cobertura geográfica; componente del ancla semántica |
| `dc_rights` | Condiciones de uso; imprescindible para repositorios académicos |

Si alguno de estos campos falta, el sistema devuelve `422` con la lista de campos pendientes. El instrumento no se crea.

---

## 4. Pipeline de limpieza

### 4.1 Responsabilidad

Convertir el archivo crudo en texto estructurado y utilizable, y luego generar el JSON canónico consolidando ese texto con los metadatos Dublin Core ya disponibles.

### 4.2 Disparador

Polling activo sobre PostgreSQL cada 30 segundos. Busca instrumentos con:
- `estado = 'recibido'`
- Sin registro activo en `pipeline_limpieza_log` con `resultado = 'en_proceso'`

El mecanismo de lock es optimista: el registro en `pipeline_limpieza_log` con `resultado = 'en_proceso'` previene procesamiento paralelo del mismo instrumento.

### 4.3 Etapas internas

```
1. Registrar inicio en pipeline_limpieza_log (resultado = 'en_proceso')
2. Leer ruta del archivo crudo desde raw_data (versión más reciente)
3. Extraer texto según tipo MIME:
   - PDF       → pypdf (página por página)
   - DOCX      → python-docx (párrafos en orden)
   - XLSX      → openpyxl (celda por celda, hoja por hoja)
   - TXT / CSV → lectura directa UTF-8 / latin-1
   - Otros     → intento de decodificación; si falla, texto vacío
4. Limpiar y estructurar el texto con LLM (Ollama):
   - El prompt conserva la estructura original del instrumento.
   - Para textos > umbral configurable: segmentación con solapamiento.
5. Guardar storage/data/{id}_limpio.txt
6. Actualizar instrumento_procesado:
   - estado = 'limpio'
   - ruta_texto_limpio = ruta relativa al archivo de texto
7. Actualizar pipeline_limpieza_log:
   - resultado = 'exitoso'
   - extractor_usado, modelo_llm, prompt_version, tokens, latencia, segmentos
```

### 4.4 Artefacto producido por el pipeline de limpieza

El único artefacto en disco que genera este pipeline es el archivo de texto limpio:

```
storage/data/{instrumento_id}_limpio.txt
```

Este archivo contiene el texto del instrumento tal como quedó después de la limpieza con el LLM. Es el insumo que los pipelines posteriores (inferencia KPI, chunking IEC) leen para generar conocimiento.

La trazabilidad técnica de la ejecución (modelo LLM, extractor, prompt, tokens, latencia, hash del texto extraído) queda completamente en `pipeline_limpieza_log`. No va al JSON canónico porque es información operativa del pipeline, no semántica del instrumento.

### 4.5 Manejo de errores

| Tipo de fallo | Comportamiento |
|---|---|
| Formato no soportado | `estado → error`, mensaje en `error_detalle` |
| Archivo no encontrado en disco | `estado → error` |
| LLM no disponible (Ollama caído) | No cambia estado. Reintenta en el próximo ciclo de polling. |
| LLM devuelve texto vacío | `estado → error` |
| Error al escribir JSON en disco | `estado → error`, conserva archivos temporales para diagnóstico |

---

## 5. El JSON canónico

### 5.1 Cuándo nace

El JSON canónico nace al completar la fase de estandarización (transición `limpio → estandarizado`). No existe durante los estados `recibido` ni `limpio`.

El momento de creación se elige en estandarización porque es entonces cuando el conocimiento del instrumento está completo en su primera versión útil: los metadatos Dublin Core ya existen (cargados por el investigador), el texto limpio ya está disponible (producido por el pipeline de limpieza) y los KPIs han sido inferidos (producidos por el pipeline de inferencia KPI). El JSON nace consolidando esos tres insumos — no antes, porque hacerlo con insumos parciales produciría un JSON incompleto.

### 5.2 Quién escribe cada bloque

| Bloque | Autor | Cuándo |
|---|---|---|
| `_meta` | Sistema | Al crear el JSON y en cada actualización |
| `dublin_core` | Investigador (al cargar) + editable después | Al crear el JSON (leído desde PostgreSQL) y en actualizaciones del investigador |
| `contexto` | Sistema (derivado de `dublin_core`) | Al crear el JSON. El investigador puede enriquecer `objetivo` y `periodo_fin` |
| `kpis_inferidos` | Pipeline de inferencia KPI | Al crear el JSON (ya inferidos en esta fase) |
| `unidades_semanticas` | Pipeline de chunking IEC | Durante la vectorización |

Ningún bloque es sobreescrito por un autor que no le corresponde. El contrato es estricto: el pipeline de vectorización preserva `dublin_core`, `contexto` y `kpis_inferidos` intactos.

**Qué no vive en el JSON canónico:**
- El bloque `especifico` (dimensiones, guión temático, áreas): es información de estructura interna que puede enriquecer el análisis pero no aporta conocimiento semántico independiente. Vive en los metadatos del investigador en PostgreSQL y se usa como insumo de los pipelines, no como parte del documento canónico.
- La trazabilidad del pipeline de limpieza (modelo LLM, extractor, tokens): es información operativa. Vive en `pipeline_limpieza_log`.
- El texto limpio: vive en `storage/data/{id}_limpio.txt`. No se duplica en el JSON.

### 5.3 Estructura completa

```json
{
  "_meta": {
    "instrumento_id": 42,
    "schema_version": "1.0",
    "creado_en": "ISO-8601",
    "ultima_actualizacion": "ISO-8601",
    "tipo_instrumento": "encuesta"
  },
  "dublin_core": {
    "dc_title": "Encuesta de Satisfacción Estudiantil 2023",
    "dc_creator": "Dr. Juan Pérez",
    "dc_subject": ["satisfacción estudiantil", "deserción", "calidad docente"],
    "dc_description": "Instrumento para evaluar la satisfacción de estudiantes de licenciatura",
    "dc_publisher": "Universidad Autónoma del Estado",
    "dc_contributor": "Dra. Ana López",
    "dc_date": "2023-1",
    "dc_type": "encuesta",
    "dc_format": "PDF",
    "dc_identifier": "IND-ENC-042",
    "dc_source": null,
    "dc_language": "es",
    "dc_relation": null,
    "dc_coverage": "Estudiantes de licenciatura, ciclo 2023-1",
    "dc_rights": "Uso institucional, no comercial"
  },
  "contexto": {
    "titulo": "Encuesta de Satisfacción Estudiantil 2023",
    "descripcion": "Instrumento para evaluar la satisfacción...",
    "objetivo": null,
    "institucion_responsable": "Universidad Autónoma del Estado",
    "poblacion_alcance": "Estudiantes de licenciatura, ciclo 2023-1",
    "periodo_inicio": "2023-1",
    "periodo_fin": null,
    "idioma": "es",
    "condiciones_uso": "Uso institucional, no comercial",
    "palabras_clave": ["satisfacción estudiantil", "deserción", "calidad docente"]
  },
  "kpis_inferidos": [
    {
      "kpi_id": 15,
      "nombre_kpi": "Tasa de Deserción",
      "descripcion_kpi": "...",
      "evidencia_textual": "La dimensión 3 mide intención de abandono...",
      "score_inferencia": 0.91,
      "secciones_relacionadas": ["Dimensión 3"]
    }
  ],
  "unidades_semanticas": []
}
```

El JSON no contiene: texto limpio (vive en `storage/data/`), estructura interna del instrumento (dimensiones, ítems, guión — los pipelines la leen del archivo de texto limpio), ni trazabilidad del pipeline (vive en `pipeline_limpieza_log`).

### 5.4 El texto limpio como insumo central

El texto limpio vive en `storage/data/{instrumento_id}_limpio.txt`. Es el archivo que los pipelines de inferencia KPI y chunking IEC leen como materia prima para generar conocimiento. No se duplica en el JSON canónico porque es un artefacto de proceso, no conocimiento semántico consolidado.

La ruta a ese archivo se almacena en `instrumento_procesado.ruta_texto_limpio` para que los pipelines puedan localizarlo sin consultar el JSON.

### 5.5 Actualización del JSON canónico

Después de que nace (en estandarización), el JSON puede ser actualizado por:
- El investigador (vía `PATCH /instrumentos/{id}/metadatos`) — actualiza `dublin_core` y `contexto`. Si el instrumento estaba en `vectorizado`, la edición lo regresa a `estandarizado` para forzar re-vectorización.
- El pipeline de vectorización — escribe `unidades_semanticas[]` y preserva el resto.

Toda escritura al JSON es atómica (write-to-temp → rename) para prevenir corrupción.

---

## 6. Persistencia de artefactos por fase

| Artefacto | Ubicación | Fase de creación | Fase de eliminación |
|---|---|---|---|
| Archivo crudo | `storage/raw/{nombre_unico}` | Ingesta | Nunca (historial permanente) |
| Texto limpio | `storage/data/{id}_limpio.txt` | Limpieza | Opcional: tras vectorización exitosa |
| JSON canónico | `storage/json/{id}.json` | Estandarización (al completar KPI) | Si el investigador sube nueva versión del archivo |
| Archivo `.sav` | `storage/sav/{id}.sav` | Estandarización (solo encuestas) | Si se sube nueva versión |
| Archivos temporales | `storage/temp/` | Durante pipeline | Inmediatamente tras éxito; se conservan en error |

---

## 7. Integración con ChromaDB (visión superficial)

ChromaDB es la base de datos vectorial donde viven los embeddings del instrumento. El sistema interactúa con ChromaDB exclusivamente en la fase de vectorización (pipeline IEC + embeddings). Este documento no entra en el detalle técnico del pipeline de embeddings, que se especificará por separado.

**Qué va a ChromaDB:** Un subconjunto del JSON canónico. Cada chunk (unidad semántica, hallazgo, resumen del instrumento) se convierte en un vector con metadatos de filtrado.

**Metadatos de filtrado en ChromaDB** (extraídos del JSON canónico):

| Campo del JSON | Metadato en ChromaDB | Para qué sirve |
|---|---|---|
| `dublin_core.dc_title` | `titulo` | Mostrar la fuente al usuario |
| `dublin_core.dc_type` | `tipo_instrumento` | Filtrar por tipo de instrumento |
| `dublin_core.dc_publisher` | `institucion` | Filtrar por institución |
| `dublin_core.dc_date` | `periodo` | Filtrar por rango temporal |
| `dublin_core.dc_coverage` | `poblacion` | Mostrar contexto en respuestas |
| `dublin_core.dc_identifier` | `codigo_instrumento` | Referencia legible en citas |
| `dublin_core.dc_language` | `idioma` | Filtrar por idioma |
| `kpis_inferidos[].kpi_id` | `kpis_ids` | Filtrar por indicador educativo |
| `instrumento_id` (PostgreSQL) | `instrumento_id` | Trazabilidad de vuelta a la BD |
| tipo de chunk | `tipo_chunk` | Filtrar por tipo de chunk |

**Qué nunca va a ChromaDB:** rutas de archivos, estados del pipeline, hash_md5, timestamps de carga, ids de raw_data. Nada administrativo.

---

## 8. Integración con el pipeline RAG (visión superficial)

El pipeline RAG responde preguntas de los investigadores usando los instrumentos vectorizados. La calidad de las respuestas depende de:

1. **La completitud del ancla semántica** — los 13 campos Dublin Core obligatorios garantizan que todo instrumento tenga contexto de atribución completo al llegar a la vectorización. No puede existir un instrumento en el sistema sin estos campos.

2. **La calidad del texto limpio** — el pipeline de estandarización verifica que el archivo `storage/data/{id}_limpio.txt` tenga contenido útil antes de proceder con la inferencia KPI. Si el texto está vacío o no es procesable, el instrumento queda en `error`.

3. **La completitud del bloque `especifico`** — la estructura interna del instrumento (dimensiones, ítems, guión) que el investigador puede registrar enriquece el análisis del pipeline IEC. No es obligatoria para que el JSON exista, pero mejora la precisión de la recuperación semántica.

---

## 9. Estructura de directorios del backend

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py          ← AppSettings con rutas de storage ya definidas
│   │   ├── security.py        ← Hashing y verificación de contraseñas
│   │   └── ollama_client.py   ← Cliente Ollama (a usar en pipeline de limpieza)
│   └── database/
│       ├── base.py            ← DeclarativeBase de SQLAlchemy
│       └── database.py        ← Engine, SessionLocal, get_db
│
├── cargar_instru/             ← Módulo de gestión de instrumentos (usuario)
│   ├── models.py              ← Modelos ORM: InstrumentoProcesado, RawData, etc.
│   ├── schemas.py             ← Schemas Pydantic de entrada y salida
│   ├── services.py            ← Lógica de negocio
│   ├── routers_cargar_instru.py  ← Endpoints FastAPI
│   └── dependencies.py        ← get_current_user, verificar_propietario, puede_acceder
│
├── pipeline_limpieza/         ← Pipeline automático (sistema, no usuarios)
│   ├── orchestrator.py        ← Polling + coordinación + generación del JSON
│   ├── extractor.py           ← Extracción de texto por MIME
│   ├── llm_cleaner.py         ← Limpieza con Ollama
│   ├── json_writer.py         ← Creación y escritura del JSON canónico
│   └── prompts/
│       └── limpieza_v1.txt    ← Prompt versionado
│
└── main.py                    ← Punto de entrada, startup del pipeline
```

---

## 10. Relación entre los cuatro documentos de diseño

| Documento | Responde a |
|---|---|
| `instrumentos-funcional.md` | ¿Qué puede hacer el usuario? ¿Qué ve en pantalla? |
| `instrumentos-arquitectura.md` (este) | ¿Cómo funciona el sistema por dentro? ¿Qué estados, pipelines y artefactos existen? |
| `instrumentos-impacto-backend.md` | ¿Qué hay que cambiar en el código y la BD actual para implementar esto? |
| `instrumentos-fastapi.md` | ¿Cómo se organizan los modelos, schemas, services, routers y dependencias? |
