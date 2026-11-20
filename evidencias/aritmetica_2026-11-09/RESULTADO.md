# Prueba de aritmética: el modelo calcula frente al código calcula

| ID | Inst. | Pregunta | Esperado | A. Solo RAG | B. Modelo con datos | C. Sistema |
|---|---|---|---|---|---|---|
| A01 | 59 | ¿Qué porcentaje del turno vespertino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase? | 13.3 % (4 de 30) | ✘ | ✘ | ✘ |
| A02 | 59 | ¿Qué porcentaje del turno matutino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase? | 56.7 % (17 de 30) | ✘ | ✘ | ✘ |
| A03 | 59 | ¿Cuántos respondentes están en desacuerdo con que las calificaciones reflejan lo que realmente aprendieron? | 15 de 60 | ✘ | ✘ | ✔ |
| A04 | 59 | ¿Qué porcentaje de los respondentes está de acuerdo con sentirse parte de la comunidad escolar? | 50.0 % (30 de 60) | ✔ | ✘ | ✔ |
| A05 | 59 | ¿Cuántas mujeres están de acuerdo con que se sienten seguras dentro de las instalaciones de la escuela? | 14 de 34 | ✘ | ✘ | ✘ |
| A06 | 59 | ¿Qué porcentaje del turno vespertino está en desacuerdo con que los criterios de evaluación se explican con claridad? | 40.0 % (12 de 30) | ✘ | ✘ | ✔ |
| A07 | 61 | ¿Cuántos estudiantes trabajan más de 30 horas? | 37 de 160 | ✔ | ✘ | ✔ |
| A08 | 61 | ¿Qué porcentaje de los estudiantes tiene dificultades para equilibrar trabajo y estudios? | 51.9 % (83 de 160) | ✔ | ✘ | ✔ |
| A09 | 61 | ¿Cuántos estudiantes han reprobado alguna materia por falta de tiempo para estudiar? | 88 de 160 | ✔ | ✘ | ✘ |
| A10 | 61 | ¿Cuál es el promedio de horas por semana que los estudiantes dedican al estudio fuera de clases? | 27.23 | ✔ | ✘ | ✘ |
| A11 | 61 | ¿Cuántos estudiantes de universidad pública dicen que su institución ofrece talleres de gestión del tiempo? | 31 de 83 | ✘ | ✘ | ✘ |
| A12 | 61 | ¿Qué porcentaje de los estudiantes está de acuerdo con que tiene tiempo suficiente para estudiar cada materia? | 43.8 % (70 de 160) | ✘ | ✘ | ✘ |
| A13 | 61 | ¿Cuántos estudiantes que trabajan más de 30 horas tienen dificultades para equilibrar trabajo y estudios? | 14 de 160 | ✘ | ✘ | ✔ |
| A14 | 127 | ¿Cuántos estudiantes llevan carga académica máxima? | 486 de 1931 | ✔ | no cabe | ✔ |
| A15 | 127 | ¿Qué porcentaje de los estudiantes cursa su programa en línea? | 13.5 % (263 de 1949) | ✔ | no cabe | ✘ |
| A16 | 127 | ¿Qué porcentaje está en desacuerdo con que los laboratorios, equipos y espacios son adecuados para su formación? | 37.7 % (721 de 1911) | ✔ | no cabe | ✘ |
| A17 | 127 | ¿Cuántos estudiantes trabajan en un área relacionada con su carrera? | 500 de 1946 | ✘ | no cabe | ✔ |
| A18 | 127 | ¿Cuántos estudiantes presentaron un examen de certificación profesional y lo aprobaron? | 379 de 1952 | ✔ | no cabe | ✘ |
| A19 | 127 | ¿Qué porcentaje espera titularse en el tiempo que marca su plan de estudios? | 19.7 % (382 de 1942) | ✔ | no cabe | ✔ |
| A20 | 127 | ¿Cuántos estudiantes de modalidad presencial llevan carga académica máxima? | 316 de 1881 | ✘ | no cabe | ✔ |

| Condición | Correctas |
|---|---|
| A. Solo RAG | 10 de 20 (50.0 %) |
| B. Modelo con datos | 0 de 13 (0.0 %) |
| C. Sistema | 10 de 20 (50.0 %) |

## Respuestas

