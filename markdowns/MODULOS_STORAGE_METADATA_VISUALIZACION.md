# Módulos storage, metadata y visualización — qué se hizo y cómo correr la app

Este documento explica los cambios que implementaron **storage-service**,
**metadata-service** y **visualization-service**, cómo se integran con el resto
de Indagata y con el frontend (`pixel-perfect-pixel`), y cómo levantar y probar
la aplicación completa.

> Detalle de endpoints de cada servicio: `services/storage-service/README.md`,
> `services/metadata-service/README.md` y `services/visualization-service/README.md`.

---

## 1. Resumen

| Módulo | Responsabilidad |
|---|---|
| **storage-service** (8004) | Todo el almacenamiento. Guarda el archivo crudo **tal cual lo subió el usuario** (con su SHA-256), el archivo limpio, los JSON estandarizados y los `.sav`. Es el **único que escribe en ChromaDB** la colección `instrumentos` (ingesta al RAG). |
| **metadata-service** (8003) | Agrega **obligatoriamente** el Dublin Core (`metadatos_dc`) a todo instrumento y completa los metadatos de su tipo (`metadatos_enriquecidos_encuestas`, `_entrevistas`, `_pruebas`). El **autor los aprueba**; solo entonces el instrumento entra al RAG. |
| **visualization-service** (8005) | Muestra la información: catálogo con filtros, KPIs, **qué preguntas de cada instrumento miden un KPI**, instrumentos relacionados, descargas y el chat RAG sobre lo propio y lo del sistema. |

---

## 2. Flujo de un instrumento

```
 Investigador                     Servicio                         Resultado
 ───────────────────────────────  ───────────────────────────────  ─────────────────────────────────────
 1. Sube el archivo               instrument-service → storage     raw_data + archivo crudo intacto (SHA-256)
 2. (Limpieza de datos)           — pendiente, ver §6 —            instrumento_procesado.ruta_de_archivo_limpio
 3. Revisa el Dublin Core         metadata-service (propuesta)     13 campos propuestos (automáticos + inferidos)
 4. Revisa metadatos del tipo     metadata-service (propuesta)     campos de la tabla de su tipo, inferidos del archivo
 5. APRUEBA los metadatos         metadata-service → storage       metadatos_dc + metadatos_enriquecidos_*,
                                                                    JSON estandarizado, ingesta a Chroma
 6. Acepta KPIs sugeridos         analysis-service                 kpi_inferido (KPIs ↔ instrumento)
 7. Guarda                        metadata-service → storage       JSON final con los KPIs, reingesta al RAG
 8. Explora / consulta            visualization-service            catálogo, dashboards, relacionados, chat
```

Estados de `instrumento_procesado.estado`: `recibido` → `estandarizado` (al
aprobar) → `vectorizado` (al quedar en el RAG). `fecha_aprobado` registra la
aprobación del autor.

---

## 3. Qué hace cada módulo

### 3.1 storage-service

- **Archivos versionados.** Cada artefacto se guarda como
  `<tipo>/<id_crudo>/<versión>__<nombre>` (tipos: `raw`, `clean`, `sav`,
  `metadata`, `analysis`, `temp`) en un manifiesto con tamaño, MIME y SHA-256.
  La escritura es atómica y las rutas se validan contra *path traversal*.
- **Crudo sin cambios.** `raw_data.raw_archivo` guarda la clave del archivo; al
  descargarlo se verifica que su huella no haya cambiado.
- **Lectura para otros servicios.** `GET /almacenamiento/tabla` (CSV, XLSX o el
  JSON de la demo) y `GET /almacenamiento/texto` (PDF, DOCX, TXT, MD).
- **Ingesta al RAG.** Trocea el JSON estandarizado en:
  - `encabezado`: título, objetivo, Dublin Core, metadatos del tipo y KPIs;
  - `pregunta`: **un fragmento por reactivo** con sus opciones y resultados
    (n, media, distribución), lo que permite consultas cualitativas y cuantitativas;
  - `contenido`: el texto íntegro de entrevistas y pruebas.

  Registra cada fragmento en `documento_vectorizado` / `coleccion_vectorial`.
  **Solo ingiere instrumentos con metadatos aprobados.**
