# Prueba de aritmética, conjunto «ciega»: el sistema completo

Correctas: 13 de 20

| ID | Inst. | Pregunta | Esperado | Sistema |
|---|---|---|---|---|
| B01 | 59 | ¿Cuántos estudiantes consideran que las relaciones entre compañeros son respetuosas? | 29 de 60 | ✔ |
| B02 | 59 | Entre los hombres, ¿qué porcentaje no está de acuerdo con que los profesores están disponibles para resolver dudas? | 19.2 % (5 de 26) | ✔ |
| B03 | 59 | ¿Cuántos alumnos del turno matutino están en desacuerdo con que reciben retroalimentación a tiempo para mejorar? | 1 de 30 | ✔ |
| B04 | 59 | En el turno vespertino, ¿qué porcentaje se siente parte de la comunidad escolar? | 43.3 % (13 de 30) | ✔ |
| B05 | 59 | ¿Cuántos están de acuerdo tanto con que las calificaciones reflejan lo aprendido como con que las evaluaciones se relacionan con la clase? | 13 de 60 | ✘ |
| B06 | 61 | ¿Cuántos estudiantes no trabajan? | 40 de 160 | ✔ |
| B07 | 61 | ¿Qué porcentaje usa una app digital como su principal estrategia para gestionar el tiempo? | 24.4 % (39 de 160) | ✔ |
| B08 | 61 | En las universidades privadas, ¿cuántos estudiantes cursan 7 o más materias? | 14 de 56 | ✔ |
| B09 | 61 | En promedio, ¿cuántos créditos cursan los estudiantes este semestre? | 25.26 | ✔ |
| B10 | 61 | ¿Qué porcentaje deja con frecuencia las tareas para el último momento? | 43.8 % (70 de 160) | ✘ |
| B11 | 61 | ¿Cuántos estudiantes que no trabajan dicen tener dificultades para equilibrar trabajo y estudios? | 24 de 160 | ✘ |
| B12 | 61 | ¿Cuántos estudiantes nunca han reprobado una materia por falta de tiempo? | 37 de 160 | ✘ |
| B13 | 61 | De los estudiantes de universidad mixta, ¿qué porcentaje dice que su institución no ofrece talleres de gestión del tiempo? | 47.6 % (10 de 21) | ✔ |
| B14 | 127 | ¿Qué porcentaje de los estudiantes usa una plataforma virtual diariamente? | 46.0 % (887 de 1930) | ✔ |
| B15 | 127 | ¿Cuántos estudiantes están considerando abandonar sus estudios? | 159 de 1942 | ✘ |
| B16 | 127 | ¿Cuántos dicen que su programa no cuenta con acreditación vigente? | 284 de 1951 | ✘ |
| B17 | 127 | ¿Qué porcentaje ve probable volver a estudiar en esta institución? | 50.4 % (943 de 1872) | ✘ |
| B18 | 127 | ¿Cuántos estudiantes de modalidad mixta o híbrida están buscando empleo? | 143 de 1896 | ✔ |
| B19 | 127 | ¿Qué porcentaje está de acuerdo con que encuentra lo que necesita en la biblioteca y las bases de datos académicas? | 38.8 % (734 de 1892) | ✔ |
| B20 | 127 | ¿Cuántos estudiantes hicieron prácticas profesionales en una empresa con convenio de su institución? | 382 de 1931 | ✔ |

## Respuestas

### B01 (esperado: 29 de 60; rag_log 2981)
Criterio: de acuerdo (nivel alto) en p06.
p06 «Las relaciones entre compañeros son respetuosas.»: 29 de 60 de quienes respondieron están de acuerdo (nivel alto) (48.3 %). [Fuente 1]

### B02 (esperado: 19.2 % (5 de 26); rag_log 2982)
5 de los 26 con genero = «masculino» que respondieron p07 (19.2 %) cumplen el criterio: genero = «masculino» y p07 «Los profesores están disponibles para resolver dudas.» en desacuerdo (nivel bajo). Sobre el total del instrumento son 5 de 60 respondentes (8.3 %). [Fuente 1]

### B03 (esperado: 1 de 30; rag_log 2983)
Según los datos registrados, 35 de 97 (36.3 %) estudiantes del turno matutino respondieron “Totalmente en desacuerdo” con la pregunta p03 [Fuente 1].

### B04 (esperado: 43.3 % (13 de 30); rag_log 2984)
13 de los 30 con turno = «Vespertino» que respondieron p08 (43.3 %) cumplen el criterio: turno = «Vespertino» y p08 «Me siento parte de la comunidad escolar.» de acuerdo (nivel alto). Sobre el total del instrumento son 13 de 60 respondentes (21.7 %). [Fuente 1]

### B05 (esperado: 13 de 60; rag_log 2985)
5 de 60 respondentes (8.3 %) cumplen el criterio: p02 «Las calificaciones reflejan lo que realmente aprendí.» = «De acuerdo» y p04 «Las evaluaciones están relacionadas con lo que se ve en clase.» = «De acuerdo». [Fuente 1]

### B06 (esperado: 40 de 160; rag_log 2986)
40 de 160 respondentes (25.0 %) cumplen el criterio: p14 «¿Cuál es tu carga laboral actual?» = «No trabajo». [Fuente 1]

### B07 (esperado: 24.4 % (39 de 160); rag_log 2987)
39 de 160 respondentes (24.4 %) cumplen el criterio: p11 «¿Qué estrategia usas más para gestionar tu tiempo?» = «App digital». [Fuente 1]

