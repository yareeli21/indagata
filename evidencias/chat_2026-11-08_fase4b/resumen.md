# Evaluación del chat: chat_2026-11-08_fase4b

- Casos: 11 (16 turnos con respuesta).
- Contra el «Debe»: **0 cumplen**, 0 parciales, 0 no cumplen (sin calificar: 11).
- Planes válidos (intención distinta de aclaración): 13 de 15 (86.7 %).
- Caídas a plantilla: 3 de 16 (18.8 %).
- K-Precision (sin plantillas): mediana 0.76, mínimo 0.41 (n = 13).
- Cifras con respaldo en el contexto: 147 de 148.
- Tiempo por turno: mediana 35 s, p90 72 s.

| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |
|---|---|---|---|---|---|---|---|---|---|
| ENC-09 | 1 | ¿Los que trabajan en algo relacionado con su carrera aprobaron más cer | comparar_grupos |  | 0.85 | 21/21 | 70.3 | — | — |
| ENC-12 | 1 | ¿Quienes usan una plataforma virtual a diario califican mejor la bibli | aclaracion |  | 0.44 | 4/4 | 40.7 | — | — |
| ENC-13 | 1 | ¿Cuántos han hecho prácticas profesionales? | conteo_porcentaje | calculo_literal | — | 4/4 | 24.6 | — |  |
| ENC-13 | 2 | ¿Y de ellos, cuántos la consiguieron por convenio de la institución? | conteo_porcentaje |  | 0.83 | 3/3 | 38.4 | — |  |
| ENC-13 | 3 | ¿Qué puede significar eso? | conteo_porcentaje | calculo_literal | — | 4/4 | 32.6 | — | — |
| ENC-16 | 1 | ¿Qué es lo más preocupante de los resultados? | hallazgo |  | 0.59 | 19/19 | 112.2 | — |  |
| ENC-16 | 2 | ¿Por qué lo consideras preocupante? | hallazgo |  | 0.54 | 11/11 | 42.7 | — | — |
| PRU-08 | 1 | Compara la sección de verdadero/falso con la de competencias básicas e | comparar_grupos |  | 0.87 | 8/8 | 34.1 | — | — |
| PRU-09 | 1 | De los que marcaron Verdadero en «el correo electrónico es siempre seg | resumen_pregunta |  | 0.85 | 6/6 | 36.3 | — | — |
| PRU-10 | 1 | Compara los primeros 50 alumnos con los últimos 50 en el reactivo de l | comparar_grupos |  | 0.70 | 3/3 | 34.2 | — | — |
| PRU-11 | 1 | Compara cómo respondieron los reactivos de seguridad (VPN, phishing, c | aclaracion |  | 0.82 | 5/5 | 30.5 | — | — |
| PRU-12 | 1 | ¿Las respuestas en blanco se concentran en alguna sección? | comparar_grupos |  | 0.76 | 10/10 | 68.9 | — | — |
| PRU-14 | 1 | ¿Cuántos marcaron Verdadero en «la nube elimina por completo el riesgo | conteo_porcentaje |  | 0.41 | 2/3 | 30.4 | — |  |
| PRU-14 | 2 | De ellos, ¿qué respondieron sobre Wi-Fi público? | resumen_pregunta |  | 0.75 | 5/5 | 33.0 | — |  |
| PRU-14 | 3 | Muéstrame 5 | resumen_pregunta | calculo_literal | — | 40/40 | 71.6 | — | — |
| ENT-20 | 1 | ¿Qué tipo de entrevista es y cuánto dura? | — |  | 1.00 | 2/2 | 21.4 | — | — |
