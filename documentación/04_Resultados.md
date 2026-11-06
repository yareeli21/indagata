# Capítulo Z. Resultados

<!--
NOTA DE TRABAJO (no incluir en el reporte)
- Fuentes en comentarios <!- - fuente: … - ->.
- Cifras de limpieza: motores reales de cleaning-service ejecutados el 18 oct 2026 sobre los
  archivos de storage/instrumentos_sinteticos, aceptando las decisiones sugeridas. Script y salida:
  evidencias/cifras_limpieza_2026-10-18/ (correr desde services/cleaning-service).
- Salida de comparar_kpis (16 oct): evidencias/comparar_kpis_2026-10-16.txt.
- KPIs: tt_rag.version_conocimiento (decisiones_kpi y perfil.kpis_asociados), 18 oct.
- RAG: tools/rag/reportes/reporte_20261017_2030.md (final), _1902, _2010 y verificacion_20261017_2032.md.
- Formatos y entrevistas: evidencias/formatos_2026-10-21/RESULTADO.md (matrices, anotación de la investigadora).
- Tablas «Tabla R.n», figuras «Figura R.n».
-->

## Z.1 Introducción y resultados por objetivo

Este capítulo presenta lo que produce la versión final del sistema (commit `29598b0`, más los cambios
de la rama `extensiones-semantica` del 20 al 22 oct) en cinco áreas:
- la limpieza y estandarización;
- la asociación de KPIs;
- el RAG con sus métricas;
- la robustez ante los formatos de instrumentos reales, con el análisis de respuestas de entrevista;
- la comparación con el estado inicial. Todos los instrumentos tienen **respuestas sintéticas**; enc_01
conserva las preguntas de un cuestionario publicado. Por eso los resultados muestran que el sistema
funciona, pero no permiten conclusiones sobre estudiantes.

**Tabla R.1.** Resultados por objetivo.

| Objetivo | Resultado | Evidencia | Sección |
|---|---|---|---|
| [PENDIENTE: texto del objetivo sobre carga y limpieza] | Los tres tipos de instrumento se limpian con decisiones del investigador; 7 instrumentos procesados con estadística antes y después | Tablas R.2–R.6 | Z.2 |
| [PENDIENTE: objetivo sobre metadatos y estandarización] | Dublin Core y metadatos del tipo propuestos desde la limpieza; perfil y documento final validados con JSON Schema | Pruebas de `test_criterios.py` y `test_perfil.py` | Z.2.5 |
| [PENDIENTE: objetivo sobre asociación de KPIs] | KPIs propuestos con puntaje, preguntas de evidencia y justificación editable | Tablas R.7–R.9 | Z.3 |
| [PENDIENTE: objetivo sobre consulta en lenguaje natural (RAG)] | Decisión de dominio correcta en 20 de 20 preguntas de referencia; 14 de 15 respuestas correctas en la verificación de punta a punta | Tablas R.10–R.12 | Z.4 |
| [PENDIENTE: objetivo sobre visualización / espacio vectorial] | Mapa PCA de 55 KPIs y 26 instrumentos que conserva el 43.6 % de la varianza; vecinos por coseno en el espacio original | X.8.4 | — |
| [PENDIENTE: objetivo sobre carga de instrumentos reales] | 10 formatos de encuesta aceptados con las mismas respuestas del chat y 3 rechazados con motivo (143/143); 7 formatos de entrevista (55/55); postura de las entrevistas con 87.5 % de acuerdo con la anotación independiente de la investigadora (κ = 0.80) | Tablas R.13–R.16 | Z.5 |
| [PENDIENTE: objetivo sobre privacidad y control de acceso] | Detección de datos personales por palabra completa; 0 datos personales del archivo de ejemplo en el documento final; chat que rechaza la reidentificación sin usar el modelo | `test_criterios.py`; Tabla R.17 | Z.4.4 |

[PENDIENTE: sustituir la columna «Objetivo» por el texto exacto del objetivo general y de los
objetivos específicos de la tesis, que no se encontraron en el repositorio.]

---

## Z.2 Calidad de la limpieza y de la estandarización ★

La limpieza se ejecutó con los motores del sistema aceptando las decisiones sugeridas, lo que
equivale a confirmar sin cambios. Se usaron siete instrumentos: cuatro encuestas, dos pruebas y una
entrevista.
<!-- fuente: evidencias/cifras_limpieza_2026-10-18/cifras.json -->

### Z.2.1 Encuestas

**Tabla R.2.** Encuestas antes y después de la limpieza.

| Medida | enc_01 (IEAE, real) | enc_04 (MSLQ-SF) | enc_09 (carga) | enc_10_turno |
|---|---|---|---|---|
| Respondentes antes / después | 180 / 180 | 200 / 200 | 160 / 160 | 60 / 60 |
| Columnas antes / después | 33 / 32 | 50 / 49 | 32 / 31 | 12 / 11 |
| Columnas con rol «pregunta» sugerido | 29 | 46 | 28 | 8 |
| Preguntas del instrumento (perfil y documento final) | 21 | 38 Likert + otras [PENDIENTE] | 20 | 8 |
| Completitud antes / después | 100 % / 100 % | 100 % / 100 % | 100 % / 99.84 % | 100 % / 100 % |
| Duplicados | 0 | 0 | 0 | 0 |
| Valores imposibles antes / después | 0 / 0 | 0 / 0 | **8 / 0** (anulados) | 0 / 0 |
| Respondentes en línea recta | 18 (10 %) | 94 (47 %) | 51 (31.9 %) | 11 (18.3 %) |
| Columnas ajenas eliminadas | 1 | 1 | 1 | 1 |
<!-- fuente: evidencias/cifras_limpieza_2026-10-18/cifras.json (metricas_antes, metricas_despues, cifras) -->

**Lectura.**
- **Las cuatro encuestas venían completas y sin duplicados**, porque el generador no inyecta esos
  casos (método A, X.6.2). Las reglas de vacíos y duplicados se verificaron con los archivos de prueba (B4, X.6.3), no con
  este acervo.
- **enc_09 tenía 8 valores fuera de la escala.** La limpieza los anuló (por eso la completitud baja
  a 99.84 %) y la columna `semestre` quedó con 5 % de vacíos. Es el único caso del acervo en que la
  limpieza cambió datos.
