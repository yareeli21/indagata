-- ============================================================================
-- INDAGATA - Migración incremental: las pruebas estandarizadas ya no se califican
-- Base de datos: indagata_db | Schema: tt_rag
-- ============================================================================
--
-- APLICA A: bases de datos EXISTENTES (los init/*.sql solo corren en primer arranque).
-- Es idempotente: puede ejecutarse varias veces sin error.
--
-- Ejecutar (Docker):
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_16_sin_clave.sql
--
-- Cambio:
--   Se elimina la columna raw_data.raw_archivo_clave. Indagata ya no recibe clave de respuestas: describe lo
--   que contestaron los alumnos (opción más elegida, nulas, no respondidas), sin marcar respuestas como
--   correctas (25 oct 2026). Borra antes las pruebas que se subieron con clave.
SET search_path TO tt_rag, public;

BEGIN;
ALTER TABLE raw_data DROP COLUMN IF EXISTS raw_archivo_clave;
COMMIT;
