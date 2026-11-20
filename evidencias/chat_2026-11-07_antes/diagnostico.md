# Fase 0: línea base y diagnóstico del chat (7 nov 2026)

No se cambió código. Versión evaluada: la congelada del 7 nov (commits `b8c7d7a` y `84b861d`), con `gemma3:4b` como
redactor e intérprete (`num_ctx` 4096) y la caché apagada.

## 1. De dónde sale la línea base

- **Tus respuestas reales.** Las baterías son las mismas preguntas que hiciste a mano. Por eso la línea base usa tus
  consultas 2271–2371 y tus 97 calificaciones (`rag_calificacion`), no una corrida nueva.
  - El script `tools/rag/evaluar_chat.py --desde-log 2271-2371` empareja cada turno con su consulta por texto e
    instrumento: encuesta 127, prueba 130 y entrevista 129.
  - Si una pregunta se repitió, toma la que calificaste. La 2281 se repitió como la 2282 porque el modelo se cayó.
- **Lo que faltaba.** Tres preguntas de cortesía (GEN-02 a GEN-04) no estaban en tu prueba; se corrieron con el
  script, en la misma versión.
- **El set de control.** Encuesta 61 y entrevista 60. No hay otra prueba estandarizada vectorizada además de la 130
  (ver §8).
- **Archivos.** Cada caso está en `casos/<ID>.json` y el resumen con todas las métricas en `resumen.md`.
- **Lo que no se encontró.** `evidencias/preguntas_prueba.docx` no existe en el repositorio ni en la carpeta del
  usuario. Las calificaciones salieron de la base de datos.

## 2. Resultado de la línea base

| Medida | Valor |
|---|---|
| Casos que cumplen el «Debe» | **31 de 79** (16 parciales, 32 no cumplen) |
| Planes válidos (intención distinta de aclaración) | 83 de 97 (85.6 %) |
| Caídas a plantilla | 28 de 102 turnos (27.5 %) |
| K-Precision (respuestas redactadas) | mediana 0.85 (n = 74) |
| Cifras con respaldo en el contexto | 963 de 982 |
| Tiempo por turno | mediana 40 s, p90 188 s |
| **Set de control** (encuesta 61, entrevista 60) | **1 de 16** cumple, 4 parciales, 11 no cumplen (`../chat_2026-11-07_control_antes/`) |

**Cómo se calificó cada caso contra el «Debe»** (`calificacion_debe.json`):
- se partió de tu calificación de cada turno: todos «bien» = cumple; algún «mal» = no cumple; lo demás, parcial;
- se cambió en cuatro casos, cada uno con su nota, cuando el «Debe» pide algo que tu calificación no cubría
  (ENC-23, ENC-25, PRU-19 y GEN-01).

**El set de control falla por las mismas causas** que las baterías (C1, C2, C3, C6, C7, C8, C10 y C11 en §7).
Eso confirma que los problemas son generales del sistema, no de estos tres instrumentos.

**K-Precision contra tu calificación: no se relacionan** (Spearman ρ = −0.04, n = 72; mediana 0.86 en «mal», 0.81 en
«parcial» y 0.86 en «bien»).
- **Por qué.** Casi todas tus respuestas «mal» no inventan nada: copian un cálculo, pero de otra operación (por
  ejemplo, ENT-12 con K-Precision 1.0). K-Precision mide **fidelidad** (si lo dicho está en los datos), no si la
  respuesta es la que se pidió.
- **Qué significa para la tesis.**
  - K-Precision sostiene que el chat casi no agrega contenido ajeno a los datos (mediana 0.85).
  - La **calidad** se mide con tu calificación y con el «Debe».
  - Los valores bajos sí señalan respuestas a revisar, por ejemplo ENT-15 (2) con 0.15: una interpretación con poco
    respaldo.

## 3. D3. Cómo se construyen hoy los chunks

**Dónde se arman.**
- `services/storage-service/services/chunks_documento.py → construir()`, a partir del **documento final vigente**.
- Los indexa `chroma_indexer.py`: colección `instrumentos`, embeddings `paraphrase-multilingual-mpnet-base-v2`.
- La colección `kpis` no se toca.

