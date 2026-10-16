# Medidas estadísticas de la limpieza: qué significan

Guía para investigadores. Explica las cifras de las pestañas **Estadística** y **Antes y después**, que aparecen en la vista final del paso «Limpieza» al subir un instrumento.

> **Para qué sirve esta pestaña.** No es el análisis final de tu investigación. Sirve para comprobar, antes de pasar a metadatos, que los datos limpios tienen sentido: que las escalas son consistentes, que no quedaron valores raros y que la limpieza no deformó los datos.

Los ejemplos salen de una encuesta real de la plataforma: 180 encuestados, 26 ítems Likert de 1 a 5 agrupados en bloques («Aportación…», «Dedicación…», …) y la pregunta `horas_trabajo_semana`.

---

## 1. Fiabilidad: alfa de Cronbach (encuestas)

**Qué mide.** Si los ítems de un mismo bloque «miden lo mismo». Cuando alguien califica alto un ítem de *Dedicación*, ¿también califica alto los demás de ese bloque? Si sí, el bloque es consistente y tiene sentido sumar o promediar sus ítems.

**Cómo se lee** (George y Mallery, 2003):

| α | Interpretación |
|---|---|
| ≥ 0.9 | Excelente |
| 0.8 – 0.9 | Buena |
| 0.7 – 0.8 | Aceptable (el mínimo habitual en investigación) |
| 0.6 – 0.7 | Cuestionable |
| 0.5 – 0.6 | Pobre |
| < 0.5 | Inaceptable |

**Cuidados al leerlo:**
- **Crece con el número de ítems.** Con 20 o más ítems, el α sale alto casi siempre, aunque mezcle temas distintos.
- **Más de 0.95 no siempre es bueno.** Puede indicar ítems redundantes, es decir, la misma pregunta dicha de varias formas.
- **Debe calcularse por dimensión** (un α por bloque o constructo), no sobre todo el cuestionario. La fila «Todas las escalas Likert» es una referencia global y no reemplaza el α por bloque.
- **Ítems invertidos.** Un ítem redactado en negativo («Nunca recibo retroalimentación…») baja el α si no se invierte. Cuando confirmas en la fase asistida que un ítem es invertido, se recodifica antes de calcular el α.

**«26 ítems · 180 casos completos».** Solo se usan las personas que respondieron **todos** los ítems del bloque. Si se excluyen muchos casos, el α es menos representativo.

**Botón «Por ítem».** Muestra dos columnas por ítem:
- **Correlación ítem-total corregida:** qué tanto se relaciona el ítem con el resto del bloque.
  - Menor a 0.3: el ítem «va por su lado» y conviene revisarlo.
  - Negativa: casi siempre es un ítem invertido que no se marcó.
- **Alfa si se elimina el ítem:** el α que tendría el bloque sin ese ítem. Si es **mayor** que el α actual, el ítem le resta consistencia. Se marca en naranja.

**Ejemplo.** «Todas las escalas Likert: α = 0.942, excelente.» Los 26 ítems responden de forma muy coherente entre sí. Pero como son 26 ítems y se mezclan varias dimensiones, ese 0.942 está inflado; lo que interesa es el α de cada bloque (ver la sección 9).

---

## 2. Estadística descriptiva (escalas y respuestas numéricas)

Hay una fila por pregunta. Estas son las columnas:

| Columna | Qué es | Cómo leerla |
|---|---|---|
| **Tipo** | Cómo clasificó la limpieza la pregunta (escala Likert, numérica, calificación…) | Si está mal, se revisan mal los rangos (ver la sección 9) |
| **n** | Respuestas válidas | Sin contar vacíos ni «No sé / No aplica» |
| **Vacíos** | % de personas que no respondieron | Más del 20 % sugiere una pregunta confusa, opcional o mal ubicada |
| **Media** | Promedio | Es sensible a valores extremos |
| **Mediana** | Valor del centro: la mitad respondió menos y la otra mitad más | No se mueve con valores extremos |
| **Desv. est.** | Qué tan dispersas están las respuestas alrededor de la media | En Likert de 1 a 5: menos de 0.6, casi todos opinan igual; alrededor de 1.1, opiniones variadas; más de 1.5, muy polarizadas |
| **Mín – Máx** | Valor más bajo y más alto | Sirve para detectar valores imposibles |
| **Q1 – Q3** | Cuartiles: el 50 % central de las respuestas está entre estos dos valores | «3 – 4» = la mitad respondió entre *neutral* y *de acuerdo* |
| **Asimetría** | Hacia dónde se carga la distribución | Ver abajo |
| **Curtosis** | Qué tan concentradas o repartidas están las respuestas | Ver abajo |
| **Atípicos σ / IQR** | Valores extremos según dos métodos | Ver abajo |

