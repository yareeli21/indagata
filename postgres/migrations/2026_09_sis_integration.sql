-- ============================================================================
-- INDAGATA - Migración incremental: integración del SIS (Survey Intelligence Service)
-- Base de datos: aprende_rag | Schema: tt_rag
-- ============================================================================
--
-- APLICA A: bases de datos EXISTENTES (los init/*.sql solo corren en primer arranque).
-- Es idempotente: puede ejecutarse varias veces sin error.
--
-- Ejecutar (Postgres local; credenciales en backend/.env):
--   $env:PGPASSWORD='ttaprobado'
--   psql -h localhost -U postgres -d aprende_rag -v ON_ERROR_STOP=1 -f postgres/migrations/2026_09_sis_integration.sql
--
-- APLICADA en aprende_rag el 2026-09-17 (verificada: tabla, columna y CHECK OK).
--
-- Cambios:
--   1. Nuevos estados de pipeline: etl_pendiente_limpieza, etl_pendiente_enriquecimiento
--      (reemplazan al antiguo 'etl_pendiente'; migra los datos existentes).
--   2. Columna instrumento_procesado.ruta_codebook (codebook opcional, entrada RAG).
--   3. Tabla improvement_opportunity (oportunidades de mejora emitidas por el SIS).
-- ============================================================================

SET search_path TO tt_rag, public;

BEGIN;

-- ────────────────────────────────────────────────────────────────────────────
-- 1. NUEVOS ESTADOS DE PIPELINE
-- ────────────────────────────────────────────────────────────────────────────

-- 1a. Migrar datos existentes con el estado antiguo 'etl_pendiente' al primer
--     estado del nuevo flujo de dos caminos (limpieza).
UPDATE instrumento_procesado
SET estado = 'etl_pendiente_limpieza'
WHERE estado = 'etl_pendiente';

-- 1b. Soltar el CHECK existente sobre 'estado' (nombre autogenerado) de forma dinámica.
DO $$
DECLARE
    v_constraint_name text;
BEGIN
    SELECT con.conname INTO v_constraint_name
    FROM pg_constraint con
    JOIN pg_class rel   ON rel.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = rel.relnamespace
    WHERE ns.nspname = 'tt_rag'
      AND rel.relname = 'instrumento_procesado'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%estado%'
    LIMIT 1;

    IF v_constraint_name IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE tt_rag.instrumento_procesado DROP CONSTRAINT %I',
            v_constraint_name
        );
    END IF;
END $$;

-- 1c. Recrear el CHECK con los estados nuevos.
ALTER TABLE instrumento_procesado
    ADD CONSTRAINT ck_estado_instrumento
    CHECK (estado IN (
        'pendiente',
        'metadata_registrado',
        'etl_pendiente_limpieza',
        'etl_pendiente_enriquecimiento',
        'etl_aprobado',
        'en_ingesta',
        'vectorizado',
        'error'
    ));

-- ────────────────────────────────────────────────────────────────────────────
-- 2. COLUMNA ruta_codebook (codebook opcional; entrada RAG del SIS, Nivel 2)
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE instrumento_procesado
    ADD COLUMN IF NOT EXISTS ruta_codebook TEXT;

COMMENT ON COLUMN instrumento_procesado.ruta_codebook IS
    'Codebook opcional (solo encuestas). Se pasa como fuente RAG al SIS (activo en Nivel 2).';

-- ────────────────────────────────────────────────────────────────────────────
-- 3. TABLA improvement_opportunity
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS improvement_opportunity (
    opportunity_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id     INTEGER NOT NULL,
    sis_opportunity_id TEXT,
    scope              VARCHAR(30) NOT NULL
        CHECK (scope IN ('survey', 'pipeline', 'future_analysis',
                         'validation_rule', 'quality_heuristic', 'pattern')),
    titulo             TEXT NOT NULL,
    descripcion        TEXT NOT NULL,
    evidencia          JSONB DEFAULT '[]'::jsonb,
    proposed_rule      JSONB,
    confianza          NUMERIC(4,3) CHECK (confianza IS NULL OR (confianza >= 0 AND confianza <= 1)),
    generado_por       VARCHAR(60),
    estado             VARCHAR(20) NOT NULL DEFAULT 'proposed'
        CHECK (estado IN ('proposed', 'under_review', 'accepted', 'promoted', 'rejected')),
    creado_en          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

COMMENT ON TABLE improvement_opportunity IS
    'Recomendaciones de mejora del SIS. El SIS emite proposed; la promocion a regla activa es gobernanza humana.';

CREATE INDEX IF NOT EXISTS idx_improvement_instrumento ON improvement_opportunity(instrumento_id);
CREATE INDEX IF NOT EXISTS idx_improvement_scope       ON improvement_opportunity(scope);
CREATE INDEX IF NOT EXISTS idx_improvement_estado      ON improvement_opportunity(estado);

-- ────────────────────────────────────────────────────────────────────────────
-- 4. Actualizar el índice parcial de estado (si existe) para los nuevos valores
-- ────────────────────────────────────────────────────────────────────────────

DROP INDEX IF EXISTS idx_instrumento_estado;
CREATE INDEX IF NOT EXISTS idx_instrumento_estado ON instrumento_procesado(estado)
    WHERE estado IN ('metadata_registrado', 'etl_pendiente_limpieza',
                     'etl_pendiente_enriquecimiento', 'etl_aprobado',
                     'en_ingesta', 'vectorizado');

COMMIT;

-- ============================================================================
-- Verificación (opcional, ejecutar por separado):
--   SELECT DISTINCT estado FROM tt_rag.instrumento_procesado;
--   \d tt_rag.improvement_opportunity
-- ============================================================================
