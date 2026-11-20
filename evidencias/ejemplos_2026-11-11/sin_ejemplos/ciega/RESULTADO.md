# Prueba de aritmética, conjunto «ciega»: el sistema completo

Correctas: 7 de 20

| ID | Inst. | Pregunta | Esperado | Sistema |
|---|---|---|---|---|
| B01 | 59 | ¿Cuántos estudiantes consideran que las relaciones entre compañeros son respetuosas? | 29 de 60 | ✘ |
| B02 | 59 | Entre los hombres, ¿qué porcentaje no está de acuerdo con que los profesores están disponibles para resolver dudas? | 19.2 % (5 de 26) | ✘ |
| B03 | 59 | ¿Cuántos alumnos del turno matutino están en desacuerdo con que reciben retroalimentación a tiempo para mejorar? | 1 de 30 | ✔ |
| B04 | 59 | En el turno vespertino, ¿qué porcentaje se siente parte de la comunidad escolar? | 43.3 % (13 de 30) | ✘ |
| B05 | 59 | ¿Cuántos están de acuerdo tanto con que las calificaciones reflejan lo aprendido como con que las evaluaciones se relacionan con la clase? | 13 de 60 | ✘ |
| B06 | 61 | ¿Cuántos estudiantes no trabajan? | 40 de 160 | ✘ |
| B07 | 61 | ¿Qué porcentaje usa una app digital como su principal estrategia para gestionar el tiempo? | 24.4 % (39 de 160) | ✔ |
| B08 | 61 | En las universidades privadas, ¿cuántos estudiantes cursan 7 o más materias? | 14 de 56 | ✔ |
| B09 | 61 | En promedio, ¿cuántos créditos cursan los estudiantes este semestre? | 25.26 | ✘ |
| B10 | 61 | ¿Qué porcentaje deja con frecuencia las tareas para el último momento? | 43.8 % (70 de 160) | ✔ |
| B11 | 61 | ¿Cuántos estudiantes que no trabajan dicen tener dificultades para equilibrar trabajo y estudios? | 24 de 160 | ✘ |
| B12 | 61 | ¿Cuántos estudiantes nunca han reprobado una materia por falta de tiempo? | 37 de 160 | ✘ |
| B13 | 61 | De los estudiantes de universidad mixta, ¿qué porcentaje dice que su institución no ofrece talleres de gestión del tiempo? | 47.6 % (10 de 21) | ✘ |
| B14 | 127 | ¿Qué porcentaje de los estudiantes usa una plataforma virtual diariamente? | 46.0 % (887 de 1930) | ✔ |
| B15 | 127 | ¿Cuántos estudiantes están considerando abandonar sus estudios? | 159 de 1942 | ✘ |
| B16 | 127 | ¿Cuántos dicen que su programa no cuenta con acreditación vigente? | 284 de 1951 | ✘ |
| B17 | 127 | ¿Qué porcentaje ve probable volver a estudiar en esta institución? | 50.4 % (943 de 1872) | ✘ |
| B18 | 127 | ¿Cuántos estudiantes de modalidad mixta o híbrida están buscando empleo? | 143 de 1896 | ✘ |
| B19 | 127 | ¿Qué porcentaje está de acuerdo con que encuentra lo que necesita en la biblioteca y las bases de datos académicas? | 38.8 % (734 de 1892) | ✔ |
| B20 | 127 | ¿Cuántos estudiantes hicieron prácticas profesionales en una empresa con convenio de su institución? | 382 de 1931 | ✔ |

## Respuestas

### B01 (esperado: 29 de 60; rag_log 3334)
«Encuesta de evaluación y ambiente escolar por turno» no registra «consideran». En p06 («Las relaciones entre compañeros son respetuosas.») las opciones que sí existen son estas:

**Distribución de p06 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Totalmente en desacuerdo | 2 | 3.3 % |
| En desacuerdo | 11 | 18.3 % |
| Ni de acuerdo ni en desacuerdo | 18 | 30.0 % |
| De acuerdo | 14 | 23.3 % |
| Totalmente de acuerdo | 15 | 25.0 % |

### B02 (esperado: 19.2 % (5 de 26); rag_log 3335)
La consulta no indica de qué pregunta se trata. [Fuente 1]

### B03 (esperado: 1 de 30; rag_log 3336)
1 de los 30 con turno = «Matutino» que respondieron p03 (3.3 %) cumplen el criterio: turno = «Matutino» y p03 «Recibo retroalimentación sobre mis trabajos a tiempo para mejorar.» = «En desacuerdo». Sobre el total del instrumento son 1 de 60 respondentes (1.7 %). [Fuente 1]

### B04 (esperado: 43.3 % (13 de 30); rag_log 3337)
30 de 60 respondentes (50.0 %) cumplen el criterio: turno = «Vespertino». [Fuente 1]

### B05 (esperado: 13 de 60; rag_log 3338)
16 de 60 respondentes (26.7 %) cumplen el criterio: p02 «Las calificaciones reflejan lo que realmente aprendí.» = «De acuerdo». [Fuente 1]

### B06 (esperado: 40 de 160; rag_log 3339)
De acuerdo con la Encuesta, 73 de 97 (75.3 %) de los estudiantes dedicaron entre 0 y 28 horas por semana al estudio fuera de clases [Fuente 1].

### B07 (esperado: 24.4 % (39 de 160); rag_log 3340)
El 24.4 % de los estudiantes usan una app digital como su principal estrategia para gestionar el tiempo [Fuente 1].

### B08 (esperado: 14 de 56; rag_log 3341)
14 de los 56 con tipo_universidad = «privada» que respondieron p09 (25.0 %) cumplen el criterio: tipo_universidad = «privada» y p09 «¿Cuántas materias cursas actualmente?» = «7 o más». Sobre el total del instrumento son 14 de 160 respondentes (8.8 %). [Fuente 1]

