# Revisión de diseño — Rediseño del indexado RAG (visualization-service)

**Documento revisado:** `.agents/tasks/rag-chunking-indexado/design.md` (Iteración 2)
**Alcance de la revisión:** ambigüedad, huecos, supuestos no verificados y choques entre secciones
que bloquearían la implementación. Esta es una revisión en frío del documento contra el código y
los datos reales que referencia. No se re-ejecutaron builds ni suites.

**Veredicto:** CHANGES_REQUESTED (2 MEDIUM, 3 NIT).

---

## Supuestos verificados (leídos en código/datos reales)

1. **`extraer_texto` produce texto pobre.** Confirmado en `sources.py`: concatena
   `title+objective+dimensions_explored+(text+options)` y **nunca** mira `respondents`. En el JSON
   real `title="enc_01_respondido.csv"`, `objective=""`, `dimensions_explored=[]`,
   `dublin_core={}`, `survey_specific={}` → texto crudo. (`storage/raw/114c9cc8…__inst_1.estandarizado.v1.json`.)
2. **Mojibake solo en el JSON.** `"Organizaci├│n_y__item1"`, `"Motivaci├│n_item1"` en el JSON;
   el `.txt` (`beb6e02b…__enc_01_original.txt`) está en UTF-8 limpio. Verificado leyendo ambos.
3. **Colisión de prefijo truncado.** `"Habilidades_par_item1..3"` aparece **dos veces** (q20–q22 y
   q31–q33), con numeración `item1..3` reiniciada en cada grupo. Confirmado por grep sobre el JSON.
4. **21 ítems likert `q13..q33` en una sola sección `s1` ("Reactivos del módulo"), en orden**,
   precedidos de q1–q12 no-likert. El `.txt` tiene 21 ítems en 6 secciones en el mismo orden
   (7+3+3+2+3+3). Correspondencia posicional 1-a-1 confirmada.
5. **Título legible solo en el `.txt`.** Cabecera `INSTRUMENTO: Inventario de Estrategias de
   Aprendizaje y Estudio (IEAE)`. `dc:title` vacío, `instrument.title` = nombre del CSV. Confirmado.
6. **`instrument_id = f"upload_{id_crudo}"`.** Confirmado en `domain_builder.py`. Luego
   `removeprefix("upload_")`→`int` es correcto para derivar `id_crudo`.
7. **La ruta del original vive en `RawData.raw_archivo_original`, no en `InstrumentoProcesado`.**
   Confirmado en `shared/models/raw_data.py` y `upload_service.py` (se setea solo si se subió
   original; si no, `None`). La consulta `select(RawData.raw_archivo_original).where(id_crudo==…)`
   es correcta y distinta de `_resolver_desde_bd`.
8. **storage-service NO devuelve el texto del `.txt`.** `obtener_artefacto` solo rellena
   `contenido` para `tipo in ("metadata","analysis")`; `raw` devuelve `contenido=None`.
   El descarte de la opción (i) en §5.1 es correcto.
9. **Convención de ruta del upload.** `local_backend.guardar` persiste `ruta=f"raw/{unique_name}"`
   y `leer` resuelve bajo `settings.raw_path_abs.parent` (= `…/storage`). Confirmado. El `seed_demo.py`
   guarda otra convención (`storage/raw/…`). El fix F1 (probar ambas convenciones) es correcto.
10. **Stack instalado.** `requirements.txt` del visualization-service trae `numpy==1.26.4` y
    `sqlalchemy==2.0.25`. La agregación con numpy + stdlib no añade dependencias. Confirmado.
11. **El contrato HTTP y el chat no se tocan.** `rag.py` arma metadata
    `{instrumentoId,titulo,tipo,investigador,kpis,investigacionId,chunk_index}`; `_construir_fuentes`
    y `prompt.construir` solo leen esas claves. Añadir `clase_chunk`/`dimension` es aditivo y no
    rompe el filtro `where={"instrumentoId":{"$in":[...]}}`. Confirmado.
12. **Tipos de answer.** Binarias llegan como strings `"True"`/`"False"` (q11/q12), likert como
    enteros, numérica como float/int. Confirmado en el primer respondente y en `_coaccionar_valor`.
13. **`chunking.trocear` descarta fragmentos `< 40` chars (`MIN_LONGITUD`) y usa `VENTANA=800`.**
    Confirmado.

## Supuestos no verificados / incorrectos

- **Orden JSON-likert == orden `.txt` para instrumentos futuros (NO garantizado).** En
  `domain_builder.construir_tabular` el orden de `questions` sigue el orden de la lista `preguntas`
  (orden de columnas del CSV), no el del `.txt`. Coincide en inst_1 por construcción del dato, pero
  nada en el código fuerza esa coincidencia para otro instrumento. El diseño lo reconoce como riesgo
  (§11.2, §12) con el guard de conteo y el fallback por prefijo. Ver Hallazgo 1 por la laguna que el
  guard de conteo deja abierta.
