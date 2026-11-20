# Evaluación del chat: chat_2026-11-07_control_antes

- Casos: 16 (20 turnos con respuesta).
- Contra el «Debe»: **1 cumplen**, 4 parciales, 11 no cumplen.
- Planes válidos (intención distinta de aclaración): 16 de 20 (80.0 %).
- Caídas a plantilla: 6 de 20 (30.0 %).
- K-Precision (sin plantillas): mediana 0.86, mínimo 0.59 (n = 14).
- Cifras con respaldo en el contexto: 201 de 206.
- Tiempo por turno: mediana 32 s, p90 55 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CEN-01 | 1 | ¿Cuántos estudiantes trabajan más de 30 horas? | conteo_porcentaje |  | 0.80 | 5/5 | 40.7 | — | no |
| CEN-02 | 1 | ¿Los que no trabajan dejan menos tareas para el último momento que los | comparar_grupos | calculo_literal | — | 15/15 | 55.2 | — | no |
| CEN-03 | 1 | ¿Cuántos tienen dificultades para equilibrar trabajo y estudios? | conteo_porcentaje |  | 0.77 | 3/3 | 33.3 | — |  |
| CEN-03 | 2 | ¿Y de ellos, cuántos no trabajan? | conteo_porcentaje |  | 0.82 | 3/3 | 28.0 | — |  |
| CEN-03 | 3 | Muéstrame 5 de ellos | ranking_preguntas |  | 0.96 | 13/13 | 37.4 | — | no |
| CEN-04 | 1 | ¿En qué pregunta están más divididas las opiniones? | ranking_preguntas |  | 0.82 | 13/13 | 33.3 | — | no |
| CEN-05 | 1 | ¿Qué es lo más preocupante de los resultados? | resumen_pregunta | calculo_literal | — | 42/42 | 66.5 | — |  |
| CEN-05 | 2 | ¿Por qué? | resumen_pregunta |  | 0.86 | 41/41 | 50.5 | — | no |
| CEN-06 | 1 | ¿Cuántos usan la meditación como estrategia para gestionar su tiempo? | conteo_porcentaje | calculo_literal | — | 1/1 | 38.3 | — | no |
| CEN-07 | 1 | Compara los primeros 40 respondentes con los últimos 40 en la presión  | comparar_grupos | calculo_literal | — | 26/26 | 66.8 | — | no |
| CEN-08 | 1 | Hola | aclaracion | aclaracion_ajena | — | 0/2 | 18.1 | — | no |
| CET-01 | 1 | ¿Cuántos participantes mencionan a su familia como apoyo? | conteo_porcentaje |  | 1.00 | 2/2 | 31.7 | — | no |
| CET-02 | 1 | ¿Cuál es la respuesta más larga de E05 y a qué pregunta corresponde? | datos_respondente |  | 0.94 | 3/3 | 22.8 | — | parcial |
| CET-03 | 1 | Compara lo que dicen sobre sus profesores con lo que dicen sobre los s | aclaracion |  | 0.59 | 2/2 | 31.0 | — | parcial |
| CET-04 | 1 | ¿Qué dijo E03 sobre abandonar la universidad? | datos_respondente |  | 0.90 | 3/3 | 26.6 | — |  |
| CET-04 | 2 | ¿Y qué estrategias usa para mantenerse? | datos_respondente |  | 0.87 | 4/4 | 30.0 | — | parcial |
| CET-05 | 1 | ¿Cuántas veces mencionan el dinero o la economía? | conteo_porcentaje |  | 0.98 | 10/10 | 25.9 | — | parcial |
| CET-06 | 1 | ¿Qué respondió el participante E99? | aclaracion | aclaracion | — | 0/3 | 7.3 | — | cumple |
| CET-07 | 1 | ¿El participante E02 tiene ansiedad? | datos_respondente |  | 0.94 | 12/12 | 33.5 | — | no |
| CET-08 | 1 | ¿Qué me recomiendas para no reprobar? | aclaracion |  | 0.60 | 3/3 | 16.0 | — | no |

## Notas de la calificación contra el «Debe»

- **CEN-01.** Usó p17 (horas de estudio) en lugar de p14 (carga laboral, «Trabajo más de 30h»): 2.5 % falso para lo que se pidió.
- **CEN-02.** C2: no hay cruce; mostró el resumen de p10.
- **CEN-03.** C3: (2) repitió el conteo de (1); (3) abrió un ranking de preguntas.
- **CEN-04.** C6: «repartida» por el % de la opción más elegida en una escala de 10 puntos.
- **CEN-05.** C11: sin polaridad; resumió p09, p13 y p18 sin decir qué es desfavorable.
- **CEN-06.** C7: «El instrumento tiene 160 respondentes»; no dice que la opción no existe.
- **CEN-07.** C1: no hay grupos por posición; mostró el resumen de p18.
- **CEN-08.** C10: mensaje genérico con ejemplos fijos.
- **CET-01.** C8: buscó la frase literal «familia como apoyo» y dio 0 de 40.
- **CET-02.** C8: dio una respuesta de E05 sin calcular cuál es la más larga.
- **CET-03.** Citas de profesores, pero casi nada de los servicios de apoyo.
- **CET-04.** (1) habló de equilibrar trabajo y estudio, no de abandonar (p02); (2) siguió con E03.
- **CET-05.** Contó participantes (9 de 40), no menciones, y no aclaró cómo contó.
- **CET-07.** C10: «sugiere una experiencia cercana a la ansiedad»: casi un diagnóstico.
- **CET-08.** C10: respondió con recomendaciones de los participantes como si fueran consejos.
