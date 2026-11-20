# Evaluación del chat: chat_2026-11-07_fase3_control

- Casos: 5 (7 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 5).
- Planes válidos (intención distinta de aclaración): 4 de 5 (80.0 %).
- Caídas a plantilla: 4 de 7 (57.1 %).
- K-Precision (sin plantillas): mediana 0.80, mínimo 0.79 (n = 3).
- Cifras con respaldo en el contexto: 37 de 42.
- Tiempo por turno: mediana 40 s, p90 41 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CEN-03 | 1 | ¿Cuántos tienen dificultades para equilibrar trabajo y estudios? | conteo_porcentaje |  | 0.79 | 3/3 | 30.5 | — |  |
| CEN-03 | 2 | ¿Y de ellos, cuántos no trabajan? | conteo_porcentaje |  | 0.80 | 4/4 | 40.2 | — |  |
| CEN-03 | 3 | Muéstrame 5 de ellos | filtrar_respondentes |  | 0.98 | 29/29 | 40.5 | — | — |
| CEN-06 | 1 | ¿Cuántos usan la meditación como estrategia para gestionar su tiempo? | conteo_porcentaje | calculo_literal | — | 1/1 | 41.0 | — | — |
| CEN-08 | 1 | Hola | — | cortesia | — | 0/1 | 0.0 | — | — |
| CET-06 | 1 | ¿Qué respondió el participante E99? | aclaracion | aclaracion | — | 0/3 | 28.2 | — | — |
| CET-08 | 1 | ¿Qué me recomiendas para no reprobar? | — | consejo | — | 0/1 | 0.0 | — | — |
