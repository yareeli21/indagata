# Capítulo Y. Pruebas

<!--
NOTA DE TRABAJO (no incluir en el reporte)
- Fuentes en comentarios <!- - fuente: … - ->. «Registro <fecha>» = sesión de Claude Code del
  proyecto (~/.claude/projects/…/0b7fa2f9….jsonl). Reportes: tools/rag/reportes/.
- Reorganizado el 8 nov: cada prueba compara condiciones (tipo de instrumento, limpio contra ruidoso, formato,
  versión anterior contra vigente) con un resultado esperado conocido. La historia de los cambios de código no se
  narra aquí: cada decisión está en Desarrollo con la prueba que la motivó.
- Evidencias: evidencias/<tema>_<fecha>/ (RESULTADO.md, README.md o JSON de cada carpeta).
- Tablas «Tabla P.n», figuras «Figura P.n».
-->

## Y.1 Estrategia y datos

### Y.1.1 Qué se prueba y cómo se compara

Este capítulo reporta cómo se comporta el sistema con instrumentos de investigación; las pruebas automatizadas del
código se describen en Desarrollo X.12. Se organiza en cinco ejes (Tabla P.1).

**Tabla P.1.** Ejes de las pruebas.

| Eje | Pregunta que responde | Qué se compara | Sección |
|---|---|---|---|
| 1. Limpieza | ¿Detecta y corrige lo que debe, y solo eso? | Cada tipo de instrumento, limpio y con ruido; ruido contemplado y no contemplado | Y.2 |
| 2. Estandarización | ¿El documento, los chunks, las dimensiones y los KPIs corresponden al instrumento? | Formatos de archivo; estrategias de chunks; criterios de dimensiones; métodos de KPIs | Y.3 |
| 3. Chat | ¿Responde con exactitud y se sostiene en las fuentes? | Versiones del chat sobre los mismos conjuntos de preguntas; instrumentos vistos y no vistos | Y.4 |
| 4. Modelos | ¿Cambia la calidad o el tiempo con otro modelo redactor o juez? | Cuatro modelos de 3–4B como redactores y como jueces | Y.5 |
| 5. Duración | ¿Cuánto tarda cada paso? | Pasos del procesamiento y respuestas del chat | Y.6 |

**Criterio común.** Cada prueba tiene un resultado esperado que se conoce sin usar el sistema: cifras calculadas con
pandas o SQL sobre el CSV, la «verdad» de los errores inyectados, la clave de una entrevista o lo que la respuesta
**debe** contener según la investigadora. Cuando una prueba se repitió después de cambiar el sistema, se reportan
las dos corridas sobre el **mismo** conjunto, para que la mejora se vea; qué se cambió está en Desarrollo. La versión
vigente de cada componente está en la Tabla D.0. Todas las respuestas de los instrumentos son sintéticas: las
conclusiones son sobre el funcionamiento del sistema, no sobre estudiantes. Lo que falta medir con instrumentos de la
investigadora queda marcado [PENDIENTE: prueba de la investigadora]; la guía está en `markdowns/GUIA_PRUEBAS.md`.

### Y.1.2 Entorno

Todas las pruebas corrieron sobre la orquestación completa en el equipo de la Tabla D.1 (Intel Core i5-11320H,
15.8 GB de RAM, GTX 1650 de 4 GiB, Windows 11), con Python 3.12.15 en los contenedores y Ollama 0.32.9 en la GPU.
La memoria fue la restricción principal: el sistema operativo detuvo procesos largos varias veces (17, 18 y 25 oct,
y Ollama el 7 nov). Por eso las pruebas pesadas se ejecutaron de una en una, las evaluaciones guardan cada pregunta
al terminarla y reinician Ollama cada 15 casos.
<!-- fuente: pip list en los contenedores (18 oct); ollama --version (25 oct); registro 17 oct 22:51; 18 oct 01:26 y 02:27; 25 oct; docker inspect indagata_ollama (OOMKilled, 7 nov); tools/rag/evaluar_chat.py (--reiniciar-ollama-cada) -->

### Y.1.3 Datos de prueba

Todas las respuestas son sintéticas. Los datos de las pruebas salen de tres fuentes:
- **El generador de datos sintéticos (Desarrollo X.6).** De sus 31 instrumentos se procesaron en el sistema enc_04,
  enc_05, enc_09 (instrumento 61), enc_11 (109), pru_01, pru_02, pru_04, pru_06 (133) y ent_01 (60). enc_01, el
  cuestionario real con respuestas sintéticas, no se subió: su CSV se usó fuera del sistema para validar las
  dimensiones sugeridas (Y.3.3).
- **Instrumentos construidos para probar una función concreta** (abajo). En ellos se sabe de antemano qué debe
  responder el sistema.
- **La encuesta de la investigadora:** una encuesta simulada de 2000 respondentes con su formulario de Google Forms
  (instrumento 127).

La Tabla P.2 dice qué datos se usaron en cada prueba, y el Anexo A, dónde está el archivo de cada instrumento, su
original y su documento final, y en qué pruebas se usó.

**Instrumentos construidos para probar.** La idea es la inversa del generador: **primero se decide qué resultado
debe dar el sistema y después se arma el archivo que lo contiene.** Así, si el sistema responde otra cosa, el error
está en el sistema y no en los datos. Son cuatro tipos, en el orden en que se hicieron (los archivos pequeños de las
pruebas automatizadas se describen en Desarrollo X.12):

| Tipo | Cómo se fija el resultado esperado | Casos |
|---|---|---|
| Resultado conocido (17 oct) | Se programa en el script que genera el archivo | enc_10_turno |
| Variantes de formato (20–22 oct) | Se reutilizan respuestas conocidas y solo cambia la forma del archivo | 3 variantes sin secciones y 13 formatos |
| Entrevistas con clave (22 oct) | Se escribe a mano cada respuesta junto con su clave | 2 entrevistas que divagan |
| Errores inyectados (24 oct, 2 nov y 7 nov) | Se inyectan errores en una copia de un instrumento y se guarda la verdad de cada uno | enc_11, pru_01, pru_03, enc_06, ent_11 y ent_02 |

**Resultado conocido: enc_10_turno (17 oct).**
- **Qué se quería probar.** Las preguntas por grupo del chat («¿qué porcentaje del turno vespertino está de acuerdo
  con la pregunta 4?»). Ninguna encuesta generada tenía columna de turno.
- **Cómo se construyó.** 60 respondentes, 30 por turno, con 8 ítems Likert en dos dimensiones («Evaluación del
  aprendizaje» y «Ambiente escolar»). Cada persona tiene un nivel de acuerdo de fondo por dimensión, del que salen sus
  cuatro respuestas. A propósito, el turno vespertino tiene un nivel de fondo más bajo en evaluación: 2.7 frente a 3.9
  del matutino. Semilla 20261017.
- **Resultado esperado.** **4 de 30 (13.3 %) del turno vespertino están de acuerdo con p04.** Se conoce antes de
  procesar el archivo, así que la respuesta del chat se califica como correcta o incorrecta.
- **Dónde.** `tools/data_synthesis/generar_enc_10_turno.py` → `storage/instrumentos_sinteticos/encuestas/enc_10_turno_*`
  (instrumento 59).
<!-- fuente: tools/data_synthesis/generar_enc_10_turno.py (docstring, SEMILLA, MEDIAS); commit 1b04c3d; registro 17 oct -->

**Variantes de formato: las mismas respuestas en otra forma (20–22 oct).**
- **Qué se quería probar.** Que el sistema funcione con los archivos tal como llegan en la realidad: sin secciones,
  con encabezados en código, exportados de Google Forms, Qualtrics o LimeSurvey, en Excel…
- **Cómo se construyó.** Se toma enc_10_turno y se reescribe el **mismo** archivo en otra forma. **No se inventa
  ninguna respuesta**: las 60 personas responden lo mismo en todas las variantes; solo cambian los encabezados, las
  secciones o el formato.
- **Resultado esperado.** **Las mismas cifras en todas las variantes** que el sistema acepta (por ejemplo, el 4 de
  30). Las que no puede leer bien (encabezados en código sin el original, formato largo, sin fila de encabezados)
  deben rechazarse al subirlas, con el motivo.
- **Dónde.** `evidencias/encuesta_sin_secciones_2026-10-20/generar_variantes.py` (variantes A, B y C) y
  `tools/formatos/generar_corpus.py` (formatos E01 a E13: 10 que se aceptan y 3 que se rechazan).
<!-- fuente: evidencias/encuesta_sin_secciones_2026-10-20/generar_variantes.py (docstring); tools/formatos/generar_corpus.py (docstring); tools/formatos/corpus/encuestas/ (E01–E13) -->

**Entrevistas escritas a mano con su clave (22 oct).**
- **Qué se quería probar.** Que el análisis de entrevistas separe lo que responde la pregunta de lo que es relato
  del pasado o digresión. Ejemplo que lo motivó: «Cuando iba en la primaria no lo pensaba así […] pero ahora creo que
  sí, me llenan de energía por querer seguir manteniendo la beca deportiva».
- **Cómo se construyó.** Dos entrevistas breves de 4 personas × 4 preguntas: una de estudiantes, sobre vida
  universitaria, y otra de docentes, sobre evaluación. Las respuestas mezclan a propósito pasado y presente,
  digresiones («por cierto, el estacionamiento…») y posturas ambivalentes («depende de la materia»). Cada respuesta
  lleva su **clave**: la postura correcta (sí, no o ambivalente), la frase que responde y la frase que es contexto. La
  misma entrevista se escribió en varios formatos de transcripción: cinco la de estudiantes y dos la de docentes.
- **Resultado esperado.** La postura y la frase de la clave. Para que la clave no dependiera solo de quien construyó
  el sistema, la investigadora anotó las 32 respuestas por su cuenta, sin ver la del autor (Y.4.7).
- **Dónde.** `tools/formatos/corpus_entrevistas.py` y `corpus_docentes.py` → `tools/formatos/corpus/`; la clave está
  en `referencia.json` de cada carpeta.
<!-- fuente: tools/formatos/corpus_entrevistas.py y corpus_docentes.py (docstrings, PREGUNTAS, RESPUESTAS); carpetas corpus/entrevistas (I01–I05) y corpus/entrevistas_docentes (D01–D02); tools/formatos/anotacion/anotacion_para_llenar.xlsx -->

**Copias con errores inyectados y la verdad de cada error (24 oct, 2 nov y 7 nov).**
- **Qué se quería probar.** Cuántos errores reales detecta y corrige la limpieza, y cuáles no, en un instrumento
  completo (las pruebas automatizadas lo comprueban regla por regla en archivos pequeños).
- **Cómo se construyó.** Se toma un instrumento sin errores y se le inyecta una cantidad conocida de cada error, con
  semilla fija y cada uno en una fila o un turno distinto. Junto al archivo se guarda un JSON con la **verdad**: qué
  se inyectó, dónde, y qué debería quedar después de limpiar. El archivo original sin cambios sirve de **control**.
  - **24 oct.** enc_11 (duplicados, valores fuera de escala, «No sé», columnas de plataforma…) y pru_01 (respuestas
    múltiples, ilegibles, ID repetido…).
  - **2 nov.** Tres archivos con errores que la limpieza **todavía no contemplaba**, elegidos de lo que suele traer
    un instrumento real: enc_06 (números escritos de otra forma, sinónimos, filas corridas…), pru_03 (letras con
    signo, alumnos repetidos con otro ID…; instrumento 130) y ent_11. ent_11 es una entrevista de una participante
    sobre salud mental, escrita para esta prueba, con una versión con ruido contemplado (instrumento 129) y otra con
    ruido no contemplado (131). pru_03 tiene también una versión con errores contemplados.
  - **7 nov.** ent_02, una entrevista generada con 30 participantes que no se había usado, con 89 errores típicos de
    transcripción.
- **Resultado esperado.** Cada error de la verdad: detectado y corregido, o dejado como estaba si la regla así lo
  decide.
- **Dónde.** `tools/limpieza/` (`inyectar_errores.py`, `ensuciar_*.py`, `medir_limpieza_entrevista.py`) →
  `evidencias/limpieza_2026-10-24/`, `storage/instrumentos_sinteticos/*/*_ruido_*.json` y
  `evidencias/limpieza_2026-11-07/`. Los resultados están en Y.2.2.
<!-- fuente: tools/limpieza/inyectar_errores.py, ensuciar_enc_06_no_contemplado.py, ensuciar_pru_03.py, ensuciar_ent_11.py, ensuciar_ent_11_no_contemplado.py y medir_limpieza_entrevista.py (docstrings); storage/instrumentos_sinteticos/entrevistas/ent_11_metadata.json; commit 339e9fb -->

**Tabla P.2.** Datos usados en cada prueba, en el orden de este capítulo.

| Prueba | Datos | Por qué esos | Dónde se reporta |
|---|---|---|---|
| Flujo completo por tipo de instrumento | Generador: enc_09, enc_10_turno, enc_11, pru_01, pru_04, ent_01 | Volumen y variedad de tipos de pregunta | Y.2.1 |
| Limpieza: limpio frente a ruidoso | Errores inyectados: enc_11, pru_01, ent_02; y enc_06, pru_03 y ent_11 para lo no contemplado | Cada error tiene su verdad | Y.2.2 |
| Robustez ante formatos | Variantes de formato (13 formatos y 3 variantes sin secciones) | Mismas respuestas, así que las cifras deben coincidir | Y.3.2 |
| Dimensiones sugeridas | enc_10_turno (estructura conocida) + generador (enc_04 y enc_01, solo los CSV, fuera del sistema) | Se compara con dimensiones que ya se conocen | Y.3.3 |
| Chat: banco y regresión | Generador (enc_09, enc_11, ent_01) + enc_10_turno + encuesta de 2000 de la investigadora (127) | enc_10_turno aporta las preguntas por grupo con cifra esperada | Y.4.3, Y.4.8 |
| Análisis de respuestas de entrevista | Entrevistas con clave (estudiantes y docentes) | Traen la clave de respuestas | Y.4.7 |
| Comparación de modelos y chat con instrumentos nuevos | 127; errores inyectados: pru_03 (130) y ent_11 (129 y 131) | 127 se usó durante el desarrollo; 129–131 el chat no los había visto | Y.4.4, Y.4.5, Y.5 |
| Evaluación final del chat (baterías de la investigadora) | 127, 130 y 129; control: enc_09 (61), ent_01 (60) y pru_06 (133) | Las baterías las escribió la investigadora sobre sus instrumentos; el control no se usó para diseñar | Y.4.6 |
| Reglas de limpieza, una por una | Archivos de las pruebas automatizadas | Un caso por regla | Desarrollo X.12 |

