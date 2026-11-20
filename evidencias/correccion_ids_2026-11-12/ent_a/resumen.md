# Evaluación del chat: ent_a

- Casos: 13 (15 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 13).
- Planes válidos (intención distinta de aclaración): 8 de 10 (80.0 %).
- Caídas a plantilla: 3 de 15 (20.0 %).
- Plan del modelo usado sin cambios: 3 de 10 (30.0 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.89, mínimo 0.74 (n = 7).
- Cifras con respaldo en el contexto: 32 de 48.
- Tiempo por turno: mediana 18 s, p90 37 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENT-01 | 1 | ¿Cuántas intervenciones tuvo la participante? | — |  | — | 0/3 | 0.1 | — | — |
| ENT-02 | 1 | ¿Cuántas palabras dijo la participante y cuántas el entrevistador? | — |  | — | 0/3 | 0.0 | — | — |
| ENT-03 | 1 | ¿Respondió todas las preguntas de la guía? ¿Cuáles no? | — |  | — | 0/2 | 0.1 | — | — |
| ENT-04 | 1 | ¿En qué respuestas menciona a sus profesores o a su tutor? | datos_respondente |  | 0.99 | 14/14 | 41.9 | — | — |
| ENT-05 | 1 | ¿Cuál fue su respuesta más larga y a qué pregunta corresponde? | — |  | — | 0/7 | 0.0 | — | — |
| ENT-06 | 1 | ¿Cuántas veces menciona el estrés o la ansiedad? | conteo_porcentaje | frase_calculada | — | 5/5 | 17.6 | — | — |
| ENT-07 | 1 | ¿Hubo preguntas de seguimiento que no estaban en la guía? | — |  | — | 0/0 | 0.0 | — | — |
| ENT-08 | 1 | Compara cómo describe su estado de ánimo con cómo valora la atención q | comparar_grupos |  | 0.74 | 2/2 | 19.1 | — | — |
| ENT-09 | 1 | ¿Notó diferencia en su desempeño académico antes y después de recibir  | hallazgo |  | 0.90 | 4/4 | 26.2 | — | — |
| ENT-10 | 1 | Compara el papel de sus profesores con el de los servicios de la unive | comparar_grupos |  | 0.84 | 3/3 | 17.6 | — | — |
| ENT-11 | 1 | ¿Qué pesó más para no buscar ayuda: el estigma, el tiempo de espera o  | hallazgo |  | 0.89 | 1/1 | 36.9 | — | — |
| ENT-12 | 1 | Compara sus respuestas con las de los demás participantes | aclaracion | aclaracion | — | 0/1 | 2.9 | — | — |
| ENT-13 | 1 | ¿Qué situaciones de la universidad le generan más estrés? | hallazgo |  | 0.89 | 1/1 | 23.4 | — |  |
| ENT-13 | 2 | ¿Y buscó ayuda por eso? | hallazgo |  | 0.84 | 2/2 | 18.6 | — |  |
| ENT-13 | 3 | ¿Cuánto tardaron en atenderla? | aclaracion | aclaracion | — | 0/0 | 6.4 | — | — |
