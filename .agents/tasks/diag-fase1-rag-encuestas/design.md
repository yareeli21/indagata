# Diseño técnico — FASE 1: Diagnóstico pedagógico del RAG para encuestas Likert (visualization-service)

> **Iteración 2** — revisión `design-review.json` (CHANGES_REQUESTED: 2 HIGH, 4 MEDIUM, 4 NIT)
> incorporada. Las respuestas puntuales a los 10 hallazgos están en §15; los cambios de fondo
> están integrados en el cuerpo (sobre todo §4.2–§4.4, §5.1, §5.4, §6.3, §6.5, §6.7). Resumen de
> los cierres: (F1) una sola API `escala_efectiva(lista_plana)`, sin `_escala_instrumento`; (F2)
> el prompt acota la comparación a lo presente en el CONTEXTO y se apoya en los chunks
> interpretados; (F3) cortes por tercios `1/3,2/3` fijados sin alternativa pendiente; (F4) se
> documenta que la prosa estadística heredada sigue en "/5" y "4 o 5"; (F5) invariante de escala
> homogénea declarado y, por robustez, `escala_efectiva` toma min/max sobre todos los ítems; (F6)
> el puntaje global se define y justifica como **media de las medias por dimensión**
> (equiponderado).

> **Alcance de esta fase (SOLO encuestas Likert).** Mejora la *calidad interpretativa* del RAG ya
> existente del `visualization-service`, sin rehacer lo ya implementado y verificado. Hoy ya
> funciona: resolución del artefacto (`sources.resolver_artefacto`), parseo del `.txt` original y
> mapeo `question_id → dimensión` (`original_txt.py`), chunks de **estructura** y de **hallazgos
> estadísticos por dimensión** (media, DE, % extremo alto, ítem más alto/bajo, n), el contrato HTTP
> de `/rag/index` y `/rag/chat`, y el fix de Ollama `keep_alive='-1m'`. El diseño de base está en
> `.agents/tasks/rag-chunking-indexado/design.md` y se respeta íntegro.
>
> Esta fase añade exactamente **3 mejoras**, todas condicionadas a instrumentos Likert:
> 1. **Prompt de diagnóstico** (`app/core/prompt.py`): permitir que el LLM *interprete* en vez de
>    limitarse a repetir el contexto.
> 2. **Chunks de hallazgos interpretados** (`app/core/agregacion.py` + orquestación en
>    `sources.construir_chunks`): clasificar el nivel de cada dimensión y compararlas entre sí
>    **dentro de un mismo chunk**.
> 3. **Chunks de grupo por desempeño** (`app/core/agregacion.py` + orquestación): agrupar
>    respondentes por su puntaje global Likert (bajo/medio/alto) y describir cada grupo.

## 1. Resumen y objetivo

El chat RAG ya recupera fuentes y ya responde con el modelo (tras el fix de `keep_alive`). Pero el
*core* del producto —que los datos de los instrumentos se aprovechen y el modelo ayude a
**interpretarlos** como diagnóstico pedagógico— todavía no se cumple por dos causas:

1. **El prompt prohíbe interpretar.** `prompt._INSTRUCCION` dice *"responde USANDO ÚNICAMENTE la
   información del CONTEXTO… si el contexto no contiene la respuesta, dilo y no inventes"*. Con un
   LLM pequeño (`llama3.2:3b`), esa instrucción se lee como "no razones, no concluyas": ante
   "¿cuáles son las fortalezas y debilidades?", el modelo responde que no tiene información
   suficiente, aunque los chunks traen todas las medias necesarias para concluirlo.
2. **Los chunks de hallazgos son descriptivos, no interpretativos.** Hoy un chunk de dimensión dice
   *"media 4.1/5, DE 0.8, 72 % respondió 4 o 5…"*. Son cifras correctas, pero no clasifican el
   nivel (¿4.1 es alto?) ni comparan dimensiones (¿cuál es la más débil?). El LLM pequeño no
   siempre hace ese salto por sí solo; conviene que el *propio texto indexado* ya traiga la
   interpretación derivada de las respuestas, para que el modelo tenga de dónde fundamentarla.

El objetivo de la Fase 1 es cerrar esa brecha para **encuestas Likert**: reescribir el prompt para
habilitar interpretación pedagógica fundamentada (sin inventar cifras) y enriquecer el espacio de
chunks con (a) interpretación por dimensión y (b) grupos de desempeño derivados exclusivamente de
las respuestas Likert. Todo en español, sin tocar el contrato HTTP ni añadir dependencias.

### 1.1 Stack fijado (no cambia)

Python 3, FastAPI, `numpy` ya presente (`np.mean`/`np.std` bastan; **no se usa ninguna API nueva de
numpy** ni se añade dependencia), stdlib (`collections`). SQLAlchemy 2.0 ya presente (no se toca en
esta fase). El LLM sigue siendo Ollama `llama3.2:3b` vía `ollama_client.py` (no se toca). Chroma vía
`chroma_client.py` (no se toca).

## 2. Causa raíz confirmada (leyendo el código real)