- **La limpieza sugiere el rol «pregunta» para 8 columnas demográficas** en enc_01, enc_04 y enc_09
  (que traen 12 columnas de contexto), por eso cuenta 29, 46 y 28 «preguntas». El investigador puede
  cambiar el rol en la fase asistida, y el perfil, que se empareja con el instrumento original,
  reconoce solo las preguntas reales (21 en enc_01 y 20 en enc_09). En enc_10_turno, con 4 columnas de
  contexto, no ocurre. [PENDIENTE: listar las 8 columnas y decidir si se ajusta la regla de roles.]
- **La línea recta varía de 10 % a 47 %.** En enc_04 casi la mitad de los respondentes contestó
  igual todo un bloque. En datos reales justificaría revisar esos registros; en datos sintéticos
  refleja perfiles de respuesta homogénea. El sistema los señala y los conserva hasta que el
  investigador decida.

**Tabla R.3.** α de Cronbach por bloque.

| Instrumento | Bloques (α) | Global |
|---|---|---|
| enc_01 | Organización y planificación 0.935 · Habilidades* 0.847 · Motivación 0.874 · Recursos de aprendizaje 0.809 · Estrategias de control 0.852 | 0.937 (21 ítems) |
| enc_04 | Elaboración 0.919 · Organización 0.859 · Pensamiento crítico 0.919 · Autorregulación 0.921 · Gestión del tiempo 0.924 · Elaboración con… 0.894 · Motivación intrínseca 0.871 · Autoeficacia 0.897 | 0.960 (38 ítems) |
| enc_09 | Carga horaria 0.907 · Organización 0.908 | 0.876 (9 ítems) |
| enc_10_turno | Evaluación 0.874 · Ambiente 0.832 | 0.783 (8 ítems) |
<!-- fuente: evidencias/cifras_limpieza_2026-10-18/cifras.json (fiabilidad) -->

\* **Hallazgo en enc_01: dos dimensiones fusionadas.** El instrumento tiene seis dimensiones, pero
la limpieza encontró cinco bloques. El generador recorta los encabezados a 15 caracteres y
«Habilidades para el examen» y «Habilidades para jerarquizar» quedaron ambos como
`Habilidades_par_item1…3`; la limpieza, que agrupa por prefijo, los unió en un bloque de 6 ítems.
Es un defecto de los datos de entrada, no de la regla de agrupación, pero muestra un límite: si dos
dimensiones comparten prefijo, el sistema no puede distinguirlas sin el instrumento original.
<!-- fuente: encabezados de storage/instrumentos_sinteticos/encuestas/enc_01_respondido.csv; secciones de enc_01_original.txt (6 dimensiones) -->

**Resumen «En pocas palabras» de enc_04** (generado por reglas, sin modelo de lenguaje):
- «Los 8 bloques de escalas son consistentes (α de 0.859 o más).»
- «En general, las respuestas a las escalas se inclinan ligeramente hacia los valores altos de la
  escala (promedio 3.3 en una escala de 1 a 5; el punto neutral es 3).»
- «"edad": la mitad de las respuestas está entre 20 y 26 (mediana 22); unos pocos valores altos
  (hasta 35) suben el promedio a 23.1.»

**[Figura propuesta R.1: pestañas «Estadística» y «Antes y después» de enc_04 (Figuras 36 y 37 del
avance, si coinciden).]**

### Z.2.2 Pruebas estandarizadas

**Tabla R.4.** Pruebas estandarizadas: lo que respondieron los alumnos (no se califican, Desarrollo X.5.4).

| Medida | pru_04 | pru_01 |
|---|---|---|
| Alumnos × reactivos | 90 × 18 | 100 × 25 |
| Respuestas válidas / nulas / no respondidas | 1,620 / 0 / 0 | 2,500 / 0 / 0 |
| Tipos de reactivo detectados | 6 opción múltiple · 8 escala · 4 Sí/No | 15 opción múltiple · 5 V/F · 5 de puntos |
| Tarjetas de decisión | 0 | 0 |
| Reactivo donde más alumnos coinciden | r16 (Sí/No): 73.3 % respondió «No» | r21 (respuesta corta): 83 % con 0 puntos |
| Reactivo con las respuestas más repartidas | r06 (escala de conductas): la opción más elegida, 4, reúne 26.7 % | r15 (opción múltiple): la más elegida, A, reúne 35 % |
| Reactivos casi unánimes / con opciones que nadie eligió | 0 / 0 | 0 / 1 (r02: nadie eligió C) |
| Columnas de contexto conservadas | 11: perfil, edad, género, semestre, promedio, horas de trabajo, tipo de universidad, nivel socioeconómico, nivel de estudio, primera generación y beca | las mismas 11 |
<!-- fuente: evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json (motor de limpieza de cleaning-service sobre pru_01 y pru_04 regenerados el 25 oct sin clave, semilla 42) -->

**Lectura.** Las dos pruebas se limpian sin ninguna decisión pendiente: sin clave no hay nada que confirmar,
y los datos sintéticos no traen respuestas nulas ni alumnos repetidos. La limpieza reconoce el tipo de cada
reactivo por sus valores y describe qué eligieron los alumnos. Las respuestas sintéticas son aleatorias
(Desarrollo X.6.2), así que las distribuciones no reflejan dominio de un tema; solo comprueban que la
descripción coincide con los datos. Las 11 columnas de contexto se reconocen todas desde el 25 oct; antes,
8 de ellas se proponían como preguntas.

### Z.2.3 Entrevista

**Tabla R.5.** ent_01 antes y después de la limpieza.

| Medida | Antes | Después |
|---|---|---|
| Palabras | 27,330 | 25,335 |
| Caracteres | 169,313 | 155,135 |
| Líneas / turnos | 1,209 líneas | 960 turnos |
| Ruido detectado | 4 | 0 |
| Hablantes | — | 2 (entrevistador y entrevistado) |
| Entrevistados × preguntas | — | 40 × 12 = 480 respuestas |
| Palabras por respuesta (media / mediana / mín–máx) | — | 40.1 / 37 / 26–59 |
| Palabras del entrevistado / entrevistador | — | 76 % / 24 % |
<!-- fuente: evidencias/cifras_limpieza_2026-10-18/cifras.json (ent_01_respondido) -->

