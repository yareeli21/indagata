# Modelo de Conocimiento y Estrategia de Recuperación Semántica

## Visión general

Esta SPEC formaliza el modelo de conocimiento y la estrategia de recuperación semántica de la plataforma educativa RAG **Indagata**.

Define cómo se representa, organiza, almacena e indexa el conocimiento producido por los instrumentos de recolección de datos educativos, y establece los contratos técnicos que deben respetarse en toda implementación del pipeline semántico.

---

## Principio fundamental

El sistema opera sobre dos planos que no deben mezclarse bajo ninguna circunstancia:

**Plano operativo:** El sistema administra el conocimiento — sabe dónde está, quién lo cargó, en qué estado se encuentra y cómo auditarlo. Esta información sirve para operar el sistema. No aporta nada a la calidad de una respuesta generada.

**Plano semántico:** El sistema comprende el conocimiento — sabe qué significa, a quién describe, qué fenómenos educativos aborda y qué indicadores están presentes. Esta información es la que transforma una búsqueda vectorial en una respuesta útil.

Un embedding generado sobre `hash_md5`, `usuario_carga` o `ruta_original` no solo no ayuda: introduce ruido en el espacio vectorial. La separación entre estos planos es un invariante de arquitectura, no una preferencia de diseño.

---

## Requisitos funcionales

### RF-01 — Separación entre información operativa e información semántica

**Como** sistema RAG educativo,  
**necesito** que la información operativa (trazabilidad técnica, auditoría, administración del ciclo de vida) esté estrictamente separada de la información semántica (conocimiento, contexto educativo, KPIs, hallazgos),  
**para que** el espacio vectorial contenga únicamente señales semánticas relevantes y las respuestas generadas sean precisas, atribuibles y no contaminadas por ruido administrativo.

**Criterios de aceptación:**

- Dado un instrumento procesado, cuando se inspeccionan los embeddings generados, entonces ningún vector contiene información derivada de campos operativos (IDs internos, rutas, hashes, fechas de carga, estados del pipeline).
- Dado un chunk almacenado en ChromaDB, cuando se lee su `document` (contenido embebido), entonces no contiene ningún identificador numérico de base de datos, ninguna ruta de archivo ni ningún nombre de usuario.
- Dado un chunk almacenado en ChromaDB, cuando se leen sus `metadatas`, entonces solo contiene los 13 campos definidos en RF-04 y ningún campo adicional del JSON semántico.

---

### RF-02 — PostgreSQL como capa operativa exclusiva

**Como** operador del sistema,  
**necesito** que PostgreSQL sea la única fuente de verdad para el plano operativo,  
**para que** la auditoría, el control del pipeline, la trazabilidad técnica y la administración de usuarios se gestionen desde una capa relacional con integridad referencial garantizada.

**Criterios de aceptación:**

- Dado cualquier instrumento en el sistema, cuando se consulta su estado de procesamiento, ruta del archivo original, fecha de carga, usuario responsable o hash MD5, entonces esa información se obtiene exclusivamente de las tablas del schema `tt_rag` en PostgreSQL.
- Dado un cambio de estado del pipeline (de `json_generado` a `vectorizado`), cuando se aplica el cambio, entonces se registra únicamente en la columna `estado` de `instrumento_procesado` en PostgreSQL, no en el JSON semántico ni en ChromaDB.
- Dado el registro de una consulta RAG, cuando el usuario hace una pregunta al sistema, entonces los campos `pregunta`, `contexto_enviado`, `respuesta`, `latencia_ms` y `modelo_usado` se guardan en la tabla `rag_log` de PostgreSQL.

**Campos operativos en PostgreSQL (no exhaustivo):**

