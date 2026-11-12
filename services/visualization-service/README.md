# visualization-service (puerto 8005)

Lo que el investigador ve y consulta: el catálogo del acervo, los dashboards de KPIs, el mapa del espacio
vectorial, las descargas, las noticias y el **chat RAG**. Es de solo lectura sobre la base de datos y ChromaDB
(salvo `rag_log`); la ingesta la hace storage-service.

## Endpoints (por el api-gateway)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/visualizacion/catalogo` | Instrumentos con filtros (`q`, `tipo`, `nivel`, `kpi`, `autor`, `anio`, `estado`, `propios`, `aprobados`) y facetas |
| GET | `/visualizacion/catalogo/{id}` | Ficha: Dublin Core, metadatos del tipo, preguntas, estadísticas |
| GET | `/visualizacion/catalogo/{id}/tiempos` | Tiempo de cómputo de cada paso del instrumento |
| GET | `/visualizacion/investigadores` | Autores |
| POST | `/visualizacion/relacionados` | Instrumentos relacionados (KPIs, nivel, similitud) |
| GET | `/visualizacion/kpis/catalogo`, `/visualizacion/kpis/resumen` | Catálogo de KPIs y métricas del acervo |
| POST | `/visualizacion/kpis/{kpi}/datos` | Dashboard de un KPI y qué preguntas lo miden |
| GET | `/visualizacion/instrumentos/{id}/kpis` | KPIs de un instrumento |
| GET | `/visualizacion/espacio/mapa`, `/espacio/vecinos/{tipo}/{ref}`; POST `/espacio/buscar` | Espacio vectorial |
| GET | `/visualizacion/descargas/{id}?formato=crudo\|json\|sav` | Descargas |
| GET | `/visualizacion/noticias` | Noticias reales (RSS de `config/noticias.yaml`, GNews opcional) |
| POST | `/rag/chat` | Chat RAG (SSE o JSON), con `historial` de los últimos mensajes |
| POST | `/rag/interpretar` | Plan JSON de una pregunta y su resultado calculado, sin redacción (para depurar) |
| GET / POST | `/rag/consultas/{id}/metricas` | Métricas de una respuesta: indicadores del sistema (sin juez), RAGAS del juez (se calculan al pedirlas; `?juez=<modelo>` con otro juez), evaluaciones por juez y calificación humana |
| PUT | `/rag/consultas/{id}/calificacion` | Calificación humana: 0 mal, 1 parcial, 2 bien; si entendió y si fundamentó |
| GET | `/rag/consultas/{id}` | Pregunta, respuesta, contexto, plan, tiempos y métricas registrados |
| POST | `/rag/index` | Asegura la ingesta de los instrumentos de una investigación |

## Chat RAG: cinco etapas

1. **Reglas fijas de PA** (`services/dominio.py`, `config/dominio.yaml`): reidentificación, manipulación y tareas
   ajenas reciben un mensaje fijo; las preguntas de uso van a la base de ayuda (`config/ayuda.yaml`).
2. **Interpretación** (`interpretacion.py`): Ollama convierte la pregunta, el historial (sin tablas), el **tema
   anterior** (de qué trató la última respuesta, leído de `rag_log` con el `consultaId` que manda el frontend) y el
   catálogo compacto de cada instrumento (`catalogo.py`) en un plan JSON (`plan_consulta.py`, esquema en
   `esquemas/plan_consulta.json`). El plan se valida contra el catálogo y se ancla a lo que la pregunta dice
   literalmente (`anclaje.py`). Si pide aclaración pero la pregunta se refiere a la respuesta anterior («¿qué significa
   eso?»), se retoma el plan anterior.
3. **Ejecución** (`ejecutor.py`, `hallazgos.py`): cálculo determinista sobre el documento final vigente (filtrar,
   contar, ordenar, limitar, agrupar por contexto, hallazgos). Las preguntas abiertas van a la búsqueda semántica
   en Chroma (`rag_service.py`); las reglas deterministas del enrutador anterior (`enrutador.py`) siguen como
   respaldo cuando no hay plan.
0. **RAG primero** (`rag_service._recuperar_primero`, 5 nov): antes de interpretar se buscan en Chroma los fragmentos
   del alcance más parecidos a la pregunta (o al seguimiento con su pregunta anterior). Orientan a la interpretación
   (`pistas`), responden por sí mismos cuando el plan solo sabría pedir aclaración y la pregunta es del alcance, y
   complementan cualquier cálculo. Las preguntas sobre el instrumento reciben su ficha (`_fichas`).
