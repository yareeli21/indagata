# Evaluación del chat: control_u055_llama

- Casos: 24 (29 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 24).
- Planes válidos (intención distinta de aclaración): 19 de 22 (86.4 %).
- Caídas a plantilla: 16 de 29 (55.2 %).
- Plan del modelo usado sin cambios: 3 de 22 (13.6 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.88, mínimo 0.21 (n = 11).
- Cifras con respaldo en el contexto: 247 de 264.
- Tiempo por turno: mediana 17 s, p90 26 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CEN-01 | 1 | ¿Cuántos estudiantes trabajan más de 30 horas? | conteo_porcentaje | frase_calculada | — | 5/5 | 17.6 | — | — |
| CEN-02 | 1 | ¿Los que no trabajan dejan menos tareas para el último momento que los | comparar_grupos | calculo_literal | — | 37/37 | 16.8 | — | — |
| CEN-03 | 1 | ¿Cuántos tienen dificultades para equilibrar trabajo y estudios? | conteo_porcentaje |  | 0.71 | 4/4 | 17.4 | — |  |
| CEN-03 | 2 | ¿Y de ellos, cuántos no trabajan? | conteo_porcentaje | frase_calculada | — | 6/6 | 22.2 | — |  |
| CEN-03 | 3 | Muéstrame 5 de ellos | filtrar_respondentes | calculo_literal | — | 31/31 | 23.4 | — | — |
| CEN-04 | 1 | ¿En qué pregunta están más divididas las opiniones? | ranking_preguntas | calculo_literal | — | 16/16 | 14.4 | — | — |
| CEN-05 | 1 | ¿Qué es lo más preocupante de los resultados? | hallazgo |  | 0.45 | 8/8 | 18.3 | — |  |
| CEN-05 | 2 | ¿Por qué? | — |  | 0.21 | 1/1 | 11.4 | — | — |
| CEN-06 | 1 | ¿Cuántos usan la meditación como estrategia para gestionar su tiempo? | resumen_pregunta |  | 0.91 | 9/9 | 10.9 | — | — |
| CEN-07 | 1 | Compara los primeros 40 respondentes con los últimos 40 en la presión  | comparar_grupos | calculo_literal | — | 19/19 | 26.3 | — | — |
| CEN-08 | 1 | Hola | — | cortesia | — | 0/1 | 0.0 | — | — |
| CET-01 | 1 | ¿Cuántos participantes mencionan a su familia como apoyo? | conteo_porcentaje |  | 0.94 | 10/10 | 18.5 | — | — |
| CET-02 | 1 | ¿Cuál es la respuesta más larga de E05 y a qué pregunta corresponde? | — |  | — | 0/4 | 0.0 | — | — |
| CET-03 | 1 | Compara lo que dicen sobre sus profesores con lo que dicen sobre los s | aclaracion |  | 0.63 | 2/2 | 19.4 | — | — |
| CET-04 | 1 | ¿Qué dijo E03 sobre abandonar la universidad? | datos_respondente |  | 0.98 | 15/15 | 23.5 | — |  |
| CET-04 | 2 | ¿Y qué estrategias usa para mantenerse? | hallazgo |  | 0.56 | 7/7 | 26.5 | — | — |
| CET-05 | 1 | ¿Cuántas veces mencionan el dinero o la economía? | conteo_porcentaje |  | 0.92 | 11/11 | 15.5 | — | — |
| CET-06 | 1 | ¿Qué respondió el participante E99? | datos_respondente | calculo_literal | — | 15/15 | 20.0 | — | — |
| CET-07 | 1 | ¿El participante E02 tiene ansiedad? | — |  | — | 0/4 | 0.0 | — | — |
| CET-08 | 1 | ¿Qué me recomiendas para no reprobar? | — | consejo | — | 0/1 | 0.1 | — | — |
| CPR-01 | 1 | ¿Qué opción eligieron más en el reactivo del alpha de Cronbach? | resumen_pregunta |  | 0.88 | 9/9 | 15.3 | — | — |
| CPR-02 | 1 | ¿En qué reactivo están más repartidas las respuestas? | ranking_preguntas | calculo_literal | — | 16/16 | 23.4 | — | — |
| CPR-03 | 1 | Compara lo que eligieron en el reactivo del muestreo probabilístico en | comparar_grupos | calculo_literal | — | 18/18 | 25.6 | — | — |
| CPR-04 | 1 | ¿Cuántos marcaron Falso en el reactivo del acceso abierto? | conteo_porcentaje | frase_calculada | — | 4/4 | 16.9 | — |  |
| CPR-04 | 2 | De ellos, ¿qué eligieron en el reactivo del DOI? | aclaracion | aclaracion | — | 0/0 | 12.4 | — | — |
| CPR-05 | 1 | ¿En qué sección hay más respuestas en blanco? | comparar_grupos |  | 0.92 | 4/4 | 13.8 | — | — |
| CPR-06 | 1 | ¿Qué respondieron en el reactivo 20? | aclaracion | aclaracion | — | 0/3 | 10.8 | — | — |
| CPR-07 | 1 | ¿Cuál es la calificación promedio del grupo? | — | sin_calificar | — | 0/2 | 0.0 | — | — |
| CPR-08 | 1 | Hola | — | cortesia | — | 0/2 | 0.1 | — | — |
