-- ============================================================================
-- INDAGATA - Migración incremental: versiones del conocimiento (knowledge-service)
-- Base de datos: indagata_db | Schema: tt_rag
-- ============================================================================
--
-- APLICA A: bases de datos EXISTENTES (los init/*.sql solo corren en primer arranque).
-- Es idempotente: puede ejecutarse varias veces sin error.
--
-- Ejecutar (Docker):
--   docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_11_conocimiento.sql
--
-- Cambios:
--   1. Tabla version_conocimiento: UNA fila por versión del conocimiento de un
--      instrumento, que avanza por el wizard:
--        perfil_aprobado → kpis_confirmados → borrador → vigente (→ reemplazado)
--      - perfil:          perfil semántico (lo único que se usa para asociar KPIs).
--      - decisiones_kpi:  KPIs propuestos, aceptados Y rechazados, con score,
--                         componentes, evidencia y justificación.
--      - ruta_documento:  key en storage-service del documento final (insumo del RAG).
--      El JSON técnico (registro técnico) NO va aquí: sigue en storage como siempre.
-- ============================================================================

SET search_path TO tt_rag, public;

BEGIN;

CREATE TABLE IF NOT EXISTS version_conocimiento (
    id_version          SERIAL       PRIMARY KEY,
    id_crudo            INTEGER      NOT NULL REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    version             INTEGER      NOT NULL,
    estado              VARCHAR(20)  NOT NULL DEFAULT 'perfil_aprobado'
                        CHECK (estado IN ('perfil_aprobado', 'kpis_confirmados', 'borrador', 'vigente', 'reemplazado')),
    perfil              JSONB        NOT NULL,
    decisiones_kpi      JSONB        NOT NULL DEFAULT '[]'::jsonb,
    ruta_documento      VARCHAR(255),
    esquema_version     VARCHAR(10),
    avisos              JSONB        NOT NULL DEFAULT '[]'::jsonb,
    sha256              VARCHAR(64),
    id_limpieza         INTEGER      REFERENCES limpieza_ejecucion(id_limpieza) ON DELETE SET NULL,
    id_usuario          INTEGER      REFERENCES usuario(usuario_id) ON DELETE SET NULL,
    fecha_creacion      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    fecha_kpis          TIMESTAMP,
    fecha_documento     TIMESTAMP,
    fecha_publicacion   TIMESTAMP,
    CONSTRAINT uq_version_conocimiento UNIQUE (id_crudo, version)
);

CREATE INDEX IF NOT EXISTS idx_version_conocimiento_crudo_estado ON version_conocimiento(id_crudo, estado);

COMMIT;