El inventario de todos los instrumentos que pasaron por el sistema, incluidos los que se borraron, está en el
Anexo A.


---

## Y.2 Limpieza ★

### Y.2.1 Flujo completo por tipo de instrumento

**Qué se comprueba.** Que un instrumento de cada tipo, generado sin errores, recorra los 7 pasos del asistente hasta
quedar publicado y consultable, con sus tipos de pregunta reconocidos y con las cifras del chat iguales a las del
CSV.

**Tabla P.3.** Flujo completo con instrumentos del generador (Desarrollo X.6).

| Tipo | Instrumento | Tipos reconocidos | Resultado |
|---|---|---|---|
| Encuesta | enc_10_turno (59): 60 respondentes, 8 ítems Likert | Likert en 2 dimensiones; contexto (turno, género, semestre) | 480 respuestas, 145 chunks; «4 de 30 del turno vespertino de acuerdo con p04», igual que el valor esperado |
| Encuesta | enc_09 (61): 160 respondentes | Likert, opción múltiple, Sí/No, numérica | Filtros de 88, 37 y 23 de 160, iguales a SQL |
| Encuesta | enc_11 (109): 160 respondentes | Los seis tipos: Likert, opción múltiple, Sí/No, escala numérica, selección múltiple, jerarquización y abierta | 4160 respuestas; 44 de 160 reprobados (27.5 %) y 33 de 160 con beca (20.6 %), iguales al CSV |
| Prueba | pru_04: 90 alumnos | 6 de opción múltiple, 8 de escala, 4 Sí/No | Pasó de punta a punta, sin calificar |
| Prueba | pru_01: 100 alumnos | Opción múltiple, V/F y respuesta corta por puntos | 2500 respuestas |
| Entrevista | ent_01 (60): 40 participantes en un archivo | 12 preguntas de la guía; líneas de perfil como contexto | 40 entrevistados × 12 preguntas = 480 respuestas, 521 chunks |
<!-- fuente: registro 16–18 oct y 22 oct; tt_rag.respuesta_interpretada (2500 filas del 55, 4160 del 109); evidencias/datos_sinteticos_2026-10-22/procesar_enc_11.log y procesar_enc_11_v2.log; salidas de probar_filtro.py y psql (18 oct) -->

Las fallas que aparecieron en estas rondas (bloques Likert sin reconocer, columnas de cantidad tomadas como
calificación, una escala 1–5 con pocos cincos tomada como 1–4, 40 entrevistas fusionadas en un solo hablante,
columnas de contexto propuestas como preguntas) quedaron como reglas de la limpieza (Desarrollo X.5 y X.7.2). Las
cifras de limpieza de cada instrumento están en Resultados.

**[Figura propuesta P.1: fase asistida de la limpieza (tarjetas con la opción sugerida). Figura propuesta P.2:
confirmación de roles de hablantes de ent_01. Figura propuesta P.3: pestaña «Estadística» de una prueba.]**

### Y.2.2 Instrumento limpio frente a instrumento con ruido

**Qué se comprueba.** Qué hace la limpieza con el mismo instrumento sin errores y con errores conocidos, en los tres
tipos.

**Método.** De cada tipo se toma un instrumento limpio (el **control**) y una copia con errores inyectados con semilla
fija, cada uno en una fila o un turno distinto, y con un JSON que guarda la **verdad**: qué se inyectó, dónde y qué
debería quedar. Los dos se limpian con las decisiones sugeridas. Lo que se detecta de más en la copia se compara con
la verdad, para no contar las anomalías que ya traía el original (por ejemplo, encuestados en línea recta). Hay dos
clases de ruido:
- **Contemplado:** errores que la limpieza está diseñada para atender.
- **No contemplado:** errores frecuentes en instrumentos reales que no se habían previsto. Se midieron con la versión
  del 2 nov y con la vigente (7 nov), después de agregar reglas el 5 nov.
<!-- fuente: tools/limpieza/inyectar_errores.py, verificar_limpieza.py, medir_limpieza_entrevista.py, remedir_no_contemplado.py; tools/limpieza/ensuciar_*.py -->

**Tabla P.4.** La limpieza por tipo de instrumento y condición.