**Tamaño.**
- `VENTANA` = 450 caracteres. Cada pieza repite su prefijo; el solape es de 60 caracteres en texto corrido y ninguno en
  listas.
- El texto de la pregunta dentro de un respondente se recorta a 40 caracteres, y en el prefijo de una pregunta a 160.

**Qué lleva cada chunk:**

| Tipo | Chunks (sección) | Contenido |
|---|---|---|
| Todos | `encabezado` (ficha, chunk 0) | Título, tipo, objetivo, población, nivel, temas, n, KPIs asociados |
| Encuesta | `pregunta` | Texto (160 c.), válidas/sin respuesta, distribución con n y %, por nivel, media, interpretación, KPIs |
| Encuesta | `respondente` | Contexto + una línea por pregunta: ID, texto (40 c.) y significado de la respuesta |
| Prueba | `reactivo` | Texto (160 c.), opciones, opción más elegida, distribución en %, opciones sin elegir, KPIs |
| Prueba | `alumno` | Respondidas, nulas y sin respuesta + una línea por reactivo: letra (significado) [estado] |
| Entrevista | `pregunta` | Texto de la pregunta guía (300 c.) y KPIs |
| Entrevista | `intercambio` | Participante, pregunta (160 c.) y respuesta completa; si hay análisis (esquema 2.1), primero la postura y el núcleo |
| Todos | `kpi` | Definición, qué mide, justificación y preguntas que lo sustentan |

**Metadatos para filtrar:**
- `instrumentoId`, `tipo`, `seccion` (hace de tipo de chunk), `preguntaId`, `seccionInstrumento`, `respondenteId` y
  `kpiId`;
- además: `titulo`, `investigador`, `autorId`, `anio`, `nivel`, `fuente` y `kpis`.

**Cómo se recuperan** (`services/visualization-service/services/rag_service.py`):
- **RAG primero** (`_recuperar_primero`): busca en el alcance antes de interpretar y pasa los fragmentos como pistas.
- **Apoyo** (`_apoyo_rag`): fragmentos del mismo instrumento, filtrados a los respondentes o preguntas del resultado.
- **Umbral** `RAG_MIN_SCORE` = 0.35; a lo más 1 ficha y 3 fragmentos por instrumento; `top_k` ≤ 8.
- **En el prompt**, cada instrumento es una fuente `[Fuente n]` con sus fragmentos dentro de `<datos fuente="n">`
  (`prompt.py`).

**Chunks que pasan del límite del modelo.** `max_seq_length` = **128 tokens**, medido con el tokenizador del modelo
dentro del contenedor; lo que pasa de ahí no se embebe.

| Instrumento | Chunks truncados | Dónde |
|---|---|---|
| 127 (encuesta) | 1,094 de 6,667 | 1,085 de 6,608 `respondente` (máx. 140 tokens) y 9 de 28 `pregunta` (máx. 158) |
| 130 (prueba) | **385 de 465** | 385 de 420 `alumno` (máx. 179 tokens) |
| 129 (entrevista) | 0 de 47 | máx. 115 tokens |
| 61 (encuesta) | 149 de 690 | 138 `respondente`, 11 `pregunta` |
| 60 (entrevista) | 0 de 521 | máx. 109 tokens |

**Por qué se truncan:**
- 450 caracteres de español con números y letras sueltas dan más de 128 tokens;
- en los alumnos, cada línea «r07: B (texto de la opción)» gasta muchos tokens.

**La consecuencia** es que el final de esos chunks no cuenta para la búsqueda.

## 4. D5. Dónde aparece hoy la calificación de pruebas

Se quitó el 25 oct (Desarrollo X.5.4). La revisión de hoy, con grep sobre código, configuración, esquemas, frontend y
README, encontró:

