# Rediseño del texto indexado del RAG: estructura legible + estadística agregada por dimensión

El cambio reescribe *qué texto* indexa el `visualization-service` para que cada chunk sea prosa densa en español en vez de nombres de columna crudos y opciones numéricas sueltas. Introduce dos módulos puros/aislados (`agregacion.py` para estadística agregada por dimensión, `original_txt.py` para parsear el `.txt` original y mapear `question_id→dimensión`), y hace que `sources.construir_chunks` orqueste ambos devolviendo una `list[ChunkIndexable]` ya redactada que `rag.py` indexa directamente. No se toca el troceo, el contrato HTTP ni ninguno de los módulos prohibidos. El objetivo real del usuario —que el RAG deje de responder "información muy general"— se ataca generando chunks de estructura (qué mide el instrumento) y de hallazgos (media, DE, % extremo alto, ítem más alto/bajo, n) por dimensión.

**Watch for:** redundancia cosmética "Dimensión Dimensión" en el encabezado del chunk de estructura, solo en modo degradado sin `.txt` (NIT, confirmed). Ningún hallazgo bloqueante.

**Verdict**: APPROVED

## High-level view

La decisión de arquitectura central es devolver chunks pre-redactados en lugar de un texto monolítico troceado, para garantizar "un chunk = una dimensión". `rag.py` aplana cada `ChunkIndexable` a piezas y solo re-trocea las que superan la ventana, numerando `id`/`chunk_index` sobre la lista aplanada; la metadata gana `clase_chunk` y `dimension` sin alterar las claves existentes, así que el chat y el frontend siguen funcionando sin cambios.

El mapeo `question_id→dimensión` usa dos métodos con precedencia: posicional contra el `.txt` (primario, resuelve la colisión de prefijos truncados `Habilidades_par` por posición) y por prefijo reparando mojibake (fallback degradado). El chequeo monotónico barato de §15.1 descarta reordenamientos patológicos antes de aceptar el posicional, y el conteo desigual o la ausencia de `.txt` también fuerzan el fallback.

La invariante "nunca un chunk por respondente" vive en `agregacion.py` por construcción, y "nunca nan/`\ufffd` en texto citable" se garantiza en origen: `n==0` devuelve `None` (sin chunk, sin formatear conjuntos vacíos) y el `.txt` se lee en utf-8 estricto degradando a `None` ante bytes ilegibles.

La precedencia de título se reordenó a `dc:title → .txt → instrument.title` con un punto único de verdad, de modo que las fuentes citadas muestran el título real del instrumento (IEAE) y no el nombre del CSV.

La degradación es grácil en todos los caminos: cada bloque va en su propio `try/except`, sin `.txt` la estructura cae a etiquetas por prefijo y los hallazgos se generan igual, y sin `respondents` solo se emiten chunks de estructura.

<details>
<summary>Issues (1)</summary>

1. **Redundancia "Dimensión Dimensión" en degradado** — en modo fallback el encabezado del chunk de estructura queda `Dimensión «Dimensión <Prefijo> (agrupación aproximada)»`; quitar el prefijo literal de la etiqueta de `mapa_por_prefijo` o no anteponer `Dimensión «...»` cuando el mapa viene del fallback.

</details>

<details>
<summary>Details</summary>

### Chunks pre-redactados en vez de texto monolítico troceado

El diseño (§3.1) eligió devolver `list[ChunkIndexable]` ya redactada en lugar de un `str` grande que `chunking.trocear` partiría por 800 chars, lo que rompería la unidad "un chunk = una dimensión" que la usuaria pidió. `construir_chunks` emite cabecera + un chunk por dimensión de estructura y un chunk por dimensión/pregunta de hallazgos + resumen global. `extraer_texto` se conserva intacto como último fallback.

El re-troceo solo ocurre cuando una pieza supera `chunking.VENTANA`, y la numeración se hace sobre la lista **aplanada** (`piezas`), no sobre la original, de modo que `id`/`chunk_index` quedan secuenciales y únicos aunque un chunk se expanda; `clase_chunk`/`dimension` se propagan a cada pieza. El test `test_chunk_sobredimensionado_se_aplana` confirma ids únicos y metadata propagada.

