# Indagata: documento final, pruebas y resultados

> Texto redactado para el reporte técnico. La numeración de capítulos, tablas y figuras es local
> (Capítulo 1 a 3) y debe ajustarse al índice general del documento. Los marcadores
> `[Figura x.y …]` indican el lugar exacto de cada captura y los `[completar: …]`, datos por agregar.
> El **Anexo de trabajo** del final no forma parte del reporte.

---

# Capítulo 1. Diseño del documento final para la recuperación de información

## 1.1 Introducción

Indagata es un sistema para gestionar y consultar instrumentos de investigación educativa: encuestas,
entrevistas y pruebas estandarizadas. Su propósito final es que una persona investigadora pueda hacer
preguntas en lenguaje natural sobre los instrumentos y sus respuestas mediante un esquema de
generación aumentada por recuperación (RAG, *Retrieval-Augmented Generation*).

En una primera versión, cada instrumento producía un único JSON técnico que mezclaba metadatos
Dublin Core, tipos provisionales de pregunta, estadísticas por pregunta, el reporte de limpieza y los
indicadores (KPIs) asociados. Ese archivo cumplía tres funciones a la vez: servía para proponer KPIs,
se dividía en fragmentos para el chat y lo leían los tableros. Esta mezcla tenía dos consecuencias.
Por un lado, las métricas técnicas introducían ruido en la asociación semántica con los KPIs. Por otro,
el archivo no contenía las respuestas individuales, de modo que no podía responder preguntas como
«¿qué contestó el respondente R017 en la pregunta sobre los profesores?».

Para resolverlo se separó la información en artefactos con un propósito único y se diseñó un
**documento final** por instrumento, construido después de la limpieza, la aprobación de metadatos y
la confirmación de KPIs. Este capítulo describe ese documento: cómo se trata la información estadística,
qué medidas se calculan y para qué, cuál es la estructura del documento para cada tipo de instrumento
y en qué medida es suficiente para la recuperación de información.

## 1.2 Flujo de procesamiento

El instrumento recorre siete pasos en el asistente de carga: archivo, limpieza, Dublin Core, metadatos
del tipo, aprobación de metadatos, KPIs sugeridos y guardado. Cada servicio produce un artefacto
específico, versionado y trazable (Tabla 1.1).

**Tabla 1.1.** Artefactos generados por instrumento.

| Artefacto | Servicio | Formato | Almacenamiento |
|---|---|---|---|
| CSV limpio | cleaning-service | CSV separado por `;`, UTF-8 con BOM | storage-service, artefacto `clean` (versionado, SHA-256) |
| Reporte de limpieza | cleaning-service | JSON: métricas antes/después, transformaciones, decisiones y estadística | `tt_rag.limpieza_ejecucion` (una fila por versión) |
| Metadatos Dublin Core y del tipo | metadata-service | 13 campos Dublin Core más los campos propios del tipo | Base de datos y JSON técnico (artefacto `metadata`) |
| Perfil semántico | knowledge-service | JSON `perfil_semantico/1.0` | `tt_rag.version_conocimiento.perfil` |
| Decisiones de KPIs | analysis-service | JSON con KPIs aceptados y rechazados, puntaje, evidencia y justificación | `version_conocimiento.decisiones_kpi` y `kpi_inferido` |
| Documento final | knowledge-service | JSON validado con JSON Schema | storage-service, artefacto `documento` (SHA-256) |

El **perfil semántico** describe el instrumento sin respuestas ni métricas (título, objetivo, temas,
nivel educativo, población, secciones y preguntas) y es la base para sugerir KPIs. La asociación se
calcula comparando, con el modelo de embeddings `paraphrase-multilingual-mpnet-base-v2`, una unidad
general del perfil (*g*) y una unidad por pregunta contra el catálogo de KPIs:

```text
score_k = 0.45 · g  +  0.45 · p_k  +  0.10 · c_k
  g    = similitud coseno entre el perfil general y el KPI
  p_k  = media de las tres preguntas más parecidas al KPI
  c_k  = min(1, |preguntas con similitud ≥ umbral| / 3)   (cobertura)
```

El componente *p* premia que existan preguntas que realmente midan el indicador y *c* favorece a los
KPIs respaldados por varias preguntas. Cada KPI sugerido se presenta con sus preguntas de evidencia y
una justificación redactada por un modelo de lenguaje local (`llama3.2:3b`), que la investigadora puede
editar; si el modelo no está disponible, se usa una plantilla determinística. Los vectores del catálogo
de KPIs solo se leen: no se modifican.

## 1.3 Tratamiento de la información estadística

En el sistema conviven dos niveles de información estadística con propósitos distintos, y cada uno
tiene un destino diferente (Tabla 1.2).

**Tabla 1.2.** Niveles de información estadística y su destino.

| Nivel | Contenido | Dónde se conserva | ¿Forma parte del documento final? |
|---|---|---|---|
| Calidad del dato (limpieza) | α de Cronbach, α si se elimina el ítem, correlación ítem-total, asimetría, curtosis, rango intercuartílico y atípicos, respuesta en línea recta, KR-20, correlación punto biserial, extensión de las respuestas | Reporte de limpieza versionado | No |
| Resumen descriptivo por pregunta o reactivo | Distribución de respuestas, porcentaje por nivel, media y mediana, porcentaje de acierto, distractor más elegido, dificultad, discriminación y una frase interpretativa | Documento final | Sí, solo en encuesta y prueba |

### 1.3.1 Las medidas de calidad no se integran al documento final

Las medidas de la limpieza describen la **calidad del dato**, no el **contenido** del instrumento:
indican si una escala es consistente, si hay personas que respondieron sin leer o si existen valores
atípicos. Su función es apoyar las decisiones de la investigadora durante la fase asistida de limpieza
y se cumple cuando la limpieza se confirma. Integrarlas al documento final tendría un efecto negativo:
un fragmento con «curtosis −0.84, α = 0.71» se parece semánticamente a cualquier otro fragmento con
cifras y aleja la búsqueda vectorial del tema educativo sobre el que se pregunta. Por esa razón
permanecen en el reporte de limpieza, donde siguen disponibles para auditoría.

### 1.3.2 Encuesta y prueba incluyen un resumen descriptivo precalculado

Un sistema RAG recupera solo una parte de los fragmentos, los más parecidos a la pregunta, y un modelo
de lenguaje no cuenta filas de manera confiable. En investigación educativa son frecuentes las preguntas
agregadas, por ejemplo: «¿qué porcentaje de los estudiantes considera justa la evaluación?», «¿cuál
fue el reactivo más difícil y qué distractor eligieron?» o «¿cuál es el promedio de satisfacción con
los profesores?». Si el modelo tuviera que deducir esas cifras a partir de unas cuantas respuestas
individuales recuperadas, el resultado sería impreciso o inventado.