### A01 — ¿Qué porcentaje del turno vespertino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase? (esperado: 13.3 % (4 de 30))
- **A:** 35.0 %
- **B:** El número total de personas que dieron respuesta "De acuerdo" al turno vespertino es 26.
- **C:** Criterio: turno = «Vespertino» y p04 «Las evaluaciones están relacionadas con lo que se ve en clase.» de acuerdo (nivel alto).
Cumplen la condición 4 de 60 respondentes (6.7 %). [Fuente 1]

### A02 — ¿Qué porcentaje del turno matutino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase? (esperado: 56.7 % (17 de 30))
- **A:** 35.0 % del turno matutino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase.
- **B:** El número de personas de turno matutino que expresaron acuerdo es 13.
- **C:** Criterio: turno = «Matutino» y p04 «Las evaluaciones están relacionadas con lo que se ve en clase.» de acuerdo (nivel alto).
Cumplen la condición 17 de 60 respondentes (28.3 %). [Fuente 1]

### A03 — ¿Cuántos respondentes están en desacuerdo con que las calificaciones reflejan lo que realmente aprendieron? (esperado: 15 de 60)
- **A:** El número exacto de respondientes que se encuentran en desacuerdo con la pregunta p02 es 46, representando un 31.7% del total de respuestas válidas (145).
- **B:** Hay un total de 23 estudiantes que respondieron "En desacuerdo" con la pregunta sobre si las calificaciones reflejan lo aprendido.
- **C:** Criterio: en desacuerdo (nivel bajo) en p02.
p02 «Las calificaciones reflejan lo que realmente aprendí.»: 15 de 60 de quienes respondieron están en desacuerdo (nivel bajo) (25.0 %). [Fuente 1]

### A04 — ¿Qué porcentaje de los respondentes está de acuerdo con sentirse parte de la comunidad escolar? (esperado: 50.0 % (30 de 60))
- **A:** 50.0 %.
- **B:** El número total de personas que expresaron "De acuerdo" es 34. Por lo tanto, el porcentaje de respondientes que están de acuerdo con sentirse parte de la comunidad escolar es del 34%.
- **C:** 30 de 60 de quienes respondieron están de acuerdo (50.0 %) con el criterio “Me siento parte de la comunidad escolar.” [Fuente 1]

### A05 — ¿Cuántas mujeres están de acuerdo con que se sienten seguras dentro de las instalaciones de la escuela? (esperado: 14 de 34)
- **A:** No se proporciona información sobre el género de los encuestados en ninguno de los datos proporcionados. Por lo tanto, no puedo determinar cuántas mujeres están de acuerdo con sentirse seguras.
- **B:** Hay 23 mujeres que han expresado estar de acuerdo con la pregunta.
- **C:** Criterio: p05 «Me siento seguro dentro de las instalaciones de la escuela.» de acuerdo (nivel alto).
Cumplen la condición 25 de 60 respondentes (41.7 %). [Fuente 1]

### A06 — ¿Qué porcentaje del turno vespertino está en desacuerdo con que los criterios de evaluación se explican con claridad? (esperado: 40.0 % (12 de 30))
- **A:** 25.0 %
- **B:** Hay 23 personas en el turno vespertino que han expresado estar en desacuerdo, lo que representa un 36.8% del total de respuestas del turno vespertino.
- **C:** El 40.0 % (12 de 30) del grupo de estudiantes del turno Vespertino está en desacuerdo con que los criterios de evaluación se explican con claridad al inicio del curso [Fuente 1].

### A07 — ¿Cuántos estudiantes trabajan más de 30 horas? (esperado: 37 de 160)
- **A:** 37 estudiantes.
- **B:** 7
- **C:** 37 de 160 respondentes (23.1 %) cumplen la condición p14 «¿Cuál es tu carga laboral actual?» [Fuente 1].

### A08 — ¿Qué porcentaje de los estudiantes tiene dificultades para equilibrar trabajo y estudios? (esperado: 51.9 % (83 de 160))
- **A:** 51.9 %.
- **B:** El número total de respuestas "No" a la pregunta "p15" es 96. Por lo tanto, el porcentaje de estudiantes que tienen dificultades para equilibrar trabajo y estudios es del 96%.
- **C:** Según la Encuesta de Carga Académica y Gestión del Tiempo, un 51.9% de los estudiantes reporta tener dificultades para equilibrar su trabajo y sus estudios [Fuente 1]. Esta distribución se basa en 83 respuestas afirmativas obtenidas de un total de 160 respuestas válidas [Fuente 1]. El porcentaje de estudiantes que no experimentan dificultades en este equilibrio es del 48.1%, reflejado en 77 respuestas [Fuente 1].