4. **Recuperación (RAG)** (`rag_service._apoyo_rag`, 4 nov): cada resultado calculado se acompaña con los fragmentos
   de Chroma más parecidos a la pregunta, del mismo instrumento (de las personas del resultado, o de las preguntas de
   los patrones calculados); si con el filtro nada pasa el umbral, entran los más cercanos igual. Si el cálculo y lo
   recuperado difieren, manda el cálculo. Listados, patrones, filtros y pruebas sin calificar también se redactan con
   el texto recuperado, con el cálculo de respaldo. En una entrevista, las preguntas de los intercambios recuperados se suman a la tabla de
   la persona («¿cuántas sesiones le dieron?» está en p04, que no nombra el tema), y los patrones salen del texto
   recuperado. El panel muestra qué se recuperó («Recuperado del RAG»).
5. **Redacción y verificación** (`consulta_planificada.py`, `prompt.py`): el modelo redacta con el RESULTADO CALCULADO
   (las cifras), el TEXTO RECUPERADO (para contextualizar e interpretar) y la conversación previa, con formato por
   intención: lo que dijo una persona se parafrasea e interpreta encima de su tabla; los patrones son 3 o 4. Se
   descarta una redacción vacía, que niega el resultado, escribe una tabla, inventa un ID, cambia u omite una cifra o
   pone entre comillas una frase que no está en los datos o en la pregunta que cita (se regenera una vez y, si vuelve a
   fallar, se muestra el resultado calculado). En conteos, comparaciones, resúmenes, rankings y patrones de encuesta los
   fragmentos llegan sin sus cifras y solo valen las del cálculo.

Cada consulta queda en `rag_log` con su plan y el tiempo de cada etapa. El panel de cada respuesta tiene tres partes:
- **Indicadores del sistema** (`indicadores.py`, sin juez): intención entendida; si la respuesta la redactó el modelo, es
  el cálculo tal cual o una plantilla; regeneraciones; cifras con respaldo; IDs inventados; tiempo por etapa.
- **Juez** (`evaluacion.py`): fidelidad, relevancia y precisión del contexto, **bajo demanda**
  (`RAG_METRICAS_BAJO_DEMANDA`). Cada evaluación se guarda por juez en `rag_metrica_juez`, para comparar jueces sobre las
  mismas respuestas; la del juez por defecto (`RAG_JUEZ_MODELO`) también va en `rag_log.metricas`.
- **Juez Claude Fable 5.2** (`juez_fable.py`, 11 nov): evalúa **cada** respuesta en segundo plano, sin que se pida, en la
  API de Anthropic (no usa la GPU de Ollama). Seis métricas de RAGAS 0.4.3: precisión del contexto, recuerdo del
  contexto, fidelidad, relevancia de la respuesta, sensibilidad al ruido (menor es mejor) y corrección factual (F1). El
  juez solo da veredictos con salida JSON validada por esquema; los puntajes se calculan en Python. Recuerdo, ruido y
  corrección se comparan con una respuesta de referencia que el juez escribe **sin ver la del sistema**, a partir de lo
  que vio el redactor más los `RAG_JUEZ_FABLE_AMPLIADO` fragmentos más cercanos de Chroma (sin umbral). Se guarda en
  `rag_metrica_juez` (`modelo_juez = claude-fable-5-2`) y se lee en `juezFable` de `GET /rag/consultas/{id}/metricas`;
  `POST …/metricas?juez=claude-fable-5-2` la repite. Necesita `ANTHROPIC_API_KEY` (sin ella queda «omitida»); se apaga
  con `RAG_JUEZ_FABLE=false`. Si Fable declina, responde su modelo de respaldo (`fallbacks: "default"`) y la fila queda
  con `fallback: true` y `modelo_real`. Cuesta ~3 llamadas a Fable por respuesta.
- **Calificación humana** (`rag_calificacion`).

El selector del chat tiene «Modelo del servidor», que no envía modelo: el servicio usa `OLLAMA_MODEL` en todas las
etapas. La temperatura de la redacción es `RAG_TEMPERATURA_REDACCION` (0.2); la interpretación y el juez van en 0. El detalle de
las decisiones está en `documentación/02_Desarrollo.md` §X.9.

## Evaluación

- `tools/rag/regresion/`: 28 preguntas con plan y respuesta esperados; `evaluar_regresion.py --modo antes|despues
  [--metricas]` y `comparar.py`.
- `tools/rag/evaluar_ragas.py`: RAGAS 0.4.3 real en un entorno aparte (`.venv-ragas`).

## Pruebas

```powershell
cd services/visualization-service; ..\..\.venv\Scripts\python.exe -m pytest tests
```