| Lugar | ¿Califica? |
|---|---|
| Documento final de prueba (`knowledge-service/services/documento/prueba.py`, esquema `documento_prueba_estandarizada.json`) | No: «no hay respuesta correcta, aciertos ni puntaje» |
| Chunks (`chunks_documento.py → _prueba`) | No: opciones, distribución y opción más elegida |
| Limpieza (`cleaning-service/services/motores/estadistica.py`, `pruebas/motor.py`) | No: «no hay KR-20 ni análisis de dificultad o discriminación». La columna de puntaje global, si existe, se guarda como dato de contexto del alumno |
| README de knowledge-service | Ya no menciona «respuesta correcta», «% de acierto», «dificultad» ni «discriminación» |
| Chat | Regla «sin calificar» en `enrutador.py` (línea 135) y verificación `calificada` en la redacción |
| `markdowns/PRUEBAS_RAG_INTEGRACION.md` | Solo como historia (pruebas anteriores al 25 oct), con una nota al inicio |

**Conclusión:** no queda nada que borrar en el documento final ni en la limpieza. Faltan dos cosas del chat:
- la regla no reconoce «aprobaron», «promedio» ni «calificación» (PRU-23);
- la regla solo actúa en el enrutador anterior, no en la ruta con plan.

## 5. D4. Qué NLP hay hoy para entrevistas

- **Análisis por intercambio con el LLM** (`knowledge-service/services/analisis.py`, esquema 2.1):
  - una llamada por intercambio;
  - guarda postura, marco temporal, núcleo, motivo y antecedentes;
  - el investigador puede corregirlo («revisado»).
  - **No se corrió en las entrevistas 129 ni 60**: 0 de 15 y 0 de 498 chunks traen «Postura:».
- **No hay** temas o códigos, sentimiento con cita, actores, barreras o propuestas, ni citas clave verificadas.
- **El chat** busca menciones con raíces de palabras (`ejecutor.py → _menciones`) y recupera intercambios por
  similitud.
- **Problemas de estructura en la 129:**
  - la guía quedó con 13 preguntas, porque las indicaciones del entrevistador («Gracias por aceptar la entrevista. Todo
    lo que digas es confidencial…») se pegaron a p01;
  - la estadística de hablantes (palabras por hablante) sí está en la limpieza, pero el chat no la consulta.

## 6. Otros problemas encontrados

- **Privacidad: el nombre de la autora del instrumento aparece como si fuera la participante.**
  - En 5 respuestas de la entrevista el modelo escribió «Isabella Cortes (E01)».
  - Causa: `prompt.py:128` pone el nombre de la investigadora registrada en el encabezado de cada fuente, y el modelo
    lo atribuye a la persona entrevistada.
- **Textos de pregunta corruptos (D6):**
  - «Cargas máxima ¿Tu programa…» en p01 y «Totalmente de acuerdo ¿Sabes si…» en p08 de la encuesta 127.
  - **El lector ya está corregido** (`original.py → _sin_arrastre`, 5 nov, con prueba en `test_perfil.py`): hoy lee
    bien las 18 preguntas de ese PDF.
  - El documento final de la 127 es del **28 oct** y nunca se regeneró. Corregirlo es regenerar el perfil, el
    documento y el índice, no cambiar código.
- **Encuesta 61:** «¿Has reprobado alguna materia…?» quedó partida como opción múltiple («Sí» 55 %, «varias veces»
  28.1 %…). Las opciones «Sí, varias veces» y «Sí, una vez» se tomaron como listas. Es un error de la limpieza
  (`encuestas/tipos.py`).
- **Memoria:** 3 respuestas de la prueba salieron como «modelo no disponible» (PRU-11, PRU-12 y PRU-22). `gemma3:4b`
  corre 43 % en la CPU.

## 7. Causas raíz y cambio generalizado propuesto

Agrupadas: cada fila resuelve varios casos. Ningún cambio usa textos de estos instrumentos; todo sale del catálogo de
cada uno.

