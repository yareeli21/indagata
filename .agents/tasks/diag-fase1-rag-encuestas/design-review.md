# Revisión de diseño — FASE 1: Diagnóstico pedagógico RAG para encuestas Likert

**Artefacto revisado:** `.agents/tasks/diag-fase1-rag-encuestas/design.md` (Iteración 2).
**Revisor:** subagente de revisión de diseño, en frío, verificando contra el código real del
`visualization-service`.

**Método:** Leí el diseño completo (§1–§15) y verifiqué sus afirmaciones contra el código fuente real
(`prompt.py`, `agregacion.py`, `sources.py`, `rag.py`, `original_txt.py`, `chunking.py`) y contra el
artefacto real `storage/raw/114c9cc8b19a46cf8ad0719099771bd1__inst_1.estandarizado.v1.json`.

**Veredicto:** CHANGES_REQUESTED — 0 HIGH, 2 MEDIUM, 5 NIT.

---

## Hallazgos

### 1. [MEDIUM] Dos funciones de escala con semánticas distintas rompen la coherencia que el encargo pedía ("reusar `_escala_efectiva`")

**Dónde:** §5.4(a), §2 (bullet de `agregacion.py`), y el código real `agregacion.agregar_likert` /
`agregacion._escala_efectiva`.

**Problema:** El encargo pide explícitamente que los umbrales sean "paramétricos y relativos a
scale_min/scale_max **reusando `_escala_efectiva`**". El diseño NO reusa `_escala_efectiva`; crea una
función nueva `escala_efectiva(items)` (pública, min/max envolvente sobre TODOS los ítems) y deja la
privada `_escala_efectiva(items)` (que lee solo `items[0]`) intacta para `agregar_likert`. Verificado
en el código: `agregar_likert` hace `scale_min, scale_max = _escala_efectiva(items)` y de ahí calcula
el `umbral` del `pct_alto`. Resultado: a partir de la Fase 1 conviven **dos** rangos de escala con
reglas distintas:
- el chunk estadístico (`_redactar_likert` + `pct_alto`) usa el rango del **primer ítem**;
- el chunk interpretado y los grupos usan el rango **envolvente**.

Para los datos reales (homogéneos 1..5) coinciden, así que no hay bug hoy. Pero el diseño declara el
"invariante de escala homogénea" como salvaguarda y simultáneamente introduce la bifurcación que ese
invariante debería evitar: si algún día un instrumento mezcla escalas (justo el caso que `escala_efectiva`
dice cubrir "por robustez"), el `pct_alto` ("respondió 4 o 5") y la clasificación de nivel se calcularían
sobre rangos diferentes, produciendo un chunk estadístico y un chunk interpretado incoherentes entre sí
para la misma dimensión. Es exactamente el tipo de inconsistencia entre secciones que el encargo (punto 2)
pedía evitar.

**Fix concreto (elegir uno y dejarlo escrito en §5.4):**
- (a) **Preferido:** refactorizar `_escala_efectiva` para que acepte min/max envolvente y que
  `agregar_likert` y la nueva lógica llamen a la MISMA función (una sola fuente de verdad del rango),
  renombrando/exponiendo esa única función. Esto cumple literalmente el "reusar `_escala_efectiva`" del
  encargo y elimina la bifurcación. Requiere un test de no-regresión del `pct_alto` sobre 1..5 (que no
  cambia).
- (b) Si se decide NO tocar `agregar_likert` (postura actual), añadir al diseño una afirmación explícita
  de que, bajo el invariante de escala homogénea, `_escala_efectiva(items[0])` y
  `escala_efectiva(items)` devuelven **lo mismo**, y un test unitario que lo verifique sobre el artefacto
  real; además documentar en §13 que la coherencia stat↔interpretado SOLO está garantizada bajo
  homogeneidad y que la bifurcación es deuda consciente. Hoy el diseño documenta la homogeneidad pero no
  reconoce que la coexistencia de las dos funciones es precisamente lo que la viola si deja de cumplirse.

---

### 2. [MEDIUM] `redactar_interpretacion_dimension` nunca especifica que calcula el nivel con `_clasificar_nivel`; la firma recibe la escala pero el cuerpo no está atado al clasificador

**Dónde:** §5.2 (firma) y §5.3 (reglas de redacción, regla 1 interpola `ETIQUETA_NIVEL[nivel]`).