| Tipo | Limpio (control) | Ruido contemplado | Ruido no contemplado: 2 nov → vigente | Lo que no resuelve |
|---|---|---|---|---|
| Encuesta | enc_11: ningún dato correcto marcado como error (precisión 1.00) | enc_11, 27 errores: 17 → **27** corregidos (antes y después de las correcciones del 24 oct) | enc_06, 33 errores: 2 → **28** | Sinónimos de una opción (0/3), un «Otro: …» (2/3), casi duplicados |
| Prueba | pru_01: precisión 1.00 | pru_01, 20 errores: 18 → **20**; pru_03, 8 de 8 | pru_03, 21 errores: 0 → **15** | Número en lugar de letra (0/4), «0» como no respuesta, copia con otro ID |
| Entrevista | ent_02: los 600 turnos salen iguales a lo esperado; ninguna palabra perdida ni sobrante | ent_02, 89 errores: **89** corregidos | ent_11, 26 errores: 1 → **16** | Muletillas fuera de la lista (0/4), arranques en falso (0/2), errores del reconocimiento de voz (0/3) |
<!-- fuente: evidencias/limpieza_2026-10-24/RESULTADO.md, enc_11_verdad.json, pru_01_verdad.json, *_resultado.json (instrumentos 115–118 antes y 119–122 después); evidencias/limpieza_2026-11-07/ent_02_control.txt, ent_02_con_errores.txt, ent_02_verdad.json, ent_02_resultado.json y no_contemplado_hoy.json; storage/instrumentos_sinteticos/*/*_ruido_no_contemplado.json (resultado_medido del 2 nov) y pruebas/pru_03_ruido_contemplado.json -->

**Detalle de la encuesta y la prueba con ruido contemplado** (Tabla P.5). La primera corrida encontró tres causas de
errores no detectados; después de corregirlas se repitió con los mismos archivos.

**Tabla P.5.** Detección por tipo de error inyectado, antes y después de las correcciones del 24 oct.

| Instrumento | Error | Inyectados | Antes | Después |
|---|---|---|---|---|
| enc_11 | Duplicados | 5 | 0 | 5 |
| enc_11 | Fuera de escala | 6 | 6 | 6 |
| enc_11 | «No sé / No aplica» en escala numérica | 4 | 0 | 4 |
| enc_11 | Columna muy incompleta | 1 | 1 | 1 |
| enc_11 | Encuestados casi sin responder | 4 | 4 | 4 |
| enc_11 | Línea recta | 5 | 5 | 5 |
| enc_11 | Columnas de plataforma | 2 | 1 | 2 |
| pru_01 | Respuestas múltiples / ilegibles / inválidas | 6 / 5 / 4 | 6 / 5 / 4 | 6 / 5 / 4 |
| pru_01 | ID repetido | 3 | 3 | 3 |
| pru_01 | Filas vacías | 2 | 0 | 2 |
| **Total** | | **47** | **35 (recall 0.74)** | **47 (recall 1.00)** |

Las tres causas: una «Dirección IP» en español hacía única cada fila y escondía los duplicados; «No sé» en una escala
numérica no se reportaba; y el lector de CSV perdía las filas de solo separadores. Quedaron como decisiones en
Desarrollo X.7.2. La entrevista se midió así error por error (Tabla D.21g de Desarrollo): marcas de tiempo,
encabezados, palabras partidas, caracteres invisibles, acentos rotos, etiquetas inconsistentes y anotaciones del
transcriptor se corrigieron todas, y las 6 muletillas se detectaron y conservaron, como se sugiere.

**Lectura.**
- **Con un instrumento limpio, la limpieza no cambia nada indebido** en ningún tipo: precisión 1.00 en encuesta y
  prueba, y ningún turno alterado en la entrevista.
- **Con el ruido que contempla, lo corrige todo** en los tres tipos (47 de 47 y 89 de 89), sobre archivos que no se
  usaron para ajustarla (ent_02 no se había usado antes).
- **Con ruido no contemplado, la versión vigente pasa de 3 a 59 de 80 errores.** Antes, la mayoría pasaba sin aviso o
  se anulaba un dato que sí venía bien: «4,5» se quedaba como texto en una columna numérica y «cinco» se anulaba como
  fuera de escala; en la prueba, el reactivo que nadie respondió desaparecía y un encabezado repetido se contaba como
  alumno. Estos tres archivos guiaron las reglas del 5 nov, así que su resultado dice qué se cubrió, no cuánto
  generaliza; la entrevista ent_02 muestra que las reglas funcionan en un archivo distinto de los que las motivaron.
- **Lo que no resuelve en entrevistas no se corrige a propósito**: corregirlo cambiaría las palabras del
  participante. El catálogo completo, error por error, está en Desarrollo X.7.2 (Tablas D.21e a D.21g).

### Y.2.3 Una encuesta con errores de captura reales (28 oct)

**Qué se comprueba.** Qué hace la limpieza con un archivo de tamaño real (la encuesta de 2000 respondentes de la
investigadora, instrumento 127) que trae a propósito errores típicos de captura y de exportación. Se compara la
limpieza antes y después de los ajustes que este archivo motivó.

**Tabla P.6.** La encuesta de 2000 respondentes con la limpieza anterior y con la vigente.

| Situación del archivo | Limpieza anterior | Limpieza vigente | Casos en el archivo |
|---|---|---|---|
| Respuestas con signos de borde («Nunca.», «Algunas veces.») | Salían como valores «fuera de rango» | Coinciden con la escala | 19 |
| Respuestas que solo difieren en grafía («PRESENCIAL», «Presencial.») | Se unificaban sin aviso | Se unifican y se reportan con fila, antes y después | 1,303 celdas |
| Espacios al inicio o al final | Se quitaban sin contarse | Se reportan con su fila | 1,019 celdas |
| «Ninguno» marcado junto con otras opciones | Pasaba sin aviso | Tarjeta de selección contradictoria | 589 |
| «Totalmente de acuerdo» escrito en escalas que se respondieron con números | Pasaba sin aviso; el documento final avisó de 204 respuestas sin interpretar | Una tarjeta por valor, con su motivo y la opción de cambiarlo por su equivalente | 204 |
| Opciones con coma en su texto («Sí, y no lo aprobé») | La pregunta se tomaba como selección múltiple y ningún filtro encontraba a nadie | Opción única: la selección múltiple se reconoce por combinación | 1 pregunta |
| Ubicación de cada hallazgo | Solo las primeras 20 filas | «Ver dónde» con todas las filas | — |
<!-- fuente: cleaning-service/services/configuracion.py (normalizar_texto, _BORDES); services/motores/encuestas/universales.py; motor.py (_homologar, _contradictorias, _grupos_fuera, _por_que_fuera); tipos.py (_separados); tests/test_limpieza_visible.py; instrumento 126 (Encuesta2_Simulada_2000_SUCIA.csv) y avisos del documento final del 127 (28 oct) -->

**Lectura.** Con la limpieza anterior, buena parte de la suciedad se resolvía en silencio y la investigadora
encontraba después, en el documento final, avisos que no había visto. Con la vigente, todo lo que cambia queda a la
vista con su ubicación y cada valor dudoso tiene su tarjeta.

### Y.2.4 Pruebas de la investigadora

[PENDIENTE: prueba de la investigadora] Instrumentos propios con distintos tipos de pregunta y errores introducidos a
propósito, siguiendo la tabla de errores de `markdowns/GUIA_PRUEBAS.md` (sección 3). Por cada archivo se registra: el
error metido, si apareció su tarjeta, la decisión tomada y las medidas de «Estadística» antes y después.

---

## Y.3 Estandarización ★

### Y.3.1 Chunks y recuperación

**Qué se comprueba.** Que los chunks quepan en lo que lee el modelo de *embeddings* (128 *tokens*) y que la búsqueda
encuentre el fragmento correcto. Se comparan tres versiones de los chunks con las mismas preguntas.

**Tabla P.7.** Chunks que pasan del límite de 128 *tokens* con cada forma de medir (reindexación del 7 nov).

| Instrumento | Ventana de 450 caracteres | Medido en *tokens* (vigente) |
|---|---|---|
| Encuesta de 2000 respondentes (127) | 1,094 de 6,667 | 0 de 7,059 |
| Prueba de 97 alumnos (130) | 385 de 465 | 0 de 1,337 |
| Encuesta de control (61) | 149 de 690 | 0 de 818 |
| Otras dos encuestas (59 y 109) | 157 de 995 | 0 de 1,238 |
| Tres entrevistas (60, 129 y 131) | 0 | 0 |
<!-- fuente: evidencias/chunks_2026-11-07/README.md (tabla de truncados; tools/rag/contar_truncados.py) -->

**Tabla P.8.** *Hit rate*@3 de la recuperación: proporción de preguntas cuyo fragmento correcto queda entre los 3
primeros. 43 preguntas de las baterías de la investigadora y 9 de control, cada una con su fragmento correcto; modelo
de *embeddings* del chat, sin umbrales.

| Preguntas | 450 caracteres, con chunks de personas | En *tokens*, sin chunks de personas | Con ficha y temas de la entrevista (vigente) |
|---|---|---|---|
| Las tres baterías | 0.61 | 0.79 | 0.84 |
| Encuesta | 0.25 | 0.69 | 0.69 |
| Prueba | 0.82 | 0.91 | 0.91 |
| Entrevista | 0.81 | 0.81 | 0.94 |
| Set de control | 0.89 | 1.00 | 1.00 |
<!-- fuente: tools/rag/recuperacion_oro.json y medir_recuperacion.py; evidencias/chunks_2026-11-07/README.md; evidencias/chat_2026-11-08_final/recuperacion.json -->

**Métricas de recuperación de la versión vigente.** Siguen el método clásico de evaluación de recuperación de
información: para cada pregunta se fija de antemano qué fragmento del instrumento es el relevante (**juicio de
relevancia**, `tools/rag/recuperacion_oro.json`) y se mide en qué lugar lo pone la búsqueda. *Hit*@k es la proporción
de preguntas cuyo fragmento relevante queda entre los k primeros; el MRR (*mean reciprocal rank*) es el promedio de
1/posición del primer fragmento relevante (1 = siempre en primer lugar). La búsqueda trae 8 fragmentos por
instrumento, así que *hit*@8 es la proporción de preguntas en que el fragmento relevante llega al modelo.

**Tabla P.8a.** *Hit*@k y MRR de la versión vigente, sin y con el filtro de chunks de personas que usa el chat.

| Preguntas | n | Filtro | *Hit*@1 | *Hit*@3 | *Hit*@5 | *Hit*@8 | MRR |
|---|---|---|---|---|---|---|---|
| Baterías | 43 | Sin filtro | 0.61 | 0.70 | 0.70 | 0.74 | 0.65 |
| Baterías | 43 | Con filtro (vigente) | **0.74** | **0.84** | **0.86** | **0.95** | **0.80** |
| — encuesta (127) | 16 | Con filtro | 0.63 | 0.69 | 0.75 | 0.88 | 0.69 |
| — prueba (130) | 11 | Con filtro | 0.82 | 0.91 | 0.91 | 1.00 | 0.86 |
| — entrevista (129) | 16 | Con filtro | 0.81 | 0.94 | 0.94 | 1.00 | 0.88 |
| Set de control (61 y 60) | 9 | Sin filtro | 0.78 | 1.00 | 1.00 | 1.00 | 0.87 |
| Set de control (61 y 60) | 9 | Con filtro (vigente) | **0.89** | **1.00** | **1.00** | **1.00** | **0.93** |
<!-- fuente: evidencias/chat_2026-11-08_final/recuperacion.json (tools/rag/medir_recuperacion.py, 8 nov) -->

Los juicios de relevancia los fijó el autor. Para que no dependan de una sola persona, la investigadora los marca por
separado, sin ver los del autor (`tools/rag/relevancia/juicios_relevancia_para_llenar.xlsx`), y se mide el acuerdo
con la kappa de Cohen (`tools/rag/relevancia/comparar.py`). [PENDIENTE: acuerdo entre los dos juicios y, si
difieren, *hit*@k y MRR con los juicios de la investigadora.]

**Búsqueda de elemento conocido** (*known-item search*). Para medir la búsqueda sin ningún juicio humano, cada
pregunta o reactivo de los cinco instrumentos se usó como consulta, y se midió en qué lugar aparece un fragmento de
esa misma pregunta; la respuesta correcta la da el propio instrumento. Se probaron dos variantes de la consulta: el
texto completo de la pregunta y solo sus palabras con contenido, sin signos ni palabras vacías, para que no sea una
copia literal del fragmento (`tools/rag/known_item.py`; mismo modelo, colección y filtro que el chat).

**Tabla P.8b.** Búsqueda de elemento conocido (84 preguntas y reactivos, versión vigente).

| Instrumentos | n | Consulta | *Hit*@1 | *Hit*@3 | MRR |
|---|---|---|---|---|---|
| Todos | 84 | Texto completo | 0.98 | 1.00 | 0.99 |
| Todos | 84 | Palabras con contenido | 0.98 | 1.00 | 0.99 |
| — encuestas (127 y 61) | 38 | Texto completo | 0.95 | 1.00 | 0.97 |
| — pruebas (130) | 22 | Texto completo | 1.00 | 1.00 | 1.00 |
| — entrevistas (129 y 60) | 24 | Texto completo | 1.00 | 1.00 | 1.00 |
<!-- fuente: evidencias/known_item_2026-11-09/consultas.json y resultado.json (9 nov) -->

Las 4 consultas que no quedaron primeras quedaron segundas: dos detrás del fragmento de un KPI que usa las mismas
palabras, y dos porque la encuesta 61 tiene dos preguntas casi iguales (las horas de estudio, en número y en rangos).
Esta prueba es más fácil que las preguntas reales, porque la consulta repite el enunciado; muestra que cada pregunta
del instrumento se puede encontrar y que la búsqueda distingue unas preguntas de otras. La dificultad real está en
las preguntas de los usuarios, que no repiten el enunciado (Tabla P.8a).

**Lectura.** Con la ventana de caracteres, hasta 83 % de los chunks de una prueba se embebían truncados, sin aviso.
Medir en *tokens* y dejar fuera de la búsqueda los chunks de cada persona (que en la encuesta de 2000 eran unos 6,600
y llenaban los primeros lugares) subió el *hit rate* de las baterías de 0.61 a 0.79; la ficha con el encabezado de la
transcripción y los temas de cada intercambio, a 0.84. En la encuesta, la búsqueda sigue siendo la parte débil
(0.69): muchas preguntas se parecen entre sí.

### Y.3.2 Robustez ante formatos de encuesta

**Qué se comprueba.** Que la misma encuesta dé las mismas cifras en cualquier formato que el sistema acepta, y que los
formatos que no puede leer bien se rechacen con su motivo. Se tomó enc_10_turno (60 respondentes, 8 ítems Likert en 2
dimensiones, resultado conocido) y se escribió con exactamente las mismas respuestas en 13 formatos y 3 variantes sin
secciones (`tools/formatos/generar_corpus.py`).

**Criterio** (`tools/formatos/verificar_formatos.py`). Una variante que debe rechazarse pasa si la subida responde 422
con el motivo esperado. Una aceptada recorre los 7 pasos y pasa 14 comprobaciones: la ingesta al RAG, 8 preguntas con
el texto del original, 2 dimensiones con α y 9 preguntas al chat con cifras exactas (13.3 %, 4 de 30, R002…), hechos
clave en la redacción y la decisión de dominio esperada.

**Tabla P.9.** Formatos de encuesta y resultado con la versión final.

| Clave | Formato | Nivel esperado | Resultado |
|---|---|---|---|
| E01 | Con secciones; encabezados con prefijo de sección | Ideal | Pasa |
| E02 | Google Forms: marca temporal y texto completo de la pregunta | Ideal | Pasa |
| E03 | Sin secciones; texto de la pregunta | Aceptado | Pasa |
| E04 | Sin secciones; encabezados con prefijo | Aceptado | Pasa |
| E05 | Sin secciones; códigos P1…P8 con original | Aceptado | Pasa |
| E06 | Google Forms con cuadrícula «Instrucción [afirmación]» | Ideal | Pasa |
| E07 | Exporte de Qualtrics (3 filas de encabezado, IP y ubicación) | Aceptado | Pasa |
| E08 | Exporte de LimeSurvey (códigos `G01Q01…`, columnas de sistema) | Aceptado | Pasa |
| E09 | XLSX sin secciones | Ideal | Pasa |
| E10 | CSV con «;» y BOM UTF-8 | Ideal | Pasa |
| E11 | Códigos sin original | Rechazado | 422 con su motivo |
| E12 | Formato largo | Rechazado | 422 con su motivo |
| E13 | Sin fila de encabezados | Rechazado | 422 con su motivo |
<!-- fuente: tools/formatos/corpus/encuestas/variantes.json; evidencias/formatos_2026-10-21/encuestas.md y encuestas_final.log (143/143 en E01–E10; instrumentos 84–93) -->

En total, 143 de 143 comprobaciones; las variantes sin prefijos (E03, E05, E06, E09) recuperaron las 2 dimensiones
con el α esperado (0.87 y 0.83) gracias a las dimensiones sugeridas (Y.3.3).

**Encuesta sin secciones, antes y después de los ajustes del 20–22 oct.** Las tres variantes sin secciones son las
que más fallaban con la versión anterior (Tabla P.10).

**Tabla P.10.** Encuesta sin secciones: preguntas calculadas correctas (de 6) y respuesta a «¿qué evalúa la encuesta?».

| Variante | Versión anterior | Versión vigente |
|---|---|---|
| A, encabezados con prefijo (`Evaluación_item1…`) | 1/6; «qué evalúa» parcial | 6/6; describe el contenido |
| B, texto de la pregunta como encabezado | 6/6; parcial | 6/6; describe el contenido |
| C, códigos `P1…P8` | 1/6; describe los KPIs | 6/6; describe el contenido |
<!-- fuente: evidencias/encuesta_sin_secciones_2026-10-20/RESULTADO.md, comparacion_antes.json, comparacion_final.json (instrumentos 64–74) -->

Con la versión anterior, los encabezados en código sin secciones no se emparejaban con las preguntas del original
(«R017 no tiene respuesta registrada») y la ficha no decía qué preguntaba el instrumento. Las 19 preguntas de
referencia de los instrumentos ya publicados dieron la misma decisión que antes (19/19). Las transcripciones de
entrevista en distintos formatos se prueban en Y.4.7; las pruebas estandarizadas ya llegan estructuradas.

### Y.3.3 Dimensiones sugeridas

**Qué se comprueba.** Que, sin secciones ni prefijos, la limpieza recupere las dimensiones de encuestas cuya
estructura se conoce. Se compararon dos criterios para el número de grupos.

**Tabla P.11.** Dimensiones recuperadas por cada criterio.

| Encuesta | Dimensiones reales | Horn (percentil 95) | Kaiser (λ > 1) | Grupos con Kaiser |
|---|---|---|---|---|
| enc_10_turno | 2 (4 + 4 ítems) | 2 | 2 | Las 2 dimensiones, puras |
| enc_04 (MSLQ) | 8 subescalas | 5 (junta cuatro subescalas en un grupo) | 8 | Las 8 subescalas, puras |
| enc_01 (IEAE) | 5 detectables (dos dimensiones comparten nombre recortado) | 2 | 5 | 5 grupos; las dos de nombre igual salen separadas (3 + 3) |
<!-- fuente: registro 21 oct (comparación sobre los CSV de storage/instrumentos_sinteticos/encuestas) -->

Se adoptó Kaiser: Horn subestima el número de dimensiones cuando hay un factor general fuerte, como en estos datos.

### Y.3.4 Asociación de KPIs: un solo texto frente a unidades del perfil

**Qué se comprueba.** Si comparar el KPI con cada pregunta del instrumento (método vigente) mejora sobre comparar con
un solo texto del instrumento (método anterior). `services/analysis-service/scripts/comparar_kpis.py` calcula, sin
escribir nada, el top 5 de cada método, cuántos coinciden, la separación entre el 1.º y el 5.º y la distribución de
similitudes pregunta–KPI. Se ejecutó el 16 oct sobre dos encuestas.

**Tabla P.12.** Salida de `comparar_kpis` (16 oct, catálogo de KPIs anterior).

| Medida | Escala RAU (instrumento 39) | MSLQ-SF (instrumento 22) |
|---|---|---|
| Longitud del texto único (método anterior) | 2,643 caracteres, 811 *tokens* | 4,651 caracteres, 1,297 *tokens* |
| Parte que lee el modelo | 128 *tokens* | 128 *tokens* |
| Unidades de pregunta (método vigente) | 34 | 50 |
| Similitud pregunta–KPI: mediana / máximo | 0.279 / 0.604 | 0.186 / 0.582 |
| Pares ≥ 0.35 / ≥ 0.45 | 24.6 % / 7.7 % | 3.5 % / 0.8 % |
| Coincidencia en el top 5 | 4 de 5 | 2 de 5 (umbral 0.35); 0 de 5 (umbral 0.45) |
| Separación 1.º–5.º (anterior / vigente) | 0.062 / 0.042 | 0.037 / 0.022 |
<!-- fuente: tesis/comparar_kpis_salida.txt (copia de la salida en el registro 16 oct 01:05–01:06) -->

**Lectura.**
1. El método anterior no veía las preguntas: el modelo truncaba el texto en 128 *tokens* y las propuestas salían casi
   solo de los metadatos. El vigente cita preguntas concretas como evidencia: en la RAU, «Puntajes en Pruebas
   Estandarizadas de Referencia» quedó sustentado por «Mis calificaciones reflejan el esfuerzo que dedico al estudio»
   (0.568) y otras dos preguntas.
2. En el MSLQ-SF el vigente salió peor, porque su perfil venía de encabezados en código (`Autoeficacia_item3`,
   `promedio_gpa`); desde entonces el perfil se construye desde el instrumento original y sin columnas de contexto.
3. Con umbral 0.35, el 24.6 % de los pares de la RAU contaban como evidencia y la cobertura no discriminaba; con 0.45,
   el 7.7 %.
4. En ambos métodos los puntajes quedan juntos (separación ≤ 0.062), porque los KPIs del catálogo son institucionales y
   algunos genéricos se parecen a casi todo.

**Salvedad.** La comparación se hizo con el catálogo de KPIs anterior y con dos instrumentos (39 y 22) que ya no están
en la base; el 17 oct se adoptó el catálogo de la rama `PA` (55 KPIs) y no se repitió. Los KPIs propuestos con el
catálogo vigente están en Resultados.

### Y.3.5 Pruebas de la investigadora

[PENDIENTE: prueba de la investigadora] Con cada instrumento propio, revisar en «Dublin Core» y «Metadatos del tipo»
el título, la población, las secciones o dimensiones; en «KPIs sugeridos», el puntaje, la evidencia y la
justificación; y después de guardar, la vista rápida del catálogo.

---

## Y.4 El chat ★

### Y.4.1 Conjuntos de prueba y medidas

El chat se midió con cinco conjuntos de preguntas, cada uno con su resultado esperado calculado sin usar el sistema
(Tabla P.13). Cada conjunto se corrió con la versión anterior y con la nueva, sin caché (`RAG_CACHE_HORAS=0`).

**Tabla P.13.** Conjuntos de prueba del chat.

| Conjunto | Preguntas | Instrumentos | Referencia | Sección |
|---|---|---|---|---|
| Banco con respuesta verificada | 55, cada una con 2 paráfrasis, 3 veces | 59, 60, 61, 109 y pruebas | pandas sobre el CSV; anotación de las entrevistas | Y.4.8 |
| Regresión del rediseño | 28 | 127, 59, 61, 109 y 60 | Plan y cifras esperados, calculados con código independiente del chat | Y.4.3 |
| Casos de la investigadora | 14 casos (28 turnos) en el 127; 20 casos (35 turnos) en la prueba 130 y la entrevista 129 | 127, 130, 129 | Cifras calculadas de la base; criterios para lo interpretativo; calificación humana | Y.4.4, Y.5 |
| Baterías de la investigadora | 79 casos | 127, 130, 129 | Lo que la respuesta **debe** contener | Y.4.6 |
| Set de control | 24 casos | 61, 60 y 133, ajenos al diseño | Igual que las baterías | Y.4.6 |
<!-- fuente: tools/rag/construir_banco.py; tools/rag/regresion/generar_banco.py y banco_regresion.json; services/visualization-service/scripts/modelos/generar_casos.py y generar_casos_fase6.py; tools/rag/baterias_chat.json -->

**Medidas.**
- **Exactitud:** cifras y textos esperados en la respuesta; o «cumple», «parcial» o «no» contra el «Debe».
- **Calificación humana:** 0 mal, 1 parcial, 2 bien (la investigadora, en el panel del chat).
- **Indicadores sin modelo:** intención correcta, caídas a plantilla, cifras con respaldo en el contexto, IDs
  inventados y tiempo por etapa (Desarrollo X.10.8).
- **Métricas del juez:** fidelidad, relevancia y precisión del contexto; se reportan como aproximadas, porque ningún
  juez de 3–4B alcanzó el acuerdo con la calificación humana (Y.5.2).

### Y.4.2 Cómo cambió la técnica en cada versión

El chat pasó por seis versiones (Desarrollo X.9, Tabla D.23b). Esta sección compara, versión por versión, las cinco
técnicas que deciden la calidad de una respuesta:
- qué recibe el modelo;
- cómo se interpreta la pregunta;
- cómo se arman los chunks y se recupera;
- cómo se redacta y se verifica;
- cómo se mide.

Cada cambio nació de una falla observada y se midió sobre el mismo conjunto (Tabla P.14f).

#### Qué recibe el modelo para redactar

El modelo de lenguaje no ve la base de datos: solo lee el texto que el sistema le arma. La forma de ese texto cambió
más que ninguna otra cosa.

**Tabla P.14a.** Lo que recibe el modelo para redactar, por versión.

| Versión | Qué recibe | Falla que motivó el cambio | Efecto observado |
|---|---|---|---|
| 4 oct | Una instrucción al inicio del mensaje («responde USANDO ÚNICAMENTE la información del CONTEXTO») y los fragmentos más parecidos | Primera versión | Respuestas sin citar las fuentes |
| 16 oct (`PA`) | Las reglas en el campo `system` de Ollama (8 reglas numeradas) y los fragmentos en el mensaje | El modelo agregaba frases contradictorias y no citaba en el formato pedido | Cita en el formato pedido |
| 17–18 oct | Los fragmentos entre `<datos>…</datos>` (son datos, nunca instrucciones), un **RESULTADO CALCULADO** por el enrutador, el glosario y la ayuda (12 reglas) | Un 23.3 % inventado en un porcentaje por grupo; citas inventadas; el modelo negaba un resultado que sí tenía | El porcentaje correcto (13.3 %) y ninguna negativa del resultado de un filtro |
| 28 oct | Solo el RESULTADO CALCULADO y una instrucción de formato por intención; las tablas se anexan del cálculo, el modelo no las escribe | El modelo tomó el porcentaje de toda la muestra de un fragmento, e inventó una tabla con respuestas falsas | Cifras correctas en 100 % de la regresión (Tabla P.16) |
| 4–5 nov | Además, un **TEXTO RECUPERADO** del mismo instrumento (sin cifras en las intenciones numéricas) y la **CONVERSACIÓN PREVIA** (15 reglas, rol de analista de investigación) | Sin recuperación no podía explicar ni seguir el hilo | Interpreta lo que dijo la persona y relaciona el seguimiento (Tabla P.19) |
| 7–8 nov (vigente) | Una instrucción adicional según la forma de la pregunta («¿por qué?», opinión, «lo más…», pocas personas), dos capas al explicar un resultado y 20 reglas; sin el nombre de quien registró el instrumento | Comparaciones al revés, «diferencia significativa», porcentajes sin su número, el nombre de la autora atribuido a la participante | Baterías de 31 a 63 de 79 (Tabla P.21) |
<!-- fuente: git show 42bb731, 7e367f2, 6a1cb38, 1b04c3d, b62f7db, c42f42e, 9f86ff4, c1998ad, b8c7d7a:…/prompt.py; services/visualization-service/services/prompt.py (SISTEMA, construir) y consulta_planificada.py (FORMATO, formato_adicional); registro 17 oct 22:55 (humo_chat.py) -->

Así empezó el prompt (4 oct), y así es el mensaje que recibió el modelo para una pregunta de conteo en la versión
evaluada el 8 nov. El ejemplo es inventado y está abreviado:

```text
Eres un asistente de investigación educativa. Responde en español, de forma clara y concisa, USANDO ÚNICAMENTE la
información del CONTEXTO. Si el contexto no contiene la respuesta, dilo explícitamente y no inventes datos.
```

```text
[system] Eres un analista de investigación educativa universitaria… Reglas obligatorias: 1. Usa SOLO la información
del CONTEXTO… 10. Si hay un RESULTADO CALCULADO, es exacto: úsalo tal cual… 15. El RESULTADO CALCULADO da las cifras y
el TEXTO RECUPERADO explica de qué tratan; si dicen cosas distintas, manda el RESULTADO CALCULADO… 16. Cada porcentaje
va con su número de personas…

RESULTADO CALCULADO (exacto, no lo recalcules):
Cumplen la condición 84 de 300 respondentes (28.0 %).
Criterio: p02 «¿Con qué frecuencia asistes a tutorías?» = «Nunca»

TEXTO RECUPERADO (fragmentos del RAG más parecidos a la pregunta; úsalos para contextualizar e interpretar, las cifras
salen solo del RESULTADO CALCULADO):
[Fuente 1] Encuesta de ejemplo (encuesta)
<datos fuente="1">
- pregunta: Pregunta p02 (encuesta «Encuesta de ejemplo»): ¿Con qué frecuencia asistes a tutorías?
  Sección: Apoyo académico
  Opciones: Nunca; A veces; Siempre
</datos>

CONVERSACIÓN PREVIA (no es fuente):
Usuario: ¿qué preguntas tiene sobre tutorías?

FORMATO DE LA RESPUESTA: Responde en UNA o DOS oraciones con la cifra exacta, de cuántos y el porcentaje, y el
criterio aplicado. Nombra las opciones del criterio tal como aparecen, todas…

PREGUNTA: ¿cuántos nunca van a tutorías?
```
<!-- fuente: services/visualization-service/services/prompt.py (SISTEMA, construir); consulta_planificada.py (FORMATO); ejemplo armado con el catálogo inventado de interpretacion.py (_CATALOGO_EJEMPLO) -->

**Lectura.** La mejora no vino de pedirle más al modelo, sino de **separar lo que da cada fuente**: las cifras
llegan calculadas, el texto recuperado da el sentido y la conversación solo sirve para entender a qué se refiere la
pregunta. Las reglas del prompt pasaron de 3 líneas a 20 reglas, pero las que el modelo de 3–4B no cumplía (no cambiar
cifras, no negar el resultado) solo se garantizaron con verificaciones en código (Tabla P.14d).

#### Cómo se interpreta la pregunta

**Tabla P.14b.** Interpretación de la pregunta, por versión.

| Versión | Técnica | Falla que motivó el cambio | Medida |
|---|---|---|---|
| 10–16 oct | Ninguna: búsqueda por similitud y un umbral (0.35) | Con a lo más 8 fragmentos no se puede contar a todos los respondentes | — |
| 17–26 oct | **Reglas**: una expresión por intención (respondente, porcentaje por grupo, filtro, KPI…) y, si las reglas no hallan la condición, el modelo propone **solo la condición** en JSON, validada contra el catálogo; un clasificador con el modelo decide la zona gris de similitud | — | Banco: decisión de dominio 0.982; exactitud 31 de 45 (Tabla P.26) |
| 28 oct | **Plan JSON** escrito por el modelo con temperatura 0 y el JSON Schema en `format`: recibe instrucciones, ejemplos sobre un catálogo inventado, el **catálogo** de cada instrumento y los últimos 4 mensajes. El plan se **valida** contra el catálogo y se **ancla** a lo que la pregunta dice literalmente (IDs, números de pregunta, opciones) | Las reglas no reconocían formas nuevas de preguntar (Tabla P.15) | Plan completo correcto en 92 % de la regresión (Tabla P.16) |
| 4–5 nov | Además, el **tema de la respuesta anterior** (de `rag_log`) y los **3 fragmentos recuperados más parecidos** como pistas | Los seguimientos perdían el hilo; «la pregunta de la VPN» no se asociaba a su reactivo | La pregunta correcta en los seguimientos (Tabla P.19) |
| 7–8 nov (vigente) | El plan declara si la pregunta es nueva, continúa o profundiza la anterior; **reglas generales** después del modelo (posiciones de escala, opción escrita tal cual, «de ellos» como grupo anterior, erratas) | El modelo escribía `"[1, 2]"` por «1 o 2», elegía la opción equivocada u olvidaba el grupo | Planes válidos de 85.6 % a 92.2 %; el plan del modelo se usó sin cambios en 23 % de los turnos (Tabla P.21) |
<!-- fuente: services/visualization-service/services/enrutador.py, filtro_llm.py, interpretacion.py (SISTEMA, _EJEMPLOS, construir_prompt), catalogo.py (texto), plan_consulta.py, anclaje.py, seguimiento.py; evidencias citadas en las tablas -->

**El catálogo.** Es lo que le permite al modelo nombrar preguntas y opciones que existen. Cada instrumento se resume en
un bloque con sus preguntas (ID, tipo y opciones o escala), las variables de contexto y los KPIs. Si hay varios
instrumentos y el texto pasa de 4,500 caracteres, se recortan textos y opciones. El ejemplo que el modelo ve junto con
sus planes es inventado, para que no copie la respuesta de un instrumento de prueba:

```text
INSTRUMENTO 900 | encuesta | «Encuesta de ejemplo»
Respondentes: 300 (R001 a R300)
Contexto: Turno = Matutino, Vespertino
Contexto numérico: Edad (17–45)
Preguntas:
- p01 [likert] Los profesores explican con claridad → escala 1–5 (…); niveles baja 1/2; media 3; alta 4/5
- p02 [categorica] ¿Con qué frecuencia asistes a tutorías? → Nunca; A veces; Siempre
- p04 [numerica] ¿Cuántas horas trabajas a la semana?
KPIs: KPI-07 Satisfacción estudiantil

P: ¿cuántos nunca van a tutorías y han tomado algún curso de idiomas?
PLAN: {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "op": "=", "valor": "Nunca"},
       {"pregunta": "p03", "op": "=", "valor": ["Sí, y lo terminé", "Sí, pero lo dejé"]}]}
```
<!-- fuente: services/visualization-service/services/interpretacion.py (_CATALOGO_EJEMPLO, _EJEMPLOS); catalogo.py (Catalogo.texto) -->

**Lectura.** El paso de reglas a plan fue el cambio de mayor efecto (53.6 % a 96.4 % en la regresión): el modelo
entiende formas de preguntar que ninguna regla preveía, y el sistema conserva el control porque el plan solo puede
pedir operaciones programadas y se valida antes de ejecutarse. El costo es que un modelo de 3–4B se equivoca en
detalles del plan, y por eso creció la capa de reglas que lo corrige (Desarrollo X.9.2).

#### Chunks y recuperación

**Tabla P.14c.** Chunks y recuperación, por versión.

| Versión | De dónde salen y cómo se cortan | Falla que motivó el cambio | Medida |
|---|---|---|---|
| 4–10 oct | Del JSON técnico; 800 caracteres con solape de 150, por párrafo y oración | — | La mitad de cada chunk no influía en el vector: el modelo de *embeddings* lee unos 128 *tokens* |
| 16 oct (`PA`) | Del JSON técnico; 450 caracteres con solape de 80; la ficha esencial en el chunk 0 | La mitad de cada chunk no se embebía | En la auditoría del 17 oct, «¿qué opinan los estudiantes sobre la evaluación?» se respondió sin ninguna respuesta real: el JSON no trae lo que contestó cada persona |
| 17–22 oct | Del **documento final**: ficha, una pieza por pregunta, una o más por respondente (respuestas por su significado), una por intercambio de entrevista y una por KPI; listas por líneas completas, sin solape; la ficha dice «KPIs asociados: ninguno» cuando no hay, y trae «Aspectos que pregunta» en las encuestas sin secciones; la ficha llega completa a la redacción | El solape partía respuestas; el modelo atribuía a una encuesta los KPIs de otra y describía una encuesta sin secciones por sus KPIs | «¿Qué evalúa la encuesta?» se responde con su contenido (Tabla P.10) |
| 28 oct – 4 nov | Igual; las respuestas con plan **no consultaban** ChromaDB | — | 13 de 170 respuestas del 127 usaban la recuperación (Tabla P.18) |
| 5 nov | **RAG primero**: se busca antes de interpretar, en toda pregunta; si con el filtro nada pasa el umbral, entran los fragmentos más cercanos | El chat era «modelo + cálculo» | 60 % de respuestas con recuperación y luego todas |
| 7–8 nov (vigente) | Medidos en ***tokens*** (≤ 128); la definición de cada pregunta separada de sus resultados; sin los chunks de cada persona en la búsqueda; la ficha de la entrevista con el encabezado de la transcripción y los intercambios con sus temas | Hasta 83 % de los chunks de una prueba se truncaban sin aviso; los 6,600 chunks de personas llenaban los primeros lugares | *Hit rate*@3 de 0.61 a 0.84 en las baterías y de 0.89 a 1.00 en el control (Tablas P.7 y P.8) |
<!-- fuente: commits 42bb731, 7e367f2, 6a1cb38, 1b04c3d, eb17985, 310af4c; .agents/tasks/fullstack-rag/design.md:617; registro 17 oct 21:25 (auditoría); evidencias/encuesta_sin_secciones_2026-10-20/RESULTADO.md; evidencias/chunks_2026-11-07/README.md; tt_rag.rag_log.ruta 1290–1771 -->

Un ejemplo de la separación entre definición y resultados (7 nov), con la encuesta inventada del catálogo anterior.
A «¿cuántos caminan a la escuela?» se parece la definición, que trae la opción «Caminando», y no la distribución; por
eso van en piezas distintas:

```text
Pregunta p06 (encuesta «Encuesta de ejemplo»): ¿Cómo llegas a la escuela?
Sección: Traslado
Opciones: Transporte público; Auto o moto; Bicicleta; Caminando

Pregunta p06: ¿Cómo llegas a la escuela?
Respuestas válidas: 296; sin respuesta: 4
Distribución: Transporte público 47.6 % (n=141); Auto o moto 25.0 % (n=74); Bicicleta 8.1 % (n=24); Caminando 19.3 % (n=57)
```
<!-- fuente: services/storage-service/services/chunks_documento.py (_encuesta: parte «definicion» y «resultados»; _resumen_pregunta); ejemplo inventado -->

**Lectura.** Cambiar **la fuente** de los chunks (del JSON técnico al documento final con las respuestas
interpretadas) y **la unidad de medida** (de caracteres a *tokens*) mejoró más la recuperación que cualquier ajuste de
tamaño. Sacar de la búsqueda los chunks de cada persona fue lo que más subió el *hit rate* en la encuesta (de 0.25 a
0.69): lo de cada persona lo resuelve el cálculo.

#### Cómo se redacta y se verifica la respuesta

**Tabla P.14d.** Verificación de la redacción, por versión.

| Versión | Qué se revisa antes de mostrar la respuesta | Si falla | Falla que motivó el cambio |
|---|---|---|---|
| 17 oct | Que no cambie una cifra del resultado; se borran citas inventadas | Se muestra el resultado calculado | El modelo cambiaba cifras y negaba resultados pese a las reglas |
| 22 oct | Que no omita cifras del conteo; se borran corchetes que no son cita | Igual | «13.3 %» sin «4 de 30»; copiaba «[R017 en p04]» del ejemplo de una regla |
| 22–24 oct (retirada) | Un juez revisaba cada afirmación antes de mostrar | Igual | Tardaba 15–42 s y descartó 3 de 4 respuestas; se retiró |
| 28 oct | Además: que no niegue, no escriba tablas, no invente IDs y no omita «cuántos de cuántos» | Se **rehace una vez** con el motivo; si vuelve a fallar, el cálculo | Inventó «R017» en un hallazgo |
| 4 nov | Que no cite entre comillas una frase que no está en los datos | Igual | Citas atribuidas a otra pregunta |
| 7 nov | Que no compare al revés, no infiera causas ni significancia y no dé un porcentaje sin su número; acepta cifras deducibles (redondeos, diferencias) | Igual | Comentarios de la investigadora a respuestas mal calificadas |
| 8 nov (vigente) | Que no atribuya un porcentaje a otra opción, no omita opciones del criterio, no desordene un ranking y, en una prueba, no juzgue aciertos o desempeño | Igual | Afirmaciones falsas con cifras verdaderas en la corrida limpia |
| En el código, sin evaluar | En conteos, cruces y resúmenes, la primera oración la escribe el sistema; el modelo solo agrega contexto sin cifras | Se muestra solo la oración del sistema | Frases sin cifras que contradicen el resultado (Tabla P.22) |
<!-- fuente: services/visualization-service/services/rag_service.py (cifras_fieles, quitar_citas_inventadas, cifras_completas, ids_fieles, citas_fieles, comparacion_invertida, inferencia_sin_respaldo, porcentajes_sin_n, cifra_mal_atribuida, opciones_omitidas, ranking_desordenado, califica_prueba, _con_frase_dato); evidencias/pruebas_2026-10-24/rag_log_704_744.txt (juez antes de mostrar); commit 6fd668d -->

**Lectura.** Cada revisión nueva respondió a un tipo de error que pasaba la anterior. La regeneración con el motivo
recupera parte de las redacciones antes de caer al cálculo. Lo que ninguna revisión detecta es el **sentido** de una
frase sin cifras; por eso la última técnica quita al modelo la oración del dato.

#### Cómo se mide cada respuesta

**Tabla P.14e.** Métricas y juez, por versión.

| Versión | Técnica | Falla que motivó el cambio | Efecto medido |
|---|---|---|---|
| 17 oct | Métricas tipo RAGAS reimplementadas (fidelidad, relevancia, precisión del contexto), con `llama3.2:3b` como juez después de cada respuesta; RAGAS 0.4.3 aparte, fuera de línea | Medir sin respuesta de referencia | — |
| 18 oct | Veredictos por número de afirmación, con la razón antes del veredicto | El juez se trababa al copiar cada afirmación (fidelidad 0.48 contra 0.76 de RAGAS) | De 0 de 1 a 6 de 7 veredictos correctos |
| 22 oct | «Fiel por construcción»: no se juzga lo que se muestra tal cual del cálculo | El juez calificó con 0.25 una copia literal | Las respuestas calculadas muestran fidelidad 100 % |
| 23–24 oct | Juez `qwen2.5:3b`, con semilla fija | llama juzgaba peor y no era estable | Copias literales: de 0.40 a 0.95 |
| 28 oct | Reintento por afirmación, sustento literal, cifras sin sustento sin juez; **bajo demanda**; indicadores sin modelo, varios jueces y calificación humana | El juez fallaba en tablas y copias; juez y redactor no caben juntos en la GPU | Cada pregunta, de 31–38 s a 1.8–5.4 s (Desarrollo X.10.7) |
| 2 nov | Juez `qwen3:4b-instruct`, elegido por su acuerdo con la investigadora | Ningún juez alcanzó kappa 0.41 ni Spearman 0.5 | El juez queda como medida aproximada (Tabla P.29) |
| 7–8 nov (vigente) | Para la evaluación final: lo que la respuesta **debe** contener, K-Precision, cifras con respaldo y plan del modelo sin cambios | El juez sobrestimaba (77–87 % contra 23–62 % de «Bien») | Medidas sin modelo, revisables caso por caso (Tabla P.21) |
<!-- fuente: services/visualization-service/services/evaluacion.py; evidencias/jueces_2026-10-23/comparar_jueces.json; registro 18 oct 02:11–02:12; evidencias/modelos_2026-11-02/resumen.md y modelos_2026-11-03/*/resumen.md; tools/rag/evaluar_chat.py -->