| # | Causa raíz | Casos | Dónde (archivo → función) | Cambio generalizado |
|---|---|---|---|---|
| C1 | Comparar grupos solo acepta variables de contexto; no puede agrupar por las respuestas a una pregunta, por posición ni por sección | ENC-08, ENC-11, ENC-12, ENC-10, PRU-10, PRU-08, PRU-11, PRU-12, CEN-07 | `ejecutor.py → _comparar_grupos`; `plan_consulta.py` (esquema) | Grupos definidos por: una pregunta y sus opciones, un rango de posición («primeros N / últimos N») o una sección. Cada grupo con su n y su distribución o media |
| C2 | No hay cruce entre dos preguntas («de los que marcaron X, ¿qué eligieron en Y?») | ENC-09, PRU-09, CEN-02 | `ejecutor.py` (falta la operación); `plan_consulta.py` | Operación `cruce`: distribución de Y dentro de cada grupo de X, en %, con n |
| C3 | El hilo no conserva el conjunto anterior: «de ellos» hereda filtros equivocados o ninguno; «muéstrame 5» y «tal cual» no reutilizan el último resultado | ENC-13, ENC-14, ENC-17, PRU-14, PRU-15, ENT-13, CEN-03 | `seguimiento.py → combinar, _continuar`; `rag_service` (estado) | Estado de conversación guardado en `rag_log`: instrumento, último plan, último conjunto de IDs y última pregunta referida. «De ellos» filtra sobre ese conjunto; «muéstrame N» lista N de ese conjunto con el total; «tal cual» devuelve la tabla del turno anterior |
| C4 | «¿Por qué? / ¿qué significa?» repite el cálculo en lugar de interpretarlo | ENC-13 (3), ENC-16 (2), PRU-17 (2), ENT-17 (2) | `seguimiento.py → combinar` (profundiza) | Profundizar = mismo resultado + instrucción de interpretar (capa 2 marcada como interpretación), sin volver a listar |
| C5 | La validación acepta planes absurdos: excluir todas las preguntas, «>» sobre opciones de texto, «menos consenso» como «coincidencia» | PRU-03, PRU-07, PRU-13, PRU-09 | `plan_consulta.py → validar_contra_catalogo`; `anclaje.py` (criterios de ranking) | Reglas de validación: no excluir lo que la pregunta no excluye; operadores numéricos solo en preguntas numéricas; dirección del ranking con negaciones («menos consenso» = más repartida) |
| C6 | El ranking «repartida» usa el % de la opción más elegida y mezcla preguntas de opción múltiple | ENC-14, PRU-07, PRU-13, CEN-04 | `ejecutor.py → _medida_ranking` | Entropía normalizada (0 = todos igual, 1 = repartido por igual) solo en preguntas de una opción; se dice la medida usada |
| C7 | El anclaje descarta condiciones válidas cuando la palabra de la pregunta no está en la opción («hecho» frente a «Sí, en una empresa…»), y una aclaración por algo inexistente se reemplaza por texto recuperado que inventa | ENC-13 (1), ENC-22, PRU-21, PRU-22, CEN-06 | `anclaje.py`; `rag_service.py` («aclaración → respuesta con lo recuperado») | (a) La negación y el «sí» genérico agrupan opciones por su forma («Sí, …» / «No, …»). (b) Valor, opción o reactivo inexistente → respuesta determinista «no existe» + opciones válidas con conteo (o el número de reactivos), nunca el texto recuperado |
| C8 | Faltan operaciones de entrevista: cobertura de la guía, intervenciones fuera de la guía, respuesta más larga, palabras por hablante (de la limpieza) y búsqueda de varios términos | ENT-02, ENT-03, ENT-05, ENT-06, ENT-07, CET-02, CET-05 | `ejecutor.py → _menciones` (frase literal); falta la operación | Operaciones de entrevista calculadas: cobertura y seguimiento contra la guía, longitud por respuesta, hablantes desde el reporte de limpieza, menciones con «o» y raíces, con citas |
| C9 | No hay conteo de participantes: «los demás participantes» o «la segunda participante» con una sola persona | ENT-12, ENT-22, CET-06 | `ejecutor.py`; validación del plan | Validar contra el número de participantes y responder «hay N participante(s)» |
| C10 | Reglas de dominio incompletas: saludos, consejos o malestar, correos, diagnósticos y «aprobaron / promedio» | GEN-01–04, ENC-24, ENC-25, ENT-24, ENT-25, PRU-23, CET-07, CET-08 | `dominio.py` / `config/dominio.yaml`; `enrutador.py` (sin calificar) | Intenciones fijas antes del planner: cortesía (bienvenida con 3 ejemplos sacados del catálogo), consejo, malestar (amable + servicios de apoyo), datos personales (correo, teléfono, dirección), diagnóstico y prueba sin calificar en todas las rutas |
| C11 | Sin polaridad por pregunta: lo «preocupante» elige respuestas favorables | ENC-16, CEN-05 | `hallazgos.py`; documento final | Polaridad por pregunta inferida de la escala y el texto, guardada con su origen y revisable por el investigador; los hallazgos «preocupantes» usan solo el extremo desfavorable |
| C12 | Documento final viejo y metadatos que no llegan al chat: textos corruptos (127), indicaciones pegadas a p01 (129), tipo de entrevista y duración ausentes de la ficha, «opcional» no se guarda | ENC-14, ENC-19, ENC-21, ENT-19, ENT-20, ENT-21 | Regenerar el documento de la 127; `chunks_documento.py → _ficha`; `estructura.py` (entrevista) | Regenerar; la ficha incluye la metodología y la duración si están, o «no registrado»; las indicaciones del entrevistador se separan de p01; «opcional» se lee del original (el «*» de Google Forms) o se dice que no se registra |
| C13 | El nombre de la autora del instrumento entra al prompt y se atribuye a la participante | ENT-17, ENT-24, ENT-05 y otros | `prompt.py:128` | El encabezado de la fuente no lleva nombres de personas |
| C14 | Chunks: el 83 % de los de alumno y el 16 % de los de respondente pasan de 128 tokens; las preguntas van recortadas a 40 caracteres | Recuperación en general | `chunks_documento.py → _encuesta, _prueba` | Encabezado compacto y piezas medidas en tokens (no en caracteres) para que la pregunta quede dentro de lo embebido (D3) |
| C15 | Listas cortas y redacción que confunde el límite con el total («De 159, 30 cumplen») | ENC-24, D6 | `ejecutor.py → _filtrar_respondentes` | Total + primeros 20 + «ver más»; la frase del total sale de la plantilla |
| C16 | «Fidelidad 100 % por construcción» en aclaraciones y respuestas sin cifras | D6 | `services/indicadores.py` / panel | Solo cuando hay cifras verificadas |
| C17 | La verificación deja pasar afirmaciones sin respaldo que no son cifras («p07 era opcional», «81 eligieron B») | ENC-21, PRU-09 | `rag_service.py → _verificar_redaccion` | Capa 1 de hechos generada con plantilla; el modelo solo agrega la interpretación marcada, y se rechaza si trae números o IDs fuera de los hechos |

