# Plan de implementación — Rediseño de la calidad del indexado RAG (visualization-service)

Fuente de verdad: `design.md` (todas las secciones, **incluida §15**, son normativas). Este
plan ordena el trabajo por dependencia y cita la sección que gobierna cada pieza. NO se
implementa código en este paso; NO se hace `git add/commit/push`.

## Contexto verificado durante la exploración

- **Servicio**: `services/visualization-service`. Python 3 (el `.venv` del repo corre **Python
  3.14.2** con **pytest 9.1.1**). FastAPI + numpy + stdlib + SQLAlchemy 2.0.
- **No hay tests previos** en el visualization-service (confirmado: no existe
  `services/visualization-service/tests`). Se crea esa carpeta con su `conftest.py` siguiendo el
  patrón de `services/metadata-service/tests/conftest.py` y
  `services/instrument-service/app/standardization/tests/conftest.py` (inserta la raíz del
  servicio y la raíz del repo en `sys.path`). **No hay** `pytest.ini`/`pyproject.toml` en la
  raíz: pytest usa defaults y depende del `conftest.py` por servicio.
- **Comando de test (real)** desde la raíz del repo:
  `./.venv/Scripts/python.exe -m pytest services/visualization-service/tests -q`
  (en PowerShell: `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests -q`).
- **Comando de "build"/compilación** (el servicio no tiene build; se usa compilación de bytecode
  como humo de sintaxis): `./.venv/Scripts/python.exe -m compileall services/visualization-service/app`.
- **Datos reales confirmados** (`storage/raw/114c9cc8…__inst_1.estandarizado.v1.json`,
  `instrument_id="upload_1"`, 180 respondents):
  - `instrument.title="enc_01_respondido.csv"`, `objective=""`, `dimensions_explored=[]`, **una
    sola** `section` con `name="Reactivos del módulo"` (genérico, inútil para dimensiones).
  - 30 preguntas: 21 `likert` (q13–q33, escala 1..5), 4 `opcion_multiple`, 2 `numerica_continua`
    (`promedio_gpa` q6, `horas_trabajo_semana` q7), 2 `binaria` (opciones `["False","True"]`), 1
    `abierta` (`id_respondente` q1).
  - Mojibake real en nombres de columna del JSON: `Organizaci├│n_y__item1`, `Motivaci├│n_item1`.
  - **Colisión de prefijo truncado**: `Habilidades_par_item1..3` aparece dos veces (q20–q22 y
    q31–q33) → confirma por qué el mapeo primario debe ser posicional (§2.2, §5.4).
  - `respondents[i] = {respondent_id, demographics{edad,genero,semestre}, answers{qN: valor}}`;
    binarios llegan como strings `"True"`/`"False"`; `q6=2.92` (float), `q7=6` (int).
  - `.txt` original (`storage/raw/*enc_01_original.txt`): cabecera
    `INSTRUMENTO: Inventario de Estrategias de Aprendizaje y Estudio (IEAE)`, 6 secciones, 21
    ítems redactados numerados `1.`..`21.` — **mismo orden** que q13..q33. Confirma el mapeo
    posicional 1-a-1 de §5.4/§2.2.
- **`RawData.raw_archivo_original`** existe en `shared/models/raw_data.py` (tabla distinta de
  `InstrumentoProcesado`), tal como fija §5.1(ii)/§5.4-F2.
- **`local_backend.py`** persiste `ruta="raw/<unique_name>"` y lee desde
  `settings.raw_path_abs.parent` (= `storage/`): confirma el candidato primario de ruta de §5.1
  fix F1 (`settings.raw_path_abs.parent / rel`). El segundo candidato (`PROJECT_ROOT / rel`) cubre
  el caso seed.
- **Config**: `settings.raw_path_abs` = `PROJECT_ROOT/storage/raw`; `.parent` = `PROJECT_ROOT/storage`.
  `settings.PROJECT_ROOT` = raíz del repo. `settings.DATABASE_URL` disponible.

### Dos avisos descubiertos en la exploración (no rediseñan; se gestionan con degradación)

