-- ============================================================================
-- INDAGATA - Migración incremental: tiempos de cómputo de cada paso del procesamiento
-- Base de datos: indagata_db | Schema: tt_rag
-- ============================================================================
--
-- APLICA A: bases de datos EXISTENTES (los init/*.sql solo corren en primer arranque).
-- Es idempotente: puede ejecutarse varias veces sin error.
--
-- Ejecutar (Docker):
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_15_tiempo_proceso.sql
--
-- Cambio:
--   Tabla nueva `tiempo_proceso`: una fila por operación automática de un instrumento (carga, limpieza,
--   metadatos, aprobación, perfil, KPIs, documento, indexación…) con su inicio, fin y duración. Las fechas
--   que ya existían (fecha_carga, fecha_confirmacion…) mezclan el tiempo de la máquina con el tiempo que la
--   investigadora tarda en decidir; esta tabla registra solo el cómputo, para estimar cuánto tardaría el
--   procesamiento en un servidor (25 oct 2026).
SET search_path TO tt_rag, public;

BEGIN;
CREATE TABLE IF NOT EXISTS tiempo_proceso (
    tiempo_proceso_id SERIAL       PRIMARY KEY,
    id_crudo          INTEGER      NOT NULL REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    servicio          VARCHAR(40)  NOT NULL,
    paso              VARCHAR(60)  NOT NULL,
    inicio            TIMESTAMP    NOT NULL,
    fin               TIMESTAMP    NOT NULL,
    duracion_ms       INTEGER      NOT NULL,
    detalle           JSONB        NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_tiempo_proceso_crudo ON tiempo_proceso(id_crudo, inicio);
COMMIT;
