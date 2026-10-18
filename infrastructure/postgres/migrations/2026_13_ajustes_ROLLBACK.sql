-- Rollback de 2026_13_ajustes.sql (borra kpi_fuente y las columnas de caché de rag_log).
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_13_ajustes_ROLLBACK.sql
SET search_path TO tt_rag, public;

BEGIN;
DROP TABLE IF EXISTS kpi_fuente;
DROP INDEX IF EXISTS idx_rag_log_clave_cache;
ALTER TABLE rag_log DROP COLUMN IF EXISTS clave_cache;
ALTER TABLE rag_log DROP COLUMN IF EXISTS salida;
COMMIT;
