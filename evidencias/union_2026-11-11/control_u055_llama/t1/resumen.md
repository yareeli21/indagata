# Evaluación del chat: t1

- Casos: 8 (11 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 8).
- Planes válidos (intención distinta de aclaración): 9 de 9 (100.0 %).
- Caídas a plantilla: 8 de 11 (72.7 %).
- Plan del modelo usado sin cambios: 1 de 9 (11.1 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.83, mínimo 0.32 (n = 3).
- Cifras con respaldo en el contexto: 138 de 139.
- Tiempo por turno: mediana 19 s, p90 22 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CEN-01 | 1 | ¿Cuántos estudiantes trabajan más de 30 horas? | conteo_porcentaje | frase_calculada | — | 5/5 | 21.4 | — | — |
| CEN-02 | 1 | ¿Los que no trabajan dejan menos tareas para el último momento que los | comparar_grupos | calculo_literal | — | 37/37 | 26.5 | — | — |
| CEN-03 | 1 | ¿Cuántos tienen dificultades para equilibrar trabajo y estudios? | conteo_porcentaje | frase_calculada | — | 4/4 | 17.6 | — |  |
| CEN-03 | 2 | ¿Y de ellos, cuántos no trabajan? | conteo_porcentaje | frase_calculada | — | 6/6 | 20.4 | — |  |
| CEN-03 | 3 | Muéstrame 5 de ellos | filtrar_respondentes | calculo_literal | — | 31/31 | 22.2 | — | — |
| CEN-04 | 1 | ¿En qué pregunta están más divididas las opiniones? | ranking_preguntas | calculo_literal | — | 16/16 | 14.9 | — | — |
| CEN-05 | 1 | ¿Qué es lo más preocupante de los resultados? | hallazgo | calculo_literal | — | 9/9 | 16.3 | — |  |
| CEN-05 | 2 | ¿Por qué? | — |  | 0.32 | 2/2 | 8.7 | — | — |
| CEN-06 | 1 | ¿Cuántos usan la meditación como estrategia para gestionar su tiempo? | resumen_pregunta |  | 0.91 | 9/9 | 10.9 | — | — |
| CEN-07 | 1 | Compara los primeros 40 respondentes con los últimos 40 en la presión  | comparar_grupos |  | 0.83 | 19/19 | 20.0 | — | — |
| CEN-08 | 1 | Hola | — | cortesia | — | 0/1 | 0.0 | — | — |
