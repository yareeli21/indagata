-- ============================================================
-- Indagata — Esquema PostgreSQL (fuente única de verdad)
--
-- Flujo del pipeline:
--   1. Llega un instrumento y se registra como crudo en raw_data.
--      Se suben DOS archivos:
--        - el respondido (tabular con respuestas)   → raw_archivo
--        - el original (solo preguntas, sin datos)  → raw_archivo_original
--      El original servirá para vectorización y búsqueda semántica futura.
--   2. raw_data es la tabla PADRE. De ella cuelgan por id_crudo (PK = FK):
--        - metadatos_dc
--        - metadatos_enriquecidos_encuestas
--        - metadatos_enriquecidos_entrevistas
--        - metadatos_enriquecidos_pruebas
--   3. Limpieza sencilla de ciencia de datos → se llenan DC y específicos.
--   4. Se genera un JSON estructurado (instrumento_procesado).
--   5. Resumen del JSON + instrumento original → vectorización → se buscan
--      KPIs relacionados. Al aceptar los KPIs propuestos, se actualiza el JSON
--      para incluir los KPIs asociados.
--
-- Referencias a Chroma:
--   - instrumento_procesado.collection_id → colección donde vive el instrumento
--   - prompts.collection_id               → colección sobre la que actúa el prompt
--   - documento_vectorizado.collection_id → colección del chunk
--   - documento_vectorizado.chunk_id      → ID del punto/vector del chunk en Chroma
--
-- Control de borrado: NO hay tabla de permisos. Se autoriza por el campo
-- usuario.rol (p. ej. 'investigador' puede borrar sus instrumentos, 'admin'
-- cualquiera). La validación la hace la aplicación.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS tt_rag;

SET search_path TO tt_rag, public;

BEGIN;

-- ── 1. Usuarios ───────────────────────────────────────────────────────────────
-- El rol autoriza la carga y el borrado de instrumentos (validado en la app).

