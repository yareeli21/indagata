# Evaluación del chat: chat_2026-11-07_fase2

- Casos: 6 (8 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 6).
- Planes válidos (intención distinta de aclaración): 7 de 8 (87.5 %).
- Caídas a plantilla: 0 de 8 (0.0 %).
- K-Precision (sin plantillas): mediana 0.79, mínimo 0.44 (n = 8).
- Cifras con respaldo en el contexto: 60 de 60.
- Tiempo por turno: mediana 34 s, p90 67 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-01 | 1 | ¿Cuántos estudiantes trabajan en un área relacionada con su carrera? | conteo_porcentaje |  | 1.00 | 4/4 | 44.1 | — | — |
| ENC-06 | 1 | ¿Cuál es la actividad de investigación de los profesores más conocida  | resumen_pregunta |  | 0.77 | 15/15 | 36.2 | — | — |
| PRU-02 | 1 | ¿Qué opción eligieron más en el reactivo sobre phishing? | resumen_pregunta |  | 0.81 | 8/8 | 32.5 | — | — |
| PRU-15 | 1 | ¿Qué respondió el alumno A001? | datos_respondente |  | 0.98 | 23/23 | 66.6 | — |  |
| PRU-15 | 2 | ¿Dejó alguno en blanco? | aclaracion |  | 0.44 | 2/2 | 32.6 | — |  |
| PRU-15 | 3 | ¿Su respuesta al reactivo de phishing es la más común? | semantica_abierta |  | 0.87 | 4/4 | 29.7 | — | — |
| ENT-11 | 1 | ¿Qué pesó más para no buscar ayuda: el estigma, el tiempo de espera o  | hallazgo |  | 0.48 | 4/4 | 76.6 | — | — |
| ENT-21 | 1 | ¿Qué indicaciones tenía el entrevistador? | metodologia |  | 0.75 | 0/0 | 11.5 | — | — |
