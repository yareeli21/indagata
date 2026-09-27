# Arquitectura del Survey Intelligent System (SIS)

> **Qué es este documento:** cómo está organizado el SIS **hoy** (verificado en código), tras la
> refactorización a una capa de estrategia por instrumento. Es un solo sistema con un único
> orquestador y tres estrategias (encuesta, entrevista, prueba estandarizada).
> **Para extenderlo** (agregar reglas de entrevista o de prueba estandarizada): ver
> `GUIA_EXTENSION_INSTRUMENTOS.md`.
> **Qué hace cada etapa en detalle:** ver `ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md`.

---

## 1. Principio rector: un solo SIS, estrategias por instrumento

El SIS es un **servicio de dominio** (hexagonal, aislado del framework). Recibe un instrumento
y produce conocimiento estructurado. Hay **un único punto de entrada** —
`SurveyIntelligenceService.process()` en `facade.py`— que selecciona una **estrategia** según el
tipo de instrumento y le delega solo lo que cambia. El resto es tronco común compartido.

- No hay tres servicios ni tres SIS: hay un facade + tres estrategias intercambiables.
- Las estrategias **componen** los stages existentes; no reimplementan su lógica.
- El contrato de salida (`SurveyIntelligenceResult`) es único y multi-instrumento (tiene caras
  opcionales: `interview_analysis` hoy; `psychometric_analysis` en el futuro).

---

## 2. Mapa de carpetas

```
survey_intelligence/
├── facade.py                # ORQUESTADOR único: process(). Selecciona pipeline + tronco común.
├── pipelines/               # ESTRATEGIA POR INSTRUMENTO (lo que diverge)
│   ├── base.py              # Protocolo InstrumentPipeline + PipelineDeps/CanonicalBuild/InstrumentAnalysis/PipelineError
│   ├── _document.py         # build_canonical documental compartido (entrevista + prueba)
│   ├── encuesta.py          # EncuestaPipeline (tabular)
│   ├── entrevista.py        # EntrevistaPipeline (documento + S10)
│   ├── prueba_estandarizada.py  # PruebaEstandarizadaPipeline (esqueleto, sin reglas aún)
│   └── __init__.py          # select_pipeline(instrument_type)
├── pipeline/stages/         # ETAPAS (S1..S10). Reusadas por las estrategias y el tronco común.
├── engine/                  # MOTORES determinísticos y prompts
│   ├── readers/             # csv/xlsx/raw_table/header_utils/codebook_reader  (tabular + codebook)
│   ├── profiling/           # scale_detector, stats, matrix_parser, name_normalizer, edit_distance
│   ├── heuristics/          # platform_columns, context_sufficiency, column_proposals
│   ├── spss/                # spss_mapper, spss_validator
│   ├── transforms/          # apply_engine, drop_columns, normalize_scale, registry
│   ├── nlp/                 # diarization, interview_prompt  (entrevistas)
│   ├── prompts/             # audit/enrichment/kpi/results prompts
│   ├── parsing/             # robust_json (común)
│   ├── question_typing.py / question_grouping.py / respondent_templates.py  (encuesta v2)
├── contracts/               # CONTRATOS (Pydantic frozen)
│   ├── request.py, result.py, enums.py        # comunes / entrada / salida
│   ├── canonical.py, spss.py, results.py, enriched.py, codebook.py, kpi.py, improvement.py  # encuesta
│   └── interview.py                            # entrevista
├── ports/                   # llm, clock, ids, telemetry (inyección de dependencias)
├── export/                  # sav_writer (.SAV, encuestas)
├── tests/                   # suite (run_all); red de seguridad. NO borrar.
├── host_toolkit.py, versioning.py, __init__.py
└── docs/                    # esta documentación
```

---

## 3. Contrato entre el facade y las estrategias

Definido en `pipelines/base.py`. Cada estrategia implementa dos métodos:

