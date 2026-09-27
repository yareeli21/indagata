# Codebooks: de RAG a Extracción Determinística — Análisis y Arquitectura Objetivo

> **Estado:** Diseño + estado de implementación. La resolución determinística está VIVA y los
> residuos del RAG de codebooks fueron RETIRADOS (ver §1-§3). El **RAG principal** (del sistema,
> para consulta de instrumentos ya procesados) NO se toca y se trabaja aparte, fuera del SIS.
> **Decisión de negocio:** los codebooks son diccionarios estructurados; se resuelven por
> extracción estructurada + coincidencia determinística en cascada, sin embeddings ni vector store.

---

## 0. Estado actual (leer primero)

La arquitectura determinística de codebooks está **implementada y verificada**, y los residuos del
RAG de codebooks **ya fueron retirados** del código. El "RAG vectorial para codebooks" nunca llegó a
implementarse — solo existió en documentación y un puerto no-op que ya se eliminó.

Lo que YA existe y hace exactamente lo pedido:
- `contracts/codebook.py` → `CodebookModel` / `CodebookEntry`: el **modelo interno unificado**
  (`name`, `label`, `value_labels`, `data_type`, `missing_values`) con búsqueda tolerante `O(1)`
  (normaliza minúsculas/acentos/snake_case). Coincide 1:1 con el ejemplo de tu solicitud.
- `engine/readers/codebook_reader.py` → `read_codebook()`: convierte codebooks a `CodebookModel`.
- `pipeline/stages/s5_codebook_resolution.py` → `resolve_codebook()`: **resolución determinística
  O(1)**, sin embeddings ni vector store. Su docstring dice literalmente *"Sustituye la aproximación
  RAG vectorial por coincidencia exacta y normalizada O(1)"*.
- `facade.py` (S5) **ya llama** a `resolve_codebook(canonical, verdicts, request.codebook)`.
- El viejo `s5_rag_retrieval.py` **ya no existe** (fue reemplazado).
- 7 tests en `tests/test_codebook_resolution.py` cubren lectura CSV/JSON/texto, lookup tolerante y resolución.

**Conclusión:** la "migración RAG→determinístico" para codebooks está **completa**. Los residuos
(puerto RAG, `SourceDocument`, `rag_sources`, `run_rag`, `EmbeddingPort`) fueron **retirados**. Lo
único opcional que queda es **ampliar formatos** (SAV/DOCX) y propagar etiquetas legibles al
consolidado. Formatos soportados hoy por `read_codebook`: **CSV/TSV, XLSX/XLS, JSON, TXT, PDF**.

---

## 1. Componentes relacionados con "RAG para codebooks"

| Componente | ¿Qué es hoy? | Acción |
|---|---|---|
| `s5_codebook_resolution.resolve_codebook` | Resolución **determinística** O(1) (ya es lo objetivo) | **Conservar** |
| `contracts/codebook.py` (CodebookModel/Entry) | Modelo interno unificado (ya es lo objetivo) | **Conservar** |
| `engine/readers/codebook_reader.read_codebook` | Extractor a estructura (CSV/JSON/texto) | **Conservar / ampliar formatos** |
| `ports/rag_port.py` (`RagRetrieverPort`, `NullRagRetriever`, `RetrievedChunk`) | Puerto RAG + Null Object | ✅ **RETIRADO** (archivo eliminado) |
| `ports/embedding_port.py` (`EmbeddingPort`) | Puerto de embeddings sin consumidor | ✅ **RETIRADO** (archivo eliminado) |
| `facade` `self._rag` / parámetro `rag_retriever` | Puerto RAG inyectado; ya no lo consumía S5 | ✅ **RETIRADO** |
| `SourceDocument` / `SourceKind` (contracts) | Contrato de fuente documental RAG | ✅ **RETIRADO** |
| `IngestionOptions.run_rag` / `request.rag_sources` | Banderas/campo del S5-RAG | ✅ **RETIRADO** |
| Docs que decían "RAG para codebooks" | Desactualizados | ✅ **Alineados** |

