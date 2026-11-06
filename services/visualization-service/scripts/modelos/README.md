# Experimento de modelos: redactor × juez

Compara modelos de Ollama en el chat sin cambiar su lógica. Se usan las mismas 28 preguntas (14 casos) sobre el
mismo instrumento, y solo cambia el modelo. Cada redactor responde una vez; después, cada juez califica las
respuestas de todos los redactores. Así sale la matriz redactor × juez sin repetir las preguntas.

| Archivo | Qué hace |
|---|---|
| `generar_casos.py` | Escribe `casos.json`: los 14 casos, el tipo de cada turno (dato, inexistente, interpretativo, capacidad, control), las intenciones aceptadas y las cifras correctas, calculadas directo de la base |
| `correr_casos.py` | Hace en el chat real las preguntas de uno o varios archivos de casos, una conversación por caso y con el historial igual que la interfaz; imprime la corrida. Se corre desde el host |
| `exportar.py` | Exporta a CSV (Excel) las consultas con su calificación humana, quién calificó, lo recuperado del RAG y las métricas de cada juez; por defecto solo lo calificado (`--todas`, `--desde`, `--hasta`). Escribe `storage/evaluacion_modelos/exportes/` |
| `juzgar.py` | Evalúa con **un** juez las respuestas de una o varias corridas y muestra el avance en la terminal (`rag_metrica_juez`) |
| `calificar.py` | Califica en la terminal los turnos de una corrida que no tienen calificación humana (la misma tabla que el panel) |
| `reporte.py` | Calcula las métricas contra la referencia y el cruce juez / sin juez / persona, y escribe `storage/evaluacion_modelos/<fecha>/` |
| `comun.py` | Corridas, emparejamiento de consultas con turnos, kappa de Cohen y Spearman |

Todos se corren dentro del contenedor del chat, que tiene la base, los embeddings y `./storage` montado:

```powershell
docker compose exec visualization-service python scripts/modelos/generar_casos.py
docker compose exec visualization-service python scripts/modelos/juzgar.py --juez qwen2.5:3b --corrida llama3.2:3b=1328-1370
docker compose exec visualization-service python scripts/modelos/calificar.py --corrida llama3.2:3b=1328
docker compose exec visualization-service python scripts/modelos/reporte.py --corrida llama3.2:3b=1328-1370 --corrida qwen2.5:3b=1371-1410
```

Una **corrida** es `modelo=INICIO-FIN`: el rango de `rag_log_id` donde la persona hizo las preguntas con ese
redactor. El final es opcional. Se toman las consultas de ese modelo cuya pregunta coincide con un turno (sin
mayúsculas, acentos ni signos). Si un turno se preguntó dos veces, cuenta la última.

Los seguimientos de `casos.json` son los textos que la investigadora escribió en la corrida con llama (consultas
1344–1365): con los demás modelos se copian tal cual, aunque no vengan al caso con su respuesta.

Para revisar una corrida (turnos encontrados, los que faltan y los que no tienen calificación), corre `calificar.py`:
lo primero que muestra es el conteo; Ctrl+C sale sin cambiar nada.

## Fase 6: prueba y entrevista nuevas

`generar_casos_fase6.py` escribe `casos_pru03.json` (prueba 130, 12 casos, 22 turnos) y `casos_ent11.json` (entrevista
129, 8 casos, 13 turnos) con las preguntas propuestas el 2 nov, tal cual. Los otros tres scripts eligen el archivo con
`--casos` (por defecto `casos.json`, el del instrumento 127). Como las preguntas de los dos instrumentos son distintas,
una sola corrida (un rango de consultas por redactor) sirve para los dos archivos:

```powershell
docker compose exec visualization-service python scripts/modelos/generar_casos_fase6.py --prueba 130 --entrevista 129
docker compose exec visualization-service python scripts/modelos/juzgar.py --casos casos_pru03.json --juez qwen3:4b-instruct --corrida gemma3:4b=1500
docker compose exec visualization-service python scripts/modelos/reporte.py --casos casos_pru03.json --corrida gemma3:4b=1500 --corrida qwen3:4b-instruct=1560
```

`reporte.py` con otro archivo de casos escribe en `storage/evaluacion_modelos/<fecha>_<nombre>/` (p. ej.
`2026-11-03_pru03`). En `intenciones`, `null` significa que el turno lo resuelve una regla de dominio (privacidad o
manipulación) sin plan.

## Paso a paso (lo hace la investigadora)

1. En `.env`, pon `RAG_CACHE_HORAS=0` mientras dure el experimento, para que una pregunta repetida se responda de
   nuevo.
2. Por cada redactor (`llama3.2:3b`, `qwen2.5:3b`, `qwen3:4b`, `gemma3:4b`):
   1. En `.env`, pon `OLLAMA_MODEL=<modelo>`.
   2. Libera la GPU: `docker compose exec ollama ollama stop <modelo anterior>`.
   3. Recrea los servicios:
      `docker compose up -d analysis-service metadata-service knowledge-service visualization-service`.
   4. Comprueba: `docker compose exec visualization-service printenv OLLAMA_MODEL`.
   5. En el chat: Ctrl+F5, instrumento 127, «Modelo del servidor». Pregunta «hola» para calentar el modelo y anota el
      número de consulta del panel o la hora.
   6. Revisa la carga en la GPU con `docker compose exec ollama ollama ps` (columnas `PROCESSOR` y `CONTEXT`).
   7. Haz los 14 casos: una «Nueva conversación» por caso, las preguntas tal cual (con sus erratas), **sin** pulsar
      «Calcular evaluación». Califica cada respuesta en el panel; lo que se quede sin calificar (p. ej., porque
      «Nueva conversación» lo quitó de la pantalla) se califica después con `calificar.py`.
3. Jueces: una corrida de `juzgar.py` por juez, con todas las corridas de redactores.
4. Reporte: `reporte.py` con todas las corridas. Después se copia a `evidencias/modelos_<fecha>/`.
5. Al terminar: `.env` con `OLLAMA_MODEL=llama3.2:3b` y `RAG_CACHE_HORAS=24`, y el mismo `up -d`.

## Qué mide

- **Sin juez** (`services/indicadores.py`, también en el panel):
  - intención entendida;
  - si la respuesta la redactó el modelo, es el cálculo tal cual o una plantilla;
  - regeneraciones;
  - cifras con respaldo;
  - IDs inventados;
  - tiempo por etapa.
- **Contra la referencia** (`casos.json`): intención correcta, contexto suficiente, exactitud de cifras, criterios y
  similitud semántica (coseno con mpnet). Los turnos interpretativos no tienen exactitud ni similitud: los califica la
  persona.
- **Juez** (LLM-as-a-judge): fidelidad, relevancia y precisión del contexto, una evaluación por juez.
- **Cruce:**
  - kappa entre la fidelidad del juez y las cifras con respaldo;
  - kappa entre «juez aprobado» (promedio ≥ 0.7) y la calificación humana «Bien»;
  - Spearman entre el juez y la calificación humana;
  - acuerdo entre jueces;
  - sesgo de autoevaluación (la diagonal menos el resto);
  - qué turnos fallan con todos los modelos, lo que apunta a una falla del código.