Por ello, el documento final de la encuesta y de la prueba incluye, por cada pregunta o reactivo, un
**resumen calculado de forma determinística** (sin modelo de lenguaje), validado contra un esquema y
acompañado de una frase interpretativa. El modelo puede así **citar** un dato verificado, por ejemplo
«63.2 % de acuerdo o totalmente de acuerdo», en lugar de aproximarlo.

- En la **encuesta**, el resumen (`preguntas[].resumen`) contiene el número de respuestas válidas y sin
  respuesta (con su motivo cuando se trata de «No sé»), la distribución por significado, el porcentaje
  por nivel (desacuerdo, neutral, acuerdo), la media, la mediana, la media recodificada de los ítems
  invertidos y la interpretación.
- En la **prueba**, el resumen (`reactivos[].resumen`) contiene el porcentaje de acierto, la distribución
  por opción, las respuestas nulas y omitidas, el distractor más elegido, la dificultad, la discriminación
  y la interpretación. Cada alumno incluye además su puntaje, el total y el porcentaje. La dificultad y la
  discriminación se conservan porque responden preguntas pedagógicas reales, como qué reactivo no
  distingue a quien domina el tema. En los reactivos no calificables (escalas, Sí/No, numéricos) estos
  campos son nulos.

### 1.3.3 La entrevista no incluye estadística

Las respuestas de una entrevista son texto libre y su valor para la investigación está en lo que la
persona expresa. Un conteo de palabras o de turnos no responde ninguna pregunta de investigación y solo
añadiría ruido a los fragmentos. Por ello, el documento final de la entrevista contiene únicamente cada
pregunta del entrevistador con la respuesta correspondiente, enlazada a la pregunta del guion y, a través
de ella, a los KPIs.

## 1.4 Medidas estadísticas calculadas por tipo de instrumento

Aunque las medidas de calidad no forman parte del documento final, se calculan para cada instrumento
durante la limpieza porque sustentan las decisiones de la investigadora y documentan la calidad del dato.
Las Tablas 1.3 a 1.5 resumen la utilidad de cada una.

En la **encuesta**, las medidas evalúan la completitud, la forma de las distribuciones y la consistencia
interna de las escalas Likert.

**Tabla 1.3.** Medidas de la limpieza de encuestas.

| Medida | Utilidad |
|---|---|
| Número de respuestas y porcentaje de faltantes | Representatividad y detección de sesgo de no respuesta en preguntas sensibles |
| Frecuencias y moda | Respuesta típica en preguntas categóricas y escalas |
| Media, mediana y desviación estándar | Tendencia central y dispersión en escalas y respuestas numéricas |
| Rango intercuartílico y valores atípicos | Errores de captura o casos extremos que distorsionan la media |
| Asimetría y curtosis | Forma de la distribución (efecto techo o piso); indica si conviene reportar la media o la mediana |
| α de Cronbach por bloque | Consistencia interna: si los ítems de un bloque miden un mismo constructo |
| α si se elimina el ítem y correlación ítem-total | Identifica el ítem que debilita la escala |
| Respuesta en línea recta | Personas que eligen la misma opción en todo un bloque, posiblemente sin leer |
| Encuestados incompletos | Registros poco confiables para el análisis |
| Recodificación de ítems invertidos | Sin ella, la media y el α resultan incorrectos |
| «No sé» y «No aplica» | Se tratan como faltantes con motivo y no como un punto de la escala |

En la **prueba estandarizada**, las medidas provienen de la teoría clásica de los tests y describen la
confiabilidad de la prueba y el comportamiento de cada reactivo.

**Tabla 1.4.** Medidas de la limpieza de pruebas estandarizadas.

| Medida | Utilidad |
|---|---|
| KR-20 | Confiabilidad de la prueba con reactivos dicotómicos |
| Dificultad *p* | Proporción de aciertos de cada reactivo; equilibrio de la prueba |
| Discriminación *D* (grupos extremos del 27 %) | Si el reactivo separa a quienes dominan el tema de quienes no |
| Correlación punto biserial | Discriminación calculada con todos los alumnos |
| Distribución de opciones y distractor más elegido | Errores conceptuales frecuentes |
| Distractores sin elegir | Opciones que no funcionan y conviene reescribir |
| Descriptivos del puntaje | Desempeño del grupo |
| Respuestas nulas y omitidas | Problemas de aplicación o de lectura óptica |
| Clave propuesta (27 % superior) | Permite calificar cuando no se dispone de la clave; la investigadora la confirma |
| Tipo de reactivo | Distingue reactivos calificables (opción múltiple, verdadero/falso, puntos) de los de autoinforme |

En la **entrevista**, las medidas se centran en las respuestas de las personas entrevistadas y verifican
que la transcripción esté completa y bien estructurada.

**Tabla 1.5.** Medidas de la limpieza de entrevistas.

| Medida | Utilidad |
|---|---|
| Entrevistados, preguntas y respuestas | Completitud del corpus |
| Respuestas faltantes por pregunta | Preguntas omitidas o que no funcionaron en campo |
| Palabras por respuesta (media, mediana, mínimo y máximo) | Profundidad de las respuestas; respuestas muy breves sugieren respuestas de sí o no, o una transcripción incompleta |
| Respuestas por entrevistado | Entrevistas truncadas o poco desarrolladas |
| Palabras por rol | Verifica la asignación de roles: se espera que predomine el texto de las respuestas |
| Ruido eliminado | Trazabilidad de la limpieza (marcas de tiempo, encabezados, separadores) |

## 1.5 Estructura de los documentos finales

Los tres documentos comparten un conjunto de principios de diseño:

- **Identificadores globales** con el prefijo del instrumento (`INS-0012-p03`), porque el sistema consultará
  varios instrumentos a la vez. Los prefijos son `s` (sección), `p` (pregunta), `r` (reactivo),
  `R` (respondente), `A` (alumno) y `E` (entrevistado).
- **Anonimización**: las personas se identifican con códigos y las columnas con datos personales (nombre,
  correo, matrícula, teléfono, CURP, entre otras) se excluyen por coincidencia de palabra completa.
- **Unicidad**: cada respuesta aparece una sola vez, dentro de la persona que la dio.
- **Navegación bidireccional** entre KPIs y preguntas: la evidencia de cada KPI apunta a sus preguntas y
  cada pregunta enumera los KPIs que la citan.
