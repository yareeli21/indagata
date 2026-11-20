# Evaluación del chat: chat_2026-11-08_fase3b_control

- Casos: 1 (3 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 1).
- Planes válidos (intención distinta de aclaración): 3 de 3 (100.0 %).
- Caídas a plantilla: 1 de 3 (33.3 %).
- K-Precision (sin plantillas): mediana 1.00, mínimo 1.00 (n = 2).
- Cifras con respaldo en el contexto: 39 de 39.
- Tiempo por turno: mediana 34 s, p90 263 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CEN-03 | 1 | ¿Cuántos tienen dificultades para equilibrar trabajo y estudios? | conteo_porcentaje |  | 1.00 | 4/4 | 18.9 | — |  |
| CEN-03 | 2 | ¿Y de ellos, cuántos no trabajan? | conteo_porcentaje |  | 1.00 | 4/4 | 34.4 | — |  |
| CEN-03 | 3 | Muéstrame 5 de ellos | filtrar_respondentes | calculo_literal | — | 31/31 | 262.9 | — | — |