**Antes de la corrección del 16 oct**, la misma entrevista se segmentaba en 12 entrevistadores
(P1…P12), un solo entrevistado «R» que agrupaba a las 40 personas y varios «hablantes» que eran en
realidad líneas de perfil (Edad, Universidad). Las cifras de participación no tenían sentido. Después
de la corrección, la proporción 76 % / 24 % es la esperada en una entrevista en la que el
entrevistador solo formula las preguntas. Todas las personas respondieron las 12 preguntas; las
respuestas más breves corresponden a la pregunta 7 (38.4 palabras en promedio).
<!-- fuente: registro 16 oct (diagnóstico y corrección de entrevistas) -->

### Z.2.4 Sugerencias de análisis

Después de guardar, el sistema convierte esas medidas en sugerencias. Para enc_09 produjo, entre
otras:

> Sugerencia (atención): 51 de 160 encuestados (31.9 %) respondieron en línea recta: repite los
> análisis principales sin ellos para ver si cambian.
>
> Sugerencia (bien): Puedes promediar los 4 ítems del bloque «Carga horaria» y analizarlo como una
> escala (α = 0.91).
<!-- fuente: registro 18 oct (respuesta del chat a «¿Qué análisis me sugieres para la encuesta de carga académica?» y GET /limpieza/61/resumen) -->

### Z.2.5 Estandarización: perfil y documento final

En los cinco instrumentos publicados, el documento final se validó contra su esquema y se
publicó (Tabla R.6).

**Tabla R.6.** Instrumentos publicados y sus artefactos.
<!-- fuente: tt_rag.respuesta_interpretada y tt_rag.documento_vectorizado por id_crudo (18 oct); version_conocimiento -->

| `id_crudo` | Instrumento | Respuestas en `respuesta_interpretada` | Chunks en el RAG |
|---|---|---|---|
| 53 | ent_01 (republicada el 18 oct) | 480 | 534 |
| 55 | pru_01 (borrado el 25 oct) | 2,500 | 464 |
| 59 | enc_10_turno | 480 | 146 |
| 60 | ent_01 | 480 | 522 |
| 61 | enc_09 | 3,200 (160 respondentes × 20 preguntas) | 691 |

En las pruebas automatizadas, el documento inválido (un identificador sin prefijo, un resumen
faltante) se rechaza con la ruta del error, y ningún nombre, correo ni matrícula del archivo de
ejemplo aparece en el documento final.
<!-- fuente: services/knowledge-service/tests/test_criterios.py -->

---

## Z.3 Asociación de KPIs ★

### Z.3.1 Ejemplos con evidencia y justificación

**Tabla R.7.** KPIs propuestos para enc_10_turno (instrumento 59), con catálogo de PA.

| KPI | Puntaje | g | p | c | Preguntas de evidencia (similitud) |
|---|---|---|---|---|---|
| Tamaño Promedio de Clase | 0.605 | 0.548 | 0.574 | 1.00 | p04 «Las evaluaciones están relacionadas con lo que se ve en clase» (0.633), p02 «Las calificaciones reflejan lo que realmente aprendí» (0.576), p03, p07, p01 |
| Puntajes en Pruebas Estandarizadas de Referencia | 0.558 | 0.489 | 0.529 | 1.00 | p02 (0.551), p04 (0.520), p01, p03 |
| Nivel de Adopción de Analítica de Aprendizaje | 0.546 | 0.493 | 0.498 | 1.00 | p04, p02, p01 |
| … | … | … | … | … | … |
| Oportunidades de Desarrollo Profesional para Docentes | 0.488 | 0.479 | 0.458 | 0.67 | p07, p04 |
<!-- fuente: version_conocimiento (id_crudo 59), decisiones_kpi -->

Justificación redactada por el modelo para el primer KPI (sin editar):

> «El indicador Tamaño Promedio de Clase relaciona con el instrumento porque mide el promedio de
> alumnos por aula, lo que evalúa la capacidad de la institución para ofrecer personalización
> docente y un entorno propicio para la participación activa. Las preguntas del instrumento se
> centran en aspectos como las evaluaciones, calificaciones, retroalimentación y disponibilidad de
> los profesores…»

**Tabla R.8.** Resumen por instrumento.
<!-- fuente: version_conocimiento.decisiones_kpi y perfil.kpis_asociados (18 oct) -->

| `id_crudo` | Instrumento | Propuestos | Rango de puntaje | Aceptados | Quién decidió |
|---|---|---|---|---|---|
| 53 | ent_01 | 8 | 0.531 – 0.572 | 4 (los 4 primeros) | Script de procesamiento |
| 55 | pru_01 (borrado el 25 oct) | 8 | 0.497 – 0.590 | 5 (posiciones 2, 3, 6, 7 y 8; no el 1.º) | Investigadora en la interfaz [PENDIENTE: confirmar] |
| 59 | enc_10_turno | 8 | 0.488 – 0.605 | 2 (los 2 primeros) | Script de procesamiento |
| 60 | ent_01 | 8 | 0.526 – 0.570 | 2 (los 2 primeros) | Script de procesamiento |
| 61 | enc_09 | 8 | 0.407 – 0.557 | 4 (posiciones 1, 4, 5 y 8) | Investigadora en la interfaz [PENDIENTE: confirmar] |

**Lectura.**
1. **Cada KPI llega con preguntas concretas como evidencia.** En el método anterior no había
   evidencia por pregunta (Z.3.2).
2. **La separación entre propuestas es pequeña**: en ent_01 los 8 KPIs quedan entre 0.531 y 0.572
   (0.041 de diferencia). El catálogo es institucional (retención, graduación, acreditación) y varios
   KPIs se parecen a casi cualquier instrumento educativo. Por eso la decisión final es humana.
3. **Es reproducible**: ent_01 procesada dos veces (53 y 60) dio los mismos 8 KPIs con las mismas
   evidencias y similitudes; los puntajes difieren en ≤ 0.005 porque el perfil general varía con los
   metadatos aprobados.
4. **Calidad de las justificaciones.** El modelo de 3B produce errores de redacción («El indicador…
   relaciona con el instrumento») y a veces relaciones débiles (por ejemplo, «Ingresos por Educación
   Continua» para una entrevista sobre permanencia, que nadie aceptó). Esto confirma la decisión de
   que el investigador revise y pueda editar cada justificación.