He leído los módulos reales (`prompt.py`, `agregacion.py`, `sources.py`, `original_txt.py`,
`rag.py`, `chunking.py`) y el artefacto real
`storage/raw/114c9cc8b19a46cf8ad0719099771bd1__inst_1.estandarizado.v1.json` (`instrument_id =
"upload_1"`). Existen **cuatro** artefactos `*__inst_1.estandarizado.v1.json` con hashes distintos
(`d8bc4a50…`, `8c966921…`, `4fde827e…`, `114c9cc8…`); el test de integración (§10) fija el
`114c9cc8…` para ser reproducible (NIT #7). Confirmo:

- **`prompt._INSTRUCCION`** es la causa 1. Texto literal actual:
  *"Eres un asistente de investigación educativa. Responde en español, de forma clara y concisa,
  USANDO ÚNICAMENTE la información del CONTEXTO. Si el contexto no contiene la respuesta, dilo
  explícitamente y no inventes datos."* `construir(pregunta, chunks)` arma `[Fuente i — titulo
  (tipo, investigador)]` + fragmento por cada chunk, luego `CONTEXTO/PREGUNTA/RESPUESTA`. El router
  (`rag.py`) llama `prompt.construir(peticion.pregunta, contexto)` donde `contexto` es
  `[FuenteChatOut.model_dump()]` (dicts con `fragmento/titulo/tipo/investigador/kpis`). **Ese
  contrato de `construir` no puede cambiar de forma** (ni la firma, ni el bloque de fuentes
  numeradas que el frontend espera reproducir).

  **Dato crítico verificado (ligado al fix F2):** `rag._construir_fuentes` **deduplica por
  `instrumentoId`** (`if instrumento_id in vistos: continue; vistos.add(...)`) y conserva solo el
  **chunk más cercano por instrumento**. Es decir, el chat suele ver **un único fragmento por
  instrumento** en el prompt. Esto condiciona qué puede pedírsele al LLM sobre "comparar" (ver §4.4).

- **`agregacion.py`** ya produce `HallazgoDimension` por dimensión Likert con `media/de/pct_alto/
  item_mas_alto/item_mas_bajo/n`, y ya tiene **`_num`** (coacción robusta) y **`_escala_efectiva`**
  (rango real de la escala, cae a 1..5). Son exactamente las piezas que esta fase debe REUSAR, no
  reinventar. `redactar_hallazgo` y `redactar_resumen_global` producen la prosa descriptiva actual.
  Verificado: `_escala_efectiva(items)` lee **solo `items[0][2]` / `items[0][3]`** (la escala del
  primer ítem). Y `_redactar_likert` **hardcodea** el texto "/5" y "respondió 4 o 5" (ligado a F4).

- **`sources.construir_chunks`** ya orquesta: construye `questions_likert = [q … if type ==
  "likert"]`, el `mapa` (posicional o por prefijo), agrupa Likert en
  `items_por_dim: dict[dim] -> list[(qid, texto, smin, smax)]` y por cada dimensión llama
  `agregar_likert` + `redactar_hallazgo` → `ChunkIndexable(clase="hallazgos", dimension=dim)`. Es el
  punto de integración natural para los chunks nuevos. **Verificado (invariante central del
  encargo):** `items_por_dim` se llena **solo** desde `questions_likert`, de modo que `perfil` (q2,
  `opcion_multiple`) **nunca** entra ahí (ver §6.1).

- **`rag.py` → `_aplanar_piezas`** propaga `{clase_chunk, dimension}` como metadata aditiva y numera
  `id`/`chunk_index` sobre la lista aplanada. **Cualquier `clase` nueva viaja sola**: basta con que
  los nuevos `ChunkIndexable` traigan su `clase` y `dimension`; no hay que tocar `rag.py`.
  `FuenteChatOut` **no** incluye `clase_chunk`/`dimension` y `_construir_fuentes` los ignora, así que
  el valor nuevo `clase_chunk="grupo_desempeno"` no rompe el contrato HTTP.

- **Datos reales confirmados (inst_1):** `respondents[]` = `{respondent_id, demographics{…},
  answers{q<id>: valor}}`. Los ítems Likert son `q13..q33` (enteros 1..5, `scale_min:1/scale_max:5`).
  Y **crítico para la mejora 3**: existe `q2 = "perfil"` (`opcion_multiple`, opciones `P1..P8`) y
  variables demográficas (`q6 promedio_gpa`, `q7 horas_trabajo_semana`, `q8 tipo_universidad`,
  `q11 primera_generacion`, etc.). El campo `perfil` es justo la etiqueta externa que la Fase 1
  **NUNCA** debe usar para agrupar: no existe en encuestas reales. La agrupación se hará solo con los
  ítems Likert.

### 2.1 Qué id alimenta el mapeo (aclaración NIT #10)

`construir_chunks` deriva el id para el mapeo del `.txt` con `_id_crudo_param(instrumento_id,
artefacto)`: usa **el parámetro `instrumentoId` del router** (vía `int(str(id).removeprefix(
"upload_"))`) y solo si no parsea cae a `artefacto["instrument_id"]`. En el ejemplo, el JSON trae
`instrument_id="upload_1"` pero el que gobierna la resolución del `.txt` es el `instrumentoId` del
request. Ninguna de las 3 mejoras de esta fase altera esa ruta (ya implementada y verificada).

## 3. Decisiones de arquitectura (Fase 1)

**D1 — Toda la mejora de chunks vive en `agregacion.py` (puro, sin I/O) y se orquesta desde
`sources.construir_chunks`.** `agregacion.py` ya es el dueño del invariante "nunca un chunk por
respondente" y de la estadística; añadir allí la interpretación y la agrupación mantiene la lógica
densa aislada del I/O y **unit-testeable sin BD/disco/Chroma**. `sources` solo decide *cuándo* se
emiten los chunks nuevos; `rag.py` **no se toca**.

**D2 — Los umbrales de clasificación son paramétricos y relativos al rango real de la escala,
reusando `_escala_efectiva`.** No se hardcodea 1..5. El mismo criterio sirve para la mejora 2 (nivel
por dimensión) y la mejora 3 (grupo por puntaje global), con una **única** función de corte
compartida (`_clasificar_nivel`) y un **único** punto de obtención del rango de escala
(`escala_efectiva`, §5.4). Esto garantiza coherencia y justificabilidad en tesis.

**D3 — Degradación grácil y "solo Likert".** Si el instrumento no tiene preguntas `type ==
"likert"`, los chunks nuevos **no se generan** (los demás tipos de instrumento siguen igual). Si
Likert existe pero una dimensión/grupo queda vacío (`n == 0`), ese chunk no se emite (nunca `nan`).
Cada bloque va en su propio `try/except` con `logger.warning`, igual que el estilo ya presente.

### 3.1 ¿Chunk interpretado separado o ampliar el chunk estadístico? → Separado

Dos opciones para la mejora 2:
- **(A)** Añadir las frases interpretativas al final del chunk estadístico actual (misma
  `dimension`, misma `clase="hallazgos"`).
- **(B)** Emitir un chunk **adicional** por dimensión con `clase="hallazgos"` cuyo texto es
  puramente interpretativo y autosuficiente.

**Se elige (B).** Razón: en recuperación vectorial, una pregunta como *"¿cuál es la mayor
debilidad?"* casa mejor con un chunk corto y enfocado en la interpretación ("nivel bajo / área de
mejora prioritaria") que con un chunk mixto largo donde la interpretación queda diluida entre cifras.
Mantenerlos separados también deja el chunk estadístico actual intacto (cero regresión) y hace el
cambio puramente **aditivo**. Hay un beneficio adicional ligado a F2: como `_construir_fuentes`
deduplica a **un fragmento por instrumento**, un chunk interpretado que **ya internaliza la
comparación** (dimensión más fuerte, más débil y brecha dentro del mismo texto) es el mecanismo real
que habilita "comparar dimensiones" en el chat sin depender de que el top_k reúna varias dimensiones
del mismo instrumento (ver §4.4 y §5.3).

> Nota de metadata: el chunk interpretado **reutiliza `clase_chunk="hallazgos"`** (no estrena valor)
> y se distingue del estadístico por su contenido. Los chunks de grupo sí estrenan
> `clase_chunk="grupo_desempeno"` (valor nuevo permitido por el encargo). Ver §6.2.

## 4. Mejora 1 — Prompt de diagnóstico (`app/core/prompt.py`)

### 4.1 Qué cambia y qué NO

- **Cambia:** solo la constante `_INSTRUCCION`. Pasa de "repite el contexto / no concluyas" a
  "analiza e interpreta como diagnóstico pedagógico, pero las CIFRAS salen del contexto y la
  comparación se ciñe a lo presente".
- **NO cambia:** la firma `construir(pregunta, chunks) -> str`, el formato de fuentes numeradas
  (`[Fuente i — titulo (tipo, investigador)]` + fragmento), ni el orden `CONTEXTO/PREGUNTA/
  RESPUESTA`. El contrato con `rag.py` y el frontend queda intacto.

### 4.2 Texto propuesto de `_INSTRUCCION` (español)

```python
_INSTRUCCION = (
    "Eres un asistente de investigación educativa que elabora DIAGNÓSTICOS\n"
    "PEDAGÓGICOS a partir de datos de instrumentos. Responde SIEMPRE en español,\n"
    "de forma clara y estructurada.\n"
    "\n"
    "Tu tarea es ANALIZAR E INTERPRETAR la información del CONTEXTO: identifica\n"
    "fortalezas y debilidades, señala patrones y explica sus implicaciones\n"
    "educativas (qué conviene reforzar y por qué). No te limites a repetir las\n"
    "cifras: razona su significado.\n"
    "\n"
    "ALCANCE DE LA COMPARACIÓN: compara dimensiones o grupos ENTRE SÍ solo si\n"
    "ambos aparecen en el CONTEXTO. Si el CONTEXTO trae una sola dimensión o un\n"
    "solo grupo, interprétalo por sí mismo SIN compararlo con otros que no estén\n"
    "presentes. Si un fragmento ya indica cuál es la dimensión más fuerte o más\n"
    "débil, puedes apoyarte en esa afirmación del propio contexto.\n"
    "\n"
    "REGLA ESTRICTA SOBRE LOS DATOS: las CIFRAS (medias, porcentajes, número de\n"
    "respondentes, nombres de dimensiones o ítems) deben provenir EXCLUSIVAMENTE\n"
    "del CONTEXTO. No inventes números, dimensiones, ítems ni resultados que no\n"
    "estén en el contexto. Si el contexto no contiene un dato concreto que se te\n"
    "pide, dilo explícitamente («el contexto no incluye ese dato») en lugar de\n"
    "inventarlo. Puedes y debes interpretar y concluir A PARTIR DE las cifras que\n"
    "sí están presentes."
)
```

### 4.3 Justificación del diseño del prompt

- **Separa dos permisos distintos** que el prompt viejo confundía: (i) *interpretar/concluir* está
  **permitido y obligatorio**; (ii) *inventar cifras o datos ausentes* está **prohibido**. El prompt
  viejo prohibía ambos a la vez ("únicamente con el contexto"), lo que bloqueaba la interpretación.
  El nuevo mantiene la defensa anti-alucinación sobre los *datos* y libera el *razonamiento*.
- **Es concreto sobre qué significa "interpretar"** (fortalezas, debilidades, patrones,
  implicaciones), porque `llama3.2:3b` necesita instrucciones explícitas.
- **Acota la comparación** (párrafo "ALCANCE DE LA COMPARACIÓN"): es la red que evita que el modelo
  invente cifras de otras dimensiones cuando el contexto trae una sola. La comparación fiable la
  aportan los chunks interpretados de §5 (que ya traen la más fuerte / más débil / brecha dentro de
  un mismo fragmento), no el prompt confiando en que varias dimensiones coincidan en el top_k.
- **Mantiene la cláusula de "si falta el dato, dilo"** como salvaguarda ante preguntas cuyo dato no
  está indexado.
- **No añade formato rígido** (listas/encabezados obligatorios) para no romper el stream SSE token a
  token ni la expectativa del frontend.

### 4.4 Edge cases del prompt (corrige la afirmación previa sobre comparar)

- **Un solo fragmento por instrumento (lo habitual).** Verificado: `_construir_fuentes` deduplica por
  `instrumentoId` y entrega el chunk más cercano por instrumento. Por eso el prompt **no asume** que
  el contexto contenga varias dimensiones del mismo instrumento; la cláusula de alcance obliga a
  interpretar lo presente sin comparar contra lo ausente. La capacidad de "comparar dimensiones"
  descansa en los **chunks interpretados** (§5.3), que internalizan la comparación en un solo
  fragmento recuperable.
- **Contexto vacío** (0 fuentes recuperadas): el bloque `CONTEXTO:` queda vacío; el modelo debe
  declarar la carencia (cláusula explícita). No se cambia `rag.py`.
- **Pregunta no diagnóstica** (p.ej. "¿quién es el investigador?"): el formato de fuentes ya trae
  `titulo/tipo/investigador`, así que el modelo responde de la metadata sin inventar.
- **Mezcla de instrumentos** en el contexto: puede haber un fragmento por cada instrumento
  recuperado; el modelo puede referirse a cada uno, pero solo compara dimensiones/grupos **si ambos
  aparecen** (cláusula de alcance). No es un riesgo de alucinación mientras las cifras salgan de los
  chunks.

## 5. Mejora 2 — Chunks de hallazgos interpretados por dimensión (`agregacion.py`)

Para cada dimensión Likert, **además** del chunk estadístico actual, se emite un chunk interpretativo
derivado de las propias respuestas: su **nivel** (clasificado por la media sobre el rango real de la
escala) y su posición **relativa** frente a las demás dimensiones del instrumento (la más fuerte, la
más débil, la brecha), **todo dentro del mismo chunk** (clave para F2).

### 5.1 Cortes paramétricos y su justificación (D2) — DECISIÓN ÚNICA: tercios

Se define **una sola** función de clasificación, reutilizada por mejoras 2 y 3. Los cortes se
expresan como **fracciones fijas del rango efectivo** `[scale_min, scale_max]` (obtenido con
`escala_efectiva`, §5.4), **no** como valores absolutos 1..5. **Se fija definitivamente tercios
`1/3` y `2/3`** (sin alternativa pendiente; cierra F3/MEDIUM#3):

```python
# Cortes paramétricos (§5.1). DECISIÓN FIJA: tercios del rango efectivo.
#   bajo    : media <  scale_min + 1/3*(scale_max - scale_min)
#   moderado: entre  1/3 y 2/3 del rango
#   alto    : media >= scale_min + 2/3*(scale_max - scale_min)
# Para la escala por defecto 1..5 esto da exactamente:
#   bajo    : media <  2.333   (≈ "< 2.5" del encargo: área de mejora prioritaria)
#   moderado: 2.333 .. 3.667   (nivel moderado)
#   alto    : media >= 3.667   (≈ "> 3.5" del encargo: fortaleza)
# Se eligen tercios (y NO 0.375/0.625) por simetría, independencia de la escala
# y por partir el continuo en tres zonas iguales sin supuestos de distribución
# ni normas poblacionales externas (que no existen en datos reales).
_FRAC_BAJO: float = 1.0 / 3.0
_FRAC_ALTO: float = 2.0 / 3.0
```

**Justificación (defendible en tesis):**
- **Por tercios del rango**: criterio simple, simétrico y explicable; parte la escala en tres zonas
  iguales (bajo/medio/alto) sin supuestos de distribución.
- **Relativo al rango real** (no a 1..5 fijo): un instrumento puede declarar `scale_min/scale_max`
  distintos (0..4, 1..7); los tercios se recalculan y la interpretación sigue coherente. Reusar el
  rango de `escala_efectiva` garantiza el mismo rango que `agregar_likert` usa para `pct_alto`
  (consistencia interna del índice).
- **Equivalencia con el enunciado del encargo**: el encargo sugiere "sobre 1..5: < 2.5 bajo, 2.5–3.5
  moderado, > 3.5 alto". Los tercios dan 2.33 y 3.67, muy cercanos, con la ventaja de ser
  paramétricos en vez de hardcodeados. **No se deja ninguna constante "a decidir"**; esta es la
  decisión final del diseño.

```python
# Vocabulario de nivel por DIMENSIÓN (mejora 2). Un único mapa fuente de verdad.
_ETIQUETA_NIVEL = {
    "bajo": "nivel bajo (área de mejora prioritaria)",
    "moderado": "nivel moderado",
    "alto": "nivel alto (fortaleza)",
}
# Renombrado único clave->etiqueta de GRUPO (mejora 3). Centralizado (NIT #9).
_ETIQUETA_GRUPO = {"bajo": "bajo", "moderado": "medio", "alto": "alto"}