- **Avisos** explícitos de lo que no pudo interpretarse o se excluyó.
- **Validación formal** con JSON Schema (draft 2020-12): un documento que no cumple su esquema no se guarda.

### 1.5.1 Encuesta

El documento de la encuesta (versión 1.0) organiza el contenido en dos ejes: las preguntas, con su
definición y resumen, y los respondentes, con su contexto y todas sus respuestas interpretadas. Cada
respuesta incluye el texto de su pregunta para que un fragmento por respondente pueda leerse de forma
autónoma.

```text
documento
├── esquema_version
├── instrumento       id, tipo, titulo, objetivo, temas, palabras_clave, nivel_educativo,
│                     poblacion, contexto, n_respondentes
├── kpis_asociados[]  kpi_id, nombre, definicion, que_mide, dimension, similitud,
│                     evidencia[{pregunta_id, similitud}], justificacion, aceptado_por, fecha
├── secciones[]       id, nombre, descripcion
├── preguntas[]       id, seccion_id, texto, tipo, escala | opciones, kpis_relacionados, resumen
├── respondentes[]    id, contexto, respuestas[{pregunta_id, pregunta, estado, valor,
│                     significado, nivel, motivo}]
└── avisos[]
```

### 1.5.2 Prueba estandarizada

El documento de la prueba (versión 1.0) sigue la misma lógica con reactivos y alumnos. Cada reactivo
incluye su texto y opciones (cuando se dispone del instrumento original), el tipo, si es calificable y la
respuesta correcta.

```text
documento
├── esquema_version
├── instrumento       … , n_alumnos
├── kpis_asociados[]
├── secciones[]
├── reactivos[]       id, clave, texto, tipo_reactivo, calificable, opciones, respuesta_correcta,
│                     puntos_max, kpis_relacionados, resumen
├── alumnos[]         id, contexto, puntaje, total, porcentaje,
│                     respuestas[{reactivo_id, respuesta, significado, correcta, estado, motivo}]
└── avisos[]
```

### 1.5.3 Entrevista

El documento de la entrevista (versión 2.0) contiene solo texto: las preguntas del guion y, por cada
persona entrevistada, los intercambios formados por la pregunta del entrevistador y su respuesta. No
incluye conteos ni estadísticas.

```text
documento
├── esquema_version
├── instrumento       id, tipo, titulo, objetivo, temas, palabras_clave, nivel_educativo,
│                     poblacion, contexto
├── kpis_asociados[]
├── preguntas[]       id, texto, kpis_relacionados
├── entrevistas[]     participante, intercambios[{pregunta_id, pregunta, respuesta}]
└── avisos[]
```

```json
{"preguntas": [{"id": "INS-0056-p04",
                "texto": "¿Qué servicios de apoyo institucional has utilizado?",
                "kpis_relacionados": ["KPI-11"]}],
 "entrevistas": [{"participante": "INS-0056-E01", "intercambios": [
   {"pregunta_id": "INS-0056-p04",
    "pregunta": "¿Qué servicios de apoyo institucional has utilizado?",
    "respuesta": "Hubo un semestre en que casi abandono, pero el orientador me ayudó a reorganizarme."}]}]}
```

El esquema formal impone esta forma; por ejemplo, cada intercambio solo admite tres campos y la
respuesta no puede estar vacía:

```json
"intercambios": {"type": "array", "items": {
  "type": "object", "additionalProperties": false,
  "required": ["pregunta", "respuesta"],
  "properties": {
    "pregunta_id": {"$ref": "comun.json#/$defs/id_hijo"},
    "pregunta":    {"type": "string"},
    "respuesta":   {"type": "string", "minLength": 1}}}}
```

## 1.6 Suficiencia para la recuperación aumentada

Para valorar si los documentos son suficientes como insumo del RAG se clasificaron las preguntas que
una persona investigadora podría formular, desde las generales hasta las muy específicas, y se identificó
el campo que permite responder cada una (Tabla 1.6).

**Tabla 1.6.** Tipo de pregunta y campo del documento que la responde.

| Tipo de pregunta | Ejemplo | Campo |
|---|---|---|
| General | «¿De qué trata el instrumento y a quién se aplicó?» | `instrumento` |
| General | «¿Qué KPIs mide y por qué?» | `kpis_asociados[]` |
| KPI → preguntas | «¿Qué preguntas miden la retención?» | `evidencia[].pregunta_id` ↔ `kpis_relacionados` |
| Encuesta, agregada | «¿Qué porcentaje está de acuerdo con X?» | `preguntas[].resumen` |
| Encuesta, individual | «¿Qué respondió R017 sobre X?» | `respondentes[].respuestas[]` |
| Encuesta, segmentada | «¿Y en el turno vespertino?» | `respondentes[].contexto` con consulta estructurada |
| Prueba, agregada | «¿Cuál fue el reactivo más difícil?» | `reactivos[].resumen` |
| Prueba, individual | «¿Qué alumnos fallaron los reactivos del KPI X?» | `alumnos[].respuestas[].correcta` |
| Entrevista, temática | «¿Qué dijo E02 sobre las tutorías?» | `entrevistas[].intercambios[]` |
| Entrevista, por pregunta | «¿Qué respondieron sobre el apoyo familiar?» | Intercambios con el mismo `pregunta_id` |

La suficiencia se comprobó con siete criterios de aceptación respondidos mediante consultas
determinísticas sobre el propio documento (Capítulo 2, sección 2.8). Todos se cumplen. En la entrevista
sintética ent_01 (40 personas), el documento generado contiene 40 entrevistas de 12 intercambios cada
una, todas enlazadas a su pregunta del guion.

Se identificaron las siguientes limitaciones:

1. Los conteos y cruces sobre respuestas individuales («¿cuántos entrevistados mencionaron becas?»,
   «porcentaje de acuerdo por semestre») no se resuelven solo con similitud vectorial; requieren
   consultas estructuradas como herramienta del RAG.
2. El documento de entrevista no incluye el contexto de la persona (edad, género, semestre), por lo que
   no permite segmentar por perfil. Ese contexto se conserva en el reporte de limpieza y podría
   reincorporarse sin datos personales.
3. Una prueba sin instrumento original no tiene el texto de sus reactivos.
4. La anonimización del texto libre es parcial: los nombres mencionados dentro de una respuesta no se
   detectan con certeza, lo que se advierte en los avisos.
5. La división del documento final en fragmentos para el RAG corresponde a la siguiente etapa del proyecto.

