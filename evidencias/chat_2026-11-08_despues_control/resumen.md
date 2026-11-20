# Evaluación del chat: chat_2026-11-08_despues_control

- Casos: 16 (20 turnos con respuesta).
- Contra el «Debe»: **9 cumplen**, 5 parciales, 2 no cumplen.
- Planes válidos (intención distinta de aclaración): 14 de 16 (87.5 %).
- Caídas a plantilla: 5 de 20 (25.0 %).
- K-Precision (sin plantillas): mediana 0.91, mínimo 0.59 (n = 13).
- Cifras con respaldo en el contexto: 178 de 192.
- Tiempo por turno: mediana 31 s, p90 50 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CEN-01 | 1 | ¿Cuántos estudiantes trabajan más de 30 horas? | conteo_porcentaje |  | 0.74 | 6/7 | 48.8 | — | no |
| CEN-02 | 1 | ¿Los que no trabajan dejan menos tareas para el último momento que los | comparar_grupos |  | 0.93 | 37/37 | 37.3 | — | cumple |
| CEN-03 | 1 | ¿Cuántos tienen dificultades para equilibrar trabajo y estudios? | conteo_porcentaje |  | 0.74 | 3/3 | 30.0 | — |  |
| CEN-03 | 2 | ¿Y de ellos, cuántos no trabajan? | conteo_porcentaje |  | 0.88 | 4/4 | 45.3 | — |  |
| CEN-03 | 3 | Muéstrame 5 de ellos | filtrar_respondentes | calculo_literal | — | 31/31 | 33.9 | — | parcial |
| CEN-04 | 1 | ¿En qué pregunta están más divididas las opiniones? | ranking_preguntas |  | 0.94 | 16/16 | 27.8 | — | parcial |
| CEN-05 | 1 | ¿Qué es lo más preocupante de los resultados? | hallazgo |  | 0.70 | 9/9 | 80.3 | — |  |
| CEN-05 | 2 | ¿Por qué? | hallazgo | calculo_literal | — | 11/11 | 31.9 | — | parcial |
| CEN-06 | 1 | ¿Cuántos usan la meditación como estrategia para gestionar su tiempo? | resumen_pregunta |  | 0.91 | 9/9 | 18.6 | — | cumple |
| CEN-07 | 1 | Compara los primeros 40 respondentes con los últimos 40 en la presión  | comparar_grupos |  | 0.91 | 19/19 | 35.8 | — | cumple |
| CEN-08 | 1 | Hola | — | cortesia | — | 0/1 | 0.0 | — | cumple |
| CET-01 | 1 | ¿Cuántos participantes mencionan a su familia como apoyo? | conteo_porcentaje |  | 0.99 | 10/10 | 50.2 | — | cumple |
| CET-02 | 1 | ¿Cuál es la respuesta más larga de E05 y a qué pregunta corresponde? | — |  | — | 0/4 | 0.0 | — | cumple |
| CET-03 | 1 | Compara lo que dicen sobre sus profesores con lo que dicen sobre los s | aclaracion |  | 0.75 | 1/1 | 24.2 | — | parcial |
| CET-04 | 1 | ¿Qué dijo E03 sobre abandonar la universidad? | datos_respondente |  | 0.92 | 8/8 | 24.5 | — |  |
| CET-04 | 2 | ¿Y qué estrategias usa para mantenerse? | metodologia |  | 0.59 | 3/3 | 26.4 | — | no |
| CET-05 | 1 | ¿Cuántas veces mencionan el dinero o la economía? | conteo_porcentaje |  | 0.97 | 11/11 | 21.4 | — | parcial |
| CET-06 | 1 | ¿Qué respondió el participante E99? | aclaracion | aclaracion | — | 0/3 | 6.6 | — | cumple |
| CET-07 | 1 | ¿El participante E02 tiene ansiedad? | — |  | — | 0/4 | 0.0 | — | cumple |
| CET-08 | 1 | ¿Qué me recomiendas para no reprobar? | — | consejo | — | 0/1 | 0.0 | — | cumple |

## Notas de la calificación contra el «Debe»

- **CEN-01.** El anclaje tomó las tres opciones que empiezan con «Trabajo» y además un filtro «30 horas» en otra pregunta (horas de estudio); respondió «1 estudiante» y 1.9 %. La opción «Trabajo más de 30h» tiene 37.
- **CEN-03.** (2) la cifra es correcta (24), pero el % se da sobre 160 y no sobre los 83 de (1); (3) bien.
- **CEN-04.** La tabla pone primero p09; la redacción dice que la primera es p10 y no explica la medida.
- **CEN-05.** Usa la polaridad propuesta (sin revisar), que marca «Más de 20h» de estudio como desfavorable; (1) agrega una opinión sin marcarla como interpretación. (2) bien.
- **CET-03.** Cita a un solo participante (E34) para los dos temas; no compara entre participantes.
- **CET-04.** (1) bien; (2) el modelo pidió aclaración (intención metodología) y la respuesta habló de E15, E19 y E26 en lugar de E03.
- **CET-05.** Cuenta participantes (13), no veces, y no explica que cuenta por raíz de palabra.
