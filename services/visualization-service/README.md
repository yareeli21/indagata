# visualization-service (puerto 8005)

Muestra la información de forma amigable para el investigador: cómo se
relacionan sus instrumentos con los KPIs, filtrar el acervo y hacer consultas
sobre lo que subió **y** lo que hay en el sistema. Es de solo lectura sobre la
BD y ChromaDB (salvo `rag_log`); la ingesta la hace el storage-service.

## Endpoints (por el api-gateway)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/visualizacion/catalogo` | Instrumentos con filtros (`q`, `tipo`, `nivel`, `kpi`, `autor`, `anio`, `estado`, `propios`, `aprobados`) y facetas |
| GET | `/visualizacion/catalogo/{id}` | Ficha: Dublin Core, metadatos del tipo, preguntas y estadísticas |
| GET | `/visualizacion/investigadores` | Autores (nombre e institución) |
| POST | `/visualizacion/relacionados` | Instrumentos de otros autores relacionados (KPIs, nivel, similitud semántica) |
| GET | `/visualizacion/kpis/catalogo` | Catálogo de KPIs (tabla `kpi` + variables) e instrumentos asociados |
| GET | `/visualizacion/kpis/resumen` | Métricas del acervo |
| POST | `/visualizacion/kpis/{kpi}/datos` | Dashboard de un KPI y **qué preguntas** de cada instrumento lo miden |
| GET | `/visualizacion/instrumentos/{id}/kpis` | KPIs de un instrumento y las preguntas que los miden |
| GET | `/visualizacion/descargas/{id}?formato=crudo\|json\|sav` | Descargas (de instrumentos ajenos, solo el crudo) |
| POST | `/rag/index` | Asegura la ingesta de los instrumentos de una investigación |
| POST | `/rag/chat` | Chat RAG (SSE o JSON) sobre la investigación o todo el acervo |

### ¿Qué preguntas miden un KPI?

Para un KPI se toma su vector de la colección `kpis` (la escribe el
analysis-service) y se buscan, dentro de la colección `instrumentos`, los
chunks de tipo `pregunta` de cada instrumento más cercanos a él. Así el
dashboard muestra, por instrumento, las preguntas con su porcentaje de
similitud. Un KPI se asocia a un instrumento si el autor lo aceptó
(`kpi_inferido`) o si figura en el diseño del instrumento (`kpi_hints`).

### Chat RAG

Recupera los fragmentos más cercanos a la pregunta (fichas, reactivos con sus
resultados, texto de entrevistas) filtrando por los instrumentos de la
investigación; sin filtro consulta todo el acervo aprobado. El prompt incluye el
contexto de la investigación (objetivo, población, nivel) y cada consulta queda
en `rag_log`.

### Descarga .sav

Se genera desde la tabla de respuestas (archivo limpio si existe, si no el
crudo): variables `P1…Pn` con la pregunta como etiqueta, categorías de texto
codificadas con etiquetas de valor (ordinales en escalas de acuerdo/frecuencia)
y se guarda en el storage-service para no recalcularla.

## Estructura

```
visualization-service/
├── main.py
├── models.py                DTOs HTTP (espejan los tipos del frontend)
├── dependencies.py          JWT
├── routers/  catalog.py · kpis.py · download.py · rag.py · health.py
└── services/
    ├── query_engine.py      fichas, filtros, facetas, KPIs, evidencia, relacionados
    ├── rag_service.py       ingesta delegada, recuperación, respuesta y rag_log
    ├── sav_export.py        exportación a SPSS
    ├── storage_client.py    cliente del storage-service
    ├── vectores.py          lectura de Chroma y embeddings
    ├── ollama_client.py     generación con Ollama (degradación grácil)
    └── prompt.py            prompt de fundamentación
```

## Pruebas

```sh
cd services/visualization-service
python -m pytest tests
```