**Lectura.** Un juez de 3–4B mide mal precisamente lo que más importa en este chat, si una cifra o una opción cambió.
Por eso la evaluación pasó del juez a medidas que no dependen de un modelo: el «Debe» de la investigadora, las cifras
con respaldo y la calificación humana. El juez se conserva como aproximación en el panel de cada respuesta.

#### Resultado de cada versión

La Tabla P.14f resume el efecto de cada versión con el conjunto que la midió antes y después.

**Tabla P.14f.** Cada versión del chat contra la anterior, sobre el mismo conjunto.

| Cambio de versión | Conjunto | Antes | Después |
|---|---|---|---|
| Primera corrida del enrutador por reglas → corregido (17 oct) | 12 preguntas de humo, más ayuda y glosario | 4 fallas en 12: el porcentaje del turno vespertino salía 23.3 % (el valor es 13.3 %), una cita y KPIs inventados, una pregunta ajena sin rechazar | 14 de 15 correctas |
| Enrutador por reglas → cuatro etapas (28 oct) | Regresión, 28 preguntas | 53.6 % correctas; cifras 46.7 % | **96.4 %** correctas; cifras **100 %** |
| Correcciones generales con instrumentos no vistos (2–4 nov) | Casos de la prueba 130 y la entrevista 129, `gemma3:4b` | 35 de 70 puntos humanos | **43 de 70** |
| Cálculo sin recuperación → RAG en las respuestas (4–5 nov) | Casos del 127, la prueba 130 y la entrevista 129 | 13 de 170 respuestas del 127 usaban la recuperación | 38 de 63 (60 %) en la primera versión con RAG |
| Versión del 7 nov → cambios generalizados (8 nov) | Baterías, 79 casos | 31 cumplen | **63 cumplen** |
| Igual | Set de control (encuesta y entrevista), 16 casos | 1 cumple | **13 cumplen** |
<!-- fuente: registro 17 oct 22:55 (humo_chat.py) y tools/rag/reportes/verificacion_20261017_2032.md; evidencias/rag_rediseno_2026-10-28/regresion_comparacion.md; evidencias/modelos_2026-11-03 y modelos_2026-11-04 (resumen.md); tt_rag.rag_log.ruta 1290–1771; evidencias/chat_2026-11-07_antes, chat_2026-11-07_control_antes, chat_2026-11-08_final y chat_2026-11-08_final_control (resumen.md) -->

