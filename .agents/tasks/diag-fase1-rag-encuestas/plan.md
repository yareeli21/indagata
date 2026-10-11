# Implementation Plan — FASE 1: Diagnóstico pedagógico del RAG para encuestas Likert

> Implementa el diseño APROBADO (`.agents/tasks/diag-fase1-rag-encuestas/design.md`, normativo
> §4–§10 y §16) sobre el `visualization-service`. NO reabre decisiones de diseño. Solo encuestas
> Likert; cambios **aditivos**; sin tocar el contrato HTTP ni añadir dependencias.
>
> Archivos que se tocan: `app/core/agregacion.py`, `app/core/sources.py` (solo `construir_chunks`),
> `app/core/prompt.py` (solo `_INSTRUCCION`), y tests. **NO** se tocan `rag.py`, `chunking.py`,
> `ollama_client.py`, `chroma_client.py`, `embeddings.py`, los schemas, ni la estadística existente
> de `agregacion.py` (`agregar_likert`, `_num`, `redactar_hallazgo`, `redactar_resumen_global`,
> `_redactar_likert`).
>
> **Comando de verificación (desde la raíz del repo):**
> `.\.venv\Scripts\python.exe -m pytest services/visualization-service/tests -q`
> Baseline actual: 43 tests en verde. Toda la lógica densa de `agregacion.py` es pura y unit-testable
> sin BD/disco/Chroma; la integración mockea embeddings y Chroma (patrón ya en `test_rag_index.py`).

---

- [ ] 1. Clave de escala única: renombrar `_escala_efectiva` → `escala_efectiva` (pública, min/max envolvente) con alias.
      En `app/core/agregacion.py` renombra la función privada `_escala_efectiva(items)` a
      `escala_efectiva(items)` y cambia su cuerpo para tomar `scale_min = min` de `it[2]` y
      `scale_max = max` de `it[3]` sobre **todos** los ítems de la lista (hoy lee solo `items[0]`),
      cayendo a `(1.0, 5.0)` si la lista es vacía, los tipos son inválidos (`TypeError/ValueError/
      IndexError`) o `scale_min >= scale_max` (§16.1, §5.4). Deja el alias
      `_escala_efectiva = escala_efectiva` después de la definición para no romper la llamada interna
      de `agregar_likert` (que la usa para `pct_alto`). Añade `escala_efectiva` a `__all__`.
      Files: services/visualization-service/app/core/agregacion.py
      Verify: `.\.venv\Scripts\python.exe -m pytest services/visualization-service/tests/test_agregacion.py -q` — los 20 tests existentes (incl. `test_agregar_likert_escala_no_1_5_umbral_tercio_superior`) siguen en verde, porque con escala homogénea 1..5 el envolvente coincide con `items[0]`.

