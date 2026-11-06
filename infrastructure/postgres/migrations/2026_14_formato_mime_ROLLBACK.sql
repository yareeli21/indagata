-- Rollback de 2026_14_formato_mime.sql (vuelve dc_format a 50; recorta los valores más largos).
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_14_formato_mime_ROLLBACK.sql
SET search_path TO tt_rag, public;

BEGIN;
UPDATE metadatos_dc SET dc_format = left(dc_format, 50) WHERE length(dc_format) > 50;
ALTER TABLE metadatos_dc ALTER COLUMN dc_format TYPE VARCHAR(50);
COMMIT;