**Lectura.** Cada versión mejoró la anterior en su conjunto. Donde se midió si el modelo inventaba datos, no lo
hizo: en las 140 respuestas sobre instrumentos no vistos (Y.4.4), 0 cifras sin respaldo y 0 IDs inventados; en la
evaluación final, 815 de 856 cifras con respaldo en el contexto.

Las secciones siguientes dan el detalle de las tres comparaciones principales.

### Y.4.3 Enrutador por reglas frente a cuatro etapas (28 oct)

**Por qué se rediseñó.** Con la encuesta de 2000 respondentes (127), tres preguntas fallaron con el enrutador. Ninguna
causa era del modelo de lenguaje: estaban en las reglas que deciden antes que él (Tabla P.15).

**Tabla P.15.** Las tres preguntas que fallaron con el enrutador.

| Pregunta | Qué pasó | Causa |
|---|---|---|
| «dame un dato que encuentres interesante del instrumento» | Respondió con la ficha | La intención de patrones solo se activaba con «lo más interesante», «hallazgos» o «patrones», y los hallazgos no existen como texto en Chroma |
| «dame los primeros 5 estudiantes que contestaron que tienen carga mínima, junto con todas sus respuestas» | 10 IDs y «372 más», sin respuestas | El filtro no tenía límite, orden ni campos |
| «qué respondió el primer respondente en todas las preguntas?» | Rechazada como fuera de dominio | Un respondente solo se reconocía por su ID; la similitud (0.44) cayó en la zona gris y el clasificador la rechazó |
<!-- fuente: tt_rag.rag_log 1093, 1094 y 1097 (28 oct) -->

**Conjunto de regresión.** 28 preguntas sobre cinco instrumentos (127, 59, 61, 109 y 60) que cubren los tres casos
anteriores, datos por respondente, filtros combinados, negación, límites, seguimientos, porcentajes por nivel y por
grupo, comparaciones, hallazgos, KPIs, semántica abierta, metodología, uso de la plataforma, una pregunta ambigua, un
valor que no existe, dos fuera de dominio y un intento de reidentificación. Se corrió en vivo, sin caché, con el flujo
de reglas (`usarInterpretacion: false`) y con el de cuatro etapas, pidiendo las métricas del juez en ambos.
<!-- fuente: tools/rag/regresion/generar_banco.py, banco_regresion.json, evaluar_regresion.py, comparar.py -->

**Tabla P.16.** Regresión del chat con el enrutador y con las cuatro etapas (`llama3.2:3b`).

| Medida | Enrutador por reglas | Cuatro etapas |
|---|---|---|
| Respuesta correcta (cifras, textos y decisión) | 53.6 % | 96.4 % |
| Cifras correctas | 46.7 % | 100.0 % |
| Decisión de dominio correcta | 85.7 % | 100.0 % |
| Plan completo correcto | — (no hay plan) | 92.0 % |
| Fidelidad (juez, media) | 0.846 (20 evaluadas) | 0.807 (23 evaluadas) |
| Relevancia (juez, media) | 0.561 | 0.526 |
| Precisión del contexto (juez, media) | 0.903 | 0.913 |
| Tiempo por pregunta, mediana, sin métricas | 2.0 s | 5.5 s |
<!-- fuente: evidencias/rag_rediseno_2026-10-28/regresion_antes.json, regresion_despues.json y regresion_comparacion.md -->

**Lectura.**
- **Las cuatro etapas responden bien casi todo** (27 de 28) y aciertan todas las cifras, a cambio de unos 3.5 s más
  por pregunta (interpretación y redacción verificada; la ejecución tarda 14 ms).
- **La fidelidad del juez baja un poco** (0.846 a 0.807) aunque las respuestas mejoran: el modo de reglas respondió
  mal o rechazó más preguntas, y esas no se evalúan. Tres redacciones tenían las cifras correctas pero palabras que
  cambiaban el sentido («certificación aprobada» cuando el criterio incluye «Sí, y no lo aprobé»); de ahí que la
  verificación revise también que se nombren todas las opciones del criterio.
- La única pregunta que siguió fallando, «¿cuántos estudian en modalidad nocturna?» (una opción que no existe), se
  responde ahora con una aclaración y las opciones reales.

### Y.4.4 Instrumentos que el chat no había visto (2–4 nov)

**Qué se comprueba.** Si las correcciones generales mejoran el chat en instrumentos que no se usaron durante el
desarrollo. El 127 se había usado todo el tiempo, así que el chat pudo ajustarse a él sin querer.

**Método.** La prueba 130 (97 alumnos; 12 casos, 22 turnos) y la entrevista 129 (una participante; 8 casos, 13 turnos)
se preguntaron con los dos mejores redactores de Y.5.1 antes de cualquier corrección (línea base, 2 nov) y después de
siete correcciones generales (3–4 nov), con el mismo código para ambos redactores. Las correcciones fueron reglas sobre
el catálogo de cualquier instrumento: preguntas válidas que recibían el mensaje de fuera de dominio, comparaciones
numéricas sobre datos de contexto, ranking de preguntas, menciones en respuestas abiertas, preguntas de calidad y el
contexto de la participante (Desarrollo X.9). La investigadora calificó todos los turnos.
<!-- fuente: services/visualization-service/scripts/modelos/generar_casos_fase6.py; evidencias/modelos_2026-11-03/casos_pru03.json y casos_ent11.json; tt_rag.rag_log y rag_calificacion 1462–1631 -->

