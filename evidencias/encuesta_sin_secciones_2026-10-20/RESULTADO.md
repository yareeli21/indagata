# Prueba: encuesta sin secciones (enc_10_turno, sintético) — 20–21 oct 2026

Mismas 60 respuestas en todas las variantes; solo cambia la forma (`generar_variantes.py`).
Procesadas con `tools/rag/procesar_instrumento.py` (7 pasos, decisiones sugeridas, 2 KPIs),
comparadas con `comparar.py base=59,A=64,B=65,C=66` → `comparacion.json`.

| | 59 base | A (64) | B (65) | C (66) |
|---|---|---|---|---|
| Original | con secciones | sin secciones | sin secciones | sin secciones |
| Encabezados CSV | `Evaluación_item1…` | `Evaluación_item1…` | texto de la pregunta | `P1…P8` |
| Preguntas en perfil/documento | 8 | 16 (8 sin columna + 8 «Otras preguntas del archivo») | 8 | 16 (igual que A) |
| Aviso en el perfil | — | `preguntas_sin_original` | — | `preguntas_sin_original` |
| Secciones del documento | EVALUACIÓN…, AMBIENTE… | INSTRUCCIONES, Otras… | INSTRUCCIONES | INSTRUCCIONES, Otras… |
| α por bloque (limpieza) | Evaluación 0.87, Ambiente 0.83, todas 0.78 | igual que base | solo todas 0.78 | bloque «P» 0.78 |
| Respuesta en chunks | etiqueta («De acuerdo») | «3 en escala 1–5» | etiqueta | «3 en escala 1–5» |
| Chunks (respondente) | 120 | 60 | 120 | 60 |

Chat (9 preguntas de referencia sin dependencia de KPIs):

| Pregunta | base | A | B | C |
|---|---|---|---|---|
| Q01 R017 retroalimentación | correcta | «no tiene respuesta registrada» | correcta | igual que A |
| Q02 R005 pregunta 8 | correcta | sin respuesta | correcta | sin respuesta |
| Q03 desacuerdo p1–p3 | R002 | «no existe» | R002 | «no existe» |
| Q04 neutral en las 8 | «no existe» (correcta) | correcta (por coincidencia: no hay datos) | correcta | correcta (coincidencia) |
| Q05 % vespertino p4 | 13.3 % (4 de 30) | «nadie respondió válidamente» | 13.3 % | igual que A |
| Q06 % desacuerdo p8 | 16.7 % (10 de 60) | «nadie respondió válidamente» | 16.7 % | igual que A |
| Q14 qué evalúa | correcta | parcial (solo ambiente) | parcial (mezcla KPI) | incorrecta (describe los KPIs) |
| Q17 transporte | sin información | sin información | sin información | sin información |
| Q18 nombre R017 | privacidad | privacidad | privacidad | privacidad |

Hallazgos:
1. Sin secciones y con encabezados codificados, las columnas no se emparejan con las preguntas
   del original (el emparejamiento de códigos usa sección + posición, `estructura._por_seccion_y_posicion`).
   El sistema no inventa cifras: responde «sin respuesta registrada», pero no responde lo que debe.
2. Con encabezados de texto completo (B) todo lo calculado coincide con la base; solo se pierde α por dimensión.
3. La línea «INSTRUCCIONES:» se toma como título de sección (línea corta en mayúsculas, `original._es_titulo_seccion`).
4. Q14 (semántica) se degrada en las tres variantes; en C la ficha/perfil describe los KPIs en lugar del contenido.

## Después de la corrección (21 oct 2026)

Cambios (rama `extensiones-semantica`, sin commit):
- `services/knowledge-service/services/estructura.py`: `_por_orden()` empareja por orden los encabezados
  codificados sueltos cuando TODAS las columnas sueltas son codificadas y hay tantas como preguntas libres
  del original; deja el aviso `emparejadas_por_posicion`. Si no cuadran, no adivina (como antes).
- `services/knowledge-service/services/original.py`: «INSTRUCCIONES» / «INDICACIONES» ya no se toman como sección.
- `tests/test_perfil.py`: 3 pruebas nuevas; knowledge-service 94 pruebas en verde (antes 91).

Reprocesadas como 67 (A), 68 (B), 69 (C); `comparar.py base=59,A=67,B=68,C=69` → `comparacion_despues.json`
(el primer intento quedó en `comparacion_antes.json`).

