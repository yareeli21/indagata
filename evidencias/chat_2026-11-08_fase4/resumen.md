# Evaluación del chat: chat_2026-11-08_fase4

- Casos: 29 (39 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 29).
- Planes válidos (intención distinta de aclaración): 26 de 28 (92.9 %).
- Caídas a plantilla: 6 de 39 (15.4 %).
- K-Precision (sin plantillas): mediana 0.81, mínimo 0.29 (n = 26).
- Cifras con respaldo en el contexto: 321 de 343.
- Tiempo por turno: mediana 40 s, p90 65 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-08 | 1 | Compara la opinión sobre laboratorios y equipos entre modalidad presen | comparar_grupos | calculo_literal | — | 30/30 | 63.7 | — | — |
| ENC-09 | 1 | ¿Los que trabajan en algo relacionado con su carrera aprobaron más cer | comparar_grupos |  | 0.77 | 9/9 | 62.3 | — | — |
| ENC-10 | 1 | Compara los primeros 100 respondentes con los últimos 100 en qué tan p | comparar_grupos | calculo_literal | — | 25/25 | 57.5 | — | — |
| ENC-11 | 1 | ¿Cambia la expectativa de titularse según la carga académica? | comparar_grupos | calculo_literal | — | 53/53 | 70.3 | — | — |
| ENC-12 | 1 | ¿Quienes usan una plataforma virtual a diario califican mejor la bibli | aclaracion |  | 0.46 | 4/4 | 40.1 | — | — |
| ENC-13 | 1 | ¿Cuántos han hecho prácticas profesionales? | resumen_pregunta |  | 0.76 | 10/10 | 40.2 | — |  |
| ENC-13 | 2 | ¿Y de ellos, cuántos la consiguieron por convenio de la institución? | resumen_pregunta |  | 0.72 | 10/10 | 40.7 | — |  |
| ENC-13 | 3 | ¿Qué puede significar eso? | resumen_pregunta |  | 0.29 | 4/4 | 34.4 | — | — |
| ENC-14 | 1 | ¿En qué pregunta están más divididas las opiniones? | ranking_preguntas |  | 0.91 | 18/18 | 29.5 | — |  |
| ENC-14 | 2 | Muéstrame los datos tal cual | resumen_pregunta |  | 0.81 | 14/14 | 52.2 | — | — |
| ENC-16 | 1 | ¿Qué es lo más preocupante de los resultados? | resumen_pregunta | calculo_literal | — | 13/13 | 69.2 | — |  |
| ENC-16 | 2 | ¿Por qué lo consideras preocupante? | resumen_pregunta |  | 0.37 | 3/3 | 23.1 | — | — |
| ENC-20 | 1 | ¿Cuáles preguntas usan escala del 1 al 5 y qué significan sus extremos | — |  | — | 0/6 | 0.0 | — | — |
| ENC-21 | 1 | ¿Qué preguntas eran opcionales? | — |  | — | 0/0 | 0.1 | — | — |
| PRU-07 | 1 | ¿En qué reactivo estuvieron más repartidas las respuestas? | ranking_preguntas |  | 0.96 | 15/15 | 40.9 | — | — |
| PRU-08 | 1 | Compara la sección de verdadero/falso con la de competencias básicas e | — |  | 0.84 | 3/3 | 18.4 | — | — |
| PRU-09 | 1 | De los que marcaron Verdadero en «el correo electrónico es siempre seg | resumen_pregunta |  | 0.81 | 6/6 | 64.7 | — | — |
| PRU-10 | 1 | Compara los primeros 50 alumnos con los últimos 50 en el reactivo de l | comparar_grupos |  | 0.80 | 2/2 | 45.5 | — | — |
| PRU-11 | 1 | Compara cómo respondieron los reactivos de seguridad (VPN, phishing, c | aclaracion |  | 0.82 | 5/5 | 30.6 | — | — |
| PRU-12 | 1 | ¿Las respuestas en blanco se concentran en alguna sección? | — |  | 0.85 | 3/3 | 19.3 | — | — |
| PRU-13 | 1 | ¿En qué reactivo hubo menos consenso? | ranking_preguntas |  | 0.91 | 15/15 | 44.0 | — |  |
| PRU-13 | 2 | Muéstrame cómo se repartieron las respuestas | resumen_pregunta |  | 0.85 | 6/6 | 31.8 | — |  |
| PRU-13 | 3 | ¿Qué podría explicar esa división? | resumen_pregunta |  | 0.46 | 5/5 | 35.4 | — | — |
| PRU-14 | 1 | ¿Cuántos marcaron Verdadero en «la nube elimina por completo el riesgo | conteo_porcentaje |  | 1.00 | 4/4 | 19.0 | — |  |
| PRU-14 | 2 | De ellos, ¿qué respondieron sobre Wi-Fi público? | conteo_porcentaje |  | 1.00 | 4/4 | 18.7 | — |  |
| PRU-14 | 3 | Muéstrame 5 | filtrar_respondentes |  | 1.00 | 4/4 | 17.8 | — | — |
| PRU-17 | 1 | ¿Qué reactivos convendría revisar por cómo se respondieron? | resumen_pregunta | calculo_literal | — | 27/27 | 58.6 | — |  |
| PRU-17 | 2 | ¿Por qué? | resumen_pregunta |  | 0.63 | 8/8 | 38.7 | — | — |
| ENT-02 | 1 | ¿Cuántas palabras dijo la participante y cuántas el entrevistador? | — |  | — | 0/3 | 0.0 | — | — |
| ENT-03 | 1 | ¿Respondió todas las preguntas de la guía? ¿Cuáles no? | — |  | — | 0/2 | 0.0 | — | — |
| ENT-05 | 1 | ¿Cuál fue su respuesta más larga y a qué pregunta corresponde? | — |  | — | 0/7 | 0.1 | — | — |
| ENT-06 | 1 | ¿Cuántas veces menciona el estrés o la ansiedad? | conteo_porcentaje | calculo_literal | — | 6/6 | 55.0 | — | — |
| ENT-07 | 1 | ¿Hubo preguntas de seguimiento que no estaban en la guía? | — |  | — | 0/0 | 0.0 | — | — |
| ENT-11 | 1 | ¿Qué pesó más para no buscar ayuda: el estigma, el tiempo de espera o  | resumen_pregunta |  | 0.62 | 2/2 | 53.6 | — | — |
| ENT-17 | 1 | ¿Cuáles son los hallazgos principales de la entrevista? | hallazgo |  | 0.86 | 5/5 | 55.1 | — |  |
| ENT-17 | 2 | ¿Cuál debería atender primero la universidad y por qué? | hallazgo |  | 0.65 | 5/5 | 128.7 | — | — |
| ENT-19 | 1 | ¿Cuántas preguntas tiene la guía y qué temas cubre? | — |  | 0.80 | 1/1 | 18.5 | — | — |
| ENT-20 | 1 | ¿Qué tipo de entrevista es y cuánto dura? | — |  | 1.00 | 2/2 | 19.8 | — | — |
| ENT-24 | 1 | ¿La participante tiene depresión? | — |  | — | 0/4 | 0.1 | — | — |
