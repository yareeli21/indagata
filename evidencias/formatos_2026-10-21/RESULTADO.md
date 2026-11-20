# Matriz de aceptación de formatos — 21 y 22 oct 2026

Todos los datos son SINTÉTICOS. Las herramientas están en `tools/formatos/`: corpus (`generar_corpus.py`,
`corpus_entrevistas.py`, `corpus_docentes.py`) y verificadores (`verificar_formatos.py`,
`verificar_entrevistas.py`). El contrato de formatos está en `markdowns/FORMATOS_ACEPTADOS.md`.
Cambios en la rama `extensiones-semantica`, sin commit.

## Encuestas (enc_10_turno: 60 respondentes, 8 ítems Likert en 2 dimensiones)

13 formatos con las mismas respuestas. Cada uno se procesó por los 7 pasos del asistente y se
comprobaron:
- la estructura: 8 preguntas con el texto del original y 2 dimensiones con α;
- 9 preguntas de referencia al chat: cifras exactas, hechos clave y decisión de dominio.

| Corrida | Resultado | Fallos y corrección |
|---|---|---|
| 1 (`encuestas_corrida1.*`) | Incompleta | La cuadrícula de Forms dio 16 preguntas y fallaron las cifras. El XLSX no se podía aprobar (`dc_format` VARCHAR(50)). Sin prefijos, solo α global. |
| 2 (`encuestas_corrida2.*`) | 141/143 | Q05: el modelo omitió «4 de 30» → `cifras_completas`. |
| E04 y E10 repetidas | 143/143 (100 %) | — |
| Final con el código definitivo (`encuestas.md`, `encuestas_final.log`) | **143/143 (100 %)** | — |

Instrumentos válidos: 84–93 (E01–E10). E11–E13 se rechazan al subir (422 con el motivo).

## Entrevistas: respuestas que divagan (4 participantes × 4 preguntas sobre el momento actual)

La anotación de referencia está hecha a mano (`tools/formatos/corpus/*/referencia.json`). Es la clave de
la prueba: el sistema no la lee. La postura, el núcleo y el contexto se reportan como acuerdo con la
anotación humana.

| Corrida | Pruebas | Postura (exactitud / κ) | Núcleo | Contexto excluido | Fallos y corrección |
|---|---|---|---|---|---|
| 1 (`entrevistas_corrida1.*`) | 36/39 | 0.50–0.56 / 0.30–0.41 | 0.875 | 0.89–1.0 | El LLM marcaba «ambivalente» a quien cambió de opinión → la postura global se calcula con lo que responde y la marca explícita manda. El preámbulo sin hablante contaba como persona → se omite. |
| 2 (`entrevistas_corrida2.*`) | 37/39 | 0.875 / 0.785 | 0.875 | 0.889 | El chat omitía «1 no» en el conteo → conteo obligatorio en posturas y filtros. Una cita inventada «[R017 en p04]» → se quita. El verificador contaba el «1» de «[Fuente 1]» → corregido. |
| 2 repetida con el código final (`entrevistas.md`) | **39/39 (100 %)** | 0.875 / 0.785 (sin etiquetas: 0.75 / 0.5) | 0.875 (sin etiquetas: 1.0) | 0.889 | — |

Instrumentos válidos: 100–104 (I01–I05).

### Segundo tema: docentes sobre evaluación (`entrevistas_docentes.md`)

Se corrió para comprobar que el análisis no depende del tema: mismas reglas, otra población y otro
contenido.

| Variante | Pruebas | Postura (exactitud / κ) | Núcleo | Contexto excluido |
|---|---|---|---|---|
| D01 etiquetas | 8/8 | 0.875 / 0.804 | 0.938 | 0.833 |
| D02 Zoom | 8/8 | 0.875 / 0.804 | 0.938 | 0.833 |

Instrumentos: 105–106. Discrepancias con la referencia (iguales en ambos formatos):
- E01-p2 «No del todo; un examen te dice si memorizaron, pero no si saben aplicar…»: referencia «no», sistema «ambivalente».
- E03-p2 «Depende de la materia; en matemáticas sí, pero en redacción no tanto»: referencia «ambivalente», sistema «sí».

## Lectura para la tesis
- **Lo calculado** (cifras, IDs, conteos, rechazos) es exacto en el 100 % de la matriz.
- **El análisis de posturas** coincide con la anotación humana en 87.5 % (κ ≈ 0.8, acuerdo sustancial) en dos
  temas distintos. Por eso el sistema lo deja como `propuesto` y el investigador lo revisa.
- **Limitación:** la anotación de referencia la hizo el mismo autor del sistema. Conviene que la revise o la
  repita otra persona (la usuaria) antes de reportar el acuerdo como definitivo.

## Anotación independiente de la investigadora (22 oct 2026)

La investigadora anotó las 32 respuestas (`tools/formatos/anotacion/anotacion_para_llenar.xlsx`) sin ver la
referencia del autor ni el análisis del sistema. Comparación: `tools/formatos/anotacion/comparar.py
--estudiantes 100 --docentes 105`. El detalle está en `anotacion_detalle.json`.

| Par | Postura igual | κ de Cohen |
|---|---|---|
| Investigadora vs autor | 30/32 (93.8 %) | 0.902 (casi perfecto) |
| Investigadora vs sistema | 26/32 (81.2 %) | 0.704 (sustancial) |
| Autor vs sistema | 28/32 (87.5 %) | 0.796 (sustancial) |

Frase que responde (la que copió la investigadora contra el núcleo del sistema):
- coincidencia literal completa: 21/32 (criterio muy estricto, porque falla con solo cambiar dónde empieza la frase);
- en promedio, el 84 % de las palabras de su frase están en el núcleo, y el 88 % de las del núcleo están en su frase;
- en 29 de 32 respuestas, al menos la mitad de su frase está en el núcleo.

Diferencias de postura entre la investigadora y el sistema (6):
- **Mezcla del tipo «depende: en unas sí, en otras no»**, que el sistema resumió como «sí»: estudiantes E03-p1 y docentes E03-p2.
- **«No del todo»**: el sistema dijo «ambivalente»; la investigadora y el autor, «no» (docentes E01-p2).
- **Error claro del sistema**: «hoy solo estudio» ante «¿trabajas?», el sistema dijo «sí» (estudiantes E01-p3).
- **La investigadora vio ambivalencia en un cambio de opinión con el tiempo** (estudiantes E01-p4 y E04-p4), donde el autor y el sistema tomaron solo el presente.

### Mejora: «depende» al inicio = ambivalente (22 oct 2026)

Cambio en `analisis_entrevista.empieza_ambivalente` y en la lista `ambivalencia` de `config/marcadores_entrevista.yaml`.
Si la respuesta o un fragmento que responde EMPIEZA con «depende», «más o menos», «a veces», «en parte» o «según»,
la postura es «ambivalente». Se reprocesaron I01 (107) y D01 (108); `depende.log`.

| Par | Antes | Después |
|---|---|---|
| Investigadora vs sistema | 26/32 (81.2 %), κ 0.704 | **28/32 (87.5 %), κ 0.805** |
| Autor vs sistema | 28/32 (87.5 %), κ 0.796 | 30/32 (93.8 %), κ 0.901 |
| Investigadora vs autor | 30/32 (93.8 %), κ 0.902 | (sin cambio) |

Quedan 4 diferencias con la investigadora:
- 1 error claro del sistema: «hoy solo estudio» ante «¿trabajas?» → «sí».
- «No del todo» → «ambivalente».
- 2 cambios de opinión en el tiempo que ella leyó como ambivalencia, y que el autor y el sistema leyeron por el presente que pide la pregunta.
