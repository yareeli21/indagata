-- ============================================================================
-- INDAGATA - Migración incremental: formato Dublin Core con el tipo MIME completo
-- Base de datos: indagata_db | Schema: tt_rag
-- ============================================================================
--
-- APLICA A: bases de datos EXISTENTES (los init/*.sql solo corren en primer arranque).
-- Es idempotente: puede ejecutarse varias veces sin error.
--
-- Ejecutar (Docker):
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_14_formato_mime.sql
--
-- Cambio:
--   metadatos_dc.dc_format VARCHAR(50) → VARCHAR(120). Los MIME de XLSX (65 caracteres)
--   y DOCX (71) no cabían: una encuesta en Excel o una entrevista en Word no se podía
--   aprobar (matriz de formatos, 21 oct 2026).
SET search_path TO tt_rag, public;

BEGIN;
ALTER TABLE metadatos_dc ALTER COLUMN dc_format TYPE VARCHAR(120);
COMMIT;
