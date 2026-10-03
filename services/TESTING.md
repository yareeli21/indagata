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

El `.env` de la raíz ya trae `POSTGRES_HOST=localhost` y `AUTH_DEV_MODE=true`,
así que el servicio arranca y resuelve el usuario de desarrollo (id=1) sin token.

Una vez levantado:

- **http://localhost:8001/docs** — Swagger UI. Explora y ejecuta cada endpoint
  (p. ej. subir un archivo real en `/instrumentos/upload` y ver la respuesta).
- **http://localhost:8001/redoc** — documentación alternativa (solo lectura).
- **http://localhost:8001/health** — confirma que el servicio responde.

> **Requisito para operaciones que escriben:** el usuario `DEV_USER_ID=1` debe
> existir en `tt_rag.usuario`. Lo siembra
> `infrastructure/postgres/init/05_seed_usuarios.sql` al inicializar Postgres.

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
# Health check
curl http://localhost:8001/health

# Upload multipart: archivo respondido + archivo original (opcional)
curl.exe -F "tipo_instrumento=encuesta" `
         -F "archivo=@C:\ruta\respuestas.csv" `
         -F "archivo_original=@C:\ruta\cuestionario.pdf" `
         http://localhost:8001/instrumentos/upload
```

> En PowerShell usa `curl.exe` (no el alias `curl`) para pasar flags como `-F`.

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
| 500 "usuario de prueba no existe"         | Falta sembrar `DEV_USER_ID=1`; corre los seeds de Postgres.           |
| El servicio no conecta a Postgres en local| `POSTGRES_HOST` debe ser `localhost` (no `postgres`) fuera de Docker. |
| Puerto ocupado                            | Otro proceso usa el puerto; cámbialo con `--port` o libéralo.          |
| Cambios no se reflejan                    | Usa `--reload` en local; en Docker reconstruye con `--build`.          |
