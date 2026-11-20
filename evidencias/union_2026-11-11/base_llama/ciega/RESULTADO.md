# Prueba de aritmética, conjunto «ciega»: el sistema completo

Correctas: 9 de 20

| ID | Inst. | Pregunta | Esperado | Sistema |
|---|---|---|---|---|
| B01 | 59 | ¿Cuántos estudiantes consideran que las relaciones entre compañeros son respetuosas? | 29 de 60 | ✘ |
| B02 | 59 | Entre los hombres, ¿qué porcentaje no está de acuerdo con que los profesores están disponibles para resolver dudas? | 19.2 % (5 de 26) | ✘ |
| B03 | 59 | ¿Cuántos alumnos del turno matutino están en desacuerdo con que reciben retroalimentación a tiempo para mejorar? | 1 de 30 | ✔ |
| B04 | 59 | En el turno vespertino, ¿qué porcentaje se siente parte de la comunidad escolar? | 43.3 % (13 de 30) | ✘ |
| B05 | 59 | ¿Cuántos están de acuerdo tanto con que las calificaciones reflejan lo aprendido como con que las evaluaciones se relacionan con la clase? | 13 de 60 | ✔ |
| B06 | 61 | ¿Cuántos estudiantes no trabajan? | 40 de 160 | ✔ |
| B07 | 61 | ¿Qué porcentaje usa una app digital como su principal estrategia para gestionar el tiempo? | 24.4 % (39 de 160) | ✔ |
| B08 | 61 | En las universidades privadas, ¿cuántos estudiantes cursan 7 o más materias? | 14 de 56 | ✘ |
| B09 | 61 | En promedio, ¿cuántos créditos cursan los estudiantes este semestre? | 25.26 | ✔ |
| B10 | 61 | ¿Qué porcentaje deja con frecuencia las tareas para el último momento? | 43.8 % (70 de 160) | ✘ |
| B11 | 61 | ¿Cuántos estudiantes que no trabajan dicen tener dificultades para equilibrar trabajo y estudios? | 24 de 160 | ✘ |
| B12 | 61 | ¿Cuántos estudiantes nunca han reprobado una materia por falta de tiempo? | 37 de 160 | ✘ |
| B13 | 61 | De los estudiantes de universidad mixta, ¿qué porcentaje dice que su institución no ofrece talleres de gestión del tiempo? | 47.6 % (10 de 21) | ✘ |
| B14 | 127 | ¿Qué porcentaje de los estudiantes usa una plataforma virtual diariamente? | 46.0 % (887 de 1930) | ✔ |
| B15 | 127 | ¿Cuántos estudiantes están considerando abandonar sus estudios? | 159 de 1942 | ✔ |
| B16 | 127 | ¿Cuántos dicen que su programa no cuenta con acreditación vigente? | 284 de 1951 | ✘ |
| B17 | 127 | ¿Qué porcentaje ve probable volver a estudiar en esta institución? | 50.4 % (943 de 1872) | ✘ |
| B18 | 127 | ¿Cuántos estudiantes de modalidad mixta o híbrida están buscando empleo? | 143 de 1896 | ✔ |
| B19 | 127 | ¿Qué porcentaje está de acuerdo con que encuentra lo que necesita en la biblioteca y las bases de datos académicas? | 38.8 % (734 de 1892) | ✔ |
| B20 | 127 | ¿Cuántos estudiantes hicieron prácticas profesionales en una empresa con convenio de su institución? | 382 de 1931 | ✘ |

## Respuestas

### B01 (esperado: 29 de 60; rag_log 3385)
*   50.0 %: El 50.0 % de los estudiantes que respondieron a la pregunta p06 consideran que las relaciones entre compañeros son respetuosas.
*   La pregunta p08 «Me siento parte de la comunidad escolar.» tiene el mayor porcentaje de respuestas de acuerdo, pero no se relaciona directamente con la pregunta sobre las relaciones entre compañeros.

### B02 (esperado: 19.2 % (5 de 26); rag_log 3386)
9 de 60 respondentes (15.0 %) cumplen el criterio: p07 «Los profesores están disponibles para resolver dudas.» = «De acuerdo» y p08 «Me siento parte de la comunidad escolar.» = «De acuerdo». [Fuente 1]