- **Purga.** Al borrar un instrumento elimina sus archivos derivados y sus vectores.
- Es **interno**: los demás servicios lo llaman con un token de servicio; por
  el api-gateway solo un administrador puede usarlo.

### 3.2 metadata-service

- **Propuesta de Dublin Core** (13 campos). Automáticos: creador (usuario),
  tipo, fecha de carga, formato (MIME), fuente (nombre del archivo), idioma
  (detectado). Inferidos del contenido: título, tema, descripción, cobertura
  (nivel educativo + población), editor (institución detectada).
- **Metadatos del tipo**, inferidos del archivo:
  - *Encuesta (CSV/XLSX)*: número de respondentes, dimensiones (encabezados
    `Bloque [ítem]` de Google Forms), carreras, población, palabras clave,
    notas de calidad de los datos; además detecta el tipo de cada reactivo
    (Likert, escala, opción múltiple, abierta) y sus estadísticas.
  - *Entrevista (PDF/DOCX/TXT)*: preguntas del entrevistador, objetivo,
    metodología (semiestructurada, a profundidad…), institución.
  - *Prueba (PDF/DOCX/TXT)*: reactivos y opciones, reactivos por sección,
    unidad de aprendizaje, ciclo escolar, grado, grupo, tipo de prueba, niveles
    de la taxonomía de Bloom, nivel educativo.
- **LLM opcional.** Lo que no se puede deducir (objetivo, constructo…) se pide
  a Ollama si `METADATA_USAR_LLM=true`. Si Ollama no responde, el autor lo
  captura: nunca es requisito.
- **Origen de cada valor**: `automatico`, `archivo`, `inferido`, `llm` o
  `aprobado`; el frontend lo muestra junto a cada campo.
- **Aprobación del autor** (`POST /api/metadata/{id}/aprobar`): valida
  obligatorios, persiste las tablas, genera el JSON estandarizado (compatible
  con el formato que ya leen analysis- e instrument-service), lo guarda en el
  storage-service y pide la ingesta al RAG. Se puede volver a aprobar para
  corregir (se sobrescribe y se reingiere).
- **Finalizar** (`POST /api/metadata/{id}/finalizar`): añade al JSON los KPIs
  aceptados en `kpi_inferido` y lo guarda como versión final.

### 3.3 visualization-service

- **Catálogo** con filtros (texto, tipo, nivel, KPI, autor, año, estado,
  propios, aprobados) y facetas; ficha completa de cada instrumento.
- **KPIs**: catálogo desde la tabla `kpi` (con variables), métricas del acervo
  y dashboard por KPI.
- **Relación KPI ↔ preguntas**: para un KPI se toma su vector (colección `kpis`)
  y se buscan las **preguntas** de cada instrumento más cercanas. El dashboard y
  la vista rápida del instrumento muestran esas preguntas con su % de similitud.
- **Relacionados**: instrumentos de otros autores por KPIs en común, nivel y
  similitud semántica.
- **Descargas**: crudo (cualquiera), JSON y `.sav` (solo el autor o un
  administrador). El `.sav` lleva etiquetas de variable y de valor de SPSS.
- **Chat RAG**: responde con los fragmentos de la investigación activa (o de todo
  el acervo), incluye el contexto de la investigación en el prompt y registra
  cada consulta en `rag_log`.

---

## 4. Cambios en otras partes del proyecto

| Dónde | Cambio |
|---|---|
| `shared/auth/servicio.py` | Token de servicio (rol `servicio`) para llamadas internas. |
| `shared/db/core/config.py` | `STORAGE_SERVICE_URL`, `METADATA_USAR_LLM`, `METADATA_LLM_TIMEOUT`. |
| instrument-service | `HttpStorageBackend`: con `STORAGE_BACKEND=http` el crudo lo guarda el storage-service; al borrar se purgan derivados y vectores. |
| api-gateway | Proxy de `/visualizacion/*`; reenvía las cabeceras de descarga (nombre del archivo). |
| `docker-compose.yml` | Variables y dependencias de los tres servicios; el storage-service usa Postgres, Chroma y el modelo de embeddings. |
| `Dockerfile.storage-service` | Instala torch CPU (para los embeddings de la ingesta). |
| Frontend | Asistente de carga con propuesta → aprobación; campos alineados con las tablas; investigadores, relacionados, descargas, KPIs y chat conectados al backend; las investigaciones guardan sus instrumentos elegidos. |

