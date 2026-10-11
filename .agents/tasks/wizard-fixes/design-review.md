# Revisión de diseño — Etapa de estandarización + 5 fixes del wizard (Indagata)

Documento revisado: `.agents/tasks/wizard-fixes/design.md` (Revisión 3).
Contexto: `.agents/tasks/wizard-fixes/findings.md`. Esquema de referencia: `storage/raw/inst_01.v1.json`.
Revisión realizada **en frío**, verificando cada supuesto contra el código real (archivo:símbolo).

Veredicto mecánico: **CHANGES_REQUESTED** — 1 hallazgo MEDIUM, 0 HIGH, 3 NIT.
(Regla: cualquier HIGH/MEDIUM bloquea; los NIT no bloquean por sí solos.)

---

## Hallazgos

### 1. [MEDIUM] El enriquecimiento de `survey_specific` para el summary solo cubre el tipo ENCUESTA; entrevista y prueba quedan sin sus campos clave

**Dónde:** §1.4bis y §6.2 del diseño (helper `enriquecerJson` y la lista de campos a copiar a
`metadata.survey_specific`).

**Problema:** El diseño cierra el Hallazgo 1 de la revisión 2 (DC + `survey_specific` deben llegar al
summary) **solo para encuestas**. Ambas secciones enumeran exclusivamente los campos de encuesta
(`constructo_principal`, `dimensiones`, `palabras_clave`, `carrera`, `notas_contextuales`,
`notas_interpretacion`) y los describen como "los que `metadata_extractor` lee para el summary". Pero
`metadata_extractor` lee **conjuntos distintos por tipo** (verificado en
`services/analysis-service/app/vectorization/config/constants.py:CAMPOS_ESPECIFICOS_POR_TIPO`):

```python
ENCUESTA:             ("carrera", "notas_contextuales", "notas_interpretacion",
                       "constructo_principal", "dimensiones", "palabras_clave")
ENTREVISTA:           ("objetivo", "metodologia")
PRUEBA_ESTANDARIZADA: ("unidad_de_aprendizaje", "taxonomia_bloom",
                       "objetivo_de_evaluacion", "competencias")
```

Para un instrumento de tipo **entrevista** o **prueba**, el `surveyEspecifico` que el cliente copia a
`metadata.survey_specific` antes de `proponerKpis` **no incluye** `objetivo`/`metodologia` (entrevista) ni
`unidad_de_aprendizaje`/`taxonomia_bloom`/`objetivo_de_evaluacion`/`competencias` (prueba). Resultado:
`metadata_extractor.extract_key_metadata` no encuentra esos campos, el summary de entrevistas/pruebas se
construye **solo con Dublin Core** (sin los metadatos específicos del tipo), y las propuestas de KPI para
esos tipos se degradan — exactamente el problema que el Hallazgo 1 de la revisión 2 pretendía cerrar, pero
cerrado únicamente para encuestas. El paso 4 (§6.2) sí persiste esos campos en las tablas
`metadatos_enriquecidos_entrevistas`/`_pruebas`, pero NO los reenvía al JSON del summary.

**Fix concreto:** hacer que `surveyEspecifico` dependa del `tipo` del instrumento y copie el conjunto de
claves que `metadata_extractor` lee para ESE tipo. En §1.4bis/§6.2, reemplazar la lista fija por un mapeo
alineado a `CAMPOS_ESPECIFICOS_POR_TIPO`:

```ts
// UploadWizard.tsx — claves de survey_specific por tipo (espejo de CAMPOS_ESPECIFICOS_POR_TIPO)
const CLAVES_SURVEY_POR_TIPO: Record<TipoInstrumento, string[]> = {
  Encuesta: ["carrera", "notas_contextuales", "notas_interpretacion",
             "constructo_principal", "dimensiones", "palabras_clave"],
  Entrevista: ["objetivo", "metodologia"],
  "Prueba estandarizada": ["unidad_de_aprendizaje", "taxonomia_bloom",
                           "objetivo_de_evaluacion", "competencias"],
};
// surveyEspecifico = subconjunto de `meta` (paso 4) filtrado por CLAVES_SURVEY_POR_TIPO[tipo]
```

y actualizar §1.4bis para dejar escrito que el conjunto de claves de `survey_specific` **varía por tipo**,
citando `CAMPOS_ESPECIFICOS_POR_TIPO`. (`carrera` para encuesta ya es tolerado por `_resolver_carrera`, que
cae a respondents/poblacion_objetivo; mantener su envío.)

---

### 2. [NIT] El paso "Tipos de pregunta" (§7, `StepTiposPregunta`) no especifica el comportamiento para instrumentos de tipo documento (entrevista/prueba)

**Dónde:** §1.4 (documentos → una sola `question` `abierta` con el texto completo), §1.6(A)
(`PreviewResponse.preguntas`) y §7 (nuevo paso 2 con `StepTiposPregunta`).