def _clasificar_nivel(media: float, scale_min: float, scale_max: float) -> str:
    """Clasifica una media en 'bajo'|'moderado'|'alto' por tercios del rango
    efectivo. Compartida por las mejoras 2 y 3 (cortes paramétricos, §5.1)."""
    rango = scale_max - scale_min
    if rango <= 0:            # defensa: escala inválida -> se asume 1..5
        scale_min, scale_max, rango = 1.0, 5.0, 4.0
    corte_bajo = scale_min + _FRAC_BAJO * rango
    corte_alto = scale_min + _FRAC_ALTO * rango
    if media < corte_bajo:
        return "bajo"
    if media >= corte_alto:
        return "alto"
    return "moderado"
```

El renombrado "moderado→medio" vive **solo** en `_ETIQUETA_GRUPO` y se aplica únicamente al construir
`HallazgoGrupo.grupo` (§6.3 paso 4). Un test (§10) verifica que nunca se cuele "moderado" en un chunk
de grupo ni "medio" en uno de dimensión (NIT #9).

### 5.2 Firma nueva en `agregacion.py`

La interpretación por dimensión necesita conocer **todas** las dimensiones Likert para comparar. Por
eso trabaja sobre la lista de `HallazgoDimension` Likert ya calculados (reutilizando lo que
`construir_chunks` ya produce), no sobre los respondentes de nuevo:

```python
def redactar_interpretacion_dimension(
    h: HallazgoDimension,
    todos_likert: list[HallazgoDimension],
    scale_min: float,
    scale_max: float,
) -> str | None:
    """Chunk interpretativo para una dimensión Likert (mejora 2).

    Devuelve None si `h` no es likert o no tiene media (no se emite chunk).
    `todos_likert` son todas las dimensiones likert del instrumento (para situar
    `h` como la más fuerte / más débil / respecto a la brecha).
    """
```

Es **pura** (recibe dataclasses, devuelve `str | None`). Se añade al `__all__` del módulo.

### 5.3 Contenido del chunk interpretado (texto de ejemplo)

Para "Motivación" (media 4.1/5) en un instrumento con varias dimensiones:

> **Interpretación de la dimensión Motivación.** Con una media de 4.1 sobre 5, esta dimensión se
> ubica en un nivel alto (fortaleza) según el rango de la escala. Es la dimensión mejor evaluada del
> instrumento. La dimensión más débil es Organización y Planificación (media 2.1, nivel bajo: área
> de mejora prioritaria), con una brecha de 2.0 puntos respecto a Motivación. Esto sugiere que el
> estudiantado muestra disposición e interés, pero requiere apoyo en hábitos de organización del
> estudio. n = 180 respondentes.

Reglas de redacción (todas condicionadas a que el campo exista; nunca se formatea `None`/`nan`):
1. **Nivel propio**: `f"Con una media de {media:.1f} sobre {scale_max:.0f}, la dimensión {dim} se
   ubica en {ETIQUETA_NIVEL[nivel]} según el rango de la escala."` (el "sobre N" asume `scale_min≈1`;
   ver NIT #8 en §5.5).
