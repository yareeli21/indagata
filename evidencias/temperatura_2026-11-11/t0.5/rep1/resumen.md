# Evaluación del chat: rep1

- Casos: 12 (12 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 12).
- Planes válidos (intención distinta de aclaración): 12 de 12 (100.0 %).
- Caídas a plantilla: 9 de 12 (75.0 %).
- Plan del modelo usado sin cambios: 7 de 12 (58.3 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.91, mínimo 0.81 (n = 3).
- Cifras con respaldo en el contexto: 131 de 131.
- Tiempo por turno: mediana 22 s, p90 35 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-01 | 1 | ¿Cuántos estudiantes trabajan en un área relacionada con su carrera? | conteo_porcentaje | frase_calculada | — | 6/6 | 20.6 | — | — |
| ENC-02 | 1 | ¿Cuántos están considerando abandonar sus estudios? | conteo_porcentaje | frase_calculada | — | 6/6 | 16.9 | — | — |
| ENC-08 | 1 | Compara la opinión sobre laboratorios y equipos entre modalidad presen | comparar_grupos | calculo_literal | — | 42/42 | 24.2 | — | — |
| ENC-09 | 1 | ¿Los que trabajan en algo relacionado con su carrera aprobaron más cer | comparar_grupos |  | 0.81 | 21/21 | 23.9 | — | — |
| PRU-01 | 1 | ¿Cuántos alumnos respondieron la prueba? | kpi | calculo_literal | — | 3/3 | 17.7 | — | — |
| PRU-03 | 1 | ¿En qué reactivo hubo más respuestas en blanco? | ranking_preguntas | calculo_literal | — | 10/10 | 20.1 | — | — |
| PRU-08 | 1 | Compara la sección de verdadero/falso con la de competencias básicas e | comparar_grupos | calculo_literal | — | 9/9 | 11.1 | — | — |
| PRU-09 | 1 | De los que marcaron Verdadero en «el correo electrónico es siempre seg | resumen_pregunta | frase_calculada | — | 11/11 | 20.0 | — | — |
| ENT-04 | 1 | ¿En qué respuestas menciona a sus profesores o a su tutor? | datos_respondente | calculo_literal | — | 14/14 | 91.7 | — | — |
| ENT-06 | 1 | ¿Cuántas veces menciona el estrés o la ansiedad? | conteo_porcentaje |  | 0.91 | 5/5 | 24.2 | — | — |
| ENT-08 | 1 | Compara cómo describe su estado de ánimo con cómo valora la atención q | comparar_grupos | calculo_literal | — | 2/2 | 30.0 | — | — |
| ENT-09 | 1 | ¿Notó diferencia en su desempeño académico antes y después de recibir  | hallazgo |  | 0.98 | 2/2 | 34.7 | — | — |
