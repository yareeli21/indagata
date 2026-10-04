-- ============================================================
-- Seed de usuarios (login JWT).
--
-- Siembra el PRIMER ADMINISTRADOR (necesario para arrancar: no puede crearlo
-- otro admin porque aún no existe ninguno). A partir de él, el administrador
-- da de alta a los investigadores vía POST /auth/register en el api-gateway.
--
-- También siembra un investigador de prueba para desarrollo.
--
-- Esquema real de la tabla (tt_rag.usuario):
--   usuario_id, nombre, email (UNIQUE), password_hash (bcrypt), rol, fecha_registro
--
-- Credenciales de desarrollo (CAMBIAR EN PRODUCCIÓN):
--   admin:        admin@indagata.com          / admin123
--   investigador: investigador@indagata.com   / investigador123
-- ============================================================

SET search_path TO tt_rag, public;

-- Primer ADMINISTRADOR (idempotente por email).
INSERT INTO usuario (nombre, email, password_hash, rol)
VALUES (
    'Administrador',
    'admin@indagata.com',
    '$2b$12$oEQbNSQCRgJMRZCkcRcmgu6rbEGJHB4tMcNQPK2260k.G79pXt/PS',
    'administrador'
)
ON CONFLICT (email) DO NOTHING;

-- Investigador de prueba (idempotente por email).
INSERT INTO usuario (nombre, email, password_hash, rol)
VALUES (
    'Investigador Demo',
    'investigador@indagata.com',
    '$2b$12$9WrJ1KqiW3eHekVP7mnSnOMIiVAyZnSeOz6Ae7GwnN50ejjBXRZdi',
    'investigador'
)
ON CONFLICT (email) DO NOTHING;
