-- ============================================================
-- Seed de usuarios para desarrollo / pruebas de los microservicios.
--
-- El instrument-service y el analysis-service, en MODO DESARROLLO
-- (AUTH_DEV_MODE=true), usan el usuario con usuario_id = DEV_USER_ID (=1).
-- Ese usuario debe existir y tener un rol que pueda subir instrumentos
-- (investigador o admin). 04_seed.sql ya inserta 'admin' como primer usuario;
-- aquí garantizamos su rol y añadimos un investigador explícito de prueba.
--
-- La contraseña hash corresponde a bcrypt; cámbiela en producción.
-- ============================================================

SET search_path TO tt_rag, public;

-- Asegurar rol del primer usuario (admin). Puede subir instrumentos.
UPDATE usuarios SET rol = 'admin' WHERE usuario = 'admin';

-- Investigador de prueba (idempotente).
INSERT INTO usuarios (usuario, email, password_hash, rol)
VALUES (
    'investigador_demo',
    'investigador.demo@indagata.local',
    '$2b$12$H4Bg4iZGDjpsCChc31lt2eWa8vmKaM6f.uydwSxhU/.f2WRvMFw6a',
    'investigador'
)
ON CONFLICT (usuario) DO NOTHING;
