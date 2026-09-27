# Arquitectura de Limpieza y Estandarización — Survey Intelligent System (SIS)

> **Qué es este documento:** descripción de lo que el SIS **hace realmente** (verificado en
> código) para limpiar, normalizar, estandarizar y enriquecer un instrumento, etapa por etapa
> y por tipo de instrumento (encuesta, entrevista, prueba estandarizada).
> **Fuente:** `survey_intelligence/facade.py` + `survey_intelligence/pipelines/*` +
> `pipeline/stages/*` + `engine/*`.
> **Cómo está organizado y cómo extender:** ver `ARQUITECTURA_SIS.md` (organización actual) y
> `GUIA_EXTENSION_INSTRUMENTOS.md` (agregar entrevistas / pruebas estandarizadas).

---

## 1. Qué es el SIS y dónde empieza/termina

El SIS es un **servicio interno de dominio** (patrón hexagonal, aislado del framework). Recibe un
instrumento (bytes de CSV/XLSX para encuestas, o texto extraído para documentos) y produce
**conocimiento estructurado**: el **JSON canónico** (estructura fiel y determinística) y, aguas
abajo en el host, el **JSON consolidado** (conocimiento para el RAG).

- **Entrada:** `SurveyIngestionRequest` (archivo + metadatos Dublin Core + opciones).
- **Salida:** `SurveyIntelligenceResult` (canónico, enriquecido, propuestas, KPIs, hallazgos, y —según tipo— análisis de entrevista).
- **Frontera:** el SIS **termina** al producir el resultado; el RAG principal (vectorización, embeddings, Q&A) es otro componente que **consume** su salida.
- **Regla de oro:** el SIS **nunca lanza excepción al host**; todo fallo se reporta como `status=failed` con diagnóstico por etapa.

### Principios transversales
- **Determinístico primero, LLM después.** Todo lo que puede afirmarse sin LLM (estructura, escalas,
  distribuciones) se calcula de forma reproducible. El LLM solo añade interpretación semántica.
- **Degradación graciosa.** S1/S2 son **fatales** (si fallan → `failed`). S3..S10 son **degradables**:
  si el LLM falla, se conserva lo determinístico y se marca `degraded=True`.
- **Anti-invención.** El LLM no puede "inventar" significado sin evidencia; hay un validador en dos
  pasos (S4 marca insuficiencia; S7 degrada cualquier invención).

---

## 2. Selección de estrategia por tipo de instrumento

El facade (`SurveyIntelligenceService.process`) NO ramifica ya con `if` dispersos: selecciona
una **estrategia por instrumento** (`survey_intelligence/pipelines/`) con
`select_pipeline(instrument_type)` y le delega las dos fases que divergen. El resto (S4..S9) es
**tronco común** que vive en el facade y no se duplica.

```
process(request)
   pipeline = select_pipeline(instrument_type)     # encuesta | entrevista | prueba_estandarizada
   build    = pipeline.build_canonical(...)        # cómo se construye el canónico
   ── tronco común: S4 → S5 → S6 → S7 → S7b → S9 → S8 ──
   analysis = pipeline.analyze(...)                # análisis ESPECÍFICO del instrumento
```

- **EncuestaPipeline** (`pipelines/encuesta.py`): `build_canonical` = S1 ingest → S2 canonical →
  S3 profiling (vía tabular); `analyze` = S8b resultados (v1 por columna / v2 por pregunta).
- **EntrevistaPipeline** (`pipelines/entrevista.py`): `build_canonical` = vía documental
  (`_document.py`); `analyze` = S10 análisis de entrevista (NLP).
- **PruebaEstandarizadaPipeline** (`pipelines/prueba_estandarizada.py`): `build_canonical` = vía
  documental; `analyze` = **esqueleto, sin reglas propias aún** (ver `GUIA_EXTENSION_INSTRUMENTOS.md`).

