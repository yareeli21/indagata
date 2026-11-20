# Fase 3: entender (7–8 nov 2026)

Commit `a831838`. 406 pruebas de visualization-service en verde. Casos repetidos en `casos/` (24 de las baterías),
`../chat_2026-11-07_fase3_control/` (5 de control) y `../chat_2026-11-08_fase3b*/` (después de las últimas
correcciones).

## Qué se cambió y qué casos resuelve

| Cambio (general, sin textos de las baterías) | Casos que ahora cumplen |
|---|---|
| **Cortesía** (`services/cortesia.py`):<br>- saludo, «qué puedes hacer», gracias y adiós, con el instrumento activo y 3 ejemplos sacados de su catálogo;<br>- consejo personal: no da consejos;<br>- malestar: amable, servicios de apoyo de la institución;<br>- «aprobaron / promedio» en pruebas, sin nombrar un reactivo | GEN-01, GEN-02, GEN-03, GEN-04, ENT-25, PRU-23, CEN-08, CET-08 |
| **Privacidad:** correos, teléfonos o nombres de un grupo («de los que…»), no solo de una persona nombrada | ENC-24 |
| **Mensajes de rechazo:** dicen que es una herramienta de investigación que no da consejos ni recetas, con ejemplos del catálogo | ENC-25 |
| **Preguntas sobre el instrumento** (tipo, duración, indicaciones, metodología): van a la ficha sin pasar por la interpretación | ENT-21 (indicaciones correctas); ENT-20 mejora (ya no inventa la duración) |
| **Lo que no existe:**<br>- un valor que el instrumento no registra;<br>- una opción con letra;<br>- un reactivo fuera de rango;<br>- otra participante;<br>Se avisa y se muestra lo que sí hay, sin texto recuperado | ENC-22, PRU-21, PRU-22, ENT-12, ENT-22, CEN-06, CET-06 |
| **Hilo de la conversación:**<br>- «muéstrame N (de ellos)»;<br>- «tal cual»;<br>- la persona de la que se habló;<br>- la opción nombrada acota el grupo;<br>- se conserva la condición anterior que la pregunta no menciona;<br>- contar una opción nombrada es una condición heredable | ENC-17, ENC-14 (2), PRU-15 (2), CEN-03, ENC-13 (2) |
| **Validación:**<br>- exclusiones solo si se piden;<br>- «menos consenso» = repartida;<br>- «>» sobre texto se vuelve «=»;<br>- raíces de seis letras;<br>- erratas | PRU-03 (ya ordena todos los reactivos), ENC-13 (2) |

## Lo que aún no cumple y en qué fase se resuelve

| Caso | Por qué | Fase |
|---|---|---|
| ENC-14 (1), PRU-07, PRU-13 (1) | La medida «repartida» usa el % de la opción más elegida y mezcla preguntas de opción múltiple (C6) | 4 |
| PRU-09, PRU-14 (2), ENC-09, CEN-02 | No hay cruce entre dos preguntas (C2) | 4 |
| ENC-08, ENC-10, ENC-11, PRU-10, CEN-07 | No hay grupos por respuesta, posición o sección (C1) | 4 |
| ENC-13 (3), PRU-17 (2), ENT-17 (2) | «¿Qué significa? / ¿por qué?» repite el cálculo en lugar de interpretarlo (C4) | 4 |
| ENC-13 (2) | El % se calcula sobre 2000 y no sobre el grupo anterior (1104) | 4 |
| PRU-15 (3) | No compara la respuesta de A001 con la distribución general | 4 |
| ENT-20 | Responde de más; no dice que la duración no está registrada | 4 |

## Hallazgos sobre los datos

- **El reactivo r10 de la prueba 130 está vacío para los 97 alumnos** en el archivo original
  (`pru_03_sucio_no_contemplado.csv`): es uno de los errores inyectados del escenario «no contemplado» (reactivo
  vacío).
  - Las respuestas «r10, 97 sin respuesta» (PRU-03) y «97 de 97 dejaron al menos uno en blanco» (PRU-04) son correctas.
  - En la calificación de la línea base esos dos casos quedaron como parciales.
- **Memoria de Ollama:** a las 23:44 del 7 nov el sistema mató el proceso del modelo (`signal: killed`) durante
  PRU-13 (3), que quedó como «modelo no disponible». El script de evaluación ahora reinicia Ollama cada N casos
  (`--reiniciar-ollama-cada`).
