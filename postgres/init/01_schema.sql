-- ============================================================
-- Indagata — Esquema PostgreSQL
-- Registro operativo del pipeline de limpieza,
-- estandarizacion y consulta basado en RAG
-- ============================================================

CREATE SCHEMA IF NOT EXISTS tt_rag;

SET search_path TO tt_rag, public;

-- ── GRUPO 1: Gestión de instrumentos ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS instrumento_procesado (
    instrumento_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              VARCHAR(255) NOT NULL,
    tipo_instrumento    VARCHAR(30)  NOT NULL
                        CHECK (tipo_instrumento IN (
                            'encuesta', 'entrevista', 'prueba_estandarizada'
                        )),
    plataforma          VARCHAR(50),
    ruta_json           TEXT,                       -- NULL hasta estado estandarizado
    ruta_sav            TEXT,                       -- NULL hasta estado estandarizado (solo encuestas)
    ruta_texto_limpio   TEXT,                       -- uso exclusivo del pipeline de estandarización
    estado              VARCHAR(50)  NOT NULL
                        DEFAULT 'recibido'
                        CHECK (estado IN (
                            'recibido', 'limpio', 'estandarizado', 'vectorizado', 'error'
                        )),
    visibilidad         VARCHAR(10)  NOT NULL
                        DEFAULT 'publico'
                        CHECK (visibilidad IN ('publico', 'privado')),
    version             INTEGER      NOT NULL DEFAULT 1,
    schema_version      VARCHAR(10)  DEFAULT '1.0',
    error_detalle       TEXT,                       -- mensaje amigable; solo cuando estado = 'error'
    fecha_procesamiento TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creado_en           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── GRUPO 2: Catálogo de indicadores ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS kpi (
    kpi_id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombrekpi         VARCHAR(255) NOT NULL,
    descripcion       TEXT,
    direccion_deseada TEXT,
    razon             TEXT,
    formula           TEXT,
    umbral_bajo       NUMERIC,
    umbral_medio      NUMERIC,
    umbral_alto       NUMERIC,
    unidad            TEXT,
    activo            BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS instituciones (
    institucion_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre         TEXT,
    pais           TEXT,
    fecha          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS variable (
    variable_id     INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_variable VARCHAR(255) UNIQUE NOT NULL,
    nombre_display  VARCHAR(100) NOT NULL,
    unidad          VARCHAR(20),
    tipo_dato       VARCHAR(30)  NOT NULL
);

CREATE TABLE IF NOT EXISTS pregunta_kpi (
    pregunta_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id   INTEGER NOT NULL,
    codigo_pregunta  VARCHAR(50),
    kpi_id           INTEGER NOT NULL,
    variable_id      INTEGER NOT NULL,
    score_inferencia NUMERIC(4,3)
        CHECK (score_inferencia >= 0 AND score_inferencia <= 1),
    fecha            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    FOREIGN KEY (kpi_id)         REFERENCES kpi(kpi_id),
    FOREIGN KEY (variable_id)    REFERENCES variable(variable_id)
);

CREATE TABLE IF NOT EXISTS kpi_variable (
    kpi_id      INTEGER NOT NULL,
    variable_id INTEGER NOT NULL,
    PRIMARY KEY (kpi_id, variable_id),
    FOREIGN KEY (kpi_id)      REFERENCES kpi(kpi_id),
    FOREIGN KEY (variable_id) REFERENCES variable(variable_id)
);

CREATE TABLE IF NOT EXISTS valor_variable (
    valor_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    variable_id    INTEGER     NOT NULL,
    institucion_id INTEGER     NOT NULL,
    periodo        VARCHAR(10) NOT NULL,
    valor          NUMERIC,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variable_id)    REFERENCES variable(variable_id),
    FOREIGN KEY (institucion_id) REFERENCES instituciones(institucion_id)
);

-- ── GRUPO 3: Catálogo de prompts ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prompt (
    prompt_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo      VARCHAR(20) NOT NULL
              CHECK (tipo IN (
                  'chunking', 'metadatos', 'kpi_inferencia', 'query', 'contextualizacion'
              )),
    version   VARCHAR(20),
    contenido TEXT      NOT NULL,
    fecha     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo    BOOLEAN   NOT NULL DEFAULT TRUE
);

-- ── GRUPO 4: Vectorización y consulta ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS documento_vectorizado (
    documento_vectorizado_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id           INTEGER     NOT NULL,
    prompt_id                INTEGER     NOT NULL,
    vector_id                TEXT        NOT NULL,  -- ID del punto en ChromaDB
    col_id                   TEXT        NOT NULL,  -- colección ChromaDB
    tipo_chunk               VARCHAR(50) NOT NULL
                             CHECK (tipo_chunk IN (
                                 'resumen_instrumento', 'sintesis_hallazgo', 'unidad_semantica'
                             )),
    activo                   BOOLEAN   NOT NULL DEFAULT TRUE,
    fecha_vectorizacion      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    FOREIGN KEY (prompt_id)      REFERENCES prompt(prompt_id)
);

CREATE TABLE IF NOT EXISTS rag_log (
    rag_log_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pregunta         TEXT        NOT NULL,
    contexto         TEXT,
    respuesta        TEXT,
    modelo_llm       VARCHAR(50),
    modelo_embedding VARCHAR(50),
    latencia_ms      INTEGER CHECK (latencia_ms >= 0),
    fecha            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Usuarios ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS usuarios (
    usuario_id    INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario       VARCHAR(50)  UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    creado_en     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── Archivos crudos ───────────────────────────────────────────────────────────
-- Un registro por cada versión del archivo subido.
-- El registro con mayor raw_data_id para un instrumento_id es la versión actual.

CREATE TABLE IF NOT EXISTS raw_data (
    raw_data_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id      INTEGER      NOT NULL,
    usuario_id          INTEGER      NOT NULL,
    subido              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    tipo_de_instrumento VARCHAR(30)  NOT NULL,
    raw_archivo         TEXT         NOT NULL,  -- ruta relativa desde PROJECT_ROOT
    nombre_original     TEXT         NOT NULL,
    tipo_mime           VARCHAR(100),
    tamano_bytes        BIGINT       NOT NULL,
    hash_md5            VARCHAR(32),
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id)     REFERENCES usuarios(usuario_id)
);

-- Unicidad de archivo por usuario: el mismo investigador no puede subir
-- el mismo archivo dos veces para el mismo instrumento.
-- Dos investigadores distintos SÍ pueden tener el mismo archivo.
CREATE UNIQUE INDEX IF NOT EXISTS uidx_raw_data_hash_usuario
    ON raw_data (hash_md5, usuario_id)
    WHERE hash_md5 IS NOT NULL;

-- ── Permisos de propietario ───────────────────────────────────────────────────
-- Solo existe el rol 'propietario'. La visibilidad pública/privada
-- controla el acceso de lectura. Esta tabla controla quién puede modificar.

CREATE TABLE IF NOT EXISTS permiso_instrumento (
    permiso_id     INTEGER     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id INTEGER     NOT NULL,
    usuario_id     INTEGER     NOT NULL,
    rol            VARCHAR(20) NOT NULL DEFAULT 'propietario'
                   CHECK (rol = 'propietario'),
    otorgado_en    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (instrumento_id, usuario_id),
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id)     REFERENCES usuarios(usuario_id) ON DELETE CASCADE
);

-- ── Log del pipeline de limpieza ──────────────────────────────────────────────
-- EXCLUSIVAMENTE INTERNO DEL PIPELINE. La interfaz no consulta esta tabla.
-- Propósitos:
--   1. Lock optimista: resultado='en_proceso' bloquea doble procesamiento.
--   2. Trazabilidad técnica: modelo, prompt, extractor, métricas.
--   3. Diagnóstico de errores: error_mensaje con detalle completo.
-- La interfaz solo lee instrumento_procesado.error_detalle (mensaje amigable).

CREATE TABLE IF NOT EXISTS pipeline_limpieza_log (
    log_id          INTEGER     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id  INTEGER     NOT NULL,
    iniciado_en     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finalizado_en   TIMESTAMP,
    resultado       VARCHAR(20) NOT NULL DEFAULT 'en_proceso'
                    CHECK (resultado IN ('en_proceso', 'exitoso', 'error')),
    extractor_usado VARCHAR(50),
    modelo_llm      VARCHAR(100),
    prompt_version  VARCHAR(20),
    tokens_entrada  INTEGER,
    tokens_salida   INTEGER,
    latencia_ms     INTEGER,
    segmentos       INTEGER,    -- número de segmentos si el texto fue dividido
    error_mensaje   TEXT,       -- detalle técnico; nunca se expone en la interfaz
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

-- ── Índices ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_kpi_id
    ON pregunta_kpi(kpi_id);

CREATE INDEX IF NOT EXISTS idx_instrumento_id_pregunta
    ON pregunta_kpi(instrumento_id);

CREATE INDEX IF NOT EXISTS idx_codigo_pregunta
    ON pregunta_kpi(codigo_pregunta);

CREATE INDEX IF NOT EXISTS idx_id_variable
    ON valor_variable(variable_id);

CREATE INDEX IF NOT EXISTS idx_id_institucion
    ON valor_variable(institucion_id);

CREATE INDEX IF NOT EXISTS idx_vector_id
    ON documento_vectorizado(vector_id);

CREATE INDEX IF NOT EXISTS idx_instrumento_id_docvec
    ON documento_vectorizado(instrumento_id);

CREATE INDEX IF NOT EXISTS idx_fecha_rag
    ON rag_log(fecha);

-- Índice para el catálogo: búsqueda de texto en nombre y filtro por fechas
CREATE INDEX IF NOT EXISTS idx_instrumento_nombre_fts
    ON instrumento_procesado USING gin(to_tsvector('spanish', nombre));

CREATE INDEX IF NOT EXISTS idx_instrumento_creado_en
    ON instrumento_procesado(creado_en);

CREATE INDEX IF NOT EXISTS idx_instrumento_tipo
    ON instrumento_procesado(tipo_instrumento);

CREATE INDEX IF NOT EXISTS idx_instrumento_visibilidad
    ON instrumento_procesado(visibilidad);

-- Índice para resolver propietario en listados
CREATE INDEX IF NOT EXISTS idx_permiso_usuario
    ON permiso_instrumento(usuario_id);

-- Índices para el pipeline de limpieza (lock optimista)
CREATE INDEX IF NOT EXISTS idx_limpieza_log_instrumento
    ON pipeline_limpieza_log(instrumento_id);

CREATE INDEX IF NOT EXISTS idx_limpieza_log_en_proceso
    ON pipeline_limpieza_log(instrumento_id)
    WHERE resultado = 'en_proceso';

-- ── Configuración de búsqueda ─────────────────────────────────────────────────
ALTER DATABASE aprende_rag SET search_path TO tt_rag, public;
