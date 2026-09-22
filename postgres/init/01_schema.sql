-- ============================================================================
-- INDAGATA - Schema PostgreSQL v2.0 (Actualizado 2026-09-17)
-- Base de datos: aprende_rag
-- Schema: tt_rag
-- ============================================================================

-- Crear schema si no existe
CREATE SCHEMA IF NOT EXISTS tt_rag;

-- Asegurar que estamos en el schema correcto
SET search_path TO tt_rag, public;


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 1: GESTIÓN DE INSTRUMENTOS (ACTUALIZADO)
-- ════════════════════════════════════════════════════════════════════════════

-- Tabla principal de instrumentos procesados
-- CAMBIOS: Eliminado campo 'visibilidad' (todo público ahora)
CREATE TABLE IF NOT EXISTS instrumento_procesado (
    instrumento_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              VARCHAR(255) NOT NULL,
    tipo_instrumento    VARCHAR(30)  NOT NULL
        CHECK (tipo_instrumento IN ('encuesta', 'entrevista', 'prueba_estandarizada')),
    plataforma          VARCHAR(50),
    ruta_json           TEXT,  -- Disponible desde "etl_aprobado"
    ruta_sav            TEXT,  -- Solo encuestas, desde "vectorizado"
    ruta_texto_limpio   TEXT,  -- storage/data/{hash}.txt o {hash}.canonical.json (caché reutilizable)
    ruta_codebook       TEXT,  -- storage/raw/ codebook opcional (solo encuestas); entrada RAG futura
    estado              VARCHAR(50)  NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'metadata_registrado', 'etl_pendiente_limpieza', 'etl_pendiente_enriquecimiento', 'etl_aprobado', 'en_ingesta', 'vectorizado', 'error')),
    schema_version      VARCHAR(10)  DEFAULT '2.0',
    error_detalle       TEXT,
    fecha_procesamiento TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creado_en           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ruta_archivo        TEXT  -- storage/raw/{id}_{timestamp}_{hash}.{ext}
);

COMMENT ON COLUMN instrumento_procesado.ruta_json IS 'Ruta al JSON consolidado en storage/json/. Disponible desde "etl_aprobado".';
COMMENT ON COLUMN instrumento_procesado.ruta_sav IS 'Ruta al .sav en storage/sav/. Solo encuestas, desde "vectorizado".';
COMMENT ON COLUMN instrumento_procesado.ruta_texto_limpio IS 'Ruta al caché en storage/data/. Encuestas: {hash}.canonical.json; documentos: {hash}.txt. Reutilizable por hash.';
COMMENT ON COLUMN instrumento_procesado.ruta_codebook IS 'Codebook opcional (solo encuestas). Se pasa como fuente RAG al SIS (activo en Nivel 2).';
COMMENT ON COLUMN instrumento_procesado.estado IS 'Flujo: pendiente → metadata_registrado → (analyze SIS) → etl_pendiente_limpieza → etl_pendiente_enriquecimiento → etl_aprobado → en_ingesta → vectorizado | error';
COMMENT ON COLUMN instrumento_procesado.schema_version IS 'Versión del schema del JSON consolidado. v2.0 incluye transformaciones, metadatos enriquecidos y KPIs.';
COMMENT ON COLUMN instrumento_procesado.ruta_archivo IS 'Ruta relativa al archivo original en storage/raw/. Disponible desde estado "pendiente".';

-- Índices
CREATE INDEX IF NOT EXISTS idx_instrumento_estado ON instrumento_procesado(estado)
    WHERE estado IN ('metadata_registrado', 'etl_pendiente_limpieza', 'etl_pendiente_enriquecimiento', 'etl_aprobado', 'en_ingesta', 'vectorizado');