Un `instrument_type` desconocido cae a la estrategia de encuesta (comportamiento por defecto).
Cada estrategia **compone** los stages existentes; no reimplementa su lógica.

---

## 3. Las etapas del pipeline (qué hace cada una)

### S1 — Ingesta (FATAL)
- **Encuesta:** decodifica el archivo (base64), elige el reader por formato (CSV/XLSX), produce un
  `RawTable` (encabezados + filas como texto) y detecta la **plataforma** (Google Forms / Microsoft
  Forms / LimeSurvey) por firma de columnas administrativas.
- **Documento (entrevista/prueba):** valida que haya `extracted_text`; si está vacío → `failed`.
- **Limpieza que hace aquí:** normaliza saltos de línea, serializa valores no textuales (p. ej.
  datetime de XLSX) a string. Identifica columnas administrativas (IDs, timestamps, correo, semilla)
  para no confundirlas con preguntas.

### S2 — Construcción del Canónico (FATAL, determinístico)
- **Encuesta (`build_canonical`):**
  - Normaliza nombres de columna a `snake_case` únicos.
  - Clasifica cada columna: `platform_metadata` | `free_text` | `question`.
  - **Modo v1 (actual):** detecta preguntas-matriz por patrón `tronco [ítem]` / `tronco .subítem` y
    agrupa esos ítems; el resto son preguntas simples. Cada columna = una `variable`.
  - **Modo v2 (rediseño, tras bandera `question_grouping`):** además reagrupa columnas hermanas en
    **preguntas lógicas** (`questions[]`) con tipo canónico, opciones y trazabilidad, y conserva
    `variables[]` como capa de compatibilidad.
  - Calcula `canonical_id` = hash determinístico del contenido normalizado.
- **Documento (`build_document_canonical`):** segmenta el texto en "variables documentales"
  (párrafos/preguntas) y produce el MISMO `CanonicalSurveyModel` para que S4..S9 apliquen sin
  cambios. No detecta escalas ni matrices (los documentos narrativos no las tienen).

### S3 — Data Profiling (degradable, determinístico)
Solo aporta métricas; **no** interpreta. Por cada variable-pregunta:
- Detecta la **escala** (Likert / binaria / categórica) y **anomalías de escala** (typos con
  `canonical_guess`, p. ej. "En deesacuerdo" → "En desacuerdo").
- Calcula la **distribución de valores** (nulos, cardinalidad, top valores, nulos estructurales).
- Refina el **tipo de dato inferido** (ordinal, nominal, numérico, multi_select, datetime, ...).
- En documentos, S3 se **omite** (no hay escalas tabulares).
- **Modo v2:** además calcula `metrics`/`distribution` por pregunta (sin tocar el profiling por variable).

### S4 — Suficiencia de contexto (determinística, previa al LLM)
- Evalúa, por variable, si hay contexto suficiente para interpretarla. Marca las candidatas a
  `INSUFFICIENT_CONTEXT` **antes** de que intervenga el LLM.
- Es el **paso 1 del validador anti-invención**: fija qué preguntas NO se deben interpretar sin evidencia.

### S5 — Resolución determinística de codebook (sin RAG, degradable)
- Si el request trae `codebook` (un `CodebookModel` que el host construyó con `read_codebook`),
  resuelve las variables técnicas por coincidencia exacta/normalizada **O(1)** (sin embeddings ni
  vector store): reescribe el `raw_header` con la etiqueta descriptiva, enriquece `detected_scale`
  con las etiquetas de valor y marca los verdicts como interpretables.
- Sin codebook (caso normal actual), se marca `skipped` y no ramifica el pipeline.
- Formatos de codebook admitidos hoy: CSV/TSV, XLSX/XLS, JSON, TXT y PDF. Detalle en
  `DESIGN_CODEBOOK_DETERMINISTA.md`.

### S6 — Auditoría metodológica (LLM, degradable)
Combina dos capas:
- **Determinística (sin LLM):** preguntas demasiado cortas/largas, escalas inconsistentes entre ítems,
  columnas eliminables.
