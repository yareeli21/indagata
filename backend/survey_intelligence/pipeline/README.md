# SIS — Etapas del pipeline (`pipeline/stages/`)

Esta carpeta contiene las **etapas** (S1..S10) del SIS. NO son la orquestación: el orquestador es
`survey_intelligence/facade.py`, y la **selección por instrumento** vive en
`survey_intelligence/pipelines/` (estrategias). Ver `docs/ARQUITECTURA_SIS.md` para el panorama.

## Cómo se usan las etapas hoy

`facade.process()` selecciona una estrategia (`pipelines/`) que **compone** estas etapas:

- **EncuestaPipeline:** S1 `ingest` → S2 `build_canonical` → S3 `profile`; luego S8b resultados.
- **Entrevista / Prueba (vía documento):** S1 valida `extracted_text` → S2 `build_document_canonical`
  → S3 SKIPPED; entrevista añade S10.
- **Tronco común (todas):** S4 contexto → S5 codebook determinístico → S6 auditoría →
  S7 enriquecimiento → S7b KPIs → S9 ensamblado → S8 gap analysis.

Las etapas son piezas reutilizables; la especialización por tipo se resuelve en la estrategia
(`pipelines/<tipo>.py`), no dentro de las etapas.

## Frontera de responsabilidad

El SIS termina al producir el `SurveyIntelligenceResult`. El **JSON consolidado** lo arma el host
y el **RAG principal** (chunking, embeddings, índice, Q&A) es un componente separado que consume el
consolidado, fuera del SIS.

## Referencias

- Organización del SIS: `../docs/ARQUITECTURA_SIS.md`
- Detalle etapa por etapa: `../docs/ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md`
- Cómo extender a entrevistas / pruebas: `../docs/GUIA_EXTENSION_INSTRUMENTOS.md`