**Distribución de p15 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Sí | 83 | 51.9 % |
| No | 77 | 48.1 % |

### A09 — ¿Cuántos estudiantes han reprobado alguna materia por falta de tiempo para estudiar? (esperado: 88 de 160)
- **A:** 88
- **B:** 27
- **C:** Criterio: resumen de p09.
p09 «¿Cuántas materias cursas actualmente?»: 160 respuestas válidas.
Interpretación calculada: La opción más frecuente es «5-6» (25.6 % de las respuestas). [Fuente 1]

**Distribución de p09 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| 5-6 | 41 | 25.6 % |
| 7 o más | 41 | 25.6 % |
| 1-2 | 40 | 25.0 % |
| 3-4 | 38 | 23.8 % |

### A10 — ¿Cuál es el promedio de horas por semana que los estudiantes dedican al estudio fuera de clases? (esperado: 27.23)
- **A:** 27.23 horas.
- **B:** El promedio de horas por semana que los estudiantes dedican al estudio fuera de clases es de 30.45 horas.
- **C:** Según la Encuesta de Carga Académica y Gestión del Tiempo, 39 estudiantes (24.4%) dedicaron menos de 5 horas al estudio fuera de clases por semana [Fuente 1].  Asimismo, 34 estudiantes (21.2%) informaron haber dedicado más de 20 horas semanales al estudio [Fuente 1], mientras que 33 estudiantes (20.6%) indicaron entre 10 y 15 horas [Fuente 1]. Finalmente, 28 estudiantes (17.5%) reportaron dedicar entre 5 y 10 horas a estudiar fuera de clases semanalmente [Fuente 1].

**Distribución de p12 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Menos de 5h | 39 | 24.4 % |
| Más de 20h | 34 | 21.2 % |
| 10-15h | 33 | 20.6 % |
| 5-10h | 28 | 17.5 % |
| 15-20h | 26 | 16.2 % |

### A11 — ¿Cuántos estudiantes de universidad pública dicen que su institución ofrece talleres de gestión del tiempo? (esperado: 31 de 83)
- **A:** 63.
- **B:** Hay 35 estudiantes de universidad pública que dicen que su institución ofrece talleres de gestión del tiempo.
- **C:** 83 de 160 respondientes (51.9 %) cumplen la condición tipo_universidad = «publica» [Fuente 1]. La encuesta «Encuesta de Carga Académica y Gestión del Tiempo» indica que el 51.9% de los estudiantes universitarios públicos en México afirman que su institución ofrece talleres de gestión del tiempo [Fuente 1].

### A12 — ¿Qué porcentaje de los estudiantes está de acuerdo con que tiene tiempo suficiente para estudiar cada materia? (esperado: 43.8 % (70 de 160))
- **A:** 95.0% de los estudiantes están de acuerdo con que tienen tiempo suficiente para estudiar cada materia, según la pregunta p03 de la encuesta "Encuesta de Carga Académica y Gestión del Tiempo", donde la escala es de 1 a 5.
- **B:** De acuerdo / Frecuentemente: 46
De acuerdo / Frecuentemente: 13
Totalmente de acuerdo / Siempre: 8
Ni de acuerdo ni en desacuerdo / A veces: 40
En desacuerdo / Pocas veces: 15
- **C:** Según la encuesta «Encuesta de Carga Académica y Gestión del Tiempo», el 40.0% (14 de 35) del grupo “Casi lo hago” está de acuerdo con que tiene tiempo suficiente para estudiar, mientras que el 51.4% (19 de 37) del grupo “No, nunca” también coincide en esta afirmación. El grupo “Sí, una vez” y el grupo “Sí, varias veces” muestran un porcentaje similar, con el 41.9% (18 de 43) y el 42.2% (19 de 45) respectivamente que están de acuerdo [Fuente 1].

**Comparación por p13 «¿Has reprobado alguna materia por falta de tiempo para estudiar?» [Fuente 1]**
| Grupo | Personas | p03: de acuerdo (nivel alto) |
|---|---|---|
| Casi lo hago | 35 | 40.0 % (14 de 35) |
| No, nunca | 37 | 51.4 % (19 de 37) |
| Sí, una vez | 43 | 41.9 % (18 de 43) |
| Sí, varias veces | 45 | 42.2 % (19 de 45) |