**Problema:** Para instrumentos documento, el preview devuelve **una sola** pregunta `abierta` cuyo `text`
es el documento completo (potencialmente miles de caracteres). El diseño no dice qué muestra ni qué puede
confirmar/corregir el investigador en `StepTiposPregunta` para ese caso: un `<select>` de tipo sobre una
única "pregunta" gigante no aporta valor y puede romper la UI (texto enorme en una celda de tabla). No es
un error de contrato (el flujo no se rompe), pero el comportamiento del paso para documentos queda
indefinido.

**Fix concreto:** en §7, especificar que cuando `tipo_instrumento ∈ {entrevista, prueba_estandarizada}` (o
`preguntas.length === 1 && preguntas[0].type === "abierta"` con `es_demografica=false`), `StepTiposPregunta`
muestra un estado informativo ("Documento: se tratará como texto abierto; no hay tipos de pregunta que
confirmar") y deja avanzar sin edición. Truncar el `text` mostrado (p. ej. 300 chars + "…") en la UI,
conservando el texto completo en el estado que se envía a `/estandarizar`.

---

### 3. [NIT] Posible doble fuente de `n_respondentes` (preview detectado vs. captura del paso 4) sin regla de reconciliación

**Dónde:** §1.6(A) (`n_respondentes_detectados` = filas de datos) y §6.2 (campo `n_respondentes` capturado
por el usuario en `StepMetadatosTipo` para encuestas).

**Problema:** El sistema deriva `n_respondentes_detectados` del número de filas en el preview, y además pide
`n_respondentes` como input del usuario en el paso 4, que se persiste en
`metadatos_enriquecidos_encuestas.n_respondentes`. No hay regla sobre qué pasa si el usuario captura un
valor distinto del detectado (ni se pre-rellena con el detectado). Riesgo bajo: inconsistencia silenciosa
entre el conteo real de respondentes del JSON (`respondents[]`) y el metadato declarado.

**Fix concreto:** pre-rellenar el campo `n_respondentes` del paso 4 con `n_respondentes_detectados` del
preview (editable), y añadir una nota en §6.2 de que el valor por defecto proviene de la detección. No es
necesario validar la igualdad; basta con eliminar la ambigüedad de origen.

---

### 4. [NIT] `enriquecerJson` omite `dc:rights`/`dc:source`/`dc:relation` del bloque DC del summary (documentar que es intencional)

**Dónde:** §1.4bis (helper `enriquecerJson`).

**Problema:** `enriquecerJson` solo escribe `dc:title`, `dc:subject`, `dc:description`, `dc:coverage` en
`metadata.dublin_core`. Esto es **correcto** (verificado: `DUBLIN_CORE_KEYS` en `constants.py` son esas
cuatro, y el extractor ignora el resto), pero el diseño no lo dice explícitamente, lo que puede llevar al
implementador a "completar" los otros DC pensando que falta algo. Es coherencia editorial, no un defecto
de contrato.

**Fix concreto:** añadir una línea en §1.4bis: "Se omiten deliberadamente `dc:rights`/`dc:source`/
`dc:relation` del enriquecimiento del summary porque `DUBLIN_CORE_KEYS` (constants.py) solo contiene
`dc:title/dc:subject/dc:description/dc:coverage`; esos campos sí se persisten vía el registro DC del paso 3."

---

## Supuestos verificados (coinciden con el código real)

1. **Bug 5 — `_slug_por_id_crudo` ya consulta `_seed_map.json` primero.** Verificado en
   `instrument-service/app/services/instrumento_query.py`: el fallback directo es exactamente
   `if id_crudo >= 1: return f"inst_{id_crudo:02d}"`. El fix (eliminar esas dos líneas, conservar la
   consulta al seed map) es correcto y mínimo.
2. **Ruteo del gateway por prefijos explícitos.** Verificado en `api-gateway/proxy/proxy.py`: solo
   `/instrumentos/*`, `/almacenamiento/*`, `/rag/*`, `/api/metadata/*`, `/api/enrichment/*` tienen handler;
   `analysis-service` no se proxea. `POST /api/metadata/{id}/especificos` cae bajo `/api/metadata/{path:path}`
   y se reenvía AS-IS. Un `/api/especificos` daría 404 (como señala el diseño).
3. **Doble segmento de la ruta DC.** Verificado en `metadata-service/routers/metadata.py`:
   `APIRouter(prefix="/metadata")` + `@router.post("/metadata/{instrumento_id}")` → montado con
   `prefix="/api"` da `/api/metadata/metadata/{id}`. La ruta nueva `/{id}/especificos` no colisiona (sufijo
   literal distinto).
4. **`main.py` de metadata-service.** Verificado: importa `health, metadata, enrichment` y los registra con
   `health` sin prefijo, `metadata`/`enrichment` con `prefix="/api"`. El bloque descrito en §6.1 coincide.
5. **503 de `ProposalService.propose`.** Verificado en
   `analysis-service/app/vectorization/services/proposal_service.py`: lanza
   `HTTP_503_SERVICE_UNAVAILABLE` ante fallo de Chroma/embeddings y `422` ante JSON/summary inválidos. El
   manejo diferenciado del `catch` (§4) es correcto.
6. **Estado React y flujo de `jsonInstrumento`.** Verificado en `UploadWizard.tsx`: `jsonInstrumento` es
   `useState`, la guarda actual es `if (!jsonInstrumento || !archivoOriginal) { setSugeridos([]); return; }`,
   el `.catch(() => setSugeridos([]))` silencia errores, y `confirmarKpis({..., jsonInstrumento})` lo consume
   en `guardar()`. La regla de inmutabilidad (copia nueva + `setJsonInstrumento`) resuelve el riesgo real.
7. **DC: 7 campos de usuario incluidos `dc_source`/`dc_relation`.** Verificado en
   `metadata-service/routers/metadata.py` (docstring) y `01_schema.sql` (`metadatos_dc` tiene `dc_source`,
   `dc_relation`). El wizard hoy no envía esos dos (verificado en `UploadWizard.tsx` bloque `paso === 2`).
8. **`dc_rights` es `VARCHAR(255)` y `StepDublinCore` ya usa `maxLength={120}`.** Ambos verificados
   (`01_schema.sql:101`; `StepDublinCore.tsx` input `derechos`). El diseño corrige bien el NIT previo (no
   aflojar a 255).
9. **Tablas `metadatos_enriquecidos_*` existen con las columnas exactas de §6.1.** Verificado en
   `01_schema.sql`: las 3 tablas y sus columnas (incluidos los `JSONB` `palabras_clave`, `dimensiones`,
   `mapeo_de_reactivos_por_seccion`) coinciden columna por columna con los modelos SQLAlchemy propuestos.
   No se altera el SQL (ya tienen `IF NOT EXISTS`); los modelos solo las reflejan → cambio no destructivo.
10. **`estandarizado` ya es estado válido y mapeado.** Verificado: `CheckConstraint` de
    `shared/models/instrumento_procesado.py` incluye `'estandarizado'`, existe `ruta_json` (Text), y
    `map_instrumento._ESTADO_MAP["estandarizado"] = "Estandarizado"`. El avance de estado es no destructivo.
11. **Vectorización usa solo texto de preguntas + metadatos, nunca el `type`.** Verificado:
    `summary_builder.build_summary` recibe `metadatos` + `instrumento_original` (texto);
    `metadata_extractor.extract_key_metadata` lee `metadata.dublin_core` + `metadata.survey_specific` +
    `respondents[].demographics`, nunca `questions[].type`. La regla §2 se cumple y se preserva.
12. **`DUBLIN_CORE_KEYS`** = `dc:title, dc:subject, dc:description, dc:coverage` (verificado). El
    enriquecimiento cliente escribe esas claves `dc:`.
13. **`proponerKpis` (carga.ts)** envía `archivo_json` (`application/json`) + `instrumento_original`
    (`text/markdown`) + `tipo_instrumento` + `id_instrumento` (verificado), confirmando el riesgo de enviar
    un binario como `text/markdown` (Hallazgo 3 rev 3, correctamente mitigado restringiendo `accept`).
14. **`StepArchivo` acepta hoy `.txt,.pdf,.docx` para el original** (verificado); el diseño pide
    restringir a `.md,.txt`, coherente con que el original viaja como `text/markdown`.
15. **`ExtractedDocument.text`** es el texto plano completo (verificado en `document_parser.py`); usar
    `read_document(...).text` (no el preview truncado) es correcto. `read_document` soporta `.pdf/.txt/.docx`.
16. **`TipoInstrumento`** del analysis-service = `encuesta/entrevista/prueba_estandarizada` (verificado),
    coherente con §1.6(A) y con `raw_data.tipo_instrumento`.
17. **Permanecer en `elotro-back` sin push.** El diseño lo declara en el encabezado y en §9; esta revisión
    no modifica código ni toca git.

## Supuestos no verificados / pendientes (declarados por el propio diseño, no bloqueantes)

- **`document_parser` no segmenta** (base del MVP "documento = una sola pregunta abierta"): el diseño lo
  afirma desde `findings.md` y pide releer el parser antes de implementar §1.4. No contradice lo verificado
  (la clase `ExtractedDocument` entrega un único `text`), pero la ausencia de segmentación no se verificó
  línea por línea en esta revisión.
- **`tabular_parser.normalize_cell`** (base de la heurística del detector §1.3): citado en `findings.md`;
  el diseño pide releerlo antes de codificar `type_detector.py`. No verificado aquí en detalle; no bloquea
  el diseño.
- **Comportamiento exacto de `_resolver_por_ruta_json` con rutas con prefijo `storage/`** (§1.5): se
  verificó que resuelve `settings.PROJECT_ROOT / ruta_json`; el invariante de persistir la ruta relativa
  con prefijo `storage/` es correcto por construcción, pero depende de que `standardization_service`
  componga la ruta como se describe (test unitario propuesto en §8, correcto).
