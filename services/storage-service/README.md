# storage-service (puerto 8004)

Autoridad de **todo el almacenamiento** de Indagata:

- **Archivos.** Guarda el instrumento crudo **tal cual lo subió el usuario**
  (bytes intactos + SHA-256 que se verifica en cada descarga), el archivo
  limpio, los JSON estandarizados (`metadata` al aprobar, `analysis` con KPIs)
  y los `.sav`. Cada artefacto tiene una clave estable y versionada
  `<tipo>/<instrumentoId>/<versión>__<nombre>`; esa clave es lo que se guarda en
  `raw_data.raw_archivo`.
- **Base vectorial.** Es el **único escritor** de la colección `instrumentos`
  de ChromaDB y de `documento_vectorizado`. Solo ingiere instrumentos con
  metadatos **aprobados por su autor**.

Es un servicio **interno**: lo llaman los demás servicios con un token de
servicio (`shared/auth/servicio.py`). Por el api-gateway (`/almacenamiento/*`)
solo pueden usarlo administradores; los investigadores descargan por el
visualization-service, que aplica la regla de propiedad.

## Ingesta al RAG

`POST /almacenamiento/indice/instrumentos/{id_crudo}` toma el último JSON
estandarizado del instrumento y lo trocea:

| Chunk | Contenido | Para qué |
|---|---|---|
| `encabezado` (chunk 0) | título, objetivo, Dublin Core, metadatos del tipo, KPIs | contexto general; comparar instrumentos |
| `pregunta` (uno por reactivo) | sección, texto, opciones y resultados (n, media, distribución) | RAG cuali+cuanti; qué preguntas miden un KPI |
| `contenido` | texto íntegro de entrevistas y pruebas | análisis cualitativo |

Cada vector lleva metadata (`instrumentoId`, `titulo`, `tipo`, `autorId`,
`nivel`, `anio`, `seccion`, `preguntaId`, `kpis`) para filtrar por
investigación. Reingerir reemplaza los vectores anteriores; las filas de
`documento_vectorizado` de otras colecciones (p. ej. la evidencia de KPIs del
analysis-service) no se tocan. El instrumento pasa a estado `vectorizado`.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/almacenamiento/archivo` | Guardar binario (`raw` · `clean` · `sav` · `temp`) |
| POST | `/almacenamiento/json` | Guardar JSON (`metadata` · `analysis`) |
| GET | `/almacenamiento/artefacto/{tipo}/{id}` | Último artefacto (o `?version=`), con contenido si es JSON |
| GET | `/almacenamiento/artefactos` | Listar / filtrar (`instrumentoId`, `tipo`) |
| GET | `/almacenamiento/descarga?ruta=` | Bytes del archivo + `X-Checksum-SHA256` |
| GET | `/almacenamiento/tabla?ruta=` | Contenido tabular (CSV, XLSX o JSON v1) |
| GET | `/almacenamiento/texto?ruta=` | Texto plano (PDF, DOCX, TXT, MD, JSON) |
| DELETE | `/almacenamiento/archivo?ruta=` | Eliminar un archivo (idempotente) |
| DELETE | `/almacenamiento/instrumentos/{id}` | Purgar archivos y vectores de un instrumento |
| GET | `/almacenamiento/estadisticas` | Uso por tipo y estado de la caché |
| POST | `/almacenamiento/mantenimiento/limpiar-temporales` | Borrar `temp` antiguos |
| POST | `/almacenamiento/indice/instrumentos/{id}` | Ingerir / reingerir al RAG |
| DELETE | `/almacenamiento/indice/instrumentos/{id}` | Quitar sus vectores |
| GET | `/almacenamiento/indice/instrumentos/{id}` | Estado de la ingesta |
| GET | `/almacenamiento/indice/colecciones` | Colecciones de Chroma y conteos |

`ruta` acepta la clave del manifiesto o las rutas heredadas guardadas en la BD
(`raw/<uuid>__x.csv`, `storage/raw/inst_01.v1.json`) y siempre se verifica que
quede dentro de la raíz de storage.

## Estructura

```
storage-service/
├── main.py
├── models.py                DTOs HTTP
├── dependencies.py          token de servicio / administrador
├── routers/  files.py · index.py · health.py
└── services/
    ├── file_manager.py      manifiesto versionado, escritura atómica, SHA-256, purga
    ├── chroma_indexer.py    troceo e ingesta a Chroma + documento_vectorizado
    ├── cache_manager.py     caché TTL en proceso + limpieza de temporales
    ├── lectura.py           lectores de tablas y texto
    └── vectores.py          cliente de Chroma y modelo de embeddings
```

## Pruebas

```sh
cd services/storage-service
python -m pytest tests
```
