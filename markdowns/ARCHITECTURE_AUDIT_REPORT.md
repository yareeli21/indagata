# ARCHITECTURE AUDIT REPORT — Backend Indagata (v2, reevaluado con contexto de negocio)

> **Modo:** Auditoría de solo lectura. No se ha modificado, eliminado ni renombrado ningún archivo. No se ha generado código.
> **Alcance:** `backend/` completo (capa `api/`, `services/` raíz y módulo `survey_intelligence/`).
> **Versión:** 2.0 — reevaluación completa tras las aclaraciones de negocio y arquitectura del propietario.
> **Fecha:** 2026-09-20
> **Regla rectora de esta versión:** las aclaraciones de negocio **tienen prioridad** sobre cualquier recomendación previa que implicara eliminación, simplificación o reorganización. Todo componente ligado a una funcionalidad futura planificada se reclasifica como **"Funcionalidad futura planificada"**, no como código muerto ni deuda técnica.

---

## Nota de versión: qué cambió respecto a la v1

La v1 de este reporte trató varias piezas como "código muerto" o "deuda técnica" por falta de integración visible. Con el contexto de negocio ahora sé que muchas de esas piezas son **puntos de extensión deliberados** para funcionalidades ya planificadas (JWT, RAG de codebooks, módulo unificado de extracción, pipelines de entrevistas y pruebas estandarizadas).

Esta versión introduce una **taxonomía de tres categorías** y reclasifica cada hallazgo dentro de ella. También añade la **arquitectura objetivo del SIS**, la **evolución de los JSON canónico y consolidado** por tipo de instrumento, y un **roadmap actualizado**.

### Taxonomía adoptada (obligatoria en todo el reporte)

| Categoría | Definición | Acción permitida |
|---|---|---|
| **Código obsoleto** | Reemplazado por una implementación viva; ya no representa el diseño objetivo. | Puede deprecarse/retirarse con verificación. |
| **Código muerto** | Sin consumidores, sin plan de uso, sin valor de referencia. | Candidato a revisión (nunca eliminación automática). |
| **Funcionalidad futura planificada** | Incompleto o comentado **a propósito** porque habilita un roadmap conocido. | **Conservar**: interfaces, puntos de extensión y componentes relacionados. |

---

# Resumen Ejecutivo

El backend de Indagata es una API FastAPI cuyo núcleo de dominio es el **Survey Intelligent System (SIS)**: un **servicio interno de dominio** (no un microservicio, no un producto independiente) que transforma un instrumento en conocimiento estructurado (JSON canónico → JSON consolidado). El resto del backend expone endpoints, gestiona persistencia y orquesta el SIS.

La arquitectura de fondo es **sólida y compatible con la visión objetivo**: el aislamiento hexagonal del SIS (puertos y adaptadores) es precisamente lo que permitirá crecer hacia tres pipelines especializados (encuestas, entrevistas, pruebas estandarizadas) sin fragmentar el módulo. El acople controlado con el host (`services/sis_adapter.py`) es el patrón correcto para un servicio interno de dominio.

Reevaluada con el contexto de negocio, la conclusión central cambia de tono:

- **La mayoría de lo que la v1 marcó como "eliminable" es funcionalidad futura planificada** y debe conservarse: el código JWT comentado, el stack RAG, el `_extract_text_placeholder`, el `EmbeddingPort`, el endpoint de ingesta comentado y las rutas de extensión del `sis_adapter`.
- **La deuda técnica real y accionable se reduce** a: documentación desincronizada, un par de duplicaciones con divergencia (normalizador de tipo), una inconsistencia de estado (`etl_pendiente`) y algunos residuos verdaderamente obsoletos del flujo ETL antiguo (a confirmar, no a eliminar automáticamente).
- **El SIS termina su responsabilidad al generar el JSON consolidado.** El RAG principal es un componente separado que **consume** ese conocimiento. No se debe fusionar SIS y RAG.

**Prioridades preservadas:** funcionalidad actual, lógica de negocio, contratos de API, estructura de BD, modelos y servicios críticos. Además, esta versión añade una cuarta prioridad explícita: **preservar los puntos de extensión del roadmap.**

**Veredicto v2:** el backend está bien encaminado hacia la visión objetivo. El trabajo inmediato es de **alineación** (documentación, consistencia, nombres) y de **preparación de andamiaje** para entrevistas y pruebas estandarizadas, no de recorte.

---

# Arquitectura Actual

## Diagrama de capas (con la posición correcta del SIS y el RAG)