### B03 (esperado: 1 de 30; rag_log 3387)
Según la encuesta, no se proporciona información sobre el número de alumnos que están en desacuerdo con recibir retroalimentación a tiempo para mejorar. La pregunta p03 (Recibo retroalimentación sobre mis trabajos a tiempo para mejorar) está relacionada con la evaluación del aprendizaje y tiene una escala de 1 a 5, pero no se proporciona información sobre el número de alumnos que respondieron en desacuerdo.

Sin embargo, se menciona que la pregunta p04 (Las evaluaciones están relacionadas con lo que se ve en clase) está relacionada con la misma escala y KPI. Sin embargo, esta pregunta también no proporciona información sobre el número de alumnos que están en desacuerdo con recibir retroalimentación a tiempo para mejorar.

### B04 (esperado: 43.3 % (13 de 30); rag_log 3388)
Criterio: resumen de p08.
p08 «Me siento parte de la comunidad escolar.»: 60 respuestas válidas; media 3.35.
Interpretación calculada: Respuestas divididas: 50 % acuerdo, 33.3 % neutral, 16.7 % desacuerdo. [Fuente 1]

**Distribución de p08 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Totalmente en desacuerdo | 2 | 3.3 % |
| En desacuerdo | 8 | 13.3 % |
| Ni de acuerdo ni en desacuerdo | 20 | 33.3 % |
| De acuerdo | 27 | 45.0 % |
| Totalmente de acuerdo | 3 | 5.0 % |

### B05 (esperado: 13 de 60; rag_log 3389)
13 de 60 respondentes (21.7 %) cumplen el criterio: p02 «Las calificaciones reflejan lo que realmente aprendí.» de acuerdo (nivel alto) y p04 «Las evaluaciones están relacionadas con lo que se ve en clase.» de acuerdo (nivel alto). [Fuente 1]

### B06 (esperado: 40 de 160; rag_log 3390)
40 de 160 respondentes (25.0 %) cumplen el criterio: p14 «¿Cuál es tu carga laboral actual?» = «No trabajo». [Fuente 1]

### B07 (esperado: 24.4 % (39 de 160); rag_log 3391)
39 de 160 respondentes (24.4 %) cumplen el criterio: p11 «¿Qué estrategia usas más para gestionar tu tiempo?» = «App digital». [Fuente 1]

### B08 (esperado: 14 de 56; rag_log 3392)
- En p05 «Planifico mis actividades con anticipación usando agendas o calendarios.», el grupo «privada» (tipo_universidad) está en el nivel alto en un 82.1 % y el grupo «mixta» en un 9.5 %: 72.6 puntos de diferencia.
- La pregunta con las opiniones más divididas es p18 «Del 1 al 10, ¿cuánta presión sientes por la carga académica?»: desviación estándar de 2.88 puntos en la escala.
- La pregunta con más respuestas en «no» es p16 «¿Tu institución ofrece talleres de gestión del tiempo?»: 60.6 % de quienes respondieron. [Fuente 1]

### B09 (esperado: 25.26; rag_log 3393)
«Encuesta de Carga Académica y Gestión del Tiempo» no registra «promedio». En p20 («¿Cuántos créditos cursas este semestre? (número)») las opciones que sí existen son estas:

Criterio: resumen de p20.
p20 «¿Cuántos créditos cursas este semestre? (número)»: 160 respuestas válidas; media 25.26.
Interpretación calculada: Media 25.3, mediana 26 (de 10 a 40). [Fuente 1]

### B10 (esperado: 43.8 % (70 de 160); rag_log 3394)
No encontré esa condición en «Encuesta de Carga Académica y Gestión del Tiempo». En p10 («¿Con qué frecuencia dejas tareas para el último momento?») las opciones que sí existen son estas:

**Distribución de p10 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Nunca | 30 | 18.8 % |
| Raramente | 28 | 17.5 % |
| A veces | 32 | 20.0 % |
| Frecuentemente | 37 | 23.1 % |
| Siempre | 33 | 20.6 % |

### B11 (esperado: 24 de 160; rag_log 3395)
40 de 160 respondentes (25.0 %) cumplen el criterio: p14 «¿Cuál es tu carga laboral actual?» = «No trabajo». [Fuente 1]

