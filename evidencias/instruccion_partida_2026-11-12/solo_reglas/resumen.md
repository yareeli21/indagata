# Evaluación del chat: solo_reglas

- Casos: 30 (32 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 30).
- Planes válidos (intención distinta de aclaración): 26 de 31 (83.9 %).
- Caídas a plantilla: 16 de 32 (50.0 %).
- Plan del modelo usado sin cambios: 15 de 31 (48.4 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.85, mínimo 0.36 (n = 16).
- Cifras con respaldo en el contexto: 214 de 214.
- Tiempo por turno: mediana 16 s, p90 33 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENU-01 | 1 | ¿Qué porcentaje de los estudiantes tiene beca? | conteo_porcentaje | frase_calculada | — | 4/4 | 23.1 | — | — |
| ENU-02 | 1 | ¿Cuántos llegan a la universidad en bicicleta? | conteo_porcentaje | frase_calculada | — | 4/4 | 18.7 | — | — |
| ENU-03 | 1 | ¿Los que trabajan más de 30 horas reprueban más que los que no trabaja | comparar_grupos | calculo_literal | — | 7/7 | 23.5 | — | — |
| ENU-04 | 1 | ¿Qué servicio de la institución fue el más usado este semestre? | hallazgo | calculo_literal | — | 11/11 | 35.5 | — | — |
| ENU-05 | 1 | ¿Qué tan satisfechos están con su carrera en general? | resumen_pregunta |  | 0.93 | 24/24 | 13.4 | — | — |
| ENU-06 | 1 | Compara la puntualidad en clases entre hombres y mujeres | comparar_grupos | calculo_literal | — | 30/30 | 42.7 | — | — |
| ENU-07 | 1 | ¿Hay estudiantes que no estudian nada fuera de clase? ¿Cuántos? | resumen_pregunta |  | 0.90 | 7/7 | 13.3 | — | — |
| ENU-08 | 1 | ¿Cuántos sienten que la institución no les avisa a tiempo de los trámi | resumen_pregunta |  | 0.93 | 10/10 | 13.4 | — | — |
| ENU-09 | 1 | ¿Cuántos estudiantes usan el servicio de nutrición? | hallazgo | sin_informacion | — | 0/0 | 13.7 | — | — |
| ENU-10 | 1 | ¿Qué respondió el estudiante R045 sobre su carga laboral? | datos_respondente |  | 0.80 | 6/6 | 22.1 | — | — |
| ENU-11 | 1 | ¿Cuántos son de primera generación? | conteo_porcentaje | frase_calculada | — | 4/4 | 10.2 | — |  |
| ENU-11 | 2 | ¿Y cuántos de ellos han reprobado alguna materia? | hallazgo |  | 0.80 | 10/10 | 20.8 | — | — |
| ENU-12 | 1 | ¿Qué te parece lo más preocupante de los servicios de apoyo? | hallazgo |  | 0.36 | 7/7 | 23.7 | — | — |
| PNU-01 | 1 | ¿Cuál fue la opción más elegida en el reactivo de la triangulación? | resumen_pregunta |  | 0.94 | 9/9 | 12.3 | — | — |
| PNU-02 | 1 | ¿Cuántos alumnos dijeron que la fabricación de datos es aceptable? | conteo_porcentaje | calculo_literal | — | 1/1 | 18.6 | — | — |
| PNU-03 | 1 | De los alumnos de primera generación, ¿qué base de datos eligieron más | comparar_grupos |  | 0.80 | 4/4 | 18.5 | — | — |
| PNU-04 | 1 | ¿Qué alumno tuvo el mejor desempeño? | aclaracion | aclaracion | — | 0/0 | 12.2 | — | — |
| PNU-05 | 1 | ¿Cambia lo que eligieron sobre la hipótesis según si estudian pregrado | comparar_grupos | calculo_literal | — | 15/15 | 36.7 | — | — |
| PNU-06 | 1 | Muéstrame lo que contestó A033 en los primeros tres reactivos | datos_respondente |  | 0.99 | 18/18 | 17.9 | — | — |
| PNU-07 | 1 | ¿Hubo reactivos que alguien dejó en blanco? | conteo_porcentaje |  | 1.00 | 2/2 | 11.3 | — | — |
| PNU-08 | 1 | ¿Qué significa que un reactivo tenga las respuestas muy repartidas? | metodologia | sin_informacion | — | 0/0 | 13.8 | — | — |
| PNU-09 | 1 | ¿Cuántos reactivos tiene la prueba y qué temas abarca? | — |  | 0.79 | 1/1 | 9.1 | — | — |
| ETU-01 | 1 | ¿Qué obstáculos tuvo para pedir ayuda? | aclaracion | aclaracion | — | 0/0 | 12.7 | — | — |
| ETU-02 | 1 | ¿Qué opina de sus profesores? | hallazgo |  | 0.76 | 5/5 | 32.7 | — | — |
| ETU-03 | 1 | ¿Cómo se sintió en la primera sesión? | datos_respondente |  | 0.99 | 15/15 | 24.1 | — | — |
| ETU-04 | 1 | ¿Qué opina de que solo den tres sesiones? | aclaracion |  | 0.42 | 1/1 | 10.1 | — | — |
| ETU-05 | 1 | ¿Qué consejo le daría a un compañero que la está pasando mal? | hallazgo |  | 0.62 | 4/4 | 21.6 | — | — |
| ETU-06 | 1 | ¿En qué semestre va la entrevistada y si trabaja? | datos_respondente |  | 0.99 | 15/15 | 25.9 | — | — |
| ETU-07 | 1 | ¿Le sirvió el apoyo psicológico? | aclaracion | aclaracion | — | 0/0 | 11.9 | — |  |
| ETU-07 | 2 | ¿En qué lo notó? | aclaracion | aclaracion | — | 0/0 | 6.0 | — | — |
| ETU-08 | 1 | ¿Debería la entrevistada tomar algún medicamento? | fuera_de_dominio | sin_informacion | — | 0/0 | 7.7 | — | — |
| ETU-09 | 1 | ¿Qué dijo sobre su familia? | semantica_abierta | sin_informacion | — | 0/0 | 8.1 | — | — |