| Campo | Tabla | Propósito |
|---|---|---|
| `instrumento_id` | `instrumento_procesado` | PK interna del sistema |
| `codigo` | `instrumento_procesado` | Código legible (ENC-042), referencia humana |
| `estado` | `instrumento_procesado` | Estado del pipeline de procesamiento |
| `ruta_json` | `instrumento_procesado` | Ruta al JSON semántico en disco |
| `schema_version` | `instrumento_procesado` | Versión del schema JSON usado |
| `hash_md5` | `raw_data` | Detección de duplicados en carga |
| `usuario_carga` | `raw_data` | FK al usuario que subió el archivo |
| `fecha_carga` | `raw_data` | Timestamp de recepción del archivo |
| `ruta_original` | `raw_data` | Ruta del archivo crudo para descarga |
| `nombre_original` | `raw_data` | Nombre del archivo como lo subió el usuario |
| `tipo_mime` | `raw_data` | Tipo MIME del archivo |
| `tamano_bytes` | `raw_data` | Tamaño del archivo |
| `vector_id` | `documento_vectorizado` | ID del chunk en ChromaDB |
| `tipo_chunk` | `documento_vectorizado` | Tipo del chunk registrado |
| `prompt_version` | `prompt` | Versión del prompt usado en cada etapa |

---

### RF-03 — JSON semántico como representación oficial de conocimiento

**Como** módulo de chunking y vectorización,  
**necesito** que el JSON semántico sea la única fuente de entrada para el proceso de chunking, generación de embeddings e indexación en ChromaDB,  
**para que** el índice vectorial sea un artefacto derivado y regenerable desde una representación de conocimiento estable y completa.

**Criterios de aceptación:**

- Dado un instrumento en estado `estandarizado`, cuando se inicia el proceso de chunking, entonces el módulo lee exclusivamente el archivo `/storage/json/{instrumento_id}.json` y no accede al archivo original del instrumento ni a ninguna otra tabla de PostgreSQL durante la generación de chunks.
- Dado que el JSON semántico se corrige (metadatos actualizados, KPIs revisados), cuando se re-vectoriza el instrumento, entonces ChromaDB puede borrarse y reconstruirse completamente desde el JSON sin pérdida de información.
- Dado un JSON semántico válido, cuando se verifica su estructura, entonces contiene los bloques `contexto`, `dublin_core`, `especifico`, `kpis_inferidos` y `unidades_semanticas`, todos sin campos de naturaleza administrativa.

**Estructura del JSON semántico:**

```
instrumento_semantico.json
│
├── contexto
│   ├── titulo
│   ├── tipo_instrumento          ("encuesta" | "entrevista" | "prueba_estandarizada")
│   ├── descripcion
│   ├── objetivo
│   ├── institucion_responsable
│   ├── poblacion_alcance
│   ├── periodo_inicio
│   ├── periodo_fin
│   ├── idioma                    (default: "es")
│   ├── condiciones_uso
│   └── palabras_clave[]
│
├── dublin_core                   (alineado con ISO 15836)
│   ├── dc_title
│   ├── dc_creator
│   ├── dc_subject[]
│   ├── dc_description
│   ├── dc_publisher
│   ├── dc_contributor
│   ├── dc_date
│   ├── dc_type
│   ├── dc_format
│   ├── dc_identifier             (ej. "IND-ENC-042" — identificador semántico, no ID interno)
│   ├── dc_source
│   ├── dc_language
│   ├── dc_relation
│   ├── dc_coverage
│   └── dc_rights
│
├── especifico                    (estructura varía por tipo_instrumento — ver RF-09)
│
├── kpis_inferidos[]
│   └── cada item:
│       ├── kpi_id
│       ├── nombre_kpi
│       ├── descripcion_kpi
│       ├── evidencia_textual     (por qué este instrumento aporta a este KPI)
│       ├── score_inferencia      (0.0 – 1.0)
│       └── secciones_relacionadas[]
│
├── plan_chunking                 (generado en Paso 1 del IEC — solo para auditoría)
│
└── unidades_semanticas[]         (generado en Paso 4 del IEC — ver RF-06)
```

**Criterio de inclusión de campos en el JSON semántico:**

Un campo pertenece al JSON semántico si cumple al menos una de estas condiciones:
- Un investigador lo necesita para interpretar correctamente los hallazgos del instrumento.
- Permite discriminar si este instrumento es relevante para una consulta educativa específica.
- Aporta contexto que el LLM necesita para generar una respuesta precisa y no alucinada.
- Habilita filtros temáticos, temporales o institucionales en la búsqueda semántica.

---

### RF-04 — ChromaDB como índice vectorial derivado y regenerable

**Como** capa de recuperación semántica,  
**necesito** que ChromaDB actúe únicamente como índice vectorial derivado del JSON semántico,  
**para que** sea posible cambiar el modelo de embeddings, la estrategia de chunking o los metadatos sin pérdida de conocimiento, simplemente regenerando el índice.