```
                         ┌──────────────────────────────────────────┐
   HTTP  ───────────►    │  main.py  (FastAPI, CORS, routers)         │
                         └──────────────────────────────────────────┘
                                          │
        ┌──────────────────────────────────┴───────────────────────────┐
        ▼                                                                ▼
┌───────────────────┐                                    ┌───────────────────────┐
│ routers_carga.py  │                                    │ routers_visualizacion  │
└───────────────────┘                                    └───────────────────────┘
        │  Depends() → dependencies_instrumentos.py (auth/acceso; JWT = FUTURO)
        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ api/services/  (host: orquestación, BD, disco)                             │
│   services_carga.py  → InstrumentCargaService, EtlService                   │
│   services_visualizacion.py, services_compartidos.py                       │
└──────────────────────────────────────────────────────────────────────────┘
        │
        ▼  (único punto de acople aprobado)
┌───────────────────────────┐
│ services/sis_adapter.py   │  implementa LLMPort (OllamaLLMAdapter),
│ services/ollama_client.py │  build_request/build_service, load_kpi_catalog
└───────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ survey_intelligence/  (SERVICIO INTERNO DE DOMINIO — hexagonal)            │
│   facade.py → orquesta el pipeline                                         │
│   ports/ · contracts/ · engine/ · pipeline/stages · export/               │
│                                                                            │
│   RESPONSABILIDAD: Instrumento → JSON Canónico → JSON Consolidado          │
└──────────────────────────────────────────────────────────────────────────┘
        │
        ▼  (frontera de responsabilidad: aquí TERMINA el SIS)
┌──────────────────────────────────────────────────────────────────────────┐
│ RAG PRINCIPAL  (COMPONENTE SEPARADO — FUTURO)                              │
│   consume JSON consolidado → chunks enriquecidos → embeddings →            │
│   índice vectorial → preguntas y respuestas                                │
└──────────────────────────────────────────────────────────────────────────┘
```

## Flujo objetivo end-to-end (según aclaraciones)

```
Instrumento → Extracción (módulo unificado) → ETL Inteligente → SIS
   → JSON Canónico → JSON Consolidado → [FRONTERA SIS] → RAG Principal
   → Chunks enriquecidos → Embeddings → Índice vectorial → Q&A
```

## Evaluación de principios (reafirmada)

- **Clean Architecture / DDD:** el SIS es el bounded context central, correctamente aislado. La visión de "núcleo compartido + pipelines especializados" es DDD idiomático (estrategia de módulos por subdominio).
- **Separation of Concerns:** la frontera SIS↔RAG es explícita y debe mantenerse: el SIS **produce** conocimiento, el RAG lo **consume**.
- **SOLID:** el patrón de puertos (DIP) es el habilitador de la evolución multi-pipeline. Las fugas del host (autorización repetida, imports de internos del SIS) siguen siendo mejorables, pero son de bajo impacto.

---

# Mapa de Dependencias

*(Sin cambios estructurales respecto a la v1; se reinterpretan las piezas "incompletas" como puntos de extensión.)*

```
routers_carga.py
   └─► InstrumentCargaService.upload / create_metadata
   └─► EtlService.analyze
          └─► sis_adapter.build_request / build_service      (único acople)
                 └─► SurveyIntelligenceService.process()  → facade orquesta el pipeline
                        └─► OllamaLLMAdapter.complete_json → ollama_client → Ollama
   └─► EtlService.approve_cleaning / approve_enrichment
          └─► SIS: apply_engine / sav_writer / builders  (hoy import directo de internos → mover tras la superficie pública)

routers_visualizacion.py
   └─► InstrumentVisualizacionService.{list_kpis,list,get_detail,download,delete}
          └─► ArchivoService / PermissionService
          └─► SQL crudo tt_rag.kpi (resolución de nombrekpi)
```

**Puntos de extensión ya presentes (conservar):**
- `sis_adapter.build_request`: bifurcación encuesta (tabular) vs entrevista/prueba (texto) — es la costura para los pipelines especializados.
- `sis_adapter`: `rag_sources` + `SourceDocument(kind="codebook")` — costura para el RAG de codebooks.
- `_extract_text_placeholder`: marcado explícitamente como provisional hacia `pipeline_ingesta/extractor.py` — costura del módulo unificado de extracción.
- `ports/embedding_port.py`, `ports/rag_port.py`: puertos para RAG/embeddings futuros.

---

# Hallazgos (reevaluados)

## Fortalezas (preservar y potenciar)