5. **Las aceptaciones de 53, 59 y 60 no son una validación humana**: el script aceptó los N de mayor
   puntaje para preparar los datos del RAG.

### Z.3.2 Comparación con el método inicial

La comparación se hizo el 16 oct con `comparar_kpis.py`, **con el catálogo de KPIs anterior** y
sobre dos instrumentos (39 y 22) que ya no están en la base. El 17 oct se adoptó el catálogo de la
rama `PA` (55 KPIs reescritos) para ajustarlo a lo que se necesitaba; las cifras no se repitieron con
ese catálogo. El detalle está en la Tabla P.6.
<!-- fuente: registro 16 oct 01:05–01:10; registro 17 oct (adopción del catálogo) -->

**Tabla R.9.** Método inicial contra método por unidades (catálogo anterior).

| Aspecto | Método inicial (*summary*) | Método por unidades |
|---|---|---|
| Texto que se vectoriza | Metadatos + instrumento completo en un solo vector | Perfil general + una unidad por pregunta |
| Lo que realmente lee el modelo | 128 de 811 (RAU) y de 1,297 *tokens* (MSLQ-SF) | Unidades cortas que caben completas |
| Evidencia por pregunta | No | Sí (hasta 5 preguntas por KPI) |
| Coincidencia del top 5 entre métodos | — | RAU 4 de 5; MSLQ-SF 0 de 5 |
| Separación 1.º–5.º | RAU 0.062; MSLQ-SF 0.037 | RAU 0.042; MSLQ-SF 0.022 |
| Problema observado | Propuestas basadas casi solo en metadatos | En el MSLQ-SF, encabezados en código y columnas demográficas como evidencia (perfil desde el JSON técnico antiguo) |

**Conclusión.** El método por unidades no aumentó la separación entre KPIs (sigue limitada por el
catálogo), pero sí resolvió dos problemas verificables: usa las preguntas, que el método inicial no
veía, y permite justificar cada KPI con evidencia concreta. Su punto débil apareció cuando el perfil
contenía encabezados en código, lo que llevó a construir el perfil desde el instrumento original.

**[Figura propuesta R.2: paso «KPIs sugeridos» con puntaje, componentes, evidencia y justificación
editable.]**

---

## Z.4 RAG y métricas RAGAS ★

### Z.4.1 Qué mide cada métrica y cómo se calculó

**Tabla R.10.** Métricas.
<!-- fuente: services/visualization-service/services/evaluacion.py; documentación de RAGAS 0.4.3 consultada el 18 oct -->

| Métrica | Pregunta que responde | Cálculo | Necesita respuesta de referencia |
|---|---|---|---|
| Fidelidad (*faithfulness*) | ¿Lo que afirma la respuesta está en el contexto? | El juez extrae las afirmaciones y decide cuáles se deducen del contexto: sustentadas ÷ total | No |
| Relevancia de la respuesta (*answer relevancy*) | ¿La respuesta contesta la pregunta? | El juez genera 3 preguntas desde la respuesta; media del coseno con la pregunta original; 0 si la respuesta es evasiva | No |
| Precisión del contexto (*context precision*, variante sin referencia `ContextUtilization`) | ¿Los fragmentos útiles estaban primero? | El juez marca cada fragmento como útil o no; precisión@k ponderada | No |
| Recall del contexto (*context recall*) | ¿El contexto cubre la respuesta esperada? | Proporción de afirmaciones de la respuesta esperada que se encuentran en el contexto | Sí (solo fuera de línea) |

**Dos implementaciones.**
- **En el chat**: métricas propias que siguen las fórmulas de RAGAS 0.4.3, calculadas en segundo
  plano después de responder (unos 20 segundos), con el mismo modelo de *embeddings* del sistema.
- **Fuera de línea**: RAGAS 0.4.3 real en un entorno aislado, porque sus dependencias exigen NumPy 2 y
  LangChain 0.3, incompatibles con los servicios. Usa embeddings `nomic-embed-text` en Ollama.

**Modelo juez y sus limitaciones.** En las corridas de esta sección (17 oct), el juez de ambas
implementaciones fue `llama3.2:3b`, el mismo modelo que genera. Un juez pequeño parte mal las afirmaciones
y no siempre reconoce una paráfrasis: RAGAS dio fidelidad 0.5 a una respuesta exactamente correcta («R005
respondió "Ni de acuerdo ni en desacuerdo"», Q02). Por eso las cifras de fidelidad y recall se presentan como
**aproximadas**, y la interfaz lo advierte.

Desde el 23 oct, el juez del chat es `qwen2.5:3b`. En las copias literales del resultado calculado dio 0.95
de fidelidad media contra 0.40 de llama3.2, y en las redacciones correctas o con errores rindió parecido
(Desarrollo, Tabla D.29a). Además, las respuestas que son el resultado calculado tal cual ya no las califica
el juez: se registran como «fiel por construcción».

[PENDIENTE: la Tabla R.11 no se ha recalculado con el juez nuevo, y falta medir el acuerdo entre el juez y una
anotación humana (κ de Cohen). Ambos están en el plan de evaluación modelo por modelo.]
<!-- fuente: evidencias/jueces_2026-10-23/comparar_jueces.json; services/visualization-service/services/evaluacion.py (por_construccion) -->

### Z.4.2 Resultados sobre las 20 preguntas de referencia

El conjunto cubre todos los tipos de pregunta: por respondente, porcentajes por grupo, KPIs,
reactivos, entrevistas, preguntas generales, comparación, fuera del dominio, sin datos, privacidad,
glosario y ayuda. Cada pregunta tiene una respuesta esperada verificada en los datos.
<!-- fuente: tools/rag/preguntas_referencia.json -->

**Tabla R.11.** Resultado final (corrida del 17 oct, 20:30).
<!-- fuente: tools/rag/reportes/reporte_20261017_2030.md -->

| Métrica | Propia (servicio) | RAGAS 0.4.3 |
|---|---|---|
| Decisión de dominio correcta | **100 % (20 de 20)** | — |
| Fidelidad | 0.51 | 0.74 |
| Relevancia de la respuesta | 0.77 | 0.56 |
| Precisión del contexto | **1.00** | **0.90** |
| Recall del contexto | 0.51 | 0.89 |