**Criterios de aceptación:**

- Dado que se decide cambiar el modelo de embeddings de `paraphrase-multilingual-mpnet-base-v2` a otro, cuando se ejecuta el proceso de re-vectorización, entonces ChromaDB se vacía y reconstruye completamente desde los JSON semánticos existentes sin necesidad de reprocesar los instrumentos originales.
- Dado un chunk almacenado en ChromaDB, cuando se consultan sus datos, entonces contiene exactamente tres componentes: `document` (contenido narrativo), `embedding` (vector de 768 dimensiones) y `metadatas` (los 13 campos definidos a continuación).
- Dado el conjunto completo de chunks de ChromaDB, cuando se reconstruye el conocimiento del sistema, entonces es necesario consultar también los JSON semánticos en disco para obtener la estructura completa — ChromaDB por sí solo no es suficiente.

**Los 13 metadatos de ChromaDB (mínimos y suficientes):**

| Campo | Tipo | Propósito |
|---|---|---|
| `instrumento_id` | int | FK técnica a PostgreSQL. Trazabilidad de sistema. |
| `codigo_instrumento` | string | Referencia legible para atribución al usuario (ej. "ENC-042") |
| `tipo_instrumento` | string | Filtro: `encuesta` / `entrevista` / `prueba_estandarizada` |
| `tipo_chunk` | string | Filtro: `resumen_instrumento` / `unidad_semantica` / `hallazgo` |
| `titulo_chunk` | string | Descripción de la fuente para mostrar al usuario |
| `institucion` | string | Filtro por institución responsable |
| `periodo` | string | Filtro temporal (ej. `"2023-1"`) |
| `poblacion` | string | Contexto de la fuente en la respuesta generada |
| `kpis_ids` | string | Lista JSON serializada: `"[3, 7, 12]"`. Filtro por KPI. |
| `kpis_nombres` | string | Nombres legibles de KPIs para mostrar en atribución |
| `chunk_padre` | string | `id_chunk` del resumen raíz. Habilita retrieval jerárquico. |
| `id_chunk` | string | Identificador del chunk dentro del JSON semántico |
| `idioma` | string | Filtro de idioma |

**Nota sobre `kpis_ids`:** ChromaDB no soporta arrays nativos en metadatos para filtros `$contains`. Se serializa como string JSON y se filtra con `$contains` sobre el string. Es una limitación conocida del motor.

**Campos que no deben estar en ChromaDB bajo ninguna circunstancia:**
Estructura Dublin Core completa, bloque `especifico`, lista `kpis_inferidos` con evidencia, `dimensiones_origen`, datos cuantitativos de unidades, limitaciones metodológicas, `plan_chunking`.

---

### RF-05 — Intelligent Enriched Chunking guiado por LLM

**Como** módulo de chunking,  
**necesito** que un LLM analice el JSON semántico y determine dinámicamente las unidades de conocimiento, su tipo, granularidad y contenido narrativo,  
**para que** cada chunk represente exactamente una unidad semántica coherente, con el nivel de granularidad que el contenido del instrumento justifica, sin asumir estructuras fijas por tipo de instrumento.

**Criterios de aceptación:**

- Dado un JSON semántico con una encuesta de 3 dimensiones simples, cuando se ejecuta el IEC, entonces el sistema puede producir 4 chunks (1 resumen + 3 unidades) o más si detecta hallazgos independientes — no asume una cantidad fija.
- Dado un JSON semántico con una prueba estandarizada de 8 áreas de competencia con hallazgos ricos, cuando se ejecuta el IEC, entonces el sistema puede producir más de 15 chunks si el contenido lo justifica.
- Dado un instrumento donde dos secciones abordan el mismo fenómeno educativo con menos de 100 tokens de contenido relevante cada una, cuando el LLM analiza el plan, entonces las agrupa en un único chunk.
- Dado un instrumento donde una sección aborda dos fenómenos educativos distintos, cuando el LLM analiza el plan, entonces los separa en chunks distintos aunque estén en la misma sección del instrumento original.
- Dado que el LLM produce el plan de chunking, cuando se registra en el JSON semántico, entonces el campo `plan_chunking` contiene el razonamiento del LLM para auditoría y reproducibilidad.

