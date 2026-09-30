-- ============================================================
-- INDAGATA - Esquema de base de datos (PostgreSQL)
--
-- Generado a partir del diagrama entregado, con las correcciones
-- de normalización discutidas:
--   - PK simples en USUARIO, KPI e INSTRUMENTO_PROCESADO
--     (antes compuestas o inexistentes)
--   - Catálogo KPI <-> VARIABLE separado en tabla puente N:M,
--     en vez de columnas repetidas VARIABLE_1..6
--   - KPI_INFERIDO como tabla asociativa N:M entre
--     INSTRUMENTO_PROCESADO y KPI, con atributos propios
--   - VALOR_VARIABLE_INFERIDO separado de KPI_INFERIDO para
--     almacenar el valor de cada variable usada en la inferencia
--
-- Pendiente de decidir fuera de este script (no se puede resolver
-- solo con SQL):
--   - Columnas reales de METADATOS_ENRIQUECIDOS_ENTREVISTAS y PROMPTS
--   - Validación de que tipo_instrumento coincida con la tabla de
--     metadatos enriquecidos que se llena (regla de negocio -> FastAPI)
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- USUARIO
-- ------------------------------------------------------------
CREATE TABLE usuario (
    usuario_id      SERIAL PRIMARY KEY,
    nombre          VARCHAR(255) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    rol             VARCHAR(255),
    fecha_registro  TIMESTAMP NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- RAW_DATA
-- ------------------------------------------------------------
CREATE TABLE raw_data (
    id_crudo            SERIAL PRIMARY KEY,
    id_owner            INTEGER NOT NULL REFERENCES usuario(usuario_id),
    tipo_instrumento    VARCHAR(30) NOT NULL
        CHECK (tipo_instrumento IN ('encuesta', 'entrevista', 'prueba_estandarizada')),
    nombre_archivo      TEXT NOT NULL,
    ruta                TEXT NOT NULL,
    fecha_carga         TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_raw_data_owner ON raw_data(id_owner);
CREATE INDEX idx_raw_data_tipo  ON raw_data(tipo_instrumento);

-- ------------------------------------------------------------
-- METADATOS_DC (Dublin Core) - relación 1:0..1 con RAW_DATA
-- ------------------------------------------------------------
CREATE TABLE metadatos_dc (
    id_crudo        INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    dc_title        TEXT,
    dc_creator      TEXT,
    dc_description  TEXT,
    dc_type         VARCHAR(50),
    dc_date         DATERANGE,
    dc_languaje     CHAR(10),
    dc_coverage     TEXT,
    dc_subject      TEXT,
    dc_publisher    TEXT,
    dc_rights       VARCHAR(25),
    dc_format       VARCHAR(10),
    dc_source       TEXT,
    dc_relation     VARCHAR(255)
);

-- ------------------------------------------------------------
-- Metadatos enriquecidos por tipo de instrumento
-- (1:0..1 con RAW_DATA; solo debe existir fila en la tabla que
--  corresponda a raw_data.tipo_instrumento -- esa coherencia se
--  valida en la aplicación, no aquí)
-- ------------------------------------------------------------
CREATE TABLE metadatos_enriquecidos_encuestas (
    id_crudo                INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    n_respondentes          INTEGER,
    n_poblacion             INTEGER,
    tipo_investigacion      TEXT,
    notas_contextuales      TEXT,
    notas_interpretacion    TEXT,
    secciones               JSONB
);

CREATE TABLE metadatos_enriquecidos_pruebas_estandarizadas (
    id_crudo                        INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    unidad_de_aprendizaje           TEXT NOT NULL,
    mapeo_de_reactivos_por_seccion  TEXT NOT NULL,
    institucion                     TEXT NOT NULL,
    campus                          TEXT,
    grado                           TEXT NOT NULL,
    ciclo_escolar                   TEXT NOT NULL,
    tipo_de_prueba                  TEXT,
    version                         TEXT,
    taxonomia_bloom                 TEXT NOT NULL,
    objetivo_de_evaluacion          TEXT NOT NULL,
    aplicantes                      INTEGER
);

-- Pendiente de especificar: en el diagrama esta tabla sigue como
-- placeholder ("Key/Field/Type" genérico). Queda con la misma forma
-- de sus tablas hermanas para que se complete con las columnas
-- reales de entrevista (duración, entrevistador, guion, etc.).
CREATE TABLE metadatos_enriquecidos_entrevistas (
    id_crudo    INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo) ON DELETE CASCADE
    -- TODO: columnas específicas de entrevista
);

-- ------------------------------------------------------------
-- PROMPTS - también placeholder en el diagrama, sin relación clara
-- a otra tabla. Queda como catálogo independiente.
-- ------------------------------------------------------------
CREATE TABLE prompts (
    prompt_id   SERIAL PRIMARY KEY
    -- TODO: columnas reales (nombre, contenido, version, etc.)
);

-- ------------------------------------------------------------
-- INSTRUMENTO_PROCESADO
-- PK simple (id_procesado); id_crudo es FK normal, no parte de la PK.
-- ------------------------------------------------------------
CREATE TABLE instrumento_procesado (
    id_procesado            SERIAL PRIMARY KEY,
    id_crudo                INTEGER NOT NULL REFERENCES raw_data(id_crudo),
    ruta_de_archivo_limpio  VARCHAR(255),
    ruta_json               TEXT,
    estado                  VARCHAR(50) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN (
            'pendiente',
            'metadata_registrado',
            'etl_pendiente_limpieza',
            'etl_pendiente_enriquecimiento',
            'etl_aprobado',
            'en_ingesta',
            'vectorizado',
            'error'
        )),
    fecha_procesamiento     TIMESTAMP,
    fecha_aprobado          TIMESTAMP,
    -- chroma_id / collection_id referencian el espacio de IDs de
    -- ChromaDB, que vive fuera de Postgres: no hay tabla local que
    -- referenciar, por eso quedan como INTEGER simples, no FK real.
    chroma_id               INTEGER,
    collection_id           INTEGER
);