- **F1. SIS hexagonal** — habilitador directo de la arquitectura multi-pipeline objetivo. Sin dependencias de FastAPI/SQLAlchemy en su interior (verificado).
- **F2. Acople único vía `sis_adapter`** — patrón correcto para un servicio interno de dominio; **no** convierte al SIS en microservicio.
- **F3. Transaccionalidad e idempotencia en `analyze`** — el trabajo LLM ocurre antes de tocar la BD; rollback si el SIS falla; reanálisis idempotente.
- **F4. Costuras de extensión ya colocadas** — request bifurcado por tipo, `rag_sources` para codebooks, placeholder de extracción, puertos RAG/embedding. El diseño ya anticipa el roadmap.
- **F5. Frontera SIS↔RAG explícita** — el SIS termina en el JSON consolidado; el RAG consume. Separación de responsabilidades correcta.

## Deuda técnica real (accionable, de bajo riesgo)

- **H1. Documentación desincronizada (prioridad 1).** `backend/README.md` y `api/routers/README.md` describen el flujo ETL antiguo (`etl/extract`, `etl/approve`, estado `etl_pendiente`). El flujo real es `analyze → approve/cleaning → approve/enrichment`.
- **H2. Normalizador `tipo_instrumento` divergente.** `schemas_carga` (`lower().strip()`) vs `schemas_visualizacion` (además `replace(" ", "_")`). Bug latente de filtrado.
- **H3. Estado obsoleto `etl_pendiente` en `services_visualizacion.list()`.** Ya no se produce; el filtro debe alinearse a los estados vigentes (verificar contra datos).
- **H4. Resolución de `nombrekpi` por SQL crudo repetida 3× + N+1** en visualización. Falta `relationship KpiInferido↔KPI`.
- **H5. Constantes de dominio duplicadas** (modelos vs `Literal` en schemas) sin fuente única.
- **H6. `services_carga.py` sobredimensionado.** Mezcla carga, ETL, extracción de texto y generación de artefactos. Su división encaja con el módulo unificado de extracción (ver Rec-Ext).
- **H7. Autorización repetida** entre dependencies (correcto) y services.
- **H8. Higiene menor:** `print()` de depuración en `llm_service`; engine sin `pool_pre_ping`; `httpx` no declarado en requirements; `KPI.activo` (bool sobre Integer); mensaje de `validar_formato` no menciona `.xls`; CORS `*` con credenciales (endurecer antes de producción).
- **H9. Import de internos del SIS desde el host** (`apply_engine`, `sav_writer`, builders). Debe pasar por la superficie pública para proteger el aislamiento del servicio de dominio.

## Elementos posiblemente obsoletos (a confirmar, NO eliminar automáticamente)

- **H10. Residuos del flujo ETL antiguo:** `EtlService._approve_legacy` (requiere estado `etl_pendiente` inexistente) y schemas `EtlExtractResponse`. Estos sí parecen **obsoletos** (reemplazados por el flujo vivo), pero se dejan como **candidatos a revisión** hasta tu confirmación explícita.
- **H11. `services/llm_service.py`:** su ruta de ETL por prompts fue reemplazada por el SIS. Clasificación matizada abajo (parte obsoleta, parte futura).

---

# Código Duplicado

*(Reafirmado desde v1; sin cambios de fondo — la duplicación real es deuda, no roadmap.)*

| ID | Ubicación | Descripción | Impacto | Propuesta | Riesgo |
|---|---|---|---|---|---|
| D1 | `schemas_carga` vs `schemas_visualizacion` | `normalizar_tipo_instrumento` divergente | Bug latente | Normalizador único compartido | Bajo |
| D2 | `PermissionService.es_propietario` vs `verificar_propietario` | Misma query de propiedad; services re-verifica | Autorización dispersa | Centralizar en dependencies | Medio (seguridad) |
| D3 | `services_visualizacion` (list/get_detail/list_kpis) | SQL crudo `nombrekpi` 3× + N+1 | Rendimiento | `relationship KpiInferido↔KPI` | Bajo-Medio |
| D4 | modelos vs schemas | Tipos/estados duplicados | Desincronización | Fuente única de enums | Bajo |
| D5 | SIS S6/S7/S7b/S8b | Patrón "LLM 2 intentos + parse + degradación" | Repetición interna | Helper en `engine/parsing/` | Medio (tocar SIS) |

> **No duplicados (aclarado):** `contracts/result.py` vs `results.py`; `s2_canonical` vs `s2_document`; `s7`/`s7b`; `s8`/`s8b`. Son responsabilidades distintas. Con la visión multi-pipeline, la separación `s2_canonical` (tabular) vs `s2_document` (narrativo) es además **estratégica**: es el germen de los pipelines especializados.

> **D6 (parser JSON duplicado host vs SIS):** se resuelve solo cuando se retire la parte obsoleta de `llm_service` (ver reclasificación). No forzar ahora.

---