**Media frente a mediana.** Si se parecen, la distribución es equilibrada. Si la media es bastante mayor que la mediana, unos pocos valores altos la jalan hacia arriba.
- Ejemplo: en `horas_trabajo_semana`, la media es 17.69 y la mediana 14. La mayoría trabaja pocas horas, pero algunas personas trabajan muchas.

**Asimetría:**
- Entre **−0.5 y 0.5**: casi simétrica.
- **Negativa**: se acumulan las respuestas **altas** (en Likert, mucha gente de acuerdo) y hay una «cola» de pocas respuestas bajas.
- **Positiva**: se acumulan las respuestas **bajas** y hay pocos valores muy altos.
- Más allá de ±1: asimetría fuerte.
- Ejemplo: en los ítems Likert va de −0.1 a −0.44, así que se inclinan levemente hacia «de acuerdo». En horas es 0.5: pocas personas con muchas horas.

**Curtosis** (en exceso; 0 = forma de campana normal):
- **Negativa** (−0.5 a −1): respuestas **repartidas** entre varias opciones, sin un consenso claro.
- **Positiva**: respuestas **concentradas** en un solo valor (mucho consenso) o con varios valores extremos.
- Entre **−1 y 1** se considera razonable para la mayoría de los análisis.
- Ejemplo: en los ítems va de −0.45 a −0.98. La gente usa toda la escala; no hay un acuerdo unánime.

**Atípicos σ / IQR.** Dos formas de contar valores extremos:
- **σ (sigma):** valores a más de 4 desviaciones estándar de la media. Es estricto; solo marca lo muy raro.
- **IQR (rango intercuartílico):** valores por debajo de Q1 − 1.5·IQR o por encima de Q3 + 1.5·IQR. Es más sensible; es el criterio de los diagramas de caja.
- El método que genera el **hallazgo** en la fase asistida se configura en `services/cleaning-service/config/limpieza.yaml` (`estadistica.metodo_atipicos`). La tabla muestra siempre los dos.
- **En las escalas aparece «—».** En una escala Likert de 1 a 5 no existen atípicos: cualquier valor de 1 a 5 es válido, y lo que está fuera de la escala ya se reporta como «fuera de rango».

---

## 3. Frecuencias y moda

Para las preguntas de opción (Likert, categóricas, binarias) se muestra cuántas personas eligieron cada opción, con barras y porcentaje.
- La **moda** es la opción más elegida y aparece resaltada.
- En las escalas Likert aparecen **todas** las opciones en orden, incluso las que nadie eligió.
- Las respuestas «No sé / No aplica» se **excluyen** del cálculo (no son un punto de la escala), y se indica cuántas hubo.

---

## 4. Pruebas estandarizadas

| Medida | Qué es | Cómo leerla |
|---|---|---|
| **Dificultad (p)** | Proporción de alumnos que acertaron el reactivo | > 0.7 **fácil** · 0.3 – 0.7 **media** · < 0.3 **difícil**. Lo ideal es que la mayoría sean de dificultad media |
| **Discriminación (D)** | Aciertos del 27 % de alumnos con mejor puntaje menos los aciertos del 27 % con peor puntaje | ≥ 0.4 **excelente** · 0.3 – 0.4 **buena** · 0.2 – 0.3 **regular** (mejorable) · < 0.2 **pobre** (revisar). **Negativa:** los alumnos con peor puntaje aciertan más; casi siempre la clave está mal o el reactivo es confuso |
| **Punto-biserial** | Relación entre acertar el reactivo y el puntaje en el resto de la prueba | Se lee como la D: ≥ 0.3 bien; cerca de 0 o negativa, revisar |
| **Opciones elegidas** | Cuántos alumnos eligieron cada opción. La correcta va en verde | Un **distractor que nadie eligió** (naranja) no cumple su función; conviene reemplazarlo por uno más creíble |
| **Puntajes** | Media, mediana, desviación estándar y rango de aciertos | Muestra si la prueba quedó muy fácil o muy difícil para el grupo |
| **KR-20** | Fiabilidad de la prueba completa (el equivalente del α para respuestas correcta/incorrecta) | Misma tabla que el α: ≥ 0.7 aceptable. Con pocos reactivos o pocos alumnos suele salir bajo |

---

## 5. Entrevistas

Las medidas se centran en las **respuestas de los entrevistados**. Si el archivo trae varias
entrevistas (bloques `RESPONDENTE: R0001` con preguntas `P1:`… y respuestas `R:`), las preguntas
numeradas cuentan como un solo entrevistador y cada bloque es un entrevistado.

