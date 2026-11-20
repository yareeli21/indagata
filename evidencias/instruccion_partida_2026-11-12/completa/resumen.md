# Evaluación del chat: completa

- Casos: 30 (32 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 30).
- Planes válidos (intención distinta de aclaración): 27 de 31 (87.1 %).
- Caídas a plantilla: 13 de 32 (40.6 %).
- Plan del modelo usado sin cambios: 18 de 31 (58.1 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.90, mínimo 0.42 (n = 19).
- Cifras con respaldo en el contexto: 234 de 234.
- Tiempo por turno: mediana 17 s, p90 36 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENU-01 | 1 | ¿Qué porcentaje de los estudiantes tiene beca? | conteo_porcentaje | frase_calculada | — | 4/4 | 15.9 | — | — |
| ENU-02 | 1 | ¿Cuántos llegan a la universidad en bicicleta? | conteo_porcentaje | frase_calculada | — | 4/4 | 15.7 | — | — |
| ENU-03 | 1 | ¿Los que trabajan más de 30 horas reprueban más que los que no trabaja | comparar_grupos |  | 0.65 | 7/7 | 17.6 | — | — |
| ENU-04 | 1 | ¿Qué servicio de la institución fue el más usado este semestre? | hallazgo | calculo_literal | — | 11/11 | 48.3 | — | — |
| ENU-05 | 1 | ¿Qué tan satisfechos están con su carrera en general? | resumen_pregunta |  | 0.93 | 24/24 | 12.4 | — | — |
| ENU-06 | 1 | Compara la puntualidad en clases entre hombres y mujeres | comparar_grupos |  | 0.74 | 30/30 | 18.9 | — | — |
| ENU-07 | 1 | ¿Hay estudiantes que no estudian nada fuera de clase? ¿Cuántos? | resumen_pregunta |  | 0.90 | 7/7 | 12.3 | — | — |
| ENU-08 | 1 | ¿Cuántos sienten que la institución no les avisa a tiempo de los trámi | conteo_porcentaje |  | 1.00 | 3/3 | 11.9 | — | — |
| ENU-09 | 1 | ¿Cuántos estudiantes usan el servicio de nutrición? | hallazgo | sin_informacion | — | 0/0 | 12.3 | — | — |
| ENU-10 | 1 | ¿Qué respondió el estudiante R045 sobre su carga laboral? | datos_respondente |  | 0.83 | 6/6 | 19.3 | — | — |
| ENU-11 | 1 | ¿Cuántos son de primera generación? | conteo_porcentaje | frase_calculada | — | 4/4 | 8.6 | — |  |
| ENU-11 | 2 | ¿Y cuántos de ellos han reprobado alguna materia? | hallazgo |  | 0.46 | 10/10 | 17.5 | — | — |
| ENU-12 | 1 | ¿Qué te parece lo más preocupante de los servicios de apoyo? | hallazgo |  | 0.42 | 9/9 | 21.0 | — | — |
| PNU-01 | 1 | ¿Cuál fue la opción más elegida en el reactivo de la triangulación? | resumen_pregunta |  | 0.94 | 9/9 | 11.0 | — | — |
| PNU-02 | 1 | ¿Cuántos alumnos dijeron que la fabricación de datos es aceptable? | conteo_porcentaje | calculo_literal | — | 1/1 | 16.8 | — | — |
| PNU-03 | 1 | De los alumnos de primera generación, ¿qué base de datos eligieron más | comparar_grupos |  | 0.61 | 4/4 | 23.4 | — | — |
| PNU-04 | 1 | ¿Qué alumno tuvo el mejor desempeño? | aclaracion | aclaracion | — | 0/0 | 11.2 | — | — |
| PNU-05 | 1 | ¿Cambia lo que eligieron sobre la hipótesis según si estudian pregrado | comparar_grupos | calculo_literal | — | 15/15 | 28.2 | — | — |
| PNU-06 | 1 | Muéstrame lo que contestó A033 en los primeros tres reactivos | datos_respondente |  | 0.97 | 18/18 | 26.0 | — | — |
| PNU-07 | 1 | ¿Hubo reactivos que alguien dejó en blanco? | conteo_porcentaje |  | 1.00 | 2/2 | 10.8 | — | — |
| PNU-08 | 1 | ¿Qué significa que un reactivo tenga las respuestas muy repartidas? | metodologia | sin_informacion | — | 0/0 | 13.3 | — | — |
| PNU-09 | 1 | ¿Cuántos reactivos tiene la prueba y qué temas abarca? | — |  | 0.91 | 6/6 | 9.6 | — | — |
| ETU-01 | 1 | ¿Qué obstáculos tuvo para pedir ayuda? | aclaracion | aclaracion | — | 0/0 | 11.2 | — | — |
| ETU-02 | 1 | ¿Qué opina de sus profesores? | hallazgo |  | 0.77 | 5/5 | 24.8 | — | — |
| ETU-03 | 1 | ¿Cómo se sintió en la primera sesión? | datos_respondente |  | 0.98 | 15/15 | 22.7 | — | — |
| ETU-04 | 1 | ¿Qué opina de que solo den tres sesiones? | aclaracion |  | 0.45 | 1/1 | 7.8 | — | — |
| ETU-05 | 1 | ¿Qué consejo le daría a un compañero que la está pasando mal? | hallazgo |  | 0.66 | 1/1 | 43.6 | — | — |
| ETU-06 | 1 | ¿En qué semestre va la entrevistada y si trabaja? | datos_respondente |  | 1.00 | 15/15 | 20.5 | — | — |
| ETU-07 | 1 | ¿Le sirvió el apoyo psicológico? | hallazgo | calculo_literal | — | 4/4 | 47.6 | — |  |
| ETU-07 | 2 | ¿En qué lo notó? | hallazgo | calculo_literal | — | 4/4 | 36.5 | — | — |
| ETU-08 | 1 | ¿Debería la entrevistada tomar algún medicamento? | aclaracion | aclaracion | — | 0/0 | 8.3 | — | — |
| ETU-09 | 1 | ¿Qué dijo sobre su familia? | datos_respondente |  | 1.00 | 15/15 | 30.9 | — | — |