2. **Posición relativa** (solo si hay ≥2 dimensiones Likert con media): si `h` es la de media máxima
   → "Es la dimensión mejor evaluada del instrumento."; si es la mínima → "Es la dimensión con menor
   puntuación del instrumento."; en otro caso se omite.
3. **Comparación/brecha** (solo si hay ≥2 dimensiones Likert con media y `h` no es a la vez máx y
   mín): nombra la dimensión más fuerte y la más débil del instrumento y la **brecha**
   `abs(media_max - media_min)` con un decimal. **Esta cláusula es la que habilita "comparar" en el
   chat** aun con un solo fragmento recuperado (F2).
4. **Implicación educativa**: conclusión breve derivada del nivel. Bajo → "conviene priorizar el
   refuerzo de esta área."; moderado → "hay margen de mejora consolidando los aspectos más débiles.";
   alto → "constituye una base sobre la que apoyar otras áreas." Genérica y derivada del nivel
   calculado; no inventa causas.

La **última** frase repite `n` de la dimensión para que el chunk sea autosuficiente y citable:
`f"n = {h.n} respondentes."`

### 5.4 Obtención del rango de escala — API ÚNICA (fix F1 + invariante F5)

Hoy `agregacion._escala_efectiva(items)` es **privado** y lee **solo `items[0]`**. Para esta fase:

**(a) Se expone UNA sola función pública** que recibe **lista plana** de tuplas (nunca un dict), para
que `sources` no toque un símbolo privado y para eliminar cualquier segunda API (se **elimina** del
diseño el nombre `_escala_instrumento(items_por_dim)` del borrador previo, origen del HIGH F1):

```python
def escala_efectiva(items: list[tuple[str, str, int, int]]) -> tuple[float, float]:
    """Rango efectivo de la escala del instrumento. ÚNICO punto público (§5.4).

    Robustez (F5): toma scale_min = min de todos los items y scale_max = max de
    todos los items (no solo items[0]), para no sesgar la clasificación si el
    instrumento mezclara dimensiones con escalas distintas. Cae a 1..5 si la
    lista es vacía o el rango resultante es inválido (min >= max).
    """
    try:
        mins = [float(it[2]) for it in items]
        maxs = [float(it[3]) for it in items]
    except (TypeError, ValueError, IndexError):
        return 1.0, 5.0
    if not mins or not maxs:
        return 1.0, 5.0
    scale_min, scale_max = min(mins), max(maxs)
    if scale_min >= scale_max:
        return 1.0, 5.0
    return scale_min, scale_max
```

Nota: la estadística existente (`agregar_likert`) sigue usando internamente `_escala_efectiva(items)`
(solo primer ítem) sin cambios para no tocar lo verificado; la nueva `escala_efectiva` es la que usan
**sources** y las mejoras 2/3. Como el instrumento real es homogéneo (todos 1..5), ambos coinciden;
`escala_efectiva` es además robusta ante heterogeneidad (ver invariante abajo).

**(b) Invariante de escala homogénea (fix F5), declarado y con dueño.** Las mejoras 2 y 3 asumen que
todas las dimensiones Likert de un instrumento comparten escala. Dueño del invariante:
`escala_efectiva` (al reducir a min/max sobre todos los ítems, cualquier heterogeneidad produce un
rango *envolvente* en vez de un error silencioso). Documentado aquí y en §9/§13 (supuesto). En los
datos reales la escala es homogénea 1..5, así que el envolvente coincide con la escala real.

### 5.5 Integración en `sources.construir_chunks` (segundo pase, lista plana — fix F1)

En el bucle que hoy recorre `orden_dim` para emitir el chunk estadístico Likert, ya se acumulan los
`HallazgoDimension` en `hallazgos`. Tras ese bucle se añade un **segundo pase** que emite el chunk
interpretado por dimensión Likert con media. **El rango de escala se obtiene aplanando `items_por_dim`
a una lista y pasándola a `escala_efectiva` (nunca el dict):**

```python
# (B.2) Chunks de HALLAZGOS INTERPRETADOS por dimensión (mejora 2) — SOLO Likert.
hallazgos_likert = [h for h in hallazgos if h.tipo == "likert" and h.media is not None]
if hallazgos_likert:
    items_plano = [it for its in items_por_dim.values() for it in its]  # lista plana (F1)
    smin, smax = agregacion.escala_efectiva(items_plano)
    for h in hallazgos_likert:
        try:
            texto = agregacion.redactar_interpretacion_dimension(
                h, hallazgos_likert, smin, smax
            )
            if texto:
                chunks.append(
                    ChunkIndexable(texto=texto, clase="hallazgos", dimension=h.dimension)
                )
        except Exception as exc:  # noqa: BLE001 - degradación grácil
            logger.warning("Falló la interpretación de la dimensión %r: %s", h.dimension, exc)
```

Al pasar siempre **lista plana** a `escala_efectiva`, desaparece el `KeyError/TypeError` del HIGH F1
(que se habría tragado el `try/except`, anulando en silencio toda la mejora 2).

> **NIT #8 — "sobre N".** El texto dice "media X sobre {scale_max}". Para escalas que no empiezan en 1
> (p.ej. 0..4) "2.1 sobre 4" omite el mínimo; dado 1..5 confirmado es cosmético. Se **documenta** que
> "sobre N" asume `scale_min≈1`; si se quisiera precisión total para escalas raras, la frase incluiría
> el mínimo (`"media X en la escala {scale_min:.0f}..{scale_max:.0f}"`). Fuera de alcance por 1..5.

## 6. Mejora 3 — Chunks de grupo por desempeño (`agregacion.py`, `clase="grupo_desempeno"`)

### 6.1 Punto crítico de robustez (invariante duro)

La agrupación se basa **EXCLUSIVAMENTE en las respuestas Likert del propio instrumento**. Nunca en
`perfil` (q2, valores P1..P8) ni en ninguna etiqueta externa, porque esos campos **no existen en
datos reales**. Dueño del invariante: `agregacion.agrupar_por_desempeno`, por construcción —solo
recibe los `items` Likert y los `respondents`, y jamás lee la columna `perfil` ni demográficas para
decidir el grupo. `sources` tampoco le pasa `perfil` (verificado: `items_por_dim` se construye solo
desde `questions_likert`). Las variables de contexto (gpa, horas_trabajo, tipo_universidad,
primera_generacion…) son **opcionales**: podrían enriquecer el texto si están, pero el núcleo
funciona sin ellas y **no falla si faltan** (ver §6.6).

### 6.2 Metadata y clase nueva

Los chunks de grupo estrenan `clase_chunk="grupo_desempeno"` (valor nuevo permitido). `dimension` se
usa para el nombre del grupo: `"bajo"`, `"medio"` o `"alto"` (escalar, no rompe claves). El resto de
la metadata de Chroma (`instrumentoId, titulo, tipo, investigador, kpis, investigacionId,
chunk_index`) la escribe `rag.py` sin cambios. `_aplanar_piezas` ya propaga `clase`/`dimension` tal
cual, así que **`rag.py` no se toca**.

### 6.3 Algoritmo (Opción A — reglas simples y explicables)

```python
def agrupar_por_desempeno(
    items_likert: list[tuple[str, str, int, int]],   # (qid, texto, smin, smax) de TODAS las dims
    dims_por_qid: dict[str, str],                     # qid -> nombre de dimensión (para destacar)
    respondents: list[dict],
) -> list[HallazgoGrupo]:
    """Agrupa respondentes por su puntaje global Likert (bajo/medio/alto).

    Puntaje global de un respondente = MEDIA DE LAS MEDIAS POR DIMENSIÓN
    (equiponderado, §6.3). Devuelve un HallazgoGrupo por grupo NO vacío
    (típicamente 2-3). SOLO Likert; nunca lee 'perfil' ni demográficas.
    """
```

