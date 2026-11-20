# Evaluación del chat: t3

- Casos: 8 (9 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 8).
- Planes válidos (intención distinta de aclaración): 5 de 7 (71.4 %).
- Caídas a plantilla: 7 de 9 (77.8 %).
- Plan del modelo usado sin cambios: 1 de 7 (14.3 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.91, mínimo 0.88 (n = 2).
- Cifras con respaldo en el contexto: 51 de 58.
- Tiempo por turno: mediana 15 s, p90 21 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CPR-01 | 1 | ¿Qué opción eligieron más en el reactivo del alpha de Cronbach? | resumen_pregunta |  | 0.88 | 9/9 | 15.6 | — | — |
| CPR-02 | 1 | ¿En qué reactivo están más repartidas las respuestas? | ranking_preguntas | calculo_literal | — | 16/16 | 21.3 | — | — |
| CPR-03 | 1 | Compara lo que eligieron en el reactivo del muestreo probabilístico en | comparar_grupos | calculo_literal | — | 18/18 | 25.9 | — | — |
| CPR-04 | 1 | ¿Cuántos marcaron Falso en el reactivo del acceso abierto? | conteo_porcentaje | frase_calculada | — | 4/4 | 16.8 | — |  |
| CPR-04 | 2 | De ellos, ¿qué eligieron en el reactivo del DOI? | aclaracion | aclaracion | — | 0/0 | 12.4 | — | — |
| CPR-05 | 1 | ¿En qué sección hay más respuestas en blanco? | comparar_grupos |  | 0.95 | 4/4 | 13.7 | — | — |
| CPR-06 | 1 | ¿Qué respondieron en el reactivo 20? | aclaracion | aclaracion | — | 0/3 | 11.0 | — | — |
| CPR-07 | 1 | ¿Cuál es la calificación promedio del grupo? | — | sin_calificar | — | 0/2 | 0.0 | — | — |
| CPR-08 | 1 | Hola | — | cortesia | — | 0/2 | 0.1 | — | — |
