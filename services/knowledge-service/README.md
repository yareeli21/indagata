# Knowledge Service

Puerto **8009**; se expone en el gateway bajo `/conocimiento/*`. Construye los artefactos de conocimiento de un instrumento ya limpio y con metadatos aprobados:

| Artefacto | Dónde se muestra | Para qué |
|---|---|---|
| **Perfil semántico** | «Aprobar metadatos» | Describe el instrumento y es **lo único** que se usa para asociar KPIs |
| **Documento final** *(fases siguientes)* | «Guardar» | Respuestas interpretadas por respondente: el insumo de los chunks del RAG |

El JSON técnico de metadata-service (el registro técnico) **no se toca**: sigue guardándose en storage-service.

## Almacenamiento
Se usa una sola tabla, `tt_rag.version_conocimiento` (migración `infrastructure/postgres/migrations/2026_11_conocimiento.sql`), con una fila por versión.

Estados: `perfil_aprobado` → `kpis_confirmados` → `borrador` → `vigente`. Al publicar otra versión, la anterior pasa a `reemplazado`.

## Perfil semántico
- **Contiene solo:**
  - título, objetivo, temas, palabras clave, nivel educativo, población y contexto (en texto);
  - las preguntas agrupadas por sección, con opciones únicamente en las preguntas categóricas, binarias y de opción múltiple.
- **No contiene:** métricas, conteos, respuestas, IDs de columna, rutas, formatos, fechas de carga ni tipos técnicos. Del contexto se eliminan las frases con métricas, como las notas automáticas «20 registros…».
- **Validación:** el perfil se valida contra `esquemas/perfil.json`.
- **De dónde salen las preguntas** (`services/estructura.py`):
  1. Del **instrumento original**, si se subió (`services/original.py`). Cada columna se empareja con una pregunta del original por:
     - similitud de palabras, tolerante a encabezados truncados;
     - o por **sección + posición**, cuando los encabezados vienen codificados («Falta_de_organi_item3»).
     Las preguntas del original que corresponden a columnas de contexto (turno, semestre) se omiten.
  2. Si no hay original, de los **encabezados** del CSV limpio, con secciones por grupo («Pregunta [aspecto]» o un prefijo numerado).
  3. En instrumentos anteriores a la limpieza, del **JSON técnico**.
- **Avisos:** cuando algo no se encuentra, la respuesta incluye `avisos` (p. ej. «3 preguntas del archivo no están en el original»).
- **IDs:** son globales y estables, como `INS-0012-s1` o `INS-0012-p03` (en pruebas, `r03`). Salen de la misma versión de limpieza y del mismo original, así que el documento final reconstruye exactamente los mismos.

## Endpoints
| Método y ruta | Uso |
|---|---|
| `POST /conocimiento/{id}/perfil/vista-previa` | Perfil con los metadatos del formulario, sin guardar. Cuerpo: `{dublin_core, enriquecidos}` |
| `POST /conocimiento/{id}/perfil` | Perfil con los metadatos **aprobados**; crea la versión N |
| `GET /conocimiento/{id}/perfil` | Perfil de la versión actual |
| `GET /health` | Estado del servicio |

Solo pueden usarlos el autor del instrumento o un administrador (JWT del gateway).

## Pruebas
```powershell
cd services/knowledge-service; ..\..\.venv\Scripts\python.exe -m pytest tests -q
```
Los reportes de limpieza de `tests/datos/limpieza_*.json` se generan con los motores **reales** de cleaning-service: `python tests/datos/generar_limpiezas.py`, después de `crear_archivos.py`.

## Asociación de KPIs (vive en analysis-service, usa este perfil)
- **Endpoints:** `POST /vectorizacion/perfil/propuestas {id_crudo}` y `POST /vectorizacion/perfil/confirmar`. Se llaman con el JWT, directo a analysis-service, igual que el resto de `/vectorizacion`.
- **Qué se embebe:** el perfil general (U₀) y una unidad por pregunta (Uᵢ), en texto con plantilla, con el mismo modelo que los KPIs. La colección `kpis` **solo se lee**: no se toca cómo se embeben (`texto_contexto_rag_vectorial`).
- **Fórmula** (`app/vectorization/perfil/asociacion.py`):
  `score = 0.45·g + 0.45·p + 0.10·c`
  - g = similitud con el perfil general;
  - p = media de las 3 preguntas más parecidas;
  - c = min(1, preguntas con similitud ≥ 0.45 / 3).

  Los pesos y umbrales están en `shared` settings (`KPI_PESO_*`, `KPI_UMBRAL_EVIDENCIA`).