1. **numpy real = 2.5.3**, no 1.26.4 como declaran `requirements.txt` y el diseño (§1, §11
   supuesto 5). `agregacion.py` solo usa `np.mean`/`np.std`, que funcionan igual en numpy 2.x, así
   que **no bloquea**. No se toca `requirements.txt` (el encargo prohíbe cambiar dependencias).
   Se registra como riesgo conocido; si algún día se ejecuta con el chromadb-client que exige
   numpy<2 habría que reconciliar, pero eso está fuera del alcance.
2. **El mojibake real es cp850↔utf-8, no cp1252↔utf-8.** Verificado: `s.encode("cp1252")` lanza
   `UnicodeEncodeError` sobre `├│`, mientras que `s.encode("cp850").decode("utf-8")` reconstruye
   `Organización_y__item1`. El diseño §5.4-m2/§14-F10 especifica cp1252 y "si lanza UnicodeError,
   deja el original". **Asunción adoptada (mínima, no rediseño):** la reparación intenta
   `cp1252` y, si falla, `cp850`, y si ambas fallan deja el original. Esto respeta la letra del
   diseño (cp1252 primero) y además repara el dato real. Es intrascendente para inst_1 porque el
   mapeo **posicional** (con `.txt` presente y conteos 21==21) gana y el fallback por prefijo no
   se ejerce; solo mejora el modo degradado. Se cubre con un test unitario.

---

## Orden de edición (por dependencia)

Primero los dos módulos nuevos puros/aislados (no dependen de nada del servicio), luego la
orquestación en `sources.py`, luego el cableado en `rag.py`, y en paralelo lógico los tests de
cada pieza. Cada ítem deja el repo compilable.

- [ ] 1. Crear `app/core/agregacion.py` — estadística pura de respuestas (§4, §8, §9, §15.3-NIT5).
      Dataclasses `ResumenItem` y `HallazgoDimension` (§4.1) y funciones:
      `_num(v)->float|None` (coacción única; **excluye `bool` explícito** antes de int/float;
      str con `,`→`.`; §4.2), `agregar_likert(items, respondents, dimension)->HallazgoDimension|None`,
      `agregar_numerica(question_id, texto, respondents)->…|None`,
      `agregar_categorica(question_id, texto, tipo, respondents, top=5)->…|None`,
      `redactar_hallazgo(h)->str`, `redactar_resumen_global(hallazgos, n_respondentes, titulo)->str`.
      Reglas exactas de §4.2 (vector likert = concatenación de todos los valores válidos; `n` =
      nº de respondentes con ≥1 `_num` no-None; `media=np.mean`, `de=np.std(ddof=0)`; `pct_alto` =
      `% >= 4` en 1..5, o umbral de tercio superior `scale_min+2*(max-min)/3` si la escala difiere;
      ítem más alto/bajo por media; `abierta` NO se agrega; binaria `"True"/"False"`→`"sí"/"no"`).
      Casos borde §4.4: `n==0`⇒`None` (nunca `np.mean([])`, nunca formatear `nan`); % solo con `n>0`;
      `redactar_*` omiten cláusulas cuyos campos sean `None`. Redacción en español, números con
      `f"{x:.1f}"` y porcentajes `round(pct)` (§4.3). `redactar_resumen_global` defensivo (§15.3-NIT5:
      sin likert omite media alta/baja; sin numéricas omite esa cláusula; con `hallazgos` vacío solo
      reporta `n` y lista de dimensiones). Módulo **sin I/O**.
      Files: `services/visualization-service/app/core/agregacion.py`
      Verify: tras el ítem 6, `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests\test_agregacion.py -q` pasa;
      y `.\.venv\Scripts\python.exe -m compileall services\visualization-service\app\core\agregacion.py` sin error.

