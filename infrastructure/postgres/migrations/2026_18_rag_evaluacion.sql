-- Evaluación del chat para el experimento redactor × juez (28 oct 2026):
--   rag_metrica_juez  una evaluación (fidelidad, relevancia, precisión del contexto) por respuesta y por juez, para
--                     comparar jueces sobre las mismas respuestas; rag_log.metricas sigue guardando la del juez por
--                     defecto, que es la que muestra la interfaz.
--   rag_calificacion  la calificación humana de cada respuesta (0 mal, 1 parcial, 2 bien).
SET search_path TO tt_rag, public;

BEGIN;
CREATE TABLE IF NOT EXISTS rag_metrica_juez (
    rag_metrica_juez_id SERIAL       PRIMARY KEY,
    rag_log_id          INTEGER      NOT NULL REFERENCES rag_log(rag_log_id) ON DELETE CASCADE,
    modelo_juez         VARCHAR(100) NOT NULL,
    metricas            JSONB        NOT NULL DEFAULT '{}'::jsonb,
    version             VARCHAR(10),
    fecha               TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (rag_log_id, modelo_juez)
);

CREATE TABLE IF NOT EXISTS rag_calificacion (
    rag_log_id   INTEGER   PRIMARY KEY REFERENCES rag_log(rag_log_id) ON DELETE CASCADE,
    calificacion SMALLINT  NOT NULL CHECK (calificacion BETWEEN 0 AND 2),
    entendio     BOOLEAN,
    fundamenta   BOOLEAN,  -- NULL = no aplica
    comentario   TEXT,
    usuario_id   INTEGER   REFERENCES usuario(usuario_id) ON DELETE SET NULL,
    fecha        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMIT;