- **Semántica (LLM):** ambigüedad, preguntas de doble cañón ("doble pregunta"), sesgo de redacción.
- Si el LLM falla (tras 1 reintento) → conserva lo determinístico, `degraded=True`.

### S7 — Enriquecimiento semántico (LLM, degradable) + validador anti-invención
Por cada variable **interpretable** produce su cara semántica: `constructo`, `rol_semantico`, `tags`,
`chunking_hint`, y `analytical_sufficiency` (qué tan rica es la pregunta). Fusiona esto con el
diccionario SPSS determinístico.
- **Validador anti-invención (paso 2):** respeta el veredicto de S4; si el LLM propone significado
  para una variable **sin evidencia**, la **degrada** a `INSUFFICIENT_CONTEXT`. La evidencia manda,
  no el LLM.
- Sin LLM → variables interpretables quedan con su SPSS determinístico y sin cara semántica; `degraded=True`.

### S7b — Inferencia de KPIs (LLM, degradable)
- Infiere qué KPIs del **catálogo del host** (solo nombres/descripciones) están presentes en el
  instrumento, con un `score`. **No inventa**: filtra los que no estén en el catálogo.
- Requiere LLM + catálogo; si falta alguno, se omite.

### S8b — Análisis de resultados (solo encuestas, LLM en lote, degradable)
Qué **respondió la población** y qué **significa**, por pregunta:
- **Determinístico:** métricas (n, nulos, moda, media codificada) y distribución de frecuencias.
- **LLM en lote (una llamada):** interpretación, insights, evidencia numérica, texto semántico, sobre
  los **datos observados** (no inventa). Con fallback determinístico si el LLM falla.
- En documentos se **omite** (no hay respuestas tabulares que agregar).
- **Modo v2:** produce la perspectiva **por pregunta** (`por_pregunta`) sobre las preguntas reagrupadas.

### S9 — Ensamblado del Enriquecido
Combina S6 (auditoría) + S7 (enriquecimiento) en el `EnrichedSurveyModel`. Solo estructura, sin lógica nueva.

### S8 — Gap analysis + propuestas ejecutables (determinístico)
- Convierte las lagunas detectadas en **oportunidades de mejora** (`ImprovementOpportunity`, estado `proposed`).
- Genera **propuestas de transformación** ejecutables para la fase de limpieza (ver §5).

### S10 — Análisis de entrevista (solo entrevistas; determinístico + LLM)
- **Determinístico:** diarización textual → participantes (con rol e identificador) y turnos
  (quién pregunta, quién responde, a qué pregunta).
- **LLM (opcional):** temas, hallazgos, patrones, citas y resúmenes, con evidencia trazable al turno.
  Sin LLM → conserva la capa determinística, `degraded=True`.

---

## 4. Qué se hace por tipo de instrumento (resumen)

| Etapa | Encuesta | Entrevista | Prueba estandarizada |
|---|---|---|---|
| S1 Ingesta | Lee CSV/XLSX + detecta plataforma | Valida texto extraído | Valida texto extraído |
| S2 Canónico | `build_canonical` (tabular; v2 reagrupa por pregunta) | `build_document_canonical` (segmentos) | `build_document_canonical` |
| S3 Profiling | Escalas, distribución, tipo | SKIPPED | SKIPPED |
| S4 Contexto | Sí | Sí | Sí |
| S5 Codebook | Si hay codebook (determinístico) | — (no aplica) | — (no aplica) |
| S6 Auditoría | Determinística + LLM | Determinística + LLM | Determinística + LLM |
| S7 Enriquecimiento | Sí (validador anti-invención) | Sí | Sí |
| S7b KPIs | Sí (catálogo) | Sí | Sí |
| S8b Resultados | Sí (por pregunta) | NO (no tabular) | NO |
| S9 Ensamblado | Sí | Sí | Sí |
| S8 Gap + propuestas | Sí | Sí | Sí |
| S10 Entrevista | — | **Sí** (participantes/turnos/NLP) | — |

