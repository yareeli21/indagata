# Indagata — Guía de arranque

Plataforma de microservicios (FastAPI) + frontend React/TanStack Start para la gestión
y análisis de instrumentos de investigación educativa, con RAG (Chroma + Ollama) y
diagnóstico pedagógico.

---

## 1. Requisitos previos

Antes de clonar y correr, instala:

- **Docker Desktop** (con el motor corriendo — "Engine running").
- **Bun** (para el frontend): https://bun.sh
- **Git**.
- ~4 GB de espacio libre (el modelo de Ollama pesa ~2 GB).

> El proyecto se ha probado en **Windows / PowerShell**. En Linux/Mac los comandos de
> Docker son iguales; el script `arrancar.ps1` es específico de PowerShell.

---

## 2. Primer arranque (desde cero, tras clonar)

### Paso 1 — Clonar y entrar al proyecto
```powershell
git clone https://github.com/yareeli21/indagata.git
cd indagata
git checkout elotro-back
```

### Paso 2 — Crear el archivo de entorno `.env`
El `.env` **no está en el repo** (contiene secretos). Créalo copiando la plantilla:
```powershell
Copy-Item .env.example .env
```
Luego **edita `.env`** y cambia al menos:
- `SECRET_KEY` → una cadena larga y aleatoria (es la que firma los JWT; debe ser la misma
  para todos los servicios).
- `POSTGRES_PASSWORD` → si quieres una contraseña propia.

Los demás valores por defecto funcionan para desarrollo local.

### Paso 3 — Levantar el backend (Docker)
Con Docker Desktop abierto, desde la raíz del proyecto:
```powershell
.\arrancar.ps1
```
Si PowerShell bloquea el script por la política de ejecución:
```powershell
powershell -ExecutionPolicy Bypass -File .\arrancar.ps1
```

`arrancar.ps1` hace todo el trabajo pesado:
1. Verifica que Docker esté corriendo.
2. Recrea los volúmenes (Postgres + Chroma limpios, con el esquema actual).
3. Reconstruye las imágenes con el código de la rama.
4. Levanta los 6 microservicios + infraestructura (Postgres, Redis, Ollama, Chroma).
5. Espera a que respondan los `/health`.
6. Descarga el modelo de Ollama `llama3.2:3b` (~2 GB, una sola vez).
7. Siembra los 55 KPIs y reindexa la colección vectorial.

Al terminar verás los usuarios sembrados y la instrucción para el frontend.

### Paso 4 — Levantar el frontend (en otra terminal)
```powershell
cd pixel-perfect-pixel
bun install        # solo la primera vez (instala node_modules)
bun run dev
```
Abre la URL que muestre Vite: **http://localhost:5173**

> ⚠️ **No uses el puerto 8080.** Vite está fijado en **5173** (ver `vite.config.ts`,
> `strictPort: true`). Si otro proceso ocupa 5173, Vite fallará con un error claro en
> vez de saltar a otro puerto en silencio.

### Paso 5 — Iniciar sesión
Usuarios de prueba sembrados:

| Rol          | Email                        | Contraseña         |
|--------------|------------------------------|--------------------|
| admin        | `admin@indagata.com`         | `admin123`         |
| investigador | `investigador@indagata.com`  | `investigador123`  |

---

## 3. Arranques siguientes (día a día)

Si ya hiciste el primer arranque y **quieres conservar tus datos** (instrumentos cargados,
colecciones indexadas):
```powershell
.\arrancar.ps1 -SinBorrar     # NO borra volúmenes; solo reconstruye y levanta
```
Y en otra terminal:
```powershell
cd pixel-perfect-pixel
bun run dev
```

Usa `.\arrancar.ps1` **sin** `-SinBorrar` solo cuando quieras partir de una base de datos
limpia (recrea todo y vuelve a sembrar).

---

## 4. Qué incluye el repo y qué NO (importante)

Al clonar obtienes **todo el código, configuración y datos de prueba**, pero **no** el
entorno de ejecución (por diseño: los secretos y los binarios grandes no se versionan).

