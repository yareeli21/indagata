# Cómo probar cada microservicio

Guía práctica para probar los microservicios de Indagata, de la forma más rápida
(sin levantar nada) a la más completa (todo el stack en Docker). Los ejemplos
usan el **instrument-service** (puerto 8001), pero el procedimiento aplica a
cualquier servicio cambiando el puerto y la carpeta.

## Puertos por servicio

| Servicio                | Puerto | Carpeta                          |
|-------------------------|--------|----------------------------------|
| api-gateway             | 8000   | `services/api-gateway`           |
| instrument-service      | 8001   | `services/instrument-service`    |
| analysis-service        | 8002   | `services/analysis-service`      |
| metadata-service        | 8003   | `services/metadata-service`      |
| storage-service         | 8004   | `services/storage-service`       |
| visualization-service   | 8005   | `services/visualization-service` |

> El Python local vive en el venv del repo: `.venv\Scripts\python.exe`.
> Los comandos de PowerShell usan `;` para encadenar (no `&&`).

---

## 1. Prueba en aislamiento (sin servidor ni base de datos)

La más rápida: levanta la app en memoria con el `TestClient` de FastAPI y
simula (mockea) la sesión de base de datos. No necesita Postgres ni Docker.
Ideal para iterar en segundos sobre la lógica de un endpoint.

- **Ventaja:** inmediato, sin infraestructura.
- **Limitación:** la BD es simulada; no valida el SQL real ni las constraints.

Ejemplo mínimo (ejecutar desde la carpeta del servicio, p. ej.
`services/instrument-service`):

```python
# smoke.py  (borrar al terminar)
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
r = client.get("/health")
print(r.status_code, r.json())
```

```powershell
# desde services/instrument-service
& "..\..\.venv\Scripts\python.exe" -B smoke.py
```

Para endpoints que tocan la BD, sobreescribe las dependencias con un fake:

```python
from app.dependencies import get_current_user
from shared.db.session import get_db
main.app.dependency_overrides[get_db] = lambda: MiSesionFake()
main.app.dependency_overrides[get_current_user] = lambda: mi_usuario_fake
```

---

## 2. Levantar SOLO ese servicio en local (contra Postgres)

Prueba realista del servicio con su base de datos, sin levantar los demás
microservicios.

```powershell
# 1) Postgres solo, vía Docker (inicializa el esquema y los seeds)
docker compose up -d postgres

# 2) El servicio en local con recarga en caliente (desde su carpeta)
#    cwd = services/instrument-service
uvicorn main:app --reload --port 8001
```

El `.env` de la raíz ya trae `POSTGRES_HOST=localhost`.

Una vez levantado:

- **http://localhost:8001/docs** — Swagger UI. Explora y ejecuta cada endpoint
  (p. ej. subir un archivo real en `/instrumentos/upload` y ver la respuesta).
- **http://localhost:8001/redoc** — documentación alternativa (solo lectura).
- **http://localhost:8001/health** — confirma que el servicio responde.

> **El instrument-service exige autenticación (JWT).** `/instrumentos/upload` y
> `DELETE /instrumentos/{id_crudo}` requieren un token válido en el header
> `Authorization: Bearer <token>`. Para obtenerlo, primero haz login en el
> api-gateway (ver sección **5. Autenticación**). Sin token → 401; con rol no
> autorizado → 403.

### Nota sobre `import shared` en local

Cada servicio corre con un directorio de trabajo distinto en local vs. Docker.
Para que `import shared` resuelva al ejecutar `uvicorn main:app` desde la carpeta
del servicio, `main.py` añade la raíz del repo al `sys.path`. Si al crear un
servicio nuevo aparece `ModuleNotFoundError: shared`, copia ese mismo patrón del
`main.py` del instrument-service.

---

## 3. Todo el stack en Docker (integración real)

Cuando quieras probar varios servicios comunicándose entre sí
(gateway → instrument-service, etc.) y la infraestructura completa
(Postgres, Ollama, ChromaDB, Redis).

```powershell
docker compose up -d                                 # levantar todo
docker compose up -d --build instrument-service      # reconstruir un servicio
docker compose logs -f instrument-service            # ver sus logs en vivo
docker compose ps                                    # estado de los contenedores
docker compose down                                  # detener todo
docker compose down -v                               # detener y borrar volúmenes
```

En Docker, `docker-compose.yml` sobreescribe el entorno de cada servicio
(`POSTGRES_HOST=postgres`, rutas `/app/storage/*`), de modo que la configuración
local no interfiere.

---

## 4. Probar desde la terminal con `curl`

Alternativa a Swagger UI, útil para scripts.