- [ ] 2. Crear `app/core/original_txt.py` — localización/lectura del `.txt`, parseo y mapeo a
      dimensión (§5, §8, §15.1). Dataclasses `SeccionOriginal`, `EstructuraOriginal` (§5.2) y
      funciones:
      `ruta_original(instrumento_id)->Path|None` (deriva `id_crudo = int(str(id).removeprefix("upload_"))`;
      si no parsea ⇒ sin BD-path; consulta `select(RawData.raw_archivo_original).where(RawData.id_crudo==id_crudo)`
      reusando el **patrón** de `sources._resolver_desde_bd` —engine con `settings.DATABASE_URL`,
      `Session`, degradar en silencio sin BD/driver—; resuelve la ruta probando **dos convenciones**
      `settings.raw_path_abs.parent / rel` y `settings.PROJECT_ROOT / rel`, quedándose con la que
      `is_file()`; fallback a glob en `settings.raw_path_abs` por nombre base derivado de
      `instrument.title` (`"enc_01_respondido.csv"`→`"enc_01"`→`glob("*enc_01_original.txt")`, más
      reciente por mtime) §5.1.1),
      `leer_texto_original(instrumento_id)->str|None` (lee en **utf-8 estricto**; `UnicodeDecodeError`/
      `OSError`/vacío ⇒ `None`; límite blando 2 MB; §8),
      `parsear_estructura(texto)->EstructuraOriginal` (título vía `^\s*INSTRUMENTO:\s*(.+?)\s*$`,
      secciones vía `^-{2,}\s*(.+?)\s*-{2,}$` a *Capitalización de Título*, ítems vía
      `^\s*(\d+)\.\s+(.+)$`; ignora `ID:`, `Fuente:`, `INSTRUCCIONES:`, líneas de escala, casillas y
      `FIN DEL INSTRUMENTO`; §5.3),
      `construir_mapa_dimension(estructura, questions_likert)->dict[str, tuple[str,str]]` (§5.4-m1 +
      §15.1): aplana `plano=[(sec.titulo, item) …]`; **chequeo de consistencia monotónica OBLIGATORIO
      (§15.1)** antes de aceptar posicional — agrupa `questions_likert` por prefijo normalizado
      (hasta `_item`) **por aparición contigua**, extrae `_item(\d+)$` y exige secuencia `1..k`
      creciente por grupo; si algún grupo no es monotónico ⇒ `{}` + WARNING "orden de ítems no
      monotónico; se usa agrupación por prefijo"; además condición de conteo `len(plano)==len(questions_likert)`
      (si no ⇒ `{}`); ambas deben cumplirse para posicional; `zip` por índice guardando
      `question_id → (dimensión, texto_redactado)`. Log INFO del método usado (`posicional`|`prefijo`)
      y motivo (`conteo_desigual`|`orden_no_monotonico`|`sin_txt`). Comentario de invariante en la
      función (§15.1 punto 1). I/O aislado del parseo puro.
      Files: `services/visualization-service/app/core/original_txt.py`
      Verify: tras el ítem 7, `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests\test_original_txt.py -q` pasa;
      `.\.venv\Scripts\python.exe -m compileall services\visualization-service\app\core\original_txt.py` sin error.

- [ ] 3. Añadir la lógica de reparación de mojibake + etiquetas de fallback por prefijo en
      `original_txt.py` (helper interno usado por `construir_mapa_dimension` en modo degradado,
      §5.4-m2, §4.3 modo degradado, §14-F9). Normalización: intentar reparar `cp1252` y (asunción
      del plan, ver avisos) `cp850`; si ambas lanzan `UnicodeError`, dejar el string original
      (NFKD). Recortar sufijo `_item\d+$`. Etiqueta de dimensión =
      `"Dimensión <Prefijo Reparado> (agrupación aproximada)"`; etiqueta por ítem = `f"{prefijo} ítem {n}"`.
      WARNING de colisión cuando dos `question_id` caen en el mismo prefijo colisionado.
      Files: `services/visualization-service/app/core/original_txt.py` (mismo archivo que el ítem 2)
      Verify: cubierto por `test_original_txt.py` (ítem 7); el test del fallback por prefijo con
      mojibake reparado y etiqueta "(agrupación aproximada)" pasa.

