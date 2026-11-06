-- Revierte 2026_16_sin_clave.sql: vuelve a crear la columna (vacía; las claves borradas no se recuperan).
SET search_path TO tt_rag, public;

BEGIN;
ALTER TABLE raw_data ADD COLUMN IF NOT EXISTS raw_archivo_clave TEXT;
COMMIT;