**Tabla P.17.** Línea base contra segunda corrida (entre paréntesis, la línea base).

| Métrica | Prueba: `gemma3:4b` | Prueba: `qwen3:4b-instruct` | Entrevista: `gemma3:4b` | Entrevista: `qwen3:4b-instruct` |
|---|---|---|---|---|
| Intención correcta | 59 % (46 %) | 64 % (50 %) | 92 % (92 %) | 62 % (62 %) |
| Plantillas indebidas | 2 (8) | 7 (10) | 2 (2) | 7 (11) |
| Exactitud de cifras | 46 % (18 %) | 64 % (46 %) | 100 % (100 %) | 100 % (0 %) |
| Contexto suficiente (turnos de dato) | 64 % (27 %) | 64 % (46 %) | 80 % (60 %) | 40 % (20 %) |
| Cifras sin respaldo / IDs inventados | 0 / 0 (0 / 0) | 0 / 0 (0 / 0) | 0 / 0 (0 / 0) | 0 / 0 (0 / 0) |
| Calificación humana «Bien» | 46 % (27 %) | 50 % (27 %) | 69 % (62 %) | 62 % (23 %) |
| Calificación media (0–2) | 1.05 (0.77) | 1.14 (0.77) | 1.54 (1.38) | 1.38 (0.54) |
| Latencia mediana | 18.0 s (17.0 s) | 12.7 s (9.7 s) | 8.1 s (6.7 s) | 11.8 s (6.3 s) |
<!-- fuente: evidencias/modelos_2026-11-03/pru03/resumen.md y ent11/resumen.md (línea base); evidencias/modelos_2026-11-04/pru03/resumen.md y ent11/resumen.md -->

**Lectura.**
- **Las correcciones generales mejoran a los dos modelos** en instrumentos no vistos: sumando prueba y entrevista,
  `gemma3:4b` pasa de 35 a 43 de 70 puntos y `qwen3:4b-instruct` de 24 a 43. Como las reglas no se escribieron para
  estos instrumentos, la mejora apunta a fallas reales del código.
- **La prueba fallaba más que el 127** en la línea base (14 de 22 turnos con los dos redactores): evidencia de que el
  sistema se había ajustado al 127 durante el desarrollo.
- **Ninguno inventó datos** en las 140 respuestas.
- **Un mismo modelo arma otro plan para la misma pregunta.** Al repetir los turnos afectados, `gemma3:4b` respondió mal
  un caso que antes había respondido bien, sin que ninguna corrección lo tocara: la variación entre corridas es del
  mismo orden que la diferencia entre modelos, así que una corrida por modelo no basta para estimar su exactitud.
<!-- fuente: tt_rag.rag_log 1633–1635 y 1597 (tercera ronda, 4 nov) -->

### Y.4.5 Uso del RAG en las respuestas (4–5 nov)

**Qué se comprueba.** Cuántas respuestas usan la recuperación y qué cambia cuando la usan. Se contó la ruta de cada
consulta en `rag_log` y se repitieron las mismas preguntas antes y después.

**Tabla P.18.** Respuestas que consultaron ChromaDB.

| Versión | Consultas | Con RAG |
|---|---|---|
| Plan y cálculo, sin recuperación (28 oct – 4 nov) | 127: 1290–1461 | 13 de 170 |
| Igual | 130, 129 y 131: 1462–1687 | 44 de 213 |
| RAG como complemento del cálculo (4 nov), `gemma3:4b` | Los tres juegos de casos: 1709–1771 | 38 de 63 (60 %) |
| RAG primero (5 nov, vigente) | Toda pregunta que no bloquean las reglas de dominio | Siempre se busca antes de interpretar |
<!-- fuente: tt_rag.rag_log.ruta, consultas 1290–1771 -->

**Tabla P.19.** Las mismas preguntas sin recuperación y con ella (`gemma3:4b`).

| Pregunta | Sin recuperación | Con recuperación |
|---|---|---|
| Entrevista 131: «¿Y cuántas sesiones le dieron?» (seguimiento) | La tabla de otra pregunta (el tiempo de espera) | «tuvo tres sesiones… de cincuenta minutos», con la pregunta correcta recuperada |
| Entrevista 131: «¿Le parecieron suficientes?» | La tabla sin interpretación | «no le parecieron suficientes… terminaron justo cuando empezaba a sentir avances» |
| Entrevista 131: «¿qué patrones interesantes encuentras?» | «No hay resúmenes calculados» | Cinco temas con citas |
| 127: «qué patrones interesantes encontraste…» | Un patrón | Cuatro patrones con cifras calculadas |
| 127: «y eso, ¿qué puede significar?» | Una aclaración | Explicación de los patrones anteriores |
<!-- fuente: tt_rag.rag_log 1676–1681, 1649, 1689–1708 -->

**Lectura.** Sin recuperación, el chat era «modelo + cálculo»: daba cifras, pero no podía explicar ni seguir el hilo
en entrevistas. Con la recuperación, la redacción interpreta lo que dijo la persona y relaciona el seguimiento con la
pregunta correcta. El costo fue la latencia: las respuestas redactadas pasaron de 18 s de mediana a 30–55 s, porque el
prompt es más largo y `gemma3:4b` no cabe completo en la GPU.

### Y.4.6 Evaluación final: baterías de la investigadora y set de control (7–8 nov)

**Qué se comprueba.** El chat vigente con preguntas que la investigadora escribió sin verlas antes de los cambios, y
si los cambios generalizan a instrumentos ajenos al diseño.

**Tabla P.20.** Baterías y set de control (`tools/rag/baterias_chat.json`).

| Conjunto | Instrumento (Anexo A) | Casos | Qué cubre |
|---|---|---|---|
| Encuesta | 127: 2000 respondentes, 18 preguntas | 25 | Conteos, negaciones, escalas, comparaciones por otra pregunta y por posición, hilo, «lo más preocupante», KPIs, opcionales, lo que no existe, privacidad, manipulación |
| Prueba | 130: 97 alumnos, 22 reactivos en 3 secciones | 25 | Distribuciones, respuestas en blanco por reactivo y por sección, cruces, «más repartidas», una persona, lo que no existe, sin calificar |
| Entrevista | 129: 1 participante, guía de 12 preguntas | 25 | Participación por hablante, cobertura de la guía, menciones, comparaciones entre temas, hilo, diagnósticos, ficha |
| Cortesía | 127 | 4 | Saludo, «¿qué puedes hacer?», gracias, consejo personal |
| **Control** | 61: encuesta (160 respondentes); 60: entrevista (40 participantes); 133, solo en la corrida final: prueba (80 alumnos) | 8 + 8 + 8 | Los mismos tipos de pregunta; ninguno de estos instrumentos se usó para diseñar los cambios |

**Procedimiento.**
- **Línea base:** las consultas que la investigadora hizo a mano sobre la versión congelada del 7 nov (2271–2371),
  emparejadas con cada caso; las tres preguntas de cortesía que no había hecho y el set de control se corrieron con el
  script en esa misma versión.
- **Corridas «después»:** `tools/rag/evaluar_chat.py` hace cada caso como una conversación nueva, sin caché, con
  `gemma3:4b`, una sola vez. La **limpia** tiene los cambios generalizados; la **final**, además, las correcciones
  generales que reveló la limpia. Se reportan las dos para separar lo que se corrigió después de ver resultados.
- **Medidas:** cumple el «Debe» (cumple, parcial o no, con una nota por caso); planes válidos; caídas a plantilla
  (incluye respuestas fijas que son las correctas: cortesía, privacidad, «Indagata no califica», operaciones de
  entrevista); K-Precision (proporción de palabras con contenido de la respuesta presentes en el contexto: mide
  fidelidad, no calidad); cifras con respaldo; tiempo por turno; plan del modelo usado sin cambios; *hit rate*@3.
<!-- fuente: tools/rag/evaluar_chat.py (--desde-log, --reiniciar-ollama-cada, k_precision, cifras_respaldo, plantilla); evidencias/chat_2026-11-07_antes/diagnostico.md §1–2; documentación/guia_reprueba_chat.md -->

**Diagnóstico de la línea base.** De 17 causas, casi todas estaban en el sistema y no en el modelo: faltaban
operaciones (comparar por otra pregunta, por posición o por sección; cruces; operaciones de entrevista); el hilo se
perdía en «de ellos» y «muéstrame 5»; la validación aceptaba planes absurdos; faltaban datos en el documento
(polaridad, indicaciones de la entrevista); los chunks se truncaban; y el nombre de la autora del instrumento entraba al
prompt y el modelo se lo atribuía a la participante.
<!-- fuente: evidencias/chat_2026-11-07_antes/diagnostico.md §5 -->

**Tabla P.21.** Resultados. La prueba de control (133) se cargó para la corrida final, así que no tiene línea base.

| Medida | Línea base | Corrida limpia | Corrida final |
|---|---|---|---|
| Baterías: cumplen el «Debe» (de 79) | 31 (16 parciales, 32 no) | 54 (16 parciales, 9 no) | **63** (14 parciales, 2 no) |
| — encuesta (de 25) | 12 | 19 | 21 |
| — prueba (de 25) | 8 | 13 | 21 |
| — entrevista (de 25) | 11 | 18 | 17 |
| — cortesía (de 4) | 0 | 4 | 4 |
| Control, encuesta y entrevista: cumplen (de 16) | 1 (4 parciales, 11 no) | 9 (5 parciales, 2 no) | **13** (3 parciales, 0 no) |
| Control, prueba: cumplen (de 8) | — | — | 6 (2 parciales, 0 no) |
| Planes válidos | 83 de 97 (85.6 %) | 69 de 77 (89.6 %) | 71 de 77 (92.2 %) |
| Plan del modelo usado sin cambios | — | — | 18 de 77 (23.4 %) |
| Caídas a plantilla | 28 de 102 (27.5 %) | 31 de 102 (30.4 %) | 34 de 102 (33.3 %) |
| K-Precision, mediana | 0.85 (n = 74) | 0.86 (n = 63) | 0.87 (n = 60) |
| Cifras con respaldo | 963 de 982 | 760 de 800 | 815 de 856 |
| Tiempo por turno: mediana / p90 | 40 s / 188 s | 33 s / 64 s | 35 s / 115 s |
| *Hit rate*@3 (baterías / control) | 0.61 / 0.89 | 0.79 / 1.00 | 0.84 / 1.00 |
<!-- fuente: evidencias/chat_2026-11-07_antes/resumen.md; chat_2026-11-07_control_antes/resumen.md; chat_2026-11-08_despues/ y chat_2026-11-08_despues_control/ (resumen.md, calificacion_debe.json); chat_2026-11-08_final/ y chat_2026-11-08_final_control/; chunks_2026-11-07/README.md -->

**Lectura.**
- **El chat pasó de cumplir 31 a 63 de los 79 casos.** Las mayores ganancias están en la prueba (8 a 21) y la encuesta
  (12 a 21), donde faltaban operaciones y el hilo de la conversación.
- **El set de control pasó de 1 a 13 de 16**, sin ningún caso que no cumpla, y la prueba de control, que nunca se usó
  para diseñar, cumplió 6 de 8: los cambios generalizan a instrumentos ajenos al diseño. Además, ninguno de los 288
  textos de pregunta y opción de los tres instrumentos de las baterías influye en el código
  (`evidencias/chat_2026-11-08_final/textos_instrumentos_en_codigo.txt`).
- **El modelo pequeño necesita al sistema.** Su plan se usó sin cambios en 18 de 77 turnos (23 %); en los demás lo
  corrigieron la validación, las reglas o el hilo. En el control, 3 de 23 (13 %).
- **Más plantillas no es peor**: subieron porque la verificación descarta más redacciones y porque varias respuestas
  correctas son fijas.
- **La K-Precision casi no cambió** (0.85 a 0.87): confirma que mide fidelidad y no si la respuesta es la que se pidió
  (en la línea base no se relacionó con la calificación humana: Spearman ρ = −0.04, n = 72).
- **El p90 del tiempo** (115 s) refleja los turnos en que Ollama corrió en parte sobre la CPU por falta de memoria.

**Lo que sigue sin resolverse en la corrida final.**
- **No implementado:** comparar conjuntos de reactivos agrupados por tema (PRU-11) y agrupar la guía de una entrevista
  en temas (ENT-19).
- **Una frase sin cifras que contradice el resultado** pasa la verificación: «el 34.6 % sobre el total» cuando es sobre
  el grupo anterior (ENC-13), «57 cumplieron la condición r15» cuando los 57 son del otro reactivo (PRU-14), «no
  mencionó haber buscado ayuda» cuando lo cuenta en otra respuesta (ENT-13).
- **En entrevistas**, la redacción parafrasea cuando se pide la cita textual (ENT-04, ENT-08, ENT-14) y no siempre
  aclara que se trata de un solo testimonio (ENT-15, ENT-17).
- **La polaridad sin revisar** de la encuesta de control marca como desfavorables respuestas discutibles (CEN-05).
- **Variación del modelo:** ENC-22 dijo que «nocturna» no existe en la corrida limpia y no en la final.
<!-- fuente: evidencias/chat_2026-11-08_final/ (README.md, resumen.md, calificacion_debe.json, recuperacion.json, pytest/, textos_instrumentos_en_codigo.txt); evidencias/chat_2026-11-08_final_control/ -->

**Ronda posterior: frase del dato calculada y entrevistas** (Desarrollo X.9.5). [PENDIENTE: fecha de la corrida.]
- **Qué se repite:** los casos afectados (la batería de la entrevista, ENC-13, ENC-11, PRU-14 y los de conteo, «de
  ellos» y cruce) y después la batería completa y el control, para descartar regresiones.
- **Procedimiento:** el mismo de la corrida final (`documentación/guia_reprueba_chat.md`).

**Tabla P.22.** Casos afectados, antes y después de la ronda posterior.