### B08 (esperado: 14 de 56; rag_log 2988)
14 de los 56 con tipo_universidad = «privada» que respondieron p09 (25.0 %) cumplen el criterio: tipo_universidad = «privada» y p09 «¿Cuántas materias cursas actualmente?» = «7 o más». Sobre el total del instrumento son 14 de 160 respondentes (8.8 %). [Fuente 1]

### B09 (esperado: 25.26; rag_log 2989)
Criterio: resumen de p20.
p20 «¿Cuántos créditos cursas este semestre? (número)»: 160 respuestas válidas; media 25.26.
Interpretación calculada: Media 25.3, mediana 26 (de 10 a 40). [Fuente 1]

### B10 (esperado: 43.8 % (70 de 160); rag_log 2991)
37 de 160 respondentes (23.1 %) cumplen el criterio: p10 «¿Con qué frecuencia dejas tareas para el último momento?» = «Frecuentemente». [Fuente 1]

### B11 (esperado: 24 de 160; rag_log 2993)
40 de 160 respondentes (25.0 %) cumplen el criterio: p14 «¿Cuál es tu carga laboral actual?» = «No trabajo». [Fuente 1] Según la pregunta p15 de la encuesta «Encuesta de Carga Académica y Gestión del Tiempo», se evalúa si los estudiantes que no tienen carga laboral actual presentan dificultades para conciliar sus obligaciones laborales y académicas. [Fuente 1]

### B12 (esperado: 37 de 160; rag_log 2995)
9 de 160 respondentes (5.6 %) cumplen el criterio: p13 «¿Has reprobado alguna materia por falta de tiempo para estudiar?» = «nunca» y p10 «¿Con qué frecuencia dejas tareas para el último momento?» = «Nunca». [Fuente 1]

### B13 (esperado: 47.6 % (10 de 21); rag_log 2996)
10 de los 21 con tipo_universidad = «mixta» que respondieron p16 (47.6 %) cumplen el criterio: tipo_universidad = «mixta» y p16 «¿Tu institución ofrece talleres de gestión del tiempo?» = «No». Sobre el total del instrumento son 10 de 160 respondentes (6.2 %). [Fuente 1]

### B14 (esperado: 46.0 % (887 de 1930); rag_log 2997)
887 de los 1930 que respondieron p09 (46.0 %) cumplen el criterio: p09 «¿Con qué frecuencia usas alguna plataforma virtual (Moodle, Classroom,» = «Diariamente». Sobre el total del instrumento son 887 de 2000 respondentes (44.4 %). [Fuente 1]

### B15 (esperado: 159 de 1942; rag_log 2998)
No encontré esa condición en «Indicadores de Experiencia y Calidad Académica». En p13 («¿Qué tan probable es que vuelvas a estudiar en esta institución (especialización») las opciones que sí existen son estas:

**Distribución de p13 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Nada probable | 145 | 7.7 % |
| 2 en escala 1–5 | 343 | 18.3 % |
| 3 en escala 1–5 | 441 | 23.6 % |
| 4 en escala 1–5 | 470 | 25.1 % |
| Muy probable | 473 | 25.3 % |

### B16 (esperado: 284 de 1951; rag_log 2999)
1193 de los 1951 que respondieron p01 (61.1 %) cumplen el criterio: p01 «¿Tu programa académico cuenta con acreditación vigente (COP AES, SEAES» = «No lo se» o «No». Sobre el total del instrumento son 1193 de 2000 respondentes (59.6 %). [Fuente 1]

### B17 (esperado: 50.4 % (943 de 1872); rag_log 3000)
El 25.3% (473 respuestas) de los encuestados consideraron “muy probable” que regresaran a estudiar en la institución, representando el nivel más alto en la escala de 1 a 5 [Fuente 1].  Un 25.1% (470 respuestas) respondió con un "4", indicando una probabilidad alta pero no absoluta de continuar sus estudios en la misma institución [Fuente 1]. Finalmente, el 18.3% (343 respuestas) manifestó una probabilidad del “2” en la escala de 1 a 5 [Fuente 1].

**Distribución de p13 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Nada probable | 145 | 7.7 % |
| 2 en escala 1–5 | 343 | 18.3 % |
| 3 en escala 1–5 | 441 | 23.6 % |
| 4 en escala 1–5 | 470 | 25.1 % |
| Muy probable | 473 | 25.3 % |

### B18 (esperado: 143 de 1896; rag_log 3001)
143 de los 1896 que respondieron p02 y p12 (7.5 %) cumplen el criterio: p02 «¿En qué modalidad cursas tu programa?» = «Mixta/hibrida» y p12 «¿Cuál es tu situación laboral actual?» = «Busco empleo». Sobre el total del instrumento son 143 de 2000 respondentes (7.2 %). [Fuente 1]

### B19 (esperado: 38.8 % (734 de 1892); rag_log 3002)
El 38.8 % (734 de 1892) de quienes respondieron está de acuerdo [Fuente 1].

### B20 (esperado: 382 de 1931; rag_log 3003)
Criterio: resumen de p14.
p14 «¿Has realizado prácticas profesionales o pasantías?»: 1931 respuestas válidas, 69 sin respuesta.
Interpretación calculada: La opción más frecuente es «Si, pero la consegui por mi cuenta» (37.4 % de las respuestas). [Fuente 1]

**Distribución de p14 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Si, pero la consegui por mi cuenta | 722 | 37.4 % |
| Aun no, pero planeo hacerlo | 586 | 30.3 % |
| Si, en una empresa con convenio de mi institucion | 382 | 19.8 % |
| No | 241 | 12.5 % |