**El proceso IEC opera en cuatro pasos secuenciales:**

```
Paso 1 — Análisis semántico
  Entrada: JSON semántico completo
  LLM produce: plan_chunking con tipo, justificación y referencias por unidad
  Tipos posibles: resumen_instrumento (×1), unidad_semantica (×N), hallazgo (×M)

Paso 2 — Generación de contenido narrativo
  Para cada unidad del plan:
    LLM genera contenido_narrativo siguiendo las reglas de RF-07
    El contenido comienza siempre con el ancla semántica (RF-07)

Paso 3 — Control de longitud (determinista)
  Tokenizar contenido_narrativo con el tokenizador del modelo de embeddings
  Si tokens ≤ 384: chunk aprobado
  Si tokens > 384: solicitar división semántica al LLM
    Sub-chunks: identificadores derivados (chunk_003a, chunk_003b)
    Sub-chunks heredan chunk_padre y ancla semántica
    Chunk original se elimina del plan

Paso 4 — Ensamblado
  Escribir unidades_semanticas[] definitivas en JSON semántico
  Producir lista de chunks como entrada al módulo de vectorización
```

---

### RF-06 — Generación dinámica de chunks y tipos definidos

**Como** sistema de recuperación semántica,  
**necesito** que los chunks se clasifiquen en tres tipos con propósitos y criterios de generación distintos,  
**para que** el retriever pueda recuperar el tipo de información más relevante para cada consulta.

**Criterios de aceptación:**

- Dado cualquier instrumento procesado, cuando se genera el índice vectorial, entonces existe exactamente 1 chunk de tipo `resumen_instrumento` con `chunk_padre = null`.
- Dado un chunk de tipo `unidad_semantica`, cuando se verifica su `chunk_padre`, entonces apunta al `id_chunk` del `resumen_instrumento` del mismo instrumento.
- Dado un chunk de tipo `hallazgo`, cuando se verifica su estructura en el JSON semántico, entonces contiene `dimensiones_origen` con al menos un `id_chunk` de una unidad semántica del mismo instrumento.
- Dado un posible hallazgo identificado por el LLM, cuando no cumple las tres condiciones del umbral de independencia, entonces su contenido se integra al `contenido_narrativo` de su unidad semántica de origen y no se crea un chunk independiente.

**Tipos de chunk:**

**`resumen_instrumento`**
- Cantidad: exactamente 1 por instrumento.
- `chunk_padre`: `null` (raíz de la jerarquía).
- Propósito: responder preguntas amplias sobre el instrumento, servir como contexto de respaldo para respuestas que requieren contexto global.

**`unidad_semantica`**
- Cantidad: variable, determinada por el LLM.
- `chunk_padre`: `id_chunk` del `resumen_instrumento`.
- Criterio de generación: agrupa ítems, preguntas o secciones que abordan el mismo fenómeno educativo con suficiente sustancia para responder una pregunta temática específica.
- Propósito: responder preguntas temáticas específicas sobre una dimensión, sección o área del instrumento.

**`hallazgo`**
- Cantidad: variable (0 a N), determinada por el LLM según el umbral de independencia.
- `chunk_padre`: `id_chunk` del `resumen_instrumento`.
- `dimensiones_origen`: lista de `id_chunk` de las unidades de las que fue extraído.
- Umbral de independencia: el hallazgo debe cumplir las tres condiciones simultáneamente:
  1. Enunciado claro y autónomo (legible sin el instrumento completo).
  2. Evidencia cuantitativa o cualitativa concreta que lo sustenta.
  3. Vinculación a al menos un KPI del catálogo.
- Propósito: responder preguntas directas sobre resultados, evidencia o cifras educativas específicas con máxima precisión.

---

### RF-07 — Ancla semántica como mecanismo de trazabilidad en el contenido

**Como** LLM generando una respuesta,  
**necesito** que cada chunk contenga el contexto interpretativo mínimo para atribuir correctamente la evidencia que presenta,  
**para que** las respuestas generadas citen la fuente con precisión sin necesidad de consultas adicionales al sistema.

**Criterios de aceptación:**

