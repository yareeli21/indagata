# Anexo A. Instrumentos usados en las pruebas

<!-- fuente: consulta a tt_rag.raw_data e instrumento_procesado (8 nov 2026); storage/instrumentos_sinteticos/*/*_metadata.json; documentos finales vigentes en storage/json/<id>/; capítulos de Desarrollo y Pruebas -->

Este anexo dice, para cada instrumento que aparece en los capítulos, **qué es, de dónde salió, dónde está su archivo y
en qué pruebas se usó**. En los capítulos, cada instrumento se nombra por su número en el sistema (`id`, por ejemplo
«la encuesta 127»). Todas las respuestas son sintéticas.

## A.1 Dónde buscar

| Qué | Carpeta (desde la raíz del repositorio) | ¿Está en el repositorio? |
|---|---|---|
| Archivo que se subió al sistema, su instrumento original (cuestionario, guion o prueba en texto o PDF) y sus metadatos de generación | `storage/instrumentos_sinteticos/{encuestas,entrevistas,pruebas}/` | Sí |
| Cómo se generaron los datos sintéticos | `storage/instrumentos_sinteticos/METODOLOGIA_DATOS_SINTETICOS.md` y Desarrollo X.6 | Sí |
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
| 59 | Encuesta de evaluación y ambiente escolar por turno | Encuesta | 60 | 8 | `encuestas/enc_10_turno_respondido.csv` | `encuestas/enc_10_turno_original.txt` | Método B1: generada para saber de antemano la respuesta por turno (Desarrollo X.6.3) |
| 60 | Entrevista sobre estrategias de permanencia universitaria | Entrevista | 40 | 12 | `entrevistas/ent_01_respondido.txt` | `entrevistas/ent_01_original.txt` | Método A: generación por perfiles (X.6.2) |
| 61 | Encuesta de Carga Académica y Gestión del Tiempo | Encuesta | 160 | 20 | `encuestas/enc_09_respondido.csv` | `encuestas/enc_09_original.txt` | Método A (X.6.2) |
| 109 | Encuesta de Trayectoria Académica, Trabajo y Uso de Servicios | Encuesta | 160 | 26 | `encuestas/enc_11_respondido.csv` | `encuestas/enc_11_original.txt` | Método A, con los seis tipos de pregunta (X.6.2) |
| 127 | Indicadores de Experiencia y Calidad Académica | Encuesta | 2000 | 18 | `encuestas/Encuesta2_Simulada_2000_SUCIA.csv` | `encuestas/Indicadores de Experiencia y Calidad Académica - Formularios de Google.pdf` | Encuesta simulada por la investigadora, con su formulario de Google Forms; el archivo trae errores a propósito para probar la limpieza («SUCIA») |
| 129 | Salud mental en la universidad | Entrevista | 1 | 12 | `entrevistas/ent_11_salud_mental_ruido.txt` | `entrevistas/ent_11_original.txt` (versión limpia: `ent_11_salud_mental_limpia.txt`; ruido inyectado: `ent_11_ruido_inyectado.json`) | Entrevista de la investigadora con ruido de transcripción contemplado (método B5) |
| 130 | Prueba de Alfabetización Digital | Prueba estandarizada | 97 | 22 | `pruebas/pru_03_sucio_no_contemplado.csv` | `pruebas/pru_03_original.txt` (sin errores: `pru_03_respondido.csv`; errores: `pru_03_ruido_no_contemplado.json`) | Prueba de la investigadora con errores no contemplados por la limpieza (método B5), entre ellos un reactivo vacío para todos (r10) |
| 131 | Salud mental entrevista | Entrevista | 1 | 13 | `entrevistas/ent_11_salud_mental_ruido_no_contemplado.txt` | `entrevistas/ent_11_original.txt` (errores: `ent_11_ruido_no_contemplado.json`) | La misma entrevista con ruido no contemplado (método B5) |
| 132 | — (sin publicar) | Entrevista | 1 | — | `entrevistas/ent_11_salud_mental_ruido.txt` | — | Segunda carga de la 129; quedó en «limpio» y no se reporta |
| 133 | Prueba de Competencia en Investigación Científica | Prueba estandarizada | 80 | 15 | `pruebas/pru_06_respondido.csv` | `pruebas/pru_06_original.txt` | Método A; cargada el 8 nov como prueba de control, ajena al diseño del chat |
<!-- fuente: tt_rag.raw_data (nombre_archivo, raw_archivo, raw_archivo_original); documentos finales vigentes: storage/json/59/1__v1, 60/484__v2, 61/21__v2, 109/3__v3, 127/54__v4, 129/49__v8, 130/1__v2, 131/1__v1 y 133/1__v1 _documento_final.json -->

**Documento final vigente** (el que leyó el chat en la evaluación final): `storage/json/<id>/` con el número de
versión más alto; por ejemplo, `storage/json/127/54__v4_documento_final.json`.

## A.3 En qué pruebas se usó cada instrumento

**Tabla A.2.** Pruebas por instrumento vigente.

| id | Pruebas | Dónde se reporta | Evidencia |
|---|---|---|---|
| 59 | Flujo completo; respuesta conocida (4 de 30 del turno vespertino); encuesta sin secciones; regresión del chat; chunks en *tokens* | Pruebas Y.2.1, Y.3.3, Y.4, Y.4.12; Desarrollo X.9.1 | `evidencias/encuesta_sin_secciones_2026-10-20/`, `evidencias/chunks_2026-11-07/` |
| 60 | Flujo completo; regresión del chat; **set de control de la evaluación final** (8 casos CET); análisis de lo que se cuenta, solo con reglas | Pruebas Y.2.1, Y.4.12, Y.4.14; Desarrollo X.7.8 | `evidencias/chat_2026-11-07_control_antes/`, `evidencias/chat_2026-11-08_final_control/` |
| 61 | Filtros y calidad de los datos; regresión; **set de control** (8 casos CEN); polaridad propuesta sin revisar | Pruebas Y.2.1, Y.4.3, Y.4.6, Y.4.12, Y.4.14; Desarrollo X.7.7 | `evidencias/chat_2026-11-08_final_control/`, `evidencias/nlp_formato_2026-11-07/` |
| 109 | Seis tipos de pregunta; banco de preguntas con respuesta verificada; chunks en *tokens* | Pruebas Y.2.1, Y.4.11; Desarrollo X.9.1 | `evidencias/banco_2026-10-24/`, `evidencias/chunks_2026-11-07/` |
| 127 | Limpieza con errores reales; regresión del rediseño; comparación de modelos redactor × juez; **batería de encuesta de la evaluación final** (25 casos ENC más 4 de cortesía GEN); polaridad revisada por la investigadora; chunks en *tokens* | Desarrollo X.7.2, X.7.7, X.9.1, X.9.6; Pruebas Y.4.12, Y.5.2, Y.4.14 | `evidencias/modelos_2026-11-02/`, `evidencias/chat_2026-11-07_antes/`, `evidencias/chat_2026-11-08_final/` |
| 129 | Instrumento nuevo con ruido de transcripción; **batería de entrevista de la evaluación final** (25 casos ENT); análisis de lo que se cuenta con el modelo (Tabla D.23.1) | Pruebas Y.4.13, Y.4.14; Desarrollo X.7.8 | `evidencias/nlp_formato_2026-11-07/`, `evidencias/chat_2026-11-08_final/` |
| 130 | Instrumento nuevo con errores no contemplados; **batería de prueba de la evaluación final** (25 casos PRU); chunks en *tokens* | Pruebas Y.4.13, Y.4.14; Desarrollo X.9.1 | `evidencias/chat_2026-11-08_final/` |
| 131 | La misma entrevista con ruido no contemplado | Pruebas Y.4.13 | — |
| 133 | **Set de control de la evaluación final** (8 casos CPR) | Pruebas Y.4.14 | `evidencias/chat_2026-11-08_final_control/` |

Las preguntas de cada caso (ENC, PRU, ENT, GEN y el control CEN, CET y CPR), con lo que la respuesta debe contener,
están en `tools/rag/baterias_chat.json`. La respuesta del chat a cada caso y su calificación están en
`evidencias/<carpeta>/casos/<caso>.json` y `calificacion_debe.json`.

## A.4 Instrumentos que se usaron y ya no están en el sistema

Los instrumentos de las primeras pruebas (15 al 25 oct) se borraron por decisión de la investigadora, por la vía
oficial (`DELETE /instrumentos/{id}`), después de guardar sus resultados en `evidencias/`. La Tabla P.1a de Pruebas
Y.1.4 los lista con su número, su archivo y la sección donde se reportan. Sus archivos fuente siguen en
`storage/instrumentos_sinteticos/` (enc_04, enc_05, pru_01, pru_02, pru_04, pru_10), en
`tools/formatos/corpus/` (matrices de formatos de encuestas y entrevistas) y en `evidencias/` (variantes sin secciones,
copias con errores inyectados).

## A.5 Instrumentos usados solo fuera del sistema

Se usaron para cálculos sobre el CSV, sin subirlos (Pruebas Y.1.4):
- enc_01, enc_04 y enc_10_turno, para comparar los criterios de Horn y Kaiser de las dimensiones sugeridas (Y.3.5);
- enc_06 a enc_11, para verificar el modelo coherente de respuestas (Desarrollo X.6.2);
- enc_09, para recalcular el α por separado y la estadística de la limpieza (Desarrollo X.6.2, X.7.2).

Sus archivos están en `storage/instrumentos_sinteticos/encuestas/`.