> Decisión tomada por el usuario: los puertos RAG/embedding se retiran del SIS; el RAG principal se
> trabaja **aparte, fuera del SIS**. Por eso no se conservan aquí.

---

## 2. Retiro de residuos RAG (COMPLETADO)

Se eliminaron del SIS los componentes del RAG de codebooks, sin cambiar el comportamiento
determinístico (suite verde + arranque 200 tras el retiro):

- **Eliminados:** `ports/rag_port.py` (`RagRetrieverPort`/`NullRagRetriever`/`RetrievedChunk`) y
  `ports/embedding_port.py` (`EmbeddingPort`); sus exports en `ports/__init__.py`.
- **`facade.py`:** sin el parámetro `rag_retriever` ni `self._rag`.
- **`contracts/request.py`:** sin `SourceDocument`, `rag_sources` ni `run_rag`;
  **`contracts/enums.py`:** sin `SourceKind`. Exports limpiados en los `__init__`.
- **Host:** `sis_adapter.build_request` construye el `CodebookModel` (`read_codebook`) y lo pasa en
  `request.codebook`; los docstrings de `services_carga.py` y `routers_carga.py` ya dicen "codebook
  determinístico", no "RAG".

La cadena host↔SIS quedó verificada de punta a punta: `build_request` → `request.codebook` →
`facade` S5 `resolve_codebook`. Un smoke (CSV `P01_1 → "Parentesco…"` con `value_labels`) confirma
S5 con `skipped=False`, reescritura del `raw_header`, enriquecimiento de `detected_scale.labels` y
verdicts `is_interpretable=True`.

---

## 3. Formatos y validación (estado actual)

- **`read_codebook`** soporta: CSV/TSV, XLSX/XLS (pandas), JSON, TXT (clave-valor) y **PDF**
  (extracción de texto con PyPDF2→pdfplumber). Pendiente opcional: SAV, DOCX.
- **Validación de entrada (host):** el codebook (solo encuestas) admite `.csv` o `.pdf`
  (`ArchivoService.validar_formato_codebook`). Las encuestas de entrada son `.csv`/`.xlsx`.

---

## 4. Arquitectura objetivo (extracción estructurada)

```
Codebook (CSV/XLSX/SAV/PDF/DOCX)
   ↓  Extractor de Codebook (read_codebook, ampliado a más formatos)
CodebookModel (estructura unificada, en memoria)
   ↓  (host lo pasa en request.codebook)
SIS · S5 resolve_codebook (cascada determinística)
   ↓
Canónico enriquecido (label, value_labels, tipo por variable)
   ↓
JSON Consolidado (hallazgos con etiquetas legibles)
```

### Estrategia de resolución en CASCADA (tu diseño, mapeado a lo existente)
- **Nivel 1 — Diccionario estructurado (principal):** `CodebookModel.lookup(name)` O(1) por
  `raw_header`/`normalized_name`. **Ya implementado.**
- **Nivel 2 — Búsqueda léxica exacta:** si no hay entrada estructurada, buscar el identificador como
  **texto exacto** dentro del documento del codebook (sin embeddings). **A añadir** (hoy S5 hace solo Nivel 1).
- **Nivel 3 — LLM excepcional, una sola vez:** solo si el documento es tan irregular que no se puede
  estructurar; el LLM ayuda **durante la extracción inicial** del codebook, NUNCA variable por variable
  ni dentro del pipeline de encuesta. **A añadir en el extractor**, como fallback opcional y acotado.

---

## 5. Modelo interno de representación (ya existe; se confirma)

```python
# contracts/codebook.py (actual)
CodebookEntry: { name, label, value_labels: {code: label}, data_type?, missing_values[] }
CodebookModel: { entries: {name: CodebookEntry} } + lookup() tolerante O(1)
```
Coincide con el ejemplo de tu solicitud:
```json
{ "P01_1": { "label": "Parentesco con el jefe del hogar",
             "value_labels": { "1": "Jefe(a)", "2": "Cónyuge", "3": "Hijo(a)" } } }
```
No requiere rediseño; a lo sumo añadir campos opcionales (p. ej. `question_text` vs `label`) si hiciera falta.