## 1.7 Conclusiones del capítulo

El documento final separa el contenido que debe recuperarse de la información sobre la calidad del dato.
La encuesta y la prueba incluyen un resumen descriptivo mínimo porque las preguntas agregadas no pueden
responderse con fiabilidad a partir de fragmentos parciales; la entrevista conserva únicamente preguntas
y respuestas porque su valor está en el texto. La estructura, validada con JSON Schema, anonimizada y con
relaciones navegables entre KPIs y preguntas, permite responder tanto preguntas generales como específicas,
con las limitaciones señaladas para los conteos sobre texto libre.

---

# Capítulo 2. Pruebas

## 2.1 Introducción

Este capítulo describe cómo se verificó el funcionamiento del sistema en las etapas de limpieza,
estandarización, asociación de KPIs y generación del documento final. Se presentan el alcance, el entorno,
los datos utilizados, la estrategia de pruebas por niveles, los casos y criterios de aceptación, y el
procedimiento para reproducir la verificación. Los valores que el sistema produce se presentan en el
Capítulo 3.

La estrategia combina pruebas automatizadas por servicio, pruebas que encadenan los componentes reales,
validación formal de los documentos y pruebas de punta a punta en el navegador. El objetivo de esta
combinación es detectar errores en cada nivel: en una regla aislada, en la integración entre servicios
y en la experiencia de la persona usuaria.

## 2.2 Objetivo y alcance

El objetivo de las pruebas es comprobar que, para los tres tipos de instrumento, la limpieza, los
metadatos, el perfil semántico, la asociación de KPIs y el documento final se generan correctamente,
sin datos personales y con una estructura apta para la recuperación de información.

El alcance incluye los servicios de limpieza (cleaning-service), metadatos (metadata-service),
conocimiento (knowledge-service), análisis (analysis-service, en la asociación de KPIs por perfil) y
almacenamiento (storage-service), la API expuesta a través del gateway y la interfaz del asistente de
carga. Queda fuera la evaluación del RAG con el documento final, que corresponde a la siguiente etapa.

## 2.3 Entorno de pruebas

Las pruebas se ejecutaron sobre la arquitectura de microservicios orquestada con Docker Compose
(Tabla 2.1). La Figura 2.1 muestra los servicios en ejecución.

**Tabla 2.1.** Entorno de pruebas.

| Elemento | Detalle |
|---|---|
| Orquestación | Docker Compose: api-gateway, instrument, cleaning, metadata, knowledge, analysis, storage, visualization y frontend, más PostgreSQL, ChromaDB, Redis y Ollama |
| Hardware | [completar: procesador y memoria], GPU de 4 GiB |
| Modelos | Embeddings `paraphrase-multilingual-mpnet-base-v2` (768 dimensiones); modelo de lenguaje `llama3.2:3b` |
| Backend | Python [completar: versión], FastAPI, SQLAlchemy, pytest |
| Frontend | Node [completar: versión], React 19, TanStack Start, Vite |
| Navegador | Chrome en modo *headless*, controlado mediante Chrome DevTools Protocol |

**[Figura 2.1.** Servicios del sistema en ejecución (`docker compose ps`). Fuente: elaboración propia.**]**

## 2.4 Datos de prueba

Se utilizaron tres conjuntos de datos. El principal está formado por **30 instrumentos sintéticos**:
10 encuestas, 10 entrevistas y 10 pruebas, cada uno con el archivo de respuestas, el instrumento original
y sus metadatos. Los datos se generaron a partir de perfiles de estudiante con parámetros estadísticos
definidos, distribuciones beta reescaladas para los ítems Likert y una estructura de correlación entre
ítems, como se detalla en la metodología de generación de datos sintéticos del proyecto.

El uso de datos sintéticos responde a tres razones: protege la privacidad de estudiantes reales, permite
disponer de suficientes instrumentos de cada tipo y controla la variabilidad para provocar situaciones
concretas (respuesta en línea recta, reactivos difíciles, respuestas breves). Las pruebas sintéticas no
incluyen la clave de respuestas, por lo que también sirvieron para verificar la propuesta automática de clave.

El segundo conjunto es una encuesta real [completar: número de respondentes, origen y forma de anonimización].
El tercero son archivos pequeños construidos para casos límite: una transcripción con marcas de tiempo,
encabezados de página, palabras partidas y letras espaciadas; una encuesta con «No sé», ítems invertidos
y columnas de datos personales; y una prueba con respuestas múltiples e ilegibles.

## 2.5 Estrategia de pruebas

**Pruebas unitarias y de integración por servicio.** Cada servicio cuenta con una suite de pytest que
se ejecuta sobre una base de datos SQLite en memoria con el esquema del sistema adjunto, con
implementaciones en memoria de ChromaDB y de los embeddings, y con el cliente de pruebas de FastAPI
con la autenticación sustituida. Estas pruebas no requieren PostgreSQL, ChromaDB ni Ollama, lo que
permite ejecutarlas de forma rápida y repetible.

**Pruebas con componentes reales encadenados.** Los reportes de limpieza que utiliza el servicio de
conocimiento se generan ejecutando los motores reales de limpieza sobre los archivos de ejemplo. Los
valores esperados se calculan por separado, directamente del CSV limpio, para evitar que el documento
se valide contra sí mismo.

**Validación formal con JSON Schema.** Los documentos de los tres tipos se validan contra su esquema,
con y sin instrumento original. Además, se construye un documento deliberadamente inválido (un
identificador sin prefijo y un resumen faltante) que el sistema debe rechazar indicando la ruta del error
(Figura 2.2).

**[Figura 2.2.** Rechazo de un documento inválido por el JSON Schema, con la ruta del error. Fuente: elaboración propia.**]**

**Pruebas de privacidad.** Se verifica que la exclusión de columnas personales funcione por palabra
completa: encabezados como «Idioma» o «Identidad de género» se conservan, mientras que «ID», «Nombre
completo», «correo_institucional» y «Matrícula» se excluyen. También se buscan los nombres, correos y
matrículas de los archivos de ejemplo dentro del documento final.

**Pruebas de la API.** A través del gateway, con autenticación JWT, se recorre el ciclo de estados de
cada versión del conocimiento: perfil aprobado, KPIs confirmados, borrador, vigente y reemplazado.

**Pruebas de punta a punta.** Un navegador automatizado recorre el asistente completo para cada tipo de
instrumento a 1366 y 390 píxeles de ancho. En cada paso se verifica el avance, la ausencia de errores de
JavaScript y que no exista desplazamiento horizontal en la vista móvil (Figura 2.3).