- [ ] 4. Modificar `app/core/sources.py` — precedencia de título + `construir_chunks`
      (§6.1, §6.2, §7, §15.2). (a) `extraer_metadata` gana el parámetro
      `titulo_override: str | None = None` y **REORDENA** la precedencia a (§15.2):
      `dc:title → titulo_override(.txt) → instrument.title → f"Instrumento {id}"` (hoy está al revés:
      `instrument.title` primero). (b) Añadir `ChunkIndexable(texto, clase, dimension)` dataclass
      (§6.1) y `construir_chunks(artefacto, instrumento_id)->list[ChunkIndexable]` que orquesta
      `original_txt` + `agregacion`: deriva `id_crudo` del **parámetro** (§15.3-NIT3,
      `artefacto["instrument_id"]` solo como respaldo); lee/parsea el `.txt`; calcula el título UNA
      vez vía `extraer_metadata(..., titulo_override=estructura.titulo_instrumento)` y lo reutiliza
      para la cabecera (§15.2 punto 2); emite chunks de ESTRUCTURA (cabecera + uno por sección/dimensión;
      degrada a nombres de columna normalizados si no hay `.txt`) y de HALLAZGOS (uno por dimensión
      likert, uno por numérica, uno por categórica/binaria, un resumen global; §6.1-B). Cada bloque
      en su propio `try/except` con WARNING y continuación (§6.5, §9). `extraer_texto` se **conserva**
      intacto en firma `(json)->str` (compat/fallback). `extraer_kpis` sin cambios.
      Files: `services/visualization-service/app/core/sources.py`
      Verify: tras el ítem 8, `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests\test_sources_chunks.py -q` pasa;
      `.\.venv\Scripts\python.exe -m compileall services\visualization-service\app\core\sources.py` sin error.

- [ ] 5. Modificar `app/routers/rag.py` — `POST /rag/index` usa `construir_chunks` + aplanado +
      numeración + metadata aditiva (§6.3, §6.4, §15.3-NIT4). En `indexar`, por instrumento:
      llamar `chunks_ix = sources.construir_chunks(artefacto, instrumento_id)`; **aplanar** cada
      `ChunkIndexable` a `piezas` re-troceando con `chunking.trocear` **solo** si
      `len(ch.texto) > chunking.VENTANA`, propagando `clase_chunk`/`dimension` a cada pieza (§6.4);
      **descartar** piezas con `len(texto.strip()) < chunking.MIN_LONGITUD` (§15.3-NIT4); numerar
      `ids`/`chunk_index` sobre la lista **aplanada** (§6.4); añadir a cada metadata los escalares
      `clase_chunk` y `dimension` **sin tocar** las claves existentes
      `{instrumentoId, titulo, tipo, investigador, kpis, investigacionId, chunk_index}` (§6.3, §9).
      Degradación: si `construir_chunks` devuelve `[]`, caer al camino actual
      (`extraer_texto`+`trocear`); si aún así no hay texto, `estado="omitido"` (ruta ya existente,
      §6.5). Embeddings/upsert/respuesta y el **contrato HTTP** no cambian (§7, §13).
      Files: `services/visualization-service/app/routers/rag.py`
      Verify: tras el ítem 9, `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests\test_rag_index.py -q` pasa;
      `.\.venv\Scripts\python.exe -m compileall services\visualization-service\app\routers\rag.py` sin error.

## Tests pytest a crear (§10)

Crear la carpeta `services/visualization-service/tests/` con un `conftest.py` que inserte la raíz
del servicio y la raíz del repo en `sys.path` (patrón de `metadata-service/tests/conftest.py`). La
BD y Chroma se mockean/omiten como en los tests existentes del repo.

- [ ] 6. `tests/conftest.py` + `tests/test_agregacion.py` (unit puro, §10). Con un `respondents`
      sintético pequeño verificar: media/DE/`pct_alto`, ítem más alto/bajo, distribución
      categórica, cadenas redactadas (formato `.1f`, porcentajes enteros, español). Casos borde:
      todos `None`⇒`None` (sin chunk, sin `nan`); un solo respondente; escala no 1..5 (umbral tercio
      superior); `bool` en answers (se excluye vía `_num`); str numérico con coma decimal;
      `redactar_resumen_global` sin likert / sin numéricas / con `hallazgos` vacío (§15.3-NIT5).
      Files: `services/visualization-service/tests/conftest.py`, `services/visualization-service/tests/test_agregacion.py`
      Verify: `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests\test_agregacion.py -q` pasa.