```
construir_chunks(artefacto, id)
   ├─ ESTRUCTURA: cabecera (título real + descripción + constructo)
   │              + 1 chunk por dimensión (ítems redactados del .txt)
   └─ HALLAZGOS:  1 chunk por dimensión likert
                  + 1 por numérica / categórica / binaria
                  + resumen global
        │
        ▼ (rag.py) _aplanar_piezas → re-trocea solo si > VENTANA
        ▼ numeración id/chunk_index sobre lista APLANADA
        ▼ metadata = claves existentes + clase_chunk + dimension
```

### Mapeo question_id → dimensión: posicional con chequeo monotónico, prefijo como fallback

El método primario (§5.4 m1) aplana las secciones del `.txt` y hace `zip` posicional con las preguntas likert del JSON, lo que separa la colisión de prefijo truncado `Habilidades_par` (q20–q22 vs q31–q33) por posición. Antes de aceptarlo, `_secuencia_monotonica` (§15.1) agrupa por prefijo de aparición contigua y exige que cada grupo sea `1..k` creciente; un reordenamiento patológico (test `test_mapa_orden_no_monotonico_devuelve_vacio`) o un conteo desigual degradan a prefijo. La doble condición (conteo + monotonicidad) es exactamente la especificada y está cubierta por tests.

El fallback `mapa_por_prefijo` repara el mojibake real cp850↔utf-8 (`Organizaci├│n_y_` → `Organización_y_`), etiqueta la dimensión como `"Dimensión <Prefijo> (agrupación aproximada)"` y emite `WARNING` ante colisión. El intento cp1252 primero falla sobre glifos como `├│` y se salta a cp850, comportamiento verificado por `test_mapa_por_prefijo_repara_mojibake_cp850`.

Sobre esta etiqueta aparece el único hallazgo: `_chunks_estructura_dimension` antepone `Dimensión «{dim}»` y, en degradado, `dim` ya empieza por `"Dimensión "`, produciendo `Dimensión «Dimensión Organización_y_ (agrupación aproximada)»`. Es cosmético (confirmed), solo en el camino sin `.txt`, sigue en español y es citable, pero conviene limpiarlo.

### Estadística agregada por dimensión y la invariante "nunca un chunk por respondente"

`agregacion.py` concatena todos los valores válidos (ítems × respondentes) de una dimensión likert en un vector, calcula media y DE poblacional (`ddof=0`), `pct_alto` por umbral del tercio superior del rango efectivo (`scale_min + 2*(scale_max-scale_min)/3`, cae a 1..5 si falta o es inválido) e ítem más alto/bajo por media de cada `question_id`. `n` es el número de respondentes con ≥1 valor válido en la dimensión. Numéricas y categóricas/binarias producen cada una su propio hallazgo. La invariante vive aquí por construcción: las funciones agregan sobre `respondents` y devuelven un objeto por dimensión; `sources` no itera respondentes para emitir chunks.

`_num` excluye `bool` explícitamente (es subclase de `int`), acepta str con coma decimal y descarta no numéricos; `test_num_excluye_bool` y `test_agregar_likert_str_con_coma_decimal` lo fijan.

### Nunca nan ni carácter de reemplazo en texto citable

El saneo está en origen, no en los consumidores. Si tras `_num` el conjunto queda vacío (`n==0`), las `agregar_*` devuelven `None` y el orquestador no emite chunk; nunca se llama a `np.mean([])` ni se formatea `nan`. Los porcentajes solo se calculan con `n>0`. `leer_texto_original` lee en utf-8 estricto y degrada a `None` ante `UnicodeDecodeError` en vez de inyectar `\ufffd` (`test_leer_texto_original_ilegible_devuelve_none`). El test de integración afirma explícitamente que los documentos indexados no contienen `├`, `\ufffd` ni `nan`.

### Precedencia de título con punto único de verdad