**[Figura 2.3.** Asistente de carga en vista móvil (390 px), sin desplazamiento horizontal. Fuente: elaboración propia.**]**

**Comparación de métodos de asociación de KPIs.** Un script compara el método anterior, basado en un
resumen único del instrumento, con el método por unidades descrito en la sección 1.2.

## 2.6 Suites automatizadas

La Tabla 2.2 resume las suites por servicio y lo que cubre cada archivo.

**Tabla 2.2.** Suites automatizadas por servicio.

| Servicio | Archivo | Cobertura |
|---|---|---|
| cleaning-service | `test_encuestas.py` | Tipos de columna, «No sé», ítems invertidos, columnas ajenas, línea recta |
| | `test_entrevistas.py` | Ciclo de limpieza de ruido, hablantes y roles, bloques por respondente, preguntas numeradas, DOCX, PDF sin texto |
| | `test_pruebas.py` | Validación de respuestas, nulas, duplicados, clave propuesta, tipos de reactivo |
| | `test_estadistica.py` | α de Cronbach, KR-20, dificultad, discriminación, estadística de entrevistas |
| | `test_resumen.py` | Frases del resumen «En pocas palabras» |
| | `test_esqueleto.py` | Ejecuciones, decisiones obligatorias, confirmación y versionado |
| knowledge-service | `test_perfil.py` | Perfil sin métricas, sin duplicados, emparejamiento con el original |
| | `test_interpretacion.py` | Interpretación por tipo de pregunta |
| | `test_criterios.py` | Esquemas, privacidad, criterios de aceptación, entrevista solo texto |
| | `test_documento_api.py` | Generación, publicación y reemplazo de versiones |
| metadata-service | `test_limpieza.py`, `test_metadatos.py` | Propuesta Dublin Core a partir de la limpieza |
| analysis-service | `test_kpis_perfil.py`, `test_seed_kpis.py` | Fórmula de puntaje, umbral de evidencia, justificación con plantilla, registro de rechazos |
| storage-service | `test_archivos.py`, `test_indice.py` | Artefactos versionados con SHA-256 e ingesta |
| visualization-service | `test_espacio.py`, `test_visualizacion.py` | Espacio vectorial, catálogo y tableros |

## 2.7 Casos de prueba representativos

La Tabla 2.3 presenta casos representativos de cada módulo. Varios de ellos corresponden a situaciones
detectadas durante el desarrollo, como la estructura de entrevistas con varias personas en un mismo archivo.

**Tabla 2.3.** Casos de prueba representativos.

| ID | Módulo | Caso | Entrada | Resultado esperado |
|---|---|---|---|---|
| CP-01 | Limpieza de entrevistas | Ruido que aparece al reconstruir una palabra | «Pá-» / «gina 3» | Dos iteraciones del ciclo; ruido eliminado |
| CP-02 | Limpieza de entrevistas | Varias entrevistas en un archivo | Bloques «RESPONDENTE» con «P1:» y «R:» | Un entrevistador, un entrevistado por bloque y contexto fuera de los turnos |
| CP-03 | Limpieza de entrevistas | Pregunta sin contestar | «R:» vacío | Una respuesta faltante en esa pregunta |
| CP-04 | Limpieza de encuestas | «No sé» en una escala | Valor «No sé» | Faltante con motivo, no punto de la escala |
| CP-05 | Limpieza de encuestas | Ítem invertido | Ítem redactado en negativo | Recodificación y α correcto |
| CP-06 | Limpieza de pruebas | Prueba sin clave | `pru_04_respondido.csv` | Clave propuesta y decisión obligatoria de confirmarla |
| CP-07 | KPIs | Fórmula de asociación | Embeddings controlados | Puntaje igual a 0.45·g + 0.45·p + 0.10·c |
| CP-08 | KPIs | Modelo de lenguaje no disponible | Ollama detenido | Justificación con plantilla |
| CP-09 | Documento final | Entrevista solo texto | Limpieza de entrevista | Intercambios con pregunta y respuesta, sin conteos |
| CP-10 | Documento final | Documento inválido | Identificador sin prefijo, resumen faltante | Rechazo con la ruta del error |
| CP-11 | Privacidad | Encabezados similares | «Idioma», «ID», «Matrícula» | Se conserva «Idioma»; se excluyen «ID» y «Matrícula» |

El caso CP-02 verifica la regla que reconoce el inicio de la entrevista de cada persona. La línea debe
contener una etiqueta de bloque y un identificador con un dígito, o bien la etiqueta en mayúsculas, para
no confundir «Entrevistado: Sí.» con el inicio de un bloque:

```python
_BLOQUE = re.compile(
    r"^\s*(?P<etq>respondente|participante|entrevistad[oa]|informante|caso)"
    r"\s*(?:n[°º.o]*\s*)?[:#\-–]?\s*(?P<id>[\w\-]{1,20})\s*$", re.I)
# «P1», «Pregunta 3» → un solo hablante «P» (el entrevistador), conservando el número
_NUMERADA = re.compile(r"^(?P<base>p|preg|pregunta|r|resp|respuesta)\.?\s*(?P<n>\d{1,3})$", re.I)
```

El caso CP-06 se ilustra en la Figura 2.4.

**[Figura 2.4.** Fase asistida de una prueba sin clave: decisión obligatoria «Confirmar la clave» y
tarjetas por reactivo. Fuente: elaboración propia con Indagata (datos sintéticos).**]**

## 2.8 Criterios de aceptación

Los criterios de aceptación expresan preguntas que el documento final debe permitir responder. Cada uno
se verifica con una consulta determinística sobre el JSON (Tabla 2.4).

**Tabla 2.4.** Criterios de aceptación y consulta que los verifica.

| # | Criterio | Consulta |
|---|---|---|
| 1 | Respuesta de un respondente a una pregunta | `respuesta(doc, "R017", texto=…)` |
| 2 | Respondente en desacuerdo en varias preguntas, o ninguno | `respondente_con_nivel(doc, [...], "desacuerdo")` |
| 3 | Porcentaje de un grupo en un nivel | `pct_nivel(doc, "p4", "acuerdo", {"turno": "Vespertino"})` |
| 4 | Por qué un KPI está relacionado y qué mide | `info_kpi(doc, "KPI-07")` |
| 5 | Preguntas que miden un KPI | `preguntas_de_kpi(doc, "KPI-07")` |
| 6 | Reactivo más difícil y alumnos que fallaron un KPI | `reactivo_mas_dificil(doc)`, `alumnos_que_fallaron_kpi(doc, "KPI-03")` |
| 7 | Lo que dijo un participante sobre un tema | `dijo(doc, "E02", "tutorías")` |

