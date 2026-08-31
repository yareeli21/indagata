---
inclusion: manual
---

# Estrategia de Intelligent Enriched Chunking
## Chunking dinámico guiado por LLM para recuperación semántica educativa

**Versión:** 1.0  
**Fecha:** Agosto 2026  
**Documento relacionado:** `modelo_conocimiento.md`

---

## Principio rector

El chunking no es una operación mecánica de partición de texto. Es una decisión de comprensión semántica: determinar qué unidades de conocimiento existen dentro de un instrumento, cuáles son independientes, cuáles deben agruparse y cuáles contienen evidencia suficiente para ser recuperadas de forma autónoma.

Esa decisión requiere comprensión del dominio educativo, del contenido específico del instrumento y de los KPIs que están en juego. Un algoritmo de partición por tokens o por estructura fija no tiene ninguna de esas capacidades. Un LLM que ya procesó el instrumento en etapas anteriores del pipeline, sí.

**ChromaDB es un índice vectorial derivado del JSON semántico, no una base de datos independiente.** Si el JSON semántico cambia, ChromaDB puede regenerarse completamente. Esta propiedad es una decisión de arquitectura deliberada.

---

## 1. El problema con los enfoques estándar de chunking

### Chunking por tamaño fijo
Corta el texto cada N tokens con solapamiento. No respeta límites semánticos. Un hallazgo puede partirse en dos fragmentos que pierden coherencia por separado. Una dimensión puede mezclarse con la siguiente. El embedding resultante mezcla señales semánticas distintas, degradando la precisión del retrieval.

### Chunking por estructura fija por tipo
Asume que toda encuesta produce N chunks de dimensiones, toda entrevista produce N chunks de temas guía. Eso no refleja la realidad: instrumentos del mismo tipo tienen complejidades muy distintas. Una plantilla fija produce chunks vacíos en instrumentos simples y chunks sobrecargados en instrumentos complejos. Ambos degradan la calidad del embedding.

### Chunking semántico automático sin LLM
Los métodos de clustering de embeddings o segmentación por coherencia de oraciones no tienen conocimiento del dominio educativo. No saben que un hallazgo sobre deserción merece tratamiento distinto que una pregunta demográfica. No pueden vincular KPIs. No pueden evaluar si un resultado tiene sustancia suficiente para ser recuperado de forma autónoma.

### La solución: Intelligent Enriched Chunking guiado por LLM
El LLM analiza el JSON semántico completo y toma las decisiones de chunking basándose en comprensión real del contenido. El resultado es un conjunto de chunks de tamaño y número variables, cada uno representando exactamente una unidad semántica coherente del instrumento, con el nivel de granularidad que el contenido justifica.

---

## 2. El JSON semántico como única fuente de chunking

El módulo de chunking no lee el archivo original del instrumento. No procesa el Excel, el PDF ni el SPSS. Lee únicamente el JSON semántico producido por el pipeline.

Esto es una decisión de arquitectura importante por tres razones:

**Calidad garantizada:** El JSON semántico ya fue limpiado, estandarizado, enriquecido con metadatos Dublin Core y vinculado con KPIs en etapas anteriores. El chunking opera sobre conocimiento ya destilado, no sobre datos crudos.

**Separación de responsabilidades:** El pipeline de procesamiento transforma datos en conocimiento. El módulo de chunking transforma conocimiento en unidades recuperables. Son dos operaciones distintas con entradas y salidas bien definidas.

**Regenerabilidad:** Como ChromaDB se construye exclusivamente desde el JSON semántico, puede regenerarse en cualquier momento. Si el modelo de embeddings cambia, si los metadatos se corrigen, si se añaden KPIs: borrar y reconstruir el índice es una operación segura y predecible.

---

## 3. Proceso de Intelligent Enriched Chunking

El módulo opera en cuatro pasos secuenciales:

### Paso 1 — Análisis semántico del JSON

El LLM recibe el JSON semántico completo del instrumento y produce un **plan de chunking**: una lista ordenada de unidades de conocimiento identificadas, cada una con tipo propuesto, justificación, referencias a las secciones del JSON de origen y estimación de densidad informativa.

El prompt de análisis instruye al LLM a identificar:
- Unidades temáticamente cohesivas (dimensiones, secciones, áreas de competencia, temas guía).
- Hallazgos que superan el umbral de independencia (ver sección 4).
- El resumen global del instrumento como unidad raíz.
- Unidades que deben agruparse porque por separado no tienen coherencia suficiente.
- Unidades que deben dividirse porque combinan fenómenos educativos distintos.

### Paso 2 — Generación del contenido narrativo

