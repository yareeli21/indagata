-- ============================================================================
-- INDAGATA - Migración incremental: RAG completo (respuestas en formato largo,
-- decisión de dominio y métricas por consulta)
-- Base de datos: indagata_db | Schema: tt_rag
-- ============================================================================
--
-- APLICA A: bases de datos EXISTENTES (los init/*.sql solo corren en primer arranque).
-- Es idempotente: puede ejecutarse varias veces sin error.
--
-- Ejecutar (Docker):
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_12_rag.sql
--
-- Cambios:
--   1. Tabla respuesta_interpretada: una fila por respuesta (respondente × pregunta)
--      del documento final VIGENTE de cada instrumento. La escribe knowledge-service
--      al publicar (reemplaza las filas del instrumento). Sirve para conteos y
--      porcentajes exactos, incluso entre varios instrumentos; `contexto` guarda los
--      datos del respondente (turno, carrera…) para filtrar por grupo.
--        - encuesta:   valor/significado/nivel de la escala (acuerdo, desacuerdo…)
--        - prueba:     opción elegida, su significado y nivel correcta/incorrecta
--        - entrevista: la respuesta (texto) de cada participante a cada pregunta
--   2. rag_log: decisión de dominio y ruta de cada consulta, y las métricas de
--      evaluación automática (RAGAS) que se calculan después de responder.
-- ============================================================================

SET search_path TO tt_rag, public;

BEGIN;

CREATE TABLE IF NOT EXISTS respuesta_interpretada (
    id_respuesta    SERIAL       PRIMARY KEY,
    id_crudo        INTEGER      NOT NULL REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    version         INTEGER      NOT NULL,
    respondente_id  VARCHAR(40)  NOT NULL,
    pregunta_id     VARCHAR(40)  NOT NULL,
    valor           TEXT,
    significado     TEXT,
    nivel           VARCHAR(30),
    estado          VARCHAR(20)  NOT NULL,
    contexto        JSONB        NOT NULL DEFAULT '{}'::jsonb,
    fecha_creacion  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_respuesta_crudo_pregunta    ON respuesta_interpretada(id_crudo, pregunta_id);
CREATE INDEX IF NOT EXISTS idx_respuesta_crudo_respondente ON respuesta_interpretada(id_crudo, respondente_id);

ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS decision_dominio VARCHAR(20);   -- dentro | fuera | privacidad | manipulacion | sin_informacion | ayuda
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS motivo           TEXT;
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS score_max        REAL;
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS ruta             VARCHAR(20);   -- semantica | estructurada | mixta | ayuda
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS instrumentos     JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS contexto_usado   JSONB NOT NULL DEFAULT '[]'::jsonb;  -- fragmentos dados al LLM (para RAGAS)
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS metricas         JSONB;
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS modelo_juez      VARCHAR(100);
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS fecha_metricas   TIMESTAMP;

COMMIT;