| Caso | Corrida final | Ronda posterior |
|---|---|---|
| ENC-11 | parcial: atribuye las dos opciones de retraso al grupo de carga media | [PENDIENTE] |
| ENC-13 | parcial: «34.6 % sobre el total» | [PENDIENTE] |
| PRU-14 | parcial: «57 cumplieron la condición r15» | [PENDIENTE] |
| ENT-04, ENT-08, ENT-14 | parcial: parafrasea en lugar de citar | [PENDIENTE] |
| ENT-13 | parcial: «no mencionó haber buscado ayuda» | [PENDIENTE] |
| ENT-15, ENT-17 | no / parcial: sin aclarar que es un solo testimonio | [PENDIENTE] |

**Tabla P.23.** Batería completa y control después de la ronda posterior.

| Medida | Corrida final | Ronda posterior |
|---|---|---|
| Baterías: cumplen (de 79) | 63 | [PENDIENTE] |
| Control: cumplen (de 24) | 19 | [PENDIENTE] |
| Plan del modelo usado sin cambios | 18 de 77 | [PENDIENTE] |
| Caídas a plantilla | 34 de 102 | [PENDIENTE] |
| Tiempo por turno: mediana / p90 | 35 s / 115 s | [PENDIENTE] |

[PENDIENTE: lectura de la ronda posterior y regresiones, si las hubo.]

**Amenazas a la validez.**
- **Las baterías orientaron qué capacidades se construyeron.** Por eso el set de control es la medida de
  generalización.
- **La calificación contra el «Debe» la hizo el mismo asistente que programó los cambios.** Cada caso tiene su nota
  para que la investigadora la revise.
- **Cada caso se preguntó una sola vez:** con temperatura 0.2 en la redacción, otra corrida puede variar la redacción,
  no las cifras.

### Y.4.7 Análisis de respuestas de entrevista

**Qué se comprueba.** Que el análisis separe lo que responde la pregunta de lo que es relato del pasado o digresión,
en distintos formatos de transcripción y con otro tema. Se escribió una entrevista de 4 estudiantes × 4 preguntas con
relatos del pasado, digresiones y posturas ambivalentes (`tools/formatos/corpus_entrevistas.py`), en cinco formatos:
etiquetas «Entrevistador:/Entrevistado:» (I01), «P1:» y «R:» (I02), Zoom con muletillas (I03), WebVTT de Teams (I04) y
sin etiquetas (I05); y otra de docentes sobre evaluación, en dos formatos (`corpus_docentes.py`). Cada respuesta tiene
su clave: la postura, la frase que responde y la frase que es contexto.

**Criterio** (`tools/formatos/verificar_entrevistas.py`). Deben pasar: los participantes y los intercambios esperados,
cada respuesta unida a su pregunta, cada unidad literal de su respuesta, el conteo de posturas del chat igual al del
documento y la respuesta a una pregunta abierta sobre lo que dijo una persona. Se reportan sin decidir el aprobado
el acuerdo de la postura con la clave (exactitud y κ de Cohen) y el núcleo correcto.

**Tabla P.24.** Análisis de entrevistas, primera corrida y versión final.

| Corpus | Comprobaciones: primera corrida → final | Postura (exactitud / κ): primera corrida → final |
|---|---|---|
| Estudiantes, 5 formatos | 36/39 → **39/39** | 0.50–0.56 / 0.30–0.41 → **0.875 / 0.785** (sin etiquetas: 0.75 / 0.50) |
| Docentes, 2 formatos (otro tema) | — → **16/16** | — → **0.875 / 0.804** |
<!-- fuente: evidencias/formatos_2026-10-21/entrevistas_corrida1.*, entrevistas.md, entrevistas_docentes.md (instrumentos 95–106) -->

En la primera corrida, el modelo marcaba «ambivalente» a quien cambió de opinión con el tiempo; la postura global se
calcula ahora desde las unidades que responden (Desarrollo X.7.8).

**Anotación independiente.** La clave la hizo el autor del sistema, lo que podía inflar el acuerdo. La investigadora
anotó las 32 respuestas **sin ver** la clave ni el análisis (`tools/formatos/anotacion/`). La comparación reveló dos
casos «Depende: en unas sí, en otras no» que el sistema resumía como «sí»; se agregó la regla de ambivalencia y se
repitió (Tabla P.25).

**Tabla P.25.** Acuerdo de la postura con cada anotación.

| Comparación | Sin la regla de ambivalencia | Con la regla (vigente) |
|---|---|---|
| Investigadora vs sistema | 26/32 (81.2 %), κ 0.70 | 28/32 (87.5 %), κ 0.80 |
| Autor vs sistema | 28/32 (87.5 %), κ 0.80 | 30/32 (93.8 %), κ 0.90 |
| Investigadora vs autor | 30/32 (93.8 %), κ 0.90 | sin cambio |
<!-- fuente: evidencias/formatos_2026-10-21/RESULTADO.md §Anotación independiente; anotacion_detalle.json; depende.log (instrumentos 107 y 108) -->

La interpretación y las cuatro diferencias que quedan están en Resultados.

### Y.4.8 Dominio, privacidad y manipulación

**Qué se comprueba.** Que el chat rechace lo que debe (preguntas ajenas, reidentificación de personas, intentos de
manipularlo) y acepte las del dominio. Se midió con el banco de 55 preguntas con respuesta verificada, cada una con 2
paráfrasis y 3 corridas (redactor `llama3.2:3b`, enrutador por reglas, 24 oct).

**Tabla P.26.** Banco de preguntas (275 consultas).

| Medida | Resultado |
|---|---|
| Decisión de dominio | 0.982 (54 de 55), F1 macro 0.965, **0 falsas aceptaciones** en privacidad y manipulación |
| Exactitud con referencia | 31 de 45 (0.69) |
| Consistencia ante paráfrasis | 0.68 |
| Estabilidad (3 corridas) | 1.0 |
| Latencia | p50 2.6 s, p95 17.3 s |
<!-- fuente: evidencias/banco_2026-10-24/evaluacion_llama3.2_3b_2122.json y .md -->

Las decisiones de dominio se volvieron a comprobar en la regresión del 28 oct (100 %, Tabla P.16) y en las baterías
finales, que incluyen privacidad y manipulación (Tabla P.20). La única pregunta mal decidida en el banco, «¿cuántas
personas fueron entrevistadas?», rechazada como ajena, se responde desde entonces como consulta de estructura.

### Y.4.9 Pruebas de la investigadora

[PENDIENTE: prueba de la investigadora] Con cada instrumento propio, hacer preguntas de cada tipo (porcentaje, filtro,
respondente, estructura, patrones, abierta y fuera del dominio), comprobar las cifras contra el CSV y anotar las
métricas de «Evaluación automática» de cada respuesta (plantilla de `markdowns/GUIA_PRUEBAS.md`).

---

## Y.5 Distintos modelos

Qué se revisa: si otro modelo, como redactor de las respuestas o como juez de las métricas, cambia la exactitud, las
métricas o el tiempo. Se cambia **un modelo a la vez**: cada redactor responde una vez y los cuatro modelos juzgan
todas las respuestas.

### Y.5.1 Redactores (28 oct – 2 nov)

**Diseño.**
- **Instrumento:** el 127.
- **Preguntas:** los 14 casos (28 turnos) de las pruebas de la investigadora, con sus erratas y sus seguimientos en la
  misma conversación. Los seguimientos quedaron con el texto que ella escribió en la corrida con `llama3.2:3b`
  (consultas 1344–1365) y se repiten tal cual con los demás redactores. Como se escribieron reaccionando a las
  respuestas de llama (por ejemplo, «Me sigues dando una pregunta»), con otro modelo pueden no venir al caso; se hacen
  igual para que la comparación sea con las mismas preguntas.
- **Redactores:** `llama3.2:3b`, `qwen2.5:3b`, `qwen3:4b-instruct` y `gemma3:4b` (Tabla P.27). Cada uno hace
  **todas** las etapas del chat (`OLLAMA_MODEL`), no solo la redacción. Se planeó `qwen3:4b`, pero esa variante razona
  antes de responder; tras una consulta (1396) se cambió por la variante *instruct*, que responde directo.
- **Jueces:** cada redactor responde una vez y los cuatro modelos juzgan todas las respuestas, así que salen
  16 combinaciones.
- **Referencia:** los turnos de dato tienen sus cifras correctas, calculadas directo de la base. Por ejemplo:
  - 486 de 2000 llevan carga máxima;
  - la pregunta con más desacuerdo es p17, con 37.7 %;
  - 833 respondentes dejaron alguna pregunta en blanco.

  Los interpretativos tienen criterios y los califica la investigadora.
- **Cuidados:** la caché se apaga durante el experimento (`RAG_CACHE_HORAS=0`) y la temperatura no se mueve.

<!-- fuente: services/visualization-service/scripts/modelos/ (README.md, generar_casos.py, casos.json, juzgar.py, calificar.py, reporte.py); rag_log 1344–1365 (31 oct); Desarrollo X.10.8 -->

**Tabla P.27.** Versiones exactas de los modelos (Ollama 0.32.9).

| Modelo (etiqueta de Ollama) | Familia | Parámetros | Cuantización | Contexto máximo del modelo | ID (digest) | Tamaño |
|---|---|---|---|---|---|---|
| `llama3.2:3b` | Llama 3.2 (Meta) | 3.2 B | Q4_K_M | 131 072 | `a80c4f17acd5` | 2.0 GB |
| `qwen2.5:3b` | Qwen 2.5 (Alibaba) | 3.1 B | Q4_K_M | 32 768 | `357c53fb659c` | 1.9 GB |
| `qwen3:4b-instruct` | Qwen 3, variante *instruct* (sin razonamiento) | 4.0 B | Q4_K_M | 262 144 | `0edcdef34593` | 2.5 GB |
| `gemma3:4b` | Gemma 3 (Google) | 3.9 B, más 0.4 B del módulo de visión, que no se usa | Q4_K_M | 131 072 | `68ceab7e468a` | 3.4 GB |

Embeddings:
- Del sistema: `paraphrase-multilingual-mpnet-base-v2`.
- Solo del RAGAS fuera de línea: `nomic-embed-text` (`0a109f422b47`).

En el chat todos corren con contexto de 4096 tokens. La temperatura es 0.2 al redactar y 0 al interpretar y al
juzgar. Se reporta el ID porque una etiqueta de Ollama puede apuntar a otra versión si se vuelve a publicar con el
mismo nombre.
<!-- fuente: ollama show y ollama list en el contenedor indagata_ollama (5 nov 2026); shared/db/core/config.py (RAG_TEMPERATURA_REDACCION); services/visualization-service/services/ollama_client.py (num_ctx 4096) -->

**Corridas.** La investigadora hizo los 28 turnos con cada redactor y calificó todas las respuestas (0 mal, 1 parcial,
2 bien). Después, cada uno de los cuatro modelos juzgó las cuatro corridas. Las negativas y los mensajes fijos no se
juzgan, así que cada juez evaluó 78 respuestas.

| Redactor | Consultas (`rag_log`) |
|---|---|
| `llama3.2:3b` | 1328–1365 |
| `qwen2.5:3b` | 1366–1395 |
| `qwen3:4b-instruct` | 1397–1429 |
| `gemma3:4b` | 1430–1461 (el caso 1 se repitió en 1459–1461: en 1432 la respuesta llegó cortada) |

<!-- fuente: evidencias/modelos_2026-11-02/resumen.md y resumen.json (reporte.py, 2 nov); tt_rag.rag_metrica_juez y tt_rag.rag_calificacion, consultas 1328–1461 -->

**Tabla P.28.** Comparación de redactores (instrumento 127, 28 turnos).

| Redactor | Intención correcta | Plantillas indebidas | Exactitud de cifras | Cifras con respaldo (cifras sin respaldo) | IDs inventados | Calificación humana «Bien» | Calificación media (0–2) | Latencia mediana | Promedio del juez (otros jueces) | Sesgo de autoevaluación |
|---|---|---|---|---|---|---|---|---|---|---|
| `llama3.2:3b` | 54 % | 7 | 59 % | 100 % (0) | 0 | 29 % | 0.64 | 7.2 s | 65 % | +8 puntos |
| `qwen2.5:3b` | 71 % | 8 | 33 % | 100 % (0) | 0 | 29 % | 0.86 | 4.9 s | 73 % | −16 puntos |
| `qwen3:4b-instruct` | 54 % | 10 | 78 % | 83 % (2) | 0 | 46 % | 1.07 | 15.6 s | 73 % | −2 puntos |
| **`gemma3:4b`** | 64 % | **2** | 37 % | 100 % (0) | 0 | 43 % | 1.07 | 18.3 s | 72 % | +7 puntos |

<!-- fuente: evidencias/modelos_2026-11-02/resumen.md, secciones 1–3; «otros jueces» = promedio de la fila de la matriz sin la diagonal, calculado de resumen.json → matriz.celdas -->

Las dos cifras sin respaldo de `qwen3:4b-instruct` están en el turno 9.2 (consulta 1414). Una es un falso positivo del
detector: el «1» de la cita «[Fuente 1]». La otra, «18 indicadores», no está en los datos que recibió el modelo. La
investigadora calificó ese turno con 0.
<!-- fuente: tt_rag.rag_log 1414 (contexto_usado y salida); evidencias/modelos_2026-11-02/qwen3_4b-instruct.json, turno 9.2 -->

### Y.5.2 Confiabilidad del juez y decisión

**Cómo se mide.** Las métricas tipo RAGAS evalúan las respuestas; para saber si se puede
confiar en el juez que las calcula, se compara con la calificación humana y con los indicadores sin modelo, usando dos
estadísticos clásicos que hoy se usan para validar evaluadores automáticos:
- **Kappa de Cohen** (Cohen, 1960): acuerdo entre dos evaluadores que clasifican en categorías, descontado el acuerdo
  esperable por azar. Va de −1 a 1; 0 equivale al azar. Se calcula sobre «el juez aprueba» (promedio de sus tres
  métricas ≥ 0.7) contra «la investigadora calificó Bien», y sobre «fidelidad ≥ 0.8» contra «todas las cifras tienen
  respaldo». El umbral de 0.41 corresponde al acuerdo «moderado» de la escala de Landis y Koch (1977).
