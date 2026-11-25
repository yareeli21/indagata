-- 2026_23 — Investigaciones y sus conversaciones en el servidor (25 nov 2026).
--
-- Antes vivían solo en el navegador (localStorage): en otro dispositivo, en otro navegador o en modo incógnito no
-- aparecían. Ahora cada usuario guarda aquí las suyas; el navegador queda como copia rápida.
--
--   id            el mismo identificador que ya usaba la página («res-1700000000000»).
--   instrumentos  ids de los instrumentos elegidos (id_crudo como texto).
--   sesion        conversación: {contexto, mensajes, actualizada}; NULL si aún no se ha chateado.
--
-- Aplicar: docker compose exec postgres psql -U postgres -d indagata_db -f /migrations/2026_23_investigaciones.sql

SET search_path TO tt_rag;

CREATE TABLE IF NOT EXISTS investigacion (
    usuario_id      INTEGER      NOT NULL REFERENCES usuario(usuario_id) ON DELETE CASCADE,
    id              VARCHAR(64)  NOT NULL,
    nombre          VARCHAR(255) NOT NULL,
    fecha_creacion  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    instrumentos    JSONB        NOT NULL DEFAULT '[]'::jsonb,
    sesion          JSONB        NULL,
    actualizada     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, id)
);