**Problema:** La regla 1 interpola `_ETIQUETA_NIVEL[nivel]`, pero ni la firma ni el cuerpo del diseño
dicen de dónde sale `nivel`. Se **infiere** que debe ser `_clasificar_nivel(h.media, scale_min,
scale_max)`, pero no está escrito. Como el encargo (punto 2) exige que los umbrales sean "paramétricos y
relativos a scale_min/scale_max reusando [la función de escala], no hardcodeados a 1..5", dejar implícito
el único punto donde `redactar_interpretacion_dimension` consume esos umbrales abre la puerta a que la
implementación clasifique con un criterio ad-hoc (p. ej. comparar `h.media` contra `todos_likert` por
cuartiles, o contra 2.5/3.5 fijos) y rompa la coherencia con los grupos. El invariante §9 ("cortes
coherentes vía `_clasificar_nivel`") no basta si el diseño no ata explícitamente esta función a él.

**Fix concreto:** Añadir a §5.3 (o a §5.2) la línea normativa:
```python
nivel = _clasificar_nivel(h.media, scale_min, scale_max)   # ÚNICO origen del nivel por dimensión
```
y una frase: "La clasificación de nivel de `redactar_interpretacion_dimension` DEBE provenir
exclusivamente de `_clasificar_nivel`; no se permite ningún otro criterio de corte." Añadir al §10 un
test que fije que una media que cae en 'alto' por `_clasificar_nivel` produce la etiqueta
`_ETIQUETA_NIVEL["alto"]` en el texto.

---

### 3. [NIT] Empates de media entre dimensiones no están especificados

**Dónde:** §5.3 reglas 2–3 ("si `h` es la de media máxima → mejor evaluada… si es la mínima → …").

**Problema:** Con `max(todos_likert, key=…)` / `min(…)`, dos dimensiones con la misma media producen una
elección arbitraria de "la mejor evaluada" / "la más débil". No es incorrecto, pero el texto podría
afirmar que una dimensión es "la mejor evaluada" cuando hay otra empatada, lo que es defendible pero no
está documentado.

**Fix concreto:** Documentar en §5.3 que ante empate se elige la primera en orden de aparición
(determinista) y, si se quiere precisión, usar "una de las dimensiones mejor evaluadas" cuando haya
empate exacto. Suficiente con una nota; no requiere lógica nueva obligatoria.

---

### 4. [NIT] Riesgo (menor) de re-troceo de chunks interpretados por `chunking.VENTANA`

**Dónde:** §3.1 / §5.3 / §6.5 y `rag._aplanar_piezas` + `chunking.trocear` (VENTANA=800,
MIN_LONGITUD=40, verificado).

**Problema:** `_aplanar_piezas` re-trocea cualquier `ChunkIndexable.texto` que supere 800 chars y
descarta piezas <40 chars. El ejemplo interpretado (§5.3) ronda ~400 chars y los de grupo ~300, así que
hoy no se parten ni se descartan. Pero el diseño vende la ventaja de que el chunk interpretado
"internaliza la comparación en un solo fragmento recuperable" (clave de F2). Si en un instrumento con
muchas dimensiones el texto creciera >800 chars, `trocear` lo partiría y la comparación dejaría de estar
"en un solo fragmento", debilitando precisamente el mecanismo que §4.4/§5.3 presentan como la solución a
F2.

**Fix concreto:** Añadir a §5.3 una restricción de longitud (el texto interpretado por dimensión se
mantiene conciso, p. ej. ≤ ~700 chars, acotando a 1–2 dimensiones comparadas) y una nota en §14 (Riesgos)
de que el chunk interpretado debe caber en una sola ventana para preservar la propiedad de F2. No cambia
`chunking.py`.

---

### 5. [NIT] `redactar_interpretacion_dimension` filtra por `h.tipo == "likert"` pero `sources` ya le pasa solo likert

**Dónde:** §5.5 (`hallazgos_likert = [h for h in hallazgos if h.tipo == "likert" and h.media is not
None]`) y §7 (tabla, fila "h no es likert / sin media → None").

**Problema:** `sources` ya filtra a likert con media antes de llamar, así que la rama "no es likert" de
`redactar_interpretacion_dimension` es inalcanzable desde el único llamador. No es un error (defensa
redundante razonable para una función pura y testeada aislada), pero conviene que el diseño lo diga para
que el implementador no asuma que hay un segundo llamador.

**Fix concreto:** Nota de una línea en §5.2: "La comprobación interna `h.tipo != 'likert' → None` es
defensa para uso directo en tests; el único llamador (`sources`) ya pre-filtra."

---

### 6. [NIT] `dims_por_qid` y `items_likert` llevan información redundante hacia `agrupar_por_desempeno`

**Dónde:** §6.3 (firma `agrupar_por_desempeno(items_likert, dims_por_qid, respondents)`) y §6.7
(construcción de ambos desde `items_por_dim`).

**Problema:** `items_likert` es `[(qid, texto, smin, smax)…]` y `dims_por_qid` es `{qid: dim}`; juntos
describen lo mismo que `items_por_dim`. No es un bug, pero el paso 1 de §6.3 ("Ids Likert por dimensión
desde `items_likert` + `dims_por_qid`") reconstruye el agrupamiento que `sources` ya tenía en
`items_por_dim`, dejando dos representaciones que deben mantenerse consistentes a mano. Como el encargo
pone el foco en que la agrupación salga EXCLUSIVAMENTE de los ítems Likert (y nunca de `perfil`), simplificar
la interfaz reduce la superficie de error.

**Fix concreto (opcional):** Considerar pasar `items_por_dim` (o un `dict[dim] -> list[qid]`) directamente
a `agrupar_por_desempeno` en vez de las dos estructuras planas, o documentar en §6.3 que ambas DEBEN
derivarse del mismo `items_por_dim` (como ya hace §6.7) para no divergir. Mantiene el invariante §6.1.

---

### 7. [NIT] El texto de ejemplo del chunk interpretado afirma una implicación causal que el prompt prohíbe inventar

**Dónde:** §5.3 texto de ejemplo: "…el estudiantado muestra disposición e interés, pero requiere apoyo
en hábitos de organización del estudio."

**Problema:** La regla 4 dice que la implicación educativa es "genérica y derivada del nivel calculado;
no inventa causas". Pero el ejemplo redactado va más allá del mapa genérico de la regla 4 (bajo →
"conviene priorizar…", etc.) y produce una interpretación específica ("disposición e interés", "hábitos
de organización"). Esa frase del ejemplo no sale de ninguna de las cuatro reglas de redacción listadas;
si el implementador la toma como objetivo, estaría generando prosa que el propio diseño clasifica como
"inventar causas". Es incoherencia entre el ejemplo ilustrativo y las reglas normativas.

**Fix concreto:** Alinear el ejemplo con la regla 4: terminar en la implicación genérica derivada del
nivel (p. ej. "…lo que sugiere priorizar el refuerzo de la organización del estudio, la dimensión peor
evaluada."), sin atribuir rasgos ("disposición e interés") que no derivan de las cifras. O bien marcar
explícitamente que el ejemplo es ilustrativo y que la salida real se ciñe a las 4 reglas.

---

## Supuestos verificados (contra código y artefacto real)

1. **`prompt.construir` — contrato intacto.** VERIFICADO. El código real solo tiene la constante
   `_INSTRUCCION` y la función `construir(pregunta, chunks)` que arma `[Fuente i — titulo (tipo,
   investigador)]` + fragmento y el orden `CONTEXTO/PREGUNTA/RESPUESTA`. Cambiar únicamente
   `_INSTRUCCION` (§4.1/§4.2) no toca la firma ni el bloque de fuentes. El nuevo texto conserva la regla
   dura ("las CIFRAS… EXCLUSIVAMENTE del CONTEXTO… no inventes") y añade el permiso de interpretar: la
   defensa anti-alucinación se mantiene. CUMPLE el check (1) del encargo.
2. **Deduplicación por `instrumentoId` en `_construir_fuentes`.** VERIFICADO literalmente: `if
   instrumento_id in vistos: continue; vistos.add(...)`. El chat ve un fragmento por instrumento, lo que
   justifica la cláusula "ALCANCE DE LA COMPARACIÓN" (§4.2) y la estrategia de internalizar la comparación
   en el chunk interpretado (§5.3). CUMPLE el soporte argumental de F2.
3. **`agregacion` ya tiene `_num`, `_escala_efectiva`, `HallazgoDimension(tipo, media, n, …)`,
   `redactar_hallazgo`, `redactar_resumen_global`.** VERIFICADO. `HallazgoDimension` expone `tipo` y
   `media`, usados por §5.5. `_escala_efectiva` lee SOLO `items[0][2]/[3]` (confirmado). `_redactar_likert`
   hardcodea "/5" y "respondió 4 o 5" (confirmado; sustenta F4). `__all__` NO incluye aún los símbolos
   nuevos (deberán añadirse, como dice §11).
4. **`sources.construir_chunks` arma `questions_likert` por `type=="likert"`, el `mapa`, `items_por_dim`
   solo desde likert, y llama `agregar_likert`+`redactar_hallazgo` por dimensión.** VERIFICADO. `perfil`
   (q2, `opcion_multiple`) NO entra en `items_por_dim`; entra por la rama categórica aparte. El invariante
   §6.1 (la agrupación nunca ve `perfil`) está garantizado por construcción. CUMPLE el check (3).
5. **`rag._aplanar_piezas` propaga `{clase_chunk, dimension}` como metadata aditiva y numera `id`/
   `chunk_index`; `FuenteChatOut` NO incluye `clase_chunk`/`dimension`.** VERIFICADO. Un `clase` nuevo
   (`"grupo_desempeno"`) viaja solo; `rag.py` no requiere cambios y el contrato HTTP de `/rag/chat`
   (claves de `FuenteChatOut`) no cambia. CUMPLE el check (5).
6. **Metadata de Chroma escrita por `rag.indexar`:** claves `instrumentoId, titulo, tipo, investigador,
   kpis, investigacionId, chunk_index, clase_chunk, dimension`. VERIFICADO. Añadir el valor
   `clase_chunk="grupo_desempeno"` no agrega ni quita claves. CUMPLE el check (5).
7. **Artefacto real `114c9cc8…__inst_1`.** VERIFICADO ejecutando lectura del JSON: `instrument_id =
   "upload_1"`; 30 preguntas (21 `likert` q13..q33 con `scale_min=1/scale_max=5`, 4 `opcion_multiple`
   incl. q2 `perfil` con opciones P1..P8, 2 `numerica_continua`, 2 `binaria`, 1 `abierta`); 180
   `respondents` con claves `{respondent_id, demographics, answers}`. Coincide con §2 y §6.1. El hash
   fijado en §2/§10 existe en disco.
8. **Degradación "solo Likert" y sin respondentes.** VERIFICADO en `construir_chunks`: si no hay
   `instrument/preguntas` devuelve `[]`; si no hay `respondents` retorna tras los chunks de estructura
   (`if not respondents: return chunks`). Los bloques nuevos (§5.5, §6.7) se condicionan a
   `hallazgos_likert`. CUMPLE el check (4) para los casos sin Likert y sin respondentes.
9. **Cortes paramétricos relativos al rango, no hardcodeados a 1..5.** VERIFICADO en el diseño:
   `_clasificar_nivel` usa `scale_min + _FRAC*rango` con `_FRAC_BAJO=1/3`, `_FRAC_ALTO=2/3`, y defensa
   `rango<=0 → 1..5`. Son relativos y justificados (§5.1). CUMPLE el check (2) en cuanto a parametrización
   y justificación (la objeción es la fuente del rango, hallazgo MEDIUM #1).
10. **Agrupación sin columnas demográficas.** VERIFICADO: `agrupar_por_desempeno` recibe solo
    `items_likert`, `dims_por_qid`, `respondents` y clasifica por puntaje global Likert; §6.6 excluye
    demográficas del núcleo. Funciona sin columnas de contexto. CUMPLE el check (3) y parte del (4).

## Supuestos no verificados / corregidos

1. **"Reusar `_escala_efectiva`" (encargo, check 2).** PARCIALMENTE INCUMPLIDO. El diseño NO reusa
   `_escala_efectiva`; introduce una función paralela `escala_efectiva` y deja la privada para la
   estadística existente. Verificado en código que `agregar_likert` seguirá usando la de primer-ítem. Es
   la base del hallazgo MEDIUM #1. (El diseño lo documenta como decisión F5, pero contradice la letra del
   encargo y crea una bifurcación de escala.)
2. **Grado de degradación grácil ante instrumento SIN columnas de contexto en el *texto* de grupo.** NO
   APLICABLE/NO VERIFICABLE porque §6.6 decide no incorporar variables de contexto al chunk de grupo en
   Fase 1. El check (4) "sin columnas de contexto" queda cubierto por omisión (el núcleo no las usa), no
   por manejo activo. Correcto, pero conviene notar que "cubre instrumentos sin columnas de contexto"
   se satisface trivialmente al no usarlas nunca.
3. **Comportamiento de `_aplanar_piezas` con los chunks nuevos (longitud/MIN_LONGITUD).** VERIFICADO el
   código de `chunking` (VENTANA=800, MIN_LONGITUD=40). Los ejemplos de chunk nuevos caen dentro del rango
   seguro HOY; el diseño no acota la longitud explícitamente (NIT #4). No es un supuesto roto, pero sí uno
   no declarado.
4. **`__all__` actualizado.** El diseño afirma añadir los símbolos nuevos a `__all__` (§5.2, §6.4, §11);
   verificado que el `__all__` actual NO los contiene (es trabajo pendiente correcto, no una afirmación
   falsa).

---

## Resumen del veredicto

- HIGH: 0
- MEDIUM: 2 (coherencia de escala stat↔interpretado por la bifurcación de funciones; nivel de dimensión
  no atado explícitamente a `_clasificar_nivel`)
- NIT: 5

Como hay 2 hallazgos MEDIUM, el veredicto es **CHANGES_REQUESTED**. Ambos MEDIUM son cerrables con cambios
de especificación acotados (una decisión sobre la función de escala y una línea normativa que ate la
clasificación de nivel a `_clasificar_nivel`), sin ampliar el alcance de la fase.