- [ ] 2. Constantes de clasificación y `_clasificar_nivel` compartida (mejoras 2 y 3).
      En `agregacion.py` añade las constantes `_FRAC_BAJO = 1.0/3.0`, `_FRAC_ALTO = 2.0/3.0`, el mapa
      `_ETIQUETA_NIVEL = {"bajo": "nivel bajo", "medio": "nivel moderado", "alto": "nivel alto"}`
      (vocabulario de dimensión, §16.2) y `_ETIQUETA_GRUPO = {"bajo": "bajo", "medio": "medio",
      "alto": "alto"}` (etiqueta de salida de grupo; el renombrado se centraliza aquí, NIT #9).
      Implementa `_clasificar_nivel(media, scale_min, scale_max) -> str` por tercios del rango
      efectivo con la defensa `rango <= 0 -> asume 1..5` (código normativo en §16.2 + §5.1): devuelve
      `"bajo"` si `media < scale_min + rango/3`, `"alto"` si `media >= scale_min + 2*rango/3`, si no
      `"medio"`. NOTA: §16.2 fija las claves de salida como `bajo/medio/alto` (no `moderado`); usa
      esas tres claves de forma consistente con los dos mapas.
      Files: services/visualization-service/app/core/agregacion.py
      Verify: `.\.venv\Scripts\python.exe -m pytest services/visualization-service/tests/test_agregacion.py -q` — verde (aún sin tests nuevos; este paso solo añade símbolos). Se cubre con el paso 6.

- [ ] 3. Mejora 2 — `redactar_interpretacion_dimension` (chunk interpretado por dimensión).
      En `agregacion.py` implementa
      `redactar_interpretacion_dimension(h: HallazgoDimension, todos_likert: list[HallazgoDimension],
      scale_min: float, scale_max: float) -> str | None`. Reglas (§5.3 + §16.2–§16.5, §16.7):
      (a) rama defensiva `if h.tipo != "likert": return ""` (NIT #5, comentada como defensa para
      tests); `if h.media is None: return None`.
      (b) Nivel propio vía `nivel = _clasificar_nivel(h.media, scale_min, scale_max)` y
      `_ETIQUETA_NIVEL[nivel]`; **prohibido** cualquier corte ad-hoc 2.5/3.5.
      (c) Comparación entre dimensiones SOLO si hay ≥2 en `todos_likert` con `media is not None`:
      identifica la de media máxima y mínima; **desempate determinista** = primera en el orden de
      `todos_likert` (NIT #3, usar `max`/`min` sobre la lista preserva el primer máximo/mínimo). Si
      máx y mín son la misma dimensión (1 sola con media), omite la cláusula comparativa. Nombra la
      más fuerte, la más débil y la brecha `abs(media_max - media_min)` con 1 decimal.
      (d) Implicación GENÉRICA derivada solo del nivel (sin inventar causas, §16.7): bajo → "área de
      mejora prioritaria"; medio → "competencia parcialmente desarrollada / área de mejora
      recomendable"; alto → "fortaleza a sostener".
      (e) Cierre `f"n = {h.n} respondentes."`.
      (f) Denominador en los textos NUEVOS como "rango de 1 a {scale_max:.0f}" o "sobre un rango de 1
      a {scale_max:.0f}" (NO "/5" hardcodeado, §16.7); "sobre N" asume `scale_min≈1` (NIT #8,
      documentado en comentario).
      (g) El texto debe caber en ≤~700 chars para no re-trocearse (§16.4): si se acerca al límite,
      recorta la implicación antes que la comparación. Añade la función a `__all__`.
      Files: services/visualization-service/app/core/agregacion.py
      Verify: paso 6 (tests unitarios).

- [ ] 4. Mejora 3 — dataclass `HallazgoGrupo`, `agrupar_por_desempeno` y `redactar_grupo`.
      En `agregacion.py` añade `@dataclass(frozen=True) HallazgoGrupo` con campos
      `grupo:str, n:int, pct:float, puntaje_medio:float, dim_altas:list[tuple[str,float]],
      dim_bajas:list[tuple[str,float]]` (§6.4). Implementa
      `agrupar_por_desempeno(items_por_dim: dict[str, list[tuple[str,str,int,int]]],
      respondents: list[dict]) -> list[HallazgoGrupo]` (§16.6 — recibe el **dict** `items_por_dim`,
      NO estructuras planas paralelas; de ahí deriva internamente qids por dimensión). Algoritmo
      (§6.3, F6):
      (1) si no hay ítems Likert ⇒ `return []`;
      (2) rango = `escala_efectiva(lista_plana_de_items)`;
      (3) por respondente, **puntaje global = media de las medias por dimensión** (equiponderado):
      por cada dimensión promedia los `_num` válidos de esa dimensión (descartando `None`); una
      dimensión sin valor válido en ese respondente no cuenta; respondente sin ninguna dimensión
      válida se EXCLUYE del total;
      (4) clasifica con `_clasificar_nivel(puntaje_r, smin, smax)` y mapea la etiqueta de salida con
      `_ETIQUETA_GRUPO`;
      (5) por grupo acumula puntajes globales y la media por dimensión de cada miembro;
      (6) por grupo NO vacío construye `HallazgoGrupo` con `pct = n/total*100` (`total` =
      respondentes clasificados, nunca `/0`), `puntaje_medio`, y `dim_altas`/`dim_bajas` = 1–2 dims
      con mayor/menor media del grupo.
      INVARIANTE DURO (§6.1, §9): la agrupación sale EXCLUSIVAMENTE de `items_por_dim` (solo Likert);
      jamás se lee `perfil`/`profile_id`/P1..P8 ni demográficas. No se incorporan variables de
      contexto al chunk (§6.6, backlog).
      Implementa `redactar_grupo(g: HallazgoGrupo, scale_max: float) -> str` (§6.5): encabezado con
      `grupo`, `n`, `% = round(pct)`; puntaje `f"{g.puntaje_medio:.1f} sobre {scale_max:.0f}"`;
      `dim_bajas` → "Mayor debilidad en {dim} (media X.X)[ y en {dim2} …]"; `dim_altas` → "relativa
      fortaleza en {dim} (media Z.Z)" (omite si coincide con una `dim_baja` en grupos de 1
      dimensión); cierre interpretativo por grupo (bajo/medio/alto, §6.5). 1 decimal, % enteros,
      nunca `nan`. Añade `HallazgoGrupo`, `agrupar_por_desempeno`, `redactar_grupo` a `__all__`.
      Files: services/visualization-service/app/core/agregacion.py
      Verify: paso 6 (tests unitarios).

