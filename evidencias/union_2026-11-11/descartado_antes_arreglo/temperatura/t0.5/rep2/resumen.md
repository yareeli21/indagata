# Evaluación del chat: rep2

- Casos: 12 (12 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 12).
- Planes válidos (intención distinta de aclaración): 11 de 11 (100.0 %).
- Caídas a plantilla: 8 de 12 (66.7 %).
- Plan del modelo usado sin cambios: 6 de 11 (54.5 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.78, mínimo 0.68 (n = 4).
- Cifras con respaldo en el contexto: 129 de 129.
- Tiempo por turno: mediana 21 s, p90 33 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-01 | 1 | ¿Cuántos estudiantes trabajan en un área relacionada con su carrera? | conteo_porcentaje | frase_calculada | — | 6/6 | 18.6 | — | — |
| ENC-02 | 1 | ¿Cuántos están considerando abandonar sus estudios? | conteo_porcentaje | frase_calculada | — | 6/6 | 18.0 | — | — |
| ENC-08 | 1 | Compara la opinión sobre laboratorios y equipos entre modalidad presen | comparar_grupos | calculo_literal | — | 42/42 | 32.6 | — | — |
| ENC-09 | 1 | ¿Los que trabajan en algo relacionado con su carrera aprobaron más cer | comparar_grupos | calculo_literal | — | 21/21 | 24.5 | — | — |
| PRU-01 | 1 | ¿Cuántos alumnos respondieron la prueba? | — |  | 0.68 | 1/1 | 22.0 | — | — |
| PRU-03 | 1 | ¿En qué reactivo hubo más respuestas en blanco? | ranking_preguntas |  | 0.82 | 10/10 | 19.5 | — | — |
| PRU-08 | 1 | Compara la sección de verdadero/falso con la de competencias básicas e | comparar_grupos |  | 0.91 | 8/8 | 11.2 | — | — |
| PRU-09 | 1 | De los que marcaron Verdadero en «el correo electrónico es siempre seg | resumen_pregunta | frase_calculada | — | 11/11 | 19.5 | — | — |
| ENT-04 | 1 | ¿En qué respuestas menciona a sus profesores o a su tutor? | datos_respondente | calculo_literal | — | 14/14 | 75.2 | — | — |
| ENT-06 | 1 | ¿Cuántas veces menciona el estrés o la ansiedad? | conteo_porcentaje | frase_calculada | — | 5/5 | 17.8 | — | — |
| ENT-08 | 1 | Compara cómo describe su estado de ánimo con cómo valora la atención q | comparar_grupos | calculo_literal | — | 2/2 | 28.7 | — | — |
| ENT-09 | 1 | ¿Notó diferencia en su desempeño académico antes y después de recibir  | hallazgo |  | 0.73 | 3/3 | 23.2 | — | — |
