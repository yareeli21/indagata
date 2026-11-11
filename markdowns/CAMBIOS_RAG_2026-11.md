# Cambios al chat RAG — 9 al 11 de noviembre de 2026

Rama: `PArturo` (commit `aa75164e` + este). Resumen para el equipo de **qué se modificó, por qué, qué hay que aplicar a
mano y cómo se evalúa**. Las pruebas del servicio del chat pasan (394) y hay una nueva en analysis-service.

## ⚠️ Lo que cada quien tiene que hacer al traer la rama

1. **Aplicar la migración nueva** (índice de texto completo para la búsqueda híbrida; no cambia datos):
   ```powershell
   docker compose exec postgres psql -U postgres -d indagata_db -f /migrations/2026_20_busqueda_hibrida.sql
   ```
   Sin el índice la búsqueda funciona, pero más lenta. Rollback: `2026_20_busqueda_hibrida_ROLLBACK.sql`.
2. **Reiniciar** `visualization-service` y `analysis-service` (`docker compose restart <servicio>`).
3. Si algún instrumento aparece en el chat con IDs `q01…` en lugar de `p01…`, está indexado con el JSON técnico
   viejo: reindexarlo con `POST /almacenamiento/indice/instrumentos/{id}` (`{"reindexar": true}`, admin). Le pasó a
   «Simulación» (117): pasó de 27 a 6,246 fragmentos.

## 1. Velocidad

| Problema | Cambio | Archivo |
|---|---|---|
| Con 31 instrumentos el catálogo de la interpretación medía 12–28 mil tokens; Ollama lo recortaba por el **inicio** a ~2,050 (se perdían instrucciones y ejemplos) y no reusaba su caché: 16–107 s por plan | Si el alcance no cabe, entran primero los instrumentos que recuperó el RAG y los que nombra la pregunta, hasta un tope de caracteres (`_MAX_CARACTERES_PROMPT`). Ahora 3–10 s | `services/interpretacion.py`, `consulta_planificada.py` |
| Bucles de repetición en la redacción | `num_predict` 1024 solo en redacción y corte cuando el texto empieza a repetirse | `services/ollama_client.py` |

Medido: la GTX 1650 procesa ~170 tokens/s y escribe ~47 tokens/s; sin flash attention el modelo no cabe (24 % a CPU).
No tocar `OLLAMA_FLASH_ATTENTION` ni `OLLAMA_KV_CACHE_TYPE`.

## 2. Búsqueda

### Umbral
- `RAG_MIN_SCORE`: 0.35 → **0.65** (`shared/db/core/config.py`).
- Se quitó el **relleno** con fragmentos bajo el umbral (en `_recuperar_primero` y en `_apoyo_rag`): era la causa de
  responder con instrumentos que no trataban el tema.
- Los fragmentos cercanos (≥ `RAG_FUERA_MAX`) siguen yendo solo como **pistas** a la interpretación (no a la respuesta).
- Un plan `hallazgo` sobre un **tema** que nada del alcance alcanza responde «sin información»
  (`_hallazgo_sin_relacion`); no aplica a «dame un dato interesante» ni a seguimientos reales.
- Si la interpretación reescribe la consulta semántica, se busca también con la pregunta original y se usa la mejor.

### Búsqueda híbrida — `services/hibrida.py`
- Significado (Chroma) + palabras (`to_tsvector('spanish', chunk_texto)` en Postgres para encontrar, **BM25** con la
  frecuencia real de cada palabra para ordenar), combinadas con **RRF** (k = 60).
- Llega a la respuesta si: coseno ≥ `RAG_MIN_SCORE` **o** contiene ≥ `RAG_MIN_COBERTURA` (0.75) de las palabras con
  contenido de la pregunta (y 2 o más).
- **Ficha y KPI** («textos generales») por significado solo cuentan si además comparten ≥ 50 % de las palabras.
- Candidatos por palabra: primero preguntas/reactivos/ficha/KPI y después lo de cada persona; máximo 2 fragmentos de
  respondente/alumno/intercambio por instrumento en la lista por palabras.
- La similitud que se muestra en las tarjetas sigue siendo el coseno.
- Parámetros nuevos: `RAG_HIBRIDA` (true; false = solo semántica, igual que antes), `RAG_MIN_COBERTURA` (0.75),
  `RAG_LEXICOS_MAX` (40). En las pruebas `RAG_HIBRIDA` está apagada por defecto (`tests/conftest.py`).

