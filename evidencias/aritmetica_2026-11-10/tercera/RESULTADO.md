# Tercera prueba de aritmética (10 nov): fallas de interpretación corregidas

Solo el sistema completo (C), sin caché, en las 6 preguntas que fallaron por interpretación del plan.

| ID | Esperado | Primera prueba | Tercera prueba | Qué se corrigió |
|---|---|---|---|---|
| A05 | 14 de 34 | ✘ | ✔ | «mujeres» nombra genero = femenino (equivalencias en config/dominio.yaml) |
| A09 | 88 de 160 | ✘ | ✔ | la mención «reprobar materias» es el texto de p13: filtro p13 = «Sí…» |
| A10 | 27.23 | ✘ | ✔ | «promedio» usa la pregunta numérica p17 en lugar de los rangos de p12 |
| A11 | 31 de 83 | ✘ | ✔ | la mención «talleres de gestión del tiempo» es p16: filtro p16 = «Sí» |
| A12 | 43.8 % (70 de 160) | ✘ | ✔ | «está de acuerdo con» no es «según»; «qué porcentaje… de acuerdo» es un conteo en ese nivel; el mismo nivel como filtro y como nivel es una sola condición |
| A18 | 379 de 1952 | ✘ | ✔ | «…y lo aprobaron» distingue «Si, y lo aprobe»: no se juntan todas las «Sí…» |

Resultado del sistema con las 20 preguntas: 20 de 20 (primera prueba 10, segunda 14).

## Intentos intermedios de A12

- `A12_antes_del_nivel.json` (rag_log 2939): ya sin la comparación «según p13», pero resumió p03 (distribución) en lugar del porcentaje de acuerdo. Se agregó: «qué porcentaje / cuántos… de acuerdo» sobre una pregunta de escala es un conteo en ese nivel.
- `A12_antes_del_filtro_repetido.json` (rag_log 2941): el plan quedó con «p03 de acuerdo» como filtro y como nivel; el porcentaje salió sobre quienes ya estaban de acuerdo (70 de 70, 100 %). Se corrigió en el ejecutor: es una sola condición.

## Respuestas

### A05 — ¿Cuántas mujeres están de acuerdo con que se sienten seguras dentro de las instalaciones de la escuela? (esperado: 14 de 34)
- **Primera prueba:** Criterio: p05 «Me siento seguro dentro de las instalaciones de la escuela.» de acuerdo (nivel alto).
Cumplen la condición 25 de 60 respondentes (41.7 %). [Fuente 1]
- **Tercera prueba** (rag_log 2935): 14 de los 34 con genero = «femenino» que respondieron p05 (41.2 %) cumplen el criterio: genero = «femenino» y p05 «Me siento seguro dentro de las instalaciones de la escuela.» de acuerdo (nivel alto). Sobre el total del instrumento son 14 de 60 respondentes (23.3 %). [Fuente 1]

### A09 — ¿Cuántos estudiantes han reprobado alguna materia por falta de tiempo para estudiar? (esperado: 88 de 160)
- **Primera prueba:** Criterio: resumen de p09.
p09 «¿Cuántas materias cursas actualmente?»: 160 respuestas válidas.
Interpretación calculada: La opción más frecuente es «5-6» (25.6 % de las respuestas). [Fuente 1]

**Distribución de p09 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| 5-6 | 41 | 25.6 % |
| 7 o más | 41 | 25.6 % |
| 1-2 | 40 | 25.0 % |
| 3-4 | 38 | 23.8 % |
- **Tercera prueba** (rag_log 2936): 88 de 160 respondentes (55.0 %) cumplen el criterio: p13 «¿Has reprobado alguna materia por falta de tiempo para estudiar?» = «Sí». [Fuente 1]

### A10 — ¿Cuál es el promedio de horas por semana que los estudiantes dedican al estudio fuera de clases? (esperado: 27.23)
- **Primera prueba:** Según la Encuesta de Carga Académica y Gestión del Tiempo, 39 estudiantes (24.4%) dedicaron menos de 5 horas al estudio fuera de clases por semana [Fuente 1].  Asimismo, 34 estudiantes (21.2%) informaron haber dedicado más de 20 horas semanales al estudio [Fuente 1], mientras que 33 estudiantes (20.6%) indicaron entre 10 y 15 horas [Fuente 1]. Finalmente, 28 estudiantes (17.5%) reportaron dedicar entre 5 y 10 horas a estudiar fuera de clases semanalmente [Fuente 1].