### B09 (esperado: 25.26; rag_log 3342)
*   El grupo “privada” (tipo_universidad) respondió con un 82.1 % a la pregunta p05 «Planifico mis actividades con anticipación usando agendas o calendarios», mientras que el grupo “mixta” lo hizo en un 9.5 %. [Fuente 1] Esto sugiere una diferencia de 72.6 puntos entre los dos grupos en cuanto a la planificación académica.
*   La pregunta p18 «Del 1 al 10, ¿cuánta presión sientes por la carga académica?» tuvo una desviación estándar de 2.88 puntos. [Fuente 1] Esto indica una amplia gama de respuestas sobre el nivel de presión percibida.
*   El 60.6 % de los encuestados respondieron “no” a la pregunta p16 «¿Tu institución ofrece talleres de gestión del tiempo?» [Fuente 1].
*   El 51.9 % de los encuestados respondieron “sí” a la pregunta p15 «¿Tienes dificultades para equilibrar trabajo y estudios?» [Fuente 1].

### B10 (esperado: 43.8 % (70 de 160); rag_log 3343)
El 43.8% deja las tareas con frecuencia para el último momento [Fuente 1].

### B11 (esperado: 24 de 160; rag_log 3344)
«Encuesta de Carga Académica y Gestión del Tiempo» no registra «tener». En p15 («¿Tienes dificultades para equilibrar trabajo y estudios?») las opciones que sí existen son estas:

**Distribución de p15 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Sí | 83 | 51.9 % |
| No | 77 | 48.1 % |

### B12 (esperado: 37 de 160; rag_log 3345)
9 de 160 respondentes (5.6 %) cumplen el criterio: p10 «¿Con qué frecuencia dejas tareas para el último momento?» = «Nunca» y p13 «¿Has reprobado alguna materia por falta de tiempo para estudiar?» = «nunca». [Fuente 1]

### B13 (esperado: 47.6 % (10 de 21); rag_log 3346)
21 de 160 respondentes (13.1 %) cumplen el criterio: tipo_universidad = «mixta». [Fuente 1]

### B14 (esperado: 46.0 % (887 de 1930); rag_log 3347)
887 de los 1930 que respondieron p09 (46.0 %) cumplen el criterio: p09 «¿Con qué frecuencia usas alguna plataforma virtual (Moodle, Classroom,» = «Diariamente». Sobre el total del instrumento son 887 de 2000 respondentes (44.4 %). [Fuente 1]

### B15 (esperado: 159 de 1942; rag_log 3348)
*   57.8 % de quienes respondieron (respondieron «Nunca» o «Rara vez») a la pregunta p05 «¿Con qué frecuencia te ha tocado un cambio de profesor ya iniciado el periodo, o una materia sin profesor asignado?» [Fuente 1]. Podría indicar una necesidad de mejorar la estabilidad del profesorado y la gestión de recursos.
*   61.7 % de quienes respondieron (respondieron «No lo se») a la pregunta p08 «¿Sabes si la institución ha obtenido patentes en los últimos años?» [Fuente 1]. Sugiere un desconocimiento general sobre la actividad de investigación e innovación de la institución.
*   50.4 % de quienes respondieron (respondieron «4 en escala 1–5» o «Muy probable») a la pregunta p13 «¿Qué tan probable es que vuelvas a estudiar en esta institución (especialización, maestría, doctorado)?» [Fuente 1]. Sugiere un nivel de satisfacción general con la institución y su oferta académica.
*   65.1 % de quienes respondieron (respondieron «Carga media/normal») a la pregunta p03 «¿Cómo es tu carga académica actual?» [Fuente 1]. Sugiere que la mayoría de los estudiantes perciben su carga académica como adecuada, aunque se observa una desviación en las respuestas entre cargas máxima y mínima.

### B16 (esperado: 284 de 1951; rag_log 3349)
El instrumento tiene 2000 respondentes. [Fuente 1]

### B17 (esperado: 50.4 % (943 de 1872); rag_log 3350)
«Indicadores de Experiencia y Calidad Académica» no registra «volver». En p13 («¿Qué tan probable es que vuelvas a estudiar en esta institución (especialización») las opciones que sí existen son estas:

**Distribución de p13 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Nada probable | 145 | 7.7 % |
| 2 en escala 1–5 | 343 | 18.3 % |
| 3 en escala 1–5 | 441 | 23.6 % |
| 4 en escala 1–5 | 470 | 25.1 % |
| Muy probable | 473 | 25.3 % |

### B18 (esperado: 143 de 1896; rag_log 3351)
«Indicadores de Experiencia y Calidad Académica» no registra «buscando». En p02 («¿En qué modalidad cursas tu programa?») las opciones que sí existen son estas:

**Distribución de p02 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Presencial | 1251 | 64.2 % |
| Mixta/hibrida | 435 | 22.3 % |
| En linea | 263 | 13.5 % |

### B19 (esperado: 38.8 % (734 de 1892); rag_log 3352)
734 de los 1892 que respondieron p18 (38.8 %) cumplen el criterio: p18 «En la biblioteca y las bases de datos académicas (Scopus, IEEE Xplore,» de acuerdo (nivel alto). Sobre el total del instrumento son 734 de 2000 respondentes (36.7 %). [Fuente 1]

### B20 (esperado: 382 de 1931; rag_log 3353)
382 de los 1931 que respondieron p14 (19.8 %) cumplen el criterio: p14 «¿Has realizado prácticas profesionales o pasantías?» = «Si, en una empresa con convenio de mi institucion». Sobre el total del instrumento son 382 de 2000 respondentes (19.1 %). [Fuente 1]
