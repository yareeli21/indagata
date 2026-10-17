# Cómo levantar Indagata (paso a paso)

Esta guía es para quien baja el repositorio por primera vez, o para quien ya lo tenía y trae los
cambios nuevos de la rama `pruebas`. Los comandos son para **Windows con PowerShell**; en Linux o
macOS funcionan igual, salvo donde se indica.

> Qué hace cada servicio: [MICROSERVICIOS.md](MICROSERVICIOS.md).
> Nota: `markdowns/QUICKSTART.md` está desactualizado (puertos viejos). Usa esta guía.

---

## 1. Requisitos

| Requisito | Detalle |
|---|---|
| Git | Cualquier versión reciente |
| Docker Desktop | Con WSL 2 en Windows. Asignarle **al menos 8 GB de RAM** (Settings → Resources); con menos, los servicios de embeddings se caen |
| Disco | ~15 GB libres (imágenes, el modelo de embeddings y el modelo de Ollama) |
| GPU NVIDIA (opcional) | Acelera el chat. Sin GPU todo funciona, pero ve al paso 4 |
| Puertos libres | 3000, 8001–8009, 8085, 5432, 6379 y 11434 |

## 2. Obtener el código

**Primera vez:**
```powershell
git clone https://github.com/yareeli21/indagata.git
cd indagata
git checkout pruebas
```

**Si ya tenías el repositorio:**
```powershell
cd indagata
git checkout pruebas
git pull origin pruebas
```

## 3. Crear el archivo `.env`

```powershell
Copy-Item .env.example .env
```

Los valores por defecto sirven para desarrollo. Lo único importante es que `SECRET_KEY` sea la misma
para todos los servicios (el `docker-compose.yml` ya la reparte). Si la cambias, cierra sesión en la
app y vuelve a entrar.

## 4. Si tu equipo **no** tiene GPU NVIDIA

El servicio `ollama` de `docker-compose.yml` reserva una GPU NVIDIA. Sin ella, `docker compose up`
falla con un error de *device driver*. Comenta este bloque dentro de `ollama:`:

```yaml
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
```

No subas ese cambio al repositorio. El chat funcionará en CPU, más lento.

## 5. Construir y levantar todo

```powershell
docker compose up -d --build
```

La primera vez tarda entre 10 y 20 minutos, porque descarga imágenes e instala dependencias.
Revisa que todo esté arriba:

```powershell
docker compose ps
```

Todos los contenedores `indagata_*` deben aparecer como `Up` (o `healthy`). Si alguno se reinicia
una y otra vez, mira su log:

```powershell
docker compose logs -f cleaning-service
```

## 6. Base de datos

### 6.a Instalación nueva (no existía el volumen `postgres_data`)
No hay que hacer nada. Al primer arranque, Postgres ejecuta `infrastructure/postgres/init/*.sql`,
que crea todas las tablas (incluidas `limpieza_ejecucion` y `version_conocimiento`) y los usuarios
de prueba.

### 6.b Ya tenías una base de datos de una versión anterior
Los scripts de `init/` **no** vuelven a ejecutarse, así que aplica las migraciones nuevas. Son
idempotentes: ejecutarlas dos veces no hace daño.

```powershell
docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_10_limpieza.sql
docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_11_conocimiento.sql
```

**Alternativa: empezar de cero.** Esto **borra** todos los datos, instrumentos y usuarios creados:
```powershell
docker compose down -v
docker compose up -d --build
```

## 7. Cargar los modelos y los KPIs (solo la primera vez)

**7.1 Modelo de lenguaje de Ollama.** Se usa para el chat, los metadatos interpretativos y la
justificación de KPIs:
```powershell
docker compose exec ollama ollama pull llama3.2:3b
```

**7.2 Catálogo de KPIs.** Son dos comandos. Sin ellos, el paso «KPIs sugeridos» del asistente sale
vacío.

Primero, cargar el catálogo en PostgreSQL desde `infrastructure/postgres/seed/KPI_Ampliacion.csv`:
```powershell
docker compose exec analysis-service python scripts/seed_kpis.py
```

Después, vectorizarlo en la colección `kpis` de ChromaDB. Este paso pide iniciar sesión:
```powershell
$token = (curl.exe -s -X POST http://localhost:8006/auth/login -H "Content-Type: application/json" -d '{\"email\":\"admin@indagata.com\",\"password\":\"admin123\"}' | ConvertFrom-Json).access_token
curl.exe -s -X POST http://localhost:8002/vectorizacion/kpis/reindex -H "Authorization: Bearer $token"
```
La respuesta indica cuántos KPIs se indexaron. La primera vez se descarga el modelo de embeddings
(unos cientos de MB), que queda en caché en el volumen `hf_cache`.