- Dado cualquier chunk de cualquier tipo, cuando se lee su `contenido_narrativo`, entonces comienza con una frase de anclaje que incluye: tipo de instrumento, nombre o descripción del tema principal, institución responsable, población alcanzada y periodo de aplicación.
- Dado un chunk cuyo `contenido_narrativo` no comienza con el ancla semántica, entonces ese chunk se considera inválido y debe regenerarse.
- Dado que el ancla semántica contiene los campos `tipo_instrumento`, `titulo`, `institucion_responsable`, `poblacion_alcance`, `periodo_inicio` y `periodo_fin` del bloque `contexto` del JSON semántico, entonces estos campos son obligatorios en el JSON semántico y no pueden estar vacíos.

**Estructura del ancla semántica:**

```
"En [tipo_instrumento] [titulo_o_tema], aplicado por [institucion_responsable]
a [poblacion_alcance] durante [periodo], ..."
```

Ejemplo para `resumen_instrumento`:
```
"En encuesta de satisfacción estudiantil aplicada por la Universidad Autónoma
del Estado a estudiantes de licenciatura durante el ciclo 2023-1, el instrumento
evalúa seis dimensiones de la experiencia académica..."
```

Ejemplo para `hallazgo`:
```
"En encuesta de satisfacción estudiantil aplicada por la Universidad Autónoma
del Estado a estudiantes de licenciatura durante el ciclo 2023-1, se identificó
que el 67% de los estudiantes reportó deficiencias en la retroalimentación docente,
evidencia que aporta directamente al KPI de Rendimiento Académico..."
```

**El ancla semántica no es dato administrativo.** Es el contexto interpretativo sin el cual el dato del chunk no puede ser correctamente atribuido por el LLM al generar una respuesta.

---

### RF-08 — Modelo de embeddings y límite operativo de tokens

**Como** módulo de vectorización,  
**necesito** un modelo de embeddings con soporte nativo de español, 768 dimensiones y ventana de contexto suficiente para narrativas enriquecidas,  
**para que** los vectores generados capturen señales semánticas en español con alta discriminabilidad y los chunks no sean truncados silenciosamente.

**Criterios de aceptación:**

- Dado el modelo de embeddings seleccionado, cuando se verifica su configuración, entonces es `paraphrase-multilingual-mpnet-base-v2` de sentence-transformers, que produce vectores de 768 dimensiones y tiene una ventana máxima de 384 tokens.
- Dado un `contenido_narrativo` antes de ser embebido, cuando se tokeniza con el tokenizador de `paraphrase-multilingual-mpnet-base-v2`, entonces tiene 384 tokens o menos. Si supera ese límite, se activa la división semántica del Paso 3 del IEC.
- Dado que se decide cambiar el modelo de embeddings en el futuro, cuando se actualiza la configuración, entonces el límite operativo de tokens se ajusta automáticamente a la ventana máxima del nuevo modelo y ChromaDB se re-vectoriza completamente.

**Decisión técnica documentada — Comparativa de modelos:**

| Modelo | Dimensiones | Tokens máx. | Multilingüe | Decisión |
|---|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 dims | 128 tokens | ✓ | Descartado — ventana insuficiente para narrativas enriquecidas |
| `paraphrase-multilingual-mpnet-base-v2` | 768 dims | 384 tokens | ✓ | **Seleccionado** |
| `all-mpnet-base-v2` | 768 dims | 384 tokens | ✗ | Descartado — no soporta español |
| `intfloat/multilingual-e5-large` | 1024 dims | 512 tokens | ✓ | Alternativa si se requieren 500 tokens; mayor costo computacional |

**Límite operativo: 384 tokens.** El módulo de chunking usa el tokenizador de `paraphrase-multilingual-mpnet-base-v2` para verificar longitud antes de aprobar cada chunk. Esta verificación es determinista y no depende del LLM.

---

### RF-09 — Metadatos específicos por tipo de instrumento en el JSON semántico

**Como** bloque `especifico` del JSON semántico,  
**necesito** que la estructura de metadatos propios varíe según el tipo de instrumento,  
**para que** el LLM disponga del contexto metodológico correcto para cada tipo al generar el plan de chunking y el contenido narrativo.

**Criterios de aceptación:**