### B12 (esperado: 37 de 160; rag_log 3396)
9 de 160 respondentes (5.6 %) cumplen el criterio: p13 «¿Has reprobado alguna materia por falta de tiempo para estudiar?» = «nunca» y p10 «¿Con qué frecuencia dejas tareas para el último momento?» = «Nunca». [Fuente 1]

### B13 (esperado: 47.6 % (10 de 21); rag_log 3397)
Según la encuesta "Encuesta de Carga Académica y Gestión del Tiempo" [Fuente 1], se pregunta a los estudiantes si su institución ofrece talleres de gestión del tiempo. La respuesta es la siguiente:

<datos>
- respuesta: R017 en p16 (Sí)
</datos>

Sin embargo, no se proporciona información sobre el porcentaje de estudiantes que respondieron "No" a esta pregunta. Por lo tanto, no puedo proporcionar un porcentaje específico.

Si deseas saber si hay algún KPI asociado con esta pregunta, es posible que sea relacionado con la diversidad de la oferta académica o las métricas de compromiso e interacción del estudiante en plataformas virtuales.

### B14 (esperado: 46.0 % (887 de 1930); rag_log 3398)
887 de los 1930 que respondieron p09 (46.0 %) cumplen el criterio: p09 «¿Con qué frecuencia usas alguna plataforma virtual (Moodle, Classroom,» = «Diariamente». Sobre el total del instrumento son 887 de 2000 respondentes (44.4 %). [Fuente 1]

### B15 (esperado: 159 de 1942; rag_log 3399)
159 de los 1942 que respondieron p10 (8.2 %) cumplen el criterio: p10 «¿Cuándo esperas titularte?» = «Estoy considerando abandonar». Sobre el total del instrumento son 159 de 2000 respondentes (8.0 %). [Fuente 1] El criterio se refiere a que los estudiantes esperan abandonar sus estudios si no logran titularse dentro de un plazo determinado. Según la pregunta, los estudiantes pueden elegir entre cuatro opciones: con hasta un año de retraso, más de un año de retraso, en el tiempo que marca su plan de estudios o considerando abandonar. El criterio se cumple cuando los estudiantes eligen la opción "considerando abandonar".

### B16 (esperado: 284 de 1951; rag_log 3400)
1193 de los 1951 que respondieron p01 (61.1 %) cumplen el criterio: p01 «¿Tu programa académico cuenta con acreditación vigente (COP AES, SEAES» = «No lo se» o «No». Sobre el total del instrumento son 1193 de 2000 respondentes (59.6 %). [Fuente 1]

### B17 (esperado: 50.4 % (943 de 1872); rag_log 3401)
473 de los 1872 que respondieron p13 (25.3 %) cumplen el criterio: p13 «¿Qué tan probable es que vuelvas a estudiar en esta institución (espec» = «Muy probable». Sobre el total del instrumento son 473 de 2000 respondentes (23.6 %). [Fuente 1]

### B18 (esperado: 143 de 1896; rag_log 3402)
143 de los 1896 que respondieron p02 y p12 (7.5 %) cumplen el criterio: p02 «¿En qué modalidad cursas tu programa?» = «Mixta/hibrida» y p12 «¿Cuál es tu situación laboral actual?» = «Busco empleo». Sobre el total del instrumento son 143 de 2000 respondentes (7.2 %). [Fuente 1]

### B19 (esperado: 38.8 % (734 de 1892); rag_log 3403)
En la pregunta p18 «En la biblioteca y las bases de datos académicas (Scopus, IEEE Xplore, EBSCO, etc.) encuentro lo que necesito para mis materias y proyectos.», el 38.8 % (734 de 1892) de quienes respondieron está de acuerdo. [Fuente 1]

### B20 (esperado: 382 de 1931; rag_log 3404)
- La pregunta con más respuestas en el nivel bajo es p05 «¿Con qué frecuencia te ha tocado un cambio de profesor ya iniciado el periodo, o una materia sin profesor asignado?»: 57.8 % de quienes respondieron (respondieron «Nunca» o «Rara vez»).
- La pregunta con más respuestas en el nivel alto es p13 «¿Qué tan probable es que vuelvas a estudiar en esta institución (especialización, maestría, doctorado)?»: 50.4 % de quienes respondieron (respondieron «4 en escala 1–5» o «Muy probable»).
- En p03 «¿Cómo es tu carga académica actual?» predomina «Carga media/normal»: 65.1 % de quienes respondieron. [Fuente 1]