## 3. Respuestas y conversación
- **Prompt, regla 16** (`services/prompt.py`): interpretar con sus palabras, puede citar frases textuales, no abrir
  siempre con «Según el contexto…» ni repetir «esto sugiere».
- **Seguimientos de inferencia** (`services/seguimiento.py`): «¿por qué crees que pasa eso?», «¿quién lo dijo?»,
  «¿qué podría hacer la universidad?» se responden con la evidencia de la respuesta anterior leída de `rag_log`
  (sus fuentes con pasajes y su resultado calculado), sin reinterpretar sobre toda la colección. Solo puede nombrar
  IDs que aparecen en la evidencia. «¿Qué significa eso?» tras un cálculo se difiere: si `_retomar_anterior` retoma
  el plan, gana ese camino. Lo que pide datos nuevos («¿cuántos…?», «R017», «p04») sigue por la interpretación.
- **«¿Cómo inferiste que no hay…?»** tras un «sin información»: explicación **sin LLM** (qué buscó, la parte más
  parecida y su similitud frente al umbral).
- `_VERSION_RESPUESTAS` llegó a 42 (la caché vieja no se reusa).

## 4. Trazabilidad y «Ver métricas»
- Cada tarjeta de fuente trae `similitud` (mayor coseno de ese instrumento con la pregunta, aunque la respuesta sea un
  cálculo). `models.py → FuenteChatOut.similitud`.
- Botón **«Ver métricas»** debajo de cada respuesta (`VerMetricas.tsx`), servido por
  `GET /rag/consultas/{id}/metricas → indicadores.{recuperacion, fundamentacion, citas}`
  (`services/metricas_respuesta.py`): fragmentos usados con coseno, cobertura de palabras, lugar en cada búsqueda y
  por qué pasaron; oraciones respaldadas por lo recuperado; oraciones con cita y citas a fuentes inexistentes.
- **Ojo**: son métricas de **diagnóstico**. «Fundamentación» es una aproximación léxica a la fidelidad de RAGAS y
  «Citas» se inspira en ALCE; la evaluación formal es la de la sección 6.

## 5. Interfaz (frontend)
- Chat con altura fija: la barra de pregunta y el panel de noticias ya no se pierden al desplazarse; al abrir una
  conversación se ve el último mensaje (`ChatPage.tsx`).
- Un solo modelo en el selector: «Llama 3.2 (3B) — local» (`api/chat.ts`, `types/index.ts`).
- KPIs: clic en una tarjeta abre su ficha (`KpisPage.tsx`).
- Ingesta: nivel educativo solo «Licenciatura», por defecto (`StepDublinCore.tsx`, `UploadWizard.tsx`, `api/carga.ts`;
  los filtros del catálogo conservan «Posgrado»).
- Ingesta: **KPI agregados a mano** al final del paso de KPI (`StepKpis.tsx`): buscador del catálogo sin los
  sugeridos; se confirman aceptados con `score 0`, sin evidencia y justificación «Agregado manualmente por el
  investigador: …». El backend ya lo aceptaba (prueba nueva en `analysis-service/tests/test_kpis_perfil.py`).

## 6. Evaluación — `tools/rag/evaluacion/`

**Banco congelado** `banco_v1.json` (11 nov, revisado): 72 preguntas sobre los 31 instrumentos vigentes.
- 62 con respuesta (2 por instrumento), redactadas con palabras distintas a las del instrumento, 2 paráfrasis cada una,
  fragmento correcto etiquetado (`instrumentoId` + `preguntaId`); respuesta esperada de encuestas y pruebas calculada
  con SQL sobre `respuesta_interpretada` (sin el chat). Las 20 de entrevistas **no tienen hechos clave** todavía.
- 8 sin respuesta (temas que ningún fragmento menciona) y 2 fuera de dominio.
- Desarrollo (34) para calibrar / prueba (38) para reportar. **No modificar el banco antes de medir.**
- Se regenera con `construir_banco_v1.py`; guía de revisión en `README.md`.