- **Justificación:** el LLM (Ollama) la redacta y, si falla, se usa una plantilla. El investigador puede editarla, y su origen queda como `llm`, `llm_revisada`, `plantilla` o `plantilla_revisada`.
- **Al confirmar:** la misma fila de `version_conocimiento` guarda en `decisiones_kpi` los KPIs aceptados **y los rechazados**. Los aceptados se agregan a `perfil.kpis_asociados` (con el mismo formato del documento final) y además se escriben en `kpi_inferido` / `kpi_inferido_chunk`, porque los tableros los leen.
- **Comparación** con el método anterior: `docker compose exec -e STORAGE_SERVICE_URL=http://storage-service:8004 analysis-service python scripts/comparar_kpis.py <id_crudo>`.

## Capa de interpretación (`services/interpretacion/`)
Convierte cada valor crudo del CSV limpio en una respuesta con `valor`, `significado` (la etiqueta exacta), `nivel` (la agrupación para consultas) y `estado` (`respondida` / `sin_respuesta` / `no_interpretada`). Es **determinística**: no usa el LLM.

| Tipo | Regla |
|---|---|
| likert / cuadrícula | Código → etiqueta del libro de códigos → nivel. En ítems invertidos se agrega `valor_recodificado`; el significado sigue siendo lo que la persona respondió |
| binaria | Sí/No, 1/0, True/False, S/N → «Sí»/«No» (nivel `si`/`no`) |
| categórica | Etiqueta normalizada (la grafía más frecuente) |
| opción múltiple / ranking | `seleccion` (lista; en ranking, ordenada) |
| escala lineal | «4 en escala 1–5, donde 1 = Nada y 5 = Mucho» si hay anclas en el original; si no, «4 de 5» |
| calificación / numérica | «8.5 (escala 0–10)» / «14 horas» (la unidad sale del encabezado) |
| texto | Tal cual |
| vacías | `sin_respuesta`: nunca se omiten |
| pruebas | Letra → texto de la opción del original, o «Opción C», más `correcta`, `estado` y `motivo` |

- **Niveles:** salen de `shared/config/escalas_likert.yaml` (`niveles` de cada escala), por posición, así que sirven para escalas de 4, 5 o 7 puntos.
- **Datos personales:** se detectan con la lista `datos_personales` de `config/conocimiento.yaml`, por palabra completa.

## Documento final (`services/documento/`)
Es el insumo de los chunks del RAG. Se construye después de la asociación de KPIs; la vista y el almacenamiento llegan en la fase 5.

- **Encuesta:** `preguntas` (definición, escala con niveles, opciones, KPIs relacionados y resumen precalculado) y `respondentes` (R001…, con su contexto y sus respuestas interpretadas, una por pregunta).
- **Prueba:** `reactivos` (texto, opciones, respuesta correcta, % de acierto, distribución, distractor más elegido, dificultad y discriminación) y `alumnos` (A001…, contexto, puntaje, total, % y respuestas).
- **Entrevista:** `preguntas_guia` y `participantes` (E01…) con `intercambios`. Lo que dice el entrevistador es la pregunta; lo que dice cada participante hasta la siguiente intervención del entrevistador es su respuesta. Los turnos consecutivos del mismo hablante se unen.

**Principios del documento:**
- Cada respuesta aparece una sola vez.
- Los IDs son globales (`INS-0012-p03`).
- La relación KPI ↔ pregunta se puede recorrer en ambos sentidos (`kpis_asociados[].evidencia` ↔ `kpis_relacionados`).
- No contiene datos personales: los hablantes también se anonimizan dentro del texto.
- Se valida con JSON Schema (`esquemas/documento_<tipo>.json` + `comun.json`).

`services/consultas.py` reúne funciones determinísticas que responden los criterios de aceptación sobre el JSON. `tests/test_criterios.py` comprueba cada resultado contra un cálculo independiente hecho sobre el CSV limpio.

### Almacenamiento y endpoints del documento
El documento completo se guarda en storage-service como artefacto JSON tipo `documento` (`documento/<id>/<n>__v<versión>_documento_final.json`, con SHA-256). Su registro (`ruta_documento`, `esquema_version`, `avisos`, `sha256`, fechas) va en la misma fila de `version_conocimiento`.

| Método y ruta | Uso |
|---|---|
| `POST /conocimiento/{id}/documento` | Genera, valida y guarda el documento de la versión actual (`borrador`) |
| `GET /conocimiento/{id}/documento` | Vista ligera: todo menos las respuestas individuales, con su conteo y una muestra |
| `GET /conocimiento/{id}/documento/json` | Documento completo («Ver JSON») |
| `POST /conocimiento/{id}/documento/{versión}/publicar` | Lo deja `vigente`; la versión vigente anterior pasa a `reemplazado` |

En el wizard, «Guardar» genera el documento al entrar y lo publica al guardar el instrumento. La tabla de respuestas en formato largo (`respuesta_interpretada`) queda para la etapa del RAG y se derivará del documento vigente.
