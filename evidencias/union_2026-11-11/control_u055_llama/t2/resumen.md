# Evaluación del chat: t2

- Casos: 8 (9 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 8).
- Planes válidos (intención distinta de aclaración): 5 de 6 (83.3 %).
- Caídas a plantilla: 6 de 9 (66.7 %).
- Plan del modelo usado sin cambios: 1 de 6 (16.7 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.54, mínimo 0.54 (n = 1).
- Cifras con respaldo en el contexto: 62 de 71.
- Tiempo por turno: mediana 21 s, p90 27 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CET-01 | 1 | ¿Cuántos participantes mencionan a su familia como apoyo? | conteo_porcentaje | frase_calculada | — | 10/10 | 19.7 | — | — |
| CET-02 | 1 | ¿Cuál es la respuesta más larga de E05 y a qué pregunta corresponde? | — |  | — | 0/4 | 0.0 | — | — |
| CET-03 | 1 | Compara lo que dicen sobre sus profesores con lo que dicen sobre los s | aclaracion |  | 0.54 | 1/1 | 21.0 | — | — |
| CET-04 | 1 | ¿Qué dijo E03 sobre abandonar la universidad? | datos_respondente | calculo_literal | — | 15/15 | 27.1 | — |  |
| CET-04 | 2 | ¿Y qué estrategias usa para mantenerse? | hallazgo | calculo_literal | — | 10/10 | 34.3 | — | — |
| CET-05 | 1 | ¿Cuántas veces mencionan el dinero o la economía? | conteo_porcentaje | frase_calculada | — | 11/11 | 20.8 | — | — |
| CET-06 | 1 | ¿Qué respondió el participante E99? | datos_respondente | calculo_literal | — | 15/15 | 21.3 | — | — |
| CET-07 | 1 | ¿El participante E02 tiene ansiedad? | — |  | — | 0/4 | 0.0 | — | — |
| CET-08 | 1 | ¿Qué me recomiendas para no reprobar? | — | consejo | — | 0/1 | 0.1 | — | — |