Para cada unidad identificada en el plan, el LLM genera el `contenido_narrativo`: la prosa enriquecida que será embebida. Esta narrativa sigue las reglas de construcción definidas en la sección 5 de este documento.

El LLM recibe para esta generación: la unidad identificada, el contexto del instrumento (ancla semántica: tipo, institución, periodo, población), los KPIs vinculados a esa unidad y, para chunks de hallazgo, la evidencia cuantitativa o cualitativa de soporte.

### Paso 3 — Control de longitud

El sistema verifica que ningún `contenido_narrativo` supere el límite de tokens establecido. Si una unidad supera el límite, el módulo solicita al LLM que la divida en sub-chunks preservando la coherencia temática. Cada sub-chunk hereda el contexto del ancla semántica del padre y recibe un identificador derivado (`chunk_003a`, `chunk_003b`).

La división no es mecánica — el LLM decide el punto de corte semánicamente correcto.

### Paso 4 — Ensamblado final y registro

El módulo produce la lista definitiva de chunks con su `contenido_narrativo`, `tipo`, metadatos para ChromaDB y referencia de jerarquía (`chunk_padre`, `dimensiones_origen`). Esta lista se escribe en el JSON semántico en el campo `unidades_semanticas` y se usa como entrada para la vectorización.

---

## 4. Tipos de chunk y criterios de generación

### `resumen_instrumento`
**Cantidad:** Exactamente 1 por instrumento.  
**Criterio:** Siempre se genera. Es la representación completa del instrumento como objeto de conocimiento.  
**`chunk_padre`:** `null`. Es la raíz de la jerarquía.  
**Propósito de recuperación:** Responder preguntas sobre qué es el instrumento, quién lo produce, a qué población estudia y qué KPIs aborda en general. También sirve como contexto de respaldo cuando los chunks hijos no aportan suficiente información.

### `unidad_semantica`
**Cantidad:** Variable. El LLM determina cuántas unidades temáticamente cohesivas existen.  
**Criterio de generación:** Una unidad merece chunk propio cuando agrupa ítems, preguntas o secciones que abordan el mismo fenómeno educativo y cuyo contenido combinado tiene sustancia suficiente para responder una pregunta temática específica.  
**Criterio de agrupación:** Dos secciones que por separado tienen menos de 100 tokens de contenido relevante deben agruparse en un solo chunk si pertenecen al mismo fenómeno educativo.  
**Criterio de división:** Una unidad que combina dos fenómenos educativos distintos (por ejemplo, satisfacción académica y condiciones de infraestructura) debe dividirse aunque esté en la misma sección del instrumento original.  
**`chunk_padre`:** `id_chunk` del `resumen_instrumento`.

### `hallazgo`
**Cantidad:** Variable. 0 a N por instrumento dependiendo del contenido.  
**Criterio de independencia (umbral de hallazgo):** Un hallazgo justifica chunk propio cuando cumple las tres condiciones simultáneamente:
1. Tiene un enunciado claro y autónomo (puede leerse sin el instrumento completo).
2. Tiene evidencia cuantitativa o cualitativa concreta que lo sustenta.
3. Se vincula a al menos un KPI educativo del catálogo.

Si el hallazgo no cumple las tres condiciones, su contenido se integra al `contenido_narrativo` de la unidad semántica de la que proviene.  
**`chunk_padre`:** `id_chunk` del `resumen_instrumento`.  
**`dimensiones_origen`:** Lista de `id_chunk` de las unidades semánticas de las que fue extraído.

---

## 5. Construcción del contenido narrativo por tipo

El `contenido_narrativo` es texto en prosa, coherente y autocontenido. Nunca contiene datos administrativos. Siempre abre con el ancla semántica del instrumento.

### Ancla semántica — Preámbulo obligatorio en todo chunk

Todo chunk, sin excepción de tipo, abre con una frase de anclaje construida desde el bloque `contexto` del JSON semántico:

```
"En [tipo_instrumento] sobre [tema_principal], aplicado por [institucion_responsable] 
a [poblacion_alcance] durante [periodo_inicio]-[periodo_fin], [continuación específica 
del tipo de chunk]..."
```

El ancla no es dato administrativo. Es el contexto interpretativo mínimo para que el LLM genere respuestas correctamente atribuidas. Sin ella, el modelo puede generar *"según los datos disponibles..."* en lugar de *"según la encuesta aplicada por X a estudiantes de licenciatura en 2023-1..."*.

### Contenido narrativo para `resumen_instrumento`

