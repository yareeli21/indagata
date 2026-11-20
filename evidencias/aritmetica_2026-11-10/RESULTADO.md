# Segunda prueba de aritmética (10 nov): base del porcentaje corregida

Solo el sistema completo (C), sin caché, en las preguntas cuyo porcentaje dependía de la base. A06 se repite porque su plan usa la misma forma que A01 con nivel dentro del grupo.

| ID | Esperado | Primera prueba | Segunda prueba |
|---|---|---|---|
| A01 | 13.3 % (4 de 30) | ✘ | ✔ |
| A02 | 56.7 % (17 de 30) | ✘ | ✔ |
| A06 | 40.0 % (12 de 30) | ✔ | ✔ |
| A15 | 13.5 % (263 de 1949) | ✘ | ✔ |
| A16 | 37.7 % (721 de 1911) | ✘ | ✔ |
| A20 | 316 de 1881 | ✔ | ✔ |

## Respuestas

### A01 — ¿Qué porcentaje del turno vespertino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase? (esperado: 13.3 % (4 de 30))
- **Primera prueba:** Criterio: turno = «Vespertino» y p04 «Las evaluaciones están relacionadas con lo que se ve en clase.» de acuerdo (nivel alto).
Cumplen la condición 4 de 60 respondentes (6.7 %). [Fuente 1]
- **Segunda prueba** (rag_log 2933): 4 de los 30 con turno = «Vespertino» que respondieron p04 (13.3 %) cumplen el criterio: turno = «Vespertino» y p04 «Las evaluaciones están relacionadas con lo que se ve en clase.» de acuerdo (nivel alto). Sobre el total del instrumento son 4 de 60 respondentes (6.7 %). [Fuente 1]

### A02 — ¿Qué porcentaje del turno matutino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase? (esperado: 56.7 % (17 de 30))
- **Primera prueba:** Criterio: turno = «Matutino» y p04 «Las evaluaciones están relacionadas con lo que se ve en clase.» de acuerdo (nivel alto).
Cumplen la condición 17 de 60 respondentes (28.3 %). [Fuente 1]
- **Segunda prueba** (rag_log 2929): 17 de los 30 con turno = «Matutino» que respondieron p04 (56.7 %) cumplen el criterio: turno = «Matutino» y p04 «Las evaluaciones están relacionadas con lo que se ve en clase.» de acuerdo (nivel alto). Sobre el total del instrumento son 17 de 60 respondentes (28.3 %). [Fuente 1]

### A06 — ¿Qué porcentaje del turno vespertino está en desacuerdo con que los criterios de evaluación se explican con claridad? (esperado: 40.0 % (12 de 30))
- **Primera prueba:** El 40.0 % (12 de 30) del grupo de estudiantes del turno Vespertino está en desacuerdo con que los criterios de evaluación se explican con claridad al inicio del curso [Fuente 1].
- **Segunda prueba** (rag_log 2934): El 40.0 % (12 de 30) del grupo de estudiantes del turno Vespertino está en desacuerdo con que los criterios de evaluación se explican con claridad al inicio del curso [Fuente 1].

### A15 — ¿Qué porcentaje de los estudiantes cursa su programa en línea? (esperado: 13.5 % (263 de 1949))
- **Primera prueba:** Criterio: p02 «¿En qué modalidad cursas tu programa?» = «En linea».
Cumplen la condición 263 de 2000 respondentes (13.2 %). [Fuente 1]
- **Segunda prueba** (rag_log 2930): 263 de los 1949 que respondieron p02 (13.5 %) cumplen el criterio: p02 «¿En qué modalidad cursas tu programa?» = «En linea». Sobre el total del instrumento son 263 de 2000 respondentes (13.2 %). [Fuente 1]

### A16 — ¿Qué porcentaje está en desacuerdo con que los laboratorios, equipos y espacios son adecuados para su formación? (esperado: 37.7 % (721 de 1911))
- **Primera prueba:** 36.0% de los 2000 respondientes (721 de 2000) están en desacuerdo con que los laboratorios, equipos, materiales y espacios de la institución son adecuados para su formación [Fuente 1].
- **Segunda prueba** (rag_log 2931): 721 de los 1911 que respondieron p17 (37.7 %) cumplen el criterio: p17 «Los laboratorios, equipos, materiales y espacios de la institución son» en desacuerdo (nivel bajo). Sobre el total del instrumento son 721 de 2000 respondentes (36.0 %). [Fuente 1]

### A20 — ¿Cuántos estudiantes de modalidad presencial llevan carga académica máxima? (esperado: 316 de 1881)
- **Primera prueba:** Criterio: p03 «¿Cómo es tu carga académica actual?» = «Cargas maxima» y p02 «¿En qué modalidad cursas tu programa?» = «Presencial».
Cumplen la condición 316 de 2000 respondentes (15.8 %). [Fuente 1]
- **Segunda prueba** (rag_log 2932): 316 de los 1881 que respondieron p03 y p02 (16.8 %) cumplen el criterio: p03 «¿Cómo es tu carga académica actual?» = «Cargas maxima» y p02 «¿En qué modalidad cursas tu programa?» = «Presencial». Sobre el total del instrumento son 316 de 2000 respondentes (15.8 %). [Fuente 1]

## Nota: primer intento de A01 (rag_log 2928)

Con la base ya corregida, el modelo escribió el plan de A01 como «nivel de acuerdo en p04 dentro del turno» (la forma
de A06). El código calculó 4 de 30 (13.3 %), pero la frase de la respuesta se armó con el tamaño del grupo («30 de 60
respondentes cumplen turno = Vespertino») y la cifra correcta no apareció. Se corrigió la frase del dato en esa forma
del plan (`ejecutor._conteo_porcentaje`) y se repitió A01. La respuesta del primer intento está en
`A01_antes_de_la_frase_del_nivel.json`.

Resultado del sistema con las 20 preguntas: 14 de 20 (antes 10 de 20). Las 6 que siguen fallando (A05, A09, A10, A11,
A12 y A18) son de interpretación del plan, no de cálculo.
