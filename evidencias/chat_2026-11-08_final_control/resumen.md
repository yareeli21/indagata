# Evaluación del chat: chat_2026-11-08_final_control

- Casos: 24 (29 turnos con respuesta).
- Contra el «Debe»: **19 cumplen**, 5 parciales, 0 no cumplen.
- Planes válidos (intención distinta de aclaración): 20 de 23 (87.0 %).
- Caídas a plantilla: 12 de 29 (41.4 %).
- Plan del modelo usado sin cambios: 3 de 23 (13.0 %); el resto lo corrigieron la validación, las reglas o el hilo de la conversación.
- K-Precision (sin plantillas): mediana 0.90, mínimo 0.48 (n = 15).
- Cifras con respaldo en el contexto: 254 de 274.
- Tiempo por turno: mediana 37 s, p90 158 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| CEN-01 | 1 | ¿Cuántos estudiantes trabajan más de 30 horas? | conteo_porcentaje |  | 0.91 | 5/5 | 36.8 | — | cumple |
| CEN-02 | 1 | ¿Los que no trabajan dejan menos tareas para el último momento que los | comparar_grupos |  | 0.91 | 37/37 | 34.8 | — | cumple |
| CEN-03 | 1 | ¿Cuántos tienen dificultades para equilibrar trabajo y estudios? | conteo_porcentaje |  | 0.77 | 4/4 | 31.5 | — |  |
| CEN-03 | 2 | ¿Y de ellos, cuántos no trabajan? | conteo_porcentaje | calculo_literal | — | 6/6 | 37.0 | — |  |
| CEN-03 | 3 | Muéstrame 5 de ellos | filtrar_respondentes |  | 0.99 | 31/31 | 33.8 | — | cumple |
| CEN-04 | 1 | ¿En qué pregunta están más divididas las opiniones? | ranking_preguntas | calculo_literal | — | 16/16 | 42.7 | — | cumple |
| CEN-05 | 1 | ¿Qué es lo más preocupante de los resultados? | hallazgo |  | 0.48 | 9/9 | 54.2 | — |  |
| CEN-05 | 2 | ¿Por qué? | hallazgo | calculo_literal | — | 11/11 | 38.5 | — | parcial |
| CEN-06 | 1 | ¿Cuántos usan la meditación como estrategia para gestionar su tiempo? | resumen_pregunta |  | 0.91 | 9/9 | 18.8 | — | cumple |
| CEN-07 | 1 | Compara los primeros 40 respondentes con los últimos 40 en la presión  | comparar_grupos |  | 0.87 | 19/19 | 38.1 | — | cumple |
| CEN-08 | 1 | Hola | — | cortesia | — | 0/1 | 0.0 | — | cumple |
| CET-01 | 1 | ¿Cuántos participantes mencionan a su familia como apoyo? | conteo_porcentaje |  | 0.98 | 10/10 | 49.7 | — | cumple |
| CET-02 | 1 | ¿Cuál es la respuesta más larga de E05 y a qué pregunta corresponde? | — |  | — | 0/4 | 0.0 | — | cumple |
| CET-03 | 1 | Compara lo que dicen sobre sus profesores con lo que dicen sobre los s | aclaracion |  | 0.76 | 3/3 | 25.4 | — | parcial |
| CET-04 | 1 | ¿Qué dijo E03 sobre abandonar la universidad? | datos_respondente |  | 0.92 | 8/8 | 25.6 | — |  |
| CET-04 | 2 | ¿Y qué estrategias usa para mantenerse? | datos_respondente |  | 0.90 | 9/9 | 29.8 | — | cumple |
| CET-05 | 1 | ¿Cuántas veces mencionan el dinero o la economía? | conteo_porcentaje |  | 0.97 | 11/11 | 23.3 | — | parcial |
| CET-06 | 1 | ¿Qué respondió el participante E99? | aclaracion | aclaracion | — | 0/3 | 7.3 | — | cumple |
| CET-07 | 1 | ¿El participante E02 tiene ansiedad? | — |  | — | 0/4 | 0.0 | — | cumple |
| CET-08 | 1 | ¿Qué me recomiendas para no reprobar? | — | consejo | — | 0/1 | 0.0 | — | cumple |
| CPR-01 | 1 | ¿Qué opción eligieron más en el reactivo del alpha de Cronbach? | resumen_pregunta |  | 0.85 | 10/10 | 58.6 | — | parcial |
| CPR-02 | 1 | ¿En qué reactivo están más repartidas las respuestas? | ranking_preguntas |  | 0.89 | 16/16 | 157.9 | — | cumple |
| CPR-03 | 1 | Compara lo que eligieron en el reactivo del muestreo probabilístico en | comparar_grupos | calculo_literal | — | 21/21 | 58.7 | — | cumple |
| CPR-04 | 1 | ¿Cuántos marcaron Falso en el reactivo del acceso abierto? | conteo_porcentaje | calculo_literal | — | 4/4 | 184.9 | — |  |
| CPR-04 | 2 | De ellos, ¿qué eligieron en el reactivo del DOI? | resumen_pregunta |  | 0.90 | 10/10 | 511.0 | — | cumple |
| CPR-05 | 1 | ¿En qué sección hay más respuestas en blanco? | comparar_grupos | calculo_literal | — | 5/5 | 51.1 | — | parcial |
| CPR-06 | 1 | ¿Qué respondieron en el reactivo 20? | aclaracion | aclaracion | — | 0/3 | 17.0 | — | cumple |
| CPR-07 | 1 | ¿Cuál es la calificación promedio del grupo? | — | sin_calificar | — | 0/2 | 0.0 | — | cumple |
| CPR-08 | 1 | Hola | — | cortesia | — | 0/2 | 0.0 | — | cumple |

## Notas de la calificación contra el «Debe»

- **CEN-01.** Corregido en la Fase 5: «más de 30» elige la opción «Trabajo más de 30h» (37 de 160).
- **CEN-03.** (2) 24 de los 83 del grupo anterior (28.9 %); (3) 5 IDs con el total.
- **CEN-04.** Se mostró el cálculo, con la medida explicada (entropía normalizada).
- **CEN-05.** Usa la polaridad propuesta (sin revisar), que marca «Más de 20h» de estudio como desfavorable; agrega opiniones sin marcarlas como interpretación. (2) bien.
- **CET-03.** Cita a un solo participante (E34) para los dos temas; no compara entre participantes.
- **CET-04.** Corregido en la Fase 5: (2) sigue hablando de E03.
- **CET-05.** Cuenta participantes (13), no veces, y no explica que cuenta por raíz de palabra.
- **CPR-01.** La distribución y la opción más elegida son correctas y no califica, pero la segunda oración dice que otra opción tuvo «mayor aceptación» (contradice la primera).
- **CPR-02.** Repetido tras corregir la comprobación del orden del ranking.
- **CPR-03.** Se mostró el cálculo: distribución por tipo de universidad con n y %.
- **CPR-04.** (2) distribución del reactivo dentro de los 34 de (1). Repetido tras quitar el filtro por una opción del mismo reactivo (en la primera pasada se resumía sobre los 80).
- **CPR-05.** La tabla muestra 0 en las tres secciones, pero la frase calculada decía «la sección con más… es Metodología: 0» (corregido después en el código; no se repitió). En la primera pasada la redacción hablaba de «conocimiento uniforme»; en la segunda Ollama no respondió y se repitió.
- **CPR-06.** Repetido tras agregar el reactivo fuera de rango (en la primera pasada respondió con r02).
