# Evaluación del chat: control_ent

- Casos: 8 (9 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 8).
- Planes válidos (intención distinta de aclaración): 5 de 6 (83.3 %).
- Caídas a plantilla: 2 de 9 (22.2 %).
- Plan del modelo usado sin cambios: 1 de 6 (16.7 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.99, mínimo 0.55 (n = 5).
- Cifras con respaldo en el contexto: 67 de 76.
- Tiempo por turno: mediana 16 s, p90 20 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CET-01 | 1 | ¿Cuántos participantes mencionan a su familia como apoyo? | conteo_porcentaje | frase_calculada | — | 10/10 | 16.5 | — | — |
| CET-02 | 1 | ¿Cuál es la respuesta más larga de E05 y a qué pregunta corresponde? | — |  | — | 0/4 | 0.0 | — | — |
| CET-03 | 1 | Compara lo que dicen sobre sus profesores con lo que dicen sobre los s | aclaracion |  | 0.55 | 2/2 | 18.3 | — | — |
| CET-04 | 1 | ¿Qué dijo E03 sobre abandonar la universidad? | datos_respondente |  | 0.99 | 15/15 | 22.7 | — |  |
| CET-04 | 2 | ¿Y qué estrategias usa para mantenerse? | datos_respondente |  | 0.99 | 14/14 | 20.0 | — | — |
| CET-05 | 1 | ¿Cuántas veces mencionan el dinero o la economía? | conteo_porcentaje |  | 0.90 | 12/12 | 15.9 | — | — |
| CET-06 | 1 | ¿Qué respondió el participante E99? | datos_respondente |  | 0.99 | 14/14 | 13.4 | — | — |
| CET-07 | 1 | ¿El participante E02 tiene ansiedad? | — |  | — | 0/4 | 0.0 | — | — |
| CET-08 | 1 | ¿Qué me recomiendas para no reprobar? | — | consejo | — | 0/1 | 0.1 | — | — |