# Reclasificación: Funcionalidad Futura vs Obsoleto vs Muerto

Esta es la sección central de la reevaluación. Cada elemento que la v1 tocó como "eliminable" se reclasifica aquí.

| ID | Elemento | Clasificación v1 | **Clasificación v2** | Justificación (aclaración de negocio) | Acción |
|---|---|---|---|---|---|
| C1 | Bloque JWT comentado + rama de `get_current_user` real | Código muerto | **Funcionalidad futura planificada** | §1: se usará al implementar login. | **Conservar** |
| C2 | `core/security.py` (`hashear/verificar_password`) | Candidato a revisión | **Funcionalidad futura planificada** | Soporte directo del login JWT. | **Conservar** |
| C3 | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Inerte | **Funcionalidad futura planificada** | Config del JWT futuro. | **Conservar** |
| C4 | `chromadb`, `langchain*`, `sentence-transformers`, config ChromaDB | Dependencias no usadas | **Funcionalidad futura planificada (RAG principal)** | §6: RAG principal separado, futuro. | **Conservar** (aislar en extra opcional, sin eliminar) |
| C5 | `ports/embedding_port.py`, `ports/rag_port.py` (+ `NullRagRetriever`) | Muerto/anticipatorio | **Funcionalidad futura planificada** | §3 y §6: RAG de codebooks + embeddings. | **Conservar** |
| C6 | `rag_sources` / `SourceDocument(kind="codebook")` en `sis_adapter` | Incompleto | **Funcionalidad futura planificada** | §3: ingesta/análisis de codebooks. | **Conservar** |
| C7 | `_extract_text_placeholder` (multi-formato) | Duplicación conceptual | **Funcionalidad futura planificada** | §2: será el módulo unificado de extracción (`pipeline_ingesta/extractor.py`). | **Conservar y promover** |
| C8 | Endpoint `/instrumentos/ingesta` comentado + `InstrumentCargaService.ingest` + `Ingesta*` schemas | Código muerto | **Funcionalidad futura planificada** | Vectorización futura (paso hacia el RAG). | **Conservar** |
| C9 | `llm_service.responder_consulta_rag`, `inferir_kpis_desde_texto` (NotImplementedError) | Muerto | **Funcionalidad futura planificada** | Puntos de extensión RAG/KPIs. | **Conservar** |
| C10 | `s4.insufficient_variable_ids()` | Muerto | **Funcionalidad futura / utilidad de dominio** | Útil para RAG de codebooks (resolver variables insuficientes). | **Conservar** |
| C11 | `EtlService._approve_legacy` | Candidato a revisión | **Código obsoleto** (a confirmar) | Reemplazado por el flujo de dos fases; requiere estado inexistente. | **Candidato a revisión** (no eliminar sin OK) |
| C12 | `EtlExtractResponse` (schema) | Muerto | **Código obsoleto** (a confirmar) | Reemplazado por `AnalyzeResponse`. | **Candidato a revisión** |
| C13 | `llm_service.generar_propuestas_etl` + parser/helpers | Muerto | **Mixto: obsoleto (ETL viejo) pero reutilizable** | El ETL migró al SIS; el parser robusto podría reaprovecharse. | **Conservar por ahora**; decidir en Fase C |
| C14 | Variable `join_realizado` (no leída) | Eliminable | **Código muerto trivial** | Variable local sin efecto. | Eliminable de riesgo nulo (Fase A) |

> **Regla aplicada:** ante la duda entre "obsoleto" y "futuro", prevalece **conservar**. Solo `C14` (variable local) y, previa confirmación, `C11`/`C12` se consideran retirables.

---

# Problemas de Organización (reencuadrados hacia la visión objetivo)

- **O1. `services_carga.py` monolítico → oportunidad de extraer el Módulo Unificado de Extracción (§2).** La lógica de `_extract_text_placeholder` debe convertirse en un módulo `extraction/` (o `pipeline_ingesta/extractor.py`) desacoplado del tipo de instrumento, con un dispatcher por formato (CSV/XLSX/PDF/DOCX/TXT/SAV/futuros). El tipo de instrumento **no** decide la extracción; lo decide el formato. El SIS decide luego cómo procesar.
- **O2. Ausencia de capa de repositorio** — tolerable hoy; recomendable al crecer los pipelines para no dispersar SQL.
- **O3. Autorización dispersa** — centralizar en dependencies (compatible con el JWT futuro).
- **O4. Constantes de dominio dispersas** — fuente única de enums (tipos/estados), especialmente porque se sumarán estados/tipos para entrevistas y pruebas.
- **O5. Imports de internos del SIS desde el host** — encapsular tras la superficie pública para que el SIS siga siendo un servicio de dominio limpio y evolucionable.
- **O6. Numeración de stages vs orden real (S8/S9)** — documentar; se volverá más relevante al añadir pipelines.