Las rutas del metadata-service dejaron de tener el doble segmento
(`/api/metadata/{id}/...` en lugar de `/api/metadata/metadata/{id}/...`).

---

## 5. Cómo correr la app

### 5.1 Requisitos

- **Docker Desktop** (Windows: con WSL 2) **abierto y con el motor corriendo**.
- Node.js 20+ (o Bun) para el frontend.
- GPU NVIDIA opcional para Ollama (ver §8).

### 5.2 Backend con Docker

Desde la raíz del repositorio:

```powershell
# 1. Variables de entorno
Copy-Item .env.example .env        # Linux/macOS: cp .env.example .env

# 2. Construir y levantar todo
docker compose up -d --build

# 3. Comprobar que todo responde (en PowerShell usa curl.exe, no el alias curl)
docker compose ps
curl.exe http://localhost:8006/health   # api-gateway
curl.exe http://localhost:8003/health   # metadata-service
curl.exe http://localhost:8004/health   # storage-service
curl.exe http://localhost:8005/health   # visualization-service
```

La primera vez Postgres ejecuta `infrastructure/postgres/init/01_schema.sql` y
`05_seed_usuarios.sql` (solo si el volumen `postgres_data` está vacío).

### 5.3 Datos iniciales

```powershell
# Modelo del LLM (una sola vez; queda en el volumen ollama_data)
docker exec -it indagata_ollama ollama pull llama3.2:3b

# Catálogo de 55 KPIs desde infrastructure/postgres/seed/kpis_ampliados.csv
# (OJO: vacía la tabla kpi y, en cascada, kpi_variable y kpi_inferido)
docker exec indagata_analysis_service python scripts/seed_kpis.py

# Vectorizar los KPIs en Chroma (colección `kpis`)
curl.exe -X POST http://localhost:8002/vectorizacion/kpis/reindex

# (Opcional) los 21 instrumentos de la demo de storage/raw
docker exec indagata_instrument_service python scripts/seed_demo.py
```

Sin KPIs en la tabla `kpi` y en la colección `kpis`, el paso «KPIs sugeridos»
del asistente y los dashboards de KPIs quedan vacíos.

### 5.4 Frontend

```powershell
cd pixel-perfect-pixel
Copy-Item .env.example .env        # VITE_API_URL=http://localhost:8006
npm install                        # o: bun install
npm run dev                        # o: bun run dev
```

Abre **http://localhost:8080**.