| Método | Qué hace | Encuesta | Entrevista | Prueba |
|---|---|---|---|---|
| `build_canonical(request, deps, emit)` | Construye el `CanonicalSurveyModel` y emite `ingestion`/`canonical`/`profiling` | S1+S2+S3 (tabular) | documental (S1 valida texto, S2 doc, S3 skip) | documental |
| `analyze(request, canonical, build, spss_by_id, deps, emit)` | Análisis específico del instrumento; nunca lanza (degrada) | S8b (v1/v2) | S10 interview | — (esqueleto) |

Tipos de apoyo:
- `PipelineDeps`: subconjunto de dependencias que las estrategias necesitan (`llm`, `clock`, `ids`).
- `CanonicalBuild`: resultado de `build_canonical` (`canonical`, y opcionalmente `ingestion` para la
  vía tabular o `document_text` para la documental).
- `InstrumentAnalysis`: cara de conocimiento específica (aditiva) — `results_findings`,
  `interview_analysis`, `llm_calls`, `degraded`. El facade la fusiona en el resultado.
- `PipelineError`: fallo fatal en la construcción del canónico (equivale a S1/S2 fatales). El facade
  lo traduce a `status=failed` con diagnóstico, sin lanzar al host.

El `emit` lo provee el facade: las estrategias reportan sus etapas con los MISMOS nombres/estados
que antes, para no romper el contrato de diagnósticos ni los tests.

---

## 4. El tronco común (en el facade, no se duplica)

Tras `build_canonical` y antes de `analyze`, el facade ejecuta para TODOS los instrumentos:

- **S4** suficiencia de contexto (determinística).
- **S5** resolución determinística de codebook (sin RAG; ver `DESIGN_CODEBOOK_DETERMINISTA.md`).
- **SPSS** determinístico (`build_spss_dictionary`) — base del enriquecimiento.
- **S6** auditoría metodológica (LLM, degradable).
- **S7** enriquecimiento semántico + validador anti-invención (LLM, degradable).
- **S7b** inferencia de KPIs contra el catálogo del host (LLM, degradable).

Y tras `analyze`:

- **S9** ensamblado del `EnrichedSurveyModel`.
- **S8** gap analysis + propuestas de transformación.

Garantías transversales: degradación graciosa (S1/S2 fatales, resto degradable), el SIS nunca lanza
al host, todo lo determinístico es reproducible, y cada etapa emite un diagnóstico
(`ok`/`skipped`/`degraded`/`failed`).

---

## 5. Estado de madurez por instrumento

| Instrumento | build_canonical | analyze | Estado |
|---|---|---|---|
| **Encuesta** | tabular (S1+S2+S3) | S8b + perfiles de respondente | **Completo** |
| **Entrevista** | documental | S10 (diarización + temas/hallazgos NLP) | **Implementado** |
| **Prueba estandarizada** | documental | — (esqueleto, sin reglas) | **Pendiente de diseñar** |

Hoy una prueba estandarizada se **ingiere como texto** (canónico documental mínimo) y recorre el
tronco común, pero **no tiene interpretación psicométrica**. Ese es el hueco a llenar; ver la guía
de extensión. La entrevista es la plantilla a seguir: una estrategia documental con su propia cara
de conocimiento (`contracts/interview.py`) y su motor (`engine/nlp/`).

---

## 6. Relación con el host

El host (`api/`) invoca al SIS a través de `services/sis_adapter.py` (`build_request` +
`service.process`). El host:

- Fija el `instrument_type` en el upload y extrae el texto de los documentos (entrevista/prueba)
  antes de llamar al SIS.
- Cachea el resultado del SIS y **genera el JSON consolidado** (`carga_artifacts._generar_json_consolidado`),
  que es el insumo del RAG principal. El consolidado es responsabilidad del host, no del SIS.

El **RAG principal** (chunking, embeddings, índice, Q&A) es un componente separado que **consume**
el consolidado. No vive dentro del SIS.

---

## 7. Verificación

Toda modificación del SIS se valida con:

```
python -m survey_intelligence.tests.run_all       # suite completa (cada módulo expone _run())
```

y el arranque de la app (host) con un `TestClient` → `/` == 200. La carpeta `tests/` es la red de
seguridad del sistema; no se borra.