## 8. Lo que necesito que decidas antes de la Fase 1

1. **Modelo.** Tus principios dicen `llama3.2:3b` con `num_ctx` 2048, pero hoy el chat usa `gemma3:4b` con 4096.
   gemma lo elegiste tú en la comparación de modelos (Y.5.2), y con él la mediana fue de 40 s, el p90 de 188 s y hubo
   caídas por memoria.
   - **Mi recomendación:** quedarnos con gemma mientras se hacen los cambios, para no mezclar dos variables, y medir
     llama solo al final, con la misma batería, si quieres bajar los tiempos.
   - `num_ctx` 2048 no alcanza para el prompt actual (reglas + catálogo + datos); lo mediría antes de cambiarlo.
2. **Control de prueba estandarizada.** No hay otra prueba cargada. Para la comprobación de generalización necesito
   subir una sintética (por ejemplo `pru_01` de `tools/data_synthesis`) con la cuenta admin. ¿Me das permiso?
3. **Regenerar la encuesta 127** (perfil, documento e índice) para corregir los textos pegados. Hay que volver a
   confirmar sus KPIs aceptados; los conservo tal cual. ¿De acuerdo?
4. **D5.** No hay nada que borrar en el documento final ni en la limpieza (§4). Solo se completa la regla del chat.
5. **D4.** Para el NLP de entrevistas propongo:
   - el LLM local, offline y una vez por intercambio (ya existe el esquema 2.1 y se amplía con temas, valoración con su
     cita, actores, barreras y propuestas), con cada cita verificada contra el texto;
   - **pysentimiento** como segunda opinión del sentimiento (corre en CPU).
   - No usaría spaCy: el lematizado que hace falta ya lo cubren las raíces del código.
   - Lo detallo con ejemplos al inicio de la Fase 1.
