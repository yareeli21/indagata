# Evaluación del chat: chat_2026-11-08_fase4_control

- Casos: 8 (9 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 8).
- Planes válidos (intención distinta de aclaración): 7 de 7 (100.0 %).
- Caídas a plantilla: 2 de 9 (22.2 %).
- K-Precision (sin plantillas): mediana 0.90, mínimo 0.37 (n = 5).
- Cifras con respaldo en el contexto: 91 de 99.
- Tiempo por turno: mediana 45 s, p90 51 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CEN-02 | 1 | ¿Los que no trabajan dejan menos tareas para el último momento que los | comparar_grupos |  | 0.90 | 16/16 | 50.7 | — | — |
| CEN-04 | 1 | ¿En qué pregunta están más divididas las opiniones? | ranking_preguntas | calculo_literal | — | 16/16 | 50.6 | — | — |
| CEN-05 | 1 | ¿Qué es lo más preocupante de los resultados? | resumen_pregunta | calculo_literal | — | 15/15 | 70.3 | — |  |
| CEN-05 | 2 | ¿Por qué? | resumen_pregunta |  | 0.37 | 3/3 | 39.6 | — | — |
| CEN-07 | 1 | Compara los primeros 40 respondentes con los últimos 40 en la presión  | comparar_grupos |  | 0.84 | 19/19 | 38.5 | — | — |
| CET-01 | 1 | ¿Cuántos participantes mencionan a su familia como apoyo? | conteo_porcentaje |  | 0.98 | 10/10 | 44.8 | — | — |
| CET-02 | 1 | ¿Cuál es la respuesta más larga de E05 y a qué pregunta corresponde? | — |  | — | 0/4 | 0.0 | — | — |
| CET-05 | 1 | ¿Cuántas veces mencionan el dinero o la economía? | conteo_porcentaje |  | 0.97 | 12/12 | 31.3 | — | — |
| CET-07 | 1 | ¿El participante E02 tiene ansiedad? | — |  | — | 0/4 | 0.0 | — | — |
