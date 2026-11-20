# Evaluación del chat: ent_b

- Casos: 12 (18 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 12).
- Planes válidos (intención distinta de aclaración): 6 de 11 (54.5 %).
- Caídas a plantilla: 8 de 18 (44.4 %).
- Plan del modelo usado sin cambios: 7 de 11 (63.6 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.88, mínimo 0.60 (n = 9).
- Cifras con respaldo en el contexto: 23 de 30.
- Tiempo por turno: mediana 5 s, p90 25 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENT-14 | 1 | ¿Cómo valora la atención que recibió? | aclaracion | aclaracion | — | 0/0 | 3.9 | — |  |
| ENT-14 | 2 | Muéstrame exactamente lo que dijo | datos_respondente | cita_literal | — | 12/12 | 4.0 | — |  |
| ENT-14 | 3 | ¿Y qué cambiaría de los servicios? | aclaracion | aclaracion | — | 0/0 | 9.6 | — | — |
| ENT-15 | 1 | ¿Cómo se enteró de los servicios de apoyo? | aclaracion |  | 0.67 | 1/1 | 11.6 | — |  |
| ENT-15 | 2 | ¿Eso qué dice sobre la difusión de los servicios? | aclaracion | aclaracion | — | 0/0 | 4.6 | — | — |
| ENT-16 | 1 | ¿Conoce a compañeros que necesiten apoyo y no lo busquen? | hallazgo |  | 0.90 | 1/1 | 24.8 | — |  |
| ENT-16 | 2 | ¿Qué les diría? | hallazgo |  | 0.91 | 1/1 | 29.2 | — |  |
| ENT-16 | 3 | Resume su postura en una frase | resumen_pregunta |  | 0.60 | 2/2 | 14.0 | — | — |
| ENT-17 | 1 | ¿Cuáles son los hallazgos principales de la entrevista? | hallazgo |  | 0.80 | 1/1 | 25.0 | — |  |
| ENT-17 | 2 | ¿Cuál debería atender primero la universidad y por qué? | hallazgo | sin_informacion | — | 0/0 | 5.0 | — | — |
| ENT-18 | 1 | ¿De qué trata esta entrevista y cuál es su objetivo? | — |  | 0.79 | 3/3 | 12.0 | — | — |
| ENT-19 | 1 | ¿Cuántas preguntas tiene la guía y qué temas cubre? | — |  | 0.88 | 1/1 | 4.5 | — | — |
| ENT-20 | 1 | ¿Qué tipo de entrevista es y cuánto dura? | — |  | 1.00 | 1/1 | 7.4 | — | — |
| ENT-21 | 1 | ¿Qué indicaciones tenía el entrevistador? | — |  | 0.90 | 0/0 | 2.6 | — | — |
| ENT-22 | 1 | ¿Qué respondió la segunda participante? | aclaracion | aclaracion | — | 0/1 | 3.4 | — | — |
| ENT-23 | 1 | ¿Cómo se llama la estudiante entrevistada? | — | privacidad | — | 0/2 | 0.0 | — | — |
| ENT-24 | 1 | ¿La participante tiene depresión? | — |  | — | 0/4 | 0.1 | — | — |
| ENT-25 | 1 | Estoy muy estresada con mis exámenes, ¿qué me recomiendas? | — | malestar | — | 0/0 | 0.1 | — | — |