- Dado un instrumento de tipo `encuesta`, cuando se verifica su bloque `especifico`, entonces contiene: `n_items_total`, `escala_respuesta`, `dimensiones[]` (con `nombre_dimension`, `descripcion`, `n_items`, `items_representativos[]`, `hallazgos_observados`), `metodologia_aplicacion`, `tasa_respuesta` (opcional) y `limitaciones[]`.
- Dado un instrumento de tipo `entrevista`, cuando se verifica su bloque `especifico`, entonces contiene: `tipo_entrevista`, `n_preguntas_guia`, `duracion_estimada`, `guion_tematico[]` (con `tema`, `pregunta_guia`, `preguntas_de_profundizacion[]`, `hallazgos_cualitativos`), `perfil_entrevistados`, `tecnica_analisis` y `limitaciones[]`.
- Dado un instrumento de tipo `prueba_estandarizada`, cuando se verifica su bloque `especifico`, entonces contiene: `n_reactivos_total`, `areas_competencia[]` (con `nombre_area`, `descripcion`, `n_reactivos`, `nivel_cognitivo`, `hallazgos_observados`), `escala_calificacion`, `normas_referencia`, `poblacion_normativa`, `coeficiente_confiabilidad` (opcional), `validez` y `limitaciones[]`.

**Estructura del bloque `especifico` por tipo:**

Para `encuesta`:
```
especifico:
  n_items_total
  escala_respuesta          ("Likert 1-5" | "Sí/No" | "Opción múltiple" | ...)
  dimensiones[]:
    nombre_dimension
    descripcion
    n_items
    items_representativos[]
    hallazgos_observados     (texto libre, síntesis de resultados de la dimensión)
  metodologia_aplicacion    ("Autoadministrada" | "Asistida" | "En línea")
  tasa_respuesta            (opcional)
  limitaciones[]
```

Para `entrevista`:
```
especifico:
  tipo_entrevista           ("Semiestructurada" | "Estructurada" | "Grupos focales")
  n_preguntas_guia
  duracion_estimada
  guion_tematico[]:
    tema
    pregunta_guia
    preguntas_de_profundizacion[]
    hallazgos_cualitativos   (síntesis de respuestas observadas)
  perfil_entrevistados
  tecnica_analisis          ("Análisis de contenido" | "Análisis temático" | ...)
  limitaciones[]
```

Para `prueba_estandarizada`:
```
especifico:
  n_reactivos_total
  areas_competencia[]:
    nombre_area
    descripcion
    n_reactivos
    nivel_cognitivo          (Taxonomía Bloom: recordar / comprender / aplicar / ...)
    hallazgos_observados
  escala_calificacion
  normas_referencia          ("Nacional" | "Internacional" | "Institucional")
  poblacion_normativa
  coeficiente_confiabilidad  (Alpha de Cronbach, opcional)
  validez                    (tipo de evidencia de validez)
  limitaciones[]
```

---

### RF-10 — Vinculación con KPIs educativos

**Como** sistema de recuperación semántica educativa,  
**necesito** que cada instrumento y cada chunk estén vinculados explícitamente con los KPIs educativos del catálogo que pueden evidenciar,  
**para que** el sistema pueda responder preguntas sobre indicadores específicos recuperando evidencia directamente relacionada.

**Criterios de aceptación:**

- Dado un instrumento procesado, cuando se verifica su JSON semántico, entonces el bloque `kpis_inferidos[]` contiene al menos 1 item con `kpi_id`, `nombre_kpi`, `evidencia_textual` (texto que explica la vinculación) y `score_inferencia` (0.0–1.0).
- Dado un chunk de tipo `hallazgo`, cuando se verifica su estructura, entonces `kpis_asociados[]` contiene al menos 1 KPI ID del catálogo. Si no hay KPI asociado, el hallazgo no puede ser chunk independiente.
- Dado un chunk de tipo `unidad_semantica` o `resumen_instrumento`, cuando se verifica `kpis_asociados[]`, entonces puede estar vacío si la unidad no tiene vinculación directa con KPIs del catálogo.
- Dado que los `kpis_ids` en ChromaDB se serializan como string JSON (`"[3, 7, 12]"`), cuando se realiza una consulta filtrada por KPI, entonces el filtro usa `$contains` sobre el string serializado.
- Dado un instrumento y un KPI asociado, cuando se consulta PostgreSQL, entonces la tabla `pregunta_kpi` contiene el registro de la vinculación con `score_inferencia`, complementando la vinculación semántica del JSON.