Usuarios de desarrollo:

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@indagata.com` | `admin123` |
| Investigador | `investigador@indagata.com` | `investigador123` |

> El servicio `frontend` del `docker-compose.yml` todavía monta `./frontend`
> (el frontend anterior) y expone el puerto 3000; para la app actual usa el
> frontend local de este paso.

### 5.5 Recorrido de prueba

1. Entra como investigador → **Subir instrumento** → elige **Encuesta** y un CSV
   (por ejemplo `storage/clean/4_clean.csv`). Opcional: adjunta el instrumento
   original (PDF/DOCX/TXT).
2. Revisa el **Dublin Core** y los **metadatos del tipo** propuestos (cada
   campo indica de dónde salió) y completa los obligatorios (*).
3. En **Aprobar metadatos** revisa el JSON y aprueba: el instrumento entra al RAG.
4. Acepta los **KPIs sugeridos** y **guarda**.
5. En **Mis instrumentos** abre la vista rápida: verás sus KPIs y las preguntas
   que los miden, y podrás descargar crudo, JSON o `.sav`.
6. **Armar investigación** → elige instrumentos (y relacionados de otros
   autores) → **Chat** para preguntar sobre ellos; **KPIs** para los dashboards.

### 5.6 Puertos

| Servicio | URL en el host |
|---|---|
| Frontend (local) | http://localhost:8080 |
| api-gateway | http://localhost:8006 |
| instrument-service | http://localhost:8001 |
| analysis-service | http://localhost:8002 |
| metadata-service | http://localhost:8003 |
| storage-service | http://localhost:8004 |
| visualization-service | http://localhost:8005 |
| ChromaDB | http://localhost:8008 |
| Visor de vectores | http://localhost:8085 |
| Postgres / Redis / Ollama | 5432 / 6379 / 11434 |

Cada servicio publica su documentación interactiva en `/docs`
(p. ej. http://localhost:8003/docs).

---

## 6. Decisiones y pendientes

- **Limpieza de datos** (imputación, duplicados, registros vacíos): no forma
  parte de estos módulos y sigue pendiente. Cuando exista, basta con guardar el
  archivo limpio en el storage-service (tipo `clean`) y llenar
  `instrumento_procesado.ruta_de_archivo_limpio`: metadata-service y las
  descargas `.sav` ya lo usan en lugar del crudo.
- **Una sola colección para el RAG.** El chat ya no crea una colección por
  investigación: consulta la colección `instrumentos` filtrando por los
  instrumentos de la investigación (o sin filtro para todo el acervo). Las
  colecciones `investigacion_*` anteriores quedan sin uso.
- **Instrumentos de la demo**: los que tienen estado `estandarizado` se
  consideran aprobados y pueden entrar al RAG.
- Las investigaciones y su selección de instrumentos se guardan en el navegador
  (no hay servicio de investigaciones todavía). Las noticias siguen en mock.
- Las guías antiguas de `services/metadata-service/*.md` (salvo el README) y
  `services/README.md` describen la arquitectura anterior.

---

## 7. Pruebas automatizadas

Cada servicio tiene pruebas con SQLite en memoria y dobles de ChromaDB, Ollama
y del storage-service (no requieren Docker ni descargar modelos):

```powershell
python -m venv .venv-pruebas
.venv-pruebas\Scripts\pip install fastapi==0.115.6 pydantic==2.9.0 pydantic-settings==2.5.0 sqlalchemy==2.0.25 "psycopg[binary]==3.2.3" httpx==0.27.0 python-multipart "python-jose[cryptography]==3.3.0" "passlib[bcrypt]==1.7.4" bcrypt==4.0.1 email-validator openpyxl pypdf python-docx pytest pandas pyreadstat

cd services/storage-service;       ..\..\.venv-pruebas\Scripts\python -m pytest tests
cd ../metadata-service;            ..\..\.venv-pruebas\Scripts\python -m pytest tests
cd ../visualization-service;       ..\..\.venv-pruebas\Scripts\python -m pytest tests
```

Resultado esperado: 18 + 13 + 12 pruebas en verde.

---

## 8. Problemas comunes

**`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`**
El motor de Docker no está corriendo. Abre **Docker Desktop**, espera a que
indique *Engine running* y comprueba con `docker version` (debe mostrar una
sección `Server`). Si Docker Desktop no aparece en el menú Inicio, reinstálalo
desde docker.com con el backend WSL 2.

**`could not select device driver "nvidia"` al levantar `ollama`**
El servicio `ollama` reserva una GPU NVIDIA. Sin GPU, borra el bloque `deploy:`
de ese servicio en `docker-compose.yml` (Ollama correrá en CPU, más lento) o
desactiva las sugerencias del LLM con `METADATA_USAR_LLM=false` en `.env`.

**La primera aprobación tarda**
El storage-service descarga el modelo de embeddings la primera vez (queda en el
volumen `hf_cache`). Si la ingesta falla, la aprobación se conserva y la
respuesta lo indica; se reintenta al armar una investigación.

**«KPIs sugeridos» aparece vacío**
Falta sembrar la tabla `kpi` o reindexar la colección `kpis` (§5.3).

**`usuario de prueba (usuario_id=1) no existe` o `column kpi.nombre does not exist`**
El volumen `postgres_data` viene de una versión anterior del proyecto: los
scripts de `infrastructure/postgres/init/` solo corren con el volumen vacío, así
que no se crearon los usuarios o la tabla `kpi` conserva la forma vieja. Si no
necesitas los datos de esa base, recréala y repite §5.3:
`docker compose down` → `docker volume rm <carpeta>_postgres_data` (el nombre
exacto sale en `docker volume ls`; con la carpeta `indagata` es
`indagata_postgres_data`) → `docker compose up -d`. No uses `down -v`: también
borraría el modelo de Ollama y la caché de embeddings.

**El chat responde que no encontró información**
Solo entran al RAG los instrumentos con metadatos aprobados; aprueba los tuyos
o amplía la selección de la investigación.