---

## 6. Integración con el pipeline de encuestas

Ya está integrada en S5 (`resolve_codebook`), que:
1. Por cada variable, busca en el `CodebookModel` por `raw_header`/`normalized_name`.
2. Si coincide: marca la variable **INTERPRETABLE**, actualiza el texto de la pregunta con la
   `label` del codebook, y enriquece `DetectedScale` con las `value_labels` (para SPSS y etapas siguientes).
3. Sin codebook o sin coincidencias: opera limpio (skipped), sin romper nada.

**Estado de las mejoras (no son gaps de integración):**
- (a) ✅ **RESUELTO/VERIFICADO**: el host construye el `CodebookModel` (con `read_codebook`) y lo pasa
  en `request.codebook`; S5 lo resuelve (smoke end-to-end: `skipped=False`).
- (b) Formatos: `read_codebook` cubre **CSV/TSV, XLSX/XLS, JSON, TXT y PDF**; pendiente opcional **SAV, DOCX**.
- (c) **Pendiente**: que el **JSON consolidado** use la etiqueta legible (`"Parentesco… = Cónyuge"`
  en vez de `"P01_1 = 2"`), mapeando `value` → `value_labels[value]` al construir
  `por_pregunta`/`por_respondente` cuando hay codebook.

---

## 7. JSON canónico y consolidado con codebook

- **Canónico** (por variable resuelta): `raw_header` (nombre original), `text`/label descriptiva,
  tipo, categorías y `value_labels`, más los metadatos disponibles del codebook. S5 ya inyecta label y
  value_labels; el resto es aditivo.
- **Consolidado**: los hallazgos y perfiles deben mostrar **etiquetas**, no códigos. Ejemplo objetivo:
  `"Parentesco con el jefe del hogar = Cónyuge"`. Esto se logra mapeando `value` → `value_labels[value]`
  al construir `por_pregunta`/`por_respondente` cuando hay codebook.

---

## 8. Estado de la migración RAG → determinístico

| Paso | Estado |
|---|---|
| Motor determinístico (`read_codebook` + `resolve_codebook`) | ✅ Implementado |
| Integración host↔SIS (`request.codebook`) | ✅ Verificada (smoke end-to-end) |
| Retiro de residuos RAG (puertos, `SourceDocument`, `rag_sources`, `run_rag`) | ✅ Hecho |
| Documentación alineada | ✅ Hecho |
| Formatos CSV/TSV, XLSX/XLS, JSON, TXT, PDF | ✅ Soportados |
| Formatos SAV, DOCX | ⏳ Opcional pendiente |
| Nivel 2 (léxico exacto en el documento) | ⏳ Pendiente (hoy S5 hace Nivel 1) |
| Nivel 3 (LLM único en extracción, excepcional) | ⏳ Pendiente / a evaluar |
| Consolidado con etiquetas legibles (`value_labels`) | ⏳ Pendiente |

**Sin ruptura:** S5 opera "skipped" sin codebook, así que las encuestas sin codebook no cambian.
El RAG principal no se toca en ningún punto y se trabaja fuera del SIS.

---

## 9. Pendientes (mejoras, no bloqueantes)

1. Ampliar formatos: **SAV** (pyreadstat) y **DOCX** (python-docx) en `read_codebook`.
2. Propagar `value_labels` al consolidado para etiquetas legibles.
3. Evaluar Nivel 2 (búsqueda léxica exacta) y Nivel 3 (LLM único en extracción) si aparecen
   codebooks demasiado irregulares para la extracción estructurada.

---

## 10. Alcance

La resolución determinística de codebooks está **viva y verificada**, y los residuos del RAG de
codebooks fueron **retirados**. Formatos soportados: CSV/TSV, XLSX/XLS, JSON, TXT, PDF. Los pendientes
de §9 son mejoras opcionales, no gaps de integración. El RAG principal permanece fuera del SIS.