- **Correlación de Spearman** (Spearman, 1904): si los dos ordenan las respuestas igual aunque usen escalas distintas
  (el juez de 0 a 1 y la investigadora 0, 1 o 2). El umbral fijado fue 0.5.

La correlación de rangos con el juicio humano es la forma habitual de reportar un evaluador automático; G-Eval (Liu et
al., 2023), por ejemplo, reporta Spearman contra calificaciones humanas. Thakur et al. (2025) advierten que el
porcentaje de acuerdo solo puede engañar: jueces con mucho acuerdo pueden dar puntajes muy distintos. Por eso
recomiendan medidas corregidas por azar junto con un análisis cualitativo. Ellos usan la π de Scott, porque la kappa de
Cohen tiene problemas teóricos documentados; las dos coinciden cuando los evaluadores reparten sus calificaciones de
forma parecida. En esta tesis se usa la kappa de Cohen, junto con Spearman y la revisión turno por turno.

Referencias:
- Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*,
  20(1), 37–46. https://doi.org/10.1177/001316446002000104
- Landis, J. R. y Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1),
  159–174. https://doi.org/10.2307/2529310
- Spearman, C. (1904). The proof and measurement of association between two things. *The American Journal of
  Psychology*, 15(1), 72–101. https://doi.org/10.2307/1412159
- Liu, Y., Iter, D., Xu, Y., Wang, S., Xu, R. y Zhu, C. (2023). G-Eval: NLG evaluation using GPT-4 with better human
  alignment. En *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing*
  (pp. 2511–2522). https://doi.org/10.18653/v1/2023.emnlp-main.153
- Thakur, A. S., Choudhary, K., Ramayapally, V. S., Vaidyanathan, S. y Hupkes, D. (2025). Judging the judges:
  Evaluating alignment and vulnerabilities in LLMs-as-judges. En *Proceedings of the Fourth Workshop on Generation,
  Evaluation and Metrics (GEM²)* (pp. 404–430). Association for Computational Linguistics. arXiv:2406.12624.
<!-- fuente: Crossref (api.crossref.org) para Cohen, Landis y Koch, y Spearman; https://aclanthology.org/2023.emnlp-main.153/; https://arxiv.org/abs/2406.12624 y su versión HTML v6 (nota 2 y apéndice B); consultadas el 6 nov 2026. Fórmulas: scripts/modelos/comun.py (kappa, spearman) y reporte.py (cruce, APROBADO = 0.7) -->

**Tabla P.29.** Confiabilidad de cada juez (78 respuestas por juez, todas con calificación humana).

| Juez | Fidelidad vs cifras con respaldo (kappa / π) | Aprobado vs «Bien» humano (kappa / π) | Spearman promedio vs humana | Spearman relevancia vs humana | Precisión del contexto alta con contexto insuficiente |
|---|---|---|---|---|---|
| `gemma3:4b` | 0.159 / 0.075 (n=37) | 0.143 / 0.088 | 0.203 | 0.326 | 22 de 36 |
| `llama3.2:3b` | 0.043 / −0.279 (n=38) | 0.121 / 0.099 | 0.136 | 0.317 | 22 de 36 |
| `qwen2.5:3b` | 0.023 / −0.449 (n=39) | 0.108 / 0.090 | 0.266 | 0.281 | 11 de 36 |
| **`qwen3:4b-instruct`** | 0.033 / −0.357 (n=37) | **0.226 / 0.218** | **0.331** | **0.446** | 20 de 36 |

La π de Scott se agregó el 6 nov regenerando el reporte con las mismas corridas; las kappas salieron idénticas. En
«juez aprobado vs Bien» las dos medidas casi coinciden. En «fidelidad vs cifras con respaldo» la π es mucho menor, y
negativa en tres jueces: el juez y el detector de cifras reparten sus «sí» y «no» en proporciones muy distintas, y
la π castiga esa diferencia, que la kappa absorbe. Las dos llevan a la misma conclusión: ningún juez alcanza el acuerdo moderado.

<!-- fuente: evidencias/modelos_2026-11-02/resumen.md, sección 4; π de Scott: storage/evaluacion_modelos/2026-11-02_con_pi/resumen.md (reporte.py con --corrida llama3.2:3b=1328-1365 qwen2.5:3b=1366-1395 qwen3:4b-instruct=1397-1429 gemma3:4b=1430-1461, 6 nov) -->

**Decisión (2 nov).**
- **Redactor: `gemma3:4b`.** El primer criterio era no inventar IDs ni cifras; lo cumplen `llama3.2:3b`, `qwen2.5:3b`
  y `gemma3:4b`. Entre ellos, `gemma3:4b` tiene la mayor proporción de respuestas «Bien» (43 %) y la menor cantidad de
  plantillas indebidas (2).
  - En contra: es el más lento (18.3 s de mediana, porque no cabe completo en la GPU de 4 GiB) y su exactitud de cifras
    es baja (37 %).
  - `qwen3:4b-instruct` queda en segundo lugar: es el mejor en respuestas «Bien» (46 %) y en exactitud de cifras (78 %),
    pero escribió una cifra sin respaldo.
- **Juez: `qwen3:4b-instruct`, como medida aproximada.** Ningún juez alcanzó el umbral fijado (kappa ≥ 0.41 y
  Spearman ≥ 0.5). `qwen3:4b-instruct` es el que más se parece a la calificación humana, y no es el redactor.
  - `gemma3:4b` y `llama3.2:3b` no distinguen el contexto suficiente del insuficiente: dan precisión del contexto
    alta en los 36 turnos de dato.
  - Por eso, la evidencia principal sobre la calidad de las respuestas son los indicadores del sistema y la
    calificación humana; las métricas del juez se reportan como aproximadas.

**Juez anterior.** El 23 oct se comparó `llama3.2:3b` con `qwen2.5:3b` calificando la fidelidad de 9 respuestas cuya
verdad se conoce: en las copias literales del cálculo, qwen dio 0.95 de media contra 0.40 de llama; los dos
detectaron un objetivo común inventado y ninguno detectó el cambio de una opción por otra (Desarrollo, Tabla D.29a).
Se adoptó `qwen2.5:3b` hasta esta comparación.
<!-- fuente: evidencias/jueces_2026-10-23/comparar_jueces.json -->

**Fallas que apuntan al código.** Ocho turnos fallan con los cuatro redactores: 4.1, 5.1, 6.2, 9.1, 9.2, 10.2, 10.4 y
12.2. La intención correcta va de 54 % a 71 % según el modelo, así que parte del problema está en la interpretación de
la pregunta y no en la redacción; son las que motivaron las correcciones de Y.4.4.
<!-- fuente: evidencias/modelos_2026-11-02/resumen.md, sección 5 -->

Con los instrumentos que el chat no había visto, `gemma3:4b` y `qwen3:4b-instruct` quedaron muy cerca (Tabla P.17);
se mantuvo `gemma3:4b` por su ventaja en la entrevista. El 127 se volvió a medir con `gemma3:4b` en la evaluación final
(Y.4.6).

---

## Y.6 Duración del procesamiento

Qué se revisa: cuánto tarda la máquina en cada paso al subir un instrumento y cuánto tarda el chat en responder,
para estimar la duración en un servidor.

### Y.6.1 Cómo se mide

Desde el 25 oct, cada servicio registra el **tiempo de cómputo** de sus pasos en la tabla `tiempo_proceso`:
- carga y lectura del archivo;
- fase automática de la limpieza y aplicación de las decisiones;
- propuestas de metadatos;
- aprobación e indexación al aprobar;
- perfil semántico;
- propuesta y confirmación de KPIs;
- documento final;
- análisis de respuestas de entrevista;
- publicación e indexación al RAG.

**No incluye el tiempo que la persona tarda en decidir.** La vista rápida del catálogo los muestra en «Tiempos del
procesamiento», con tres cifras:
- el **cómputo total**: la suma de los pasos, que es la base para estimar el servidor;
- el tiempo **de la carga a lo último**, que sí incluye las decisiones;
- la **latencia del chat** sobre ese instrumento (mediana y p95).

Cada respuesta del chat muestra además «Respondió en … s» (Desarrollo X.7.10).

### Y.6.2 Lo que ya se midió

- **Latencia del chat con el instrumento 59** (186 consultas registradas): mediana 1.3 s y p95 10.3 s. Las
  respuestas calculadas, sin modelo, tardan de 0.1 a 0.8 s; las que redacta el modelo, de 2 a 18 s; la primera
  después de reiniciar, unos 20 a 48 s, por la carga del modelo.
- **Indexación al aprobar un instrumento de 160 respondentes:** más de 120 s, lo que obligó a subir el límite
  del gateway a 600 s.
- Los instrumentos ya publicados se procesaron antes del registro de tiempos y no tienen tiempos por paso.
<!-- fuente: GET /visualizacion/catalogo/59/tiempos (25 oct); evidencias/banco_2026-10-24/evaluacion_llama3.2_3b_2122.json (latencias); registro 24 oct (aprobación de 109) -->

- **Latencia del chat con `gemma3:4b` (7 nov, versión congelada).** En las primeras 11 consultas de la prueba nueva
  de la investigadora (2271–2281), cada respuesta tardó de 44 a 479 s: la interpretación, de 35 a 137 s, y la
  redacción, de 53 a 196 s, más el reintento cuando la verificación rechaza la primera redacción. La causa es el
  equipo: `gemma3:4b` no cabe en la GPU de 4 GiB y corre 43 % en la CPU, y cada pregunta hace dos o tres llamadas al
  modelo. En la consulta 2281 el sistema operativo detuvo el proceso del modelo por falta de memoria (Ollama marcado
  `OOMKilled`, memoria de intercambio de Docker al 97 %) y el chat mostró el aviso «No se pudo contactar al modelo
  local». Esa respuesta es una falla de infraestructura, no del sistema.
<!-- fuente: tt_rag.rag_log 2271–2281 (latencia_ms, tiempos); ollama ps (43%/57% CPU/GPU); docker inspect indagata_ollama (OOMKilled=true); docker compose logs ollama (completion error EOF, 18:10 UTC, 7 nov); free -m en el contenedor -->

### Y.6.3 Pruebas de la investigadora

[PENDIENTE: prueba de la investigadora] Subir instrumentos de distinto tamaño (por ejemplo, 50, 160 y 500 respondentes; una entrevista de 4 y
otra de 40 participantes) y anotar los tiempos de la vista rápida.

**Tabla P.30.** Tiempos de cómputo por paso (por llenar).

| Instrumento | Tamaño | Carga | Limpieza (automática + aplicar) | Metadatos | Aprobación + indexación | Perfil | KPIs | Documento | Indexación al RAG | Cómputo total | Punta a punta | Chat p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | |

Equipo de referencia: Tabla D.1 (Intel Core i5-11320H, 15.8 GB de RAM, GTX 1650 de 4 GiB). En un servidor con más
memoria y una GPU mayor, los pasos con el modelo (metadatos, KPIs y redacción del chat) y la indexación serían los
más beneficiados.

---

## Y.7 Lo que no se cubrió

| Aspecto | Por qué |
|---|---|
| Datos reales | No se contó con respuestas de una institución; los formatos usan datos sintéticos escritos con la forma de los exportes reales |
| Una entrevista real anotada | El acuerdo del análisis de posturas se midió con dos entrevistas sintéticas (32 respuestas); falta repetirlo con una entrevista real con consentimiento |
| Instrucciones inyectadas dentro de un instrumento (no en la pregunta) | No se construyó un caso; solo se probaron instrucciones escritas por el usuario |
| Comparación entre instrumentos después de la corrección de la ficha | Los instrumentos usados para compararla se borraron de la base antes de repetirla |
| Pruebas estandarizadas en formatos distintos | Ya vienen estructuradas; no se escribieron variantes de formato |
| Excel de pregunta y respuesta por fila, y audio | Fuera del contrato: el primero no está entre las fuentes confirmadas y el audio requiere transcripción previa |
| Recorridos de la interfaz en el navegador | Se hicieron con Chrome *headless* el 15–16 oct, pero los scripts y capturas no quedaron versionados; la tarjeta de dimensiones sugeridas y el panel de análisis de respuestas no se recorrieron |
| Carga concurrente de varios usuarios | Un solo equipo de desarrollo, con memoria limitada |
| `comparar_kpis` con el catálogo vigente | No se repitió después de adoptar el catálogo de `PA` (Y.3.4) |
| Juez de métricas con un modelo mayor | Solo se contó con una GPU de 4 GiB; ningún juez de 3–4B alcanzó el umbral (Tabla P.29) |
| Varias corridas por caso | Cada caso se preguntó una vez; la variación entre corridas del mismo modelo es del orden de la diferencia entre modelos (Y.4.4) |

---

## Figuras propuestas

| Figura | Contenido | Sección |
|---|---|---|
| P.1 | Fase asistida de la limpieza (tarjetas con la opción sugerida) | Y.2.1 |
| P.2 | Confirmación de roles de hablantes de ent_01 | Y.2.1 |
| P.3 | Estadística de una prueba: opción más elegida por reactivo | Y.2.1 |
| P.4 | «Ver dónde» de un valor fuera de la escala en la encuesta de 2000 | Y.2.3 |
| P.5 | «KPIs sugeridos» con puntaje, evidencia y justificación editable | Y.3.4 |
| P.6 | Tarjeta de dimensiones sugeridas en la limpieza (grupos con sus ítems y α) | Y.3.3 |
| P.7 | Chat: respuesta calculada con «Ver datos» y «Cómo lo calculé» | Y.4.6 |
| P.8 | Panel «Análisis de las respuestas» con la respuesta de la beca deportiva | Y.4.7 |

## Lista de [PENDIENTE] de este capítulo

1. Resultado de la ronda posterior (frase del dato y entrevistas): Tablas P.22 y P.23 (Y.4.6).
2. Acuerdo de los juicios de relevancia de la investigadora con los del autor (Y.3.1).
3. Pruebas de la investigadora con instrumentos propios (Y.2.4, Y.3.5, Y.4.9 y Y.6.3).
4. Repetir la anotación independiente con una entrevista real, si se cuenta con una con consentimiento (Y.4.7).
5. Tomar las capturas P.1 a P.8.
