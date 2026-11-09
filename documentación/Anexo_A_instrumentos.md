# Anexo A. Instrumentos usados en las pruebas

<!-- fuente: consulta a tt_rag.raw_data e instrumento_procesado (8 nov 2026); storage/instrumentos_sinteticos/*/*_metadata.json; documentos finales vigentes en storage/json/<id>/; capítulos de Desarrollo y Pruebas -->

Este anexo dice, para cada instrumento que aparece en los capítulos, **qué es, de dónde salió, dónde está su archivo y
en qué pruebas se usó**. En los capítulos, cada instrumento se nombra por su número en el sistema (`id`, por ejemplo
«la encuesta 127»). Todas las respuestas son sintéticas.

## A.1 Dónde buscar

| Qué | Carpeta (desde la raíz del repositorio) | ¿Está en el repositorio? |
|---|---|---|
| Archivo que se subió al sistema, su instrumento original (cuestionario, guion o prueba en texto o PDF) y sus metadatos de generación | `storage/instrumentos_sinteticos/{encuestas,entrevistas,pruebas}/` | Sí |
| Cómo se generaron los datos sintéticos | Desarrollo X.6; código en `tools/data_synthesis/` | Sí |
| Copia que guardó el sistema al subirlo | `storage/raw/_/<n>__<archivo>` | No (solo en el equipo del proyecto) |
| CSV limpio de cada versión de la limpieza | `storage/clean/<id>/` | No |
| Documento final de cada versión (lo que lee el chat) | `storage/json/<id>/<n>__v<versión>_documento_final.json` | No |
| Respuestas del chat, calificaciones y métricas de cada evaluación | `evidencias/<carpeta>/` (cada carpeta tiene su `README.md` o `resumen.md`) | No |
| Preguntas de las evaluaciones del chat | `tools/rag/baterias_chat.json`, `tools/rag/recuperacion_oro.json`, `tools/rag/preguntas_referencia.json` | Sí |

Las carpetas `storage/raw`, `storage/clean`, `storage/json` y `evidencias/` no se suben al repositorio porque son
salidas del sistema y de las pruebas. Se pueden regenerar subiendo de nuevo el archivo fuente
(`tools/rag/procesar_instrumento.py`) y repitiendo la prueba (`documentación/guia_reprueba_chat.md`).

## A.2 Instrumentos en el sistema al 8 nov

**Tabla A.1.** Instrumentos vigentes. Las rutas de «Archivo fuente» y «Original» son relativas a
`storage/instrumentos_sinteticos/`.

| id | Título | Tipo | Personas | Preguntas | Archivo fuente | Original | Origen |
|---|---|---|---|---|---|---|---|
| 59 | Encuesta de evaluación y ambiente escolar por turno | Encuesta | 60 | 8 | `encuestas/enc_10_turno_respondido.csv` | `encuestas/enc_10_turno_original.txt` | Construida con resultado conocido: la respuesta por turno se sabe de antemano (Pruebas Y.1.3) |
| 60 | Entrevista sobre estrategias de permanencia universitaria | Entrevista | 40 | 12 | `entrevistas/ent_01_respondido.txt` | `entrevistas/ent_01_original.txt` | Generador de datos sintéticos (Desarrollo X.6) |
| 61 | Encuesta de Carga Académica y Gestión del Tiempo | Encuesta | 160 | 20 | `encuestas/enc_09_respondido.csv` | `encuestas/enc_09_original.txt` | Generador de datos sintéticos (X.6) |
| 109 | Encuesta de Trayectoria Académica, Trabajo y Uso de Servicios | Encuesta | 160 | 26 | `encuestas/enc_11_respondido.csv` | `encuestas/enc_11_original.txt` | Generador de datos sintéticos, con los seis tipos de pregunta (X.6) |
| 127 | Indicadores de Experiencia y Calidad Académica | Encuesta | 2000 | 18 | `encuestas/Encuesta2_Simulada_2000_SUCIA.csv` | `encuestas/Indicadores de Experiencia y Calidad Académica - Formularios de Google.pdf` | Encuesta simulada por la investigadora, con su formulario de Google Forms; el archivo trae errores a propósito para probar la limpieza («SUCIA») |
| 129 | Salud mental en la universidad | Entrevista | 1 | 12 | `entrevistas/ent_11_salud_mental_ruido.txt` | `entrevistas/ent_11_original.txt` (versión limpia: `ent_11_salud_mental_limpia.txt`; ruido inyectado: `ent_11_ruido_inyectado.json`) | Entrevista de la investigadora con ruido de transcripción contemplado (errores inyectados, Pruebas Y.1.3) |
| 130 | Prueba de Alfabetización Digital | Prueba estandarizada | 97 | 22 | `pruebas/pru_03_sucio_no_contemplado.csv` | `pruebas/pru_03_original.txt` (sin errores: `pru_03_respondido.csv`; errores: `pru_03_ruido_no_contemplado.json`) | Prueba de la investigadora con errores no contemplados por la limpieza (errores inyectados, Pruebas Y.1.3), entre ellos un reactivo vacío para todos (r10) |
| 131 | Salud mental entrevista | Entrevista | 1 | 13 | `entrevistas/ent_11_salud_mental_ruido_no_contemplado.txt` | `entrevistas/ent_11_original.txt` (errores: `ent_11_ruido_no_contemplado.json`) | La misma entrevista con ruido no contemplado (errores inyectados, Pruebas Y.1.3) |
| 132 | — (sin publicar) | Entrevista | 1 | — | `entrevistas/ent_11_salud_mental_ruido.txt` | — | Segunda carga de la 129; quedó en «limpio» y no se reporta |
| 133 | Prueba de Competencia en Investigación Científica | Prueba estandarizada | 80 | 15 | `pruebas/pru_06_respondido.csv` | `pruebas/pru_06_original.txt` | Generador de datos sintéticos (X.6); cargada el 8 nov como prueba de control, ajena al diseño del chat |
<!-- fuente: tt_rag.raw_data (nombre_archivo, raw_archivo, raw_archivo_original); documentos finales vigentes: storage/json/59/1__v1, 60/484__v2, 61/21__v2, 109/3__v3, 127/54__v4, 129/49__v8, 130/1__v2, 131/1__v1 y 133/1__v1 _documento_final.json -->

**Documento final vigente** (el que leyó el chat en la evaluación final): `storage/json/<id>/` con el número de
versión más alto; por ejemplo, `storage/json/127/54__v4_documento_final.json`.

## A.3 En qué pruebas se usó cada instrumento

**Tabla A.2.** Pruebas por instrumento vigente.

| id | Pruebas | Dónde se reporta | Evidencia |
|---|---|---|---|
| 59 | Flujo completo; respuesta conocida (4 de 30 del turno vespertino); encuesta sin secciones; regresión del chat; chunks en *tokens* | Pruebas Y.2.1, Y.3.2, Y.3.3, Y.4.3; Desarrollo X.9.1 | `evidencias/encuesta_sin_secciones_2026-10-20/`, `evidencias/chunks_2026-11-07/` |
| 60 | Flujo completo; regresión del chat; **set de control de la evaluación final** (8 casos CET); análisis de lo que se cuenta, solo con reglas | Pruebas Y.2.1, Y.4.3, Y.4.6; Desarrollo X.7.8 | `evidencias/chat_2026-11-07_control_antes/`, `evidencias/chat_2026-11-08_final_control/` |
| 61 | Filtros y calidad de los datos; regresión; **set de control** (8 casos CEN); polaridad propuesta sin revisar | Pruebas Y.2.1, Y.3.1, Y.4.3, Y.4.6; Desarrollo X.7.7 | `evidencias/chat_2026-11-08_final_control/`, `evidencias/nlp_formato_2026-11-07/` |
| 109 | Seis tipos de pregunta; banco de preguntas con respuesta verificada; chunks en *tokens* | Pruebas Y.2.1, Y.3.1, Y.4.8 | `evidencias/banco_2026-10-24/`, `evidencias/chunks_2026-11-07/` |
| 127 | Limpieza con errores reales; regresión del rediseño; comparación de modelos redactor × juez; **batería de encuesta de la evaluación final** (25 casos ENC más 4 de cortesía GEN); polaridad revisada por la investigadora; chunks en *tokens* | Desarrollo X.7.7; Pruebas Y.2.3, Y.3.1, Y.4.3, Y.4.6, Y.5.1 | `evidencias/modelos_2026-11-02/`, `evidencias/chat_2026-11-07_antes/`, `evidencias/chat_2026-11-08_final/` |
| 129 | Instrumento nuevo con ruido de transcripción; **batería de entrevista de la evaluación final** (25 casos ENT); análisis de lo que se cuenta con el modelo (Tabla D.23.1) | Pruebas Y.2.2, Y.4.4, Y.4.6; Desarrollo X.7.8 | `evidencias/nlp_formato_2026-11-07/`, `evidencias/chat_2026-11-08_final/` |
| 130 | Instrumento nuevo con errores no contemplados; **batería de prueba de la evaluación final** (25 casos PRU); chunks en *tokens* | Pruebas Y.2.2, Y.3.1, Y.4.4, Y.4.6 | `evidencias/chat_2026-11-08_final/` |
| 131 | La misma entrevista con ruido no contemplado | Pruebas Y.2.2, Y.4.5 | — |
| 133 | **Set de control de la evaluación final** (8 casos CPR) | Pruebas Y.4.6 | `evidencias/chat_2026-11-08_final_control/` |

Las preguntas de cada caso (ENC, PRU, ENT, GEN y el control CEN, CET y CPR), con lo que la respuesta debe contener,
están en `tools/rag/baterias_chat.json`. La respuesta del chat a cada caso y su calificación están en
`evidencias/<carpeta>/casos/<caso>.json` y `calificacion_debe.json`.

## A.4 Todos los instrumentos que pasaron por el sistema

Los instrumentos de las primeras pruebas se borraron por decisión de la investigadora, por la vía oficial
(`DELETE /instrumentos/{id}`), después de guardar sus resultados en `evidencias/`. Sus archivos fuente siguen en
`storage/instrumentos_sinteticos/`, en `tools/formatos/corpus/` (formatos de encuestas y entrevistas) y en
`evidencias/` (variantes sin secciones, copias con errores inyectados).

**Tabla A.3.** Instrumentos procesados en el sistema, en orden cronológico. La columna «Sección» es del capítulo de Pruebas.

| Fecha | id | Archivo | Qué se probó y resultado | Sección |
|---|---|---|---|---|
| 14 oct | 2–20 | `storage/raw/inst_02.v1.json` … `inst_20.v1.json` | JSON técnicos cargados directamente, sin limpieza ni documento final. Borrados el 28 oct | — |
| 15 oct | — (borrados) | Encuesta de ejemplo con ítem invertido; encuesta de la investigadora (26 ítems); prueba de ejemplo | α 0.586 → 0.892; un α por dimensión | Y.2.1 |
| 15 oct | 22 | `storage/instrumentos_sinteticos/encuestas/enc_04_respondido.csv` | Asociación de KPIs: método anterior contra el nuevo. Borrado el 28 oct | Y.3.4 |
| 16 oct | — (borrados) | `…/pruebas/pru_02_respondido.csv`, `…/pruebas/pru_04_respondido.csv`, `…/encuestas/enc_05_respondido.csv` (id 39 en Y.3.4) | pru_04 de punta a punta; justificaciones de KPIs | Y.2.1, Y.3.4 |
| 16 oct | 53 | `storage/instrumentos_sinteticos/entrevistas/ent_01_respondido.txt` | Segmentación por `RESPONDENTE`: 40 entrevistados, 480 respuestas. Republicado el 18 oct (534 chunks) | Y.2.1 |
| 16 oct | 55 | `storage/instrumentos_sinteticos/pruebas/pru_01_respondido.csv` | 100 alumnos × 25 reactivos = 2500 respuestas. Borrado el 25 oct | Y.2.1, Y.4.2 |
| 17 oct | 59 | `storage/instrumentos_sinteticos/encuestas/enc_10_turno_respondido.csv` | 4 de 30 del turno vespertino = 13.3 %, igual que el valor esperado | Y.2.1, Y.4.3 |
| 17 oct | 60 | `storage/instrumentos_sinteticos/entrevistas/ent_01_respondido.txt` | ent_01 como instrumento nuevo: 480 respuestas, 521 chunks | Y.2.1 |
| 18 oct | 61 | `storage/instrumentos_sinteticos/encuestas/enc_09_respondido.csv` | Filtros 88, 37 y 23 de 160 (comprobados con SQL); calidad de los datos | Y.2.1 |
| 19 oct | 62, 63 | `storage/instrumentos_sinteticos/encuestas/enc_04_respondido.csv` | Cargas de enc_04 sin documento final (62 quedó en «limpio»). No se reportan | — |
| 20 oct | 64–66 | `evidencias/encuesta_sin_secciones_2026-10-20/enc_10_sinsec_{A,B,C}_respondido.csv` | Encuesta sin secciones, antes de corregir: 1/6, 6/6 y 1/6 | Y.3.2 |
| 22 oct | 67–74 | Las mismas variantes A, B y C, más `enc_10_turno` (71) | Después de corregir: 6/6 en las tres; 19/19 en las preguntas de referencia | Y.3.2 |
| 22 oct | 75–83 | `tools/formatos/corpus/encuestas/E01…E09` | Corrida 1 de la matriz de encuestas, detenida en E09 (83 quedó en «limpio») | Y.3.2 |
| 22 oct | 84–93 | `tools/formatos/corpus/encuestas/E01…E10` | Corrida válida: 143/143. E11–E13 se rechazaron con 422, como se esperaba, y por eso no tienen id | Y.3.2 |
| 22 oct | 94 | `tools/formatos/corpus/entrevistas/I01_transcripcion.txt` | Intento sin documento publicado. No se reporta | — |
| 22 oct | 95–99 | `tools/formatos/corpus/entrevistas/I01…I05` | Corridas 1 y 2 de la matriz de entrevistas: 36/39 y 37/39 | Y.4.7 |
| 22 oct | 100–104 | Las mismas I01…I05 | Corrida final: 39/39; postura 0.875 / κ 0.785 | Y.4.7 |
| 22 oct | 105–106 | `tools/formatos/corpus/entrevistas_docentes/D01_transcripcion.txt`, `D02_zoom.txt` | Segundo tema: 16/16; κ 0.804 | Y.4.7 |
| 22 oct | 107–108 | I01 y D01, reprocesadas | Contra la anotación de la investigadora: 81.2 % → 87.5 % | Y.4.7 |
| 22 oct | 109 | `storage/instrumentos_sinteticos/encuestas/enc_11_respondido.csv` | Seis tipos de pregunta; 44 y 33 de 160, iguales al CSV; estructura con sus secciones | Y.2.1 |
| 24 oct | 113–122 | `evidencias/limpieza_2026-10-24/enc_11_*` y `pru_01_*` (control y con errores) | Limpieza con errores inyectados: 35 de 47 antes y 47 de 47 después de corregir. Borrados el 25 oct | Y.2.2 |
| 24–25 oct | 110–112 | `…/pruebas/pru_02_respondido.csv`, `pru_04_respondido.csv`, `pru_10_respondido.csv` | Pruebas procesadas con la versión que las calificaba. Borradas el 25 oct | — |
| 26–28 oct | 124–126 | enc_01 limpia y sucia; `Encuesta2_Simulada_2000_SUCIA.csv` | Subidas por la investigadora; la de 2000 se volvió a subir como 127 después de los arreglos de la limpieza. Borradas | Y.2.3 |
| 28 oct | 127 | `Encuesta2_Simulada_2000_SUCIA.csv` con su PDF de Google Forms | Encuesta de 2000 respondentes; regresión del chat y comparación de modelos | Y.4.3, Y.5.1 |
| 2 nov | 129 | `storage/instrumentos_sinteticos/entrevistas/ent_11_salud_mental_ruido.txt` | Entrevista nueva con ruido contemplado; chat con un instrumento no visto | Y.4.4 |
| 2 nov | 130 | `storage/instrumentos_sinteticos/pruebas/pru_03_sucio_no_contemplado.csv` | Prueba nueva con errores no contemplados; chat con un instrumento no visto | Y.4.4 |
| 4 nov | 131 | `…/entrevistas/ent_11_salud_mental_ruido_no_contemplado.txt` | La misma entrevista con ruido no contemplado | Y.4.4 |
| 4 nov | 132 | `…/entrevistas/ent_11_salud_mental_ruido.txt` | Segunda carga de la 129; se quedó en «limpio». No se reporta | — |
| 8 nov | 133 | `storage/instrumentos_sinteticos/pruebas/pru_06_respondido.csv` | Prueba de control de la evaluación final del chat, ajena al diseño | Y.4.6 |
<!-- fuente: evidencias/pruebas_2026-10-22/inventario_instrumentos.txt (consulta a tt_rag.raw_data, instrumento_procesado, limpieza_ejecucion, version_conocimiento, respuesta_interpretada y kpi_inferido, 22 oct); registro 15–22 oct; RESULTADO.md de evidencias/encuesta_sin_secciones_2026-10-20 y evidencias/formatos_2026-10-21 -->

Los instrumentos borrados del 15 y 16 oct no conservan su número en la base; sus resultados quedan en
el registro de las sesiones. **El 25 oct se borraron, por decisión de la investigadora, los instrumentos de
prueba 62–108 y 113–122**, por la vía oficial (`DELETE /instrumentos/{id}`, que elimina filas, archivos y
vectores). Sus resultados quedan en `evidencias/`. Después del 24 oct se habían agregado las pruebas 110–112
(pru_02, pru_04 y pru_10) y los controles de errores inyectados (113–122). **El mismo 25 oct se borraron
también las cuatro pruebas estandarizadas (55, 110, 111 y 112)**, porque se procesaron con la versión que
las calificaba; desde ese día las pruebas no se califican (Desarrollo X.5.4).

Entre el 26 y el 28 oct la investigadora subió y borró enc_01 limpia y sucia (124 y 125) y la encuesta de 2000
respondentes (126, que se volvió a subir como 127 después de los arreglos de la limpieza). **El 28 oct se borraron
los JSON iniciales de la demostración (2–20) y enc_04 (22)**, por la misma vía, para dejar una versión limpia del
sistema; con ellos se retiraron `seed_demo.py` y los archivos `inst_XX` de `storage/raw/`. **Al 28 oct quedaban en la
base 59, 60, 61, 109 y 127**, los instrumentos del conjunto de regresión del chat (Pruebas Y.4.3), y ninguna prueba
estandarizada. El 2 y el 4 nov se agregaron 129 a 132 (Tabla A.1).
<!-- fuente: DELETE /instrumentos/{id} de 2–20 y 22 (28 oct, 200 en los 20); consulta a tt_rag.raw_data (28 oct: 59, 60, 61, 109, 127) -->

## A.5 Instrumentos usados solo fuera del sistema

Se usaron para cálculos sobre el CSV, sin subirlos:
- enc_01, enc_04 y enc_10_turno, para comparar los criterios de Horn y Kaiser de las dimensiones sugeridas (Pruebas Y.3.3);
- enc_09, para la estadística de la limpieza (Desarrollo X.7.2).

Sus archivos están en `storage/instrumentos_sinteticos/encuestas/`.
