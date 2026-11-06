# api-gateway (puerto 8006 → 8000)

Único punto de entrada HTTP del frontend (salvo analysis-service, que el frontend llama directo en el 8002).
Hace dos cosas:

1. **Autenticación** (`app/auth/`): emite y valida el JWT que usan todos los servicios.
2. **Proxy** (`proxy/proxy.py`): reenvía cada ruta, sin cambiarla, al servicio que le corresponde.

## Autenticación

| Ruta | Método | Qué hace |
|---|---|---|
| `/auth/login` | POST | Correo y contraseña → `access_token` (JWT, 60 minutos) |
| `/auth/me` | GET | Usuario del token |
| `/auth/register` | POST | Alta de usuario; solo administradores (ver `markdowns/ALTA_DE_USUARIOS.md`) |

El token se firma con `SECRET_KEY` (raíz `.env`); todos los servicios lo validan con la misma clave, así que una
clave distinta se ve como 401.

## Proxy

| Prefijo | Servicio |
|---|---|
| `/instrumentos/*` | instrument-service (8001) |
| `/api/metadata/*`, `/api/enrichment/*` | metadata-service (8003) |
| `/limpieza/*` | cleaning-service (8007) |
| `/conocimiento/*` | knowledge-service (8009) |
| `/visualizacion/*`, `/rag/*` | visualization-service (8005); `/rag/chat` transmite por SSE |
| `/almacenamiento/*` | storage-service (8004), solo administradores |

La ruta, el código de estado y el cuerpo pasan sin cambios; se conservan `Authorization`, `Content-Disposition`,
`X-Checksum-SHA256` y `X-Nombre-Archivo`. Cada prefijo registra la ruta base y `{path:path}` para evitar la
redirección 307 de FastAPI: un prefijo nuevo debe seguir el mismo patrón.

## Correr

```powershell
docker compose up -d api-gateway        # con el resto del stack
docker compose restart api-gateway      # después de cambiar el código (no corre con --reload)
```