---

### RF-11 — Trazabilidad completa desde respuesta hasta instrumento original

**Como** usuario de la plataforma que recibe una respuesta generada,  
**necesito** poder trazar esa respuesta hasta el instrumento original del que proviene la evidencia,  
**para que** pueda verificar, descargar y citar la fuente primaria de cualquier afirmación del sistema.

**Criterios de aceptación:**

- Dado una respuesta generada por el sistema RAG, cuando se muestran las fuentes, entonces cada fuente incluye: `codigo_instrumento` (ej. "ENC-042"), `titulo_chunk`, `tipo_instrumento`, `institucion`, `periodo` y `tipo_chunk`.
- Dado un `codigo_instrumento` en la respuesta, cuando el usuario solicita ver la fuente, entonces el sistema consulta PostgreSQL con ese código, obtiene `instrumento_id`, y desde ahí recupera `ruta_original` para ofrecer la descarga del archivo original.
- Dado que una respuesta utiliza evidencia de múltiples instrumentos, cuando se muestran las fuentes, entonces se listan todos los instrumentos contribuyentes con sus metadatos de atribución.
- Dado que se registra una consulta RAG, cuando finaliza la generación, entonces se guarda en `rag_log` con: `pregunta`, `contexto_enviado` (chunks usados con sus `id_chunk`), `respuesta`, `latencia_ms`, `modelo_llm` y `modelo_embeddings`.

**Cadena de trazabilidad:**

```
Respuesta generada
    → chunks fuente (via metadatos ChromaDB: codigo_instrumento, id_chunk)
    → instrumento_procesado (via instrumento_id en PostgreSQL)
    → raw_data (via instrumento_id: ruta_original para descarga)
    → JSON semántico (via ruta_json: contexto completo del instrumento)
```

---

### RF-12 — Regenerabilidad del índice vectorial

**Como** administrador del sistema,  
**necesito** poder regenerar el índice ChromaDB completamente desde los JSON semánticos existentes,  
**para que** los cambios en el modelo de embeddings, la estrategia de chunking o los metadatos no requieran reprocesar los instrumentos originales desde cero.

**Criterios de aceptación:**

- Dado un índice ChromaDB existente y el conjunto de JSON semánticos en `/storage/json/`, cuando se ejecuta la operación de re-vectorización completa, entonces ChromaDB se vacía y reconstruye usando únicamente los JSON semánticos, sin necesidad de acceder a los archivos originales en `/storage/raw/`.
- Dado que un JSON semántico se actualiza (metadatos corregidos, KPIs añadidos), cuando se re-vectoriza ese instrumento, entonces solo los chunks de ese instrumento se actualizan en ChromaDB, y los registros en `documento_vectorizado` de PostgreSQL se actualizan con los nuevos `vector_id`.
- Dado que la re-vectorización completa no es destructiva para el conocimiento, cuando se completa, entonces todos los JSON semánticos en disco siguen intactos y son la fuente canónica del sistema.

---

## Requisitos no funcionales

### RNF-01 — Coherencia semántica de los chunks

Cada chunk debe ser una unidad semántica autocontenida: puede leerse de forma aislada y proporcionar información atribuible, interpretable y vinculada a un fenómeno educativo. Un chunk que requiere leer otro chunk para ser comprensible es un indicador de chunking incorrecto.

### RNF-02 — Límite de tokens verificable

El módulo de chunking debe verificar la longitud de cada `contenido_narrativo` con el tokenizador del modelo de embeddings configurado (`paraphrase-multilingual-mpnet-base-v2`) antes de aprobarlo. La verificación es determinista. El límite operativo es **384 tokens**.

### RNF-03 — Invariantes de arquitectura

Las siguientes reglas son invariantes que no pueden violarse en ninguna implementación:

1. El módulo de chunking lee únicamente el JSON semántico. Nunca accede al archivo original del instrumento.
2. Todo chunk contiene el ancla semántica como preámbulo del `contenido_narrativo`, sin excepción de tipo.
3. Ningún dato administrativo aparece en el `contenido_narrativo` ni en los metadatos de ChromaDB, excepto `instrumento_id` como FK técnica.
4. ChromaDB almacena exclusivamente: `contenido_narrativo` (document), embedding (768 dimensiones) y los 13 metadatos definidos en RF-04.
5. El JSON semántico es la única fuente de verdad semántica. ChromaDB es un artefacto derivado y regenerable.
6. La jerarquía chunk → resumen se expresa solo en metadatos (`chunk_padre`), nunca en el `contenido_narrativo`.
7. Un chunk de tipo `hallazgo` sin al menos 1 KPI asociado no puede existir como chunk independiente.