| Medida | Cómo leerla |
|---|---|
| **Entrevistados, preguntas y respuestas** | Si el corpus está completo (p. ej. 40 entrevistados × 12 preguntas = 480 respuestas) |
| **Respondieron / sin respuesta** por pregunta | Preguntas que se omitieron o no funcionaron en campo |
| **Palabras por respuesta** (media, mín., máx.) por pregunta | Profundidad de las respuestas; respuestas muy cortas pueden indicar «sí/no» o una transcripción incompleta |
| **Por entrevistado** | Preguntas respondidas y palabras de cada persona: detecta entrevistas truncadas |
| **Palabras por rol** | Entrevistado frente a entrevistador. Lo esperado es que domine el texto de las respuestas; si no, revisa los roles |

---

## 6. Antes y después

Compara el archivo **original** con el **limpio**. Cada fila tiene el valor antes, el valor después y el cambio.

| Fila | Qué esperar después de limpiar |
|---|---|
| Respondentes / Alumnos | Igual o un poco menos (se quitaron duplicados, incompletos, etc.) |
| Columnas | Menos, si se eliminaron columnas ajenas (marca temporal, IDs, etc.) |
| Completitud / Celdas vacías | La completitud sube y las celdas vacías bajan |
| Filas duplicadas, IDs repetidos | Deberían quedar en 0 |
| Valores fuera de rango | Deberían quedar en 0, o en lo que decidiste conservar |
| Respuestas en línea recta | Bajan solo si decidiste eliminarlas (lo sugerido es conservarlas) |
| Encuestados incompletos | Bajan si decidiste eliminarlos (lo sugerido) |
| Respuestas nulas / No respondidas (pruebas) | Se mantienen; quedan **marcadas** con su motivo, no se borran |
| Alfa de Cronbach · bloque / KR-20 | Debería mantenerse o subir. Si **baja mucho**, la limpieza quitó información útil o falta invertir algún ítem |

La pestaña **Estadística** también tiene el botón **Antes**, para ver las mismas tablas calculadas con los datos originales.

---

## 7. Lectura completa del ejemplo

> - **Fiabilidad:** las escalas son muy consistentes (α = 0.942). Ojo: es el α global de 26 ítems; el de cada dimensión es el que importa.
> - **Opinión general:** ligeramente positiva y cercana a neutral. Las medias van de 3.2 a 3.4 en una escala de 1 a 5, y la mediana es 3 (en un ítem, 4).
> - **Consenso:** bajo. Las respuestas se reparten por toda la escala (desviación estándar ≈ 1.1, curtosis negativa) y la mitad de las personas respondió entre «neutral» y «de acuerdo».
> - **Datos completos:** 0 % de vacíos en todas las preguntas que se ven.
> - **Horas de trabajo:** la mitad trabaja de 7 a 28 horas a la semana (mediana 14). Algunas personas llegan a 48, y eso sube la media a 17.7.

---

## 8. Glosario rápido

| Término | En una línea |
|---|---|
| n | Cuántas respuestas válidas hay |
| Media | El promedio |
| Mediana | El valor del centro |
| Desviación estándar | Qué tan diferentes son las respuestas entre sí |
| Q1 – Q3 | Donde está la mitad central de las respuestas |
| Asimetría | Si las respuestas se cargan hacia arriba (negativa) o hacia abajo (positiva) |
| Curtosis | Si las respuestas están concentradas (positiva) o repartidas (negativa) |
| Atípico | Un valor muy alejado del resto |
| Alfa de Cronbach | Si los ítems de un bloque miden lo mismo (≥ 0.7 aceptable) |
| Correlación ítem-total | Si un ítem «va de la mano» con su bloque (≥ 0.3) |
| KR-20 | El alfa de una prueba de opción múltiple |
| Dificultad p | Qué proporción acertó |
| Discriminación D | Si el reactivo separa a quienes saben de quienes no |
| Línea recta | Marcar la misma opción en todo un bloque |
| Encuestado incompleto | Dejó sin responder más de la mitad del cuestionario |

---

## 9. Lo que noté en el ejemplo (y qué se corrigió)

1. **Solo aparecía un α para todo el cuestionario.** Los encabezados tenían la forma `Aportación_en_a_item1…5`, y la limpieza solo agrupaba bloques del tipo «Pregunta [aspecto]» (el formato de Google Forms). Ahora también reconoce los sufijos `_item1`, `_1` y `.1`, y muestra un α por dimensión además del global.
2. **`horas_trabajo_semana` aparecía como «Calificación».** Una columna con valores de 0 a 100 se tomaba como calificación, así que solo se revisaba que estuviera entre 0 y 100. Ahora, si el encabezado habla de horas, edad, años, minutos, cantidades, etc., se clasifica como **numérica** y se le buscan atípicos.

Para ver estas correcciones en un instrumento ya limpiado, usa **«Volver a ajustar limpieza»**.