La consulta del criterio 7, por ejemplo, busca el tema en la pregunta y en la respuesta de cada
intercambio de la persona indicada:

```python
def dijo(doc, participante, tema):
    objetivo, buscado = _id(doc, participante), _norm(tema)
    e = next((x for x in doc.get("entrevistas") or [] if x["participante"] == objetivo), None)
    if e is None:
        return []
    return [{"pregunta_id": i.get("pregunta_id"), "pregunta": i["pregunta"], "respuesta": i["respuesta"]}
            for i in e["intercambios"] if buscado in _norm(i["pregunta"]) or buscado in _norm(i["respuesta"])]
```

## 2.9 Procedimiento de ejecución

La verificación puede reproducirse con el siguiente procedimiento:

1. Iniciar el sistema con `docker compose up -d`.
2. Ejecutar la suite de cada servicio desde su carpeta, sin combinar servicios en un mismo proceso:
   `cd services/<servicio>; ..\..\.venv\Scripts\python.exe -m pytest tests -q`.
3. Si cambian los motores de limpieza, regenerar los reportes de ejemplo con
   `python services/knowledge-service/tests/datos/generar_limpiezas.py`.
4. Para la prueba de punta a punta, cargar un instrumento por tipo con su original y recorrer los siete
   pasos del asistente a 1366 y 390 píxeles, registrando capturas de cada paso.
5. Eliminar los instrumentos de prueba con `DELETE /instrumentos/{id}` a través del gateway.

## 2.10 Criterios de aprobación

Se consideró aprobada la verificación si se cumplían todas las condiciones siguientes:

- El 100 % de las pruebas automatizadas de cada servicio se ejecuta sin fallos.
- Los documentos finales de los tres tipos son válidos contra su esquema y el documento inválido se rechaza.
- Ningún dato personal de los archivos de ejemplo aparece en el documento final.
- El asistente se recorre completo sin errores de JavaScript y sin desplazamiento horizontal en 390 píxeles.
- Los siete criterios de aceptación se responden correctamente.

---

# Capítulo 3. Resultados de la limpieza y la estandarización

## 3.1 Introducción

Este capítulo presenta lo que el sistema produce en las etapas de limpieza y estandarización. Para que
los resultados sean comparables, se utilizó un instrumento sintético de cada tipo: la encuesta enc_04, la
prueba pru_04 (sin clave de respuestas) y la entrevista ent_01. La limpieza se ejecutó con los motores
del sistema aceptando las decisiones sugeridas, lo que equivale a confirmar la limpieza sin cambios.
Se presentan los artefactos generados, los resultados de la limpieza por tipo, la estandarización, el
documento final, los defectos corregidos durante las pruebas y el resultado de las suites automatizadas.

## 3.2 Artefactos generados

Cada instrumento procesado produce los artefactos descritos en la Tabla 1.1: el CSV limpio, el reporte de
limpieza, los metadatos, el perfil semántico, las decisiones de KPIs y el documento final. El proceso
inicia en el paso «Archivo» del asistente, donde se elige el tipo de instrumento y se adjuntan el archivo
de respuestas, el instrumento original y, en las pruebas, la clave opcional (Figura 3.1).

**[Figura 3.1.** Paso «Archivo» del asistente con el tipo de instrumento, el instrumento original y la
clave opcional. Fuente: elaboración propia con Indagata (datos sintéticos).**]**

## 3.3 Limpieza de la encuesta

La encuesta enc_04 contiene 200 respondentes y 50 columnas. La limpieza normalizó la codificación y los
encabezados, asignó identificadores seguros a las columnas y eliminó una columna ajena al instrumento.
Durante la fase asistida se presentaron 49 hallazgos de rol de columna, uno de columna ajena y uno de
respuesta en línea recta, sin decisiones obligatorias (Figura 3.2). La Tabla 3.1 compara el estado antes
y después de la limpieza.

**Tabla 3.1.** Encuesta enc_04 antes y después de la limpieza.

| Medida | Antes | Después |
|---|---|---|
| Respondentes | 200 | 200 |
| Columnas | 50 | 49 |
| Preguntas | — | 46 |
| Completitud | 100 % | 100 % |
| Duplicados y valores imposibles | 0 y 0 | 0 y 0 |
| Respondentes en línea recta | 94 | 94 (señalados y conservados) |

**[Figura 3.2.** Fase asistida de la limpieza de la encuesta: acciones automáticas y decisiones para la
investigadora. Fuente: elaboración propia con Indagata (datos sintéticos).**]**

La consistencia interna de las escalas fue alta (Tabla 3.2). Los ocho bloques obtuvieron un α de Cronbach
entre 0.859 y 0.924 y el conjunto de las 38 preguntas Likert alcanzó 0.960. Los nombres de los bloques
corresponden a los prefijos de los encabezados del archivo.

**Tabla 3.2.** α de Cronbach por bloque de la encuesta enc_04.

| Bloque | Ítems | α | Interpretación |
|---|---|---|---|
| Elaboración | 5 | 0.919 | Excelente |
| Organización | 4 | 0.859 | Buena |
| Pensamiento_crí | 5 | 0.919 | Excelente |
| Autorregulación | 6 | 0.921 | Excelente |
| Gestión_del_tie | 7 | 0.924 | Excelente |
| Elaboración_con | 3 | 0.894 | Buena |
| Motivación_intr | 4 | 0.871 | Buena |
| Autoeficacia | 4 | 0.897 | Buena |
| Todas las escalas Likert | 38 | 0.960 | Excelente |

El resumen generado por el sistema indica que todas las preguntas tienen respuesta de todos los
encuestados, que las escalas se inclinan ligeramente hacia los valores altos (promedio de 3.3 en una
escala de 1 a 5) y que la edad tiene una mediana de 22 años (rango intercuartílico de 20 a 26), con
algunos valores altos que elevan el promedio a 23.1 (Figura 3.3). El hallazgo más relevante es que 94
de los 200 respondentes (47 %) respondieron en línea recta en al menos un bloque. En datos reales, esta
proporción justificaría revisar esos registros. En los datos sintéticos refleja perfiles de respuesta
homogénea, y el sistema lo señala para que la investigadora decida conservarlos o retirarlos (Figura 3.4).

**[Figura 3.3.** Pestaña «Estadística» de la encuesta: resumen «En pocas palabras» y α por bloque.
Fuente: elaboración propia con Indagata (datos sintéticos).**]**