| En el repo (se clona)                     | Fuera del repo (se genera localmente)              |
|-------------------------------------------|----------------------------------------------------|
| Código de microservicios y frontend       | `.env` (créalo desde `.env.example`)               |
| `docker-compose.yml`, Dockerfiles         | `node_modules/`, `.venv/` (se instalan)            |
| Datos sintéticos en `storage/raw/`        | Modelo de Ollama `llama3.2:3b` (lo baja `arrancar.ps1`) |
| `.env.example`, `arrancar.ps1`            | Volúmenes de Docker: Postgres y Chroma (los crea `arrancar.ps1`) |

---

## 5. Trabajar con ramas (git) y el entorno

Es clave entender que hay **dos cosas separadas**:

**A) Los archivos del proyecto** los controla git. Al hacer `git checkout <rama>`, el código
en disco cambia a esa rama.
- ✅ **Antes de cambiar de rama, commitea o guarda (`git stash`) tus cambios.** Si cambias
  con cambios sin commitear, git puede arrastrarlos o bloquear el cambio.
- Al volver a `elotro-back`, el código vuelve a ser exactamente el de esa rama.

**B) El entorno de ejecución** NO lo controla git y **no cambia al cambiar de rama**:
- `.env`, `node_modules/`, `.venv/` → se quedan igual.
- **Los volúmenes de Docker** (Postgres con tus datos, Chroma con tus colecciones) viven en
  Docker, no en la carpeta del proyecto. Cambiar de rama en git **no los toca**.
- El modelo de Ollama → igual, persiste en su volumen.

**El único punto que debes resincronizar al cambiar de rama:** los **contenedores en
ejecución** siguen corriendo la imagen que construiste, no el código nuevo de la rama. Si la
otra rama tocó el backend, al volver a `elotro-back` **reconstruye los contenedores** de los
servicios que cambiaron para que corran el código correcto:
```powershell
docker compose -p indagata build <servicio>
docker compose -p indagata up -d --force-recreate <servicio>
```
Si no estás seguro, reconstruir sin caché garantiza tomar el código actual:
```powershell
docker compose -p indagata build --no-cache <servicio>
```

> Los datos en los volúmenes (BD, Chroma) persisten entre ramas. Mientras las ramas
> compartan el mismo esquema de base de datos, no hay conflicto. Si una rama cambia el
> esquema, usa `.\arrancar.ps1` (sin `-SinBorrar`) para recrear la BD limpia.

---

## 6. Servicios y puertos

| Servicio                | Puerto | Contenedor                       |
|-------------------------|--------|----------------------------------|
| api-gateway (entrada)   | 8000   | `indagata_api_gateway`           |
| instrument-service      | 8001   | `indagata_instrument_service`    |
| analysis-service        | 8002   | `indagata_analysis_service`      |
| metadata-service        | 8003   | `indagata_metadata_service`      |
| storage-service         | 8004   | `indagata_storage_service`       |
| visualization-service   | 8005   | `indagata_visualization_service` |
| Postgres                | 5432   | `indagata_postgres`              |
| Redis                   | 6379   | `indagata_redis`                 |
| Ollama                  | 11434  | `indagata_ollama`                |
| ChromaDB                | 8008   | `indagata_chromadb`              |
| Frontend (Vite dev)     | 5173   | (local, `bun run dev`)           |

El **frontend habla solo con el api-gateway (:8000)**, que enruta a los microservicios.

---

## 7. Problemas comunes

- **El chat RAG solo muestra fuentes y no responde** → el modelo de Ollama no está
  disponible. Verifica: `docker exec indagata_ollama ollama list` debe mostrar `llama3.2:3b`.
- **No salen KPIs sugeridos** → la colección de KPIs no está indexada. Reindexa:
  `Invoke-RestMethod http://localhost:8002/vectorizacion/kpis/reindex -Method Post`
- **El chat dice "la investigación no está indexada"** → primero junta/indexa los
  instrumentos de la investigación en la UI; luego pregunta.
- **El frontend no refleja cambios de código** → reinicia `bun run dev` (y recarga el
  navegador con Ctrl+Shift+R).
- **Un servicio no toma cambios de código** → reconstruye su contenedor
  (`docker compose -p indagata build --no-cache <servicio>` + `up -d --force-recreate`).