CREATE INDEX idx_instrumento_procesado_raw    ON instrumento_procesado(id_crudo);
CREATE INDEX idx_instrumento_procesado_estado ON instrumento_procesado(estado);

-- ------------------------------------------------------------
-- Catálogo de KPI y variables (relación N:M vía tabla puente)
-- ------------------------------------------------------------
CREATE TABLE kpi (
    kpi_id              SERIAL PRIMARY KEY,
    nombre_kpi          TEXT NOT NULL,
    descripcion         TEXT,
    categoria           TEXT,
    ambito              TEXT,
    url_documentacion   TEXT,
    formula             TEXT
);

CREATE TABLE variable (
    variable_id     SERIAL PRIMARY KEY,
    nombre_variable TEXT NOT NULL,
    descripcion     TEXT,
    tipo_dato       VARCHAR(20) NOT NULL
        CHECK (tipo_dato IN ('entero', 'decimal', 'texto', 'booleano')),
    unidad          TEXT
);

CREATE TABLE kpi_variable (
    kpi_id      INTEGER NOT NULL REFERENCES kpi(kpi_id),
    variable_id INTEGER NOT NULL REFERENCES variable(variable_id),
    PRIMARY KEY (kpi_id, variable_id)
);

-- ------------------------------------------------------------
-- KPI inferido por instrumento procesado
-- (tabla asociativa N:M instrumento_procesado <-> kpi,
--  con atributos propios de la inferencia)
-- ------------------------------------------------------------
CREATE TABLE kpi_inferido (
    id_procesado        INTEGER NOT NULL REFERENCES instrumento_procesado(id_procesado),
    kpi_id              INTEGER NOT NULL REFERENCES kpi(kpi_id),
    puntuacion_llm      NUMERIC,
    puntuacion_rag      NUMERIC,
    razon               TEXT,
    resultado           NUMERIC,
    fecha_inferencia    TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (id_procesado, kpi_id)
);

CREATE INDEX idx_kpi_inferido_kpi ON kpi_inferido(kpi_id);

-- ------------------------------------------------------------
-- Valores de cada variable usada en un KPI inferido.
--
-- valor_numerico / valor_texto / valor_booleano: exactamente una
-- debe llenarse, según variable.tipo_dato. El CHECK de abajo solo
-- garantiza "exactamente una columna llena"; que sea la columna
-- correcta según tipo_dato se valida en la aplicación, porque un
-- CHECK no puede leer una columna de otra tabla.
-- ------------------------------------------------------------
CREATE TABLE valor_variable_inferido (
    id_procesado        INTEGER NOT NULL,
    kpi_id              INTEGER NOT NULL,
    variable_id         INTEGER NOT NULL REFERENCES variable(variable_id),
    valor_numerico      NUMERIC,
    valor_texto         TEXT,
    valor_booleano      BOOLEAN,
    confianza_variable  NUMERIC,
    PRIMARY KEY (id_procesado, kpi_id, variable_id),
    FOREIGN KEY (id_procesado, kpi_id)
        REFERENCES kpi_inferido(id_procesado, kpi_id) ON DELETE CASCADE,
    CHECK (num_nonnulls(valor_numerico, valor_texto, valor_booleano) = 1)
);

COMMIT;