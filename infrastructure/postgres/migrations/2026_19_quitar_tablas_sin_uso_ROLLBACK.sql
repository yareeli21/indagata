-- Revierte 2026_19_quitar_tablas_sin_uso.sql: vuelve a crear las cuatro tablas, vacías.
SET search_path TO tt_rag, public;

BEGIN;
-- ── 6. prompts ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prompts (
    prompt_id     SERIAL      PRIMARY KEY,
    tipo          VARCHAR(50) NOT NULL,
    version       VARCHAR(10) NOT NULL,
    contenido     TEXT        NOT NULL,
    coleccion_id  INTEGER     REFERENCES coleccion_vectorial(coleccion_id) ON DELETE SET NULL,  -- colección sobre la que actúa el prompt
    activo        BOOLEAN     DEFAULT TRUE,
    creado_en     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- ── 8. variable ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS variable (
    variable_id     SERIAL PRIMARY KEY,
    nombre_variable TEXT   NOT NULL,
    descripcion     TEXT,
    tipo_dato       VARCHAR(20),
    unidad          TEXT
);

-- ── 9. kpi_variable ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS kpi_variable (
    kpi_id      INTEGER NOT NULL REFERENCES kpi(kpi_id) ON DELETE CASCADE,
    variable_id INTEGER NOT NULL REFERENCES variable(variable_id) ON DELETE CASCADE,
    PRIMARY KEY (kpi_id, variable_id)
);

-- ── 11. valor_variable_inferido ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS valor_variable_inferido (
    id_procesado       INTEGER NOT NULL,
    kpi_id             INTEGER NOT NULL,
    variable_id        INTEGER NOT NULL REFERENCES variable(variable_id) ON DELETE CASCADE,
    valor_numerico     NUMERIC,
    valor_texto        TEXT,
    valor_booleano     BOOLEAN,
    confianza_variable NUMERIC,
    PRIMARY KEY (id_procesado, kpi_id, variable_id),
    FOREIGN KEY (id_procesado, kpi_id) REFERENCES kpi_inferido(id_procesado, kpi_id) ON DELETE CASCADE
);

COMMIT;