**Evolución en tres corridas** (17 oct): la decisión de dominio pasó de 95 % a 100 % al reconocer más
formas de negativa; la fidelidad propia pasó de 0.48 a 0.51 tras cambiar el formato del juez
(veredicto por número en lugar de copiar cada afirmación).
<!-- fuente: reporte_20261017_1902.md, _2010.md, _2030.md -->

**Cómo leerlo.**
- **Resultados sólidos:** la decisión de dominio (20 de 20) y la precisión del contexto (1.00 propia y
  0.90 en RAGAS): la recuperación entrega primero lo que sirve.
- **No comparable por construcción:** la relevancia, porque cada implementación usa un modelo de
  *embeddings* distinto (mpnet contra nomic).
- **Aproximados:** fidelidad y recall, limitados por el juez de 3B.

### Z.4.3 Casos ilustrativos por tipo de pregunta

**Tabla R.12.** Respuestas reales del sistema (verificación del 17 oct).
<!-- fuente: tools/rag/reportes/verificacion_20261017_2032.md -->

| Tipo | Pregunta | Respuesta | Tiempo | Fid. / Rel. / Prec. |
|---|---|---|---|---|
| Por respondente | Dame un respondente en desacuerdo en p1, p2 y p3 | «El respondente R002 está en desacuerdo en p01, p02 y p03. [Fuente 1]» | 1.3 s | 0.67 / 0.81 / 1.00 |
| Porcentaje por grupo | ¿Qué porcentaje del turno vespertino está de acuerdo con p4? | «…el 13.3 % (4 de 30) de quienes respondieron del grupo turno = Vespertino está de acuerdo. [Fuente 1]» | 2.9 s | 0.50 / 0.48 / 1.00 |
| No existe | ¿Hay algún respondente neutral en las preguntas 1 a 8? | «No existe ningún respondente que esté en posición neutral en p01…p08 a la vez.» | 0.2 s | omitida |
| Entrevista | ¿Qué dijo E02 sobre el orientador? | El orientador le ayudó a reorganizarse cuando consideró abandonar; los compañeros fueron un apoyo | 2.9 s | 0.67 / 0.85 / 1.00 |
| General | ¿Qué evalúa la encuesta de evaluación y ambiente escolar? | «…evalúa la experiencia del estudiante en términos de evaluación del aprendizaje y ambiente escolar. [Fuente 1]» | 4.3 s | 1.00 / 0.96 / 1.00 |
| Comparativa | Compara qué miden las dos encuestas | Atribuyó a ambas los KPIs de una sola (**incorrecta**) | 7.7 s | 0.40 / 0.81 / 1.00 |
| Fuera del dominio | ¿Quién ganó el mundial de futbol? | Mensaje fijo con ejemplos de lo que sí puede responder | 0.1 s | omitida |
| Sin datos | ¿Qué opinan los estudiantes sobre el transporte público? | «No tengo información relacionada con lo que solicitas en los instrumentos consultados.» | 2.1 s | omitida |
| Reidentificación | ¿Cuál es el nombre del respondente R017? | «Los respondentes… son anónimos y no puedo ayudar a identificarlos…» | 0.1 s | omitida |
| Glosario | ¿Qué significa un alfa de Cronbach bajo? | Definición con `[Glosario: Alfa de Cronbach (α)]` | 2.9 s | 0.50 / 0.82 / 1.00 |
| Ayuda | ¿Cómo subo un instrumento? | Los 7 pasos del asistente | 3.1 s | 0.25* / 0.80 / 1.00 |

\* Error del juez: partió la respuesta en fragmentos como «Entra a» y «Selecciona» y los marcó como
no sustentados. Resultado global: **14 de 15 respuestas correctas**; la comparativa es la excepción. La
verificación incluía una pregunta por el reactivo con menos aciertos; la tabla la omite porque desde el 25 oct
las pruebas no se califican (Desarrollo X.5.4).

**Preguntas sobre los instrumentos (23–24 oct).** Las filas «General» y «Comparativa» se respondían por
búsqueda semántica. Desde el 23 oct, las preguntas de este tipo («¿de qué trata…?», «¿qué relación hay entre
los instrumentos?», «¿qué patrones hay?») se responden con el resultado calculado sobre el documento, sin el
modelo:
- **«Dime la relación entre uno y otro instrumento»** (entrevista 53 y encuesta 61): tipos distintos, el
  objetivo de cada uno, el nivel Licenciatura en común, el KPI «Porcentaje de Estudiantes a Tiempo Parcial»
  en común y las palabras clave «trabajo» y «tiempo».
- **«¿Qué patrón de información consideras más interesante…?»:**
  - en la entrevista, «familia» aparece en las respuestas de 36 de 40 participantes;
  - en la encuesta, el 60.6 % dice que su institución no ofrece talleres de gestión del tiempo, el 55 % ha
    reprobado alguna materia por falta de tiempo, y la pregunta con más nivel bajo es la eficacia para
    gestionar el tiempo (56.2 %).

Cada una tarda menos de 1 s. La redacción del modelo, en cambio, inventó relaciones y cambió una opción
(Desarrollo X.10.3).
<!-- fuente: evidencias/pruebas_2026-10-24/rag_log_704_744.txt (consultas 738, 743 y 744); probar_chat2.py y probar_patrones.py (salidas del 23 oct) -->

**Consultas con filtros (18 oct).** «…uno de los estudiantes que sí han reprobado por falta de
tiempo…» → 88 de 160 (55 %) y un respondente de ejemplo con sus 20 respuestas; «¿Cuántos trabajan
más de 30 horas?» → 37 de 160 (23.1 %). Ambas cifras coinciden con consultas SQL independientes. Una
pregunta repetida se respondió desde la caché en 0.1 s, contra 27.2 s de la primera vez.
<!-- fuente: registro 18 oct 05:40 y 06:13–06:16 -->

**[Figura propuesta R.3: respuesta del chat con fuentes citadas y el panel de métricas debajo.]**

### Z.4.4 Privacidad en el chat

Las cuatro preguntas de privacidad y manipulación de la auditoría reciben un mensaje fijo **sin
llamar al modelo**, en 0.1 s. Antes, con el control de la rama `PA`, tres de ellas llegaban al modelo
y una respondía con un mensaje engañoso («No tengo información…» ante una petición de nombre y
correo).
<!-- fuente: registro 17 oct (auditoría); verificacion_20261017_2032.md caso 12 -->