---

# Revisión de Survey Intelligent System (SIS)

## Naturaleza (corregida y fijada)

El SIS es un **servicio interno de dominio**, no un microservicio ni un producto independiente. Su aislamiento actual es una **decisión de ingeniería por complejidad**, no una frontera de despliegue. Se consume desde los endpoints del backend a través de `sis_adapter`. **No debe separarse artificialmente del backend.**

## Responsabilidad (fijada)

Instrumento → limpieza → normalización → ETL inteligente guiado por LLM → extracción de conocimiento → enriquecimiento semántico → metadatos → inferencia de KPIs → **JSON canónico → JSON consolidado**. **Aquí termina el SIS.** El RAG principal es otro componente que consume el consolidado.

## Frontera SIS ↔ RAG (fijada)

- SIS = **produce** conocimiento estructurado.
- RAG principal = **consume** conocimiento estructurado (chunking, embeddings, índice, Q&A).
- **No fusionar.** No mover lógica de RAG al SIS. El RAG de codebooks (§3) es una **entrada auxiliar** del SIS para enriquecer interpretación, distinta del RAG principal de salida.

## Arquitectura objetivo del SIS (propuesta)

Un **único SIS** con **núcleo compartido + pipelines especializados**. La estructura actual ya apunta aquí; se propone hacerla explícita conforme se incorporen entrevistas y pruebas.

```
survey_intelligence/
├── contracts/              # contratos compartidos + específicos por instrumento
├── ports/                  # LLM, RAG, embedding, clock, ids, telemetry (compartidos)
├── engine/                 # NÚCLEO COMPARTIDO reutilizable
│   ├── readers/            # (alimentado por el módulo unificado de extracción)
│   ├── parsing/            # robust_json, helper LLM común (D5)
│   ├── profiling/ heuristics/ spss/ transforms/ prompts/
│   └── nlp/                # NUEVO (futuro): tópicos, discurso, citas, resumen  ← entrevistas
├── pipeline/
│   ├── shared/             # etapas comunes (ingestion, canonical base, context, audit)
│   ├── encuestas/          # pipeline tabular (S1..S9 actuales)
│   ├── entrevistas/        # NUEVO: participantes, roles, Q-R, NLP, temas, hallazgos
│   └── pruebas/            # NUEVO (placeholder extensible): métricas psicométricas futuras
├── export/                 # sav_writer + futuros export por tipo
└── facade.py               # selecciona el pipeline según instrument_type
```

**Principios de la arquitectura objetivo:**
1. **Un solo módulo, no tres SIS.** Los pipelines comparten núcleo (`engine/`, `ports/`, contratos base) y especializan solo lo necesario.
2. **Selección de pipeline en el facade** por `instrument_type` (la costura ya existe en `build_request`/facade). Cada pipeline produce el mismo tipo de resultado de alto nivel (`SurveyIntelligenceResult`) para no romper el contrato del host.
3. **El JSON canónico admite variantes por tipo** pero conserva un envoltorio común (metadatos, versión, trazabilidad) para que el RAG principal consuma cualquier consolidado de forma uniforme.
4. **NLP para entrevistas vive dentro del SIS** (`engine/nlp/`), no en el RAG. El RAG solo consume el consolidado resultante.

## Mejoras internas (sin fragmentar, riesgo controlado)

1. Formalizar `pipeline/shared/` vs `pipeline/encuestas/` sin romper imports (refactor incremental).
2. Extraer helper LLM común (D5).
3. Aclarar nombres `result.py`/`results.py`.
4. Mantener y documentar `EmbeddingPort`/`RagRetrieverPort` como puertos del roadmap.
5. Preparar contratos base para participantes/roles (entrevistas) sin activarlos aún.

---

# Evolución de los JSON Canónico y Consolidado

Principio transversal (§10, §11): el consolidado de **encuestas ya es adecuado**; solo mejoras **incrementales y compatibles hacia atrás**. Entrevistas y pruebas deben **alcanzar una riqueza semántica equivalente**. Todos los consolidados deben ser: comprensibles para humanos, útiles para RAG (chunking/embeddings), con trazabilidad y con **conocimiento consolidado** (no solo datos transformados).

## Envoltorio común (todos los tipos)

Para que el RAG principal consuma cualquier consolidado de forma uniforme, se propone un **envoltorio común** (compatible con el consolidado actual de encuestas):