**Decisión metodológica del puntaje global (fix F6) — equiponderado por dimensión.** El borrador
previo definía el puntaje global como "media de TODAS las respuestas Likert", lo que **pondera cada
dimensión por su número de ítems** (en inst_1: Organización=7 vs Motivación=3), sesgo no declarado.
Se **cambia** a **media de las medias por dimensión**: cada dimensión pesa igual en la clasificación
del respondente. Justificación para tesis: el constructo de interés es el perfil del estudiante
*across dimensiones*; un diagnóstico que deje que una dimensión larga domine la etiqueta bajo/medio/
alto sería difícil de defender. Equiponderar por dimensión es la decisión consciente y documentada.

Pasos:
1. **Ids Likert por dimensión** desde `items_likert` + `dims_por_qid`. Si no hay ítems Likert ⇒
   `return []` (no Likert).
2. **Puntaje global por respondente (equiponderado):** para cada `r` y cada dimensión, calcular la
   media de los `_num(answers[qid])` válidos de esa dimensión (descartando `None`); una dimensión sin
   ningún valor válido en ese respondente **no cuenta**. El puntaje global del respondente = media de
   las medias por dimensión disponibles. Si el respondente no tiene ninguna dimensión con valor
   válido, **no se clasifica** (se excluye del total).