> **Estado de madurez:** encuestas — completo. Entrevistas — implementado (vía documento + S10).
> Pruebas estandarizadas — recorren la vía documento genérica; **sin reglas psicométricas dedicadas**
> todavía (extensión futura).

---

## 5. Limpieza y estandarización EJECUTABLE (propose → decide → apply)

El SIS no aplica cambios a los datos por su cuenta: **propone**, el usuario **decide** (en el host,
pasos `approve/cleaning` y `approve/enrichment`), y luego se **aplica**.

- **Propuestas de transformación** (S8): cada una codifica un `transform_id` + `params`. Hoy el
  registro (`engine/transforms/transform_registry.py`) soporta:
  - `drop_columns` — eliminar columnas (p. ej. administrativas o sin valor analítico).
  - `normalize_scale` — normalizar los valores de una escala a un mapeo canónico (corrige typos e
    inconsistencias detectados en S3, p. ej. unificar "En deesacuerdo" → "En desacuerdo").
- **Aplicación** (host, tras aprobación): el `apply_engine` ejecuta solo las transformaciones
  **aceptadas** sobre los datos y produce un **dataset limpio** (`storage/clean/{id}_clean.csv`),
  reversible e inspeccionable. El archivo original nunca se modifica.
- **Estandarización SPSS:** el `spss_mapper` deriva, de forma determinística, un diccionario SPSS
  (etiquetas de variable/valor, niveles de medición) que alimenta la exportación **`.SAV`** (solo encuestas).

### Metadatos y KPIs (estandarización semántica)
- **Metadatos enriquecidos** (de S7, tras aprobación): constructo/rol/tags por variable → insumo del RAG.
- **KPIs inferidos** (de S7b, tras aprobación): vínculo instrumento↔KPI del catálogo, con evidencia.

---

## 6. Salidas del proceso

- **JSON canónico:** estructura fiel y determinística (variables/preguntas, escalas, distribución,
  trazabilidad). Reproducible vía `canonical_id`.
- **Dataset limpio (`.csv`):** datos con las transformaciones aprobadas aplicadas (encuestas).
- **`.SAV` (SPSS):** encuestas, con diccionario de etiquetas y niveles de medición.
- **JSON consolidado** (lo arma el host): conocimiento para el RAG — metadatos DC, KPIs, hallazgos por
  pregunta y (v2) perfiles por respondente. Es puramente semántico (sin texto crudo ni estados).

---

## 7. Degradación y trazabilidad (garantías)

- Cada etapa emite un **diagnóstico** (`ok` / `skipped` / `degraded` / `failed`) con motivo.
- El resultado global es `completed`, `completed_degraded` o `failed`.
- El SIS **no lanza al host**: un archivo ilegible/vacío se reporta como `failed` y el host lo traduce
  a un `HTTP 422`, sin cambiar el estado del instrumento (permite reintentar).
- Todo lo determinístico es **reproducible**; lo del LLM va sobre datos observados, con validador anti-invención.

---

## 8. Referencias

- Flujo y orquestación: `survey_intelligence/facade.py`.
- Estrategias por instrumento: `survey_intelligence/pipelines/` (base, encuesta, entrevista, prueba_estandarizada, _document).
- Etapas: `survey_intelligence/pipeline/stages/s1..s10`.
- Motores: `survey_intelligence/engine/` (readers, profiling, heuristics, spss, transforms, prompts, parsing, nlp).
- Organización actual del SIS: `ARQUITECTURA_SIS.md`.
- Cómo extender a entrevistas / pruebas estandarizadas: `GUIA_EXTENSION_INSTRUMENTOS.md`.
- Codebooks determinísticos: `DESIGN_CODEBOOK_DETERMINISTA.md`.
- Esquema de BD: `ESQUEMA_BD.md`.