```
{
  "schema_version", "pipeline_version", "canonical_id",
  "instrument_type",                     // encuesta | entrevista | prueba_estandarizada
  "metadata": { Dublin Core },
  "summary_humano": { qué se analizó, qué se encontró, patrones, evidencia },
  "knowledge": { ...específico por tipo... },
  "traceability": { enlaces a preguntas/respuestas/participantes/variables/indicadores/fuentes },
  "rag_hints": { unidades sugeridas de chunking, campos indexables }
}
```

> El objetivo es que `summary_humano`, `traceability` y `rag_hints` existan en los **tres** tipos, garantizando comprensibilidad, trazabilidad y utilidad para RAG.

## Encuestas (mejoras incrementales, compatibles hacia atrás)

- **No rediseñar.** Añadir solo campos opcionales (aditivos) que ya no rompan consumidores: p.ej. `rag_hints` explícitos y un `summary_humano` más narrativo si aún no lo estuviera.
- Preservar `canonical_id` y las versiones.
- **Riesgo: Bajo** (cambios aditivos).

## Entrevistas (nuevo, visión desde ahora — §8)

Canónico (entrevistas) debe capturar:
- **Participantes**: `entrevistador`, `entrevistado(s)` con identificadores (`entrevistador_01`, `entrevistado_01`, …) y roles.
- **Segmentación Pregunta–Respuesta**: quién pregunta, quién responde, a qué pregunta responde (turnos de diálogo).

Consolidado (entrevistas) debe reflejar:
- participantes, roles, identificadores, cantidad de personas analizadas;
- **hallazgos, temas (agrupación temática), patrones, tópicos**;
- **citas relevantes** (evidencia textual con trazabilidad al turno);
- **resumen por participante** y **resumen general**;
- análisis vía **NLP/semántico/discursivo** (no como encuesta).

Requiere `engine/nlp/` en el SIS y contratos nuevos (`Participant`, `DialogueTurn`, `Theme`, `Quote`, `ParticipantSummary`).
- **Riesgo: Medio** (nuevos contratos + pipeline; aislado del de encuestas).

## Pruebas estandarizadas (extensión futura — §9)

- Sin reglas definitivas aún. La arquitectura debe **permitir agregarlas fácilmente**: dejar `pipeline/pruebas/` como punto de extensión y no tomar decisiones que dificulten su incorporación (p.ej. no acoplar el envoltorio común a supuestos exclusivos de encuestas/entrevistas).
- El consolidado deberá alcanzar la misma riqueza (summary humano, trazabilidad a ítems/indicadores, evidencia).
- **Riesgo: Bajo ahora** (solo andamiaje/placeholder), **Medio después** (reglas psicométricas).

---

# Riesgos Detectados (reevaluados)

| ID | Riesgo | Severidad | Nota v2 |
|---|---|---|---|
| R1 | Documentación engañosa (flujo antiguo) | Media | Prioridad de corrección; alto costo de onboarding. |
| R2 | Estado obsoleto `etl_pendiente` en filtro | Media | Verificar contra datos antes de tocar. |
| R3 | Seguridad en modo desarrollo + CORS `*` | Media (Alta en prod) | El JWT es **funcionalidad futura**; endurecer al activarlo. |
| R4 | `ImprovementOpportunity` huérfano en ORM | Baja | Borrado manual funciona; formalizar cascade al madurar. |
| R5 | Vectores huérfanos al borrar (futuro) | Baja | Se resuelve cuando exista el RAG principal. |
| R6 | Divergencia LLM host-legacy vs SIS | Baja | Mantener el SIS como única ruta viva de ETL. |
| R7 | `httpx` no declarado en requirements | Baja | Declararlo explícitamente. |
| R8 | Falta `pool_pre_ping` | Baja | Robustez de conexión. |
| R9 | Tocar el SIS sin tests verdes | Media | Ejecutar la suite del SIS antes/después de cualquier cambio interno. |
| **R10** | **Reintroducir acople de extracción al tipo de instrumento** | **Media** | Al construir el módulo unificado, no volver a atar extracción↔tipo (§2). |
| **R11** | **Fusionar SIS y RAG por conveniencia** | **Media** | Mantener la frontera: SIS produce, RAG consume (§6). |
| **R12** | **Diseñar el consolidado solo para encuestas** | **Media** | El envoltorio común debe servir a los tres tipos (§11). |

---

# Recomendaciones (actualizadas)

Formato: **descripción · beneficio · impacto · riesgo**. Ninguna se ejecuta ahora.

