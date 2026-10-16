-- Rollback de 2026_11_conocimiento.sql (borra la tabla y sus datos).
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_11_conocimiento_ROLLBACK.sql
SET search_path TO tt_rag, public;

BEGIN;
DROP INDEX IF EXISTS idx_version_conocimiento_crudo_estado;
DROP TABLE IF EXISTS version_conocimiento;
COMMIT;