> **Atención: volver a sembrar borra los KPIs aceptados.** `seed_kpis.py` reemplaza el catálogo
> completo con `TRUNCATE … CASCADE`, así que también borra los KPIs que ya se aceptaron para cada
> instrumento (`kpi_inferido`). Si la base de datos ya tenía instrumentos con KPIs (por ejemplo,
> porque se cambió de catálogo), hay que repetir con cada uno los pasos «KPIs sugeridos» y «Guardar»
> del asistente.

## 8. Comprobar que funciona

**8.1 Servicios.** Cada uno debe responder `200`:
```powershell
foreach ($p in 8006, 8001, 8002, 8003, 8004, 8005, 8007, 8009) { curl.exe -s -o NUL -w "$p -> %{http_code}`n" "http://localhost:$p/health" }
```

**8.2 Abrir la app:** <http://localhost:3000>

| Usuario | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@indagata.com` | `admin123` |
| Investigador | `investigador@indagata.com` | `investigador123` |

**8.3 Probar el flujo completo.** En «Subir instrumento», usa un instrumento sintético incluido en el
repositorio (`storage/instrumentos_sinteticos/`):

| Tipo | Archivo respondido | Instrumento original |
|---|---|---|
| Encuesta | `encuestas/enc_04_respondido.csv` | `encuestas/enc_04_original.txt` |
| Prueba estandarizada (sin clave) | `pruebas/pru_04_respondido.csv` | `pruebas/pru_04_original.txt` |
| Entrevista | `entrevistas/ent_01_respondido.txt` | `entrevistas/ent_01_original.txt` |

Recorre los 7 pasos: Archivo, Limpieza, Dublin Core, Metadatos del tipo, Aprobar metadatos, KPIs
sugeridos y Guardar. Al final, el instrumento aparece en el catálogo y se puede consultar en el chat.

Otros accesos útiles:
- Documentación de cada API (Swagger): `http://localhost:<puerto>/docs`, por ejemplo <http://localhost:8007/docs>.
- Visor de vectores: <http://localhost:8085>.

## 9. (Opcional) Ejecutar las pruebas automatizadas

No necesitan Docker. Crea el entorno de Python **en la raíz del repositorio** (Python 3.12):

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r services\cleaning-service\requirements.txt -r services\cleaning-service\requirements-dev.txt
```

Instala los `requirements*.txt` del servicio que quieras probar. Después ejecuta las pruebas
**desde la carpeta de ese servicio**, un servicio a la vez:

```powershell
cd services\cleaning-service
..\..\.venv\Scripts\python.exe -m pytest tests -q
```

No ejecutes pytest de varios servicios en un solo comando: sus módulos se llaman igual (`main`,
`models`…) y chocan.

## 10. Trabajar en el día a día

| Situación | Qué hacer |
|---|---|
| Traer cambios nuevos | `git pull origin pruebas` |
| Cambió código Python de un servicio | `docker compose restart <servicio>` (el código está montado, pero uvicorn no recarga solo) |
| Cambió un `requirements.txt` o un Dockerfile | `docker compose up -d --build <servicio>` |
| Cambió `package.json` o `package-lock.json` del frontend | `docker compose up -d --build --renew-anon-volumes frontend` (si no, conserva los `node_modules` viejos) |
| Cambió código del frontend y no se ve | `docker compose restart frontend` y recarga la página con Ctrl+F5 |
| Llegó una migración nueva en `infrastructure/postgres/migrations/` | Ejecutarla como en el paso 6.b |
| Apagar todo (conserva los datos) | `docker compose down` |

## 11. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `401 Unauthorized` en todas las pantallas | El token expiró (dura 60 min) o cambió `SECRET_KEY`. Cierra sesión y entra de nuevo |
| `409` en el paso «Dublin Core» | El instrumento no tiene una limpieza confirmada. Vuelve al paso «Limpieza» y confírmala |
| «KPIs sugeridos» vacío | Falta el paso 7.2 (`seed_kpis.py` y el reindex) |
| El chat no responde o tarda mucho | Falta el modelo (paso 7.1) o no hay GPU. Revisa `docker compose logs ollama` |
| Un contenedor se cae con *Killed* o exit 137 | Falta memoria. Sube la RAM de Docker Desktop o apaga `chroma-viewer` y `ollama` si no los usas |
| `port is already allocated` | Otro programa usa ese puerto, por ejemplo un Postgres local en 5432. Ciérralo o cambia el puerto del host en `docker-compose.yml` |
| Error de GPU al levantar `ollama` | Aplica el paso 4 |
| Tablas que no existen (`limpieza_ejecucion`, `version_conocimiento`) | Base de datos anterior. Aplica las migraciones del paso 6.b |