**[Figura 3.4.** Pestaña «Antes y después» de la encuesta. Fuente: elaboración propia con Indagata (datos sintéticos).**]**

## 3.4 Limpieza de la prueba sin clave

La prueba pru_04 contiene 90 alumnos y 18 reactivos, sin clave de respuestas. El sistema detectó el tipo
de cada reactivo (6 de opción múltiple, 8 de escala y 4 de Sí/No), propuso la clave de los reactivos
calificables a partir del 27 % de alumnos con mejor desempeño y planteó una decisión obligatoria para
confirmarla, además de una tarjeta por reactivo (Figura 2.4). También conservó las columnas de contexto
(perfil, horas de trabajo por semana, tipo de universidad y beca). La Tabla 3.3 resume los resultados.

**Tabla 3.3.** Resultados de la limpieza de la prueba pru_04.

| Medida | Valor |
|---|---|
| Alumnos y reactivos | 90 y 18 |
| Respuestas | 1,620 válidas, 0 nulas, 0 omitidas |
| Tipos de reactivo | 6 de opción múltiple, 8 de escala, 4 de Sí/No |
| Origen de la clave | Propuesta por el sistema (27 % superior) |
| KR-20 (6 reactivos calificables) | 0.447 (inaceptable) |
| Puntaje | Media de 4.06 sobre 6 (68 %), mediana de 4, desviación de 1.45 |
| Dificultad | 2 fáciles, 4 medios, 0 difíciles |
| Reactivos con discriminación pobre | 0 |

El KR-20 de 0.447 debe interpretarse con cautela: solo 6 de los 18 reactivos son calificables y el
coeficiente tiende a ser bajo con pocos reactivos. Los 12 restantes son escalas y preguntas de Sí/No de
autoinforme, que el sistema identifica como no calificables y no puntúa. Todos los reactivos calificables
discriminan al menos de forma regular (Figura 3.5).

**[Figura 3.5.** Pestaña «Estadística» de la prueba: KR-20, puntajes y análisis por reactivo. Fuente:
elaboración propia con Indagata (datos sintéticos).**]**

## 3.5 Limpieza de la entrevista

La entrevista ent_01 es un archivo de texto con el guion aplicado a 40 personas. Cada bloque inicia con una
línea «RESPONDENTE» seguida de datos de perfil y de las preguntas numeradas con sus respuestas. La limpieza
eliminó un identificador y tres separadores. El sistema reconoció dos hablantes, el entrevistador
(preguntas numeradas) y el entrevistado, y propuso sus roles en la fase asistida (Figura 3.6). Los datos de
perfil de cada persona se registraron como contexto y no como turnos de habla. La Tabla 3.4 resume los resultados.

**Tabla 3.4.** Entrevista ent_01 antes y después de la limpieza.

| Medida | Antes | Después |
|---|---|---|
| Palabras | 27,330 | 25,335 |
| Líneas o turnos | 1,209 líneas | 960 turnos |
| Ruido detectado | 4 | 0 |
| Hablantes | — | 2 |
| Entrevistados, preguntas y respuestas | — | 40, 12 y 480 |

**[Figura 3.6.** Fase asistida de la entrevista: confirmación de los roles de los hablantes. Fuente:
elaboración propia con Indagata (datos sintéticos).**]**

Las 40 personas respondieron las 12 preguntas. Las respuestas tienen en promedio 40.1 palabras (mediana de
37, mínimo de 26 y máximo de 59), y las más breves corresponden a la pregunta 7, sobre el impacto del
trabajo en el desempeño académico (38.4 palabras en promedio). El 76 % de las palabras corresponde a las
personas entrevistadas y el 24 % al entrevistador, una proporción coherente con una entrevista en la que
el entrevistador solo formula las preguntas (Figura 3.7). El CSV limpio conserva un turno por fila con el
identificador de la persona, el hablante, el rol y el texto (Figura 3.8).

**[Figura 3.7.** Pestaña «Estadística» de la entrevista: respuestas por pregunta y palabras por rol.
Fuente: elaboración propia con Indagata (datos sintéticos).**]**

**[Figura 3.8.** Vista previa del CSV limpio de la entrevista. Fuente: elaboración propia con Indagata (datos sintéticos).**]**

## 3.6 Estandarización

A partir de la limpieza confirmada, el servicio de metadatos propone los 13 campos Dublin Core, que la
autora revisa y aprueba (Figura 3.9) [completar: tabla con los campos de un instrumento de ejemplo].

**[Figura 3.9.** Paso «Dublin Core» con los campos propuestos a partir de la limpieza. Fuente:
elaboración propia con Indagata (datos sintéticos).**]**

El perfil semántico de la entrevista ent_01 tomó las 12 preguntas del instrumento original, agrupadas en
una sección, junto con el título, el objetivo, los temas, el nivel educativo (licenciatura) y el contexto.
No contiene métricas ni respuestas (Figura 3.10).

**[Figura 3.10.** Paso «Aprobar metadatos»: perfil semántico legible y su representación JSON. Fuente:
elaboración propia con Indagata (datos sintéticos).**]**

Con el perfil aprobado, el sistema sugiere los KPIs con su puntaje, las preguntas que los sustentan y la
justificación (Figura 3.11) [completar: tabla con los cinco KPIs principales por instrumento, sus
componentes g, p y c, y la comparación con el método anterior].

**[Figura 3.11.** Paso «KPIs sugeridos» con puntaje, evidencia y justificación editable. Fuente:
elaboración propia con Indagata (datos sintéticos).**]**

## 3.7 Documento final generado

Al guardar, el sistema construye, valida y almacena el documento final, y muestra una vista legible con los
avisos y la opción de consultar el JSON completo (Figura 3.12). La Tabla 3.5 resume los documentos generados.

**Tabla 3.5.** Documentos finales generados.

| Instrumento | Contenido | Tamaño | Esquema | Avisos |
|---|---|---|---|---|
| Entrevista ent_01 | 12 preguntas y 40 entrevistas de 12 intercambios (480), todos enlazados a su pregunta | 191 KB | Válido (2.0) | Anonimización del texto libre |
| Prueba pru_04 | [completar: reactivos y alumnos] | [completar] | Válido (1.0) | Clave inferida |
| Encuesta enc_04 | [completar: preguntas y respondentes] | [completar] | Válido (1.0) | [completar] |

**[Figura 3.12.** Paso «Guardar»: vista del documento final y su JSON. Fuente: elaboración propia con
Indagata (datos sintéticos).**]**

## 3.8 Defectos detectados y corregidos

