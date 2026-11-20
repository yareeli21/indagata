# Fase 2: chunks (7 nov 2026)

Commit `310af4c`. Se reindexaron los 8 instrumentos vectorizados (`reindexado.log`).

## Qué se cambió

| Antes | Después |
|---|---|
| Piezas de 450 caracteres: el modelo de embeddings solo lee 128 tokens y lo demás no se embebía | Piezas medidas con el tokenizador del modelo (`vectores.contar_tokens`); ninguna pasa de 128 tokens |
| El texto de la pregunta se recortaba a 160 caracteres en su chunk | Texto completo en cada pieza (solo se recorta si él solo no deja lugar al cuerpo) |
| Un chunk por pregunta que empezaba con «Respuestas válidas: 1966…» | Dos chunks: **definición** (texto, sección, opciones o extremos de la escala, KPIs; sin cifras) y **resultados** (distribución con n, interpretación) |
| Reactivo con la distribución solo en % | Distribución con la letra, el texto de la opción y su n, y las respuestas en blanco y nulas |
| Ficha sin indicaciones ni estructura de la prueba | Ficha con indicaciones del entrevistador, participantes, preguntas de la guía y reactivos por sección |
| Intercambio con la pregunta del turno (podía venir recortada o con indicaciones) | Intercambio con el texto completo de la pregunta guía, los temas y la valoración del análisis (Fase 1) |
| La búsqueda por similitud incluía los ~6,600 chunks de respondentes | Sin chunks de personas salvo que la consulta nombre a alguien (R017, A001, E02); lo de cada persona lo calcula la ruta estructurada |
| Metadatos: instrumentoId, tipo, seccion, preguntaId, respondenteId… | Además `tipoChunk` y `parte` (definición o resultados) |

La colección de KPIs no se tocó.

## Chunks que pasan del límite del modelo (128 tokens)

| Instrumento | Antes | Después |
|---|---|---|
| 127 (encuesta) | 1,094 de 6,667 | **0 de 7,059** |
| 130 (prueba) | 385 de 465 | **0 de 1,337** |
| 61 (encuesta de control) | 149 de 690 | **0 de 818** |
| 109 (encuesta) | 146 de 850 | **0 de 1,081** |
| 59 (encuesta) | 11 de 145 | **0 de 157** |
| 129, 131, 60 (entrevistas) | 0 | 0 |

Fuentes: `../chat_2026-11-07_antes/diagnostico.md` §3 (antes) y `truncados_despues.json`.

## Recuperación (hit rate@k, `recuperacion_antes*.json`, `recuperacion_despues.json`)

43 preguntas de las baterías y 9 de control con su chunk correcto (`tools/rag/recuperacion_oro.json`). Mismo modelo
de embeddings que el chat, 8 fragmentos, sin umbrales.

| | Antes (sin filtro) | Después (sin filtro) | Después (con el filtro del chat) |
|---|---|---|---|
| Baterías, hit@3 | 0.61 | 0.65 | **0.79** |
| Baterías, hit@8 | 0.65 | 0.72 | **0.93** |
| Encuesta 127, hit@3 | 0.25 | 0.38 | **0.69** |
| Prueba 130, hit@3 | 0.82 | 0.82 | **0.91** |
| Entrevista 129, hit@3 | 0.81 | 0.81 | 0.81 |
| Control (61 y 60), hit@3 | 0.89 | 1.00 | **1.00** |

Fallas que quedan (con el filtro):
- **Preguntas sobre el instrumento** (ENC-18, PRU-19, ENT-18, ENT-20, ENT-21): la ficha no queda entre los primeros
  fragmentos. Por similitud, «¿de qué trata?» se parece más a las preguntas que a la ficha. Esas preguntas deben ir a
  la ficha por intención (Fase 3), no por similitud.
- **ENC-01, ENC-04, ENC-17, ENC-22:** el chunk correcto aparece en el lugar 5 a 8 o no aparece. El modelo de
  embeddings confunde preguntas parecidas (p04 «¿cuántos profesores tienen doctorado?» frente a p12 «situación
  laboral»). La interpretación resuelve la pregunta por el catálogo, no por la similitud.

## Casos del chat (comprobación de que nada se rompió, `../chat_2026-11-07_fase2/`)

- **ENC-01, ENC-06 y PRU-02** recuperan su pregunta y responden con la cifra.
- **PRU-15 (A001)** recupera los chunks del alumno porque la consulta lo nombra.
- **Pendiente para las fases 3 y 4:** en el turno (2) el chat dice que A001 dejó r17 en blanco, y en el turno (1) que
  respondió «Falso» en r17. Es una falla del hilo y de la operación, no de los chunks.