- [ ] 7. `tests/test_original_txt.py` (unit, §10). `parsear_estructura` sobre el `.txt` de ejemplo
      (puede usarse el real `storage/raw/*enc_01_original.txt` o un fixture embebido): captura
      `titulo_instrumento`, 6 secciones, 21 ítems en orden. `construir_mapa_dimension`: mapeo
      posicional correcto con la colisión `Habilidades_par` resuelta por posición; conteo desigual
      ⇒ `{}`; **orden no monotónico ⇒ `{}`** (§15.1); fallback por prefijo con mojibake reparado
      (incluye caso cp850 real) y etiqueta "(agrupación aproximada)". `ruta_original`: con
      `raw_archivo_original="raw/x_original.txt"` resuelve bajo `storage/`, con
      `"storage/raw/x_original.txt"` resuelve bajo `PROJECT_ROOT`; ambas con un `.txt` temporal y la
      consulta a `RawData` **mockeada** (monkeypatch del engine/Session). `leer_texto_original`:
      `.txt` ilegible ⇒ `None` (sin `\ufffd`).
      Files: `services/visualization-service/tests/test_original_txt.py`
      Verify: `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests\test_original_txt.py -q` pasa.

- [ ] 8. `tests/test_sources_chunks.py` (unit, §10). Con un artefacto sintético: verificar nº y
      `clase_chunk` de los chunks y que la degradación (sin `.txt`, sin `respondents`) produce la
      combinación esperada; que un `ChunkIndexable` sobredimensionado se expande con `ids`/
      `chunk_index` únicos (§6.4). `extraer_metadata`: nueva precedencia de título
      (`dc:title` presente gana; con `dc:title` vacío y `titulo_override` del `.txt` gana el `.txt`;
      sin ninguno cae a `instrument.title` y luego a `f"Instrumento {id}"`) — **actualizar/añadir**
      cualquier aserción que antes fijara el nombre del CSV como título (§15.2 punto 3).
      Files: `services/visualization-service/tests/test_sources_chunks.py`
      Verify: `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests\test_sources_chunks.py -q` pasa.

- [ ] 9. `tests/test_rag_index.py` (integración ligera, §10). `POST /rag/index` sobre el
      `storage/raw/*inst_1.estandarizado.v1.json` real (resolución por fallback disco), mockeando
      embeddings y Chroma (monkeypatch de `embeddings.embed_texts` y `chroma_client.*` según el
      patrón de TestClient + `dependency_overrides`/monkeypatch del repo). Afirmar: los `documents`
      indexados contienen prosa con medias/porcentajes y nombres de dimensión reales (no mojibake
      ni números sueltos); cada metadata lleva las claves existentes **más** `clase_chunk` y
      `dimension`; el contrato de respuesta (`IndexResponse`) no cambió. Verificar también la
      numeración única de `chunk_index`/`id` sobre la lista aplanada.
      Files: `services/visualization-service/tests/test_rag_index.py`
      Verify: `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests\test_rag_index.py -q` pasa.

## Verificación final (integración entre piezas)

- [ ] 10. Ejecutar toda la suite del servicio y la compilación de humo.
      Files: (ninguno; verificación)
      Verify: `.\.venv\Scripts\python.exe -m pytest services\visualization-service\tests -q` pasa en verde y
      `.\.venv\Scripts\python.exe -m compileall services\visualization-service\app` sin errores.

## Notas de alcance (§13) — lo que NO se toca

`chunking.py`, `ollama_client.py` (ya con `keep_alive='-1m'`), `prompt.py`, `chroma_client.py`,
`embeddings.py`, los schemas (`app/schemas/rag.py`), el contrato HTTP de `/rag/index` y
`/rag/chat`, las claves de metadata existentes, y `requirements.txt` (no se añaden ni cambian
dependencias; el aviso de numpy 2.x queda documentado pero fuera de alcance). No se corrige
`sources._resolver_fallback_raw` (§13).