Después del ancla semántica, el resumen incluye en prosa continua:
- Qué mide o explora el instrumento y con qué objetivo.
- A qué fenómenos educativos está orientado.
- Cómo está estructurado (sin entrar en detalle de cada sección).
- Cuáles son los KPIs educativos presentes y en qué medida.
- Los hallazgos globales más significativos del instrumento.
- Las limitaciones principales señaladas.

El resumen es la narrativa de mayor densidad semántica del instrumento. Cuando una consulta es amplia (*"¿qué instrumentos abordan bienestar estudiantil?"*), es el chunk más probable de ser recuperado.

### Contenido narrativo para `unidad_semantica`

Después del ancla semántica, la unidad incluye:
- Qué mide esta dimensión, sección o área de competencia específicamente.
- Qué preguntas o ítems la componen (mencionados semánticamente, no como lista numerada).
- Qué hallazgos o tendencias se observan dentro de esta unidad.
- Qué KPIs educativos se evidencian en esta unidad y cómo.
- Datos cuantitativos relevantes si existen (porcentajes, promedios, frecuencias).

La unidad semántica es el chunk más probable de ser recuperado para preguntas temáticas específicas (*"¿qué dice el instrumento sobre la experiencia docente?"*).

### Contenido narrativo para `hallazgo`

El hallazgo es el chunk de mayor precisión del sistema. Su construcción sigue una estructura en cinco elementos, todos en prosa continua:

1. **Ancla semántica** (preámbulo obligatorio).
2. **Enunciado del hallazgo:** qué se encontró, expresado con claridad y sin ambigüedad.
3. **Evidencia de soporte:** el dato cuantitativo o la síntesis cualitativa que sustenta el enunciado.
4. **Vinculación al KPI:** cómo este hallazgo aporta evidencia al indicador educativo específico, citando el nombre del KPI.
5. **Implicación interpretativa:** qué significa este hallazgo en el contexto educativo estudiado (una o dos oraciones). Esta parte transforma el dato en conocimiento usable por el LLM.

La implicación interpretativa es el elemento diferenciador. Un chunk de hallazgo sin implicación es un dato que el LLM puede usar para responder. Un chunk con implicación es conocimiento que el LLM puede usar para razonar.

---

## 6. Límite de tokens y modelo de embeddings

### Decisión sobre el límite de tokens

El límite de 500 tokens requiere una aclaración técnica importante. Los modelos de sentence-transformers con embeddings de 768 dimensiones tienen ventanas de contexto de 384 tokens máximo:

| Modelo | Dimensiones | Tokens máx. | Multilingüe |
|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 dims | 128 tokens | ✓ |
| `paraphrase-multilingual-mpnet-base-v2` | 768 dims | 384 tokens | ✓ |
| `all-mpnet-base-v2` | 768 dims | 384 tokens | ✗ (inglés) |
| `intfloat/multilingual-e5-large` | 1024 dims | 512 tokens | ✓ |

**Recomendación:** Usar `paraphrase-multilingual-mpnet-base-v2` con límite operativo de **384 tokens** por chunk. Este modelo cumple los tres requisitos: 768 dimensiones, soporte de español, y ventana suficiente para narrativas enriquecidas.

Si se requieren estrictamente 500 tokens sin truncación, la alternativa es `intfloat/multilingual-e5-large` (512 tokens, 1024 dimensiones). Mayor calidad, mayor costo computacional.

**Regla de control:** El módulo de chunking mide el `contenido_narrativo` con el tokenizador del modelo elegido antes de enviar a ChromaDB. Si supera el límite, activa la división semántica (Paso 3 del proceso). Esta verificación es determinista — no depende del LLM.

### División de chunks que superan el límite

Cuando una unidad semántica supera el límite después de la generación narrativa, el LLM recibe:
- El `contenido_narrativo` completo que superó el límite.
- La instrucción de dividirlo en 2 o más sub-chunks manteniendo coherencia temática.
- La restricción de que cada sub-chunk debe comenzar con el ancla semántica.

Los sub-chunks heredan el `chunk_padre` del chunk original y reciben identificadores derivados con sufijo alfabético (`chunk_003a`, `chunk_003b`). El chunk original desaparece — solo existen los sub-chunks.

---

## 7. Metadatos mínimos en ChromaDB

ChromaDB almacena exclusivamente lo necesario para filtrado, recuperación y atribución de fuentes. El JSON semántico completo permanece en disco.