### Rec-1 · Alinear documentación con el flujo real *(sin cambios respecto a v1)*
Actualizar READMEs y docstrings al flujo `analyze → approve/cleaning → approve/enrichment`; marcar explícitamente lo que es **funcionalidad futura** (JWT, RAG, ingesta) para que no vuelva a interpretarse como muerto. · Onboarding correcto. · Solo documentación. · **Bajo**

### Rec-2 · Normalizador único de `tipo_instrumento`
Unificar la lógica divergente. · Elimina bug latente. · Validación de entrada. · **Bajo**

### Rec-3 · Alinear estado `etl_pendiente`
Retirar la referencia obsoleta del filtro tras verificar datos. · Consistencia. · Filtro de listado. · **Medio**

### Rec-4 · `relationship KpiInferido↔KPI` + eliminar N+1
· Rendimiento y menos SQL crudo. · Consultas de visualización (mismo contrato de salida). · **Bajo-Medio**

### Rec-5 · Centralizar autorización en dependencies (compatible con JWT futuro)
· DRY/SoC; una sola política. · Rutas de escritura. · **Medio** (seguridad)

### Rec-6 · Fuente única de enums de dominio (tipos/estados)
Prepararla para sumar estados/tipos de entrevistas y pruebas. · Consistencia y extensibilidad. · Modelos + schemas. · **Bajo-Medio**

### Rec-Ext · **Módulo Unificado de Extracción** (§2) — REEMPLAZA la propuesta v1 de "dividir extractores"
Extraer `_extract_text_placeholder` a un módulo `extraction/` (o `pipeline_ingesta/extractor.py`) con dispatcher **por formato** (CSV/XLSX/PDF/DOCX/TXT/SAV/futuros), **desacoplado del tipo de instrumento**. El SIS decide el procesamiento posterior. · Habilita el roadmap; elimina la lógica multi-formato del god-service. · Refactor de una porción de `services_carga.py`. · **Medio**

### Rec-SIS · **Arquitectura objetivo del SIS: núcleo compartido + pipelines** (§7)
Formalizar `pipeline/shared/` + `pipeline/encuestas/` y dejar preparados `entrevistas/` y `pruebas/`. Un solo SIS. · Escala a tres instrumentos sin fragmentar. · Refactor interno incremental del SIS (con tests). · **Medio**

### Rec-Entrevistas · Contratos y pipeline de entrevistas (§8)
Añadir contratos (`Participant`, `DialogueTurn`, `Theme`, `Quote`, resúmenes) y `engine/nlp/`; pipeline especializado NLP/discursivo. · Nuevo tipo de instrumento con riqueza semántica. · Adición aislada (no toca encuestas). · **Medio**

### Rec-JSON · Envoltorio común de consolidados + `rag_hints`/`summary_humano`/`traceability`
Aditivo y compatible hacia atrás para encuestas; obligatorio para entrevistas y pruebas. · Consumo uniforme por el RAG; conocimiento consolidado. · Cambios aditivos. · **Bajo** (encuestas) / **Medio** (nuevos tipos)

### Rec-Encapsular-SIS · Mover imports de internos del SIS tras la superficie pública (§4)
· Protege al SIS como servicio de dominio evolucionable. · Imports del host. · **Bajo**

### Rec-Higiene · `pool_pre_ping`, declarar `httpx`, `print()`→logging, `KPI.activo`, mensaje `.xls`
· Robustez y limpieza. · Config/infra menores. · **Bajo**

### Rec-Deps-RAG · Aislar dependencias del RAG futuro (NO eliminar)
Mover `chromadb/langchain*/sentence-transformers` a un extra opcional (p.ej. `requirements-rag.txt`) con nota "RAG principal — futuro". · Instalación más clara sin perder el roadmap. · Entorno. · **Bajo-Medio** (coordinar con roadmap)

### Rec-JWT · Reactivar autenticación cuando exista el login (funcionalidad futura)
Implementar `POST /auth/token`, activar la rama JWT, revivir `security.py`, endurecer CORS. · Seguridad de producción. · Activa el subsistema de auth. · **Alto**

### Rec-Obsoletos · Confirmar y (solo entonces) retirar residuos del ETL antiguo
`_approve_legacy`, `EtlExtractResponse`. Requiere tu confirmación explícita; hasta entonces, **candidatos a revisión**. · Reduce confusión. · Eliminación puntual verificada. · **Bajo** (tras confirmación)

---

# Plan de Refactorización (roadmap actualizado)

Ordenado por riesgo creciente. **Nada se ejecuta sin tu aprobación.**

## Fase A — Riesgo nulo/bajo (alineación)
1. Rec-1: documentación al flujo real + marcar funcionalidades futuras.
2. Rec-Higiene: `httpx`, `pool_pre_ping`, `print()`→logging, mensaje `.xls`.
3. C14: eliminar variable local no usada.
- *Verificación:* arranque API + `GET /` + suite de tests del SIS.