- **`extraer_metadata` ya respeta la precedencia de título pedida (INCORRECTO).** El código actual
  antepone `instrument.title` (el nombre del CSV) a `dc:title`. El diseño asume que basta con añadir
  `titulo_override`, pero no reordena la precedencia interna. Ver Hallazgo 2.

---

## Hallazgos

### 1. MEDIUM — El guard de conteo del mapeo posicional no detecta reordenamientos; falta criterio de validación semántica mínima
**Dónde:** §5.4 método 1; condición `len(plano) == len(questions_likert)`; §11.2, §12.

El único criterio de aplicabilidad del mapeo posicional es la **igualdad de conteo** entre ítems del
`.txt` y preguntas likert del JSON. Verifiqué en `domain_builder.construir_tabular` que el orden de
las preguntas sigue el orden de columnas del CSV, no el del `.txt`. Para inst_1 coinciden, pero un
instrumento con **el mismo número de ítems en distinto orden** pasaría el guard y produciría un
mapeo `question_id→dimensión` **silenciosamente incorrecto** (ítems asignados a la dimensión
equivocada), que es justo el tipo de error que degrada la calidad del RAG sin avisar. El diseño trata
esto como "riesgo aceptado + log del método usado", pero el log no distingue un mapeo correcto de uno
incorrecto: ambos reportan "posicional".

**Fix concreto (elegir uno y especificarlo en §5.4):**
- (a) Añadir una **comprobación de consistencia barata**: para cada par `(pregunta_likert, item_txt)`
  del `zip`, comparar el número de ítem embebido en el nombre de columna normalizado
  (`…_item{n}`) contra la posición dentro de su sección en el `.txt`; si el % de desajustes supera un
  umbral (p.ej. >0), **degradar a prefijo** y loguear `WARNING "orden .txt↔JSON inconsistente"`. O
- (b) Documentar explícitamente que el mapeo posicional **asume orden idéntico** y que el único
  escenario soportado es el actual (una sección `s1`, likert contiguos); dejar por escrito que un
  reordenamiento se acepta como mapeo potencialmente erróneo y **no** se detecta. Si se elige (b),
  dejarlo como invariante documentada en §9 y en §11.2 para que el coder no asuma robustez que no hay.

Sin una de las dos, el implementador no sabe si debe programar la verificación o no: es ambiguo.

### 2. MEDIUM — La precedencia de título no es implementable solo añadiendo `titulo_override`; `extraer_metadata` antepone hoy `instrument.title`
**Dónde:** §6.1 y §6.2 (precedencia `dc:title → .txt → instrument.title`); §7 (`extraer_metadata`
"gana un parámetro opcional `titulo_override`, retrocompatible").

Leí `sources.extraer_metadata`: hoy calcula
`titulo = _texto(instrument.title) or _texto(dc:title) or f"Instrumento {id}"`.
Es decir, `instrument.title` (= `"enc_01_respondido.csv"`) tiene **prioridad sobre `dc:title`**, al
revés de lo que pide §6.1 (`dc:title` primero). Añadir un `titulo_override` opcional **no basta**: si
el override se aplica como "úsalo solo cuando los demás faltan", el CSV seguiría ganando; y si se
aplica como "si viene, manda", entonces no implementa la precedencia de tres niveles pedida
(`dc:title → .txt → instrument.title`), sino solo dos. Además, la precedencia de §6.1 contradice el
orden actual del código, y el diseño no dice que haya que **reescribir** la lógica interna de
precedencia, solo que se "extiende de forma mínima". Eso es un hueco que lleva a dos
implementaciones divergentes entre el chunk de cabecera (§6.1) y la metadata de Chroma (§6.2).

**Fix concreto:** especificar en §6.2/§7 la **nueva** precedencia interna exacta de `extraer_metadata`
y escribirla como fórmula, p.ej.:
```python
titulo = (
    _texto(dublin_core.get("dc:title"))
    or _texto(titulo_override)            # viene del .txt (titulo_instrumento)
    or _texto(instrumento.get("title"))
    or f"Instrumento {instrumento_id}"
)
```
y decir explícitamente que **se reordena** la precedencia actual (hoy `instrument.title` va primero).
Confirmar que ese mismo orden se usa en el chunk de cabecera (§6.1) para que ambos coincidan.