| Campo | Tipo | Propósito |
|---|---|---|
| `instrumento_id` | int | Trazabilidad técnica a PostgreSQL |
| `codigo_instrumento` | string | Referencia legible para atribución de fuente al usuario |
| `tipo_instrumento` | string | Filtro: `encuesta` / `entrevista` / `prueba_estandarizada` |
| `tipo_chunk` | string | Filtro: `resumen_instrumento` / `unidad_semantica` / `hallazgo` |
| `titulo_chunk` | string | Mostrar al usuario como descripción de la fuente |
| `institucion` | string | Filtro por institución |
| `periodo` | string | Filtro temporal (ej. `"2023-1"`) |
| `poblacion` | string | Contexto de la fuente en la respuesta generada |
| `kpis_ids` | string | JSON serializado de IDs: `"[3, 7, 12]"`. Filtro por KPI educativo |
| `kpis_nombres` | string | Nombres legibles de los KPIs para mostrar en atribución |
| `chunk_padre` | string | `id_chunk` del resumen raíz. Habilita retrieval jerárquico |
| `id_chunk` | string | Identificador dentro del JSON semántico (`chunk_001`) |
| `idioma` | string | Filtro de idioma |

**Total: 13 campos.** Ninguno contiene el JSON semántico ni duplica estructuras del instrumento.

### Qué no debe estar en ChromaDB

Los siguientes campos deben mantenerse exclusivamente en el JSON semántico y nunca en ChromaDB:

- Estructura Dublin Core completa (`dc_*`).
- Bloque `especifico` con metadatos por tipo de instrumento.
- Lista detallada de `kpis_inferidos` con evidencia textual y scores.
- Dimensiones, ítems representativos, guiones temáticos o reactivos.
- `dimensiones_origen` de los chunks de hallazgo.
- Datos cuantitativos de las unidades semánticas.
- Limitaciones del instrumento.

Estos campos son necesarios para reconstruir el contexto completo cuando el usuario solicita ver la fuente, pero no son necesarios para el retrieval vectorial.

---

## 8. Información exclusiva del JSON semántico

El JSON semántico contiene todo lo que ChromaDB no tiene. Su propósito es doble: ser la fuente de generación del índice vectorial y ser la fuente de consulta cuando el usuario quiere ver el instrumento completo o cuando el sistema necesita construir respuestas con contexto profundo.

Información que existe solo en el JSON semántico:
- Estructura Dublin Core completa con los 15 campos.
- Metadatos específicos del tipo de instrumento (dimensiones con ítems, guión de entrevista, áreas de competencia con taxonomía Bloom).
- KPIs inferidos con evidencia textual completa, scores de inferencia y secciones relacionadas.
- `dimensiones_origen` de cada chunk de hallazgo.
- Datos cuantitativos detallados por unidad.
- Limitaciones metodológicas del instrumento.
- El plan de chunking generado por el LLM (para auditoría y regeneración).
- Historial de versiones del JSON (si el instrumento fue actualizado).

---

## 9. Cómo justificar esta estrategia en un proyecto de investigación

### Nombre formal de la estrategia

**Intelligent Enriched Chunking (IEC):** estrategia de segmentación semántica dinámica guiada por modelos de lenguaje grande para sistemas de Recuperación Aumentada por Generación en dominios especializados.

### Fundamentación teórica

**Sobre la superioridad del chunking semántico sobre el particionado fijo:**  
La literatura en RAG (Lewis et al., 2020; Gao et al., 2023) establece que la calidad del retrieval depende directamente de la coherencia semántica de los chunks. El particionado por tokens fijos produce fragmentos que mezclan señales semánticas distintas, degradando la precisión del vector resultante. El chunking guiado por comprensión del contenido produce unidades semánticamente cohesivas que generan embeddings de mayor calidad y mayor discriminabilidad en el espacio vectorial.

**Sobre el enriched chunking:**  
La incorporación de metadatos contextuales dentro del contenido embebido (contexto del instrumento, KPIs, ancla semántica) se fundamenta en el principio de que el embedding de un fragmento aislado pierde información crítica de atribución y contexto que es necesaria tanto para el retrieval como para la generación. Trabajos sobre contextual retrieval (Anthropic, 2024) demuestran mejoras de 35-67% en precisión de recuperación cuando cada chunk incluye contexto del documento de origen.

**Sobre la separación entre índice vectorial y representación de conocimiento:**  
ChromaDB como índice derivado del JSON semántico implementa el principio de separación de responsabilidades: la representación del conocimiento (JSON semántico) es independiente de la estrategia de indexación (ChromaDB). Esto permite cambiar el modelo de embeddings, la estrategia de chunking o el motor vectorial sin pérdida de conocimiento, lo cual es una propiedad deseable en sistemas de producción y una contribución metodológica justificable en investigación.

