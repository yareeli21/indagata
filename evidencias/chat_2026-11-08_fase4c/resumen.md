# Evaluación del chat: chat_2026-11-08_fase4c

- Casos: 4 (6 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 4).
- Planes válidos (intención distinta de aclaración): 5 de 5 (100.0 %).
- Caídas a plantilla: 1 de 6 (16.7 %).
- K-Precision (sin plantillas): mediana 0.92, mínimo 0.89 (n = 5).
- Cifras con respaldo en el contexto: 86 de 86.
- Tiempo por turno: mediana 27 s, p90 30 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-12 | 1 | ¿Quienes usan una plataforma virtual a diario califican mejor la bibli | comparar_grupos |  | 0.89 | 30/30 | 42.2 | — | — |
| PRU-09 | 1 | De los que marcaron Verdadero en «el correo electrónico es siempre seg | resumen_pregunta |  | 0.89 | 11/11 | 26.2 | — | — |
| PRU-14 | 1 | ¿Cuántos marcaron Verdadero en «la nube elimina por completo el riesgo | conteo_porcentaje | calculo_literal | — | 4/4 | 26.1 | — |  |
| PRU-14 | 2 | De ellos, ¿qué respondieron sobre Wi-Fi público? | conteo_porcentaje |  | 0.92 | 8/8 | 27.6 | — |  |
| PRU-14 | 3 | Muéstrame 5 | filtrar_respondentes |  | 0.99 | 32/32 | 30.1 | — | — |
| ENT-20 | 1 | ¿Qué tipo de entrevista es y cuánto dura? | — |  | 1.00 | 1/1 | 16.7 | — | — |
