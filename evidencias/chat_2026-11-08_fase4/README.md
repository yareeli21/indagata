# Fase 4: responder (8 nov 2026)

Commit `1213e38`. 417 pruebas de visualization-service, 126 de knowledge-service y 38 de storage-service en verde;
el frontend compila sin errores de tipos ni de lint.

Casos en `casos/` (29 de las baterías), `../chat_2026-11-08_fase4_control/` (8 de control) y en las corridas `b` y `c`,
después de las correcciones. Ollama se reinició solo cada 12 casos (`reinicios.log`).

## Qué se cambió y qué casos resuelve

| Cambio | Casos que ahora cumplen |
|---|---|
| **Comparar grupos** por la respuesta a otra pregunta («según la carga», «entre presencial y en línea», «los que X… que los que Y»), con la distribución y la media de cada grupo sobre su propio n | ENC-08, ENC-09, ENC-11, ENC-12, CEN-02 |
| **Por posición** (primeros N y últimos N; se avisa si se solapan) | ENC-10, PRU-10, CEN-07 |
| **Por sección:** respuestas en blanco o nulas, con su % de las respuestas posibles | PRU-08, PRU-12 |
| **Cruce:** distribución de una pregunta dentro del grupo que cumple una condición («de los que marcaron X en…, ¿qué eligieron en…?», «de ellos, ¿qué respondieron…?») | PRU-09, PRU-14 (2) |
| **«Más repartidas / menos consenso»** con entropía normalizada, sin preguntas de varias respuestas, diciendo la medida | ENC-14, PRU-07, PRU-13, CEN-04 |
| **«¿Qué significa? / ¿por qué?» en dos capas:** «Lo que muestran los datos» (tal cual) y «Interpretación (del asistente, no es un dato)» | ENC-13 (3), ENC-16 (2), PRU-13 (3), PRU-17 (2), CEN-05 (2) |
| **«Lo más preocupante» con la polaridad** revisada por la investigadora (127) o propuesta por el sistema (61, marcada «sin revisar») | ENC-16, CEN-05 |
| **«¿Cuántos han hecho…?»:** el grupo de las respuestas que empiezan con «Sí» | ENC-13 (1) |
| **Entrevistas sin modelo:** palabras y turnos por hablante (limpieza), cobertura de la guía, respuesta más larga, preguntas fuera de la guía | ENT-02, ENT-03, ENT-05, ENT-07, CET-02 |
| **Menciones** con «o» y calificativos, con el conteo de palabras y su método | ENT-06, CET-01, CET-05 |
| **Diagnósticos:** no se hacen; se muestra lo que la persona contó con sus citas (valoración negativa o mixta del análisis) | ENT-24, CET-07 |
| **Hallazgos de entrevista** desde el análisis de lo que se cuenta (temas, valoración y citas literales) | ENT-17 (1) |
| **Encabezado de la transcripción** en el documento y la ficha; los datos de la ficha se responden sin describir todo | ENT-20, ENT-21 |
| **Opcionales:** no se registra, se dice así. **Escalas:** las preguntas con escala y sus extremos | ENC-21, ENC-20 |
| **Listas** con total, primeros 20 y «muéstrame más» | (D6) |
| **Insignia «fiel por construcción»** solo con cifras | (D6) |
| **Interfaz:** «Ver datos» (tablas desplegables) y «Cómo lo calculé» (criterio de cada cálculo y ajustes al plan) | Principio 6 |

## Lo que aún no cumple

| Caso | Situación |
|---|---|
| PRU-11 | Comparar dos conjuntos de reactivos nombrados por tema (seguridad contra licencias) no está implementado; responde con un solo reactivo |
| ENC-13 (2) | La cifra es correcta (382), pero el % se da sobre 2000 y no sobre el grupo anterior (1104) |
| PRU-14 (2) | La tabla del cruce es correcta; la redacción nombra mal la condición («cumplieron la condición r15») |
| ENT-19 | Responde «12 preguntas» y temas generales; no agrupa las preguntas en temas |
| ENT-17 (2) | Prioriza con citas, pero sin decir que es un solo testimonio en todos los casos |
| Redacción en general | La verificación no detecta una afirmación falsa armada con cifras que sí están en el resultado (en una corrida: «97 (100 %) marcaron Verdadero» cuando el plan no tenía condición) |