### A13 — ¿Cuántos estudiantes que trabajan más de 30 horas tienen dificultades para equilibrar trabajo y estudios? (esperado: 14 de 160)
- **A:** 83
- **B:** 7
- **C:** Criterio: p14 «¿Cuál es tu carga laboral actual?» = «Trabajo más de 30h» y p15 «¿Tienes dificultades para equilibrar trabajo y estudios?» = «Sí».
Cumplen la condición 14 de 160 respondentes (8.8 %). [Fuente 1]

### A14 — ¿Cuántos estudiantes llevan carga académica máxima? (esperado: 486 de 1931)
- **A:** 486
- **B:** no cabe: 24636 tokens de datos en una ventana de 8192
- **C:** 486 de 2000 estudiantes (24.3%) indican que tienen una carga académica máxima [Fuente 1]. La pregunta p03 de la encuesta «Indicadores de Experiencia y Calidad Académica» evalúa cómo es su carga académica actual, con opciones de Carga media/normal, Cargas maxima y Carga minima [Fuente 1].

### A15 — ¿Qué porcentaje de los estudiantes cursa su programa en línea? (esperado: 13.5 % (263 de 1949))
- **A:** 13.5 %.
- **B:** no cabe: 21965 tokens de datos en una ventana de 8192
- **C:** Criterio: p02 «¿En qué modalidad cursas tu programa?» = «En linea».
Cumplen la condición 263 de 2000 respondentes (13.2 %). [Fuente 1]

### A16 — ¿Qué porcentaje está en desacuerdo con que los laboratorios, equipos y espacios son adecuados para su formación? (esperado: 37.7 % (721 de 1911))
- **A:** 37.7 %
- **B:** no cabe: 25241 tokens de datos en una ventana de 8192
- **C:** 36.0% de los 2000 respondientes (721 de 2000) están en desacuerdo con que los laboratorios, equipos, materiales y espacios de la institución son adecuados para su formación [Fuente 1].

### A17 — ¿Cuántos estudiantes trabajan en un área relacionada con su carrera? (esperado: 500 de 1946)
- **A:** No se puede determinar el número exacto de estudiantes que trabajan en un área relacionada con su carrera a partir de los datos proporcionados.
- **B:** no cabe: 28755 tokens de datos en una ventana de 8192
- **C:** Criterio: p12 «¿Cuál es tu situación laboral actual?» = «Trabajo en un area relacionada con mi carrera».
Cumplen la condición 500 de 2000 respondentes (25.0 %). [Fuente 1]

### A18 — ¿Cuántos estudiantes presentaron un examen de certificación profesional y lo aprobaron? (esperado: 379 de 1952)
- **A:** 379
- **B:** no cabe: 27917 tokens de datos en una ventana de 8192
- **C:** 625 de 2000 respondientes (31.2 %) cumplieron la condición p11 [Fuente 1]. Las opciones seleccionadas fueron: No, pero planeo hacerlo; No, y no lo planeo; Si, y lo aprobe; Si, y no lo aprobe [Fuente 1].

### A19 — ¿Qué porcentaje espera titularse en el tiempo que marca su plan de estudios? (esperado: 19.7 % (382 de 1942))
- **A:** 19.7% del total de estudiantes respondió que esperaban titularse en el tiempo que marca su plan de estudios, según los datos fuente="3".
- **B:** no cabe: 29737 tokens de datos en una ventana de 8192
- **C:** Criterio: resumen de p10.
p10 «¿Cuándo esperas titularte?»: 1942 respuestas válidas, 58 sin respuesta.
Interpretación calculada: La opción más frecuente es «Con hasta un año de retraso» (37.4 % de las respuestas). [Fuente 1]

**Distribución de p10 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Con hasta un año de retraso | 726 | 37.4 % |
| Con mas de un año de retraso | 503 | 25.9 % |
| En el tiempo que marca mi plan de estudios | 382 | 19.7 % |
| No estoy seguro(a) | 172 | 8.9 % |
| Estoy considerando abandonar | 159 | 8.2 % |

### A20 — ¿Cuántos estudiantes de modalidad presencial llevan carga académica máxima? (esperado: 316 de 1881)
- **A:** No se proporciona información específica sobre la cantidad de estudiantes de modalidad presencial que llevan carga académica máxima.
- **B:** no cabe: 39192 tokens de datos en una ventana de 8192
- **C:** Criterio: p03 «¿Cómo es tu carga académica actual?» = «Cargas maxima» y p02 «¿En qué modalidad cursas tu programa?» = «Presencial».
Cumplen la condición 316 de 2000 respondentes (15.8 %). [Fuente 1]
