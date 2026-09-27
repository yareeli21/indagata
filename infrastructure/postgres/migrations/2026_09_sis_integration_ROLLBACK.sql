-- ============================================================================
-- INDAGATA - ROLLBACK de la migración del SIS (2026_09_sis_integration.sql)
-- Base de datos: aprende_rag | Schema: tt_rag
-- ============================================================================
--
-- Revierte los tres cambios de la migración del SIS. Idempotente.
--
-- ⚠️ ADVERTENCIA: elimina la tabla improvement_opportunity y TODOS sus datos, y
--    la columna ruta_codebook con su contenido. También revierte los estados
--    nuevos a 'etl_pendiente'. Haz respaldo si tienes datos que conservar.
--
-- Ejecutar:
--   $env:PGPASSWORD='ttaprobado'
--   psql -h localhost -U postgres -d aprende_rag -v ON_ERROR_STOP=1 -f postgres/migrations/2026_09_sis_integration_ROLLBACK.sql
-- ============================================================================

SET search_path TO tt_rag, public;

BEGIN;

-- ────────────────────────────────────────────────────────────────────────────
-- 1. Revertir estados nuevos al antiguo 'etl_pendiente'
-- ────────────────────────────────────────────────────────────────────────────

UPDATE instrumento_procesado
SET estado = 'etl_pendiente'
WHERE estado IN ('etl_pendiente_limpieza', 'etl_pendiente_enriquecimiento');

-- Soltar el CHECK actual (nombrado por la migración) de forma segura.
ALTER TABLE instrumento_procesado
    DROP CONSTRAINT IF EXISTS ck_estado_instrumento;

-- Recrear el CHECK original (estados previos a la integración del SIS).
ALTER TABLE instrumento_procesado
    ADD CONSTRAINT ck_estado_instrumento
    CHECK (estado IN (
        'pendiente',
        'metadata_registrado',
        'etl_pendiente',
        'etl_aprobado',
        'en_ingesta',
        'vectorizado',
        'error'
    ));

-- Restaurar el índice parcial de estado a su forma original.
DROP INDEX IF EXISTS idx_instrumento_estado;
CREATE INDEX IF NOT EXISTS idx_instrumento_estado ON instrumento_procesado(estado)
    WHERE estado IN ('metadata_registrado', 'etl_pendiente', 'etl_aprobado',
                     'en_ingesta', 'vectorizado');

-- ────────────────────────────────────────────────────────────────────────────
-- 2. Eliminar la columna ruta_codebook
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE instrumento_procesado
    DROP COLUMN IF EXISTS ruta_codebook;

-- ────────────────────────────────────────────────────────────────────────────
-- 3. Eliminar la tabla improvement_opportunity (y sus índices por CASCADE)
-- ────────────────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS improvement_opportunity;

COMMIT;

-- ============================================================================
-- Verificación (ejecutar por separado):
--   SELECT to_regclass('tt_rag.improvement_opportunity');   -- debe ser NULL
--   SELECT DISTINCT estado FROM tt_rag.instrumento_procesado;
-- ============================================================================