**Cómo correrla** (con la app levantada):
```powershell
venv\Scripts\python.exe tools\rag\evaluacion\evaluar_v1.py recuperacion          # Hit@k, MRR, nDCG, Recall (gratis)
venv\Scripts\python.exe tools\rag\evaluacion\evaluar_v1.py chat --conjunto prueba # chat de punta a punta (gratis)
.venv-ragas\Scripts\python.exe tools\rag\evaluacion\evaluar_v1.py ragas --chat tools\rag\evaluacion\resultados\chat_<fecha>.json --juez <modelo de Claude> --limite 2
```
La recuperación corre dentro del contenedor (`services/visualization-service/scripts/evaluar_recuperacion.py`). RAGAS
usa Claude como juez por la API de Anthropic (`ANTHROPIC_API_KEY` en el `.env`, nunca en el código) y
`nomic-embed-text` en Ollama para los embeddings; el entorno aislado se instala con `tools/rag/requirements-ragas.txt`
(se agregó `anthropic`). La conexión con Claude **aún no se ha probado**.

### Resultados del 11 nov (conjunto de prueba) — `resultados/`

**Búsqueda** (`recuperacion_20261111_1421.md`), ranking antes del umbral, k = 8, IC 95 % por bootstrap:

| Alcance | Búsqueda | Hit@8 | MRR@8 | nDCG@8 |
|---|---|---|---|---|
| Instrumento de la pregunta | Semántica | 0.81 [0.65, 0.94] | 0.73 | 0.69 |
| | Híbrida | **0.90** [0.77, 1.00] | 0.73 | 0.68 |
| Colección completa | Semántica | 0.42 [0.26, 0.58] | 0.40 | 0.35 |
| | Híbrida | **0.65** [0.48, 0.81] | 0.46 | 0.39 |
| Paráfrasis, colección | Semántica / Híbrida | 0.36 / **0.66** | 0.34 / 0.46 | |

- La híbrida mejora claro en lo difícil (colección y paráfrasis); dentro de un instrumento los intervalos se traslapan.
- Hit@1 baja un poco con la híbrida (0.68 → 0.65).
- Encuestas y pruebas son débiles en la colección completa (preguntas Likert parecidas entre instrumentos); las
  entrevistas, ~1.0.
- 2 de 7 preguntas sin respuesta tienen un fragmento que pasaría el filtro (S04 videojuegos, S05 aire acondicionado).

**Chat de punta a punta** (`chat_20261111_1440.md`), sin caché, llama3.2:3b:

| Medida | Resultado |
|---|---|
| Decisión correcta | 76.3 % (38) |
| Falsos rechazos | 8 de 31 |
| Falsas aceptaciones | 1 de 7 (S01: fue una aclaración, no una respuesta inventada) |
| Exactitud de cifras | 15.4 % (13 con cifra) |
| Latencia p50 / p95 | 19.9 s / 58.7 s |

- Los **falsos rechazos** vienen del umbral: el fragmento estaba en el ranking pero no pasó 0.65 ni la cobertura de
  palabras. Calibrarlo con el conjunto de **desarrollo** es el siguiente paso.
- La **exactitud de cifras** está subestimada: se compara contra el % de la opción más elegida y en Likert el chat
  suele reportar el acuerdo agregado («50.5 % de acuerdo»). Hay además errores reales de la interpretación: I94-a
  respondió con los datos de un alumno (A001) e I117-a con «'contexto_num' no es una variable de contexto».

## 7. Pendientes
- Calibrar `RAG_MIN_SCORE` / `RAG_MIN_COBERTURA` con el conjunto de desarrollo y volver a medir con el de prueba.
- Medir la exactitud también contra el acuerdo agregado en preguntas Likert.
- Anotar los hechos clave de las 20 preguntas de entrevistas.
- Instalar `.venv-ragas`, `ollama pull nomic-embed-text`, probar RAGAS con el juez local y luego con Claude
  (`--limite 2`), y validar el juez contra calificación humana (kappa; scripts en `scripts/modelos/`).
- Planificador: «¿hay mujeres y hombres encuestados?» y «¿y de ellos cuántos tienen beca?» terminan en aclaración;
  cuando el alcance es toda la colección a veces calcula sobre los 31 instrumentos.
- `esquemas/plan_consulta.json` desactualizado (`test_esquema_publicado_coincide_con_el_modelo` falla desde antes).
