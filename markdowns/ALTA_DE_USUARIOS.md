# Alta de usuarios (registro) — INDAGATA

> Cómo dar de alta nuevos usuarios (investigadores o administradores) en el
> sistema. Documento verificado contra el backend en ejecución.

---

## 1. Concepto: quién puede crear usuarios

El sistema usa autenticación JWT. La regla de negocio es:

- **Solo un ADMINISTRADOR puede dar de alta usuarios nuevos.**
- Un investigador NO puede crear usuarios (recibe error 403).
- Nadie sin iniciar sesión puede crear usuarios (recibe error 401).

Esto resuelve el problema del "huevo y la gallina": el PRIMER administrador se
siembra automáticamente al crear la base de datos (ver `05_seed_usuarios.sql`).
A partir de ese admin, se crean todos los demás.

### Usuarios demo ya existentes

| Rol           | Email                        | Contraseña        |
|---------------|------------------------------|-------------------|
| Administrador | `admin@indagata.com`         | `admin123`        |
| Investigador  | `investigador@indagata.com`  | `investigador123` |

> Son credenciales de desarrollo. CAMBIARLAS en producción.

---

## 2. El endpoint de registro

- **Ruta:** `POST /auth/register`
- **Servicio:** api-gateway (`http://localhost:8000` en local).
- **Requiere:** cabecera `Authorization: Bearer <token-de-ADMIN>`.
- **Respuesta exitosa:** HTTP 201 con los datos del usuario creado.

### Cuerpo de la petición (JSON)

```json
{
  "nombre": "Nombre Apellido",
  "email": "persona@dominio.com",
  "password": "mínimo 6 caracteres",
  "rol": "investigador"
}
```

Reglas de los campos (validadas por el backend):

| Campo      | Regla                                                              |
|------------|--------------------------------------------------------------------|
| `nombre`   | obligatorio, mínimo 1 carácter                                     |
| `email`    | obligatorio, formato de email **válido**. NO usar dominios reservados como `.local` (los rechaza la validación). Usar `.com`, `.org`, etc. Debe ser **único**. |
| `password` | obligatorio, **mínimo 6 caracteres**. Se guarda hasheada con bcrypt (nunca en texto plano). |
| `rol`      | `investigador` (por defecto) o `administrador`.                    |

---

## 3. Proceso paso a paso (vía terminal / API)

Este es el flujo real, verificado. Son dos pasos: obtener el token de admin y
luego registrar.

### Paso 1 — Iniciar sesión como administrador para obtener el token

```powershell
$login = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" `
  -Method POST -ContentType "application/json" `
  -Body '{"email":"admin@indagata.com","password":"admin123"}'
$token = $login.access_token
```

### Paso 2 — Registrar el nuevo usuario (con el token del admin)

```powershell
$nuevo = '{
  "nombre": "María Investigadora",
  "email": "maria@indagata.com",
  "password": "maria123",
  "rol": "investigador"
}'

Invoke-RestMethod -Uri "http://localhost:8000/auth/register" `
  -Method POST -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $token" } `
  -Body $nuevo
```

Respuesta esperada (HTTP 201):

```json
{
  "usuario_id": 3,
  "nombre": "María Investigadora",
  "email": "maria@indagata.com",
  "rol": "investigador"
}
```

A partir de ahí, ese usuario puede iniciar sesión con su email y contraseña.

### Equivalente con curl (multiplataforma)

```bash
# Paso 1: login admin, guardar el token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@indagata.com","password":"admin123"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Paso 2: registrar
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"nombre":"María Investigadora","email":"maria@indagata.com","password":"maria123","rol":"investigador"}'
```

---

## 4. Errores posibles (y qué significan)

| HTTP | Cuándo ocurre                                               | Qué hacer                                  |
|------|------------------------------------------------------------|--------------------------------------------|
| 401  | No se envió token (no autenticado)                         | Inicia sesión como admin y envía el Bearer |
| 403  | El token es de un investigador, no de un admin             | Usa un token de administrador              |
| 409  | Ya existe un usuario con ese email                         | Usa otro email                             |
| 422  | Email con formato inválido (p.ej. `.local`) o password < 6 | Corrige el email / usa password ≥ 6        |

---

## 5. Estado en la interfaz web (pixel-perfect-pixel)

**Importante:** a día de hoy, el **login** del front ya está conectado al backend
real, pero la **pantalla de alta de usuarios NO existe todavía** en la interfaz.
Es decir, hoy el registro solo se puede hacer por la API (los pasos de la
sección 3), no desde un formulario en la web.

Cuando se desarrolle esa parte (fase futura), lo natural sería:

- Una pantalla visible **solo para administradores** (p.ej. "Gestión de usuarios").
- Un formulario que llame a `POST /auth/register` reutilizando el helper `pedir`
  de `src/api/client.ts` con `auth: true` (adjunta el JWT del admin).
- Una nueva función en `src/api/` (p.ej. `src/api/usuarios.ts`) siguiendo el
  patrón del proyecto (toda la UI pasa por `src/api/`).

Mientras tanto, para crear usuarios reales se usa la API directamente.

---

## 6. Nota sobre persistencia

- Los usuarios creados por `POST /auth/register` quedan guardados en la tabla
  `tt_rag.usuario` de PostgreSQL (persisten en el volumen `postgres_data`).
- Los dos usuarios demo (admin, investigador) se recrean automáticamente en cada
  arranque limpio de la base (`05_seed_usuarios.sql`), porque es idempotente
  (`ON CONFLICT (email) DO NOTHING`). Los usuarios que tú crees por la API NO se
  recrean solos: si borras el volumen (`docker compose down -v`), se pierden y
  habría que volver a darlos de alta.

---

*Documento de referencia del proceso de alta de usuarios de INDAGATA.
Credenciales mostradas son de desarrollo; cambiarlas en producción.*
