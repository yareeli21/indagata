# Evaluación del chat: chat_2026-11-08_fase3b

- Casos: 1 (3 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 1).
- Planes válidos (intención distinta de aclaración): 3 de 3 (100.0 %).
- Caídas a plantilla: 1 de 3 (33.3 %).
- K-Precision (sin plantillas): mediana 0.86, mínimo 0.86 (n = 2).
- Cifras con respaldo en el contexto: 40 de 40.
- Tiempo por turno: mediana 29 s, p90 36 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| PRU-14 | 1 | ¿Cuántos marcaron Verdadero en «la nube elimina por completo el riesgo | conteo_porcentaje |  | 0.86 | 4/4 | 28.7 | — |  |
| PRU-14 | 2 | De ellos, ¿qué respondieron sobre Wi-Fi público? | conteo_porcentaje |  | 0.86 | 4/4 | 28.8 | — |  |
| PRU-14 | 3 | Muéstrame 5 | filtrar_respondentes | calculo_literal | — | 32/32 | 36.0 | — | — |