| | 59 base | A (67) | B (68) | C (69) |
|---|---|---|---|---|
| Preguntas en perfil/documento | 8 | 8 | 8 | 8 |
| Sección | 2 del original | General | General | General |
| Aviso | — | `emparejadas_por_posicion` | — | `emparejadas_por_posicion` |
| Chunks respondente | 120 | 120 | 120 | 120 |
| KPIs aceptados | Tamaño de clase; Pruebas estandarizadas | iguales | iguales | iguales (antes cambiaba uno) |
| Calculadas Q01–Q06 | 6/6 | 6/6 | 6/6 | 6/6 |
| Q14 «¿qué evalúa?» (semántica) | correcta | describe los KPIs | parcial (ambiente y experiencia) | describe los KPIs |
| Q17 / Q18 | correctas | correctas | correctas | correctas |

Pendiente: sin secciones, la ficha no nombra las dimensiones y el modelo de 3B responde Q14 con los KPIs.
El α por dimensión solo existe si los encabezados traen el prefijo del bloque (A); en B y C queda un α global.

## Corrección de «¿qué evalúa?» sin secciones (21–22 oct 2026)

Causas encontradas (ficha del instrumento, `tt_rag.documento_vectorizado`, sección `encabezado`):
1. Al chat solo llegaba UNA pieza de la ficha por instrumento: la más parecida a la pregunta. En C (74) fue
   la cola («… KPIs asociados: …»), sin objetivo ni contenido → respondía con los KPIs (`rag_log.contexto_usado`).
2. Sin secciones, la ficha no decía qué pregunta el instrumento (con secciones, sus nombres van en «Temas»).
3. El LLM de metadatos devolvía «dimensiones» como listas anidadas de columnas
   (`['Evaluación', ['Evaluación_item1', …]]`) que entraban como texto crudo a «Temas».
4. La población se tomaba de una pregunta («Los profesores están disponibles para resolver dudas»), también en 59.

Cambios (sin commit):
- visualization `services/rag_service.py`: `_ficha_completa()` — cuando entra una pieza de la ficha, se pasa la
  ficha completa (piezas en orden, sin título repetido ni solape). `_VERSION_RESPUESTAS` 3 → 4.
- storage `services/chunks_documento.py`: encuesta sin secciones con nombre → línea «Aspectos que pregunta: …»
  (textos de las preguntas, ≤ 600 caracteres) junto al objetivo; «No especificado» ya no entra en «Temas».
- metadata `services/llm_client.py`: listas del LLM solo con cadenas que no sean códigos de columna.
- metadata `services/analizador.py`: la población se busca fuera de las preguntas numeradas.
- Pruebas: metadata 27 (antes 25), storage 34 (antes 32), visualization 161 (antes 160), knowledge 94 (antes 91).

Instrumentos: 71 (base con secciones, código nuevo), 72 (A), 73 (B), 74 (C); 72–74 reingeridos con la ficha nueva.
`comparar.py base=71,A=72,B=73,C=74` → `comparacion_final.json`:

| | 71 base | A (72) | B (73) | C (74) |
|---|---|---|---|---|
| Calculadas Q01–Q06 | 6/6 | 6/6 | 6/6 | 6/6 |
| Q14 «¿qué evalúa?» | criterios de evaluación, aprendizaje y ambiente | experiencia educativa y ambiente + lista de aspectos | experiencia educativa y ambiente + aspectos | experiencia en el ambiente escolar + aspectos |
| Q17 sin información / Q18 privacidad | correctas | correctas | correctas | correctas |

Regresión (`regresion.py` → `regresion.json`): 19/19 preguntas de referencia de 59/55/60 con la decisión esperada.

## Instrumentos creados para esta prueba (todos sintéticos; se conservan)

| id | Qué es | Código con el que se procesó |
|---|---|---|
| 64 | A: sin secciones, `Evaluación_item1…` | original (antes de corregir) |
| 65 | B: sin secciones, texto de pregunta | original |
| 66 | C: sin secciones, `P1…P8` | original |
| 67 | A | corrección 1 (emparejamiento por orden) |
| 68 | B | corrección 1 |
| 69 | C | corrección 1 |
| 70 | C | corrección 2 (metadatos); los otros tres fallaron al subir (storage reiniciándose) |
| 71 | enc_10_turno original CON secciones | corrección 3 (base de comparación) |
| 72 | A | corrección 3 + ficha completa (reingerido) |
| 73 | B | corrección 3 + ficha completa (reingerido) |
| 74 | C | corrección 3 + ficha completa (reingerido) |

Los válidos para reportar son 71–74 (y 59 como referencia publicada antes de los cambios).
Limitación que queda: sin prefijo de bloque en los encabezados (B, C) solo hay α global (0.78); no hay forma
de deducir las dimensiones sin esa información.