---

## Z.5 Robustez ante formatos reales y análisis de entrevistas ★

Esta sección presenta qué tan bien procesa el sistema los formatos en que llegarían los instrumentos
reales (X.5) y qué tan bien separa, en una entrevista, lo que responde la pregunta de lo que es relato o
digresión (X.7.8). El procedimiento de prueba está en Y.3.3, Y.3.4 y Y.4.8. Todos los datos son sintéticos, escritos con la
forma de los exportes reales.
<!-- fuente: evidencias/formatos_2026-10-21/RESULTADO.md -->

### Z.5.1 Encuestas: 13 formatos de un mismo instrumento

**Tabla R.13.** Resultado final de la matriz de encuestas (enc_10_turno, 60 respondentes).
<!-- fuente: evidencias/formatos_2026-10-21/encuestas.json y encuestas.md (corrida final, 22 oct) -->

| Variante | id | Pruebas | Dimensiones con α | Aviso o rechazo |
|---|---|---|---|---|
| E01 Con secciones y prefijos | 84 | 14/14 | Evaluación 0.87; Ambiente 0.83 | — |
| E02 Google Forms (texto de la pregunta) | 85 | 14/14 | Sugeridas: 0.87; 0.83 | — |
| E03 Sin secciones, texto de la pregunta | 86 | 14/14 | Sugeridas: 0.87; 0.83 | — |
| E04 Sin secciones, prefijos | 87 | 14/14 | Por prefijo: 0.87; 0.83 | `emparejadas_por_posicion` |
| E05 Sin secciones, códigos P1…P8 | 88 | 14/14 | Sugeridas: 0.87; 0.83 | `emparejadas_por_posicion` |
| E06 Cuadrícula de Google Forms | 89 | 14/14 | Sugeridas: 0.87; 0.83 | — |
| E07 Qualtrics | 90 | 14/14 | Sugeridas: 0.87; 0.83 | — |
| E08 LimeSurvey | 91 | 14/14 | Por grupo `G01Q`/`G02Q`: 0.87; 0.83 | `emparejadas_por_posicion` |
| E09 XLSX sin secciones | 92 | 14/14 | Sugeridas: 0.87; 0.83 | — |
| E10 CSV con «;» y BOM | 93 | 14/14 | Por prefijo: 0.87; 0.83 | — |
| E11 Códigos sin original | — | 1/1 | — | 422: pide subir el instrumento original |
| E12 Formato largo | — | 1/1 | — | 422: pide una fila por respondente |
| E13 Sin fila de encabezados | — | 1/1 | — | 422: pide agregar los encabezados |
| **Total** | | **143/143 (100 %)** | | |

**Lectura.**
- **Respuestas idénticas.** Los diez formatos aceptados producen las mismas respuestas del chat que el
  instrumento original: R017 «De acuerdo» en p03, 13.3 % (4 de 30) del turno vespertino de acuerdo con
  p04, 16.7 % (10 de 60) en desacuerdo con p08 y el mismo respondente R002 en desacuerdo en p01–p03.
  Las tres formas que el sistema no puede procesar bien se rechazan al subir, con el motivo y lo que hay
  que hacer.
- **Mismas dimensiones con el mismo α.** Las 2 dimensiones salen en todos los formatos aceptados, por tres
  vías: el prefijo del encabezado, el grupo de LimeSurvey o la sugerencia por correlación. Esta última se
  usa cuando la limpieza no ve secciones. Pasa en E02 y E07, que sí tienen secciones en el original: la
  limpieza no lee el original, y el perfil sí usa esas secciones.
- **Avisos de emparejamiento por orden.** Las variantes con encabezados en código (E04, E05, E08) llevan el
  aviso `emparejadas_por_posicion`, para que el investigador verifique que cada columna corresponde a su
  pregunta.

### Z.5.2 Dimensiones sugeridas

**Tabla R.14.** Dimensiones que propone la limpieza en encuestas de estructura conocida.
<!-- fuente: registro 21 oct (sugerir() con criterio de Kaiser sobre los CSV del acervo) -->

| Encuesta | Ítems | Dimensiones reales | Propuesta del sistema | α de los grupos propuestos |
|---|---|---|---|---|
| enc_10_turno | 8 | 2 | 2 grupos, iguales a las reales | 0.87; 0.83 |
| enc_04 (MSLQ) | 38 | 8 | 8 grupos, iguales a las subescalas | 0.90–0.93 |
| enc_01 (IEAE) | 21 | 6 publicadas, 5 distinguibles por los encabezados | 5 grupos; las dos dimensiones con nombre recortado igual salen separadas; «Recursos de aprendizaje» (2 ítems) se une a «Organización» | 0.85–0.93 |

La propuesta reproduce la estructura conocida en los tres casos. La única desviación es esperable: un
grupo necesita al menos 3 ítems, y «Recursos de aprendizaje» tiene 2. El investigador acepta o ignora
la propuesta; nunca se aplica sola.

### Z.5.3 Entrevistas: formatos y análisis de respuestas

**Tabla R.15.** Resultado final de la matriz de entrevistas.
<!-- fuente: evidencias/formatos_2026-10-21/entrevistas.md, entrevistas_docentes.md -->

| Variante | id | Pruebas | Postura (exactitud / κ) | Núcleo correcto | Contexto fuera del núcleo |
|---|---|---|---|---|---|
| I01 Etiquetas «Entrevistador:/Entrevistado:» | 100 | 8/8 | 0.875 / 0.785 | 0.875 | 0.889 |
| I02 «P1:» / «R:» | 101 | 8/8 | 0.875 / 0.785 | 0.875 | 0.889 |
| I03 Zoom (hora al final, muletillas) | 102 | 8/8 | 0.875 / 0.785 | 0.875 | 0.889 |
| I04 Teams (WebVTT) | 103 | 8/8 | 0.875 / 0.785 | 0.875 | 0.889 |
| I05 Sin etiquetas (una persona) | 104 | 7/7 | 0.75 / 0.50 | 1.0 | 1.0 |
| D01 Docentes, etiquetas | 105 | 8/8 | 0.875 / 0.804 | 0.938 | 0.833 |
| D02 Docentes, Zoom | 106 | 8/8 | 0.875 / 0.804 | 0.938 | 0.833 |
| **Total** | | **55/55 (100 %)** | | | |

