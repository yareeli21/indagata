# Evaluación del chat: rep1

- Casos: 12 (12 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 12).
- Planes válidos (intención distinta de aclaración): 11 de 11 (100.0 %).
- Caídas a plantilla: 7 de 12 (58.3 %).
- Plan del modelo usado sin cambios: 5 de 11 (45.5 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.82, mínimo 0.59 (n = 5).
- Cifras con respaldo en el contexto: 131 de 131.
- Tiempo por turno: mediana 21 s, p90 28 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-01 | 1 | ¿Cuántos estudiantes trabajan en un área relacionada con su carrera? | conteo_porcentaje |  | 0.85 | 6/6 | 20.0 | — | — |
| ENC-02 | 1 | ¿Cuántos están considerando abandonar sus estudios? | conteo_porcentaje | frase_calculada | — | 6/6 | 17.3 | — | — |
| ENC-08 | 1 | Compara la opinión sobre laboratorios y equipos entre modalidad presen | comparar_grupos | calculo_literal | — | 42/42 | 27.9 | — | — |
| ENC-09 | 1 | ¿Los que trabajan en algo relacionado con su carrera aprobaron más cer | comparar_grupos | calculo_literal | — | 21/21 | 25.2 | — | — |
| PRU-01 | 1 | ¿Cuántos alumnos respondieron la prueba? | — |  | 0.59 | 2/2 | 25.1 | — | — |
| PRU-03 | 1 | ¿En qué reactivo hubo más respuestas en blanco? | ranking_preguntas |  | 0.82 | 10/10 | 14.5 | — | — |
| PRU-08 | 1 | Compara la sección de verdadero/falso con la de competencias básicas e | comparar_grupos |  | 0.92 | 8/8 | 9.4 | — | — |
| PRU-09 | 1 | De los que marcaron Verdadero en «el correo electrónico es siempre seg | resumen_pregunta | frase_calculada | — | 11/11 | 19.1 | — | — |
| ENT-04 | 1 | ¿En qué respuestas menciona a sus profesores o a su tutor? | datos_respondente | calculo_literal | — | 14/14 | 34.9 | — | — |
| ENT-06 | 1 | ¿Cuántas veces menciona el estrés o la ansiedad? | conteo_porcentaje | frase_calculada | — | 5/5 | 17.0 | — | — |
| ENT-08 | 1 | Compara cómo describe su estado de ánimo con cómo valora la atención q | comparar_grupos | calculo_literal | — | 2/2 | 22.7 | — | — |
| ENT-09 | 1 | ¿Notó diferencia en su desempeño académico antes y después de recibir  | hallazgo |  | 0.82 | 4/4 | 23.2 | — | — |
