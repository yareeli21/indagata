-- ============================================================
-- Aprende RAG - Esquema PostgreSQL
-- Registro operativo del pipeline de limpieza,
-- estandarizacion y consulta basado en RAG
-- ============================================================

-- ============================================================
-- CONFIGURACIÓN INICIAL
-- ============================================================

CREATE SCHEMA IF NOT EXISTS tt_rag;

SET search_path TO tt_rag, public;

-- -- GRUPO 1: Gestion de instrumentos ------------------------

CREATE TABLE IF NOT EXISTS instrumento_procesado (
    instrumento_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              VARCHAR(255) NOT NULL,
    plataforma          VARCHAR(50),
    ruta_json           TEXT,
    ruta_sav            TEXT,
    metadatos           JSONB,
    estado              VARCHAR(50) NOT NULL 
                        DEFAULT 'ingresado'
                        CHECK(estado IN ('ingresado',
                          'limpio',
                          'estandarizado',
                          'vectorizado',
                          'error')),
    -- estados: ingresado, limpio, estandarizado, vectorizado
    fecha_procesamiento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -- GRUPO 2: Catalogo de indicadores ------------------------

CREATE TABLE IF NOT EXISTS kpi (
    kpi_id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombrekpi               VARCHAR(255) NOT NULL,
    descripcion             TEXT,
    direccion_deseada       TEXT,
    razon                   TEXT,
    formula                 TEXT,
    umbral_bajo             NUMERIC,
    umbral_medio            NUMERIC,
    umbral_alto             NUMERIC,
    unidad                  TEXT, --para evitar adivinar qué unidad es
    activo                  BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS instituciones (
    institucion_id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre            TEXT,
    pais              TEXT,
    fecha             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS variable (
    variable_id	        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_variable	    VARCHAR(255) UNIQUE NOT NULL,
    nombre_display	    VARCHAR(100) NOT NULL,
    unidad	            VARCHAR(20),
    tipo_dato	        VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS pregunta_kpi (
    pregunta_id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id          INTEGER NOT NULL, 
    codigo_pregunta         VARCHAR(50),
    kpi_id                  INTEGER NOT NULL, 
    variable_id             INTEGER NOT NULL,  -- VARIABLE ESTANDARIZADA ASOCIADA A LA PREGUNTA
    score_inferencia        NUMERIC(4,3)-- confianza del LLM en la asignacion (0.000 a 1.000)
        CHECK(score_inferencia >=0 AND score_inferencia <=1),
    fecha                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    FOREIGN KEY (kpi_id) REFERENCES kpi(kpi_id),
    FOREIGN KEY (variable_id) REFERENCES variable(variable_id)
);

CREATE TABLE IF NOT EXISTS kpi_variable (
    kpi_id	INTEGER NOT NULL,
    variable_id	INTEGER NOT NULL,
    PRIMARY KEY (kpi_id, variable_id),
    FOREIGN KEY (kpi_id) REFERENCES kpi(kpi_id),
    FOREIGN KEY (variable_id) REFERENCES variable(variable_id)
);

CREATE TABLE IF NOT EXISTS valor_variable(
    valor_id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    variable_id         INTEGER NOT NULL,
    institucion_id      INTEGER NOT NULL,
    periodo             VARCHAR(10) NOT NULL,
    valor               NUMERIC,
    fecha_registro      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variable_id) REFERENCES variable(variable_id),
    FOREIGN KEY (institucion_id) REFERENCES instituciones(institucion_id)

);

-- -- GRUPO 3: Catalogo de prompts ----------------------------

CREATE TABLE IF NOT EXISTS prompt (
    prompt_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo      VARCHAR(20) NOT NULL
               CHECK(
                tipo IN(
                    'chunking',
                    'metadatos',
                    'kpi_inferencia',
                    'query',
                    'contextualizacion'
                )
               ),
               -- chunking, metadatos, kpi_inferencia, query, contextualizacion
    version    VARCHAR(20),
    contenido TEXT NOT NULL,
    fecha     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo    BOOLEAN NOT NULL DEFAULT TRUE
);

-- -- GRUPO 4: Vectorizacion y consulta -----------------------

CREATE TABLE IF NOT EXISTS documento_vectorizado (
    documento_vectorizado_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id      INTEGER NOT NULL, 
    prompt_id           INTEGER NOT NULL,
    -- version del prompt que genero este chunk
    vector_id           TEXT NOT NULL, --porque el id viene de chroma y suele ser texto
    -- ID del punto en ChromaDB
    col_id              TEXT NOT NULL, --igual como sucede en vector_id
    -- coleccion ChromaDB: col_encuestas, col_entrevistas, col_pruebas_estandarizadas
    tipo_chunk          VARCHAR(50) NOT NULL
                        CHECK(
                            tipo_chunk IN (
                                'resumen_instrumento',
                                'sintesis_hallazgo',
                                'unidad_semantica'
                            )
                        ), 
                        --unidad_semántica, resumen,  metadatos
    -- resumen_instrumento, unidad_semantica
    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_vectorizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE, --si se elimina un instr, también el vectorizado
    FOREIGN KEY (prompt_id) REFERENCES prompt(prompt_id)
);

CREATE TABLE IF NOT EXISTS rag_log (
    rag_log_id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pregunta         TEXT NOT NULL,
    contexto         TEXT,
    -- chunks recuperados enviados al LLM como contexto
    respuesta        TEXT,
    modelo_llm       VARCHAR(50),
    modelo_embedding VARCHAR(50),
    latencia_ms      INTEGER
       CHECK (latencia_ms >= 0),
    fecha            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-----------TABLA USUARIOS PARA LA AUTENTICACION DE USUARIO--------------

CREATE TABLE usuarios (
    usuario_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

------------------------TABLA PARA ALMACENAR DATOS CRUDOS ----------------------------
CREATE TABLE raw_data (
    raw_data_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id      INTEGER NOT NULL,
    usuario_id          INTEGER NOT NULL REFERENCES usuarios(usuario_id),
    subido              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo_de_instrumento  VARCHAR(30) NOT NULL,
    raw_archivo         TEXT NOT NULL,---ruta de el archivo 
    nombre_original     TEXT NOT NULL,
    tipo_mime           VARCHAR(100), --el verdadero tipo de archivo
    tamano_bytes        BIGINT NOT NULL,--saber qué tan pesado es el archivo subido, incluso puede ponerse un límite de peso
    hash_md5            VARCHAR(32) UNIQUE,
    --para subir archivos iguales internamente, pero con nombre distinto, puede servir para detectar duplicados
    
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

--los índices sirven para datos que se requieran buscar de forma más específica

CREATE INDEX idx_kpi_id
ON pregunta_kpi(kpi_id);

CREATE INDEX idx_instrumento_id
ON pregunta_kpi(instrumento_id);

CREATE INDEX idx_id_variable
ON valor_variable(variable_id);

CREATE INDEX idx_id_institucion
ON valor_variable(institucion_id);

CREATE INDEX idx_vector_id
ON documento_vectorizado(vector_id);

CREATE INDEX idx_instrumento_id_docvec
ON documento_vectorizado(instrumento_id);

CREATE INDEX idx_fecha
ON rag_log(fecha);

CREATE INDEX idx_codigo_pregunta
ON pregunta_kpi(codigo_pregunta);

-- al final de 01_schema.sql, después de crear tablas e índices
ALTER DATABASE aprende_rag SET search_path TO tt_rag, public;