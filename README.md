# Indagata

Plataforma para gestionar y consultar instrumentos de investigación educativa: **encuestas**, **pruebas
estandarizadas** (que no se califican: se describe lo que contestaron los alumnos) y **entrevistas**. Una
investigadora sube un instrumento, la plataforma lo limpia con su ayuda, propone sus metadatos (Dublin Core y del
tipo), sugiere KPIs por similitud semántica y, una vez aprobado, lo publica para consultarlo en un **chat RAG**,
en dashboards de KPIs y en un mapa del espacio vectorial.

Todo el sistema (código, rutas, interfaz y documentación) está en español.

## Arquitectura

Microservicios FastAPI que comparten una base PostgreSQL (esquema `tt_rag`) y el paquete `shared/`; ChromaDB
guarda los vectores y Ollama corre los modelos de lenguaje localmente.

| Componente | Puerto | Qué hace |
|---|---|---|
| `pixel-perfect-pixel/` | 3000 | Frontend (TanStack Start + React 19 + Tailwind 4) |
| `services/api-gateway` | 8006 | Autenticación (JWT) y proxy hacia los servicios |
| `services/instrument-service` | 8001 | Carga y lectura del instrumento |
| `services/cleaning-service` | 8007 | Limpieza asistida por tipo de instrumento |
| `services/metadata-service` | 8003 | Dublin Core y metadatos del tipo, aprobación |
| `services/knowledge-service` | 8009 | Perfil semántico y documento final interpretado |
| `services/analysis-service` | 8002 | KPIs por similitud semántica, espacio vectorial |
| `services/storage-service` | 8004 | Único dueño de los archivos y de la ingesta en Chroma |
| `services/visualization-service` | 8005 | Catálogo, dashboards, descargas, noticias y chat RAG |
| ChromaDB / visor | 8008 / 8085 | Vectores (`instrumentos`, `kpis`) y visor PCA de solo lectura |
| PostgreSQL / Redis / Ollama | 5432 / 6379 / 11434 | Base de datos, caché y modelos (`llama3.2:3b` redacta, `qwen2.5:3b` juzga) |

Flujo de un instrumento (asistente de 7 pasos): archivo → limpieza → Dublin Core → metadatos del tipo → aprobación
→ KPIs sugeridos → guardar (perfil, documento final y publicación). El chat responde en cuatro etapas:
interpretación (plan JSON), ejecución determinista, redacción con formato por intención y verificación de cifras.

## Cómo levantarlo

```powershell
copy .env.example .env          # y ajusta lo necesario
docker compose up -d            # todo el stack
```

Abre http://localhost:3000 y entra con `admin@indagata.com` / `admin123` (o `investigador@indagata.com` /
`investigador123`). La guía completa, con modelos de Ollama, catálogo de KPIs y solución de problemas, está en
[`markdowns/LEVANTAR_LA_APP.md`](markdowns/LEVANTAR_LA_APP.md). El código está montado en los contenedores pero
los servicios no corren con `--reload`: después de un cambio, `docker compose restart <servicio>`.

## Estructura

```
services/            un servicio por carpeta, cada uno con su README
shared/              configuración, modelos ORM, esquemas, autenticación, lectura de archivos y consultas comunes
pixel-perfect-pixel/ frontend
infrastructure/      Dockerfiles, esquema SQL (init/), migraciones, catálogo de KPIs (seed/), visor de Chroma
storage/             archivos de los instrumentos (crudos, limpios, JSON) e instrumentos de prueba
tools/               generación de datos sintéticos, verificación de formatos y limpieza, evaluación del RAG
documentación/       capítulos de la tesis: 02 Desarrollo, 03 Pruebas, 04 Resultados
evidencias/          evidencia citada en los capítulos
markdowns/           guías de uso
```

## Instrumentos de prueba

`storage/instrumentos_sinteticos/` tiene instrumentos listos para subir, cada uno con su original y sus metadatos:
11 encuestas (`enc_01`…`enc_11`, `enc_10_turno` con turno), la encuesta de 2000 respondentes con su PDF de Google
Forms, 10 pruebas (`pru_01`…`pru_10`, respuestas aleatorias sin clave) y 10 entrevistas (`ent_01`…`ent_10`).
`enc_01`, `pru_01` y `ent_01` tienen además una versión sucia (`*_sucio_respondido.*`) para probar la limpieza. Cómo
se generan: `tools/data_synthesis/README.md` y `storage/instrumentos_sinteticos/METODOLOGIA_DATOS_SINTETICOS.md`;
cómo probarlos: [`markdowns/GUIA_PRUEBAS.md`](markdowns/GUIA_PRUEBAS.md).

## Pruebas

Pytest por servicio, desde la carpeta del servicio (no juntes varios servicios en un mismo proceso):

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd services/visualization-service; ..\..\.venv\Scripts\python.exe -m pytest tests
```

Hay pruebas en cleaning, knowledge, metadata, storage, visualization y analysis; usan SQLite en memoria y dobles de
Chroma, Ollama y storage. Frontend: `npm run lint` y `node node_modules/typescript/bin/tsc --noEmit` en
`pixel-perfect-pixel/`. Evaluación del chat: `tools/rag/regresion/` (28 preguntas con respuesta verificada, antes
y después del rediseño).

## Documentación

- `documentación/02_Desarrollo.md`, `03_Pruebas.md`, `04_Resultados.md`: diseño, decisiones, pruebas y resultados;
  cada afirmación lleva su fuente.
- `CLAUDE.md`: guía técnica del repositorio (arquitectura, flujo de datos, chat, convenciones).
- `infrastructure/postgres/SCHEMA_CHANGES.md`: historia del esquema; `init/01_schema.sql` es la fuente de verdad.
- `markdowns/`: levantar la app, probarla, dar de alta usuarios e historia de las pruebas del RAG.