Las métricas de las columnas 4 a 6 comparan contra la anotación de referencia del autor.

**Lectura.**
- **Estructura y chat.** Los siete formatos producen la misma estructura: participantes, intercambios y
  cada respuesta unida a su pregunta del guion. El conteo de posturas del chat coincide con el documento
  en todos.
- **Literalidad.** Cada unidad del análisis está textual en su respuesta. Las que el modelo inventó (una
  por entrevista, en promedio) se descartaron antes de guardarse.
- **Mismo análisis en los cuatro formatos con hablantes.** El análisis no depende de la forma de la
  transcripción.
- **El segundo tema da un acuerdo igual o mayor.** Los marcadores del respaldo son de tiempo y de postura,
  no de contenido.

Ejemplo de análisis de la respuesta que motivó esta parte (I01, participante E01, p01):

| Unidad | Función | Postura |
|---|---|---|
| «Cuando iba en la primaria no lo pensaba así, yo las practicaba porque me gustaba jugar y me divertía» | contexto (pasado) | — |
| «pero ahora creo que sí, me llenan de energía por querer seguir manteniendo la beca deportiva» | responde (actual) | sí |
| **Postura global:** sí. **Motivo:** mantener la beca deportiva. | | |

En el chat, «¿Cuántos entrevistados creen que las actividades extracurriculares actualmente tienen
impacto en sus calificaciones?» se responde con el conteo calculado: de 4 entrevistados, 3 sí y 1 no,
con la frase de cada persona.
<!-- fuente: entrevistas.json (I01, respuesta del chat); tests/test_analisis_entrevista.py -->

### Z.5.4 Acuerdo con la anotación independiente de la investigadora

Para que la medición no dependiera de quien construyó el sistema, la investigadora anotó las 32
respuestas (dos temas) sin ver la anotación del autor ni el análisis del sistema (Y.4.9).

**Tabla R.16.** Acuerdo de la postura (sí, no, ambivalente) entre los tres anotadores.
<!-- fuente: tools/formatos/anotacion/comparar.py --estudiantes 107 --docentes 108; evidencias/formatos_2026-10-21/RESULTADO.md -->

| Comparación | Coinciden | κ de Cohen | Lectura del κ |
|---|---|---|---|
| Investigadora vs autor (dos humanos) | 30/32 (93.8 %) | 0.90 | Casi perfecto |
| **Investigadora vs sistema** | **28/32 (87.5 %)** | **0.80** | **Sustancial** |
| Autor vs sistema | 30/32 (93.8 %) | 0.90 | Casi perfecto |

**Frase que responde.** La investigadora copió, en cada respuesta, la parte que contesta la pregunta.
- En promedio, el 84 % de las palabras de su frase está en el núcleo del sistema, y el 88 % de las
  palabras del núcleo está en su frase.
- En 29 de 32 respuestas, al menos la mitad de su frase está en el núcleo.
- La coincidencia literal completa (21 de 32) es un criterio demasiado estricto: basta con que la frase
  empiece o termine en otro punto para que no cuente. La diferencia típica es que el sistema recorta más
  corto.

**Las cuatro diferencias de postura que quedan** con la investigadora:
1. **Error del sistema.** «¿Actualmente trabajas mientras estudias?» → «Antes trabajaba en una tienda…,
   pero lo dejé; hoy solo estudio.» El sistema dijo «sí». La respuesta no contiene «no»: se entiende por
   el sentido, y ninguna regla general de marcadores lo resuelve.
2. **Caso de frontera.** «No del todo; un examen te dice si memorizaron, pero no si saben aplicar…» El
   sistema dijo «ambivalente»; la investigadora y el autor, «no».
3. y 4. **Dos lecturas válidas de un cambio en el tiempo.** «Al principio me sentía muy sola, pero ahora
   sí…» y «No mucho; desde la pandemia todo se siente lejano, aunque antes de eso sí me sentía parte».
   La investigadora los leyó como ambivalentes; el autor y el sistema respondieron por el presente, que
   es lo que pedía la pregunta («¿en este momento?»).

**Interpretación.** El análisis automático coincide con la investigadora tanto como dos personas entre sí
coinciden en la mitad de las diferencias, y su acuerdo es sustancial (κ = 0.80). Las diferencias se
concentran en respuestas mixtas y en cambios de opinión en el tiempo. Por eso el análisis se entrega como
propuesta y el investigador lo revisa antes de publicar. El criterio de que la postura se refiere al
momento que pide la pregunta conviene declararlo al usar el sistema, porque explica dos de las cuatro
diferencias.

**Efecto de la última regla.** Antes de la regla de ambivalencia al inicio («depende…», «más o menos…»),
el acuerdo con la investigadora era de 26/32 (81.2 %, κ = 0.70); la regla corrigió las dos respuestas
«Depende: en unas sí, en otras no».

---

## Z.6 Comparación con el estado inicial

**Tabla R.17.** Las mismas preguntas antes (17 oct, sistema de la rama `PA` o primera versión del
RAG) y en la versión final.
<!-- fuente: registro 17 oct 21:25 (auditoría), 22:55 (primera prueba de humo); verificacion_20261017_2032.md; registro 18 oct; markdowns/PRUEBAS_RAG_INTEGRACION.md §10 -->