- [ ] 5. Mejora 1 — reescribir `prompt._INSTRUCCION` (diagnóstico pedagógico).
      En `app/core/prompt.py` sustituye SOLO la constante `_INSTRUCCION` por el texto normativo de
      §4.2: habilita INTERPRETAR (fortalezas, debilidades, patrones, implicaciones), mantiene la
      REGLA DURA de que las cifras (medias, %, n, nombres de dimensión/ítem) salen EXCLUSIVAMENTE del
      CONTEXTO y no se inventan, e incluye la cláusula "ALCANCE DE LA COMPARACIÓN" (comparar solo si
      ambos elementos aparecen en el CONTEXTO; si hay uno solo, interpretarlo por sí mismo). Español.
      NO cambies la firma `construir(pregunta, chunks) -> str`, ni el bloque de fuentes numeradas
      `[Fuente i — titulo (tipo, investigador)]`, ni el orden `CONTEXTO/PREGUNTA/RESPUESTA`
      (§4.1 — el frontend y `rag.py` dependen de ello).
      Files: services/visualization-service/app/core/prompt.py
      Verify: paso 8 (test de contenido del prompt).

- [ ] 6. Tests unitarios de `agregacion.py` para las 3 piezas nuevas.
      Añade tests en `tests/test_agregacion.py` (patrón: helper `_r(**answers)` ya existente),
      cubriendo §10:
      - `escala_efectiva`: homogénea 1..5 ⇒ (1,5); mixta [(…,0,4),(…,1,5)] ⇒ envolvente (0,5) sin
        error; vacía / tipos inválidos / `min>=max` ⇒ (1,5). Y que `escala_efectiva` y el rango que
        usa `agregar_likert` para `pct_alto` coinciden en 1..5 (§16.1 test obligatorio).
      - `_clasificar_nivel`: 1..5 → 1.8 bajo, 3.0 medio, 4.2 alto; límites 2.333⇒medio, 3.667⇒alto;
        escala 0..10 → 2 bajo, 5 medio, 8 alto; `rango<=0` cae a 1..5 (§16.2).
      - `redactar_interpretacion_dimension`: 1 sola dimensión ⇒ nivel + implicación + n (sin
        comparación); 3 dimensiones ⇒ identifica máx/mín y brecha con 1 decimal; empate ⇒ primera en
        orden (NIT #3); `h.media=None` ⇒ `None`; `h.tipo!="likert"` ⇒ `""`; verifica español, 1
        decimal, "rango de 1 a 5" (no "/5"), que NO aparezca "medio" (etiqueta de grupo) y que el
        texto ≤ ~700 chars.
      - `agrupar_por_desempeno`: respondentes sintéticos ⇒ grupos esperados; **equiponderado (F6)**:
        dataset con una dimensión larga de valores bajos y una corta de valores altos clasifica
        distinto que el promedio por ítem (test que fija §6.3); respondente sin Likert válido
        excluido del total (los `%` suman ~100 sobre clasificados); `bool`/str con coma vía `_num`;
        **anti-regresión `perfil`**: dos datasets idénticos en Likert pero con `perfil` distinto ⇒
        MISMOS grupos; todos los grupos vacíos / `total==0` ⇒ `[]`; nunca `nan`.
      - `redactar_grupo`: encabezado (`n`, `%`), puntaje "x.x sobre 5", dims altas/bajas, omisión de
        cláusula redundante con 1 dimensión; aparece "medio" (nunca "moderado") en la salida (NIT #9).
      Files: services/visualization-service/tests/test_agregacion.py
      Verify: `.\.venv\Scripts\python.exe -m pytest services/visualization-service/tests/test_agregacion.py -q` — todos verdes (20 previos + nuevos).

- [ ] 7. Orquestar los chunks nuevos en `sources.construir_chunks` (segundo pase + bloque de grupos).
      En `app/core/sources.py`, DESPUÉS del bucle `for dim in orden_dim:` que ya emite el chunk
      estadístico Likert (y que ya llena `hallazgos` e `items_por_dim`), añade dos bloques, cada uno
      en su propio `try/except Exception … logger.warning(...)` (§5.5, §6.7):
      (B.2) Mejora 2: `hallazgos_likert = [h for h in hallazgos if h.tipo == "likert" and
      h.media is not None]`; si hay, `items_plano = [it for its in items_por_dim.values() for it in
      its]` (LISTA PLANA, F1), `smin, smax = agregacion.escala_efectiva(items_plano)`; por cada
      `h in hallazgos_likert` llama `agregacion.redactar_interpretacion_dimension(h, hallazgos_likert,
      smin, smax)` y si devuelve texto, `chunks.append(ChunkIndexable(texto, clase="hallazgos",
      dimension=h.dimension))` (reutiliza `clase_chunk="hallazgos"`, §3.1).
      (B.3) Mejora 3: `if hallazgos_likert and respondents:` dentro del try, `items_plano` (plana),
      `_smin, _smax = agregacion.escala_efectiva(items_plano)`,
      `grupos = agregacion.agrupar_por_desempeno(items_por_dim, respondents)` (pasa el DICT, §16.6);
      por cada grupo `chunks.append(ChunkIndexable(texto=agregacion.redactar_grupo(g, _smax),
      clase="grupo_desempeno", dimension=g.grupo))`.
      Coloca ambos bloques antes del resumen global para no alterar su cómputo. NO cambies la firma de
      `construir_chunks` ni los bloques existentes. `rag.py` NO se toca (ya propaga
      `clase`/`dimension` vía `_aplanar_piezas`; `grupo_desempeno` viaja solo).
      Files: services/visualization-service/app/core/sources.py
      Verify: `.\.venv\Scripts\python.exe -m pytest services/visualization-service/tests/test_sources_chunks.py -q` — tras actualizar sus asserts (paso 8), verde.

- [ ] 8. Actualizar los tests de integración/orquestación y añadir el test del prompt.
      (a) `tests/test_sources_chunks.py`: los asserts que hoy exigen exactamente 5 chunks de
      hallazgos y `clases.count("estructura") == 3` deben contemplar los chunks nuevos. Ajusta
      `test_construir_chunks_con_txt` para afirmar que ADEMÁS aparecen chunks interpretados por
      dimensión (p.ej. que algún texto contenga "nivel" y "rango de 1 a 5") y ≥1 chunk con
      `clase == "grupo_desempeno"`; mantén las aserciones de estructura y del resumen global, pero no
      fijes el conteo exacto de hallazgos de forma frágil (usa `>=`). Verifica que ningún chunk de
      grupo contenga "moderado" y ningún interpretado contenga la etiqueta de grupo "medio" (NIT #9).
      (b) `tests/test_rag_index.py`: el test `test_index_inst_1_prosa_y_metadata` hoy afirma
      `meta["clase_chunk"] in ("estructura", "hallazgos")` y `clases == {"estructura", "hallazgos"}`.
      Amplía ambos a incluir `"grupo_desempeno"` (p.ej. `in ("estructura","hallazgos",
      "grupo_desempeno")` y `clases >= {"estructura","hallazgos"}` o `== {"estructura","hallazgos",
      "grupo_desempeno"}`), y añade aserciones de que entre los documentos aparecen chunks
      interpretativos con "nivel"/"fortaleza"/"área de mejora" y ≥1 con
      `clase_chunk == "grupo_desempeno"`; conserva las aserciones de contrato HTTP (claves de
      `IndexResponse`, `chunk_index` secuencial, ids `inv-demo:1:0`, kpis string) intactas (§10).
      (c) Nuevo `tests/test_prompt.py`: afirma que `prompt.construir("¿fortalezas?", [dict con
      titulo/tipo/investigador/fragmento])` conserva el formato (`[Fuente 1 — …]`,
      `CONTEXTO/PREGUNTA/RESPUESTA`) y que `_INSTRUCCION` contiene las palabras clave de
      interpretación y la cláusula de alcance de comparación y la regla anti-invención (test de
      contenido mínimo, sin fijar el texto completo).
      Files: services/visualization-service/tests/test_sources_chunks.py, services/visualization-service/tests/test_rag_index.py, services/visualization-service/tests/test_prompt.py
      Verify: `.\.venv\Scripts\python.exe -m pytest services/visualization-service/tests -q` — toda la suite en verde (43 previos actualizados + nuevos).

---

## Casos borde cubiertos (del diseño)
- Instrumento sin preguntas Likert ⇒ `hallazgos_likert` vacío ⇒ no se generan chunks nuevos; el resto
  del indexado (estructura, numéricas, categóricas, resumen) sigue igual (degradación grácil, D3/§8).
- Likert-todos-None en una dimensión ⇒ `agregar_likert` ya devuelve `None` ⇒ sin chunk estadístico ni
  interpretado para esa dimensión.
- Grupo vacío / `total==0` ⇒ `agrupar_por_desempeno` devuelve `[]` ⇒ sin chunk de grupo; nunca `nan`
  ni división por cero.
- Una sola dimensión Likert ⇒ el chunk interpretado omite la comparación (solo nivel + implicación + n).
- Cada bloque nuevo en `construir_chunks` va en su propio `try/except` con `logger.warning`: un fallo
  nuevo nunca tumba `/rag/index` (cero regresión sobre estructura + hallazgos estadísticos).

## Supuestos / límites (documentados en el diseño, no se reabren)
- Escala por defecto 1..5 cuando faltan `scale_min/scale_max`; `escala_efectiva` cae a (1,5).
- La prosa estadística heredada (`_redactar_likert`) sigue en "/5" y "4 o 5" (F4, fuera de alcance);
  solo los textos NUEVOS usan "rango de 1 a N".
- Puntaje global equiponderado por dimensión (F6), no por ítem.
- Comparación en el chat limitada por la deduplicación de `_construir_fuentes` (F2): la comparación la
  internaliza el chunk interpretado, no el prompt.
