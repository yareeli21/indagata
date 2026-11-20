# Evaluación del chat: rep1

- Casos: 12 (12 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 12).
- Planes válidos (intención distinta de aclaración): 12 de 12 (100.0 %).
- Caídas a plantilla: 6 de 12 (50.0 %).
- Plan del modelo usado sin cambios: 7 de 12 (58.3 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.86, mínimo 0.79 (n = 6).
- Cifras con respaldo en el contexto: 133 de 133.
- Tiempo por turno: mediana 21 s, p90 34 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-01 | 1 | ¿Cuántos estudiantes trabajan en un área relacionada con su carrera? | conteo_porcentaje |  | 0.86 | 7/7 | 19.1 | — | — |
| ENC-02 | 1 | ¿Cuántos están considerando abandonar sus estudios? | conteo_porcentaje | frase_calculada | — | 6/6 | 16.7 | — | — |
| ENC-08 | 1 | Compara la opinión sobre laboratorios y equipos entre modalidad presen | comparar_grupos |  | 0.82 | 42/42 | 33.9 | — | — |
| ENC-09 | 1 | ¿Los que trabajan en algo relacionado con su carrera aprobaron más cer | comparar_grupos | calculo_literal | — | 21/21 | 29.6 | — | — |
| PRU-01 | 1 | ¿Cuántos alumnos respondieron la prueba? | kpi | calculo_literal | — | 3/3 | 20.1 | — | — |
| PRU-03 | 1 | ¿En qué reactivo hubo más respuestas en blanco? | ranking_preguntas |  | 0.79 | 10/10 | 21.4 | — | — |
| PRU-08 | 1 | Compara la sección de verdadero/falso con la de competencias básicas e | comparar_grupos |  | 0.91 | 8/8 | 6.5 | — | — |
| PRU-09 | 1 | De los que marcaron Verdadero en «el correo electrónico es siempre seg | resumen_pregunta | frase_calculada | — | 11/11 | 19.3 | — | — |
| ENT-04 | 1 | ¿En qué respuestas menciona a sus profesores o a su tutor? | datos_respondente | calculo_literal | — | 14/14 | 74.7 | — | — |
| ENT-06 | 1 | ¿Cuántas veces menciona el estrés o la ansiedad? | conteo_porcentaje | frase_calculada | — | 5/5 | 17.5 | — | — |
| ENT-08 | 1 | Compara cómo describe su estado de ánimo con cómo valora la atención q | comparar_grupos |  | 0.86 | 2/2 | 31.5 | — | — |
| ENT-09 | 1 | ¿Notó diferencia en su desempeño académico antes y después de recibir  | hallazgo |  | 0.88 | 4/4 | 32.5 | — | — |