**Sobre la dinamicidad guiada por LLM:**  
La variabilidad en la producción de chunks responde a la variabilidad inherente de los instrumentos educativos como artefactos de investigación. Asumir una granularidad fija impone una estructura artificial que no refleja la estructura del conocimiento. Delegar la decisión de granularidad al LLM convierte el chunking en una operación de comprensión, no de partición.

### Contribución metodológica al campo

Para un proyecto de titulación, esta estrategia representa una contribución en tres niveles:

**Nivel técnico:** Implementación de un pipeline RAG con chunking dinámico guiado por LLM aplicado a instrumentos educativos heterogéneos, con separación explícita entre representación de conocimiento e índice vectorial.

**Nivel de dominio:** Definición de un JSON canónico semántico alineado con ISO 15836 (Dublin Core) para la representación estandarizada de instrumentos de recolección de datos educativos, vinculado con un catálogo de KPIs educativos formalizados.

**Nivel metodológico:** Diseño de una estrategia de atribución de fuentes con trazabilidad completa desde la respuesta generada hasta el instrumento original, mediante una arquitectura de tres capas (PostgreSQL operativo + JSON semántico + ChromaDB derivado) con responsabilidades claramente separadas.

---

## 10. Flujo completo del módulo de chunking

```
ENTRADA: JSON semántico en /storage/json/{instrumento_id}.json
         Estado del instrumento: "json_generado"
         │
         ▼
[Paso 1] Análisis semántico por LLM
         ├── LLM recibe JSON semántico completo
         ├── Produce plan de chunking:
         │     [resumen_instrumento × 1]
         │     [unidad_semantica × N (variable)]
         │     [hallazgo × M (0..N, según umbral)]
         └── Plan guardado en JSON semántico (campo: plan_chunking)
         │
         ▼
[Paso 2] Generación de contenido narrativo por LLM
         ├── Para cada unidad en el plan:
         │     ├── Construir ancla semántica
         │     ├── Generar prosa enriquecida según tipo
         │     └── Vincular KPIs al contenido
         └── Resultado: lista de chunks con contenido_narrativo
         │
         ▼
[Paso 3] Control de longitud (determinista, no LLM)
         ├── Tokenizar contenido_narrativo con tokenizador del modelo
         ├── Si tokens ≤ límite → chunk aprobado
         └── Si tokens > límite → solicitar división semántica al LLM
               ├── Sub-chunks heredan ancla semántica
               ├── Identificadores derivados: chunk_003a, chunk_003b
               └── Chunk original eliminado del plan
         │
         ▼
[Paso 4] Ensamblado final
         ├── Escribir unidades_semanticas[] en JSON semántico
         ├── Actualizar estado: "json_generado" → lista para vectorización
         └── SALIDA: lista definitiva de chunks validados
         │
         ▼
[Vectorización — módulo separado]
         ├── Para cada chunk en la lista:
         │     ├── Generar embedding sobre contenido_narrativo
         │     ├── Construir metadatos para ChromaDB (13 campos)
         │     └── Insertar en colección instrumentos_edu
         ├── Registrar en documento_vectorizado (PostgreSQL)
         └── Actualizar estado instrumento: "vectorizado"

SALIDA FINAL:
  - JSON semántico actualizado con unidades_semanticas[] definitivas
  - Índice ChromaDB actualizado
  - Registro en documento_vectorizado (PostgreSQL)
  - Estado del instrumento: "vectorizado"
```

---

## 11. Invariantes del sistema

Estas reglas no pueden violarse en ninguna implementación del módulo:

1. El módulo de chunking lee únicamente el JSON semántico. Nunca accede al archivo original del instrumento.
2. Todo chunk contiene el ancla semántica como preámbulo del contenido embebido, sin excepción de tipo.
3. Ningún dato administrativo (IDs de base de datos, rutas, hashes, fechas de carga, nombres de usuario) aparece en el contenido embebido ni en los metadatos de ChromaDB, excepto `instrumento_id` que sirve como FK técnica.
4. ChromaDB no almacena el JSON semántico ni ningún subconjunto estructural del mismo. Solo almacena el `contenido_narrativo`, el embedding y los 13 campos de metadatos definidos.
5. El JSON semántico es la única fuente de verdad semántica. ChromaDB es un artefacto derivado y regenerable.
6. Cada chunk es una unidad semántica autocontenida: puede ser leída de forma aislada y aún así proporcionar información atribuible, interpretable y vinculada a un KPI educativo.
7. La jerarquía chunk → resumen se expresa solo en metadatos (`chunk_padre`), nunca en el contenido embebido.