`extraer_metadata` reordenó la fórmula a `dc:title → titulo_override(.txt) → instrument.title → f"Instrumento {id}"`, invirtiendo la precedencia anterior que ponía el nombre del CSV primero. `construir_chunks` y el router derivan el título por el mismo camino (`titulo_override_txt` + `extraer_metadata`), eliminando la divergencia que señaló la revisión de diseño entre §6.1 y §6.2. El router hace una lectura extra del `.txt` para la metadata; es una decisión aceptada (FEAT-002 asunción 3) a cambio de una única lógica de resolución. Los cuatro casos de precedencia están cubiertos por `test_titulo_*`, y el de integración confirma que inst_1 cita "IEAE" y no `enc_01_respondido.csv`.

### Contrato HTTP y archivos prohibidos

Verificado contra el baseline del task (`ef5cd79..HEAD`): el diff toca solo `agregacion.py`, `original_txt.py`, `sources.py`, `rag.py` y tests. No aparecen `chunking.py`, `ollama_client.py`, `prompt.py`, `chroma_client.py`, `embeddings.py`, los schemas ni `requirements.txt`. El cambio en `rag.py` es aditivo: añade las claves escalares `clase_chunk`/`dimension` sin renombrar las existentes (`instrumentoId, titulo, tipo, investigador, kpis, investigacionId, chunk_index`), mantiene la serialización de kpis a JSON string y la respuesta `IndexResponse`. El test de integración afirma que el set de claves de `IndexResponse` no cambió y que cada metadata trae las claves existentes más las dos aditivas.

### Degradación grácil

Cada bloque (cabecera, estructura por dimensión, cada likert, numérica/categórica, resumen) va en su propio `try/except` con `logger.warning` y continuación, espejando el estilo defensivo de `sources.py`. Sin `.txt` la estructura cae a etiquetas por prefijo y los hallazgos se generan igual; sin `respondents` solo se emiten chunks de estructura; sin `instrument`/preguntas se devuelve `[]` y el router degrada al camino `extraer_texto` + `trocear`. Los tests `test_degradacion_sin_txt`, `test_sin_respondents_solo_estructura` y `test_sin_instrument_devuelve_vacio` cubren estas ramas.

### Cobertura de tests

Unit sobre `agregacion` (media/DE/pct_alto, extremos, distribución categórica, redacción en español, casos borde: todos None, un solo respondente, escala no 1..5, bool, coma decimal, resumen global sin likert/sin numéricas/vacío), sobre `original_txt` (parseo de 6 secciones/21 ítems, posicional con colisión resuelta, conteo desigual, orden no monotónico, fallback con mojibake, ambas convenciones de ruta con BD mockeada, lectura ilegible→None) y sobre `sources.construir_chunks` (número/clase de chunks con y sin `.txt`, degradación, `[]`, aplanado de chunk sobredimensionado, descarte de piezas cortas, precedencia de título). Integración ligera de `POST /rag/index` sobre el inst_1 real con embeddings y Chroma mockeados. Suite completa: 43/43 pasan; compileall del `app` sin errores.

**Not tested:** el camino real por BD de `_ruta_relativa_desde_bd` (PostgreSQL) queda mockeado/forzado a `None` en todos los tests; la resolución del `.txt` por la consulta a `RawData` no se ejercita contra una BD real, solo la resolución de ruta con la BD mockeada. Es consistente con el patrón del servicio y aceptable para esta demo.

</details>

<details>
<summary>Mapa de archivos</summary>

- `services/visualization-service/app/core/agregacion.py` (nuevo) — estadística agregada por dimensión y redacción en español; módulo puro sin I/O.
- `services/visualization-service/app/core/original_txt.py` (nuevo) — localización/lectura del `.txt`, parseo de estructura, mapeo posicional + fallback por prefijo con reparación de mojibake.
- `services/visualization-service/app/core/sources.py` — `extraer_metadata` reordena la precedencia de título; nueva `ChunkIndexable` + `construir_chunks` + `titulo_override_txt`; `extraer_texto` intacto.
- `services/visualization-service/app/routers/rag.py` — `POST /rag/index` usa `construir_chunks`, aplana piezas, numera sobre la lista aplanada y añade metadata aditiva; contrato HTTP intacto.
- `services/visualization-service/tests/{conftest,test_agregacion,test_original_txt,test_sources_chunks,test_rag_index}.py` — suite nueva (43 tests).

Diff completo del task: `git diff ef5cd79..HEAD`.

</details>