3. **Rango de escala** = `escala_efectiva(items_likert)` (mismos cortes del §5.1; lista plana, F1).
4. **Clasificar** cada respondente con `_clasificar_nivel(puntaje_r, smin, smax)` → `"bajo"|
   "moderado"|"alto"`. Para la etiqueta de salida del grupo se aplica el mapa único
   `_ETIQUETA_GRUPO` ("moderado"→"medio"); el resto queda igual (NIT #9).
5. **Por grupo** acumular: puntajes globales de sus miembros y, por **dimensión**, la media de ese
   respondente en la dimensión (para promediar luego la media del grupo por dimensión, también
   equiponderada entre respondentes).
6. **Por grupo NO vacío** construir `HallazgoGrupo` con: `grupo`, `n`, `pct = n/total*100` (`total` =
   respondentes clasificados), `puntaje_medio` (media de los puntajes globales del grupo), y
   `dim_altas`/`dim_bajas` = 1–2 dimensiones con mayor/menor media del grupo.
7. **Enriquecimiento con variables de contexto:** NO entra en el núcleo (§6.6). Backlogueado.

### 6.4 Dataclass nueva

```python
@dataclass(frozen=True)
class HallazgoGrupo:
    grupo: str                           # "bajo" | "medio" | "alto" (etiqueta de salida)
    n: int                               # respondentes en el grupo
    pct: float                           # % sobre el total de respondentes clasificados
    puntaje_medio: float                 # media de los puntajes globales del grupo
    dim_altas: list[tuple[str, float]]   # 1-2 dims con mayor media del grupo
    dim_bajas: list[tuple[str, float]]   # 1-2 dims con menor media del grupo
```

Se añade a `__all__` junto con `agrupar_por_desempeno` y `redactar_grupo`.

### 6.5 Redacción del chunk de grupo (texto de ejemplo)

```python
def redactar_grupo(g: HallazgoGrupo, scale_max: float) -> str: ...
```

Produce, para un grupo bajo:

> **Grupo de desempeño bajo (n = 32, 18 % del total).** Su puntaje global promedio fue 2.1 sobre 5.
> Mayor debilidad en Organización y Planificación (media 1.8) y en Habilidades para el examen (media
> 1.9); relativa fortaleza en Motivación (media 2.6). Este grupo concentra las necesidades de apoyo
> más urgentes del instrumento.

Reglas:
- Encabezado con `grupo`, `n`, `% = round(pct)`. Etiquetas en español: "bajo", "medio", "alto"
  (vienen ya mapeadas, §6.3 paso 4).
- Puntaje global promedio `f"{puntaje_medio:.1f} sobre {scale_max:.0f}"`. "sobre N" asume
  `scale_min≈1` (NIT #8, documentado; 1..5 confirmado).
- `dim_bajas` → "Mayor debilidad en {dim1} (media X.X)[ y en {dim2} (media Y.Y)]".
- `dim_altas` → "relativa fortaleza en {dim} (media Z.Z)". Si una dimensión aparecería a la vez en
  altas y bajas (grupo con 1 sola dimensión), se omite la cláusula redundante.
- Cierre interpretativo breve derivado del grupo (bajo = "necesidades de apoyo más urgentes"; medio =
  "desempeño intermedio con áreas por consolidar"; alto = "desempeño sólido y sostenido").
- Cada número con un decimal; porcentajes enteros. Nunca `nan` (si una media por dimensión no existe,
  se omite esa dimensión del listado).

### 6.6 Variables de contexto opcionales (no en el núcleo de Fase 1)

El encargo las marca OPCIONALES y advierte no depender de ellas. **Decisión:** la Fase 1 **no** las
incorpora al chunk de grupo, para no acoplar el núcleo a columnas ausentes en datos reales y para no
arriesgar PII en el texto indexado. Punto de extensión documentado: una fase posterior podría, si
existen, añadir una frase ("en este grupo el 70 % asiste a universidad pública") calculada aparte y
envuelta en su propio `try/except` que se omite si la columna falta. Backlogueado con razón explícita
(robustez + alcance de fase).

### 6.7 Integración en `sources.construir_chunks` (lista plana — fix F1)

Tras los chunks interpretados (§5.5), y solo si hay dimensiones Likert y respondentes:

```python
# (B.3) Chunks de GRUPO POR DESEMPEÑO (mejora 3) — SOLO Likert, nunca 'perfil'.
if hallazgos_likert and respondents:
    try:
        items_plano = [it for its in items_por_dim.values() for it in its]  # lista plana (F1)
        dims_por_qid = {it[0]: dim for dim, its in items_por_dim.items() for it in its}
        _smin, _smax = agregacion.escala_efectiva(items_plano)
        grupos = agregacion.agrupar_por_desempeno(items_plano, dims_por_qid, respondents)
        for g in grupos:
            chunks.append(
                ChunkIndexable(
                    texto=agregacion.redactar_grupo(g, _smax),
                    clase="grupo_desempeno",
                    dimension=g.grupo,
                )
            )
    except Exception as exc:  # noqa: BLE001 - degradación grácil
        logger.warning("Falló la agrupación por desempeño: %s", exc)
```

`items_por_dim` solo contiene dimensiones que entraron por el mapa Likert, así que `perfil`
(`opcion_multiple`, no `likert`) **nunca** llega aquí: garantizado por construcción (invariante §6.1).

## 7. Manejo de errores — concreto por operación

| Operación | Condición de fallo | ¿Recuperable? | Qué recibe el llamador | Log |
|---|---|---|---|---|
| `escala_efectiva` | lista vacía / tipos inválidos / `min>=max` | Recuperable | cae a `(1.0, 5.0)` | — |
| `redactar_interpretacion_dimension` | `h` no es likert / sin media | Recuperable | `None` ⇒ no se emite chunk | — |
| `redactar_interpretacion_dimension` | <2 dims likert | Recuperable | texto solo con nivel propio + implicación + n (omite comparación) | — |
| `redactar_interpretacion_dimension` | excepción inesperada | Recuperable | `try/except` en `sources` ⇒ se omite ese chunk, el resto sigue | `warning` |
| `agrupar_por_desempeno` | 0 ítems likert | Recuperable | `[]` ⇒ sin chunks de grupo (no Likert) | — |
| `agrupar_por_desempeno` | respondente sin Likert válido | Recuperable | se excluye del total; grupos siguen | — |
| `agrupar_por_desempeno` | todos los grupos vacíos / `total==0` | Recuperable | `[]` ⇒ sin chunks (nunca `nan`, nunca `/0`) | — |
| `agrupar_por_desempeno`/`redactar_grupo` | excepción inesperada | Recuperable | `try/except` en `sources` ⇒ se omite el bloque de grupos | `warning` |
| `_clasificar_nivel` | `rango <= 0` (escala inválida) | Recuperable | cae a 1..5 por defecto | — |
| `prompt.construir` | contexto vacío | Recuperable (deseado) | prompt válido; el modelo declara la carencia | — |

Ningún fallo de estas tres mejoras puede tumbar `/rag/index`: cada bloque nuevo en `construir_chunks`
va envuelto en su propio `try/except` con `logger.warning` y continuación. Si todo lo nuevo fallara,
se seguirían emitiendo los chunks de estructura y hallazgos estadísticos actuales (cero regresión).

## 8. Validación de entradas externas

| Entrada | Reglas | Comportamiento ante fallo |
|---|---|---|
| `answers[q]` (Likert) | `_num` (ya existente): excluye `bool`, acepta int/float y str con coma decimal | valor no numérico ⇒ descartado; no aborta |
| Puntaje global por respondente | requiere ≥1 dimensión con valor Likert válido | 0 dimensiones válidas ⇒ respondente excluido del total |
| `scale_min/scale_max` | opcionales; `escala_efectiva` toma min/max de todos los ítems; cae a 1..5 si faltan o `min>=max` | nunca divide por rango 0 (`_clasificar_nivel` defiende) |
| `respondents` | lista; vacía/ausente ⇒ sin chunks de hallazgos (ni interpretados ni de grupo) | ya cubierto por el `if not respondents: return chunks` existente |
| `type` de pregunta | solo `"likert"` entra a mejoras 2 y 3 | otros tipos ⇒ chunks nuevos no se generan (degradación "solo Likert") |
| `perfil` (q2) y demográficas | **prohibido** para agrupar; no se leen en el núcleo | invariante por construcción (§6.1) |
| `pregunta` del chat | la valida el schema `ChatRequest` (sin cambios) | — |

## 9. Invariantes y su dueño

- **"La agrupación nunca usa `perfil` ni etiquetas externas"** — dueño:
  `agregacion.agrupar_por_desempeno` (solo recibe ítems Likert) + `sources` (solo le pasa
  `items_por_dim`, que excluye no-Likert). Cerrado por construcción.
- **"Nunca un chunk por respondente"** — dueño: `agregacion`. `agrupar_por_desempeno` devuelve a lo
  sumo 3 `HallazgoGrupo`; nunca uno por respondente.
- **"Cortes de clasificación coherentes entre mejoras 2 y 3"** — dueño: `_clasificar_nivel` (función
  única compartida) + `_FRAC_BAJO/_FRAC_ALTO` (constantes únicas).
- **"Un único vocabulario por tipo de chunk"** — dueño: `_ETIQUETA_NIVEL` (dimensión) y
  `_ETIQUETA_GRUPO` (grupo, con el renombrado moderado→medio centralizado). Testeado (NIT #9).
- **"Escala homogénea por instrumento"** (fix F5) — dueño: `escala_efectiva` (reduce a min/max
  envolvente sobre todos los ítems; nunca falla por heterogeneidad). Documentado como supuesto §13.
- **"Solo Likert esta fase"** — dueño: `sources.construir_chunks` (filtra `type=="likert"` y
  condiciona los bloques nuevos a `hallazgos_likert`).
- **"Nunca `nan`/división por cero en el texto citable"** — dueño: `agregacion` (devuelve `None`/`[]`
  ante conjuntos vacíos; porcentajes solo con `total>0`).
- **"El contrato HTTP y las claves de metadata existentes no cambian"** — dueño: `rag.py` (intacto) +
  los nuevos `ChunkIndexable` que solo aportan valores escalares nuevos de `clase_chunk`/`dimension`.

## 10. Testabilidad

**Unit (sin I/O — el grueso del valor), en `agregacion.py`:**
- `escala_efectiva`: lista homogénea 1..5 ⇒ (1,5); lista con una tupla 0..4 y otra 1..5 ⇒ envolvente
  (0,5) sin error (F5); lista vacía / tipos inválidos / `min>=max` ⇒ (1,5).
- `_clasificar_nivel`: escala 1..5 → media 2.0 "bajo", 3.0 "moderado", 4.0 "alto"; límites exactos
  (2.333 ⇒ moderado, 3.667 ⇒ alto); escala 0..4 y 1..7 reclasifican; `rango<=0` cae a 1..5.
- `redactar_interpretacion_dimension`: 1 sola dimensión ⇒ nivel + implicación + n (sin comparación);
  3 dimensiones ⇒ identifica máx/mín y brecha con un decimal; `h` sin media ⇒ `None`; verificar
  español, formato (1 decimal) y que **no** aparezca la etiqueta de grupo "medio" (NIT #9).
- `agrupar_por_desempeno`: respondentes sintéticos ⇒ grupos esperados; **puntaje equiponderado**
  (F6): un dataset con una dimensión larga de valores bajos y una corta de valores altos clasifica
  distinto a como lo haría el promedio por ítem (test que fija la decisión §6.3); respondente sin
  Likert válido excluido del total (los `%` suman ~100 sobre clasificados); `bool`/str con coma vía
  `_num`; **test anti-regresión `perfil`** (dos datasets idénticos en Likert pero con `perfil`
  distinto ⇒ MISMOS grupos); todos los grupos vacíos ⇒ `[]`; nunca `nan`.
- `redactar_grupo`: encabezado (`n`, `%`), puntaje `x.x sobre 5`, dims altas/bajas, omisión de
  cláusula redundante con 1 dimensión; etiqueta "medio" (nunca "moderado") en la salida (NIT #9).

**Unit, en `prompt.py`:**
- `construir` sigue produciendo `[Fuente i — …]` + `CONTEXTO/PREGUNTA/RESPUESTA` (firma y formato
  intactos); el nuevo `_INSTRUCCION` contiene las palabras clave de interpretación, la cláusula de
  **alcance de la comparación** (F2) y la cláusula anti-invención (test de contenido mínimo, sin
  fijar el texto completo para no ser frágil).

**Integración:**
- `POST /rag/index` sobre el artefacto fijo
  `storage/raw/114c9cc8b19a46cf8ad0719099771bd1__inst_1.estandarizado.v1.json` (NIT #7, reproducible):
  afirmar que entre los documentos indexados aparecen (a) chunks interpretativos con las palabras
  "nivel"/"fortaleza"/"área de mejora" y nombres de dimensión reales, y (b) al menos un chunk con
  `clase_chunk="grupo_desempeno"`; y que el **contrato de respuesta de `/rag/index` no cambió**
  (mismas claves). Chroma/embeddings/BD se mockean según el patrón de los tests existentes.
- Humo del prompt: `POST /rag/chat` con una pregunta diagnóstica y Ollama mockeado (eco del prompt),
  comprobando que el prompt ya no prohíbe interpretar y que incluye la cláusula de alcance.

Toda la lógica densa (clasificación, agrupación, redacción) es pura y aislada del I/O ⇒ el diseño es
altamente testeable.

## 11. Cambios por archivo (contrato interno)

- **`app/core/prompt.py`**: reescribir **solo** `_INSTRUCCION` (§4.2). Firma y formato de `construir`
  intactos.
- **`app/core/agregacion.py`** (aditivo):
  - Constantes `_FRAC_BAJO`, `_FRAC_ALTO`, `_ETIQUETA_NIVEL`, `_ETIQUETA_GRUPO` (§5.1) con comentario
    justificativo.
  - `_clasificar_nivel(media, scale_min, scale_max)` (compartida mejoras 2/3).
  - `escala_efectiva(items)` **público, lista plana, min/max envolvente** (§5.4) para `sources`.
  - `redactar_interpretacion_dimension(h, todos_likert, scale_min, scale_max) -> str | None`.
  - `HallazgoGrupo` (dataclass), `agrupar_por_desempeno(...) -> list[HallazgoGrupo]`,
    `redactar_grupo(g, scale_max) -> str`.
  - Extender `__all__`. **No se modifica** la estadística existente (`agregar_likert`, `_num`,
    `_escala_efectiva`, `redactar_hallazgo`, `redactar_resumen_global`, `_redactar_likert`).
- **`app/core/sources.py`** → `construir_chunks`: añadir el 2º pase de interpretación (§5.5) y el
  bloque de grupos (§6.7), cada uno en su `try/except`, usando **lista plana** con `escala_efectiva`.
  No cambia su firma ni el resto de bloques.
- **`app/routers/rag.py`, `chunking.py`, `ollama_client.py`, `chroma_client.py`, `embeddings.py`,
  `original_txt.py`, schemas**: **sin cambios**.

El contrato HTTP de `/rag/index` y `/rag/chat` queda idéntico; la metadata de Chroma gana el valor
nuevo `clase_chunk="grupo_desempeno"` sin romper ninguna clave existente.

## 12. Alcance — lo que NO se hace en Fase 1

- No se genera un chunk por respondente individual (fase posterior explícita del encargo).
- No se incorporan variables de contexto (gpa, demográficas) al núcleo de los grupos (§6.6);
  backlogueado por robustez y alcance.
- No se agrupa por `perfil` ni ninguna etiqueta externa (prohibido).
- No se tocan otros tipos de instrumento (entrevistas, pruebas): los chunks nuevos solo se emiten para
  Likert; el resto del pipeline sigue igual (degradación grácil).
- No se parametriza la prosa estadística heredada (`_redactar_likert` sigue en "/5" y "4 o 5"); ver
  §13 (límite documentado, F4).
- No se modifica el contrato HTTP ni se añaden dependencias.
- No se re-trabaja la Opción B de agrupación (por características objetivas / clustering); el encargo
  fija **Opción A** (reglas simples y explicables) para esta fase.

## 13. Supuestos y límites documentados

1. La escala Likert por defecto es 1..5 cuando faltan `scale_min/scale_max` (confirmado en datos
   reales; `escala_efectiva` lo asume).
2. **Cortes por tercios `1/3, 2/3`** como criterio pedagógico explicable y FIJO (§5.1). No queda
   ninguna constante pendiente de decidir (F3 cerrado).
3. **Escala homogénea por instrumento** (F5): las mejoras 2/3 asumen que todas las dimensiones Likert
   comparten escala. `escala_efectiva` toma min/max envolvente sobre todos los ítems para no fallar si
   hubiera heterogeneidad; en datos reales la escala es homogénea 1..5. Declarado como invariante
   (§9).
4. **Límite de la prosa estadística heredada (F4):** `_redactar_likert` (chunk estadístico ya
   existente) mantiene "/5" y "respondió 4 o 5" **hardcodeados**. La parametrización de escala de la
   Fase 1 aplica **solo** a los chunks nuevos (interpretado y de grupo), que usan `scale_max` real. Si
   un instrumento tuviera escala ≠ 1..5, el chunk estadístico mostraría "/5" incoherente, pero los
   datos reales confirmados son 1..5, así que queda **fuera de alcance** y documentado. Parametrizar
   esa prosa sería una ampliación de alcance futura de dos interpolaciones.
5. **Puntaje global equiponderado por dimensión (F6):** decisión metodológica consciente (§6.3), no
   la media por ítem; cada dimensión pesa igual en la clasificación del respondente.
6. `items_por_dim` en `sources.construir_chunks` contiene únicamente dimensiones Likert (verificado),
   por lo que la agrupación jamás ve `perfil`.
7. `numpy` y la stdlib bastan; no se añaden dependencias.
8. El frontend y `rag.py` toleran el nuevo valor `clase_chunk="grupo_desempeno"` porque ignoran esa
   clave al construir `FuenteChatOut` (verificado en `_construir_fuentes`).

## 14. Riesgos

- **El LLM pequeño sobre-interpreta e inventa pese al prompt.** Mitigación: regla dura sobre cifras +
  cláusula de alcance de la comparación + los chunks interpretados ya traen la conclusión fundamentada
  (menos necesidad de "rellenar"). El resumen global y el chunk estadístico siguen como anclas.
- **Comparación limitada por la deduplicación (F2).** Mitigación: la comparación la aporta el chunk
  interpretado (una dimensión + la más fuerte/débil + brecha en un solo fragmento), no el prompt
  confiando en varias dimensiones en el top_k.
- **Cortes por tercios discutibles en tesis.** Mitigación: documentados, paramétricos y justificados
  (§5.1); fáciles de ajustar cambiando dos constantes.
- **Instrumento con una sola dimensión Likert.** La comparación entre dimensiones se omite con gracia
  (§5.3 reglas 2–3); el chunk interpretado queda con nivel propio + implicación + n.
- **Grupos degenerados** (todos en un solo grupo). Resultado válido: un único chunk de grupo.
- **Densidad de chunks** mayor (estructura + estadístico + interpretado por dimensión, más 2–3 de
  grupo). A 180×21 es trivial en cómputo; `top_k` limita el contexto y chunks cortos mejoran el match.

## 15. Respuesta a los hallazgos de la revisión (`design-review.json`)

Veredicto previo: **CHANGES_REQUESTED (2 HIGH, 4 MEDIUM, 4 NIT)**. Los 10 se **atienden** (ninguno se
backloguea ni se ignora); los cambios son coherentes con los requisitos originales (mejora interna de
calidad, sin tocar el contrato HTTP ni añadir dependencias).

- **F1 (HIGH) — firma `_escala_instrumento(items_por_dim)` vs `escala_efectiva(items)`.** Atendido.
  Se **elimina** el nombre `_escala_instrumento`; una **única** API pública `escala_efectiva(items)`
  recibe **lista plana** de tuplas (§5.4). En §5.5 y §6.7 se aplana `items_por_dim` a `items_plano`
  **antes** de llamarla. Desaparece el `KeyError/TypeError` que habría anulado la mejora 2 en
  silencio.
- **F2 (HIGH) — el prompt pide comparar pero el contexto se deduplica a 1 fragmento por instrumento.**
  Atendido. §2 documenta la deduplicación de `_construir_fuentes`; §4.2 añade la cláusula "ALCANCE DE
  LA COMPARACIÓN" (comparar solo si ambos elementos están en el CONTEXTO); §4.3/§4.4 corrigen la
  afirmación anterior y apoyan la comparación en los **chunks interpretados** (§5.3 regla 3), que
  internalizan "la más fuerte / más débil / brecha" en un solo fragmento recuperable.
- **F3 (MEDIUM) — cortes sin decidir (tercios vs 0.375/0.625).** Atendido. Se **fija** tercios
  `1/3, 2/3` como decisión final (§5.1), documentando que para 1..5 da 2.333/3.667 (≈ 2.5/3.5). Se
  **elimina** toda cláusula "si en revisión se prefiere…".
- **F4 (MEDIUM) — `pct_alto`/prosa heredada siguen en "/5" y "4 o 5".** Atendido como **límite
  documentado** (§13 supuesto 4 y §12): la parametrización de escala aplica solo a los chunks nuevos;
  `_redactar_likert` no se toca y permanece 1..5. Justificado porque los datos reales confirmados son
  1..5; parametrizar esa prosa queda fuera de alcance de la Fase 1.
- **F5 (MEDIUM) — `escala_efectiva` del primer ítem; escala homogénea no declarada.** Atendido. Se
  declara el invariante "escala homogénea por instrumento" (§5.4b, §9, §13 supuesto 3) y, por
  robustez, la nueva `escala_efectiva` toma **min/max sobre todos los ítems** (envolvente), no solo
  `items[0]`.
- **F6 (MEDIUM) — puntaje global ponderado por nº de ítems (sesgo no declarado).** Atendido. Se
  **cambia** el puntaje global a **media de las medias por dimensión** (equiponderado), decisión
  consciente y justificada en §6.3 y §13 supuesto 5; con test que fija el comportamiento (§10).
- **NIT #7 — artefacto ambiguo entre §2 y §10.** Atendido. Se fija el hash exacto
  `114c9cc8b19a46cf8ad0719099771bd1__inst_1.estandarizado.v1.json` en §2 y §10 (existen 4 artefactos
  `*__inst_1…`).
- **NIT #8 — `redactar_grupo` usa `scale_max` pero no `scale_min` ("sobre 5").** Atendido como nota
  documentada (§5.5, §6.5): "sobre N" asume `scale_min≈1`; cosmético dado 1..5 confirmado.
- **NIT #9 — dos vocabularios "medio"/"moderado".** Atendido. Renombrado centralizado en el mapa único
  `_ETIQUETA_GRUPO = {"moderado":"medio"}` (§5.1), aplicado solo al construir `HallazgoGrupo.grupo`;
  tests verifican que no se cuele el término incorrecto en cada tipo de chunk.
- **NIT #10 — ambigüedad `instrument_id`/`instrumentoId`.** Atendido. §2.1 aclara que el mapeo del
  `.txt` lo gobierna el **`instrumentoId` del router** (vía `_id_crudo_param`), con
  `artefacto["instrument_id"]` como respaldo; ninguna de las 3 mejoras altera esa ruta.

### 15.1 Estado del diseño

Con §15 integrado, los 2 HIGH / 4 MEDIUM / 4 NIT quedan resueltos en la especificación (ninguno
pendiente ni backlogueado). El diseño está **cerrado para implementación**; el loop de implementación
debe tratar §4–§9 y §15 como normativos.

## 16. Cierre de la revisión final (iteración 2 → APROBADO para implementar)

Veredicto previo: **CHANGES_REQUESTED (0 HIGH, 2 MEDIUM, 5 NIT)**. Esta sección integra las 7
observaciones como especificación **vinculante**. Con §16 el diseño queda cerrado y aprobado; el
loop de implementación debe tratar §16 como parte normativa (igual que §4–§7).

### 16.1 (MEDIUM #1) Una sola función de rango de escala, compartida por stat / interpretado / grupos

Para eliminar la bifurcación de escala entre el chunk estadístico y los chunks interpretados/de
grupo, se usa **una única fuente de verdad del rango**:

1. En `agregacion.py` existe `_escala_efectiva(items)`. Se **generaliza** a aceptar la forma que
   todos los llamadores pueden construir y se renombra a público `escala_efectiva(items)`
   (manteniendo un alias `_escala_efectiva = escala_efectiva` para no romper llamadas internas
   actuales). Firma: `escala_efectiva(items: list[tuple[str, str, int, int]]) -> tuple[float, float]`.
2. Comportamiento normativo: devuelve `(min(scale_min_i), max(scale_max_i))` sobre **todos** los
   ítems de la lista (no solo `items[0]`), y cae a `(1.0, 5.0)` si la lista es vacía o algún par es
   inválido (`min >= max`). Bajo el **invariante de escala homogénea** (todos los ítems Likert de un
   instrumento comparten escala — declarado en §5/§2), el min/max envolvente coincide con el del
   primer ítem, de modo que `agregar_likert` (que hoy usa `items[0]` para `pct_alto`) obtiene el
   **mismo** rango que las mejoras 2 y 3. Así se cumple literalmente "reusar `_escala_efectiva`".
3. **Todos** los cálculos que dependan del rango (el `pct_alto` de `agregar_likert`, la
   clasificación de nivel de la mejora 2, y los cortes de grupo de la mejora 3) DEBEN llamar a esta
   única `escala_efectiva`. Prohibido recalcular el rango por otra vía.
4. Test obligatorio (§10): con una dimensión de ítems homogéneos 1..5, `escala_efectiva` y el rango
   que usa `agregar_likert` para `pct_alto` devuelven idéntico `(1.0, 5.0)`; con una lista mixta
   (defensa), devuelve el envolvente.

### 16.2 (MEDIUM #2) El nivel por dimensión sale ÚNICAMENTE de `_clasificar_nivel`

Se fija una función única de clasificación y se prohíbe cualquier otro criterio:

```python
# agregacion.py — única fuente del nivel por media.
_ETIQUETA_NIVEL = {"bajo": "nivel bajo", "medio": "nivel moderado", "alto": "nivel alto"}

def _clasificar_nivel(media: float, scale_min: float, scale_max: float) -> str:
    """Clasifica una media en bajo/medio/alto por tercios del rango efectivo."""
    rango = scale_max - scale_min
    corte_bajo = scale_min + rango / 3.0
    corte_alto = scale_min + 2.0 * rango / 3.0
    if media < corte_bajo:
        return "bajo"
    if media < corte_alto:
        return "medio"
    return "alto"
```

- `redactar_interpretacion_dimension(h, scale_min, scale_max)` obtiene el nivel **exclusivamente**
  con `nivel = _clasificar_nivel(h.media, scale_min, scale_max)` y redacta con `_ETIQUETA_NIVEL[nivel]`.
  Queda **prohibido** usar cortes fijos 2.5/3.5 u otro criterio ad-hoc; los cortes son por tercios
  del rango efectivo (relativos a la escala, como pide el encargo).
- La **mejora 3** (grupos) usa la MISMA `_clasificar_nivel` sobre el **puntaje global** del
  respondente (media de sus medias por dimensión, §6/F6), de modo que "nivel de dimensión" y "grupo
  de desempeño" comparten criterio y son coherentes.
- Test obligatorio (§10): tabla media→etiqueta para escala 1..5 (p.ej. 1.8→bajo, 3.0→medio,
  4.2→alto) y para una escala distinta (p.ej. 0..10: 2→bajo, 5→medio, 8→alto).

### 16.3 (NIT #3) Desempate determinista en comparación de dimensiones

En las reglas 2–3 de `redactar_interpretacion` (dimensión más fuerte / más débil), ante empate
exacto de media se elige la **primera en orden de aparición** (orden de `orden_dim` en
`construir_chunks`). Si la más alta y la más baja resultaran la misma dimensión (caso de una sola
dimensión), se omite la cláusula comparativa y se reporta solo el nivel de esa dimensión.

### 16.4 (NIT #4) El chunk interpretado debe caber en una ventana

El texto de cada chunk interpretado por dimensión se acota a **≤ ~700 caracteres** (1 nivel + a lo
sumo comparación con 1–2 dimensiones + 1 implicación genérica), para que NO sea re-troceado por
`chunking.trocear` (VENTANA=800) en `_aplanar_piezas`; así la comparación vive en un único fragmento
recuperable (propiedad de F2). Si por acumulación el texto se acercara al límite, se recorta la
cláusula de implicación antes que la de comparación.

### 16.5 (NIT #5) Rama defensiva no-Likert

`redactar_interpretacion_dimension` incluye una comprobación `if h.tipo != "likert": return ""` como
**defensa para uso directo en tests**; el único llamador de producción (`construir_chunks`) ya
pre-filtra a Likert, por lo que esa rama no se dispara en runtime. Documentarlo como comentario.

### 16.6 (NIT #6) Una sola estructura hacia la agrupación por desempeño

`agrupar_por_desempeno` recibe **`items_por_dim`** (el mismo dict `dim -> list[(qid, texto, smin,
smax)]` que ya construye `construir_chunks`) y los `respondents`, y deriva internamente lo que
necesite. Prohibido pasar estructuras planas paralelas (`items_likert`, `dims_por_qid`) que haya que
mantener sincronizadas a mano: esto reduce la superficie de error del invariante solo-Likert (todo
sale de `items_por_dim`, que a su vez solo contiene preguntas Likert).

### 16.7 (NIT #7) Ejemplo alineado con las reglas de redacción

El texto de ejemplo del chunk interpretado se corrige para NO inventar causas psicológicas
("disposición e interés", "hábitos de organización"). La implicación debe ser **genérica derivada
del nivel** (p.ej. nivel bajo → "área de mejora prioritaria"; nivel alto → "fortaleza a sostener"),
sin atribuir causas no presentes en los datos. Ejemplo normativo de chunk interpretado:

> «Organización y Planificación» se sitúa en nivel moderado (media 3.2 sobre un rango de 1 a 5). Es
> la dimensión más baja del instrumento, frente a «Motivación» (media 3.6), la más alta; la brecha
> entre ambas es de 0.4 puntos. Un nivel moderado señala una competencia parcialmente desarrollada
> y constituye un área de mejora recomendable. n = 180 respondentes.

Nótese: cifras del contexto, nivel vía `_clasificar_nivel`, comparación con desempate determinista,
implicación genérica derivada del nivel, denominador expresado como "rango de 1 a 5" (no "/5"
hardcodeado) en los textos NUEVOS. (La prosa estadística heredada de `_redactar_likert` sigue en
"/5" por estar fuera de alcance, F4.)

### 16.8 Estado del diseño

Con §16.1–§16.7 integrados, los 0 HIGH / 2 MEDIUM / 5 NIT quedan resueltos en la especificación. El
diseño está **aprobado para implementación**. El loop de implementación debe seguir §16 al pie de la
letra junto con §4–§10.