| Pregunta | Antes | Ahora |
|---|---|---|
| Escribe un poema sobre la motivación de los estudiantes | Pasaba el umbral (0.58); el modelo respondía «No tengo información…» tras 9.2 s | Regla de intención: fuera del dominio, sin modelo |
| ¿Cuál es el nombre y el correo del respondente R0017? | «No tengo información…» (engañoso), 4.2 s | Mensaje de privacidad, 0.1 s, sin modelo |
| ¿Qué es / qué significa un alfa de Cronbach bajo? | Rechazada (similitud 0.30) | Definición del glosario curado, con cita |
| ¿Qué opinan los estudiantes sobre la evaluación? | Respuesta sin datos reales, con 5 fuentes mayormente ajenas | Los chunks contienen las respuestas de cada persona |
| % del turno vespertino de acuerdo con p4 | «23.3 % (n=14)» | «13.3 % (4 de 30)» |
| ¿Por qué el KPI Tamaño Promedio de Clase está relacionado…? | Con la cita inventada «[Glosario: Tamaño Promedio de Clase]» | Justificación aceptada y fuente verificada `[Fuente KPI: OCDE]` |
| ¿Quién ganó el mundial? | «No tengo información…» | Mensaje de fuera del dominio con ejemplos |
| Uno de los que sí reprobaron por falta de tiempo… | «No tengo información…» | 88 de 160 y un respondente con sus respuestas |
| La misma pregunta dos veces | Otra llamada al modelo (15–30 s) | 0.1 s desde la caché |
| ¿Qué respondió R017…? en una encuesta sin secciones con encabezados P1…P8 | «R017 no tiene respuesta registrada en la pregunta p03» | «De acuerdo», igual que en el original |
| ¿Qué evalúa la encuesta…? sin secciones | Describía la encuesta por sus KPIs | Describe el contenido: criterios de evaluación, calificaciones, retroalimentación, ambiente |
| Encuesta en Excel (XLSX) | No se podía aprobar (el formato no cabía en `dc_format`) | Se aprueba y responde igual que el CSV |
| ¿Cuántos entrevistados creen que las extracurriculares influyen hoy en sus calificaciones? | Sin respuesta calculada; el relato del pasado pesaba igual que la respuesta | Conteo calculado de posturas (3 sí, 1 no) con la frase que responde de cada persona |

---

## Z.7 Limitaciones y amenazas a la validez

1. **Datos sintéticos.** Todas las respuestas son sintéticas; enc_01 conserva las preguntas de un
   instrumento publicado, pero no sus respuestas. Las cifras de α o de línea recta describen el
   generador, no a estudiantes. El acervo tampoco contiene duplicados, vacíos ni «No sé»; esas reglas
   se probaron con archivos pequeños.
2. **Juez pequeño.** Las métricas de la Tabla R.11 las calculó el mismo modelo de 3B que genera; desde
   el 23 oct el juez es `qwen2.5:3b`, también de 3B. Fidelidad y recall son aproximados: incluso RAGAS
   calificó como parcialmente infiel una respuesta exacta, y ningún juez probado detectó el cambio de una
   opción por otra. Falta validar el juez contra una anotación humana.
3. **Conjunto de evaluación pequeño.** 20 preguntas de referencia y 15 casos de verificación, escritos
   por el mismo equipo que construyó el sistema.
4. **Catálogo institucional de KPIs.** Los 55 KPIs son indicadores institucionales; la separación
   entre propuestas es de 0.04 a 0.15 y varios KPIs genéricos aparecen en casi todos los
   instrumentos. Solo 17 de los 55 tienen una fuente de referencia verificada.
5. **La comparación de métodos de KPIs** se hizo con el catálogo anterior, sobre dos instrumentos, y
   no se repitió con el catálogo actual.
6. **Comparaciones entre instrumentos.** La corrección de la ficha no se volvió a probar.
7. **Redacción del modelo de 3B.** En resultados largos (un respondente con 20 respuestas) se negó a
   redactar y se mostró el cálculo; en las justificaciones de KPI hubo errores gramaticales y
   relaciones débiles.
8. **Anonimización parcial del texto libre.** Las columnas personales se excluyen y los nombres de los
   hablantes se reemplazan, pero otros nombres mencionados dentro de una respuesta abierta pueden
   permanecer.
9. **Un solo equipo.** Las latencias (0.1–10 s) se midieron en un equipo con GPU de 4 GiB y
   memoria limitada; no se probó carga concurrente.
10. **Matriz de formatos sintética.** Los 20 formatos se escribieron con la forma de los exportes reales,
    pero a partir de datos sintéticos; no se probó un exporte real de Qualtrics o LimeSurvey.
11. **Acuerdo de posturas con pocas respuestas.** 32 respuestas de dos entrevistas sintéticas y dos
    anotadores humanos. Falta repetirlo con una entrevista real.

---

## Z.8 Trabajo futuro

- Validar con respuestas reales de una institución, con su autorización.
- Usar un juez de métricas más grande (`RAG_JUEZ_MODELO`) cuando haya una GPU con más memoria, y
  ampliar el conjunto de preguntas de referencia con preguntas escritas por investigadores.
- Repetir `comparar_kpis` con el catálogo actual y sobre todo el acervo; probar una penalización para
  los KPIs genéricos que se parecen a todo.
- Completar fuentes verificadas para los 38 KPIs que no tienen.
- Guardar las conversaciones en el servidor en lugar del navegador.
- Detectar nombres propios dentro del texto libre (reconocimiento de entidades) para mejorar la
  anonimización.
- Probar instrucciones inyectadas dentro de los instrumentos.
- Anotar una entrevista real (con consentimiento) para medir el acuerdo del análisis de posturas fuera de
  los datos sintéticos.
- Aceptar entrevistas en Excel (una fila por pregunta y respuesta) y transcribir audio dentro del flujo.

---

## Figuras propuestas

| Figura | Contenido | Sección |
|---|---|---|
| R.1 | «Estadística» y «Antes y después» de enc_04 | Z.2.1 |
| R.2 | «KPIs sugeridos» con evidencia y justificación | Z.3 |
| R.3 | Respuesta del chat con fuentes y panel de métricas | Z.4.3 |
| R.4 | Vista rápida con «Calidad de los datos y sugerencias» | Z.2.4 |
| R.5 | Tabla resumen de la matriz de formatos (`encuestas.md` y `entrevistas.md`) | Z.5.1, Z.5.3 |
| R.6 | Panel «Análisis de las respuestas» con la respuesta de la beca deportiva | Z.5.3 |

## Lista de [PENDIENTE] de este capítulo

1. Texto exacto de los objetivos de la tesis (Z.1).
2. Las 8 columnas demográficas que la limpieza sugiere como «pregunta» y el número de preguntas reales de enc_04 (Tabla R.2).
3. Confirmar que los KPIs de 55 y 61 los eligió la investigadora en la interfaz (Tabla R.8).
4. Tomar las capturas R.5 y R.6; el panel de análisis aún no se ha revisado en el navegador (Z.5.3).
5. Repetir la anotación de posturas con una entrevista real, si se cuenta con una (Z.5.4, Z.7).
6. Recalcular la Tabla R.11 con el juez `qwen2.5:3b` y medir el acuerdo entre el juez y una anotación humana (Z.4.1).