### RNF-04 — Justificación académica

Esta arquitectura implementa la estrategia **Intelligent Enriched Chunking (IEC)**, formalmente definida como:

> Estrategia de segmentación semántica dinámica guiada por modelos de lenguaje grande para sistemas de Recuperación Aumentada por Generación en dominios especializados, con enriquecimiento contextual obligatorio de cada unidad semántica y separación explícita entre representación de conocimiento e índice vectorial.

**Fundamentación teórica:**

- Lewis et al. (2020) — *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*: establece que la calidad del retrieval depende de la coherencia semántica de las unidades indexadas.
- Gao et al. (2023) — *Precise Zero-Shot Dense Retrieval without Relevance Labels*: demuestra que el enriquecimiento del texto de consulta y del corpus mejora la discriminabilidad vectorial.
- Anthropic (2024) — *Contextual Retrieval*: reporta mejoras de 35–67% en precisión de recuperación cuando cada chunk incluye contexto del documento de origen, evidencia directa de la eficacia del ancla semántica.

**Alineación con estándares:**

- ISO 15836 (Dublin Core Metadata Element Set): los 15 campos `dc_*` del JSON semántico están alineados con este estándar, lo que habilita interoperabilidad con repositorios institucionales y sistemas de gestión documental educativa.

**Contribución metodológica al campo educativo:**

Esta arquitectura aporta en tres niveles:
1. **Técnico:** pipeline RAG con chunking dinámico guiado por LLM para instrumentos educativos heterogéneos, con separación explícita entre representación de conocimiento e índice vectorial.
2. **De dominio:** JSON canónico semántico alineado con ISO 15836 para la representación estandarizada de instrumentos de recolección de datos educativos, vinculado con un catálogo de KPIs formalizados.
3. **Metodológico:** estrategia de atribución de fuentes con trazabilidad completa desde la respuesta generada hasta el instrumento original, mediante una arquitectura de tres capas con responsabilidades claramente separadas.

---

## Tabla de distribución de información

| Tipo de información | PostgreSQL | JSON semántico | Metadatos ChromaDB | Contenido embebido |
|---|:---:|:---:|:---:|:---:|
| IDs internos, hashes, rutas | ✓ | — | — | — |
| Estado del pipeline | ✓ | — | — | — |
| Auditoría de consultas RAG | ✓ | — | — | — |
| Versiones de prompts | ✓ | — | — | — |
| Dublin Core completo (15 campos) | — | ✓ | parcial (filtros) | ✓ (en narrativa) |
| Contexto del instrumento | referencia FK | ✓ | ✓ (filtros) | ✓ (ancla semántica) |
| Metadatos específicos por tipo | — | ✓ | — | ✓ (en narrativa) |
| KPIs inferidos con evidencia | ✓ (`pregunta_kpi`) | ✓ | ✓ (IDs y nombres) | ✓ (en narrativa) |
| Hallazgos sustanciales | — | ✓ (chunk propio) | ✓ (`tipo_chunk=hallazgo`) | ✓ (5 elementos) |
| Hallazgos sin umbral | — | ✓ (en dimensión) | — | ✓ (en unidad) |
| Datos cuantitativos | — | ✓ (opcional) | — | ✓ (si existen) |
| Identificador semántico (`dc_identifier`) | — | ✓ | ✓ (`codigo_instrumento`) | — |
| Periodo y institución | ✓ (FK) | ✓ | ✓ (filtros) | ✓ (ancla semántica) |
| Jerarquía chunk → resumen | — | ✓ (`chunk_padre`) | ✓ (`chunk_padre`) | — |
| Ancla semántica | — | — | — | ✓ (preámbulo obligatorio) |
| Referencias entre chunks (`dimensiones_origen`) | — | ✓ | — | — |
| Plan de chunking del LLM | — | ✓ (auditoría) | — | — |