## Fase B — Riesgo bajo (consistencia y encapsulación, sin tocar roadmap)
4. Rec-2: normalizador único.
5. Rec-Encapsular-SIS: imports del host tras la superficie pública.
6. Rec-6: fuente única de enums.
- *Verificación:* wizard completo end-to-end + tests.

## Fase C — Riesgo bajo-medio (rendimiento y obsoletos confirmados)
7. Rec-4: `relationship KpiInferido↔KPI`, quitar N+1.
8. Rec-3: alinear `etl_pendiente` (previa verificación de datos).
9. Rec-Obsoletos: retirar `_approve_legacy`/`EtlExtractResponse` **solo con tu OK**; decidir destino de `llm_service` (parser reutilizable).
- *Verificación:* pruebas de listado/detalle/filtros; comparar salidas antes/después.

## Fase D — Riesgo medio (preparación del roadmap)
10. Rec-Ext: **Módulo Unificado de Extracción** desacoplado del tipo.
11. Rec-SIS: formalizar núcleo compartido + `pipeline/shared|encuestas` y andamiaje `entrevistas/`, `pruebas/`.
12. Rec-JSON (encuestas): añadir campos aditivos (`rag_hints`, `summary_humano`) compatibles hacia atrás.
13. Rec-5: centralizar autorización (alineado con JWT futuro).
- *Verificación:* suite del SIS + flujo end-to-end + pruebas de permisos.

## Fase E — Riesgo medio/alto (nuevas capacidades)
14. Rec-Entrevistas: contratos + `engine/nlp/` + pipeline de entrevistas + consolidado con riqueza equivalente.
15. `pipeline/pruebas/`: reglas psicométricas cuando existan (§9).
16. Rec-Deps-RAG + habilitación del **RAG principal** (componente separado que consume el consolidado).
17. Rec-JWT: autenticación real + CORS endurecido.
- *Verificación:* pruebas de integración con Ollama/ChromaDB reales; pruebas de seguridad; validación de consolidados por tipo contra el RAG.

---

# Respuestas directas a la Solicitud Final

1. **Reevaluación:** completada; taxonomía de 3 categorías aplicada a cada hallazgo.
2. **Visión objetivo actualizada:** SIS como servicio interno de dominio con núcleo compartido + pipelines; frontera SIS↔RAG explícita; módulo unificado de extracción; envoltorio común de consolidados.
3. **Recomendaciones que cambian:** la v1 "dividir extractores por tipo" se **invierte** → módulo unificado desacoplado del tipo (Rec-Ext). "Eliminar dependencias RAG" pasa a **aislar sin eliminar** (Rec-Deps-RAG). "Eliminar JWT/EmbeddingPort/ingesta" pasa a **conservar como futuro**.
4. **Ya NO son candidatos de eliminación:** JWT comentado, `security.py`, config JWT, stack RAG y config ChromaDB, `embedding_port`/`rag_port`, `rag_sources`/codebook, `_extract_text_placeholder`, endpoint `ingesta` + `ingest` + `Ingesta*`, stubs `NotImplementedError` de `llm_service`, `s4.insufficient_variable_ids()`. (Ver tabla C1–C13.)
5. **Arquitectura objetivo del SIS:** propuesta en la sección del SIS (un módulo, núcleo compartido, pipelines `encuestas`/`entrevistas`/`pruebas`, `engine/nlp/`, selección por `instrument_type` en el facade).
6. **Evolución de JSON:** envoltorio común + mejoras aditivas para encuestas; contratos y consolidado ricos para entrevistas (participantes/roles/Q-R/NLP/temas/citas/resúmenes); andamiaje extensible para pruebas.
7. **Roadmap actualizado:** Fases A–E arriba.
8. **Riesgos por recomendación:** anotados en cada Rec (Bajo / Medio / Alto).

---

## Anexo — Restricciones respetadas

- No se eliminó, modificó ni renombró código. No se generó código. No se ejecutaron refactorizaciones.
- Único archivo tocado: este reporte (actualizado a v2).
- Los componentes ligados al roadmap se conservan como **funcionalidad futura planificada**.
- Solo `C14` (variable local) y, **previa confirmación**, `C11`/`C12` se consideran retirables.

**Siguiente paso:** a la espera de tus instrucciones para la Fase 2. Sugiero comenzar por la **Fase A** (riesgo nulo/bajo) para alinear documentación y marcar explícitamente las funcionalidades futuras, evitando futuras confusiones sobre qué es "muerto" y qué es "planificado".
