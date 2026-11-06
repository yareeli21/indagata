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

## Paso a paso

Modelos elegidos en el experimento (`documentación/03_Pruebas.md`): redactores `gemma3:4b` (el principal) y
`qwen3:4b-instruct` (el segundo); juez `qwen3:4b-instruct`. En otra computadora, primero sube los instrumentos y
regenera los casos con sus ids (`markdowns/GUIA_PRUEBAS.md`, sección 7).

1. **Una vez:** descarga los modelos y, mientras dure la prueba, desactiva la caché.
   ```powershell
   docker compose exec ollama ollama pull gemma3:4b
   docker compose exec ollama ollama pull qwen3:4b-instruct
   ```
   En `.env`: `RAG_CACHE_HORAS=0`, para que una pregunta repetida se responda de nuevo.
2. **Por cada redactor** (`gemma3:4b`, después `qwen3:4b-instruct`):
   1. En `.env`, pon `OLLAMA_MODEL=<modelo>`.
   2. Libera la GPU: `docker compose exec ollama ollama stop <modelo anterior>`.
   3. Recrea el chat: `docker compose up -d visualization-service`.
   4. Comprueba: `docker compose exec visualization-service printenv OLLAMA_MODEL`.
   5. Corre los casos desde la carpeta del repositorio, sin usar el chat mientras tanto (unos 45 min con gemma):
      ```powershell
      $env:PYTHONIOENCODING="utf-8"; .venv\Scripts\python.exe -u services\visualization-service\scripts\modelos\correr_casos.py casos.json casos_pru03.json casos_ent11.json
      ```
      Al final imprime la corrida (`gemma3:4b=1845-1910`): anótala. Si la memoria no alcanza, cierra los programas
      pesados; si se corta, vuelve a correr solo los archivos de casos que faltan.
   6. Para preguntar a mano en lugar del script: Ctrl+F5 en el chat, el instrumento, «Modelo del servidor», una
      «Nueva conversación» por caso, las preguntas tal cual y **sin** pulsar «Calcular evaluación».
3. **Califica** cada corrida, una vez por archivo de casos:
   `docker compose exec visualization-service python scripts/modelos/calificar.py --casos casos.json --corrida gemma3:4b=<inicio>-<fin>`.
4. **Juez:** `juzgar.py --juez qwen3:4b-instruct` con todas las corridas, una vez por archivo de casos. Tarda horas;
   puede quedarse de noche.
5. **Reporte:** `reporte.py` con todas las corridas; después se copia a `evidencias/modelos_<fecha>/`. Para compartir
   las calificaciones: `exportar.py` (CSV).
6. **Al terminar:** `.env` con `OLLAMA_MODEL=gemma3:4b` y `RAG_CACHE_HORAS=24`, y `docker compose up -d visualization-service`.

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
