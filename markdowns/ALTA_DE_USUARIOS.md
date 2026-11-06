# Alta de usuarios — Indagata

Indagata tiene dos roles: **investigador** (sube y consulta instrumentos) y **administrador** (además da de alta
usuarios). Solo un administrador puede crear cuentas.

## Usuarios de desarrollo

Se crean solos cuando la base arranca vacía (`infrastructure/postgres/init/05_seed_usuarios.sql`):

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@indagata.com` | `admin123` |
| Investigador | `investigador@indagata.com` | `investigador123` |

Son credenciales de desarrollo: cámbialas antes de usar Indagata con datos reales.

## Desde la interfaz

1. Entra con una cuenta de administrador.
2. En el menú lateral abre **Gestión de usuarios** (`/usuarios`). Un investigador ve un aviso de permisos.
3. Llena nombre, correo, contraseña (6 caracteres o más) y rol, y guarda.

La pantalla llama a `POST /auth/register` del api-gateway a través de `src/api/usuarios.ts`.

## Por la API

El api-gateway está en `http://localhost:8006` (Docker; con uvicorn local es el puerto 8000).

```powershell
$login = Invoke-RestMethod -Uri "http://localhost:8006/auth/login" -Method POST `
  -ContentType "application/json" -Body '{"email":"admin@indagata.com","password":"admin123"}'
Invoke-RestMethod -Uri "http://localhost:8006/auth/register" -Method POST -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $($login.access_token)" } `
  -Body '{"nombre":"María Investigadora","email":"maria@indagata.com","password":"maria123","rol":"investigador"}'
```

Respuestas: 201 si se creó; 401 sin token o con token vencido (dura 60 minutos); 403 si quien la pide no es
administrador; 409 si el correo ya existe; 422 si falta un campo o la contraseña es corta.

## Dónde quedan

En la tabla `tt_rag.usuario` de PostgreSQL, dentro del volumen `postgres_data`. Los usuarios de desarrollo se
recrean en cada arranque limpio; los que tú crees no: si borras el volumen (`docker compose down -v`) hay que
volver a darlos de alta.