### 3. NIT — `construir_chunks(artefacto, instrumento_id)` recibe `instrumento_id`, pero el acceso al `.txt` lo necesita como `id_crudo`; la responsabilidad de derivarlo no está asignada
**Dónde:** §3.3 / §6.1 / §7 (`construir_chunks(artefacto, instrumento_id) -> list[ChunkIndexable]`),
§5.1 (`ruta_original(instrumento_id)`), §8.

`rag.py` llama con el `instrumento_id` del parámetro HTTP (puede ser `"1"` o `"upload_1"`). §5.1
hace `id_crudo = int(str(instrumento_id).removeprefix("upload_"))` dentro de `ruta_original`. Pero
`construir_chunks` también podría tomar el `instrument_id` del **artefacto** (`"upload_1"`). El diseño
pasa `instrumento_id` (el del router) a ambos y es coherente, pero no dice **cuál** de los dos se usa
cuando difieren (p.ej. router manda `"1"`, JSON trae `"upload_7"` por un desajuste de datos). No
bloquea la implementación del caso normal, pero conviene fijarlo.

**Fix concreto:** en §5.1/§7 fijar que la fuente de verdad para derivar `id_crudo` es el
**parámetro del router** (`instrumento_id`), y que `artefacto["instrument_id"]` solo se usa para
degradación por nombre si el router no parsea. Una frase basta.

### 4. NIT — Chunks de estructura cortos pueden quedar por debajo de `MIN_LONGITUD`, pero §6.4 solo filtra al re-trocear
**Dónde:** §6.4 (bucle de aplanado) y `chunking.MIN_LONGITUD = 40`.

En §6.4, cuando `len(ch.texto) <= VENTANA` el texto se indexa **tal cual** (`[ch.texto]`), sin pasar
por el filtro de 40 chars de `trocear`. Un chunk de cabecera o de dimensión degradada muy corto
(p.ej. una dimensión con un solo ítem de nombre breve) se indexaría aunque sea casi vacío. No es un
fallo (texto corto citable no rompe nada), pero diverge del comportamiento actual, que descarta
`<40`. Vale la pena decidirlo a propósito.

**Fix concreto:** añadir en §6.4 una línea: descartar `piezas` cuyo `texto.strip()` tenga longitud
`< chunking.MIN_LONGITUD` **después** de aplanar (o justificar por qué se conservan). Esto también
garantiza que `documents`/`ids`/`metadatas` nunca lleven entradas vacías.

### 5. NIT — El resumen global (`redactar_resumen_global`) no tiene reglas de selección especificadas cuando faltan likert o numéricas
**Dónde:** §4.2 ("2–3 hallazgos más salientes: dimensión likert con media más alta y más baja,
numérica destacada") y §4.1 firma `redactar_resumen_global(hallazgos, n_respondentes, titulo)`.

La regla asume que existen dimensiones likert y al menos una numérica. En un instrumento sin likert
(p.ej. solo demográficas/numéricas) o sin numéricas, "la numérica destacada" / "media más alta y más
baja" no están definidas. §4.4 cubre `n==0` por dimensión, pero no el caso de **listas de hallazgos
sin cierto tipo**. Es un hueco menor de especificación.

**Fix concreto:** en §4.2 añadir: "si no hay dimensiones likert, el resumen omite las cláusulas de
media alta/baja; si no hay numéricas, omite la numérica destacada; si `hallazgos` está vacío, el
resumen global solo reporta `n` y la lista (vacía) de dimensiones evaluadas, sin inventar cifras."

---

## Resumen de severidades
- HIGH: 0
- MEDIUM: 2 (Hallazgos 1, 2)
- NIT: 3 (Hallazgos 3, 4, 5)

Como hay 2 hallazgos MEDIUM, el veredicto es **CHANGES_REQUESTED**.

Las preguntas directas del encargo se responden así tras verificar el código:
- **Acceso al `.txt`:** especificado y correcto (BD→`RawData.raw_archivo_original`, dos
  convenciones de ruta, fallback por disco). ✔
- **Mapeo `question_id→dimensión`:** robusto para el caso real (posicional, resuelve la colisión),
  pero el guard de conteo deja una laguna para reordenamientos del mismo tamaño (Hallazgo 1).
- **Firmas del módulo de agregación:** concretas y tipadas (§4.1), con `_num` definido. ✔
- **Forma/metadata de los chunks:** preserva `{instrumentoId,titulo,tipo}` y es aditiva; no rompe
  `/rag/index` ni `/rag/chat`. ✔ — salvo que el `titulo` real depende de arreglar la precedencia
  (Hallazgo 2).
- **Degradación grácil (original ausente / respondents ausentes):** definida y exhaustiva (§6.5). ✔
- **Agregación con solo lo instalado:** sí, numpy 1.26.4 + stdlib. ✔