```powershell
# Health check (no requiere token)
curl http://localhost:8001/health

# 1) Login en el gateway para obtener el token
$resp = curl.exe -s -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"investigador@indagata.local\",\"password\":\"investigador123\"}'
$token = ($resp | ConvertFrom-Json).access_token

# 2) Upload multipart CON el token (archivo respondido + original opcional)
curl.exe -H "Authorization: Bearer $token" `
         -F "tipo_instrumento=encuesta" `
         -F "archivo=@C:\ruta\respuestas.csv" `
         -F "archivo_original=@C:\ruta\cuestionario.pdf" `
         http://localhost:8001/instrumentos/upload

# 3) Borrar un instrumento (solo el dueño, o un administrador)
curl.exe -X DELETE -H "Authorization: Bearer $token" `
         http://localhost:8001/instrumentos/10
```

> En PowerShell usa `curl.exe` (no el alias `curl`) para pasar flags como `-F`.

---

## 5. Autenticación (login JWT)

El login vive en el **api-gateway** (puerto 8000). Emite un **JWT firmado**; los
servicios protegidos (hoy el instrument-service) lo validan con la misma
`SECRET_KEY`. El token se manda en cada petición como
`Authorization: Bearer <token>` y **expira a los 60 minutos**.

### Roles
- **investigador**: puede ingestar instrumentos y eliminar los suyos.
- **administrador**: acceso total (ingesta, borrado de cualquiera, alta de usuarios).

### Usuarios sembrados (desarrollo)
`infrastructure/postgres/init/05_seed_usuarios.sql` crea:

| Rol | Email | Password |
|---|---|---|
| administrador | `admin@indagata.local` | `admin123` |
| investigador | `investigador@indagata.local` | `investigador123` |

> Credenciales de desarrollo. **Cámbialas en producción.**

### Endpoints de auth (gateway, puerto 8000)
| Método | Ruta | Protección |
|---|---|---|
| `POST` | `/auth/login` | Público. `email` + `password` → `{ access_token, usuario }`. |
| `GET`  | `/auth/me` | Token válido. Devuelve el usuario del token. |
| `POST` | `/auth/register` | Solo **administrador**. Alta de usuario. |

### Flujo típico (navegador / Swagger)
1. Levanta gateway e instrument-service (ambos necesitan Postgres).
2. En `http://localhost:8000/docs`, ejecuta `POST /auth/login` y copia el `access_token`.
3. En `http://localhost:8001/docs`, pulsa **Authorize** y pega el token.
4. Ya puedes ejecutar `/instrumentos/upload` y `DELETE /instrumentos/{id_crudo}`.

### Comprobaciones útiles
- Sin token → **401**.
- Token expirado o manipulado → **401**.
- Investigador que intenta borrar un instrumento ajeno → **403**.
- Investigador que llama a `/auth/register` → **403** (solo administrador).

---

## Flujo recomendado

1. **Mientras desarrollas la lógica de un servicio** → forma **#1** (TestClient en
   memoria): iteras en segundos sin infraestructura.
2. **Para una prueba manual realista** → forma **#2** (uvicorn + `/docs` + Postgres
   solo): valida contra la BD real.
3. **Para validar la integración entre servicios** → forma **#3** (todo en Docker).

---

## Problemas comunes

| Síntoma                                   | Causa probable / solución                                             |
|-------------------------------------------|-----------------------------------------------------------------------|
| `ModuleNotFoundError: shared`             | Ejecuta desde la carpeta del servicio; revisa el shim de `sys.path` en `main.py`. |
| **401 en /instrumentos/***                | Falta el token. Haz login en el gateway y manda `Authorization: Bearer <token>`. |
| **401 aunque mando token**                | Token expirado (dura 60 min) o `SECRET_KEY` distinta entre gateway y servicio; vuelve a hacer login. |
| **403 al borrar**                         | Eres investigador y el instrumento no es tuyo (`id_owner`), o tu rol no está autorizado. |
| **401 en /auth/login**                    | Email o contraseña incorrectos; revisa los usuarios sembrados.         |
| El servicio no conecta a Postgres en local| `POSTGRES_HOST` debe ser `localhost` (no `postgres`) fuera de Docker. |
| Puerto ocupado                            | Otro proceso usa el puerto; cámbialo con `--port` o libéralo.          |
| Cambios no se reflejan                    | Usa `--reload` en local; en Docker reconstruye con `--build`.          |

### Saltarse la auth en pruebas aisladas (forma #1)

En la prueba en memoria (TestClient) puedes evitar el login real sobreescribiendo
la dependencia de usuario, útil para probar la lógica sin generar un token:

```python
from app.dependencies import get_current_user
from shared.models.usuario import Usuario

fake = Usuario(); fake.usuario_id = 1; fake.rol = "administrador"
main.app.dependency_overrides[get_current_user] = lambda: fake
```
