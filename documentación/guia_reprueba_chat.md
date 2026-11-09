# Guía para repetir la evaluación del chat

Cómo volver a correr las baterías de preguntas del chat, calificarlas y obtener las mismas medidas de Pruebas Y.4.6.
Todos los comandos van en PowerShell, desde la raíz del repositorio.

## 1. Qué se mide y dónde queda

| Medida | Herramienta | Resultado |
|---|---|---|
| Respuestas a las baterías (79 casos) y al set de control (24) | `tools/rag/evaluar_chat.py` | `evidencias/<carpeta>/casos/<ID>.json` y `resumen.md` |
| Calificación contra el «Debe» | A mano, en `calificacion_debe.json` | Columna «Debe» y conteo en `resumen.md` |
| *Hit rate*@k de la recuperación | `tools/rag/medir_recuperacion.py` | JSON con hit@1, @3, @5, @8 y MRR |
| Chunks que pasan del límite del modelo de *embeddings* | `tools/rag/contar_truncados.py` | JSON por instrumento |
| Textos de los instrumentos en el código | `tools/rag/buscar_textos_instrumentos.py` | Lista de coincidencias para revisar |
| Pruebas automáticas | `pytest`, servicio por servicio | Salida de cada servicio |

Las preguntas y su «Debe» están en `tools/rag/baterias_chat.json`. Cada caso tiene una clave de instrumento (`enc`,
`pru`, `ent`, `enc_control`, `ent_control`, `pru_control`) que se asocia a un `id_crudo` con `--ids`.

## 2. Antes de empezar

1. En `.env`, pon `RAG_CACHE_HORAS=0`. Si no, una pregunta repetida devuelve la respuesta guardada.
2. Levanta todo y reinicia el chat para que lea el `.env`:
   ```powershell
   docker compose up -d
   docker compose up -d visualization-service
   ```
3. Cierra los programas pesados. Con la GPU de 4 GiB, Ollama se queda sin memoria y cada respuesta tarda de 20 a
   60 s; la corrida completa tarda de 1 a 4 horas.
4. Verifica los `id_crudo`: en la evaluación del 8 nov fueron encuesta 127, prueba 130, entrevista 129 y, de control,
   61, 60 y 133.

## 3. Correr las baterías

```powershell
.venv\Scripts\python.exe tools\rag\evaluar_chat.py --ids enc=127,pru=130,ent=129 `
    --salida evidencias\chat_<fecha>_final --reiniciar-ollama-cada 15
.venv\Scripts\python.exe tools\rag\evaluar_chat.py --conjunto control --ids enc_control=61,ent_control=60,pru_control=133 `
    --salida evidencias\chat_<fecha>_final_control --reiniciar-ollama-cada 15
```

- Cada caso es una conversación nueva; sus turnos se hacen en orden, con el historial.
- `--reiniciar-ollama-cada 15` reinicia Ollama cada 15 casos y repite una vez el caso que salga «modelo no
  disponible». Cada reinicio queda en `reinicios.log`.
- El script vuelve a iniciar sesión si el token caduca (dura 60 minutos).
- Para repetir algunos casos en la misma carpeta: `--solo ENC-04,PRU-06`. El resumen conserva los demás casos.
- Para armar la línea base con consultas que ya se hicieron a mano en la interfaz: `--desde-log 2271-2371` (empareja
  cada turno con su consulta de `rag_log` por texto e instrumento).

## 4. Calificar contra el «Debe»

Abre cada `casos/<ID>.json`, compara la respuesta de cada turno con el campo `debe` y escribe
`calificacion_debe.json` en la misma carpeta:

```json
{
 "ENC-01": {"cumple": "cumple"},
 "ENC-07": {"cumple": "parcial", "nota": "Da las preguntas con más vacíos, pero no cuántas personas dejaron alguna."},
 "ENC-17": {"cumple": "no", "nota": "(2) cayó a «sin información»."}
}
```

`cumple` es `cumple`, `parcial` o `no`. Escribe siempre la nota cuando no sea `cumple`. Revisa también las cifras
contra los datos: que una respuesta esté bien redactada no significa que sea correcta.

Después rehaz el resumen sin volver a preguntar nada:

```powershell
.venv\Scripts\python.exe tools\rag\evaluar_chat.py --ids enc=127,pru=130,ent=129 --salida evidencias\chat_<fecha>_final `
    --solo-resumen --calificacion evidencias\chat_<fecha>_final\calificacion_debe.json
```

## 5. Cómo leer `resumen.md`

- **Cumplen el «Debe»:** la medida principal.
- **Planes válidos:** turnos cuyo plan no terminó en «aclaración».
- **Caídas a plantilla:** respuestas que no redactó el modelo. Incluye las fijas correctas (saludos, privacidad,
  «Indagata no califica», operaciones de entrevista); más plantillas no es peor.
- **Plan del modelo sin cambios:** en cuántos turnos el sistema no tuvo que corregir el plan del modelo.
- **K-Precision:** palabras de la respuesta presentes en el contexto. Mide fidelidad, no calidad.
- **Cifras con respaldo:** cifras de la respuesta que están en el contexto.
- **Tiempo:** mediana y percentil 90 por turno.

## 6. Recuperación y chunks

Corren dentro de visualization-service, que tiene el modelo de *embeddings* y la conexión a Chroma. Hazlo cuando no
esté corriendo una batería: cargan una segunda copia del modelo en memoria.

```powershell
docker cp tools/rag/recuperacion_oro.json indagata_visualization_service:/tmp/oro.json
docker cp tools/rag/medir_recuperacion.py indagata_visualization_service:/tmp/medir.py
docker cp tools/rag/contar_truncados.py indagata_visualization_service:/tmp/truncados.py
docker compose exec -T visualization-service python -c "exec(open('/tmp/medir.py', encoding='utf-8').read())" |
    Out-File -Encoding utf8 evidencias\<carpeta>\recuperacion.json
docker compose exec -T visualization-service python -c "exec(open('/tmp/truncados.py', encoding='utf-8').read())" |
    Out-File -Encoding utf8 evidencias\<carpeta>\truncados.json
```

Se copian los scripts al contenedor en lugar de pasarlos por la entrada estándar porque PowerShell 5.1 cambia su
codificación y se pierden los acentos; `Out-File -Encoding utf8` evita que la salida quede en UTF-16.

## 7. Generalización y pruebas automáticas

```powershell
.venv\Scripts\python.exe tools\rag\buscar_textos_instrumentos.py --ids 127,129,130 --desde <commit> --sin-pruebas
```

Revisa cada coincidencia: puede ser un comentario o una etiqueta genérica, pero no un texto en un prompt, un ejemplo o
una regla.

```powershell
cd services\visualization-service; ..\..\.venv\Scripts\python.exe -m pytest tests -q; cd ..\..
```

Repite el `pytest` en knowledge-service, storage-service, cleaning-service, metadata-service y analysis-service, uno
por uno (sus módulos se llaman igual y chocan si se corren juntos).

## 8. Al terminar

1. En `.env`, vuelve a `RAG_CACHE_HORAS=24`.
2. `docker compose up -d visualization-service`.
