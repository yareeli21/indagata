# Documentación del Survey Intelligent System (SIS)

Documentación viva del SIS, alineada con el estado real del código. El SIS es **un solo sistema**
con un orquestador único (`facade.py`) y una **estrategia por instrumento** (`pipelines/`):
encuesta, entrevista y prueba estandarizada.

## Índice

| Documento | Para qué sirve | Empieza aquí si… |
|---|---|---|
| [`ARQUITECTURA_SIS.md`](ARQUITECTURA_SIS.md) | Cómo está organizado el SIS hoy: facade + `pipelines/` + `engine/` + `contracts/`, el contrato estrategia↔facade y el estado de madurez por instrumento. | Quieres entender la estructura general. |
| [`ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md`](ARQUITECTURA_LIMPIEZA_Y_ESTANDARIZACION.md) | Qué hace cada etapa (S1..S10) para limpiar, normalizar, estandarizar y enriquecer, y qué corre por tipo de instrumento. | Necesitas el detalle etapa por etapa. |
| [`GUIA_EXTENSION_INSTRUMENTOS.md`](GUIA_EXTENSION_INSTRUMENTOS.md) | Cómo agregar reglas específicas de un instrumento (entrevistas — ya hecho, plantilla; pruebas estandarizadas — esqueleto pendiente). | Vas a extender el sistema. |
| [`DESIGN_CODEBOOK_DETERMINISTA.md`](DESIGN_CODEBOOK_DETERMINISTA.md) | Resolución determinística de codebooks (sin RAG): estado, formatos y pendientes. | Trabajas con codebooks. |
| [`ESQUEMA_BD.md`](ESQUEMA_BD.md) | Tablas de PostgreSQL (schema `tt_rag`) que el backend usa y sus relaciones. | Necesitas el modelo de datos. |

## Convenciones

- **Estado real, no planes.** Estos documentos describen lo que el código hace hoy. Los planes ya
  ejecutados y los diseños ya implementados se retiran para evitar confusión.
- **Verificación.** Toda modificación del SIS se valida con
  `python -m survey_intelligence.tests.run_all` (suite verde) + arranque de la app en 200.
- **Frontera del SIS.** El SIS produce el resultado; el **JSON consolidado** lo arma el host
  (`api/services/carga_artifacts.py`) y el **RAG principal** (chunking/embeddings/Q&A) es un
  componente separado que consume el consolidado, fuera del SIS.
