# Evaluación del chat: chat_2026-11-07_fase1

- Casos: 7 (8 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 7).
- Planes válidos (intención distinta de aclaración): 6 de 8 (75.0 %).
- Caídas a plantilla: 1 de 8 (12.5 %).
- K-Precision (sin plantillas): mediana 0.83, mínimo 0.00 (n = 7).
- Cifras con respaldo en el contexto: 94 de 94.
- Tiempo por turno: mediana 37 s, p90 53 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-14 | 1 | ¿En qué pregunta están más divididas las opiniones? | ranking_preguntas |  | 0.94 | 12/12 | 53.4 | — |  |
| ENC-14 | 2 | Muéstrame los datos tal cual | resumen_pregunta | calculo_literal | — | 17/17 | 53.3 | — | — |
| ENC-19 | 1 | ¿Qué opciones tiene la pregunta sobre la carga académica? | resumen_pregunta |  | 0.83 | 8/8 | 38.4 | — | — |
| ENC-20 | 1 | ¿Cuáles preguntas usan escala del 1 al 5 y qué significan sus extremos | resumen_pregunta |  | 0.94 | 52/52 | 46.8 | — | — |
| ENT-03 | 1 | ¿Respondió todas las preguntas de la guía? ¿Cuáles no? | aclaracion |  | 0.71 | 3/3 | 36.2 | — | — |
| ENT-19 | 1 | ¿Cuántas preguntas tiene la guía y qué temas cubre? | semantica_abierta |  | 0.88 | 1/1 | 18.9 | — | — |
| ENT-20 | 1 | ¿Qué tipo de entrevista es y cuánto dura? | semantica_abierta |  | 0.00 | 0/0 | 13.3 | — | — |
| ENT-21 | 1 | ¿Qué indicaciones tenía el entrevistador? | aclaracion |  | 0.46 | 1/1 | 15.8 | — | — |