CREATE INDEX IF NOT EXISTS idx_instrumento_tipo ON instrumento_procesado(tipo_instrumento);
CREATE INDEX IF NOT EXISTS idx_instrumento_creado_en ON instrumento_procesado(creado_en);
CREATE INDEX IF NOT EXISTS idx_instrumento_nombre_fts ON instrumento_procesado USING GIN (to_tsvector('spanish', nombre));


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 2: METADATOS DUBLIN CORE (ACTUALIZADO - SIN VISIBILIDAD)
-- ════════════════════════════════════════════════════════════════════════════

-- Metadatos Dublin Core (13 campos estándar)
-- CAMBIOS: Eliminados dc_contributor y dc_identifier
CREATE TABLE IF NOT EXISTS metadatos_dc (
    metadatos_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id INTEGER NOT NULL UNIQUE,
    dc_title       TEXT    NOT NULL,
    dc_creator     TEXT    NOT NULL,
    dc_subject     TEXT    NOT NULL,  -- JSON array: '["tema1","tema2"]'
    dc_description TEXT    NOT NULL,
    dc_publisher   TEXT    NOT NULL,
    dc_date        VARCHAR(20) NOT NULL,
    dc_type        VARCHAR(50) NOT NULL,
    dc_format      VARCHAR(50) NOT NULL,
    dc_language    VARCHAR(10) NOT NULL,
    dc_coverage    TEXT    NOT NULL,
    dc_rights      TEXT    NOT NULL,
    dc_source      TEXT,
    dc_relation    TEXT,
    registrado_en  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

COMMENT ON COLUMN metadatos_dc.dc_subject IS 'Lista de temas serializada como JSON: ''["tema1","tema2"]''';

-- Índices
CREATE INDEX IF NOT EXISTS idx_metadatos_dc_language ON metadatos_dc(dc_language);
CREATE INDEX IF NOT EXISTS idx_metadatos_dc_title_fts ON metadatos_dc USING GIN (to_tsvector('spanish', dc_title));


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 3: PROPUESTAS ETL Y METADATOS ENRIQUECIDOS (NUEVO)
-- ════════════════════════════════════════════════════════════════════════════

-- Propuestas generadas por el LLM en el paso ETL
-- NUEVO: Tabla para registrar transformaciones, metadatos enriquecidos y KPIs sugeridos
CREATE TABLE IF NOT EXISTS etl_propuesta (
    propuesta_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id   INTEGER NOT NULL,
    tipo             VARCHAR(30) NOT NULL
        CHECK (tipo IN ('transformacion', 'metadato_enriquecido', 'kpi_sugerido')),
    descripcion      TEXT NOT NULL,
    accion_sugerida  TEXT NOT NULL,
    justificacion    TEXT NOT NULL,
    impacto_esperado TEXT,
    valor_original   TEXT,
    valor_propuesto  TEXT,  -- Para metadatos: JSON. Para KPIs: nombre del KPI. Para transformaciones: texto.
    estado_decision  VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado_decision IN ('pendiente', 'aceptada', 'rechazada')),
    fecha_propuesta  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_decision   TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

COMMENT ON COLUMN etl_propuesta.tipo IS 'Categoría de la propuesta: transformacion (recomendaciones de mejora), metadato_enriquecido (campos adicionales), kpi_sugerido (indicador inferido).';
COMMENT ON COLUMN etl_propuesta.valor_propuesto IS 'Para transformaciones: valor después de aplicar la acción. Para metadatos/KPIs: JSON con el campo y valor sugeridos.';
COMMENT ON COLUMN etl_propuesta.estado_decision IS 'pendiente (por defecto tras paso 3), aceptada o rechazada (tras paso 4).';

-- Índices
CREATE INDEX IF NOT EXISTS idx_etl_propuesta_instrumento ON etl_propuesta(instrumento_id);
CREATE INDEX IF NOT EXISTS idx_etl_propuesta_tipo ON etl_propuesta(tipo);
CREATE INDEX IF NOT EXISTS idx_etl_propuesta_estado ON etl_propuesta(estado_decision);


-- Metadatos enriquecidos (campos adicionales del LLM)
-- NUEVO: JSONB flexible para campos adicionales aceptados en ETL
CREATE TABLE IF NOT EXISTS metadatos_enriquecidos (
    enriquecido_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id INTEGER NOT NULL UNIQUE,
    metadatos      JSONB   NOT NULL DEFAULT '{}'::jsonb,
    registrado_en  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_metadatos_enriquecidos_gin ON metadatos_enriquecidos USING GIN (metadatos);


-- Oportunidades de mejora continua emitidas por el SIS (Survey Intelligence Service)
-- NUEVO: el SIS solo emite status='proposed'; la promoción es gobernanza humana.
CREATE TABLE IF NOT EXISTS improvement_opportunity (
    opportunity_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id  INTEGER NOT NULL,
    sis_opportunity_id TEXT,  -- id que generó el SIS (trazabilidad)
    scope           VARCHAR(30) NOT NULL
        CHECK (scope IN ('survey', 'pipeline', 'future_analysis', 'validation_rule', 'quality_heuristic', 'pattern')),
    titulo          TEXT NOT NULL,
    descripcion     TEXT NOT NULL,
    evidencia       JSONB DEFAULT '[]'::jsonb,
    proposed_rule   JSONB,  -- {rule_id_candidate, when, then} para reglas candidatas
    confianza       NUMERIC(4,3) CHECK (confianza IS NULL OR (confianza >= 0 AND confianza <= 1)),
    generado_por    VARCHAR(60),
    estado          VARCHAR(20) NOT NULL DEFAULT 'proposed'
        CHECK (estado IN ('proposed', 'under_review', 'accepted', 'promoted', 'rejected')),
    creado_en       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

COMMENT ON TABLE improvement_opportunity IS 'Recomendaciones de mejora del SIS. El SIS emite proposed; la promocion a regla activa es gobernanza humana.';

CREATE INDEX IF NOT EXISTS idx_improvement_instrumento ON improvement_opportunity(instrumento_id);
CREATE INDEX IF NOT EXISTS idx_improvement_scope ON improvement_opportunity(scope);
CREATE INDEX IF NOT EXISTS idx_improvement_estado ON improvement_opportunity(estado);


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 4: CATÁLOGO DE INDICADORES (SIN CAMBIOS - CONSERVAR)
-- ════════════════════════════════════════════════════════════════════════════

-- Tabla de KPIs (indicadores educativos)
-- NO TOCAR - Datos maestros
CREATE TABLE IF NOT EXISTS kpi (
    kpi_id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombrekpi         VARCHAR(255) NOT NULL,
    descripcion       TEXT,
    categoria         VARCHAR(100),
    ambito            VARCHAR(50),
    url_documentacion TEXT,
    registrado_en     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de instituciones
-- NO TOCAR - Datos maestros
CREATE TABLE IF NOT EXISTS instituciones (
    institucion_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre         TEXT,
    pais           TEXT,
    tipo           TEXT
);

-- Tabla de variables
-- NO TOCAR - Datos maestros
CREATE TABLE IF NOT EXISTS variable (
    variable_id     INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_variable VARCHAR(255) UNIQUE NOT NULL,
    tipo_dato       VARCHAR(50),
    descripcion     TEXT,
    unidad_medida   VARCHAR(50)
);

-- Relación KPI-Variable (muchos a muchos)
-- NO TOCAR - Datos maestros
CREATE TABLE IF NOT EXISTS kpi_variable (
    kpi_id      INTEGER NOT NULL,
    variable_id INTEGER NOT NULL,
    PRIMARY KEY (kpi_id, variable_id),
    FOREIGN KEY (kpi_id) REFERENCES kpi(kpi_id) ON DELETE CASCADE,
    FOREIGN KEY (variable_id) REFERENCES variable(variable_id) ON DELETE CASCADE
);

-- Valores posibles para variables categóricas
-- NO TOCAR - Datos maestros
CREATE TABLE IF NOT EXISTS valor_variable (
    valor_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    variable_id    INTEGER     NOT NULL,
    valor          VARCHAR(255) NOT NULL,
    etiqueta       TEXT,
    orden          INTEGER,
    es_nulo        BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (variable_id) REFERENCES variable(variable_id) ON DELETE CASCADE
);

-- Pregunta-KPI (relación entre preguntas de instrumentos y KPIs)
-- NO TOCAR - Datos maestros
CREATE TABLE IF NOT EXISTS pregunta_kpi (
    pregunta_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id   INTEGER NOT NULL,
    pregunta_texto   TEXT,
    kpi_id           INTEGER NOT NULL,
    tipo_relacion    VARCHAR(50),
    confianza        NUMERIC(3,2),
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    FOREIGN KEY (kpi_id) REFERENCES kpi(kpi_id)
);


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 5: KPIs INFERIDOS (ACTUALIZADO)
-- ════════════════════════════════════════════════════════════════════════════

-- KPIs asociados al instrumento (manual o por LLM)
-- CAMBIOS: Agregado campo 'origen' para distinguir fuente
CREATE TABLE IF NOT EXISTS kpi_inferido (
    kpi_inferido_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id    INTEGER NOT NULL,
    kpi_id            INTEGER NOT NULL,
    tipo_relacion     VARCHAR(20),  -- directo, indirecto, complementario, inferido
    evidencia_textual TEXT,
    score_inferencia  NUMERIC(4,3) CHECK (score_inferencia >= 0 AND score_inferencia <= 1),
    origen            VARCHAR(20) NOT NULL DEFAULT 'registro_manual'
        CHECK (origen IN ('registro_manual', 'propuesta_etl')),
    registrado_en     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    FOREIGN KEY (kpi_id) REFERENCES kpi(kpi_id)
);

COMMENT ON COLUMN kpi_inferido.tipo_relacion IS 'Tipo de asociación: directa, indirecta, complementaria o inferida.';
COMMENT ON COLUMN kpi_inferido.origen IS 'registro_manual: registrado por el investigador en paso 2. propuesta_etl: aceptado en paso 4.';

-- Índices
CREATE INDEX IF NOT EXISTS idx_kpi_inferido_instrumento ON kpi_inferido(instrumento_id);
CREATE INDEX IF NOT EXISTS idx_kpi_inferido_kpi ON kpi_inferido(kpi_id);


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 6: USUARIOS Y PERMISOS
-- ════════════════════════════════════════════════════════════════════════════

-- Usuarios del sistema
CREATE TABLE IF NOT EXISTS usuarios (
    usuario_id    INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario       VARCHAR(50)  UNIQUE NOT NULL,
<<<<<<< HEAD
    password_hash VARCHAR(255) NOT NULL,
    correo         VARCHAR(60)  NOT NULL,
    fecha     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
=======
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT,
    rol           VARCHAR(20)  DEFAULT 'investigador',
    creado_en     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
>>>>>>> f1c3938aeebc5033b4cb855099078e64d6803376
);

-- Permisos sobre instrumentos (quién puede modificar/eliminar)
-- CAMBIOS: Sin campo visibilidad (todo público)
CREATE TABLE IF NOT EXISTS permiso_instrumento (
    permiso_id     INTEGER     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id INTEGER     NOT NULL,
    usuario_id     INTEGER     NOT NULL,
    tipo_permiso   VARCHAR(20) NOT NULL DEFAULT 'propietario',
    otorgado_en    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(usuario_id) ON DELETE CASCADE,
    UNIQUE (instrumento_id, usuario_id, tipo_permiso)
);

COMMENT ON TABLE permiso_instrumento IS 'Controla quién puede modificar/eliminar el instrumento. Lectura es pública para todos.';


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 7: DATOS CRUDOS Y PIPELINE
-- ════════════════════════════════════════════════════════════════════════════

-- Versiones de datos crudos del instrumento
CREATE TABLE IF NOT EXISTS raw_data (
    raw_data_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id      INTEGER      NOT NULL,
    version             INTEGER      NOT NULL,
    archivo_nombre      VARCHAR(255),
    ruta_archivo_crudo  TEXT,
    tipo_archivo        VARCHAR(20),
    tamano_bytes        BIGINT,
    hash_md5            VARCHAR(32),
    fecha_carga         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    es_version_actual   BOOLEAN      DEFAULT TRUE,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

COMMENT ON TABLE raw_data IS 'El registro con mayor raw_data_id para un instrumento_id es la versión actual.';


-- Log del pipeline de ingesta (extracción, limpieza, vectorización)
CREATE TABLE IF NOT EXISTS pipeline_ingesta_log (
    log_id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id   INTEGER NOT NULL,
    iniciado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finalizado_en    TIMESTAMP,
    resultado        VARCHAR(20) NOT NULL DEFAULT 'en_proceso'
        CHECK (resultado IN ('en_proceso', 'exitoso', 'error')),
    extractor_usado  VARCHAR(50),
    modelo_llm       VARCHAR(100),
    prompt_version   VARCHAR(20),
    tokens_entrada   INTEGER,
    tokens_salida    INTEGER,
    latencia_ms      INTEGER,
    segmentos        INTEGER,
    error_mensaje    TEXT,
    etapa_actual     VARCHAR(50),  -- extraccion | limpieza | json | chunking | embeddings | vectorstore
    n_chunks         INTEGER,
    modelo_embedding VARCHAR(100),
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE
);

COMMENT ON COLUMN pipeline_ingesta_log.etapa_actual IS 'Etapa actual del pipeline: extraccion | limpieza | json | chunking | embeddings | vectorstore';
COMMENT ON COLUMN pipeline_ingesta_log.n_chunks IS 'Número de chunks generados desde el JSON consolidado.';

-- Índices
CREATE INDEX IF NOT EXISTS idx_ingesta_log_instrumento ON pipeline_ingesta_log(instrumento_id);
CREATE INDEX IF NOT EXISTS idx_ingesta_log_en_proceso ON pipeline_ingesta_log(instrumento_id)
    WHERE resultado = 'en_proceso';


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 8: VECTORIZACIÓN Y RAG
-- ════════════════════════════════════════════════════════════════════════════

-- Documentos vectorizados (chunks del instrumento)
CREATE TABLE IF NOT EXISTS documento_vectorizado (
    documento_vectorizado_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id           INTEGER     NOT NULL,
    chunk_index              INTEGER     NOT NULL,
    chunk_texto              TEXT        NOT NULL,
    chunk_metadata           JSONB       DEFAULT '{}'::jsonb,
    embedding_modelo         VARCHAR(100),
    almacenado_en            TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_procesado(instrumento_id) ON DELETE CASCADE,
    UNIQUE (instrumento_id, chunk_index)
);

-- Log de consultas RAG
CREATE TABLE IF NOT EXISTS rag_log (
    rag_log_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pregunta         TEXT        NOT NULL,
    respuesta        TEXT,
    modelo_usado     VARCHAR(100),
    chunks_usados    INTEGER,
    latencia_ms      INTEGER,
    timestamp        TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);


-- ════════════════════════════════════════════════════════════════════════════
-- GRUPO 9: PROMPTS DEL SISTEMA
-- ════════════════════════════════════════════════════════════════════════════

-- Catálogo de prompts versionados
CREATE TABLE IF NOT EXISTS prompt (
    prompt_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo      VARCHAR(20) NOT NULL,
    version   VARCHAR(10) NOT NULL,
    contenido TEXT NOT NULL,
    activo    BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tipo, version)
);


-- ════════════════════════════════════════════════════════════════════════════
-- FIN DEL SCHEMA
-- ════════════════════════════════════════════════════════════════════════════

-- Resetear search_path
RESET search_path;