CREATE TABLE IF NOT EXISTS usuario (
    usuario_id     SERIAL       PRIMARY KEY,
    nombre         VARCHAR(255) NOT NULL,
    email          VARCHAR(255) UNIQUE NOT NULL,
    password_hash  TEXT         NOT NULL,
    rol            VARCHAR(50),
    fecha_registro TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ── 2. raw_data (TABLA PADRE) ─────────────────────────────────────────────────
-- Un registro por instrumento recibido en crudo. Guarda tanto el archivo
-- respondido (raw_archivo) como el instrumento original sin respuestas
-- (raw_archivo_original), que se usará para la vectorización semántica.

CREATE TABLE IF NOT EXISTS raw_data (
    id_crudo             SERIAL      PRIMARY KEY,
    id_owner             INTEGER     NOT NULL REFERENCES usuario(usuario_id) ON DELETE CASCADE,
    tipo_instrumento     VARCHAR(50) NOT NULL,
    nombre_archivo       TEXT        NOT NULL,
    raw_archivo          TEXT        NOT NULL,  -- ruta del archivo respondido (crudo con datos)
    raw_archivo_original TEXT,                  -- ruta del instrumento original (solo preguntas)
    raw_archivo_clave    TEXT,                  -- clave de respuestas (pruebas estandarizadas tabulares)
    fecha_carga          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- ── 3. instrumento_procesado ──────────────────────────────────────────────────
-- Hija de raw_data por id_crudo. PK propia (id_instrumento) para que las tablas
-- de KPIs y vectorización puedan relacionarse con ella.

CREATE TABLE IF NOT EXISTS instrumento_procesado (
    id_instrumento         SERIAL       PRIMARY KEY,
    id_crudo               INTEGER      NOT NULL REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    ruta_de_archivo_limpio VARCHAR(255),
    ruta_json              TEXT,
    estado                 VARCHAR(50)  NOT NULL DEFAULT 'recibido'
                           CHECK (estado IN (
                               'recibido',
                               'limpieza_en_proceso',
                               'limpio',
                               'metadatos_registrados',
                               'estandarizado',
                               'vectorizado',
                               'error'
                           )),
    fecha_procesamiento    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    fecha_aprobado         TIMESTAMP
);

-- ── 4. metadatos_dc (Dublin Core adaptado) — hija de raw_data ─────────────────

CREATE TABLE IF NOT EXISTS metadatos_dc (
    id_crudo       INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    dc_title       TEXT NOT NULL,
    dc_creator     TEXT,
    dc_description  TEXT,
    dc_type        VARCHAR(50),
    dc_date        VARCHAR(100),
    dc_language    VARCHAR(10),
    dc_coverage    TEXT,
    dc_subject     TEXT,
    dc_publisher   TEXT,
    dc_rights      VARCHAR(255),
    dc_format      VARCHAR(50),
    dc_source      TEXT,
    dc_relation    TEXT
);

-- ── 5. Metadatos enriquecidos (separados por tipo) — hijas de raw_data ────────

CREATE TABLE IF NOT EXISTS metadatos_enriquecidos_encuestas (
    id_crudo             INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    n_respondentes       INTEGER,
    n_poblacion          INTEGER,
    objetivo             TEXT,
    carrera              TEXT,
    poblacion_objetivo   TEXT,
    constructo_principal TEXT,
    palabras_clave       JSONB,
    dimensiones          JSONB,
    notas_contextuales   TEXT,
    notas_interpretacion TEXT
);  

CREATE TABLE IF NOT EXISTS metadatos_enriquecidos_entrevistas (
    id_crudo             INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    identificador_propio TEXT,
    objetivo             TEXT,
    metodologia          TEXT,
    institucion          TEXT,
    derechos             TEXT
);

CREATE TABLE IF NOT EXISTS metadatos_enriquecidos_pruebas (
    id_crudo                       INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    unidad_de_aprendizaje          TEXT,
    mapeo_de_reactivos_por_seccion JSONB,
    institucion                    TEXT,
    campus                         TEXT,
    grado                          TEXT,
    grupo                          TEXT,
    ciclo_escolar                  TEXT,
    tipo_de_prueba                 TEXT,
    version                        TEXT,
    taxonomia_bloom                TEXT,
    nivel_educativo                TEXT,
    objetivo_de_evaluacion         TEXT,
    subareas                       TEXT,
    competencias                   TEXT
);

-- ── 5b. coleccion_vectorial (config de la colección Chroma) ───────────────────
-- Una colección Chroma por configuración de embedding. Guarda los parámetros con
-- los que se vectorizó, para poder reindexar de forma reproducible. La referencian
-- prompts y documento_vectorizado.

CREATE TABLE IF NOT EXISTS coleccion_vectorial (
    coleccion_id    SERIAL      PRIMARY KEY,
    nombre          TEXT        UNIQUE NOT NULL,  -- nombre/UUID de la colección en Chroma
    embedding_model VARCHAR(100),
    chunk_size      INTEGER,
    chunk_overlap   INTEGER,
    creado_en       TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

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

-- ── 7. kpi ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS kpi (
    kpi_id                                SERIAL PRIMARY KEY,
    nombre                                TEXT   NOT NULL,  -- CSV: KPI
    polaridad_rendimiento                 TEXT,             -- CSV: Polaridad_Rendimiento
    tipo_objetivo_estrategico             TEXT,             -- CSV: Tipo_Objetivo_Estrategico
    formula_metrica_calculo               TEXT,             -- CSV: Formula_Metrica_Calculo
    descripcion_ampliada_educativa        TEXT,             -- CSV: Descripcion_Ampliada_Educativa (significado UI)
    comportamiento_direccional_causalidad TEXT,             -- CSV: Comportamiento_Direccional_y_Causalidad
    razon_estrategica_decisiones          TEXT,             -- CSV: Razon_Estrategica_y_Decisiones
    texto_contexto_rag_vectorial          TEXT   NOT NULL   -- CSV: Texto_Contexto_RAG_Vectorial (texto a embeber)
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

-- ── 10. kpi_inferido (sin puntuación LLM ni RAG) ──────────────────────────────

CREATE TABLE IF NOT EXISTS kpi_inferido (
    id_procesado     INTEGER NOT NULL REFERENCES instrumento_procesado(id_instrumento) ON DELETE CASCADE,
    kpi_id           INTEGER NOT NULL REFERENCES kpi(kpi_id) ON DELETE CASCADE,
    razon            TEXT,
    resultado        NUMERIC,
    fecha_inferencia TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_procesado, kpi_id)
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

-- ── 12. rag_log ───────────────────────────────────────────────────────────────

-- Una fila por consulta al chat. decision_dominio: dentro | fuera | privacidad |
-- manipulacion | sin_informacion | ayuda; ruta: semantica | estructurada | mixta |
-- ayuda. Las métricas (RAGAS) se calculan después de responder y se agregan aquí.
CREATE TABLE IF NOT EXISTS rag_log (
    rag_log_id       SERIAL      PRIMARY KEY,
    pregunta         TEXT        NOT NULL,
    respuesta        TEXT,
    modelo_usado     VARCHAR(100),
    chunks_usados    INTEGER,
    latencia_ms      INTEGER,
    timestamp        TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    decision_dominio VARCHAR(20),
    motivo           TEXT,
    score_max        REAL,
    ruta             VARCHAR(20),
    instrumentos     JSONB       NOT NULL DEFAULT '[]'::jsonb,
    contexto_usado   JSONB       NOT NULL DEFAULT '[]'::jsonb,
    metricas         JSONB,
    modelo_juez      VARCHAR(100),
    fecha_metricas   TIMESTAMP
);

-- ── 13. documento_vectorizado (chunks vectorizados de cada instrumento) ───────
-- Un instrumento genera muchos chunks; cada fila es un chunk con su vector en
-- Chroma (chroma_vector_id). El ON DELETE CASCADE permite borrar/reindexar los
-- vectores de un instrumento específico.

CREATE TABLE IF NOT EXISTS documento_vectorizado (
    documento_vectorizado_id SERIAL      PRIMARY KEY,
    instrumento_id           INTEGER     REFERENCES instrumento_procesado(id_instrumento) ON DELETE CASCADE,
    coleccion_id             INTEGER     REFERENCES coleccion_vectorial(coleccion_id) ON DELETE SET NULL,
    chroma_vector_id         TEXT,                        -- ID del punto/vector del chunk en Chroma (string)
    chunk_index              INTEGER,
    seccion                  TEXT,
    chunk_texto              TEXT        NOT NULL,
    chunk_metadata           JSONB       DEFAULT '{}'::jsonb,
    n_tokens                 INTEGER,
    almacenado_en            TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- ── 14. kpi_inferido_chunk (puente: evidencia de la inferencia) ───────────────
-- Registra qué chunks vectorizados sustentaron cada KPI inferido por búsqueda
-- semántica, con el score de similitud de cada chunk. Reemplaza al antiguo
-- campo 'secciones' de kpi_inferido con trazabilidad real a los chunks.

CREATE TABLE IF NOT EXISTS kpi_inferido_chunk (
    id_procesado             INTEGER NOT NULL,
    kpi_id                   INTEGER NOT NULL,
    documento_vectorizado_id INTEGER NOT NULL REFERENCES documento_vectorizado(documento_vectorizado_id) ON DELETE CASCADE,
    score                    NUMERIC,
    PRIMARY KEY (id_procesado, kpi_id, documento_vectorizado_id),
    FOREIGN KEY (id_procesado, kpi_id) REFERENCES kpi_inferido(id_procesado, kpi_id) ON DELETE CASCADE
);

-- ── 15. limpieza_ejecucion (cleaning-service) ─────────────────────────────────
-- Una fila por ejecución (versión) de la limpieza de un instrumento. El CSV limpio
-- vive en storage (ruta_csv_limpio = key); el reporte_limpieza y las decisiones
-- del investigador, en `reporte`. metadata-service usa la última 'confirmada'.

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

-- ── 16. version_conocimiento (knowledge-service) ─────────────────────────────
-- UNA fila por versión del conocimiento de un instrumento: perfil semántico →
-- decisiones de KPIs (aceptados y rechazados) → documento final (archivo en
-- storage; aquí su key). Estados: perfil_aprobado → kpis_confirmados → borrador
-- → vigente; al publicar otra versión, la anterior pasa a reemplazado.

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

-- ── 17. respuesta_interpretada (knowledge-service, al publicar) ───────────────
-- Una fila por respuesta (respondente × pregunta) del documento final VIGENTE.
-- Insumo de los conteos y porcentajes exactos del chat; `contexto` guarda los
-- datos del respondente (turno, carrera…) para filtrar por grupo.

CREATE TABLE IF NOT EXISTS respuesta_interpretada (
    id_respuesta    SERIAL       PRIMARY KEY,
    id_crudo        INTEGER      NOT NULL REFERENCES raw_data(id_crudo) ON DELETE CASCADE,
    version         INTEGER      NOT NULL,
    respondente_id  VARCHAR(40)  NOT NULL,
    pregunta_id     VARCHAR(40)  NOT NULL,
    valor           TEXT,
    significado     TEXT,
    nivel           VARCHAR(30),
    estado          VARCHAR(20)  NOT NULL,
    contexto        JSONB        NOT NULL DEFAULT '{}'::jsonb,
    fecha_creacion  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ── Índices ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_raw_data_owner           ON raw_data(id_owner);
CREATE INDEX IF NOT EXISTS idx_instrumento_crudo        ON instrumento_procesado(id_crudo);
CREATE INDEX IF NOT EXISTS idx_instrumento_estado       ON instrumento_procesado(estado);
CREATE INDEX IF NOT EXISTS idx_kpi_inferido_procesado   ON kpi_inferido(id_procesado);
CREATE INDEX IF NOT EXISTS idx_kpi_inferido_kpi         ON kpi_inferido(kpi_id);
CREATE INDEX IF NOT EXISTS idx_kpi_inf_chunk_docvec     ON kpi_inferido_chunk(documento_vectorizado_id);
CREATE INDEX IF NOT EXISTS idx_docvec_instrumento       ON documento_vectorizado(instrumento_id);
CREATE INDEX IF NOT EXISTS idx_docvec_coleccion         ON documento_vectorizado(coleccion_id);
CREATE INDEX IF NOT EXISTS idx_rag_log_timestamp        ON rag_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_limpieza_crudo_estado    ON limpieza_ejecucion(id_crudo, estado);
CREATE INDEX IF NOT EXISTS idx_version_conocimiento_crudo_estado ON version_conocimiento(id_crudo, estado);
CREATE INDEX IF NOT EXISTS idx_respuesta_crudo_pregunta    ON respuesta_interpretada(id_crudo, pregunta_id);
CREATE INDEX IF NOT EXISTS idx_respuesta_crudo_respondente ON respuesta_interpretada(id_crudo, respondente_id);

COMMIT;

-- ── search_path por defecto para el rol actual ────────────────────────────────
DO $$
BEGIN
    EXECUTE format('ALTER ROLE %I SET search_path TO tt_rag, public', current_user);
END
$$;
