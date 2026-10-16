-- ============================================================================
-- INDAGATA - ROLLBACK de 2026_10_limpieza.sql
-- Elimina la tabla limpieza_ejecucion y la columna raw_data.raw_archivo_clave.
-- ATENCIÓN: borra el historial de limpiezas (los CSV limpios en storage quedan).
--
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_10_limpieza_ROLLBACK.sql
-- ============================================================================

SET search_path TO tt_rag, public;

BEGIN;
DROP TABLE IF EXISTS limpieza_ejecucion;
ALTER TABLE raw_data DROP COLUMN IF EXISTS raw_archivo_clave;
COMMIT;
