-- ============================================================================
-- INDAGATA - Migración incremental: caché de respuestas del chat y fuentes de KPIs
-- Base de datos: indagata_db | Schema: tt_rag
-- ============================================================================
--
-- APLICA A: bases de datos EXISTENTES (los init/*.sql solo corren en primer arranque).
-- Es idempotente: puede ejecutarse varias veces sin error.
--
-- Ejecutar (Docker):
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_13_ajustes.sql
--
-- Cambios:
--   1. rag_log.clave_cache: huella de la consulta (pregunta normalizada, alcance,
--      versión vigente de cada instrumento, contexto y modelo). Una pregunta idéntica
--      se responde con la fila guardada sin llamar a Ollama. rag_log.salida: las
--      fuentes y referencias que se mostraron (para repetirlas tal cual).
--   2. kpi_fuente: fuentes de referencia verificadas de cada KPI (organismo, título,
--      URL). Se carga desde seed/KPI_Fuentes.csv con scripts/seed_kpis.py.
-- ============================================================================

SET search_path TO tt_rag, public;

BEGIN;

ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS clave_cache VARCHAR(64);
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS salida      JSONB;
CREATE INDEX IF NOT EXISTS idx_rag_log_clave_cache ON rag_log(clave_cache);

CREATE TABLE IF NOT EXISTS kpi_fuente (
    kpi_fuente_id  SERIAL   PRIMARY KEY,
    kpi_id         INTEGER  NOT NULL REFERENCES kpi(kpi_id) ON DELETE CASCADE,
    organismo      TEXT     NOT NULL,
    titulo         TEXT     NOT NULL,
    url            TEXT     NOT NULL,
    anio           INTEGER,
    nota           TEXT
);
CREATE INDEX IF NOT EXISTS idx_kpi_fuente_kpi ON kpi_fuente(kpi_id);

COMMIT;