**Distribución de p12 [Fuente 1]**
| Opción | Respondentes | % |
|---|---|---|
| Menos de 5h | 39 | 24.4 % |
| Más de 20h | 34 | 21.2 % |
| 10-15h | 33 | 20.6 % |
| 5-10h | 28 | 17.5 % |
| 15-20h | 26 | 16.2 % |
- **Tercera prueba** (rag_log 2937): El promedio de horas que los estudiantes dedican al estudio fuera de clases por semana es de 27.23 horas, según la Encuesta de Carga Académica y Gestión del Tiempo [Fuente 1]. La mediana de estas horas es de 28.5 horas, con una escala que va de 0 a 50 [Fuente 1]. Esta media se obtuvo a partir de 160 respuestas válidas recogidas en la encuesta [Fuente 1].


### A11 — ¿Cuántos estudiantes de universidad pública dicen que su institución ofrece talleres de gestión del tiempo? (esperado: 31 de 83)
- **Primera prueba:** 83 de 160 respondientes (51.9 %) cumplen la condición tipo_universidad = «publica» [Fuente 1]. La encuesta «Encuesta de Carga Académica y Gestión del Tiempo» indica que el 51.9% de los estudiantes universitarios públicos en México afirman que su institución ofrece talleres de gestión del tiempo [Fuente 1].
- **Tercera prueba** (rag_log 2938): 31 de los 83 con tipo_universidad = «publica» que respondieron p16 (37.3 %) cumplen el criterio: tipo_universidad = «publica» y p16 «¿Tu institución ofrece talleres de gestión del tiempo?» = «Sí». Sobre el total del instrumento son 31 de 160 respondentes (19.4 %). [Fuente 1]

### A12 — ¿Qué porcentaje de los estudiantes está de acuerdo con que tiene tiempo suficiente para estudiar cada materia? (esperado: 43.8 % (70 de 160))
- **Primera prueba:** Según la encuesta «Encuesta de Carga Académica y Gestión del Tiempo», el 40.0% (14 de 35) del grupo “Casi lo hago” está de acuerdo con que tiene tiempo suficiente para estudiar, mientras que el 51.4% (19 de 37) del grupo “No, nunca” también coincide en esta afirmación. El grupo “Sí, una vez” y el grupo “Sí, varias veces” muestran un porcentaje similar, con el 41.9% (18 de 43) y el 42.2% (19 de 45) respectivamente que están de acuerdo [Fuente 1].

**Comparación por p13 «¿Has reprobado alguna materia por falta de tiempo para estudiar?» [Fuente 1]**
| Grupo | Personas | p03: de acuerdo (nivel alto) |
|---|---|---|
| Casi lo hago | 35 | 40.0 % (14 de 35) |
| No, nunca | 37 | 51.4 % (19 de 37) |
| Sí, una vez | 43 | 41.9 % (18 de 43) |
| Sí, varias veces | 45 | 42.2 % (19 de 45) |
- **Tercera prueba** (rag_log 2942): Criterio: de acuerdo (nivel alto) en p03.
p03 «Tengo tiempo suficiente para estudiar cada materia adecuadamente.»: 70 de 160 de quienes respondieron están de acuerdo (nivel alto) (43.8 %). [Fuente 1]

### A18 — ¿Cuántos estudiantes presentaron un examen de certificación profesional y lo aprobaron? (esperado: 379 de 1952)
- **Primera prueba:** 625 de 2000 respondientes (31.2 %) cumplieron la condición p11 [Fuente 1]. Las opciones seleccionadas fueron: No, pero planeo hacerlo; No, y no lo planeo; Si, y lo aprobe; Si, y no lo aprobe [Fuente 1].
- **Tercera prueba** (rag_log 2940): 379 de los 1952 que respondieron p11 (19.4 %) cumplen el criterio: p11 «¿Has presentado algún examen de certificación profesional (A WS, Cisco» = «Si, y lo aprobe». Sobre el total del instrumento son 379 de 2000 respondentes (18.9 %). [Fuente 1]
