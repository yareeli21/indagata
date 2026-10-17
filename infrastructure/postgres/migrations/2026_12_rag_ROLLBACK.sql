-- Rollback de 2026_12_rag.sql (borra respuesta_interpretada y las columnas nuevas de rag_log).
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_12_rag_ROLLBACK.sql
SET search_path TO tt_rag, public;

BEGIN;
DROP INDEX IF EXISTS idx_respuesta_crudo_pregunta;
DROP INDEX IF EXISTS idx_respuesta_crudo_respondente;
DROP TABLE IF EXISTS respuesta_interpretada;
ALTER TABLE rag_log DROP COLUMN IF EXISTS decision_dominio;
ALTER TABLE rag_log DROP COLUMN IF EXISTS motivo;
ALTER TABLE rag_log DROP COLUMN IF EXISTS score_max;
ALTER TABLE rag_log DROP COLUMN IF EXISTS ruta;
ALTER TABLE rag_log DROP COLUMN IF EXISTS instrumentos;
ALTER TABLE rag_log DROP COLUMN IF EXISTS contexto_usado;
ALTER TABLE rag_log DROP COLUMN IF EXISTS metricas;
ALTER TABLE rag_log DROP COLUMN IF EXISTS modelo_juez;
ALTER TABLE rag_log DROP COLUMN IF EXISTS fecha_metricas;
COMMIT;
