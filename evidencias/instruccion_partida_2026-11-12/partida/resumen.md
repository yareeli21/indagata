# Evaluación del chat: partida

- Casos: 30 (32 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 30).
- Planes válidos (intención distinta de aclaración): 23 de 31 (74.2 %).
- Caídas a plantilla: 18 de 32 (56.2 %).
- Plan del modelo usado sin cambios: 10 de 31 (32.3 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.88, mínimo 0.48 (n = 14).
- Cifras con respaldo en el contexto: 214 de 218.
- Tiempo por turno: mediana 18 s, p90 28 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENU-01 | 1 | ¿Qué porcentaje de los estudiantes tiene beca? | conteo_porcentaje | frase_calculada | — | 4/4 | 22.5 | — | — |
| ENU-02 | 1 | ¿Cuántos llegan a la universidad en bicicleta? | conteo_porcentaje | frase_calculada | — | 4/4 | 19.1 | — | — |
| ENU-03 | 1 | ¿Los que trabajan más de 30 horas reprueban más que los que no trabaja | comparar_grupos |  | 0.76 | 7/7 | 27.5 | — | — |
| ENU-04 | 1 | ¿Qué servicio de la institución fue el más usado este semestre? | hallazgo | calculo_literal | — | 11/11 | 35.4 | — | — |
| ENU-05 | 1 | ¿Qué tan satisfechos están con su carrera en general? | resumen_pregunta |  | 0.93 | 24/24 | 12.0 | — | — |
| ENU-06 | 1 | Compara la puntualidad en clases entre hombres y mujeres | comparar_grupos |  | 0.82 | 30/30 | 18.6 | — | — |
| ENU-07 | 1 | ¿Hay estudiantes que no estudian nada fuera de clase? ¿Cuántos? | resumen_pregunta |  | 0.90 | 7/7 | 12.1 | — | — |
| ENU-08 | 1 | ¿Cuántos sienten que la institución no les avisa a tiempo de los trámi | resumen_pregunta |  | 0.93 | 10/10 | 12.0 | — | — |
| ENU-09 | 1 | ¿Cuántos estudiantes usan el servicio de nutrición? | hallazgo | sin_informacion | — | 0/0 | 12.1 | — | — |
| ENU-10 | 1 | ¿Qué respondió el estudiante R045 sobre su carga laboral? | datos_respondente |  | 0.96 | 29/29 | 22.8 | — | — |
| ENU-11 | 1 | ¿Cuántos son de primera generación? | hallazgo |  | 0.48 | 2/3 | 12.4 | — |  |
| ENU-11 | 2 | ¿Y cuántos de ellos han reprobado alguna materia? | hallazgo | calculo_literal | — | 11/11 | 24.0 | — | — |
| ENU-12 | 1 | ¿Qué te parece lo más preocupante de los servicios de apoyo? | hallazgo | calculo_literal | — | 11/11 | 36.9 | — | — |
| PNU-01 | 1 | ¿Cuál fue la opción más elegida en el reactivo de la triangulación? | comparar_grupos |  | 0.87 | 5/6 | 16.8 | — | — |
| PNU-02 | 1 | ¿Cuántos alumnos dijeron que la fabricación de datos es aceptable? | conteo_porcentaje | frase_calculada | — | 4/4 | 21.2 | — | — |
| PNU-03 | 1 | De los alumnos de primera generación, ¿qué base de datos eligieron más | aclaracion |  | 0.81 | 2/2 | 23.3 | — | — |
| PNU-04 | 1 | ¿Qué alumno tuvo el mejor desempeño? | aclaracion | aclaracion | — | 0/0 | 13.6 | — | — |
| PNU-05 | 1 | ¿Cambia lo que eligieron sobre la hipótesis según si estudian pregrado | comparar_grupos |  | 0.89 | 24/24 | 21.7 | — | — |
| PNU-06 | 1 | Muéstrame lo que contestó A033 en los primeros tres reactivos | datos_respondente |  | 0.97 | 18/18 | 27.0 | — | — |
| PNU-07 | 1 | ¿Hubo reactivos que alguien dejó en blanco? | conteo_porcentaje |  | 1.00 | 2/2 | 14.4 | — | — |
| PNU-08 | 1 | ¿Qué significa que un reactivo tenga las respuestas muy repartidas? | aclaracion | aclaracion | — | 0/0 | 11.1 | — | — |
| PNU-09 | 1 | ¿Cuántos reactivos tiene la prueba y qué temas abarca? | — |  | 0.88 | 1/1 | 10.8 | — | — |
| ETU-01 | 1 | ¿Qué obstáculos tuvo para pedir ayuda? | hallazgo | calculo_literal | — | 4/4 | 32.5 | — | — |
| ETU-02 | 1 | ¿Qué opina de sus profesores? | conteo_porcentaje | calculo_literal | — | 1/1 | 23.5 | — | — |
| ETU-03 | 1 | ¿Cómo se sintió en la primera sesión? | aclaracion | aclaracion_ajena | — | 0/1 | 10.3 | — | — |
| ETU-04 | 1 | ¿Qué opina de que solo den tres sesiones? | comparar_grupos | calculo_literal | — | 2/2 | 20.9 | — | — |
| ETU-05 | 1 | ¿Qué consejo le daría a un compañero que la está pasando mal? | hallazgo |  | 0.51 | 1/1 | 23.3 | — | — |
| ETU-06 | 1 | ¿En qué semestre va la entrevistada y si trabaja? | aclaracion | aclaracion | — | 0/0 | 8.3 | — | — |
| ETU-07 | 1 | ¿Le sirvió el apoyo psicológico? | aclaracion | aclaracion | — | 0/0 | 9.8 | — |  |
| ETU-07 | 2 | ¿En qué lo notó? | aclaracion | aclaracion | — | 0/0 | 5.8 | — | — |
| ETU-08 | 1 | ¿Debería la entrevistada tomar algún medicamento? | hallazgo | sin_informacion | — | 0/0 | 7.5 | — | — |
| ETU-09 | 1 | ¿Qué dijo sobre su familia? | aclaracion | aclaracion_ajena | — | 0/1 | 7.6 | — | — |
