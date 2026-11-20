# Evaluación del chat: rep2

- Casos: 12 (12 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 12).
- Planes válidos (intención distinta de aclaración): 11 de 11 (100.0 %).
- Caídas a plantilla: 6 de 12 (50.0 %).
- Plan del modelo usado sin cambios: 6 de 11 (54.5 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.83, mínimo 0.59 (n = 6).
- Cifras con respaldo en el contexto: 132 de 132.
- Tiempo por turno: mediana 20 s, p90 30 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-01 | 1 | ¿Cuántos estudiantes trabajan en un área relacionada con su carrera? | conteo_porcentaje |  | 0.86 | 7/7 | 18.5 | — | — |
| ENC-02 | 1 | ¿Cuántos están considerando abandonar sus estudios? | conteo_porcentaje | frase_calculada | — | 6/6 | 17.5 | — | — |
| ENC-08 | 1 | Compara la opinión sobre laboratorios y equipos entre modalidad presen | comparar_grupos |  | 0.84 | 42/42 | 30.2 | — | — |
| ENC-09 | 1 | ¿Los que trabajan en algo relacionado con su carrera aprobaron más cer | comparar_grupos | calculo_literal | — | 21/21 | 24.6 | — | — |
| PRU-01 | 1 | ¿Cuántos alumnos respondieron la prueba? | — |  | 0.59 | 2/2 | 21.1 | — | — |
| PRU-03 | 1 | ¿En qué reactivo hubo más respuestas en blanco? | ranking_preguntas |  | 0.82 | 10/10 | 14.6 | — | — |
| PRU-08 | 1 | Compara la sección de verdadero/falso con la de competencias básicas e | comparar_grupos |  | 0.92 | 8/8 | 9.5 | — | — |
| PRU-09 | 1 | De los que marcaron Verdadero en «el correo electrónico es siempre seg | resumen_pregunta | frase_calculada | — | 11/11 | 18.9 | — | — |
| ENT-04 | 1 | ¿En qué respuestas menciona a sus profesores o a su tutor? | datos_respondente | calculo_literal | — | 14/14 | 35.2 | — | — |
| ENT-06 | 1 | ¿Cuántas veces menciona el estrés o la ansiedad? | conteo_porcentaje | frase_calculada | — | 5/5 | 17.1 | — | — |
| ENT-08 | 1 | Compara cómo describe su estado de ánimo con cómo valora la atención q | comparar_grupos | calculo_literal | — | 2/2 | 22.7 | — | — |
| ENT-09 | 1 | ¿Notó diferencia en su desempeño académico antes y después de recibir  | hallazgo |  | 0.82 | 4/4 | 23.1 | — | — |