Las pruebas permitieron detectar y corregir defectos antes de dar por concluida la etapa (Tabla 3.6).

**Tabla 3.6.** Defectos detectados y corregidos.

| Defecto | Situación anterior | Situación corregida |
|---|---|---|
| Hablantes en entrevistas con guion numerado | Cada pregunta «P1» a «P12» se trataba como un entrevistador distinto, las 40 personas se fusionaban en un solo hablante y los datos de perfil se interpretaban como hablantes | Un entrevistador, una entrevista por persona y el perfil como contexto |
| Documento final de la entrevista | Incluía conteos y estadísticas sin valor para el texto libre | Solo pregunta y respuesta (esquema 2.0) |
| Clave de respuestas obligatoria | No era posible cargar una prueba sin clave | Clave propuesta por el sistema y confirmada por la investigadora |
| Entidades HTML en la justificación de KPIs | Texto con secuencias como `&quot;` | Texto limpio |
| Anclas globales de las escalas | Las anclas de las instrucciones se ignoraban | Las escalas se interpretan con esas anclas |
| Preguntas repetidas en los metadatos de entrevistas | Cada pregunta aparecía una vez por persona | Preguntas únicas |

El primer defecto es el más ilustrativo. Antes de la corrección, la estadística de participación atribuía
la mayor parte de la interacción a doce supuestos entrevistadores y no reflejaba las respuestas de las
personas entrevistadas. Tras la corrección, el sistema reconoce los bloques por persona y centra la
estadística en las respuestas (Figura 3.13).

**[Figura 3.13.** Estadística de la entrevista antes y después de la corrección del reconocimiento de
hablantes. Fuente: elaboración propia con Indagata (datos sintéticos).**]**

## 3.9 Resultados de las pruebas

Todas las pruebas automatizadas se ejecutaron sin fallos (Tabla 3.7) y los siete criterios de aceptación
se cumplieron.

**Tabla 3.7.** Resultados de las pruebas automatizadas.

| Servicio | Pruebas aprobadas |
|---|---|
| cleaning-service | 101 de 101 |
| knowledge-service | 88 de 88 |
| metadata-service | 21 de 21 |
| analysis-service | 13 de 13 |
| storage-service | 19 de 19 |
| visualization-service | 25 de 25 |

En las pruebas de punta a punta, la prueba pru_04 sin clave se procesó completa hasta la publicación del
documento final. La entrevista ent_01 se procesó hasta el paso de KPIs; la ejecución automatizada se
interrumpió por falta de memoria del equipo y no por un fallo del sistema, y el documento final se generó
a través de la API. No se registraron errores de JavaScript ni desplazamiento horizontal en la vista móvil.

## 3.10 Discusión y limitaciones

Los resultados muestran que la limpieza asistida identifica situaciones relevantes para la investigación
(respuesta en línea recta, reactivos no calificables, estructura de entrevistas con varias personas) y
deja la decisión final a la investigadora. La estandarización produce un perfil semántico sin ruido técnico
y un documento final que conserva el contenido necesario para la recuperación de información.

Deben considerarse las siguientes limitaciones. Los datos son sintéticos, por lo que las cifras demuestran
el funcionamiento del sistema y no permiten conclusiones educativas. La clave propuesta depende de que el
grupo de mejor desempeño responda correctamente y siempre requiere confirmación. La anonimización del texto
libre es parcial. La calidad de los KPIs sugeridos depende del catálogo institucional disponible. Finalmente,
el desempeño del RAG con el documento final aún no se ha evaluado.

## 3.11 Conclusiones del capítulo

La limpieza y la estandarización generan, para cada tipo de instrumento, artefactos limpios, trazables y
validados. En la encuesta se obtuvieron escalas con alta consistencia interna y se señaló un grupo amplio
de respuestas en línea recta. En la prueba sin clave, el sistema propuso la clave y distinguió los reactivos
calificables de los de autoinforme. En la entrevista se reconoció correctamente la estructura de 40
entrevistas y la estadística reflejó las respuestas de las personas entrevistadas. El documento final
resultante es válido, anónimo y está listo para la etapa de recuperación aumentada.

---

# Anexo de trabajo (no incluir en el reporte)

## A. Figuras

| Figura | Qué capturar | Estado |
|---|---|---|
| 2.1 | Terminal con `docker compose ps` | Pendiente |
| 2.2 | Salida de la prueba del documento inválido | Pendiente |
| 2.3 | Asistente en 390 px | Tomada: `e2e_ent01/3_movil.png` |
| 2.4 | Fase asistida de prueba sin clave («Confirmar la clave») | Pendiente |
| 3.1 | Paso «Archivo» | Pendiente |
| 3.2 | Fase asistida de la encuesta | Pendiente |
| 3.3 | Estadística de la encuesta | Pendiente |
| 3.4 | «Antes y después» de la encuesta | Pendiente |
| 3.5 | Estadística de la prueba | Pendiente |
| 3.6 | Fase asistida de la entrevista (roles) | Pendiente |
| 3.7 | Estadística de la entrevista | Tomada: `est_ent01/3_estadistica.png` |
| 3.8 | Vista previa del CSV de la entrevista | Pendiente |
| 3.9 | Paso «Dublin Core» | Pendiente |
| 3.10 | Perfil semántico y su JSON | Tomadas: `e2e_ent01/1_aprobar.png`, `e2e_ent01/2_json.png` |
| 3.11 | KPIs sugeridos | Pendiente |
| 3.12 | «Guardar» con el documento final y su JSON | Pendiente |
| 3.13 | Estadística de la entrevista antes y después | Pendiente (el «antes» puede describirse si no se conserva) |

Las capturas tomadas están en la carpeta temporal
`C:\Users\yarel\AppData\Local\Temp\claude\C--Users-yarel-Documents-indagata-indagata\0b7fa2f9-709a-4ffc-a456-98b02af58255\scratchpad\`.
Es temporal: deben copiarse a la carpeta del reporte.

Formato sugerido: PNG a 1366 px de ancho (390 px en móvil), recortadas al área relevante, sin datos
personales y con el mismo instrumento por tipo en todas las figuras (enc_04, pru_04, ent_01).

## B. Datos por completar

- Hardware (procesador y memoria) y versiones de Python y Node (Tabla 2.1).
- Encuesta real: número de respondentes, origen y anonimización (sección 2.4).
- Campos Dublin Core de un instrumento de ejemplo (sección 3.6).
- Cinco KPIs principales por instrumento y comparación con el método anterior (sección 3.6).
- Contenido y tamaño de los documentos finales de la encuesta y la prueba (Tabla 3.5).
