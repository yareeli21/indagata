-- 2026_22 — Gestión de usuarios y bloqueo por intentos fallidos (24 nov 2026).
--
--   activo             false = la cuenta no puede iniciar sesión (se conserva su trabajo: borrar un usuario
--                      borra en cascada sus instrumentos, por eso se desactiva en lugar de eliminar).
--   intentos_fallidos  contraseñas incorrectas seguidas; al llegar a 5 se bloquea 15 minutos.
--   bloqueado_hasta    hasta cuándo no se acepta el login (NULL = sin bloqueo).
--
-- Aplicar: docker compose exec postgres psql -U postgres -d indagata_db -f /migrations/2026_22_usuarios_gestion.sql

SET search_path TO tt_rag;

ALTER TABLE usuario ADD COLUMN IF NOT EXISTS activo            BOOLEAN   NOT NULL DEFAULT TRUE;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS intentos_fallidos INTEGER   NOT NULL DEFAULT 0;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS bloqueado_hasta   TIMESTAMP NULL;
