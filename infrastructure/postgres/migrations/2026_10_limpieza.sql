-- ============================================================================
-- INDAGATA - Migración incremental: limpieza de instrumentos (cleaning-service)
-- Base de datos: indagata_db | Schema: tt_rag
-- ============================================================================
--
-- APLICA A: bases de datos EXISTENTES (los init/*.sql solo corren en primer arranque).
-- Es idempotente: puede ejecutarse varias veces sin error.
--
-- Ejecutar (Docker):
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_10_limpieza.sql
--
-- Cambios:
--   1. Tabla limpieza_ejecucion: una fila por ejecución (versión) de la limpieza de
--      un instrumento, con su estado, decisiones y reporte_limpieza (JSONB).
--      El CSV limpio NO va en la base: se guarda como archivo vía storage-service
--      y aquí solo queda su key (ruta_csv_limpio).
--   2. Columna raw_data.raw_archivo_clave: clave de respuestas de las pruebas
--      estandarizadas tabulares (otro archivo crudo, guardado por instrument-service).
-- ============================================================================

SET search_path TO tt_rag, public;

BEGIN;

-- ── 1. limpieza_ejecucion ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS limpieza_ejecucion (
    id_limpieza         SERIAL       PRIMARY KEY,
    id_crudo            INTEGER      NOT NULL REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    version             INTEGER      NOT NULL,
    estado              VARCHAR(30)  NOT NULL DEFAULT 'esperando_decisiones'
                        CHECK (estado IN ('esperando_decisiones', 'confirmada', 'fallida')),
    id_investigador     INTEGER      REFERENCES usuario(usuario_id) ON DELETE SET NULL,
    fecha_creacion      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    fecha_confirmacion  TIMESTAMP,
    ruta_csv_limpio     VARCHAR(255),
    reporte             JSONB        NOT NULL DEFAULT '{}'::jsonb,
    error               TEXT,
    CONSTRAINT uq_limpieza_version UNIQUE (id_crudo, version)
);

CREATE INDEX IF NOT EXISTS idx_limpieza_crudo_estado ON limpieza_ejecucion(id_crudo, estado);

-- ── 2. raw_data.raw_archivo_clave ───────────────────────────────────────────
ALTER TABLE raw_data ADD COLUMN IF NOT EXISTS raw_archivo_clave TEXT;

COMMIT;
