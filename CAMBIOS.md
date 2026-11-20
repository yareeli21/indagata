# Cambios en `rag tt_alineado.docx`

Copia alineada de `documentación/rag tt.docx` (el original no se modificó; SHA-256 `0979ea88…c47d323`). Cada fila dice dónde está el cambio (sección y bloque del original, el índice `[n]` de `texto.txt`), el texto anterior, el nuevo y la evidencia o el motivo. Los números de tabla y figura de esta lista son los **del original**; el mapa de la renumeración está al final.

Resumen:

- 556 ediciones de texto, tablas, pies y bloques de código.
- 35 cambios de citas (fuentes equivocadas, duplicados, citas en texto plano o autor-año pasadas a campos de Zotero, fuentes nuevas); la bibliografía queda con 95 entradas, todas citadas, en orden de aparición (IEEE).
- 270 pies convertidos a campos SEQ y numerados en orden (187 tablas y 83 figuras; los pies de las Figuras 59–61 del original están en cuadros de texto, cuya copia de respaldo lleva el mismo número); 166 referencias del texto ajustadas a la numeración nueva, ninguna sin destino.
- Campos, índice general, índice de tablas e índice de figuras actualizados con Word.

## Ediciones

| Bloque | Sección | Antes | Después | Evidencia o motivo |
|---|---|---|---|---|
| [266] | Contexto general | cita a ['SWJX7J8W'] | cita a ['XWYDE4T4'] | fusión de entradas duplicadas |
| [273] | Estructura del documento | Para facilitar la comprensión de los alcances de esta investigación, el documento se organiza de la siguiente manera: tras esta introducción, el capítulo 2 expone el marco teórico con los fundamentos de PLN, ciencia de datos y arquitecturas web; el capítulo 3 … | Para facilitar la comprensión de los alcances de esta investigación, el documento se organiza de la siguiente manera: tras esta introducción, el capítulo 2 expone el marco teórico con los fundamentos de IA, ciencia de datos, arquitecturas web y educación; el c… | Estructura del documento: el documento tiene 8 capítulos |
| [280] | Descripción del problema | cita a ['YQWS3VSS'] | cita a ['Z4Q24JIC'] | fusión de entradas duplicadas |
| [327] | Originalidad del aporte | Adicionalmente, la validación con instrumentos educativos de fuentes públicas verificadas permite demostrar la generalidad del módulo más allá de un contexto institucional específico, lo que extiende el alcance del aporte a cualquier institución que enfrente e… | Adicionalmente, el sistema no depende de un contexto institucional específico: se probó con encuestas, entrevistas y pruebas estandarizadas que reproducen la estructura de instrumentos educativos reales, con respuestas sintéticas (5.4), lo que extiende el alca… | origen de los datos: instrumentos sintéticos, sin datos públicos de respuestas |
| [367] | Arquitectura RAG | [4] | [cita: 596YYBJT] | fuente equivocada: la eficacia de RAG es de Lewis et al. |
| [382] | Análisis comparativo del trabajo actual en materia de RAG y … | TRF-IDF/BM25 | TF-IDF/BM25 | errata |
| [382] | Análisis comparativo del trabajo actual en materia de RAG y … | [3] | [cita: N_ROBERTSON] | fuente equivocada: BM25 |
| [436] | Análisis comparativo del uso de IA generativa y métodos de r… | (nuevo) | Tabla (n) Contraste de los trabajos sobre instrumentos educativos y KPIs con la propuesta | tabla sin pie |
| [461] | IA generativa | mediante aprendizaje supervisado | mediante aprendizaje autosupervisado | los modelos fundacionales se preentrenan sin etiquetas; la frase siguiente lo dice |
| [494] | LLM | [16] | [cita: KVPJL3HS] | fuente equivocada: few-shot es de Brown et al. (el [16] era una página de Google Cloud) |
| [502] | LLM | lo que eleva exponencialmente la demanda | lo que eleva cuadráticamente la demanda | una complejidad cuadrática no crece de forma exponencial |
| [526] | Optimización de búsqueda vectorial | [23] | [cita: N_MALKOV] | fuente equivocada: HNSW |
| [527] | Optimización de búsqueda vectorial | [24, 33] | [cita: UIJ66DAV+L2XIFXZS] | fuente equivocada: las métricas de recuperación (Manning et al., Salton y McGill) |
| [560] | Transformers | cita a ['UV44K79Y'] | cita a ['Z7SGY6RC'] | fusión de entradas duplicadas |
| [560] | Transformers | cita a ['UV44K79Y'] | cita a ['Z7SGY6RC'] | fusión de entradas duplicadas |
| [561] | Transformers | cita a ['UV44K79Y'] | cita a ['Z7SGY6RC'] | fusión de entradas duplicadas |
| [562] | Transformers | cita a ['UV44K79Y'] | cita a ['Z7SGY6RC'] | fusión de entradas duplicadas |
| [563] | Transformers | cita a ['UV44K79Y'] | cita a ['Z7SGY6RC'] | fusión de entradas duplicadas |
| [565] | Transformers | cita a ['UV44K79Y'] | cita a ['Z7SGY6RC'] | fusión de entradas duplicadas |
| [566] | Transformers | cita a ['UV44K79Y'] | cita a ['Z7SGY6RC'] | fusión de entradas duplicadas |
| [600] | Importancia de la calidad de los datos | [42] | [cita: IN7CTCTZ] | fuente equivocada: calidad del dato (Pipino et al.) |
| [609] | Protección de datos y marco normativo | La Ley Federal de Protección de Datos Personales en Posesión de Sujetos Obligados (LFPDPSO) | La Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados (LGPDPPSO) | nombre correcto de la ley (la Federal es la de particulares); la vigente se publicó en el DOF el 20 de marzo de 2025 |
| [609] | Protección de datos y marco normativo | [74] | [cita: N_LGPDPPSO] | fuente equivocada: texto oficial de la ley |
| [611] | Análisis de texto | [44] | [cita: UIJ66DAV] | cita en texto plano a Manning et al. |
| [717] | Protocolos HTTP y seguridad de red | IDEMPOTENT para actualizaciones | PUT o PATCH para actualizaciones | IDEMPOTENT no es un método HTTP |
| [725] | Protocolos HTTP y seguridad de red | Mecanismo que restringe las peticiones HTTP realizadas desde un dominio distinto al del servidor, previniendo ataques de falsificación de peticiones en sitios cruzados (CSRF) y asegurando que solo orígenes autorizados interactúen con la API. | Mecanismo con el que el servidor indica qué orígenes distintos al suyo pueden leer sus respuestas desde el navegador, de modo que solo los orígenes autorizados consumen la API. No previene por sí solo la falsificación de peticiones en sitios cruzados (CSRF), q… | CORS controla las lecturas entre orígenes; no evita CSRF |
| [744] | Análisis de datos en el ámbito educativo | las clases con mayores capitales podrían reducirse si el rendimiento medio de los estudiantes no es a la altura | las clases con más alumnos podrían reducirse si el rendimiento medio de los estudiantes no está a la altura | traducción sin sentido de «larger class sizes» |
| [755] | Seguridad y/o integridad de la información | 19977 | 1977 | errata del año |
| [757] | Seguridad y/o integridad de la información | busca garantizar que sólo las personas autorizadas a ello podrán acceder a información privilegiada de la empresa. La integridad de una base de datos se aplica a través de protocolos de autenticación, políticas internas (como las que impulsan la seguridad de l… | busca garantizar que la información no se altere ni se destruya sin autorización y que se mantenga exacta y completa. Se apoya en controles como las sumas de verificación (hash), el registro de los cambios y un control de acceso que define quién puede modifica… | la definición dada era la de confidencialidad |
| [772] | Marco metodológico: enfoque DSRM | DSRM (Data Science Methodology for Research) | DSRM (Design Science Research Methodology) | así lo nombra la propia referencia de Peffers et al. |
| [772] | Marco metodológico: enfoque DSRM | y MLLMOps como framework de evaluación continua | y LLMOps como marco de evaluación continua | MLLMOps no es un marco reconocido |
| [775] | Marco metodológico: enfoque DSRM | MLLMOps | LLMOps, con RAGAS | MLLMOps no es un marco reconocido; la cita pasa a RAGAS |
| [775] | Marco metodológico: enfoque DSRM | provee el conjunto | , provee el conjunto | puntuación tras la cita |
| [775] | Marco metodológico: enfoque DSRM | cita a HFD7JIUM | cita a RMJ7ZTPK | «MLLMOps» no es un marco; la cita pasa a RAGAS |
| [784] | Fase 1 — Comprensión del dominio y definición del problema | (métricas MLLMOps definidas en la sección 6.4) | (métricas de recuperación y de RAGAS definidas en la sección 6.4) | MLLMOps no es un marco reconocido |
| [786] | Fase 2 — Ingeniería de datos: módulo de ingesta y limpieza | en el directorio /crudos/ con su hash MD5 calculado | en el servicio de almacenamiento con su huella SHA-256 calculada | storage-service usa SHA-256 (código local: services/storage-service/services/file_manager.py:147) |
| [802] | Fase 5 — Capa de almacenamiento: arquitectura de tres compon… | el archivo original en /crudos/ (inmutable, con hash MD5) | el archivo original (inmutable, con su huella SHA-256) | SHA-256 en storage-service (código local) |
| [804] | MLLMOps: evaluación continua del sistema RAG | MLLMOps | LLMOps | MLLMOps no es un marco reconocido |
| [806] | Justificación del framework | MLLMOps (Machine Learning LLM Operations) provee | LLMOps (Large Language Model Operations) reúne | MLLMOps no es un marco reconocido |
| [820] | Modelo de embeddings | El modelo pesa 420 MB y corre en CPU sin GPU dedicada. | El modelo ocupa cerca de 1.1 GB en disco y corre en CPU sin GPU dedicada. | medido en el volumen hf_cache del contenedor (1.1 GB) |
| [823] | Modelo de embeddings | Dicho modelo seleccionado tiene 512 tokens como característica fija, dado que el modelo está basado en la arquitectura BERT. BERT fue diseñado originalmente con una ventana de contexto de 512 tokens porque ese era el límite que el hardware de 2018 podía proces… | El modelo lee como máximo 128 tokens de cada texto: aunque la arquitectura BERT en la que se basa admite 512, este modelo se entrenó y se distribuye con un límite de 128, y lo que pasa de ahí se descarta sin aviso. Por eso los chunks se miden en tokens antes d… | la ventana real del modelo es de 128 tokens (caps. 4–6 y código del chunker) |
| [832] | Modelo de lenguaje | de 32 bits a 4 bits. Eso reduce el tamaño a la cuarta parte de una pérdida de calidad mínima | de 16 bits a 4 bits. Eso reduce el tamaño a la cuarta parte con una pérdida de calidad mínima | de 32 a 4 bits sería una octava parte; el ejemplo de 16 GB corresponde a 16 bits |
| [840] | Requerimientos funcionales | [RF_01 · col 3] El sistema despliega una interfaz web que permite la navegación entre módulos — ingesta, estandarización, consulta y administración | El sistema despliega una interfaz web (React 19 con TanStack Start) con un asistente de siete pasos para cargar y procesar instrumentos, el catálogo del acervo, los tableros de KPIs, el chat y, para el administrador, el alta de usuarios | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_02 · col 3] El sistema acepta archivos en formato CSV, XLSX, XLS, ODS, TXT, PDF depende qué instrumento se ingrese. Archivos con estructura incompatible depende el instrumento son rechazados con mensaje informativo al investigador | El sistema acepta, según el tipo de instrumento, archivos tabulares (CSV, XLSX, XLS) o documentos (PDF, DOCX, TXT) con las respuestas y, de forma opcional, el instrumento original sin respuestas. Los archivos que no cumplen el contrato de formatos se rechazan … | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_03 · col 3] El sistema aplica limpieza básica de ciencia de datos sin intervención humana además de detectar casos ambiguos depende el instrumento y los presenta al investigador con contexto y sugerencia para su validación explícita antes de aplicar cualqu… | El sistema aplica sin intervención las transformaciones que no requieren decisión y presenta los casos ambiguos de cada tipo de instrumento con su contexto y una opción sugerida; ninguna corrección se aplica sin la confirmación del investigador. Cada limpieza … | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_04 · col 3] El sistema guarda el archivo original sin modificación en el sistema de ficheros y calcula su hash MD5 de todo el contenido como evidencia de integridad | El sistema guarda el archivo original sin modificación en el servicio de almacenamiento, con una clave versionada y su huella SHA-256, que se comprueba al descargarlo | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_05 · col 3] El sistema captura metadatos en niveles jerárquicos depende el instrumento combinando inferencia automática con captura editorial del investigador | El sistema propone los 13 campos Dublin Core y los metadatos propios de cada tipo de instrumento a partir de la limpieza confirmada (con reglas y, en los campos interpretativos, con el modelo de lenguaje); el investigador los revisa y los aprueba | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_06 · col 1] Inferencia de KPIs mediante LLM | Asociación de KPIs por similitud | RF alineado al sistema |
| [840] | Requerimientos funcionales | [RF_06 · col 3] El sistema infiere automáticamente los KPIs relevantes para cada pregunta mediante una llamada al LLM por pregunta con el catálogo completo de indicadores activos. El investigador valida cada relación inferida antes de que quede activa | El sistema propone los KPIs del catálogo que el instrumento puede medir comparando su perfil semántico con cada KPI (puntaje 0.45·g + 0.45·p + 0.10·c), con las preguntas que los sustentan y una justificación redactada por el modelo de lenguaje. El investigador… | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_07 · col 3] El sistema genera el archivo JSON con los metadatos completos incluyendo KPIs validados | El sistema genera el JSON técnico al aprobar los metadatos y el JSON final de cada tipo de instrumento, validado con su esquema, con los KPIs aceptados y las respuestas interpretadas | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_08 · col 3] El sistema construye chunks enriquecidos semánticamente mediante prompts propuestos al LLM por tipo de instrumento, los vectoriza con el modelo de embeddings y los almacena en las colecciones correspondientes de Chroma | El sistema construye los chunks del JSON final con plantillas fijas, los mide en tokens (máximo 128), los vectoriza con el modelo de embeddings y los guarda en la colección instrumentos de ChromaDB y en la tabla documento_vectorizado | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_9 · col 3] El sistema permite al investigador formular consultas en lenguaje natural y genera respuestas contextualizadas a partir de los chunks recuperados de Chroma mediante el modelo de lenguaje local | El sistema permite formular consultas en lenguaje natural sobre los instrumentos del alcance elegido y responde con cifras calculadas en código, los fragmentos recuperados por la búsqueda híbrida y sus fuentes, mediante el modelo de lenguaje local | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_10 · col 3] El sistema presenta una vista enriquecida de cada instrumento procesado con metadatos completos, y KPIs relacionados | El sistema presenta una vista de cada instrumento procesado con sus metadatos, sus KPIs asociados, la calidad de sus datos y su tiempo de procesamiento | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_11 · col 3] El sistema permite al investigador descargar el .SAV (en caso de encuestas) y el JSON generados durante la estandarización | El sistema permite descargar el archivo original, el JSON y, en las encuestas, el archivo .sav para SPSS | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_12 · col 1] Gestión del catálogo de KPIs | Catálogo de KPIs | RF alineado al sistema |
| [840] | Requerimientos funcionales | [RF_12 · col 3] El administrador puede añadir nuevos KPIs, editar los existentes y desactivar los obsoletos sin modificar el código del sistema | El catálogo de KPIs, con sus fuentes de referencia, se carga desde un archivo CSV versionado mediante un script, y el administrador lo vuelve a vectorizar con un servicio de mantenimiento, sin modificar el código del sistema | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_13 · col 1] Gestión del catálogo de prompts | Instrucciones del modelo versionadas | RF alineado al sistema |
| [840] | Requerimientos funcionales | [RF_13 · col 3] El administrador puede añadir o actualizar los prompts para las inferencias con el LLM sin modificar el código del sistema | Las instrucciones del modelo de lenguaje y las reglas del chat están en el código y en archivos de configuración versionados con el repositorio (DA-13); no se editan desde la interfaz | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_14 · col 3] El administrador puede eliminar completamente un instrumento del sistema — vectores en Chroma, registros en PostgreSQL y ficheros físicos — de forma irreversible con confirmación explícita. | El autor de un instrumento o un administrador pueden eliminarlo por completo —registros en PostgreSQL, archivos (incluido el original) y vectores en ChromaDB— de forma irreversible y con confirmación explícita | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [840] | Requerimientos funcionales | [RF_16 · col 3] El sistema registra cada consulta del investigador en rag_log con la pregunta, la respuesta, el modelo usado y la latencia para monitoreo y auditoría | El sistema registra cada consulta en rag_log con la pregunta, la respuesta, la ruta, el plan, el contexto usado, la latencia y el tiempo de cada etapa, para monitoreo y auditoría | RF alineado al sistema (código local; DA-13, DA-14, 5.5) |
| [845] | Requerimientos no funcionales | [RNF_01 · col 3] < 15 segundos | Mediana ≤ 20 s por turno | RNF ajustado a lo que se mide (6.7.9, 6.8.1, 6.10) |
| [845] | Requerimientos no funcionales | [RNF_01 · col 4] El sistema genera respuestas a consultas en lenguaje natural en menos de 15 segundos en hardware estándar sin GPU dedicada | El chat responde con una mediana de 20 segundos o menos por turno con llama3.2:3b en una GPU de 4 GB; sin GPU, el tiempo depende del procesador y no se garantiza | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_04 · col 3] Entre 5 y 30 minutos según el instrumento | ≤ 5 min por instrumento | RNF ajustado a lo que se mide (6.7.9, 6.8.1, 6.10) |
| [845] | Requerimientos no funcionales | [RNF_04 · col 4] La vectorización completa de un instrumento, incluyendo la síntesis de chunks con LLM, depende del número de respondentes y variables. Se ejecuta una sola vez por instrumento | La vectorización de un instrumento (chunks con plantillas fijas, sin modelo de lenguaje) termina en 5 minutos o menos para instrumentos de hasta 2,000 respondentes. Se ejecuta en segundo plano al aprobar los metadatos y al publicar el JSON final | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_05 · col 1] Tiempo de inferencia de KPIs | Tiempo de propuesta de KPIs | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_05 · col 3] < 15 minutos | ≤ 3 min por instrumento | RNF ajustado a lo que se mide (6.7.9, 6.8.1, 6.10) |
| [845] | Requerimientos no funcionales | [RNF_05 · col 4] La inferencia de KPIs mediante LLM — una llamada por pregunta — se completa en menos de 15 minutos para instrumentos de hasta 200 preguntas con un catálogo de hasta 20 KPIs | La propuesta de KPIs por similitud, con la justificación del modelo de lenguaje, termina en 3 minutos o menos con el catálogo de 55 KPIs | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_06 · col 3] Precision@K y Recall@K ≥ 0.7 | Hit@8 ≥ 0.90 y MRR ≥ 0.80 | RNF ajustado a lo que se mide (6.7.9, 6.8.1, 6.10) |
| [845] | Requerimientos no funcionales | [RNF_06 · col 4] El módulo RAG recupera chunks relevantes con métricas de precisión y recall iguales o superiores a 0.7 evaluadas sobre los datasets de validación | La búsqueda pone el fragmento correcto entre los 8 que recibe el modelo en al menos el 90 % de las preguntas, con un MRR de 0.80 o más, sobre preguntas con juicios de relevancia fijados de antemano; las métricas de RAGAS se reportan como medida aproximada | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_07 · col 4] El sistema restringe el acceso a usuarios autorizados mediante autenticación. Las operaciones irreversibles como la eliminación de instrumentos están restringidas al rol administrador | El sistema restringe el acceso a usuarios autorizados mediante autenticación. La eliminación de un instrumento está restringida a su autor o a un administrador | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_10 · col 3] Hash MD5 verificable | Huella SHA-256 verificable | RNF ajustado a lo que se mide (6.7.9, 6.8.1, 6.10) |
| [845] | Requerimientos no funcionales | [RNF_10 · col 4] El sistema garantiza que el archivo original no fue modificado tras la ingesta mediante hash MD5 verificable en cualquier momento | El sistema garantiza que el archivo original no cambió tras la ingesta mediante su huella SHA-256, que el servicio de almacenamiento comprueba al descargarlo | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_11 · col 1] Inmutabilidad de metadatos | Versionado de metadatos | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_11 · col 3] Sin modificación tras estandarización | Toda versión anterior se conserva | RNF ajustado a lo que se mide (6.7.9, 6.8.1, 6.10) |
| [845] | Requerimientos no funcionales | [RNF_11 · col 4] Los metadatos editoriales quedan bloqueados una vez completada la estandarización — consistente con DA-12 | Repetir la limpieza o republicar el JSON final crea una versión nueva; las anteriores se conservan como respaldo y solo una es la vigente | RNF alineado al sistema |
| [845] | Requerimientos no funcionales | [RNF_12 · col 4] Cada vector almacenado en Chroma tiene un registro correspondiente en documento_vectorizado con el texto exacto, la plantilla usada y la fecha de generación | Cada vector almacenado en ChromaDB tiene un registro en documento_vectorizado con el texto exacto, su número de tokens, sus metadatos y el identificador del vector | RNF alineado al sistema |
| [849] | Reglas del negocio | [RN_01 · col 3] Toda respuesta generada por el LLM debe basarse exclusivamente en los chunks recuperados de Chroma. El sistema instruye al modelo a no generar información que no esté presente en el contexto proporcionado | Toda respuesta del chat se basa en el resultado calculado y en los fragmentos recuperados; el sistema instruye al modelo a no agregar información y verifica la redacción antes de mostrarla | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_02 · col 3] El sistema acepta la estructura estándar depende el instrumento. Archivos en cualquier otro formato o estructura son rechazados con mensaje informativo al investigador | El sistema acepta el formato definido para cada tipo de instrumento (5.3). Los archivos que no lo cumplen se rechazan con un mensaje que explica el motivo | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_03 · col 3] El archivo original se guarda sin modificación en /crudos/ y su hash MD5 se registra en el momento de la ingesta. | El archivo original se guarda sin modificación en el servicio de almacenamiento y su huella SHA-256 se registra al recibirlo | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_04 · col 3] El sistema distingue dos roles con permisos diferenciados. El investigador puede ingresar instrumentos, completar metadatos, consultar y descargar artefactos. El administrador tiene acceso adicional a la gestión de KPIs, prompts, usuarios y eli… | El sistema distingue dos roles con permisos diferenciados. El investigador puede ingresar instrumentos, completar metadatos, consultar, descargar artefactos y eliminar los instrumentos que él subió. El administrador puede, además, dar de alta usuarios y elimin… | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_05 · col 1] Unicidad de instrumentos | Huella de cada archivo | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_05 · col 3] El sistema detecta archivos duplicados mediante comparación de hash MD5. Si el hash de un archivo entrante coincide con el de un instrumento ya registrado el sistema informa al investigador que ese instrumento ya existe en el sistema | Cada carga se registra como un instrumento con su propio identificador, y cada archivo guardado lleva su huella SHA-256, que se comprueba en cada descarga (RM-04) | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_06 · col 3] El sistema solo puede responder consultas sobre instrumentos que han completado todo el procesamiento. Instrumentos en proceso o con errores no son consultables. | El chat solo consulta instrumentos con metadatos aprobados por su autor y ya indexados; los instrumentos en proceso no son consultables | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_07 · col 1] Validación humana de KPIs | Validación humana de KPIs | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_07 · col 3] Ninguna relación KPI-pregunta inferida automáticamente por el LLM queda activa en el sistema sin validación explícita del investigador. | Ninguna relación entre un KPI y un instrumento propuesta por el sistema queda activa sin la aceptación explícita del investigador | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_08 · col 1] Inmutabilidad de metadatos | Versionado de metadatos | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_08 · col 3] Los metadatos editoriales de un instrumento quedan bloqueados una vez completada la estandarización. Si el investigador necesita corregir algún metadato debe eliminar el instrumento completamente mediante CU-09 y volver a procesarlo desde cero | Los metadatos aprobados no se sobrescriben: corregirlos genera una nueva versión del conocimiento y la anterior se conserva | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_09 · col 3] La eliminación de un instrumento es permanente y opera en cascada sobre todas las capas del sistema. La operación queda registrada en rag_log, existe la posibilidad de eliminar igual de archivos en crudo o no, como decida el investigador. | La eliminación de un instrumento es permanente y opera en cascada sobre todas las capas del sistema: registros, archivos —incluido el original— y vectores | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_11 · col 1] Plantillas de prompts activas por tipo | Instrucciones del modelo versionadas | RN alineada al sistema |
| [849] | Reglas del negocio | [RN_11 · col 3] Para cada combinación de tipo de instrumento y tipo de chunk deben existir los prompts necesarios para emplear en el LLM activo en el catálogo. El sistema no puede construir chunks si no encuentra un prompt activo correspondiente. | Las instrucciones y plantillas que usa el sistema están en el código y en archivos de configuración versionados; los chunks se construyen con plantillas fijas, sin un catálogo de prompts | RN alineada al sistema |
| [856] | Matriz de trazabilidad | [RF_01 · col 2] Frontend (Streamlit/Web Framework) | Frontend (React 19 con TanStack Start) | el frontend no es Streamlit |
| [856] | Matriz de trazabilidad | [RF_02 · col 3] Subida exitosa de archivos .xlsx, .csv y .txt. | Subida exitosa de archivos .csv, .xlsx, .xls, .pdf, .docx y .txt según el tipo. | formatos reales |
| [856] | Matriz de trazabilidad | [RF_04 · col 2] Repositorio de Archivos | storage-service | storage-service guarda los archivos |
| [856] | Matriz de trazabilidad | [RF_04 · col 3] Persistencia de archivos originales en almacenamiento seguro. | Archivo original guardado sin cambios, con su huella SHA-256 comprobada al descargar. | SHA-256 |
| [856] | Matriz de trazabilidad | [RF_06 · col 1] Inferencia de KPIs | Asociación de KPIs por similitud | KPIs por similitud |
| [856] | Matriz de trazabilidad | [RF_06 · col 2] LLM infiere KPIs en cada instrumento | analysis-service: similitud del perfil semántico con el catálogo | KPIs por similitud |
| [856] | Matriz de trazabilidad | [RF_06 · col 3] KPI agregado como metadato | KPIs aceptados con su evidencia y su justificación | KPIs por similitud |
| [856] | Matriz de trazabilidad | [RF_07 · col 2] LLM Llama 3.2/Llama 3.1 | knowledge-service: JSON final validado con su esquema | el artefacto lo genera knowledge-service |
| [856] | Matriz de trazabilidad | [RF_07 · col 3] Respuesta coherente a preguntas abiertas del usuario. | Documento que cumple su JSON Schema. | validación real |
| [856] | Matriz de trazabilidad | [RF_08 · col 2] Base de datos vectorial ChromaDB | storage-service y ChromaDB | storage-service vectoriza |
| [856] | Matriz de trazabilidad | [RF_08 · col 3] Chunks enriquecidos semánticamente | Chunks de 128 tokens o menos indexados | chunks medidos en tokens |
| [856] | Matriz de trazabilidad | [RF_09 · col 2] LLM recupera chunks semejantes en ChromaDB | visualization-service: búsqueda híbrida, cálculo en código y redacción con llama3.2:3b | consulta real |
| [856] | Matriz de trazabilidad | [RF_12 · col 1] Generación del catálogo de KPIs | Catálogo de KPIs | catálogo cargado desde CSV |
| [856] | Matriz de trazabilidad | [RF_12 · col 2] Se implementa un catálogo de KPIs educativos | Catálogo cargado desde un archivo CSV con un script de carga | catálogo cargado desde CSV |
| [856] | Matriz de trazabilidad | [RF_12 · col 3] Al momento de realizar la inferencia por LLM al instrumento | Catálogo vectorizado en la colección kpis | catálogo cargado desde CSV |
| [856] | Matriz de trazabilidad | [RF_13 · col 1] Gestión del catálogo de prompts | Instrucciones del modelo versionadas | no existe catálogo de prompts (DA-13) |
| [856] | Matriz de trazabilidad | [RF_13 · col 2] Se implementa un catálogo de prompts para construcción de chunks durante la vectorización | Instrucciones y plantillas en archivos versionados con el repositorio | DA-13 |
| [856] | Matriz de trazabilidad | [RF_13 · col 3] Al momento de vectorizar se esperan chunks bien contextualizados | Chunks construidos con plantillas fijas | DA-08 |
| [856] | Matriz de trazabilidad | [RF_14 · col 3] Instrumento eliminado con éxito, aunque con la opción de preservar al archivo en crudo. | Instrumento eliminado por completo, incluido el archivo original. | CU-09 y DA-14 |
| [860] | Matriz de trazabilidad | [RNF_01 · col 3] Pruebas de carga y cronometraje de consultas de consultas en hardware estándar sin GPU | Mediana y percentil 90 del tiempo por turno registrados en rag_log (GPU de 4 GB) | RNF_01 ajustado |
| [860] | Matriz de trazabilidad | [RNF_05 · col 1] Tiempo de inferencia de KPIs | Tiempo de propuesta de KPIs | KPIs por similitud |
| [860] | Matriz de trazabilidad | [RNF_05 · col 3] Cronometraje del proceso de evaluación del catálogo de KPIs por cada pregunta | Tiempo registrado del paso «Propuesta de KPIs» | KPIs por similitud |
| [860] | Matriz de trazabilidad | [RNF_06 · col 3] Evaluación del sistema mediante el framework MLLMOps sobre datasets de validación | Hit@k y MRR con juicios de relevancia y búsqueda de elemento conocido; RAGAS como medida aproximada | RNF_06 ajustado |
| [860] | Matriz de trazabilidad | [RNF_10 · col 3] Generación y comparación manual del hash MD5 de un documento almacenado en /crudos/ contra el hash registrado en la ingesta | Comparación de la huella SHA-256 del archivo guardado con la registrada al recibirlo | SHA-256 |
| [860] | Matriz de trazabilidad | [RNF_11 · col 1] Inmutabilidad de metadatos | Versionado de metadatos | metadatos versionados |
| [860] | Matriz de trazabilidad | [RNF_11 · col 3] Intento de inyección de un UPDATE a los metadatos de un instrumento que ya cuenta con el estado de estandarización completada | Repetir la limpieza o republicar el JSON final crea una nueva versión y conserva la anterior | metadatos versionados |
| [878] | Recursos operativos necesarios | vectcorial | vectorial | errata |
| [878] | Recursos operativos necesarios | React 18n+ con Node.js | React 19 con Node.js | errata; la versión real es React 19 |
| [892] | Componentes técnicos del sistema | Bge-m3 (sentence-transformer) | paraphrase-multilingual-mpnet-base-v2 (Sentence-Transformers) | modelo de embeddings real (config.py:45) |
| [892] | Componentes técnicos del sistema | Hasting | Hosting | errata |
| [892] | Componentes técnicos del sistema | React 18+ | React 19 | versión real (package.json:47) |
| [900] | Requerimientos de Software | Open sourcc | Open source | errata |
| [952] | Diseño | En esta primera versión, los instrumentos se obtienen de fuentes públicas que recaban información educativa en español, con el fin de analizar su estructura y variables, y establecer un estándar de procesamiento aplicable al contexto hispanohablante. | Para establecer un estándar de procesamiento aplicable al contexto hispanohablante se analizaron la estructura y las variables de instrumentos educativos publicados, como los revisados en el estado del arte (1.6). Como no hay datos públicos de respuestas de es… | origen de los datos: instrumentos sintéticos, sin datos públicos de respuestas |
| [952] | Diseño | [99] | [cita: N_COHEN] | cita a una fuente que no existía en la bibliografía |
| [953] | Diseño | Nota: durante el desarrollo, además de los instrumentos públicos, se construyeron instrumentos sintéticos para probar cada caso de limpieza y de consulta (5.4). El JSON completo del que habla el párrafo siguiente es el JSON final de cada instrumento (5.5.6). | (se quitó) | cap. 4: la nota se integra al texto |
| [954] | Diseño | producir un JSON completo con metadatos | producir un JSON completo, el JSON final del instrumento (5.5.6), con metadatos | cap. 4: la nota se integra al texto |
| [956] | Arquitectura general del sistema | compuesta por PostgreSQL, el sistema de ficheros y ChromaDB | compuesta por PostgreSQL, un servicio de almacenamiento de archivos y ChromaDB | cap. 4: la nota se integra al texto |
| [958] | Arquitectura general del sistema | Nota: después de las pruebas en el ambiente de desarrollo, los módulos se implementaron como microservicios detrás de un API Gateway, y el sistema de ficheros quedó a cargo de un servicio de almacenamiento con archivos versionados. La separación por módulos y … | Cada módulo se implementa como uno o varios microservicios, a los que la interfaz accede a través de un API Gateway. Los archivos los administra el servicio de almacenamiento, que los guarda con claves versionadas (5.1 y 5.2). | cap. 4: la nota se integra al texto |
| [966] | Restricciones tecnológicas | sin cambiar la arquitectura del sistema. | sin cambiar la arquitectura del sistema. En el ambiente de desarrollo se usó una GPU GTX 1650 de 4 GiB, en la que el modelo llama3.2:3b cabe completo y uno de 8B no; por eso el sistema usa llama3.2:3b (5.7). | cap. 4: la nota se integra al texto |
| [967] | Restricciones tecnológicas | Nota: en el ambiente de desarrollo se usó una GPU GTX 1650 de 4 GiB, en la que llama3.2:3b cabe completo; por eso se optó por ese modelo y no por uno de 8B, que no cabe en esa memoria (5.7). | (se quitó) | cap. 4: la nota se integra al texto |
| [969] | Restricciones tecnológicas | El sistema define un umbral mínimo de similitud coseno para determinar si los chunks recuperados de Chroma son suficientemente relevantes para generar una respuesta. Este umbral es un parámetro de configuración gestionado por el administrador. Si ningún chunk … | El sistema define un umbral mínimo de similitud coseno para decidir si los chunks recuperados de ChromaDB son suficientemente relevantes para generar una respuesta. El umbral es un parámetro de configuración del servidor y actúa junto con una búsqueda por pala… | cap. 4: la nota se integra al texto |
| [970] | Restricciones tecnológicas | Nota: en la implementación, el umbral es un parámetro de configuración del servidor y, junto con una búsqueda por palabras, decide qué fragmentos llegan a la respuesta (4.9 y 5.7.3). | (se quitó) | cap. 4: la nota se integra al texto |
| [978] | Restricciones del alcance | Validación con datasets públicos educativos en español | Validación con instrumentos educativos en español | origen de los datos: instrumentos sintéticos, sin datos públicos de respuestas |
| [979] | Restricciones del alcance | El sistema se valida con instrumentos de recolección de datos educativos de acceso público en español. | El sistema se valida con instrumentos de recolección de datos educativos en español, con respuestas sintéticas generadas para este trabajo, porque no hay datos públicos de respuestas de este tipo (5.4). | origen de los datos: instrumentos sintéticos, sin datos públicos de respuestas |
| [981] | Restricciones del alcance | No se contempla acceso sin autenticación. | No se contempla acceso sin autenticación. Ninguno de los dos roles edita desde la interfaz las instrucciones del modelo ni el catálogo de KPIs: ambos se mantienen en archivos versionados con el sistema, y el catálogo se carga con un script (5.1.4 y 5.10). | cap. 4: la nota se integra al texto |
| [982] | Restricciones del alcance | Nota: después de las pruebas se optó por mantener las instrucciones del modelo y el catálogo de KPIs en archivos versionados con el sistema, en lugar de editarlos desde la interfaz; el catálogo se carga con un script (5.1.4 y 5.10). | (se quitó) | cap. 4: la nota se integra al texto |
| [990] | Restricciones metodológicas | Unicidad de instrumentos | Integridad de los archivos | cap. 4: la nota se integra al texto |
| [991] | Restricciones metodológicas | El sistema no permite el ingreso de un instrumento previamente procesado. En el momento de la ingesta, el sistema calcula un hash MD5 del contenido del archivo y la compara contra los registros existentes. Si detecta coincidencia, rechaza el archivo e informa … | Cada carga se registra como un instrumento con su propio identificador. El servicio de almacenamiento calcula una huella SHA-256 de cada archivo al guardarlo y la comprueba en cada descarga, de modo que el contenido guardado no puede cambiar sin que se detecte… | cap. 4: la nota se integra al texto |
| [992] | Restricciones metodológicas | Nota: en la versión entregada no se implementó el rechazo de archivos repetidos: cada carga se registra como un instrumento nuevo. La huella SHA-256 que guarda el almacenamiento comprueba que el archivo no cambie y queda como base para detectar duplicados en u… | (se quitó) | cap. 4: la nota se integra al texto |
| [1000] | Descripción de los módulos del sistema | La fase de limpieza aplica primero transformaciones deterministas | La fase de limpieza se basa en reglas, sin modelo de lenguaje (5.5.1): aplica primero transformaciones deterministas | cap. 4: la nota se integra al texto |
| [1000] | Descripción de los módulos del sistema | el sistema sugiere los KPIs relevantes a partir del catálogo; | el sistema sugiere los KPIs relevantes del catálogo por similitud semántica, con una justificación redactada por el modelo de lenguaje (5.5.4); | cap. 4: la nota se integra al texto |
| [1001] | Descripción de los módulos del sistema | Nota: después de las pruebas se optó por una limpieza basada en reglas, sin modelo de lenguaje, y por sugerir los KPIs por similitud semántica, con una justificación redactada por el modelo (5.5.1 y 5.5.4). | (se quitó) | cap. 4: la nota se integra al texto |
| [1003] | Descripción de los módulos del sistema | Construye los chunks a partir del JSON final | Construye los chunks con plantillas fijas, sin modelo de lenguaje, a partir del JSON final | cap. 4: la nota se integra al texto |
| [1003] | Descripción de los módulos del sistema | Los chunks se almacenan en ChromaDB con el tipo de instrumento en sus metadatos (4.7). | Los chunks se almacenan en una sola colección de ChromaDB, con el tipo de instrumento en sus metadatos (4.7 y 4.9). | cap. 4: la nota se integra al texto |
| [1004] | Descripción de los módulos del sistema | Nota: después de las pruebas se optó por construir los chunks con plantillas fijas, sin modelo de lenguaje, y por guardarlos en una sola colección; la estrategia de dos niveles se conserva (4.7 y 4.9). | (se quitó) | cap. 4: la nota se integra al texto |
| [1008] | Descripción de los módulos del sistema | Cada consulta y su respuesta se persisten | El cálculo complementa a la recuperación porque el modelo de lenguaje se equivoca al contar y, con solo unos cuantos fragmentos, no ve a todos los respondentes (5.7). Cada consulta y su respuesta se persisten | cap. 4: la nota se integra al texto |
| [1009] | Descripción de los módulos del sistema | Nota: después de las pruebas se optó por sumar un módulo de cálculo a la recuperación, porque el modelo se equivoca al contar y no ve a todos los respondentes en unos cuantos fragmentos (5.7). | (se quitó) | cap. 4: la nota se integra al texto |
| [1013] | Proceso de retiro de instrumentos | (Figura 3 del planteamiento inicial) | Figura 3 con el flujo de eliminación actual | cap. 4: la nota se integra al texto |
| [1015] | Proceso de retiro de instrumentos | La cascada de eliminación sigue un orden estricto justificado por integridad y consistencia entre componentes. Primero se desactivan lógicamente los chunks en documento_vectorizado mediante activo = false, garantizando que el módulo de consulta deje de conside… | La eliminación de un instrumento es completa y solo puede hacerla quien lo subió o un administrador. Primero se borra el registro del instrumento en PostgreSQL y, en cascada, todas las tablas que dependen de él. Después, el servicio de almacenamiento borra sus… | cap. 4: la nota se integra al texto |
| [1016] | Proceso de retiro de instrumentos | Nota: después de las pruebas se optó por una eliminación completa: se borra el registro del instrumento y, en cascada, todas sus tablas, y después el servicio de almacenamiento borra sus archivos, incluido el original, y sus vectores. Así no quedan datos de un… | (se quitó) | cap. 4: la nota se integra al texto |
| [1019] | Flujo de consulta | En el flujo de consulta en lenguaje natural el LLM recibe los chunks recuperados directamente como contexto sin realizar consultas adicionales a PostgreSQL ni a ninguna otra fuente, dado que cada chunk es semánticamente rico y contiene todos los metadatos, con… | En el flujo de consulta en lenguaje natural, el sistema revisa primero que la pregunta esté dentro del dominio de la plataforma. Después busca, por significado y por palabras, en una sola colección de ChromaDB que reúne los chunks de todos los tipos de instrum… | cap. 4: la nota se integra al texto |
| [1020] | Flujo de consulta | Nota: después de las pruebas se optó por buscar en una sola colección, por significado y por palabras, y por redactar con temperatura 0.2; además, el modelo primero convierte la pregunta en un plan que el sistema calcula. La Figura 4 conserva el flujo del dise… | (se quitó) | cap. 4: la nota se integra al texto |
| [1021] | Flujo de consulta | (Figura 4 del planteamiento inicial) | Figura 4 con el flujo de consulta actual | cap. 4: la nota se integra al texto |
| [1031] | Diseño del módulo de limpieza y estandarización: parte de li… | [Columnas con más del 50% de nulos · col 0] Columnas con más del 50% de nulos | Columnas con más del 40 % de nulos | cap. 4: la nota se integra al texto |
| [1033] | Diseño del módulo de limpieza y estandarización: parte de li… | Nota: después de las pruebas se ajustaron los umbrales (alerta desde 40 % de vacíos en una pregunta, encuestados con más de 50 % de vacíos, atípicos por ±4σ o IQR) y se agregaron casos como las respuestas en línea recta y los ítems invertidos (5.5.1). | En las encuestas, la limpieza marca para revisión las preguntas con más del 40 % de respuestas vacías, los encuestados que dejaron sin responder más de la mitad de las preguntas y los valores atípicos, a más de cuatro desviaciones estándar de la media o, si se… | cap. 4: la nota se integra al texto |
| [1053] | Limpieza encuestas | La Figura 5 representa el flujo de limpieza para encuestas. | La Figura 5 representa el flujo de limpieza para encuestas. El CSV limpio se guarda en el servicio de almacenamiento, y las métricas y decisiones de la Tabla 31 se guardan en la base de datos como el reporte de una versión de la limpieza (5.5.1). | cap. 4: la nota se integra al texto |
| [1054] | Limpieza encuestas | Nota: en la implementación, el CSV limpio se guarda en el servicio de almacenamiento y las métricas y decisiones se guardan como el reporte de una versión de la limpieza (5.5.1). | (se quitó) | cap. 4: la nota se integra al texto |
| [1058] | Limpieza entrevistas | En este módulo de limpieza de entrevistas se admiten distintos formatos como lo son (.docx, .txt, .pdf), primero saber que es importante tomar en cuenta que debe tener una estructura donde se reconozca a los hablantes para que de esta manera se identifiquen fá… | El módulo de limpieza de entrevistas admite los formatos .docx, .txt y .pdf. La transcripción debe tener una estructura en la que se reconozca a los hablantes, para identificar con facilidad a las personas entrevistadas y a quien entrevista. Con esa estructura… | tono impersonal |
| [1061] | Limpieza entrevistas | En esta figura podemos ver cómo es el proceso de limpieza de las entrevistas, donde se debe recordar los 3 formatos aceptados, esta limpieza es básica y es únicamente para eliminar posible ruido y reconstruir palabras que puedan afectar después a los siguiente… | La figura muestra el proceso de limpieza de las entrevistas para los tres formatos aceptados. Es una limpieza básica: elimina el ruido y reconstruye las palabras que podrían afectar a los módulos siguientes. | tono impersonal |
| [1061] | Limpieza entrevistas | que podrían afectar a los módulos siguientes. | que podrían afectar a los módulos siguientes. Reconoce transcripciones con y sin etiquetas de hablante y pide al investigador confirmar el rol de cada hablante (5.3.3). | cap. 4: la nota se integra al texto |
| [1062] | Limpieza entrevistas | Nota: después de las pruebas, la limpieza de entrevistas también reconoce transcripciones con y sin etiquetas de hablante, y pide confirmar el rol de cada hablante (5.3.3). | (se quitó) | cap. 4: la nota se integra al texto |
| [1066] | Limpieza pruebas estandarizadas | no muestran sesgos y no son influenciados por la asesoría del docente | se consideran menos influidas por el criterio del docente | afirmación absoluta sin cita |
| [1074] | Limpieza pruebas estandarizadas | columas | columnas | errata |
| [1077] | Limpieza pruebas estandarizadas | Tabla 30 | Tabla 32 | la tabla de los pasos es la 32 |
| [1077] | Limpieza pruebas estandarizadas | [Entrada · col 1] Registro_prueba.csvRespuestas.csv | Registro_prueba.csv | cap. 4: la nota se integra al texto |
| [1077] | Limpieza pruebas estandarizadas | [Entrada · col 2] Registro_prueba.csv: Contiene los registros de las preguntas contestadas por los alumnos Respuestas.csv: Contiene las respuestas correctas a la prueba estandarizada | Registro_prueba.csv: contiene la respuesta de cada alumno a cada reactivo. La prueba no se califica, por lo que no se pide una clave de respuestas correctas. | cap. 4: la nota se integra al texto |
| [1077] | Limpieza pruebas estandarizadas | [Salida · col 1] Respuestas_limpias.parquetauditoria.json | CSV limpio y reporte de limpieza | cap. 4: la nota se integra al texto |
| [1077] | Limpieza pruebas estandarizadas | [Salida · col 2] Respuestas_limpias.parquet: Contiene las respuestas procesadas por todos los pasos descritos en la Tabla 32auditoria.json: Contiene el conteo de los tipos de datos encontrados en el archivo procesado como las filas que contiene, repuestas nula… | CSV limpio: respuestas procesadas por los pasos de la Tabla 32. Reporte de limpieza: filas, respuestas nulas, no respondidas y duplicadas, junto con las decisiones del investigador; se guarda como una versión de la limpieza (5.5.1). | cap. 4: la nota se integra al texto |
| [1078] | Limpieza pruebas estandarizadas | Nota: después de las pruebas se optó por no calificar las pruebas, se describe qué opción eligió cada alumno y cómo se repartieron las respuestas de cada reactivo (5.3.4 y 5.5.1). | La prueba no se califica: el sistema describe qué opción eligió cada alumno y cómo se repartieron las respuestas de cada reactivo (5.3.4 y 5.5.1). | cap. 4: la nota se integra al texto |
| [1085] | Diseño del módulo de limpieza y estandarización: parte estan… | , gracias a la intervención del LLM este va recomendando metadatos posibles para cada instrumento y es decisión del investigador aceptarlos o no, excepto los obligatorios. | . El sistema propone estos metadatos con reglas aplicadas sobre la limpieza confirmada y, cuando está activo, el modelo de lenguaje completa los campos interpretativos; el investigador decide si acepta cada propuesta, salvo en los metadatos obligatorios, que s… | cap. 4: la nota se integra al texto |
| [1086] | Diseño del módulo de limpieza y estandarización: parte estan… | Los quince elementos se adaptan al contexto | De los quince elementos, el sistema usa trece, adaptados al contexto | cap. 4: la nota se integra al texto |
| [1087] | Diseño del módulo de limpieza y estandarización: parte estan… | Nota: en la implementación, la propuesta de metadatos se hace con reglas sobre la limpieza confirmada y, cuando está activo, el modelo completa los campos interpretativos; de los quince elementos de Dublin Core se usan 13 (5.5.2). | (se quitó) | cap. 4: la nota se integra al texto |
| [1095] | Asignación de KPIs | La Figura 7 ilustra | La Figura 8 ilustra | el flujo de KPIs es la Figura 8 |
| [1099] | Estandarización de encuestas | El proceso lo conduce el LLM en sesión con el investigador, quien confirma o corrige cada campo inferido antes de continuar. | El tipo de cada pregunta lo infieren reglas a partir de la limpieza (5.3.2) y el modelo de lenguaje solo apoya en los campos interpretativos; el investigador confirma o corrige cada campo propuesto antes de continuar. | cap. 4: la nota se integra al texto |
| [1100] | Estandarización de encuestas | Nota: en la implementación, el tipo de cada pregunta lo infieren reglas de la limpieza (5.3.2) y el modelo de lenguaje solo apoya en los campos interpretativos; el investigador confirma cada campo propuesto, como se describe en esta sección. | (se quitó) | cap. 4: la nota se integra al texto |
| [1105] | Estandarización de encuestas | Metadatos obligatorios | Metadatos obligatorios | errata (faltaba el espacio tras el número) |
| [1117] | Estandarización de encuestas | múlitple | múltiple | errata |
| [1135] | Estandarización de encuestas | Una vez verificado, el módulo genera dos archivos: | Una vez verificado, el módulo produce las dos salidas de la Tabla 39. El JSON estandarizado corresponde al JSON técnico y, después de asociar los KPIs, al JSON final (5.5.2 y 5.5.6); el archivo .sav se genera cuando se descarga la encuesta. | cap. 4: la nota se integra al texto |
| [1136] | Estandarización de encuestas | Nota: en la implementación, el JSON estandarizado corresponde al JSON técnico y, después de asociar los KPIs, al JSON final (5.5.2 y 5.5.6); el archivo .sav se genera al descargar la encuesta. | (se quitó) | cap. 4: la nota se integra al texto |
| [1143] | Estandarización de entrevistas | Tras la limpieza y normalización de texto de las entrevistas pasamos al módulo de estandarización donde vamos a operar de manera asistida pues vamos a designar metadatos para poder dar una mejor respuesta en los pasos posteriores de vectorización de texto. Es … | Tras la limpieza y la normalización del texto, la entrevista pasa al módulo de estandarización, que opera de forma asistida: se asignan metadatos que mejoran las respuestas en los pasos posteriores de vectorización. La Tabla 40 presenta los metadatos aplicable… | tono impersonal |
| [1147] | Estandarización de entrevistas | Para el caso de las entrevistas estos metadatos son los que fueron considerados, primeramente siguiendo la plantilla de acuerdo con la norma ISO 15836 y agregando algunos otros que se consideraron importantes para un buen enriquecimiento de las entrevistas. | Estos metadatos siguen la plantilla de la norma ISO 15836 y agregan otros que enriquecen la descripción de las entrevistas. | tono impersonal |
| [1148] | Estandarización de entrevistas | Ahora bien, podemos pasar al diseño del módulo de estandarización, donde la entrada es el texto limpio. Este diseño de la estandarización se muestra en la siguiente imagen y conlleva todos los pasos de este mismo módulo. Se pretende que con estos metadatos se … | El diseño del módulo de estandarización, cuya entrada es el texto limpio, se muestra en la Figura 10 con todos sus pasos; con estos metadatos se obtiene una salida lista para los módulos siguientes. | tono impersonal |
| [1148] | Estandarización de entrevistas | con estos metadatos se obtiene una salida lista para los módulos siguientes. | con estos metadatos se obtiene una salida lista para los módulos siguientes. Además, cada respuesta de la entrevista recibe un análisis de sus partes, su postura y sus temas, que el investigador puede revisar (5.5.7). | cap. 4: la nota se integra al texto |
| [1149] | Estandarización de entrevistas | Nota: en la implementación, cada respuesta de la entrevista recibe además un análisis de sus partes, su postura y sus temas, que el investigador puede revisar (5.5.7). | (se quitó) | cap. 4: la nota se integra al texto |
| [1155] | Estandarización de pruebas estandarizadas | -fsistema | sistema | errata |
| [1155] | Estandarización de pruebas estandarizadas | Para posteriormente ser vectorizado y entrar al sistema de recuperación. | Para posteriormente ser vectorizado y entrar al sistema de recuperación. Los metadatos de la Tabla 41 se capturan en el paso «Metadatos del tipo» del asistente, y la prueba no se califica (5.5.2). | cap. 4: la nota se integra al texto |
| [1156] | Estandarización de pruebas estandarizadas | Nota: en la implementación, los metadatos de la Tabla 41 se capturan en el paso «Metadatos del tipo» del asistente y la prueba no se califica (5.5.2). | (se quitó) | cap. 4: la nota se integra al texto |
| [1166] | Diseño del módulo de vectorización | Nota: esta sección describe el diseño tal como quedó después de las pruebas en el ambiente de desarrollo. Se optó por construir los chunks con plantillas fijas a partir del JSON final, en lugar de generarlos con el modelo; la estrategia de dos niveles y la ide… | (se quitó) | cap. 4: la nota se integra al texto |
| [1178] | Estrategia de construcción de chunks | Los chunks de una persona solo se buscan cuando la consulta la nombra; los intercambios de entrevista, siempre | En la búsqueda por significado, los chunks de una persona solo se buscan cuando la consulta la nombra; en la búsqueda por palabras entran como máximo dos por instrumento; los intercambios de entrevista, siempre | código local: services/visualization-service/services/hibrida.py:109 (_MAX_POR_PERSONA = 2) |
| [1185] | Metadatos y trazabilidad de cada chunk | Dejar fuera los chunks de personas cuando la consulta no nombra a nadie | Dejar fuera de la búsqueda por significado los chunks de personas cuando la consulta no nombra a nadie | hibrida.py:109 |
| [1192] | Diseño de la base de datos relacional | Nota: después de las pruebas se optó por un esquema con tablas para las versiones de la limpieza y del conocimiento y para la evaluación del chat; el principio de registrar la operación sin duplicar el contenido del instrumento se mantiene. | (se quitó) | cap. 4: la nota se integra al texto |
| [1204] | Diseño de la base de datos vectorial | ChromaDB guarda los vectores que permiten buscar por significado. | ChromaDB guarda los vectores que permiten buscar por significado: una sola colección reúne los chunks de todos los instrumentos, con el tipo de instrumento en sus metadatos, y otra guarda el catálogo de KPIs. | cap. 4: la nota se integra al texto |
| [1205] | Diseño de la base de datos vectorial | Nota: después de las pruebas se optó por una sola colección para los instrumentos, con el tipo en sus metadatos, y por sumar una búsqueda por palabras; la búsqueda por similitud coseno sigue siendo la base. | (se quitó) | cap. 4: la nota se integra al texto |
| [1213] | Proceso de inserción y límites operativos | ChromaDB indexa los vectores con HNSW, | ChromaDB indexa los vectores con HNSW [cita: N_MALKOV], | fuente de la técnica |
| [1220] | Decisiones de diseño | La Tabla 48 resume las decisiones de diseño del sistema construido. | La Tabla 48 resume las decisiones de diseño del sistema construido. Las relativas a la construcción de chunks, las colecciones, la gestión de las instrucciones del modelo y la asociación de KPIs se definieron a partir de las pruebas en el ambiente de desarroll… | cap. 4: la nota se integra al texto |
| [1221] | Decisiones de diseño | Nota: las decisiones que cambiaron respecto al planteamiento inicial (construcción de chunks, colecciones, gestión de las instrucciones del modelo y asociación de KPIs) se ajustaron después de las pruebas en el ambiente de desarrollo, sin cambiar el objetivo d… | (se quitó) | cap. 4: la nota se integra al texto |
| [1223] | Decisiones de diseño | [DA-18 · col 2] Indicadores sin modelo, juez bajo demanda y calificación humana | Indicadores sin modelo en «Ver métricas»; las métricas de RAGAS, con un juez externo por API (Claude Fable 5.2), para experimentación | el panel del juez ya no está en el chat; juez externo de RAGAS (origin/PArturo: juez_fable.py) |
| [1226] | Diagrama de casos de uso | dar de alta usuarios y eliminar cualquier instrumento (Figura 16). | dar de alta usuarios y eliminar cualquier instrumento (Figura 16). No hay casos de uso para editar las instrucciones del modelo ni un panel de monitoreo: la calidad de las respuestas se revisa con las métricas que el chat muestra en cada respuesta y con la eva… | cap. 4: la nota se integra al texto |
| [1227] | Diagrama de casos de uso | se sustituyeron por la evaluación de cada respuesta del chat y por la configuración del servidor | se sustituyeron por los indicadores de cada respuesta del chat, la evaluación con métricas de RAGAS y la configuración del servidor | evaluación real |
| [1227] | Diagrama de casos de uso | Nota: los casos de uso se ajustaron al asistente de siete pasos construido; la gestión de prompts y el panel de monitoreo del planteamiento inicial se sustituyeron por los indicadores de cada respuesta del chat, la evaluación con métricas de RAGAS y la configu… | (se quitó) | cap. 4: la nota se integra al texto |
| [1248] | Descripción de los casos de uso | CU-08: Consultar en lenguaje natural y evaluar la respuesta | CU-08: Consultar en lenguaje natural | el panel de evaluación ya no está en el chat |
| [1249] | Descripción de los casos de uso | [Nombre · col 1] Consultar en lenguaje natural y evaluar la respuesta | Consultar en lenguaje natural | el panel de evaluación ya no está en el chat |
| [1249] | Descripción de los casos de uso | [Resumen · col 1] El investigador hace una pregunta sobre los instrumentos de su alcance y recibe una respuesta con sus fuentes, que puede evaluar. | El investigador hace una pregunta sobre los instrumentos de su alcance y recibe una respuesta con sus fuentes. | el panel de evaluación ya no está en el chat |
| [1249] | Descripción de los casos de uso | 5. El sistema muestra la respuesta con sus fuentes, «Ver datos», «Cómo lo calculé» y «Ver métricas». 6. El investigador puede pedir la evaluación del juez y calificar la respuesta (bien, parcial o mal). | 5. El sistema muestra la respuesta con sus fuentes, «Ver datos», «Cómo lo calculé» y «Ver métricas». 6. «Ver métricas» muestra los indicadores de la respuesta: cómo se recuperó cada fragmento, cuántas cifras tienen respaldo y cuánto tardó cada paso. | PanelMetricas.tsx y CalificacionHumana.tsx no se importan; BurbujaMensaje.tsx:15 usa VerMetricas |
| [1249] | Descripción de los casos de uso | ; la evaluación y la calificación, en sus tablas. | . | el panel de evaluación ya no está en el chat |
| [1291] | Patrón de enrutamiento API Gateaway | Gateaway | Gateway | errata |
| [1292] | Patrón de enrutamiento API Gateaway | El API Gateway (puerto 8000) | El API Gateway (puerto 8000 dentro del contenedor; 8006 en el equipo) | docker-compose.yml: 8006 → 8000 |
| [1292] | Patrón de enrutamiento API Gateaway | organiza su lógica en dos módulos: app/auth/, con los endpoints de autenticación (/auth/login, /auth/me, /auth/register), y proxy/, con el reenvío de peticiones. | organiza su lógica en dos módulos: uno de autenticación, con los endpoints de inicio de sesión, consulta del usuario actual y alta de usuarios, y otro que reenvía las peticiones a cada servicio. | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [1297] | Patrón de enrutamiento API Gateaway | Gateaway | Gateway | errata |
| [1301] | Instrument-service | recibe el archivo respondido del instrumento, el instrumento original sin respuestas y, en las pruebas, la clave de respuestas. | recibe el archivo respondido del instrumento y, de forma opcional, el instrumento original sin respuestas. En las pruebas no acepta clave de respuestas: si se envía, la rechaza (400). | código local: services/instrument-service/app/routers/upload.py:47-48, 68-70 |
| [1302] | Instrument-service | Sube el archivo (respondido, original y clave opcionales). Rechaza con 422 los archivos que no cumplen el contrato: formato largo, sin fila de encabezados en código sin el original. | Sube el archivo respondido y, de forma opcional, el original. Rechaza con 422 los archivos que no cumplen el contrato (formato largo, sin fila de encabezados, encabezados en código sin el original) y con 400 una clave de respuestas. | upload.py:47-48 |
| [1302] | Instrument-service | administrados | administrador | errata |
| [1302] | Instrument-service | (nuevo) | Tabla (n) Endpoints de instrument-service | tabla sin pie |
| [1305] | Cleaning-service | Cada repetición es una nueva versión nueva | Cada repetición es una versión nueva | errata |
| [1306] | Cleaning-service | retormar | retomar | errata |
| [1306] | Cleaning-service | (nuevo) | Tabla (n) Endpoints de cleaning-service | tabla sin pie |
| [1323] | Knowledge-service | (puerto 8009) Construye | (puerto 8009) construye | errata |
| [1364] | Visualization-service | (X.9 y X.10) | (5.8.1 y 5.7.5) | referencia vacía |
| [1367] | Visualization-service | Métricas automáticas de una respuesta: fidelidad, relevancia y precisión del contexto | Métricas de una respuesta: los indicadores sin modelo y las métricas de RAGAS de cada juez | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [1367] | Visualization-service | (fila nueva) | POST \| /consultas/{consulta_id}/metricas \| Calcular las métricas de RAGAS de una respuesta con el juez indicado, incluido el juez externo externo por API (experimentación) | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [1390] | Comunicación entre servicios | (nuevo) | Tabla (n) Prefijos que el API Gateway reenvía a cada servicio | tabla sin pie |
| [1392] | Comunicación entre servicios | Guardar el archivo crudo, la clave y el original al subir un instrumento. | Guardar el archivo respondido y el original al subir un instrumento. | sin clave (upload.py) |
| [1392] | Comunicación entre servicios | Descargar el crudo (y la clave) para limpiarlo. | Descargar el archivo respondido para limpiarlo. | sin clave (upload.py) |
| [1392] | Comunicación entre servicios | (nuevo) | Tabla (n) Llamadas HTTP de cada servicio a storage-service | tabla sin pie |
| [1392] | Comunicación entre servicios | Con STORAGE_BACKEND=local | En el modo de almacenamiento local | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [1395] | Comunicación entre servicios | (nuevo) | Tabla (n) Comunicación de los servicios a través de la base de datos relacional | tabla sin pie |
| [1397] | Comunicación entre servicios | (nuevo) | Tabla (n) Comunicación de los servicios a través de ChromaDB | tabla sin pie |
| [1397] | Comunicación entre servicios | analysis (scripts/seed_kpis.py) | analysis (script de carga del catálogo) | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [1400] | Especificaciones de los instrumentos aceptados | (nuevo) | Ideal: se procesa sin avisos. | lista anunciada que faltaba (contrato de formatos, documentación/02_Desarrollo.md:639-643) |
| [1400] | Especificaciones de los instrumentos aceptados | (nuevo) | Aceptado con aviso: se procesa, y la limpieza o el perfil muestran un aviso o una decisión para el investigador. | lista anunciada que faltaba (contrato de formatos, documentación/02_Desarrollo.md:639-643) |
| [1400] | Especificaciones de los instrumentos aceptados | (nuevo) | Rechazado: se detiene con el motivo y lo que hay que hacer. | lista anunciada que faltaba (contrato de formatos, documentación/02_Desarrollo.md:639-643) |
| [1426] | Entrevista | acetados | aceptados | errata |
| [1427] | Entrevista | (x.7.8) | (5.5.7) | referencia vacía |
| [1440] | Prueba estandarizada | Verdadero/false | Verdadero/falso | errata |
| [1443] | Prueba estandarizada | Columnas faltantes respecto a la clave → error. | Hoja sin delimitador reconocido (coma o punto y coma) → error. | las pruebas no tienen clave; regla real en services/cleaning-service/services/motores/pruebas/motor.py:85 |
| [1454] | La razón de utilizar datos sintéticos | cuando una institución las aporte. | cuando una institución las aporte. Cinco de las encuestas retoman las preguntas de instrumentos publicados, como el MSLQ-SF; las demás encuestas, las pruebas y las entrevistas se construyeron para este trabajo. El Anexo D incluye un instrumento de cada tipo. | origen de los datos: instrumentos sintéticos, sin datos públicos de respuestas |
| [1466] | Generación por tipo de instrumento | # tools/data_synthesis/generators/base_generator.py, generate_correlated_block() | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1467] | Generación por tipo de instrumento | L = np.linalg.cholesky(corr_matrix) # relación entre los ítems de la | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1468] | Generación por tipo de instrumento | dimensión | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1469] | Generación por tipo de instrumento | Z = self.rng.standard_normal((n_respondents, n_items)) | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1470] | Generación por tipo de instrumento | raw = (Z @ L.T) * lk["desviacion_estimada"] + lk["media_estimada"] # lk: parámetros | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1471] | Generación por tipo de instrumento | Likert del perfil | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1472] | Generación por tipo de instrumento | responses = np.clip(np.round(raw), 1, 5).astype(int) | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1472] | Generación por tipo de instrumento | (nuevo) | # Generador base: bloque de ítems Likert relacionados entre sí | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1472] | Generación por tipo de instrumento | (nuevo) | # Relación entre los ítems de la dimensión: | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1472] | Generación por tipo de instrumento | (nuevo) | L = np.linalg.cholesky(corr_matrix) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1472] | Generación por tipo de instrumento | (nuevo) | lk = profile["likert"] # parámetros Likert del perfil | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1472] | Generación por tipo de instrumento | (nuevo) | Z = self.rng.standard_normal((n_respondents, n_items)) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1472] | Generación por tipo de instrumento | (nuevo) | raw = (Z @ L.T) * lk["desviacion_estimada"] + lk["media_estimada"] | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1472] | Generación por tipo de instrumento | (nuevo) | responses = np.clip(np.round(raw), 1, 5).astype(int) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1474] | Generación por tipo de instrumento | "¿Has reprobado alguna materia en el último año?": {"factores": {"promedio_gpa": -0.6, | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1475] | Generación por tipo de instrumento | "horas_trabajo_semana": 0.3}, "prob_si": 0.3}, | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1476] | Generación por tipo de instrumento | "¿Cuentas con una beca?": {"variable": "tiene_beca", "mapa": {"True": "Sí", "*": {"Sí": | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1477] | Generación por tipo de instrumento | 0.1, "No": 0.9}}} | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1478] | Generación por tipo de instrumento |  | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1479] | Generación por tipo de instrumento | # tools/data_synthesis/generators/coherencia.py, tendencia() | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1480] | Generación por tipo de instrumento | for nombre, peso in pesos.items(): | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1481] | Generación por tipo de instrumento | suma += peso * factores(nombre) # p. ej., promedio (−0.6) y horas | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1482] | Generación por tipo de instrumento | de trabajo (+0.3) | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1483] | Generación por tipo de instrumento | return _estandarizar(suma + np.sqrt(1 - explicado) * rng.standard_normal(n)) # más | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1484] | Generación por tipo de instrumento | una parte al azar | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1484] | Generación por tipo de instrumento | (nuevo) | # Configuración de coherencia de las encuestas | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | "¿Has reprobado alguna materia en el último año?": { | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | "factores": {"promedio_gpa": -0.6, "horas_trabajo_semana": 0.3}, | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | "prob_si": 0.3}, | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | "¿Cuentas con una beca?": { | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | "variable": "tiene_beca", | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | "mapa": {"True": "Sí", "*": {"Sí": 0.1, "No": 0.9}}}, | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) |  | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | # Tendencia de una persona a partir de sus datos de contexto | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | # p. ej., promedio (−0.6) y horas de trabajo (+0.3), más una parte al azar: | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | for nombre, peso in (pesos or {}).items(): | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | suma += float(peso) * factores(nombre) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1484] | Generación por tipo de instrumento | (nuevo) | return _estandarizar(suma + np.sqrt(1 - explicado) * rng.standard_normal(n)) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1486] | Generación por tipo de instrumento | # tools/data_synthesis/generators/prueba_generator.py, _pesos_reactivo() | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1487] | Generación por tipo de instrumento | if tipo == "opcion_multiple": | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1488] | Generación por tipo de instrumento | return self.rng.dirichlet(np.ones(len(item["opciones"])) * 1.5) # pesos distintos | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1489] | Generación por tipo de instrumento | por reactivo | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1490] | Generación por tipo de instrumento | if tipo in ("verdadero_falso", "si_no"): | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1491] | Generación por tipo de instrumento | p = float(self.rng.uniform(0.25, 0.75)); return np.array([p, 1 - p]) | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1492] | Generación por tipo de instrumento | # _generate_one(): row[col] = self.rng.choice(letras, p=w) | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1492] | Generación por tipo de instrumento | (nuevo) | # Generador de pruebas: pesos de las opciones de cada reactivo | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) | # Pesos distintos por reactivo: | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) | if tipo == "opcion_multiple": | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) | return self.rng.dirichlet(np.ones(len(item["opciones"])) * 1.5) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) | if tipo in ("verdadero_falso", "si_no"): | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) | p = float(self.rng.uniform(0.25, 0.75)) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) | return np.array([p, 1 - p]) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) |  | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) | # Elección de cada alumno con esos pesos: | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1492] | Generación por tipo de instrumento | (nuevo) | row[col] = self.rng.choice(letras, p=w) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1494] | Generación por tipo de instrumento | # tools/data_synthesis/generators/entrevista_generator.py | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1495] | Generación por tipo de instrumento | "ent_01": {"perfiles_objetivo": ["P2", "P3", "P4", "P8"], "n_respondentes": 40, ...} | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1496] | Generación por tipo de instrumento | base = random.choice(all_templates) # plantillas del perfil | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1497] | Generación por tipo de instrumento | extension = random.choice(expansions[pid]) # p. ej., P4: «El tiempo es mi | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1498] | Generación por tipo de instrumento | recurso más escaso…» | (se quitó) | bloque de código con líneas cortadas a la mitad (se reescribe con el código real) |
| [1498] | Generación por tipo de instrumento | (nuevo) | # Generador de entrevistas: perfiles a los que se dirige y frases de cada perfil | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1498] | Generación por tipo de instrumento | (nuevo) | "ent_01": {"perfiles_objetivo": ["P2", "P3", "P4", "P8"], | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1498] | Generación por tipo de instrumento | (nuevo) | "n_respondentes": 40, ...} | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1498] | Generación por tipo de instrumento | (nuevo) | base = random.choice(all_templates) # plantillas del perfil | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1498] | Generación por tipo de instrumento | (nuevo) | # p. ej., P4: «El tiempo es mi recurso más escaso…» | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1498] | Generación por tipo de instrumento | (nuevo) | extension = random.choice(expansions.get(pid, expansions["P2"])) | código real: base_generator.py:110-127, coherencia_encuestas.json:67-68, coherencia.py:91-94, prueba_generator.py:701,771-777, entrevista_generator.py:24,510,566-567 |
| [1515] | Fase de limpieza | y la Tabla 84, qué esperar al comparar | y la Tabla 87, qué esperar al comparar | la tabla de antes y después es la 87 |
| [1517] | Fase de limpieza | (George y Mallery) | [cita: N_GEORGE] | cita autor-año pasada a IEEE |
| [1537] | Perfi semántico | Perfi semántico | Perfil semántico | errata |
| [1557] | Asociación de KPIs | (KPI_PESO_*, KPI_UMBRAL_EVIDENCIA, KPI_MAX_PROPUESTAS). | , por lo que pueden ajustarse sin modificar el código. | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [1698] | Qué se vectoriza de cada instrumento | La búsqueda las usa cuando la pregunta nombra a una persona. | La búsqueda por significado las usa cuando la pregunta nombra a una persona, y la búsqueda por palabras admite como máximo dos por instrumento. | hibrida.py:109 |
| [1719] | Modelo y medida de similitud | (Sentence-BERT; Reimers y Gurevych, 2019) | (Sentence-BERT) [cita: JXRISR86] | cita autor-año pasada a IEEE |
| [1719] | Modelo y medida de similitud | (Reimers y Gurevych, 2020) | [cita: N_REIMERS20] | cita autor-año pasada a IEEE |
| [1721] | Modelo y medida de similitud | **Ventana de 128 tokens. ** El modelo solo lee los primeros 128 tokens de cada texto (unos 450 caracteres en español) y descarta el resto sin aviso. Por eso todo lo que se vectoriza se mantiene corto: los KPIs miden 300 caracteres en promedio, cada unidad del … | **Ventana de 128 tokens.** El modelo solo lee los primeros 128 tokens de cada texto (unos 450 caracteres en español) y descarta el resto sin aviso. Por eso todo lo que se vectoriza se mantiene corto: los KPIs miden 300 caracteres en promedio, cada unidad del p… | asteriscos de Markdown sobrantes |
| [1731] | RAG | (Gao et al., 2023) | [cita: N_PAL] | cita autor-año pasada a IEEE |
| [1734] | RAG | (12 intenciones) | (13 intenciones) | esquemas/plan_consulta.json:135 (13 valores) |
| [1734] | RAG | con las 21 reglas del prompt | con las reglas del prompt que aplican a ese mensaje | prompt.sistema_para, RAG_PROMPT_MODULAR = True (config.py:159) |
| [1734] | RAG | el juez evalúa cuando se pide y la persona investigadora califica | las métricas de RAGAS las calcula un juez externo por API, para experimentación | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [1734] | RAG | El juez, bajo demanda | Solo el juez externo | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [1745] | Fuente y estrategia de chunks | La búsqueda deja fuera los chunks de respondentes y alumnos cuando la consulta no trae un ID (R017, A001) | La búsqueda por significado deja fuera los chunks de respondentes y alumnos cuando la consulta no trae un ID (R017, A001), y la de palabras admite como máximo dos por instrumento | hibrida.py:109 |
| [1774] | Interpretación: el plan del modelo y las reglas que lo corri… | Una de 12: datos_respondente, filtrar_respondentes, conteo_porcentaje, comparar_grupos, hallazgo, resumen_pregunta, kpi, | Una de 13: datos_respondente, filtrar_respondentes, conteo_porcentaje, comparar_grupos, hallazgo, resumen_pregunta, ranking_preguntas, kpi, | plan_consulta.json:135 |
| [1776] | Interpretación: el plan del modelo y las reglas que lo corri… | (Rajkumar et al., 2022) | [cita: N_RAJKUMAR] | cita autor-año pasada a IEEE |
| [1776] | Interpretación: el plan del modelo y las reglas que lo corri… | (Gao et al., 2023) | [cita: N_PAL] | cita autor-año pasada a IEEE |
| [1777] | Interpretación: el plan del modelo y las reglas que lo corri… | (catalogo.py) |  | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [1792] | Interpretación: el plan del modelo y las reglas que lo corri… | las 12 intenciones | las 13 intenciones | plan_consulta.json:135 |
| [1887] | Interpretación: el plan del modelo y las reglas que lo corri… | (plan_consulta.py) |  | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [1888] | Interpretación: el plan del modelo y las reglas que lo corri… | (anclaje.py) |  | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [1889] | Interpretación: el plan del modelo y las reglas que lo corri… | (seguimiento.py) |  | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [1901] | Recuperación: RAG primero | ordenada con BM25) | ordenada con BM25 [cita: N_ROBERTSON]) | fuente de la técnica |
| [1901] | Recuperación: RAG primero | Reciprocal Rank Fusion (k = 60) | Reciprocal Rank Fusion [cita: N_CORMACK] (k = 60) | fuente de la técnica |
| [1903] | Cálculo determinista | (Gao et al., 2023) | [cita: N_PAL] | cita autor-año pasada a IEEE |
| [1917] | Cálculo determinista | (fila nueva) | ranking_preguntas \| Las preguntas o reactivos ordenados por el criterio pedido (más respuestas nulas o sin contestar, más coincidencia o respuestas más repartidas), con su medida | faltaba la intención ranking_preguntas |
| [1928] | Redacción y verificación | la conversación previa y una instrucción de formato | la conversación previa, la lista de las personas que aparecen en los datos (cuando las hay) y una instrucción de formato | prompt.construir: «PERSONAS EN LOS DATOS» (corrección del 12 nov) |
| [1981] | Dominio acotado | Prompt del sistema, con 21 reglas (5.8.3). | Prompt del sistema: de sus 21 reglas, solo las que aplican a cada mensaje (5.8.3). | RAG_PROMPT_MODULAR |
| [1989] | Reglas de fundamentación | Contiene 21 reglas: | Son 21 reglas, pero no se mandan todas en cada consulta: antes de llamar al modelo, el sistema revisa lo que trae el mensaje y deja solo las que aplican. Las de cifras van si hay un resultado calculado; las de entrevistas, si hay una entrevista; la de comparar… | prompt.reglas_para y config.py:159 |
| [2020] | Métricas del proceso | (Zheng et al., 2023) | [cita: N_ZHENG] | cita autor-año pasada a IEEE |
| [2020] | Métricas del proceso | (Es et al., 2024) | [cita: RMJ7ZTPK] | cita autor-año pasada a IEEE |
| [2022] | Métricas del proceso | Las métricas del panel se ven debajo de cada respuesta del chat; las demás se calculan con scripts fuera de línea. | Los indicadores sin modelo se ven en «Ver métricas», debajo de cada respuesta del chat; las métricas del juez y la calificación humana se calculan fuera de línea. | BurbujaMensaje.tsx:15 (VerMetricas) |
| [2026] | Métricas del proceso | Tres decisiones | Cuatro decisiones | se agregó el juez externo a la lista |
| [2028] | Métricas del proceso | El juez y el modelo que redacta no caben juntos en la GPU; por eso la evaluación se calcula cuando se pulsa «Calcular evaluación» y no después de cada respuesta. | El juez local y el modelo que redacta no caben juntos en la GPU; por eso el juez local se corre fuera de línea, en un proceso aparte, y no después de cada respuesta. | el panel «Calcular evaluación» ya no está en el chat |
| [2028] | Métricas del proceso | Bajo demanda. | Fuera de línea. | el juez local ya no se pide desde el chat |
| [2029] | Métricas del proceso | (nuevo) | Juez externo para experimentación. Para obtener las métricas de RAGAS sin ocupar la GPU en la que corre el modelo local, se optó por un juez externo, el modelo Claude Fable 5.2, al que el servicio de visualización consulta mediante la API de Anthropic. El juez… | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [2033] | Dockerización | La definición de la infraestructura se concentró en el directorio infrastructure/, que agrupa los Dockerfiles de cada servicio (en infrastructure/docker/) y los scripts de la base de datos (infrastructure/postgres/). En la raíz del repositorio se ubican el arc… | La definición de la infraestructura se concentró en una carpeta que agrupa los Dockerfiles de cada servicio y los scripts de la base de datos. Junto a ella se encuentran el archivo de orquestación de Docker Compose, la plantilla de variables de entorno y el ar… | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2036] | Dockerización | (nuevo) | Figura (n) Dockerfiles de cada servicio y archivo de orquestación | figura sin pie |
| [2038] | Construcción de imágenes mediante multi-stage builds | declaradas en el archivo requirements.txt | declaradas en su archivo de requerimientos | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2045] | Orquestación con Docker compose | El archivo docker-compose.yml, ubicado en la raíz del repositorio, orquesta | El archivo de Docker Compose orquesta | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2052] | Orquestación con Docker compose | Cada contenedor publica su puerto interno en el mismo puerto del host, siguiendo el mapa de puertos del sistema: | Cada contenedor publica su puerto interno en el mismo puerto del host, salvo api-gateway (8006 → 8000), chromadb (8008 → 8000) y chroma-viewer (8085 → 8000), según el mapa de puertos del sistema: | contradicción con la Tabla 108; docker-compose.yml |
| [2071] | Modelo de usuarios y roles | (05_seed_usuarios.sql) |  | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2079] | Contraseñas: cifrado con bcrypt | (nuevo) | Figura (n) Funciones de cifrado y verificación de contraseñas con passlib | figura sin pie |
| [2082] | El token JWT: emisión, contenido y validación | (SECRET_KEY) |  | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2084] | El token JWT: emisión, contenido y validación | la misma SECRET_KEY compartida | la misma clave secreta | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2084] | El token JWT: emisión, contenido y validación | La SECRET_KEY se inyecta | La clave secreta se inyecta | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2085] | El token JWT: emisión, contenido y validación | están centralizadas en el módulo shared/auth/, de modo que todos los servicios comparten exactamente la misma lógica. | están centralizadas en un módulo común, de modo que todos los servicios usan la misma lógica. | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2121] | 6.2. Entorno de pruebas | [Modelos · col 1] Para convertir texto en vectores: paraphrase-multilingual-mpnet-base-v2 (768 dimensiones). Modelo de lenguaje del chat: gemma3:4b; modelo juez de las métricas: qwen3:4b-instruct; ambos en Ollama 0.32.9. En la comparación de modelos (6.8) se u… | Para convertir texto en vectores: paraphrase-multilingual-mpnet-base-v2 (768 dimensiones). Modelo de lenguaje del chat: llama3.2:3b; las pruebas marcadas como «prueba final en pruebas» de 6.7 se corrieron con gemma3:4b. Juez local de las métricas: qwen3:4b-ins… | modelo del chat de la versión final (config.py:36, .env:25) |
| [2125] | 6.3. Datos de prueba | Los datos vienen de tres fuentes: | Los datos vienen de dos fuentes: | solo se enumeran dos |
| [2139] | 6.4. Estrategia de pruebas | Criterio común. Toda prueba tiene un resultado correcto | Todas las pruebas siguen un mismo criterio: cada una tiene un resultado correcto | redacción de tesis: sin encabezados de plantilla |
| [2153] | 6.4.1. Métricas | Las Tablas 113-122 dice qué mide | Las Tablas 113 a 118 dicen qué mide | las tablas de métricas son 113–118 |
| [2176] | 6.4.1. Métricas | [Tiempo · col 4] 6.11 | 6.10 | la sección 6.11 no existe |
| [2181] | 6.4.2. Configuración de los modelos | [Interpretar la pregunta (plan) · col 1] gemma3:4b o llama3.2:3b | llama3.2:3b (gemma3:4b en las pruebas que lo indican) | modelo de la versión final |
| [2181] | 6.4.2. Configuración de los modelos | [Redactar la respuesta · col 1] gemma3:4b o llama3.2:3b | llama3.2:3b (gemma3:4b en las pruebas que lo indican) | modelo de la versión final |
| [2181] | 6.4.2. Configuración de los modelos | [Clasificar preguntas dudosas · col 1] Gemma3:4b o llama3.2:3b | llama3.2:3b (gemma3:4b en las pruebas que lo indican) | modelo de la versión final |
| [2181] | 6.4.2. Configuración de los modelos | [Extraer la condición de un filtro · col 1] Gemma3:4b o llama3.2:3b | llama3.2:3b (gemma3:4b en las pruebas que lo indican) | modelo de la versión final |
| [2181] | 6.4.2. Configuración de los modelos | (fila nueva) | Juez externo de RAGAS \| Claude Fable 5.2 (API de Anthropic) \| Esfuerzo alto, salida con estructura fija y doce fragmentos adicionales de ChromaDB para redactar la respuesta de referencia \| No ocupa la GPU local; se usa para experimentación con los datos sin… | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [2181] | 6.4.2. Configuración de los modelos | [Juez de las métricas · col 0] Juez de las métricas | Juez local de las métricas | se distingue del juez externo |
| [2183] | 6.4.2. Configuración de los modelos | (config/*.yaml de cada servicio y la configuración compartida) |  | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2185] | 6.4.2. Configuración de los modelos | Entre 0.35 y 0.50 | Entre 0.55 y 0.50: vacía con este umbral | config.py:117 (RAG_ZONA_GRIS_MAX = 0.50) |
| [2185] | 6.4.2. Configuración de los modelos | Un clasificador decide si se responde | El clasificador no interviene | zona vacía con el umbral 0.55 |
| [2185] | 6.4.2. Configuración de los modelos | 0.35 | 0.55, o al menos 75 % de las palabras de la pregunta (búsqueda híbrida) | config.py:111 (RAG_MIN_SCORE = 0.55) y :128 (RAG_MIN_COBERTURA = 0.75) |
| [2190] | 6.5.1. Recorrido completo por tipo de instrumento | Qué se probó. Que un instrumento | La primera prueba de punta a punta comprobó que un instrumento | redacción de tesis: sin encabezados de plantilla |
| [2192] | 6.5.1. Recorrido completo por tipo de instrumento | Los seis tipos: | Los siete tipos: | se enumeran siete |
| [2201] | 6.5.2. Encuesta sin errores frente a encuesta con errores me… | Qué se probó. Se usaron dos versiones | Para esta prueba se usaron dos versiones | redacción de tesis: sin encabezados de plantilla |
| [2206] | 6.5.2. Encuesta sin errores frente a encuesta con errores me… | Qué pasó. La Figura | La Figura | redacción de tesis: sin encabezados de plantilla |
| [2230] | 6.5.3. Errores metidos en los tres tipos de instrumento | Qué se probó. Lo mismo que en la sección anterior, ahora | Esta prueba repite la de la sección anterior, ahora | redacción de tesis: sin encabezados de plantilla |
| [2241] | 6.5.3. Errores metidos en los tres tipos de instrumento | Resultado. | Los resultados por tipo de instrumento fueron los siguientes: | redacción de tesis: sin encabezados de plantilla |
| [2248] | 6.5.4. Prueba sin errores frente a prueba con errores metido… | Qué se probó. Se usó la prueba pru_01 | Para las pruebas estandarizadas se usó pru_01 | redacción de tesis: sin encabezados de plantilla |
| [2252] | 6.5.4. Prueba sin errores frente a prueba con errores metido… | Qué pasó. En la primera prueba encontró | En la primera prueba, la limpieza encontró | redacción de tesis: sin encabezados de plantilla |
| [2262] | 6.5.5. Entrevista sin errores frente a entrevista con errore… | Qué se probó. Se usó la entrevista ent_02 | Para las entrevistas se usó ent_02 | redacción de tesis: sin encabezados de plantilla |
| [2266] | 6.5.5. Entrevista sin errores frente a entrevista con errore… | Qué pasó. Los 600 turnos | Después de la limpieza, los 600 turnos | redacción de tesis: sin encabezados de plantilla |
| [2278] | 6.5.6. Encuesta grande con errores de captura | Qué se probó. Qué hace la limpieza | Esta prueba revisó qué hace la limpieza | redacción de tesis: sin encabezados de plantilla |
| [2282] | 6.5.6. Encuesta grande con errores de captura | Resultado. En la primera prueba | En la primera prueba | redacción de tesis: sin encabezados de plantilla |
| [2285] | 6.6.1. Estructura del JSON final, privacidad y preguntas que… | Qué se probó. Que el JSON final | Esta prueba comprobó que el JSON final | redacción de tesis: sin encabezados de plantilla |
| [2307] | 6.6.2. Asociación de KPIs: un solo texto frente a pregunta p… | Qué se probó. Primero se intentó | Primero se intentó | redacción de tesis: sin encabezados de plantilla |
| [2311] | 6.6.2. Asociación de KPIs: un solo texto frente a pregunta p… | Resultado. | Al comparar los dos métodos se observó lo siguiente: | redacción de tesis: sin encabezados de plantilla |
| [2328] | 6.7.2. Cambios en la técnica del chat, versión por versión | la Tabla 132 da el resultado | la Tabla 136 da el resultado | el resultado por versión es la Tabla 136 |
| [2330] | 6.7.2. Cambios en la técnica del chat, versión por versión | (20 reglas) | (21 reglas, enviadas según el contenido del mensaje) | prompt._REGLAS = 21 |
| [2330] | 6.7.2. Cambios en la técnica del chat, versión por versión | sin los chunks de cada persona en la búsqueda | sin los chunks de cada persona en la búsqueda por significado (en la de palabras, hasta 2 por instrumento) | hibrida.py:109 |
| [2330] | 6.7.2. Cambios en la técnica del chat, versión por versión | Indicadores sin modelo, juez bajo demanda y calificación humana | Indicadores sin modelo en «Ver métricas», juez externo de RAGAS por API y calificación humana fuera de línea | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [2339] | 6.7.2. Cambios en la técnica del chat, versión por versión | (Tabla 115) | (Tabla 119) | los parámetros son la Tabla 119 |
| [2341] | 6.7.2. Cambios en la técnica del chat, versión por versión | cada una de las 12 intenciones | cada una de las 13 intenciones | plan_consulta.json:135 |
| [2345] | 6.7.2. Cambios en la técnica del chat, versión por versión | Por ejemplo, ante un tema que el instrumento no tiene, responder con patrones generales (intención «hallazgo») en lugar de decir que el tema no está contemplado; esta falla apareció en ENC-06 y ENC-13 (6.7.6) y sigue abierta (6.9). |  | se quita la mención (decisión D7) |
| [2354] | 6.7.2. Cambios en la técnica del chat, versión por versión | se agregó la opción RAG_EJEMPLOS_INTERPRETACION, que el sistema deja encendida | se agregó una opción de configuración, que el sistema deja encendida | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2357] | 6.7.2. Cambios en la técnica del chat, versión por versión | Resultado. | La comparación muestra cuánto dependen las respuestas de los ejemplos: | redacción de tesis: sin encabezados de plantilla |
| [2364] | 6.7.2. Cambios en la técnica del chat, versión por versión | Resultado. El cambio | El cambio | redacción de tesis: sin encabezados de plantilla |
| [2366] | 6.7.3. El modelo calcula frente al código calcula | (encontrados en Anexo C) |  | el Anexo C son las preguntas de 6.7.6, no estas 20 (decisión D6) |
| [2366] | 6.7.3. El modelo calcula frente al código calcula | Qué se probó. Si el modelo | Esta prueba buscó saber si el modelo | redacción de tesis: sin encabezados de plantilla |
| [2379] | 6.7.3. El modelo calcula frente al código calcula | Resultado. | Con las tres formas se obtuvo lo siguiente: | redacción de tesis: sin encabezados de plantilla |
| [2400] | 6.7.3. El modelo calcula frente al código calcula | Resultado. Con la versión | Con la versión | redacción de tesis: sin encabezados de plantilla |
| [2405] | 6.7.3. El modelo calcula frente al código calcula | (Tabla 132; | (Tabla 136; | el resultado por versión es la Tabla 136 |
| [2418] | 6.7.4. Chunks y recuperación | La búsqueda del chat deja fuera los chunks de cada respondente o alumno, salvo que la pregunta nombre a una persona (sección 5.6.2), porque lo de cada persona lo resuelve el cálculo; | La búsqueda por significado deja fuera los chunks de cada respondente o alumno, salvo que la pregunta nombre a una persona (sección 5.6.2), porque lo de cada persona lo resuelve el cálculo (en la búsqueda híbrida de 6.7.9, la de palabras admite como máximo dos… | hibrida.py:109 |
| [2426] | 6.7.4. Chunks y recuperación | Resultado. | Sobre el tamaño de los chunks se encontró lo siguiente: | redacción de tesis: sin encabezados de plantilla |
| [2435] | 6.7.5. Sin recuperación frente a RAG primero | Qué se probó. Cuántas respuestas | Esta prueba midió cuántas respuestas | redacción de tesis: sin encabezados de plantilla |
| [2442] | 6.7.5. Sin recuperación frente a RAG primero | Resultado. Sin recuperación | Sin recuperación | redacción de tesis: sin encabezados de plantilla |
| [2444] | 6.7.6. Evaluación final para pruebas: conjunto de evaluación… | (Tabla 150). | (Tabla 150). Las preguntas de los dos conjuntos están en el Anexo C. | las preguntas están en el Anexo C (D6) |
| [2444] | 6.7.6. Evaluación final para pruebas: conjunto de evaluación… | Qué se probó. El chat en su versión final | La evaluación final probó el chat en su versión final | redacción de tesis: sin encabezados de plantilla |
| [2448] | 6.7.6. Evaluación final para pruebas: conjunto de evaluación… | Cómo se corrió. Se hicieron | Se hicieron | redacción de tesis: sin encabezados de plantilla |
| [2454] | 6.7.6. Evaluación final para pruebas: conjunto de evaluación… | Resultado. | Las tres pruebas dieron estos resultados: | redacción de tesis: sin encabezados de plantilla |
| [2456] | 6.7.6. Evaluación final para pruebas: conjunto de evaluación… | (sección 6.9) |  | la sección citada ya no existe (decisión D7) |
| [2469] | 6.7.6. Evaluación final para pruebas: conjunto de evaluación… | Límites de esta evaluación. El conjunto | Esta evaluación tiene límites. El conjunto | redacción de tesis: sin encabezados de plantilla |
| [2470] | 6.7.6. Evaluación final para pruebas: conjunto de evaluación… | o cortesía. | o cortesía. Las preguntas del conjunto de control están en la última tabla del mismo anexo. | las preguntas del control también están en el Anexo C (D6) |
| [2472] | 6.7.7. Análisis de respuestas de entrevista | Qué se probó. Que el análisis | Esta prueba comprobó que el análisis | redacción de tesis: sin encabezados de plantilla |
| [2473] | 6.7.7. Análisis de respuestas de entrevista | Cómo se decidió si pasa. Deben coincidir | Para considerar que la prueba pasa, deben coincidir | redacción de tesis: sin encabezados de plantilla |
| [2482] | 6.7.7. Análisis de respuestas de entrevista | Resultado. El sistema coincide | El sistema coincide | redacción de tesis: sin encabezados de plantilla |
| [2484] | 6.7.8. Temas permitidos, privacidad e intentos de manipulaci… | Qué se probó. Que el chat | Esta prueba comprobó que el chat | redacción de tesis: sin encabezados de plantilla |
| [2488] | 6.7.8. Temas permitidos, privacidad e intentos de manipulaci… | Resultado. La decisión | La decisión | redacción de tesis: sin encabezados de plantilla |
| [2493] | 6.7.9. Versión final para resultados: agregando búsqueda híb… | porque el de la versión final (0.65) | porque el de la versión final de pruebas (0.65) | origin/PArturo config.py:109; la versión final usa 0.55 |
| [2493] | 6.7.9. Versión final para resultados: agregando búsqueda híb… | Qué se probó. La prueba responde | Esta prueba responde | redacción de tesis: sin encabezados de plantilla |
| [2494] | 6.7.9. Versión final para resultados: agregando búsqueda híb… | Cómo se corrió. Todo con llama3.2:3b | Todo se corrió con llama3.2:3b | redacción de tesis: sin encabezados de plantilla |
| [2501] | 6.7.9. Versión final para resultados: agregando búsqueda híb… | 0.65 (versión final) | 0.65 (versión final de pruebas) | la versión final usa 0.55 |
| [2503] | 6.7.9. Versión final para resultados: agregando búsqueda híb… | Version sin umbral definido | Versión sin umbral definido | errata |
| [2511] | 6.7.9. Versión final para resultados: agregando búsqueda híb… | [Control: cumplen (de 24) · col 1] 15 (6 parciales, 3 no) | No se corrió con llama3.2:3b | no existe esa corrida (decisión D5) |
| [2513] | 6.7.9. Versión final para resultados: agregando búsqueda híb… | Límites. El umbral se eligió | Hay que considerar que el umbral se eligió | redacción de tesis: sin encabezados de plantilla |
| [2519] | 6.8. Modelos de lenguaje | Qué se probó. Si otro modelo | Esta prueba buscó saber si otro modelo | redacción de tesis: sin encabezados de plantilla |
| [2534] | 6.8. Modelos de lenguaje | Resultado. | De la comparación se desprende lo siguiente: | redacción de tesis: sin encabezados de plantilla |
| [2535] | 6.8. Modelos de lenguaje | Redactor: gemma3:4b. | Redactor en esta comparación: gemma3:4b. | la versión final usa llama3.2:3b |
| [2535] | 6.8. Modelos de lenguaje | (sección 6.7.3). | (sección 6.7.3). Con el sistema completo, la prueba final de 6.8.1 llevó a elegir llama3.2:3b. | la versión final usa llama3.2:3b |
| [2536] | 6.8. Modelos de lenguaje | (nuevo) | Por eso, para obtener las métricas de RAGAS se optó por un juez externo por API (Claude Fable 5.2, 5.8.4), que no compite con el modelo local por la GPU. Se usa para experimentación; su acuerdo con la calificación humana no se midió en este capítulo. | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [2540] | 6.8.1. llama3.2:3b frente a gemma3:4b en la prueba final en … | El sistema empezó con llama3.2:3b y terminó con gemma3:4b. | El sistema empezó con llama3.2:3b y las pruebas intermedias se corrieron con gemma3:4b. | la versión final usa llama3.2:3b |
| [2540] | 6.8.1. llama3.2:3b frente a gemma3:4b en la prueba final en … | parámetros de la Tabla 115 | parámetros de la Tabla 119 | los parámetros son la Tabla 119 |
| [2540] | 6.8.1. llama3.2:3b frente a gemma3:4b en la prueba final en … | Qué se probó. El sistema empezó | El sistema empezó | redacción de tesis: sin encabezados de plantilla |
| [2547] | 6.8.1. llama3.2:3b frente a gemma3:4b en la prueba final en … | Resultado. | Al comparar los dos modelos se obtuvo lo siguiente: | redacción de tesis: sin encabezados de plantilla |
| [2554] | 6.8.1. llama3.2:3b frente a gemma3:4b en la prueba final en … | (nuevo) | Modelo de la versión final. Con una exactitud parecida y 2.5 veces menos tiempo por turno, la versión final usa llama3.2:3b en todas las etapas del chat; con él se corrieron las pruebas de la versión unida (6.7.9) y de 6.8.2 y 6.8.3. | conclusión sobre el modelo (llama3.2:3b) |
| [2556] | 6.8.2. Temperatura de la redacción | Qué se probó. La temperatura | La temperatura | redacción de tesis: sin encabezados de plantilla |
| [2557] | 6.8.2. Temperatura de la redacción | Cómo se corrió. Versión unida, llama3.2:3b, sin caché, temperaturas 0, 0.2 y 0.5. | La prueba se corrió con la versión unida y llama3.2:3b, sin caché, con temperaturas de 0, 0.2 y 0.5. | redacción de tesis: sin encabezados de plantilla |
| [2560] | 6.8.2. Temperatura de la redacción | Resultado. | Con cada temperatura se obtuvo lo siguiente: | redacción de tesis: sin encabezados de plantilla |
| [2566] | 6.8.3. Instrucción partida, con preguntas nuevas | la redacción lleva siempre las 21 reglas. | hasta esta prueba, la redacción llevaba siempre las 21 reglas. | RAG_PROMPT_MODULAR = True desde el 12 nov |
| [2566] | 6.8.3. Instrucción partida, con preguntas nuevas | y la versión final las deja apagadas. | . | la versión final adopta las reglas por contenido |
| [2566] | 6.8.3. Instrucción partida, con preguntas nuevas | (RAG_PROMPT_MODULAR y RAG_EJEMPLOS_MAX) |  | redacción de tesis: sin rutas, archivos de código ni variables de configuración |
| [2566] | 6.8.3. Instrucción partida, con preguntas nuevas | Qué se probó. La interpretación | La interpretación | redacción de tesis: sin encabezados de plantilla |
| [2566] | 6.8.3. Instrucción partida, con preguntas nuevas | (enrutar primero y especializar después; Schluntz y Zhang, 2024) | (enrutar primero y especializar después) [cita: N_SCHLUNTZ] | cita autor-año pasada a IEEE |
| [2566] | 6.8.3. Instrucción partida, con preguntas nuevas | (IFEval, Zhou et al., 2023) | (IFEval) [cita: N_IFEVAL] | cita autor-año pasada a IEEE |
| [2566] | 6.8.3. Instrucción partida, con preguntas nuevas | (Liu et al., 2022) | [cita: N_LIU] | cita autor-año pasada a IEEE |
| [2567] | 6.8.3. Instrucción partida, con preguntas nuevas | Cómo se corrió. Se escribieron | Para esta prueba se escribieron | redacción de tesis: sin encabezados de plantilla |
| [2570] | 6.8.3. Instrucción partida, con preguntas nuevas | Resultado. | Las tres variantes dieron estos resultados: | redacción de tesis: sin encabezados de plantilla |
| [2576] | 6.8.3. Instrucción partida, con preguntas nuevas | quitar ejemplos a la interpretación los empeora. | quitar ejemplos a la interpretación los empeora. Por eso la versión final adopta las reglas por contenido y conserva todos los ejemplos; los resultados de las secciones anteriores se midieron con las 21 reglas. | config.py:158-159 |
| [2576] | 6.8.3. Instrucción partida, con preguntas nuevas | Qué se concluye. El tamaño | Se concluye que el tamaño | redacción de tesis: sin encabezados de plantilla |
| [2580] | 6.9. Demostración con métricas | [La búsqueda encuentra el fragmento correcto · col 2] 0.95 y 0.80 en el conjunto de evaluación; 1.00 y 0.93 en el control | Con la búsqueda híbrida de la versión final: 1.00 y 0.97 en el conjunto de evaluación y 1.00 y 0.94 en el control (solo por significado: 0.95 y 0.80) | valores de la versión final (Tabla 160) |
| [2580] | 6.9. Demostración con métricas | [La búsqueda encuentra el fragmento correcto · col 3] 6.7.4 | 6.7.4, 6.7.9 | valores de la versión final |
| [2580] | 6.9. Demostración con métricas | [Lo que responde está en los datos · col 2] 815 de 856 cifras con respaldo; 0 IDs inventados en 140 respuestas sobre instrumentos no vistos; 234 de 234 cifras con respaldo en las 30 preguntas nuevas | Versión final: 630 de 679 cifras con respaldo (92.8 %) y 234 de 234 en las 30 preguntas nuevas; 0 IDs inventados en 140 respuestas sobre instrumentos no vistos | valores de la versión final (Tablas 163 y 171) |
| [2580] | 6.9. Demostración con métricas | [Lo que responde está en los datos · col 3] 6.7.6, 6.8, 6.8.3 | 6.7.9, 6.8, 6.8.3 | valores de la versión final |
| [2580] | 6.9. Demostración con métricas | [La respuesta contiene lo que se pidió · col 2] Prueba final: 55 de 79 con gemma3:4b y 52 de 79 con llama3.2:3b; en la tercera prueba, con la instrucción recortada, 63 de 79 y 19 de 24 en el control; con 30 preguntas nuevas sobre instrumentos poco usados, 11 d… | Versión final: 48 de 79 y 15 de 24 en el control; con 30 preguntas nuevas sobre instrumentos poco usados, 11 de 30 (llama3.2:3b). Prueba final en pruebas: 55 de 79 con gemma3:4b y 52 de 79 con llama3.2:3b | valores de la versión final (Tablas 163 y 171) |
| [2580] | 6.9. Demostración con métricas | [La respuesta contiene lo que se pidió · col 3] 6.7.6, 6.8, 6.8.3 | 6.7.6, 6.7.9, 6.8, 6.8.3 | valores de la versión final |
| [2580] | 6.9. Demostración con métricas | [Se puede usar en el equipo disponible · col 2] De 2 min 34 s a 4 min 06 s por instrumento; respuesta del chat en la prueba final: mediana 43 s con gemma3:4b y 17 s con llama3.2:3b | De 2 min 34 s a 4 min 06 s por instrumento; respuesta del chat en la versión final: mediana 16 s y p90 30 s con llama3.2:3b | valores de la versión final (Tabla 163) |
| [2580] | 6.9. Demostración con métricas | [Se puede usar en el equipo disponible · col 3] 6.10, 6.8 | 6.10, 6.7.9 | valores de la versión final |
| [2583] | 6.9. Demostración con métricas | el juez solo se calcula si se pide, y la calificación humana se guarda aparte. | las métricas de RAGAS las calcula el juez externo por API y la calificación humana se hace fuera de línea. | origin/PArturo: services/visualization-service/services/juez_fable.py y routers/rag.py:77 |
| [2587] | 6.10. Duración del procesamiento | Qué se midió. El sistema registra | El sistema registra | redacción de tesis: sin encabezados de plantilla |
| [2593] | 6.10. Duración del procesamiento | Resultado. Más del | Más del | redacción de tesis: sin encabezados de plantilla |
| [2594] | 6.10. Duración del procesamiento | (Tablas 147 y 165) | (Tabla 169) | los tiempos por modelo son la Tabla 169 |
| [2604] | 7.1. Artefactos generados | (Figura 34) | (Figura 47) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2604] | 7.1. Artefactos generados | se adjuntan el archivo de respuestas, el instrumento original y, en las pruebas, la clave opcional | se adjuntan el archivo de respuestas y, de forma opcional, el instrumento original; las pruebas no llevan clave de respuestas porque no se califican | las pruebas no se califican (upload.py:47-48 rechaza la clave) |
| [2606] | 7.1. Artefactos generados | con el tipo de instrumento, el instrumento original y la clave opcional | con el archivo de respuestas de pru_04, el instrumento original (opcional) y el tipo de instrumento | captura nueva de la versión actual (el campo de clave ya no existe) |
| [2608] | 7.2. Limpieza de la encuesta | (Figura 35) | (Figura 48) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2608] | 7.2. Limpieza de la encuesta | La Tabla 82 | La Tabla 164 | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2614] | 7.2. Limpieza de la encuesta | (Tabla 83) | (Tabla 165) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2618] | 7.2. Limpieza de la encuesta | (Figura 36) | (Figura 49) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2618] | 7.2. Limpieza de la encuesta | (Figura 37) | (Figura 50) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2624] | 7.3. Limpieza de la prueba | (Figura 32) | (Figura 51) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2624] | 7.3. Limpieza de la prueba | La Tabla 3.3 | La Tabla 166 | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2624] | 7.3. Limpieza de la prueba | La prueba pru_04 contiene 90 alumnos y 18 reactivos, sin clave de respuestas. El sistema detectó el tipo de cada reactivo (6 de opción múltiple, 8 de escala y 4 de Sí/No), propuso la clave de los reactivos calificables a partir del 27 % de alumnos con mejor de… | La prueba pru_04 contiene 90 alumnos y 18 reactivos, sin clave de respuestas, porque el sistema no califica las pruebas. La limpieza detectó el tipo de cada reactivo (6 de opción múltiple, 8 de escala y 4 de Sí/No) y describió qué eligieron los alumnos en cada… | las pruebas no se califican; cifras de evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [Origen de la clave · col 1] Propuesta por el sistema (27 % superior) | 0 (sin clave no hay nada que confirmar) | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [Origen de la clave · col 0] Origen de la clave | Decisiones pendientes | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [KR-20 (6 reactivos calificables) · col 1] 0.447 (inaceptable) | r16 (Sí/No): 73.3 % respondió «No» | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [KR-20 (6 reactivos calificables) · col 0] KR-20 (6 reactivos calificables) | Reactivo donde más alumnos coinciden | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [Puntaje · col 1] Media de 4.06 sobre 6 (68 %), mediana de 4, desviación de 1.45 | r06 (escala de conductas): la opción más elegida, 4, reúne 26.7 % | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [Puntaje · col 0] Puntaje | Reactivo con las respuestas más repartidas | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [Dificultad · col 1] 2 fáciles, 4 medios, 0 difíciles | 0 / 0 | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [Dificultad · col 0] Dificultad | Reactivos casi unánimes / con opciones que nadie eligió | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [Reactivos con discriminación pobre · col 1] 0 | 11 | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2626] | 7.3. Limpieza de la prueba | [Reactivos con discriminación pobre · col 0] Reactivos con discriminación pobre | Columnas de contexto conservadas | las pruebas no se califican; evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2628] | 7.3. Limpieza de la prueba | (Figura 38) | (Figura 51) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2628] | 7.3. Limpieza de la prueba | El KR-20 de 0.447 debe interpretarse con cautela: solo 6 de los 18 reactivos son calificables y el coeficiente tiende a ser bajo con pocos reactivos. Los 12 restantes son escalas y preguntas de Sí/No de autoinforme, que el sistema identifica como no calificabl… | Las respuestas sintéticas son aleatorias (5.4), así que las distribuciones no reflejan dominio de un tema; solo comprueban que la descripción coincide con los datos. Ningún reactivo es casi unánime, en todos se eligieron todas las opciones y ninguno tiene resp… | quita el KR-20 y la discriminación; cifras de evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json y 04_Resultados.md Tabla R.4 |
| [2630] | 7.3. Limpieza de la prueba | KR-20, puntajes y análisis por reactivo | respuestas por reactivo de pru_04, sin calificar | captura nueva de la versión actual |
| [2632] | 7.4. Limpieza de la entrevista | (Figura 39) | (Figura 52) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2632] | 7.4. Limpieza de la entrevista | La Tabla 85 | La Tabla 167 | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2638] | 7.4. Limpieza de la entrevista | (Figura 40) | (Figura 53) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2638] | 7.4. Limpieza de la entrevista | (Figura 41) | (Figura 54) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2644] | 7.5. Estandarización | (Figura 42) | (Figura 55) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2644] | 7.5. Estandarización | (Figura 43) | (Figura 56) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2649] | 7.5. Estandarización | (Figura 44) | (Figura 57) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2652] | 7.5. Estandarización | (Figura 45) | (Figura 58) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2656] | 7.6. JSON final generado | (Figura 49) | (Figura 62) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2656] | 7.6. JSON final generado | Figuras 46, 47 y 48 | Figuras 59, 60 y 61 | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2668] | 7.7. Defectos detectados y corregidos del flujo de limpieza … | (Tabla 87) | (Tabla 168) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2670] | 7.7. Defectos detectados y corregidos del flujo de limpieza … | [Clave de respuestas obligatoria · col 2] Clave propuesta por el sistema y confirmada por la investigadora | Las pruebas no se califican: no se pide ni se propone clave y se describe lo que eligieron los alumnos | la clave propuesta por el sistema se quitó el 25 oct (memoria «pruebas sin calificar»; upload.py:47-48) |
| [2671] | 7.7. Defectos detectados y corregidos del flujo de limpieza … | (Figura 47) | (Figura 63) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2675] | 7.8. Resultados de preguntas al RAG mediante lenguaje natura… | figura 48 | Figura 64 | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2678] | 7.8. Resultados de preguntas al RAG mediante lenguaje natura… | figura 49 | Figura (n) | referencia del cap. 7 a su propio pie (D3: solo numeración) |
| [2679] | 7.8. Resultados de preguntas al RAG mediante lenguaje natura… | (nuevo) | Figura (n) Segunda prueba al RAG: razones de abandono en las entrevistas y una pregunta ajena al dominio | figura sin pie (D3: solo numeración) |
| [2698] | 8.1. Conclusiones por componentes del sistema | (nuevo) | Datos de prueba: El sistema se probó con respuestas sintéticas, porque no se encontraron datos públicos de respuestas de este tipo (5.4). Las cifras de los capítulos 6 y 7 muestran que el sistema procesa y consulta correctamente los instrumentos, pero no descr… | origen de los datos: instrumentos sintéticos, sin datos públicos de respuestas |
| [2705] | Trabajo futuro |  | Validar el sistema con instrumentos y respuestas reales aportados por una institución, con los acuerdos de confidencialidad y de protección de datos personales que correspondan, para comprobar que el comportamiento observado con datos sintéticos se mantiene co… | origen de los datos: instrumentos sintéticos, sin datos públicos de respuestas |
| [2807] | Anexo A KPIs | (nuevo) | Tabla (n) Catálogo de KPIs | tabla sin pie |
| [2809] | Interfaz en producción | Interfaz en producción | Anexo B Interfaz en producción | letra del anexo, como el Anexo A |
| [2810] | Interfaz en producción | (nuevo) | Figura (n) Pantalla de inicio | figura sin pie en anexos |
| [2811] | Interfaz en producción | (nuevo) | Figura (n) Inicio: accesos y lo recién llegado al acervo | figura sin pie en anexos |
| [2812] | Interfaz en producción | (nuevo) | Figura (n) Catálogo de instrumentos con sus filtros | figura sin pie en anexos |
| [2813] | Interfaz en producción | (nuevo) | Figura (n) Tablero de KPIs | figura sin pie en anexos |
| [2814] | Interfaz en producción | (nuevo) | Figura (n) Espacio vectorial con un KPI seleccionado | figura sin pie en anexos |
| [2815] | Interfaz en producción | (nuevo) | Figura (n) Paso «Archivo» del asistente de carga | figura sin pie en anexos |
| [2816] | Interfaz en producción | (nuevo) | Figura (n) Armar una investigación | figura sin pie en anexos |
| [2817] | Interfaz en producción | (nuevo) | Figura (n) Chat: contexto de la investigación | figura sin pie en anexos |
| [2818] | Interfaz en producción | (nuevo) | Figura (n) Chat listo para preguntar y panel de noticias | figura sin pie en anexos |
| [2819] | Interfaz en producción | (nuevo) | Figura (n) Respuesta del chat con sus fuentes | figura sin pie en anexos |
| [2820] | Interfaz en producción | (nuevo) | Figura (n) Gestión de usuarios | figura sin pie en anexos |
| [2821] | Fichas técnicas de servicios | Fichas técnicas de servicios | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2822] | Fichas técnicas de servicios | Cargar un instrumento | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2823] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.CargaDeArchivosEndpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./instrumentos/uploadMétodo HTTPLa acción solicitada al… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2824] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2825] | Fichas técnicas de servicios | Obtener los datos iniciales del instrumento | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2826] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.MetadatosInicialesEndpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./instrumentos/{instrumento_id}/metadata/initMétodo … | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2827] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2828] | Fichas técnicas de servicios | Petición para ingresar los metadatos alineados a la ISO 8536 Dublin Core | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2829] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.Registro de metadatosEndpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./instrumentos/{instrumento_id}/metadataMétodo HT… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2830] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2831] | Fichas técnicas de servicios | Análisis por LLM del instrumento | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2832] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.Análisis del instrumento por LLMEndpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./instrumentos/{instrumento_id}/etl/an… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2833] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2834] | Fichas técnicas de servicios | Observar propuestas del LLM respecto a limpieza y enriquecimiento del instrumento | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2835] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.Propuestas del LLM para el instrumento Endpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./instrumentos/{instrumento_id}… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2836] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2837] | Fichas técnicas de servicios | Aprobar o rechazar propuestas del LLM | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2838] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.Aprobar o rechazar las propuestas previas del LLM respecto a limpieza y/o enriquecimiento del instrumento.Endpoint (URL)La ruta específica a través de la cual… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2839] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2840] | Fichas técnicas de servicios | Listar instrumentos accesibles | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2841] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.Listar instrumentos disponibles Endpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./instrumentosMétodo HTTPLa acción sol… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2842] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2843] | Fichas técnicas de servicios | Detalle completo del instrumento | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2844] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.Observar detalle completo del instrumento Endpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./instrumentos/{instrumento_… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2845] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2846] | Fichas técnicas de servicios | Eliminar un instrumento | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2847] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.Observar detalle completo del instrumento Endpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./instrumentos/{instrumento_… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2848] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2849] | Fichas técnicas de servicios | Descargar instrumentos | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2850] | Fichas técnicas de servicios | AtributoDescripciónEjemplo Carga del instrumentoIdentificador claro y descriptivo de la funcionalidad.Descargar un instrumento en sus formatos: original, JSON y .SAV Endpoint (URL)La ruta específica a través de la cual se accede al recurso en el servidor./inst… | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2851] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2852] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2853] | Fichas técnicas de servicios |  | (se quitó) | fichas de endpoints que ya no existen (decisión D4) |
| [2854] | Fichas técnicas de servicios | MOCKUPS SE QUEDAN COMO ANEXOS | (se quitó) | nota pendiente «MOCKUPS SE QUEDAN COMO ANEXOS» (se vuelve título) |
| [2854] | Fichas técnicas de servicios | (nuevo) | Mockups | título para los mockups (Figuras 65–68) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Anexo C Preguntas del conjunto de evaluación y del control | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Las tablas de este anexo muestran los 79 casos del conjunto de evaluación que escribió la investigadora (6.7.6): 25 sobre la encuesta, 25 sobre la prueba, 25 sobre la entrevista y 4 de cortesía, y al final los 24 del conjunto de control. Cada caso dice lo que … | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Preguntas sobre la encuesta (127) | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | CasoPregunta y lo que la respuesta debe contenerPrueba 1Prueba 2Prueba 3Final gemmaFinal llamaENC-01datos¿Cuántos estudiantes trabajan en un área relacionada con su carrera?Debe contener: Usar la pregunta de situación laboral; número y % sobre el total.SíSíSíS… | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Preguntas sobre la prueba (130) | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | CasoPregunta y lo que la respuesta debe contenerPrueba 1Prueba 2Prueba 3Final gemmaFinal llamaPRU-01datos¿Cuántos alumnos respondieron la prueba?Debe contener: Total de alumnos después de la limpieza.SíSíSíSíNoPRU-02datos¿Qué opción eligieron más en el reactiv… | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Preguntas sobre la entrevista (129) | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | CasoPregunta y lo que la respuesta debe contenerPrueba 1Prueba 2Prueba 3Final gemmaFinal llamaENT-01datos¿Cuántas intervenciones tuvo la participante?Debe contener: Turnos de la participante, separados de los del entrevistador.SíSíSíSíSíENT-02datos¿Cuántas pal… | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Preguntas de cortesía (sobre la encuesta 127) | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | CasoPregunta y lo que la respuesta debe contenerPrueba 1Prueba 2Prueba 3Final gemmaFinal llamaGEN-01cortesíaHolaDebe contener: Bienvenida, instrumento activo y 3 ejemplos sacados de ese instrumento.NoSíSíSíSíGEN-02cortesía¿Qué tal? ¿Qué puedes hacer?Debe conte… | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Las preguntas del conjunto de control son 8 sobre la encuesta 61 (CEN), 8 sobre la entrevista 60 (CET) y 8 sobre la prueba 133 (CPR), de los mismos tipos que las del conjunto de evaluación, en instrumentos que no se usaron al hacer los cambios. Las de la prueb… | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Preguntas del conjunto de control | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | CasoPregunta y lo que la respuesta debe contenerPrueba 1Prueba 2Prueba 3CEN-01datos¿Cuántos estudiantes trabajan más de 30 horas?Debe contener: Conteo y % sobre el total, desde la pregunta de carga laboral.NoNoSíCEN-02comparación¿Los que no trabajan dejan meno… | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo C: tablas de preguntas copiadas de pruebas_v2_final.docx (decisión D6) |
| [2864] | Fichas técnicas de servicios | (nuevo) | Anexo D Instrumentos utilizados en las pruebas | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | Este anexo presenta un instrumento de cada tipo de los que se usaron para probar el sistema: la encuesta enc_04, la prueba estandarizada pru_04 y la entrevista ent_01. Son los instrumentos con los que se midió la duración del procesamiento (6.10) y los que se … | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | D.1 Encuesta enc_04: Cuestionario de Motivación y Estrategias de Aprendizaje, forma corta | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | La encuesta retoma las dimensiones y el tipo de afirmaciones del Cuestionario de Motivación y Estrategias de Aprendizaje en su forma corta (MSLQ-SF), cuya estructura interna en estudiantes universitarios analizan Masso Viatela y Fonseca Gómez ⟦N_MASSO⟧. Tiene … | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Afirmaciones de la encuesta enc_04 por dimensión | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | DimensiónNúm.AfirmaciónElaboración1Cuando leo el material para esta clase, trato de relacionarlo con lo que ya sé.2Cuando estudio, elaboro mis propios ejemplos para entender mejor los conceptos.3Intento aplicar ideas de las lecturas en actividades o discusione… | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | La Tabla (n) muestra los primeros cinco respondentes del archivo, con algunos de sus datos de contexto y sus respuestas a las cinco afirmaciones de la dimensión Elaboración. | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Muestra de respuestas de la encuesta enc_04 | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | RespondenteEdadGéneroSemestrePromedioAf. 1Af. 2Af. 3Af. 4Af. 5R000123Femenino22.2245333R000217Masculino42.2143524R000325Masculino33.8655555R000421Femenino42.8344334R000522Femenino53.123123 | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | D.2 Prueba estandarizada pru_04: Evaluación de Competencias para el Aprendizaje Autónomo | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | La prueba se construyó para este trabajo. Tiene 18 reactivos en tres secciones: 8 de frecuencia, con una escala de 1 (nunca) a 5 (siempre); 6 de opción múltiple, con cuatro opciones (A a D), y 4 de sí o no. Se generaron las respuestas de 90 alumnos. Como el si… | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Reactivos de la prueba pru_04 por sección | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | SecciónNúm.ReactivoOpcionesConductas de aprendizaje autónomo1Establezco mis propios objetivos de aprendizaje al inicio de cada materia.1 = Nunca … 5 = Siempre2Busco recursos adicionales cuando no entiendo completamente un tema.1 = Nunca … 5 = Siempre3Evalúo mi… | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | La Tabla (n) muestra los primeros cinco alumnos del archivo con sus respuestas a dos reactivos de cada sección. | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Muestra de respuestas de la prueba pru_04 | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | AlumnoEdadGéneroR1R2R9R10R15R16R000124Masculino33BCSíSíR000219Femenino33DDSíNoR000324Masculino33CDNoSíR000427Otro44ADNoNoR000519Femenino44ACNoNo | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | D.3 Entrevista ent_01: estrategias de permanencia universitaria | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | La entrevista es semiestructurada y se construyó para este trabajo. Tiene 12 preguntas abiertas sobre lo que ayuda a un estudiante a continuar sus estudios (Tabla (n)). El archivo de respuestas reúne 40 transcripciones sintéticas; cada respuesta se arma con fr… | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Guía de preguntas de la entrevista ent_01 | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | Núm.Pregunta1¿Qué factores consideras que han sido fundamentales para continuar tus estudios universitarios hasta ahora?2¿Has pensado alguna vez en abandonar la universidad? ¿Qué te llevó a tomar esa decisión en su momento?3¿De qué manera el apoyo familiar ha … | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | La Tabla (n) muestra las tres primeras respuestas del primer entrevistado del archivo (R0001). | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | Tabla (n) Muestra de respuestas de la entrevista ent_01 | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) | PreguntaRespuesta de R00011. ¿Qué factores consideras que han sido fundamentales para continuar tus estudios universitarios hasta ahora?Los videos de YouTube me han ayudado bastante cuando no entiendo los temas de clase. Es un recurso que uso mucho. Los compañ… | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | (nuevo) |  | Anexo D: un instrumento de cada tipo |
| [2864] | Fichas técnicas de servicios | ⟦N_MASSO⟧ | [cita: N_MASSO] | cita en un párrafo nuevo |

## Entradas que salen de la bibliografía

- [1]I. Estoica, “Investigación mediante encuestas en educación”, 2021, 2021, [En línea]. Di
- [7]Yunfan Gaoa et al., “Retrieval-Augmented Generation for Large Language Models: A Survey
- [17]M. Duque, “IA Estrecha (ANI)”. 2024. [En línea]. Disponible en: https://www.manuduque.
- [18]M. Cohen, Louis Lawrence y Morrison, Keith, Research Methods in Education, 8a ed. Lond
- [39]A. Vaswani et al., “Attention Is All You Need”, Adv. Neural Inf. Process. Syst. NeurIP
- [86]Amreth Chandrasehar, “Evaluating and fine tuning LLM models for generative AI.”, Inter

Las de Estoica [1], Gao [7] y Vaswani [39] eran duplicados (sus citas pasan a Stoica, Gao et al. y Vaswani et al. [30]); Cohen [18] se reemplaza por la entrada corregida; Duque [17] no se citaba en ningún lugar; Chandrasehar [86] solo sostenía «MLLMOps».

## Renumeración de tablas y figuras (original → alineado)

| Tipo | Original | Alineado | Capítulo | Pie |
|---|---|---|---|---|
| Tabla | nuevo | 4 | 1 | Tabla 4 Contraste de los trabajos sobre instrumentos educativos y KPIs con la propuesta |
| Tabla | 4 | 5 | 3 | Tabla 5 Sprints para la gestión del proyecto |
| Tabla | 5 | 6 | 3 | Tabla 6 Justificaciones para la elección del modelo de embeddings |
| Tabla | 6 | 7 | 3 | Tabla 7 Justificaciones para la elección del LLM |
| Tabla | 7 | 8 | 3 | Tabla 8 Comparación de LLMs |
| Tabla | 8 | 9 | 3 | Tabla 9 Requerimientos funcionales |
| Tabla | 9 | 10 | 3 | Tabla 10 Requerimientos no funcionales |
| Tabla | 10 | 11 | 3 | Tabla 11 Reglas de negocio |
| Tabla | 11 | 12 | 3 | Tabla 12. Matriz de trazabilidad RF. |
| Tabla | 12 | 13 | 3 | Tabla 13. Matriz de trazabilidad RNF. |
| Tabla | 13 | 14 | 3 | Tabla 14. Análisis de riesgos. |
| Tabla | 14 | 15 | 3 | Tabla 15 Estructura del equipo |
| Tabla | 15 | 16 | 3 | Tabla 16 Recursos operativos necesarios |
| Tabla | 16 | 17 | 3 | Tabla 17 Distribución del proyecto |
| Tabla | 17 | 18 | 3 | Tabla 18 Distribución del proyecto con sueldos |
| Tabla | 18 | 19 | 3 | Tabla 19 Componentes técnicos del sistema |
| Tabla | 19 | 20 | 3 | Tabla 20 Requerimientos de hardware |
| Tabla | 20 | 21 | 3 | Tabla 21 Requerimientos de software |
| Tabla | 21 | 22 | 3 | Tabla 22 Inversiones que se tomarán en cuenta |
| Tabla | 22 | 23 | 3 | Tabla 23 Inversión inicial – Hardware |
| Tabla | 23 | 24 | 3 | Tabla 24 Inversión inicial - Software y herramientas |
| Tabla | 24 | 25 | 3 | Tabla 25 Costos operativos mensuales |
| Tabla | 25 | 26 | 3 | Tabla 26 Resumen de inversión total |
| Tabla | 26 | 27 | 4 | Tabla 27 Transformaciones automáticas universales |
| Tabla | 27 | 28 | 4 | Tabla 28 Casos asistidos universales |
| Tabla | 28 | 29 | 4 | Tabla 29 Detección de plataformas |
| Tabla | 29 | 30 | 4 | Tabla 30 Tipos canónicos inferidos automáticamente |
| Tabla | 30 | 31 | 4 | Tabla 31 Métricas de calidad calculadas para encuestas |
| Tabla | 31 | 32 | 4 | Tabla 32 Archivos generados por el módulo de limpieza de encuestas |
| Tabla | 32 | 33 | 4 | Tabla 33 Proceso de ejecución del módulo de limpieza para las pruebas estandarizadas |
| Tabla | 33 | 34 | 4 | Tabla 34 Formato de entrada y salida de los datos al módulo de limpieza |
| Tabla | 34 | 35 | 4 | Tabla 35 Metadatos para estandarización – Instrumento con Dublin Core adaptado |
| Tabla | 35 | 36 | 4 | Tabla 36 Metadatos obligatorios encuesta |
| Tabla | 36 | 37 | 4 | Tabla 37 Variantes estructurales por plataforma para tipos con representación múltiple |
| Tabla | 37 | 38 | 4 | Tabla 38 Metadatos adicionales por tipo de pregunta |
| Tabla | 38 | 39 | 4 | Tabla 39 Resumen de metadatos para encuestas |
| Tabla | 39 | 40 | 4 | Tabla 40 Archivos de salida |
| Tabla | 40 | 41 | 4 | Tabla 41. Metadatos según categoría y tipo de las entrevistas |
| Tabla | 41 | 42 | 4 | Tabla 42 Tabla de metadatos aplicables a las pruebas estandarizadas |
| Tabla | 42 | 43 | 4 | Tabla 43 Tipos de chunk por tipo de instrumento |
| Tabla | 43 | 44 | 4 | Tabla 44 Reglas de diseño de los chunks |
| Tabla | 44 | 45 | 4 | Tabla 45 Metadatos de un chunk y su uso |
| Tabla | 45 | 46 | 4 | Tabla 46 Tablas de la base de datos por grupo |
| Tabla | 46 | 47 | 4 | Tabla 47 Colecciones de ChromaDB |
| Tabla | 47 | 48 | 4 | Tabla 48 Dónde se guarda cada dato |
| Tabla | 48 | 49 | 4 | Tabla 49 Resumen de decisiones de diseño |
| Tabla | 49 | 50 | 4 | Tabla 50 CU-01: Subir instrumento |
| Tabla | 50 | 51 | 4 | Tabla 51 CU-02: Completar la limpieza asistida |
| Tabla | 51 | 52 | 4 | Tabla 52 CU-03: Registrar y aprobar los metadatos |
| Tabla | 52 | 53 | 4 | Tabla 53 CU-04: Asociar KPIs |
| Tabla | 53 | 54 | 4 | Tabla 54 CU-05: Guardar y publicar el documento final |
| Tabla | 54 | 55 | 4 | Tabla 55 CU-06: Explorar el acervo y descargar |
| Tabla | 55 | 56 | 4 | Tabla 56 CU-07: Armar una investigación |
| Tabla | 56 | 57 | 4 | Tabla 57 CU-08: Consultar en lenguaje natural |
| Tabla | 57 | 58 | 4 | Tabla 58 CU-09: Eliminar un instrumento |
| Tabla | 58 | 59 | 4 | Tabla 59 CU-10: Dar de alta usuarios |
| Tabla | 59 | 60 | 5 | Tabla 60 Endpoints de API Gateway |
| Tabla | nuevo | 61 | 5 | Tabla 61 Endpoints de instrument-service |
| Tabla | nuevo | 62 | 5 | Tabla 62 Endpoints de cleaning-service |
| Tabla | 60 | 63 | 5 | Tabla 63 analysis-service: asociación de KPIs por perfil |
| Tabla | 61 | 64 | 5 | Tabla 64 analysis-service: catálogo de KPIs |
| Tabla | 62 | 65 | 5 | Tabla 65 analysis-service: método anterior, conservado sin uso en la interfaz. |
| Tabla | 63 | 66 | 5 | Tabla 66 Endpoints de metadata-service |
| Tabla | 64 | 67 | 5 | Tabla 67 knowledge-service: perfil semántico |
| Tabla | 65 | 68 | 5 | Tabla 68 knowledge-service: documento final |
| Tabla | 66 | 69 | 5 | Tabla 69 knowledge-service: análisis de respuestas de entrevista |
| Tabla | 67 | 70 | 5 | Tabla 70 storage-service: archivos y artefactos |
| Tabla | 68 | 71 | 5 | Tabla 71 storage-service: lectura de contenido |
| Tabla | 69 | 72 | 5 | Tabla 72 storage-service: índice vectorial |
| Tabla | 70 | 73 | 5 | Tabla 73 storage-service: mantenimiento |
| Tabla | 71 | 74 | 5 | Tabla 74 visualization-service: catálogo e instrumentos |
| Tabla | 72 | 75 | 5 | Tabla 75 visualization-service: KPIs y tableros |
| Tabla | 73 | 76 | 5 | Tabla 76 visualization-service: espacio vectorial |
| Tabla | 74 | 77 | 5 | Tabla 77 visualization-service: consulta RAG |
| Tabla | 75 | 78 | 5 | Tabla 78 visualization-service: métricas de las respuestas |
| Tabla | 76 | 79 | 5 | Tabla 79 visualization-service: noticias |
| Tabla | nuevo | 80 | 5 | Tabla 80 Prefijos que el API Gateway reenvía a cada servicio |
| Tabla | nuevo | 81 | 5 | Tabla 81 Llamadas HTTP de cada servicio a storage-service |
| Tabla | nuevo | 82 | 5 | Tabla 82 Comunicación de los servicios a través de la base de datos relacional |
| Tabla | nuevo | 83 | 5 | Tabla 83 Comunicación de los servicios a través de ChromaDB |
| Tabla | 77 | 84 | 5 | Tabla 84 Formato de archivo por tipo de instrumento |
| Tabla | 78 | 85 | 5 | Tabla 85 Formato aceptado para encuesta |
| Tabla | 79 | 86 | 5 | Tabla 86 Instrumento original de una encuesta |
| Tabla | 80 | 87 | 5 | Tabla 87 Tipos de pregunta que reconoce la limpieza (casos de prueba reales) |
| Tabla | 81 | 88 | 5 | Tabla 88 Formatos de entrevista aceptados |
| Tabla | 82 | 89 | 5 | Tabla 89 Perfiles de estudiante |
| Tabla | 83 | 90 | 5 | Tabla 90 Artefactos por paso |
| Tabla | 84 | 91 | 5 | Tabla 91 Medidas de las encuestas |
| Tabla | 85 | 92 | 5 | Tabla 92 Medidas de las pruebas estandarizadas (no se califican) |
| Tabla | 86 | 93 | 5 | Tabla 93 Medidas de las entrevistas |
| Tabla | 87 | 94 | 5 | Tabla 94 Qué esperar en «Antes y después» de la limpieza |
| Tabla | 88 | 95 | 5 | Tabla 95 Reglas de interpretación |
| Tabla | 89 | 96 | 5 | Tabla 96 Niveles de información estadística y su destino |
| Tabla | 90 | 97 | 5 | Tabla 97 Campos del JSON final y qué responde cada tipo de pregunta |
| Tabla | 91 | 98 | 5 | Tabla 98 Ejemplo de análisis de una respuesta |
| Tabla | 92 | 99 | 5 | Tabla 99 Peticiones para analizar lo que se cuenta, con un ejemplo de salida |
| Tabla | 93 | 100 | 5 | Tabla 100 Decisiones de la persona investigadora en el proceso |
| Tabla | 94 | 101 | 5 | Tabla 101 Pasos que se miden |
| Tabla | 95 | 102 | 5 | Tabla 102 Qué se vectoriza de un instrumento y para qué |
| Tabla | 96 | 103 | 5 | Tabla 103 Recorrido de una pregunta |
| Tabla | 97 | 104 | 5 | Tabla 104 Qué hace el modelo y qué hace el sistema en cada pregunta |
| Tabla | 98 | 105 | 5 | Tabla 105 Chunks por tipo de instrumento y su tamaño en tokens |
| Tabla | 99 | 106 | 5 | Tabla 106 Campos del plan |
| Tabla | 100 | 107 | 5 | Tabla 107 Tipos de regla que corrigen el plan |
| Tabla | 101 | 108 | 5 | Tabla 108 Ejemplo del cálculo de un conteo, paso a paso |
| Tabla | 102 | 109 | 5 | Tabla 109 Resultado del cálculo por intención |
| Tabla | 103 | 110 | 5 | Tabla 110 Operaciones para preguntas frecuentes de investigación |
| Tabla | 104 | 111 | 5 | Tabla 111 Qué responde y qué no |
| Tabla | 105 | 112 | 5 | Tabla 112 Comportamiento por tipo de petición |
| Tabla | 106 | 113 | 5 | Tabla 113 Verificaciones de la redacción |
| Tabla | 107 | 114 | 5 | Tabla 114 Métricas del chat |
| Figura | nuevo | 19 | 5 | Figura 19 Dockerfiles de cada servicio y archivo de orquestación |
| Figura | 18 | 20 | 5 | Figura 20 Patrón común para Dockerfiles |
| Tabla | 108 | 115 | 5 | Tabla 115 Puertos para cada imagen |
| Tabla | 109 | 116 | 5 | Tabla 116 Roles de usuario |
| Figura | 19 | 21 | 5 | Figura 21 Función para autenticación |
| Figura | nuevo | 22 | 5 | Figura 22 Funciones de cifrado y verificación de contraseñas con passlib |
| Figura | 20 | 23 | 5 | Figura 23 Creación de token de acceso |
| Figura | 21 | 24 | 5 | Figura 24 Decodificación del token |
| Figura | 22 | 25 | 5 | Figura 25 Identificar usuario actual |
| Tabla | 110 | 117 | 6 | Tabla 117 Entorno de pruebas |
| Tabla | 111 | 118 | 6 | Tabla 118 Datos usados en cada prueba |
| Tabla | 112 | 119 | 6 | Tabla 119 Tipos de comparación |
| Figura | 23 | 26 | 6 | Figura 26 Asistente de siete pasos que recorren las pruebas en el navegador |
| Tabla | 113 | 120 | 6 | Tabla 120 Métricas usadas en las pruebas en limpieza |
| Tabla | 114 | 121 | 6 | Tabla 121 Métricas usadas en las pruebas de chat |
| Tabla | 115 | 122 | 6 | Tabla 122 Métricas usadas en la calificación de la respuesta |
| Tabla | 116 | 123 | 6 | Tabla 123 Métricas usadas para el contenido de la respuesta |
| Tabla | 117 | 124 | 6 | Tabla 124 Métricas usadas para RAGAS |
| Tabla | 118 | 125 | 6 | Tabla 125 Métricas usadas para decidir si responder o no y el tiempo de ejecución |
| Tabla | 119 | 126 | 6 | Tabla 126 Parámetros de cada etapa que usa un modelo de lenguaje |
| Tabla | 120 | 127 | 6 | Tabla 127 Umbrales del sistema |
| Tabla | 121 | 128 | 6 | Tabla 128 Recorrido completo con instrumentos del generador |
| Figura | 24 | 27 | 6 | Figura 27 Entrevista de 40 participantes después de la limpieza: hablantes, respuestas y p |
| Figura | 25 | 28 | 6 | Figura 28 Opción más elegida en cada reactivo de una prueba, sin calificar |
| Tabla | 122 | 129 | 6 | Tabla 129 Errores metidos en la copia de enc_01 |
| Figura | 26 | 29 | 6 | Figura 29 Ajustes automáticos de la limpieza: encuesta sin errores (arriba) y con errores |
| Figura | 27 | 30 | 6 | Figura 30 Columnas detectadas como ajenas al instrumento (encuesta con errores) |
| Figura | 28 | 31 | 6 | Figura 31 Valores fuera de la escala, con su columna y su fila |
| Figura | 29 | 32 | 6 | Figura 32 Pregunta con muchos vacíos y filas duplicadas |
| Figura | 30 | 33 | 6 | Figura 33 Calidad de las respuestas; en el recuadro, una decisión distinta de la sugerida |
| Figura | 31 | 34 | 6 | Figura 34 Antes y después de la limpieza (encuesta con errores); en el recuadro, el bloque |
| Tabla | 123 | 130 | 6 | Tabla 130 Resultados de la limpieza en cada versión de enc_01 |
| Tabla | 124 | 131 | 6 | Tabla 131 La limpieza por tipo de instrumento y clase de error |
| Figura | 32 | 35 | 6 | Figura 35 Errores no previstos corregidos en la primera prueba y en la versión final |
| Tabla | 125 | 132 | 6 | Tabla 132 Errores previstos encontrados, antes y después de corregir las tres causas |
| Tabla | 126 | 133 | 6 | Tabla 133 Errores metidos en la copia de pru_01 y lo que hizo la limpieza |
| Figura | 33 | 36 | 6 | Figura 36 Limpieza de la prueba con errores metidos: ajustes automáticos y alumnos repetid |
| Tabla | 127 | 134 | 6 | Tabla 134 Errores no previstos en pru_03: primera prueba y versión final |
| Tabla | 128 | 135 | 6 | Tabla 135 Errores metidos en la copia de ent_02 y lo que hizo la limpieza |
| Figura | 34 | 37 | 6 | Figura 37 Limpieza de la entrevista con errores metidos: correcciones automáticas y decisi |
| Figura | 35 | 38 | 6 | Figura 38 Confirmación de hablantes en la entrevista con errores: cuatro etiquetas, dos ro |
| Tabla | 129 | 136 | 6 | Tabla 136 Errores no previstos en ent_11: primera prueba y versión final |
| Tabla | 130 | 137 | 6 | Tabla 137 Encuesta de 2000 respondentes en la primera prueba y con la versión final |
| Tabla | 131 | 138 | 6 | Tabla 138 Casos de prueba por módulo |
| Tabla | 132 | 139 | 6 | Tabla 139 Preguntas que el JSON final debe permitir responder y consulta que lo comprueba |
| Tabla | 133 | 140 | 6 | Tabla 140 Un solo texto frente a pregunta por pregunta (primer catálogo de KPIs) |
| Figura | 36 | 39 | 6 | Figura 39 KPIs aceptados con las preguntas del instrumento que los respaldan |
| Tabla | 134 | 141 | 6 | Tabla 141 Conjuntos de prueba del chat |
| Tabla | 135 | 142 | 6 | Tabla 142 Técnicas del chat en la primera versión y en la versión final |
| Tabla | 136 | 143 | 6 | Tabla 143 Cada versión del chat contra la anterior, con el mismo conjunto |
| Figura | 37 | 40 | 6 | Figura 40 Regresión de 28 preguntas: solo reglas frente a plan del modelo y cálculo en cód |
| Tabla | 137 | 144 | 6 | Tabla 144 La misma prueba con y sin ejemplos en la instrucción del modelo |
| Tabla | 138 | 145 | 6 | Tabla 145 Cifras correctas cuando calcula el modelo y cuando calcula el código |
| Tabla | 139 | 146 | 6 | Tabla 146 Resumen de la prueba de cálculo |
| Figura | 38 | 41 | 6 | Figura 41 Cifras correctas cuando calcula el modelo y cuando calcula el código |
| Tabla | 140 | 147 | 6 | Tabla 147 Preguntas que dependían del total del porcentaje, en la primera y en la segunda |
| Tabla | 141 | 148 | 6 | Tabla 148 Fallas de interpretación: qué pasó en la primera prueba y qué se corrigió |
| Tabla | 142 | 149 | 6 | Tabla 149 Prueba ciega: 20 preguntas nuevas en la prueba final |
| Tabla | 143 | 150 | 6 | Tabla 150 Prueba final con las preguntas usadas para corregirlo y con las preguntas nuevas |
| Figura | 39 | 42 | 6 | Figura 42 Respuesta del chat: la redacción con cifras inventadas se rechaza y se muestra e |
| Tabla | 144 | 151 | 6 | Tabla 151 Chunks que pasan del límite de 128 tokens con cada forma de cortar |
| Tabla | 145 | 152 | 6 | Tabla 152 Hit@3 con cada versión de los chunks |
| Figura | 40 | 43 | 6 | Figura 43 Hit@3 con cada versión de los chunks |
| Tabla | 146 | 153 | 6 | Tabla 153 Hit@k y MRR de la versión final, con y sin los chunks de cada persona en la búsq |
| Tabla | 147 | 154 | 6 | Tabla 154 Búsqueda de elemento conocido (84 preguntas y reactivos, versión final) |
| Figura | 41 | 44 | 6 | Figura 44 Respuesta del chat con la tabla calculada y la fuente, que indica las partes rec |
| Tabla | 148 | 155 | 6 | Tabla 155 Respuestas que consultaron ChromaDB |
| Tabla | 149 | 156 | 6 | Tabla 156 Las mismas preguntas sin recuperación y con ella (gemma3:4b) |
| Tabla | 150 | 157 | 6 | Tabla 157 Conjunto de evaluación y control |
| Tabla | 151 | 158 | 6 | Tabla 158 Resultados de la evaluación final |
| Figura | 42 | 45 | 6 | Figura 45 Casos que cumplen lo que la respuesta debe contener, en cada prueba |
| Tabla | 157 | 159 | 6 | Tabla 159 Análisis de entrevistas, primera prueba y versión final |
| Tabla | 158 | 160 | 6 | Tabla 160 Acuerdo de la postura con cada anotación |
| Tabla | 159 | 161 | 6 | Tabla 161 Banco de preguntas (275 consultas) |
| Figura | 43 | 46 | 6 | Figura 46 Rechazo de una pregunta ajena a la investigación y de un intento de identificar |
| Tabla | 160 | 162 | 6 | Tabla 162 Búsqueda solo por significado frente a búsqueda híbrida (fragmento correcto entr |
| Tabla | 161 | 163 | 6 | Tabla 163 Qué llega a la respuesta con cada umbral (búsqueda híbrida) |
| Tabla | 162 | 164 | 6 | Tabla 164 La rama de pruebas y la versión unida con tres umbrales (48 preguntas, llama3.2: |
| Tabla | 163 | 165 | 6 | Tabla 165 Validación de la versión unida (umbral 0.55, llama3.2:3b) |
| Tabla | 164 | 166 | 6 | Tabla 166 Antes y después de la corrección de los IDs (entrevista y control de entrevista, |
| Tabla | 165 | 167 | 6 | Tabla 167 Modelos comparados (Ollama 0.32.9) |
| Tabla | 166 | 168 | 6 | Tabla 168 Comparación de redactores (encuesta 127, 28 turnos) |
| Tabla | 167 | 169 | 6 | Tabla 169 Confiabilidad de cada juez (78 respuestas por juez, todas con calificación human |
| Tabla | 168 | 170 | 6 | Tabla 170 Instrumentos no vistos: antes y después de las correcciones generales (entre par |
| Tabla | 169 | 171 | 6 | Tabla 171 llama3.2:3b frente a gemma3:4b, mismo sistema y mismos 79 casos |
| Figura | 44 | 47 | 6 | Figura 47 Casos que cumplen con cada modelo, en la prueba final |
| Tabla | 170 | 172 | 6 | Tabla 172 La misma redacción con tres temperaturas (12 casos, 2 repeticiones) |
| Tabla | 171 | 173 | 6 | Tabla 173 Instrucción completa frente a instrucción partida (30 casos nuevos, llama3.2:3b) |
| Tabla | 172 | 174 | 6 | Tabla 174 Dónde fallan las 19 respuestas que no cumplen del todo (instrucción completa, 30 |
| Tabla | 173 | 175 | 6 | Tabla 175 Afirmaciones sobre el sistema y la métrica que las respalda |
| Figura | 45 | 48 | 6 | Figura 48 Panel de evaluación de una respuesta: indicadores del sistema, con lo recuperado |
| Tabla | 174 | 176 | 6 | Tabla 176 Tiempo de cómputo por paso |
| Figura | 46 | 49 | 6 | Figura 49 Concentración del tiempo de cómputo en los pasos que usan modelos |
| Figura | 47 | 50 | 7 | Figura 50 Paso «Archivo» del asistente con el archivo de respuestas de pru_04, el instrume |
| Tabla | 164 | 177 | 7 | Tabla 177 Encuesta enc_04 antes y después de la limpieza |
| Figura | 48 | 51 | 7 | Figura 51 Fase asistida de la limpieza de la encuesta: acciones automáticas y decisiones p |
| Tabla | 165 | 178 | 7 | Tabla 178 α de Cronbach por bloque de la encuesta enc_04. |
| Figura | 49 | 52 | 7 | Figura 52 Pestaña «Estadística» de la encuesta: resumen «En pocas palabras» y α por bloque |
| Figura | 50 | 53 | 7 | Figura 53 Pestaña «Antes y después» de la encuesta. |
| Tabla | 166 | 179 | 7 | Tabla 179 Resultados de la limpieza de la prueba pru_04. |
| Figura | 51 | 54 | 7 | Figura 54 Pestaña «Estadística» de la prueba: respuestas por reactivo de pru_04, sin cali |
| Tabla | 167 | 180 | 7 | Tabla 180 Entrevista ent_01 antes y después de la limpieza. |
| Figura | 52 | 55 | 7 | Figura 55 Fase asistida de la entrevista: confirmación de los roles de los hablantes. |
| Figura | 53 | 56 | 7 | Figura 56 Pestaña «Estadística» de la entrevista: respuestas por pregunta y palabras por |
| Figura | 54 | 57 | 7 | Figura 57 Vista previa del CSV limpio de la entrevista. |
| Figura | 55 | 58 | 7 | Figura 58 Paso «Dublin Core» con los campos propuestos a partir de la limpieza. |
| Figura | 56 | 59 | 7 | Figura 59 Paso «Por tipo» con los campos propuestos a partir de la limpieza. |
| Figura | 57 | 60 | 7 | Figura 60 Paso «Aprobar metadatos»: perfil semántico legible y su representación JSON. |
| Figura | 58 | 61 | 7 | Figura 61 Paso «KPIs sugeridos» con puntaje, evidencia y justificación editable. |
| Figura | 59 | 62 | 7 | Figura 62 Estructura JSON Encuestas |
| Figura | 59 | 62 | 7 | Figura 62 Estructura JSON Encuestas |
| Figura | 60 | 63 | 7 | Figura 63 Estructura JSON Pruebas estandarizadas |
| Figura | 60 | 63 | 7 | Figura 63 Estructura JSON Pruebas estandarizadas |
| Figura | 61 | 64 | 7 | Figura 64 Estructura JSON Entrevistas |
| Figura | 61 | 64 | 7 | Figura 64 Estructura JSON Entrevistas |
| Figura | 62 | 65 | 7 | Figura 65 Paso «Guardar»: vista del documento final y su JSON. |
| Tabla | 168 | 181 | 7 | Tabla 181 Defectos detectados y corregidos |
| Figura | 63 | 66 | 7 | Figura 66 Estadística de la entrevista antes y después de la corrección del reconocimient |
| Figura | 64 | 67 | 7 | Figura 67. Prueba al RAG. |
| Figura | nuevo | 68 | 7 | Figura 68 Segunda prueba al RAG: razones de abandono en las entrevistas y una pregunta aje |
| Tabla | nuevo | 182 | anexos | Tabla 182 Catálogo de KPIs |
| Figura | nuevo | 69 | anexos | Figura 69 Pantalla de inicio |
| Figura | nuevo | 70 | anexos | Figura 70 Inicio: accesos y lo recién llegado al acervo |
| Figura | nuevo | 71 | anexos | Figura 71 Catálogo de instrumentos con sus filtros |
| Figura | nuevo | 72 | anexos | Figura 72 Tablero de KPIs |
| Figura | nuevo | 73 | anexos | Figura 73 Espacio vectorial con un KPI seleccionado |
| Figura | nuevo | 74 | anexos | Figura 74 Paso «Archivo» del asistente de carga |
| Figura | nuevo | 75 | anexos | Figura 75 Armar una investigación |
| Figura | nuevo | 76 | anexos | Figura 76 Chat: contexto de la investigación |
| Figura | nuevo | 77 | anexos | Figura 77 Chat listo para preguntar y panel de noticias |
| Figura | nuevo | 78 | anexos | Figura 78 Respuesta del chat con sus fuentes |
| Figura | nuevo | 79 | anexos | Figura 79 Gestión de usuarios |
| Figura | 65 | 80 | anexos | Figura 80 Panel de consulta de información en el sistema |
| Figura | 66 | 81 | anexos | Figura 81 Mockup de interfaz de KPIs subidos en el sistema |
| Figura | 67 | 82 | anexos | Figura 82 Mockup de inicio de sesión del sistema "Indagata" |
| Figura | 68 | 83 | anexos | Figura 83 Mockup de la pantalla de carga de archivo al sistema |
| Tabla | nuevo | 183 | anexos | Tabla 183 Preguntas sobre la encuesta (127) |
| Tabla | nuevo | 184 | anexos | Tabla 184 Preguntas sobre la prueba (130) |
| Tabla | nuevo | 185 | anexos | Tabla 185 Preguntas sobre la entrevista (129) |
| Tabla | nuevo | 186 | anexos | Tabla 186 Preguntas de cortesía (sobre la encuesta 127) |
| Tabla | nuevo | 187 | anexos | Tabla 187 Preguntas del conjunto de control |
| Tabla | nuevo | 188 | anexos | Tabla 188 Afirmaciones de la encuesta enc_04 por dimensión |
| Tabla | nuevo | 189 | anexos | Tabla 189 Muestra de respuestas de la encuesta enc_04 |
| Tabla | nuevo | 190 | anexos | Tabla 190 Reactivos de la prueba pru_04 por sección |
| Tabla | nuevo | 191 | anexos | Tabla 191 Muestra de respuestas de la prueba pru_04 |
| Tabla | nuevo | 192 | anexos | Tabla 192 Guía de preguntas de la entrevista ent_01 |
| Tabla | nuevo | 193 | anexos | Tabla 193 Muestra de respuestas de la entrevista ent_01 |

## Referencias del texto ajustadas

El bloque es el del documento alineado (después de las inserciones).

| Bloque | Antes | Después |
|---|---|---|
| [833] | Tabla 7 | Tabla 8 |
| [854] | Tabla 11 | Tabla 12 |
| [859] | Tabla 12 | Tabla 13 |
| [1024] | Tabla 27 | Tabla 28 |
| [1037] | Tabla 30 | Tabla 31 |
| [1044] | Tabla 31 | Tabla 32 |
| [1066] | Tabla 32 | Tabla 33 |
| [1091] | Tabla 35 | Tabla 36 |
| [1101] | Tabla 36 | Tabla 37 |
| [1118] | Tabla 38 | Tabla 39 |
| [1122] | Tabla 39 | Tabla 40 |
| [1129] | Tabla 40 | Tabla 41 |
| [1140] | Tabla 41 | Tabla 42 |
| [1152] | Tabla 42 | Tabla 43 |
| [1159] | Tabla 98 | Tabla 105 |
| [1159] | Tabla 43 | Tabla 44 |
| [1163] | Tabla 44 | Tabla 45 |
| [1190] | Tabla 46 | Tabla 47 |
| [1192] | Tabla 42 | Tabla 43 |
| [1194] | Tabla 44 | Tabla 45 |
| [1195] | Tabla 43 | Tabla 44 |
| [1197] | Tabla 47 | Tabla 48 |
| [1201] | Tabla 48 | Tabla 49 |
| [1203] | Tabla 77 | Tabla 84 |
| [1404] | Tabla 80 | Tabla 87 |
| [1495] | Tabla 83 | Tabla 90 |
| [1501] | Tabla 80 | Tabla 87 |
| [1509] | Tablas 84, 85 y 86 | Tablas 91, 92 y 93 |
| [1509] | Tabla 87 | Tabla 94 |
| [1521] | Tabla 84 | Tabla 91 |
| [1557] | Tabla 88 | Tabla 95 |
| [1578] | Tabla 89 | Tabla 96 |
| [1583] | Tabla 90 | Tabla 97 |
| [1598] | Tabla 91 | Tabla 98 |
| [1652] | Tabla 92 | Tabla 99 |
| [1666] | Tabla 91 | Tabla 98 |
| [1672] | Tabla 93 | Tabla 100 |
| [1677] | Tabla 94 | Tabla 101 |
| [1688] | Tabla 95 | Tabla 102 |
| [1702] | Tabla 98 | Tabla 105 |
| [1715] | Tabla 98 | Tabla 105 |
| [1726] | Tabla 96 | Tabla 103 |
| [1730] | Tabla 97 | Tabla 104 |
| [1735] | Tabla 98 | Tabla 105 |
| [1739] | Tabla 43 | Tabla 44 |
| [1739] | Tabla 44 | Tabla 45 |
| [1745] | Tabla 91 | Tabla 98 |
| [1884] | Tabla 100 | Tabla 107 |
| [1902] | Tabla 101 | Tabla 108 |
| [1909] | Tabla 102 | Tabla 109 |
| [1917] | Tabla 103 | Tabla 110 |
| [1959] | Tabla 106 | Tabla 113 |
| [1965] | Tabla 104 | Tabla 111 |
| [1978] | Tabla 105 | Tabla 112 |
| [2006] | Tabla 106 | Tabla 113 |
| [2011] | Tabla 107 | Tabla 114 |
| [2116] | Tabla 110 | Tabla 117 |
| [2131] | Tabla 111 | Tabla 118 |
| [2136] | Tabla 112 | Tabla 119 |
| [2146] | Figura 23 | Figura 26 |
| [2150] | Tablas 113 a 118 | Tablas 120 a 125 |
| [2176] | Tabla 119 | Tabla 126 |
| [2180] | Tabla 120 | Tabla 127 |
| [2187] | Tabla 121 | Tabla 128 |
| [2192] | Figura 24 | Figura 27 |
| [2192] | Figura 25 | Figura 28 |
| [2198] | Tabla 122 | Tabla 129 |
| [2203] | Figura 26 | Figura 29 |
| [2206] | Figura 27 | Figura 30 |
| [2209] | Figura 28 | Figura 31 |
| [2212] | Figura 29 | Figura 32 |
| [2215] | Figura 30 | Figura 33 |
| [2218] | Figura 31 | Figura 34 |
| [2221] | Tabla 123 | Tabla 130 |
| [2227] | Tabla 124 | Tabla 131 |
| [2227] | Figura 32 | Figura 35 |
| [2233] | Tabla 125 | Tabla 132 |
| [2245] | Tabla 126 | Tabla 133 |
| [2250] | Figura 33 | Figura 36 |
| [2253] | Tabla 127 | Tabla 134 |
| [2259] | Tabla 128 | Tabla 135 |
| [2264] | Figuras 34 y 35 | Figuras 37 y 38 |
| [2269] | Tabla 129 | Tabla 136 |
| [2275] | Tabla 130 | Tabla 137 |
| [2282] | Tabla 131 | Tabla 138 |
| [2290] | Tabla 132 | Tabla 139 |
| [2304] | Tabla 133 | Tabla 140 |
| [2314] | Figura 36 | Figura 39 |
| [2319] | Tabla 134 | Tabla 141 |
| [2323] | Tabla 114 | Tabla 121 |
| [2325] | Tabla 135 | Tabla 142 |
| [2325] | Tabla 136 | Tabla 143 |
| [2325] | Figura 37 | Figura 40 |
| [2336] | Tabla 119 | Tabla 126 |
| [2351] | Tabla 137 | Tabla 144 |
| [2367] | Tabla 138 | Tabla 145 |
| [2367] | Figura 38 | Figura 41 |
| [2380] | Tabla 140 | Tabla 147 |
| [2385] | Tabla 141 | Tabla 148 |
| [2390] | Tablas 142 y 143 | Tablas 149 y 150 |
| [2398] | Figura 39 | Figura 42 |
| [2402] | Tabla 136 | Tabla 143 |
| [2405] | Tabla 144 | Tabla 151 |
| [2409] | Tabla 145 | Tabla 152 |
| [2409] | Figura 40 | Figura 43 |
| [2415] | Tabla 146 | Tabla 153 |
| [2419] | Tabla 147 | Tabla 154 |
| [2428] | Figura 41 | Figura 44 |
| [2432] | Tabla 148 | Tabla 155 |
| [2432] | Tabla 149 | Tabla 156 |
| [2441] | Tabla 150 | Tabla 157 |
| [2445] | Tabla 151 | Tabla 158 |
| [2445] | Figura 42 | Figura 45 |
| [2467] | Tabla 151 | Tabla 158 |
| [2467] | Tabla 169 | Tabla 171 |
| [2467] | Tabla 151 | Tabla 158 |
| [2470] | Tabla 157 | Tabla 159 |
| [2475] | Tabla 158 | Tabla 160 |
| [2481] | Tabla 159 | Tabla 161 |
| [2485] | Tabla 151 | Tabla 158 |
| [2486] | Figura 43 | Figura 46 |
| [2511] | Tabla 106 | Tabla 113 |
| [2516] | Tablas 165 y 166 | Tablas 167 y 168 |
| [2523] | Tabla 167 | Tabla 169 |
| [2527] | Tabla 168 | Tabla 170 |
| [2538] | Tabla 169 | Tabla 171 |
| [2538] | Figura 44 | Figura 47 |
| [2538] | Tabla 119 | Tabla 126 |
| [2577] | Tabla 173 | Tabla 175 |
| [2582] | Figura 45 | Figura 48 |
| [2582] | Figura 41 | Figura 44 |
| [2586] | Tabla 174 | Tabla 176 |
| [2592] | Figura 46 | Figura 49 |
| [2593] | Tabla 169 | Tabla 171 |
| [2603] | Figura 47 | Figura 50 |
| [2607] | Figura 48 | Figura 51 |
| [2607] | Tabla 164 | Tabla 177 |
| [2613] | Tabla 165 | Tabla 178 |
| [2617] | Figura 49 | Figura 52 |
| [2617] | Figura 50 | Figura 53 |
| [2623] | Figura 51 | Figura 54 |
| [2623] | Tabla 166 | Tabla 179 |
| [2627] | Figura 51 | Figura 54 |
| [2631] | Figura 52 | Figura 55 |
| [2631] | Tabla 167 | Tabla 180 |
| [2637] | Figura 53 | Figura 56 |
| [2637] | Figura 54 | Figura 57 |
| [2643] | Figura 55 | Figura 58 |
| [2643] | Figura 56 | Figura 59 |
| [2648] | Figura 57 | Figura 60 |
| [2651] | Figura 58 | Figura 61 |
| [2655] | Figura 62 | Figura 65 |
| [2655] | Figuras 59, 60 y 61 | Figuras 62, 63 y 64 |
| [2667] | Tabla 168 | Tabla 181 |
| [2670] | Figura 63 | Figura 66 |
| [2674] | Figura 64 | Figura 67 |
| [2677] | Figura (n) | Figura 68 |
| [2854] | Tabla 151 | Tabla 158 |
| [2854] | Tabla 169 | Tabla 171 |
| [2867] | Tabla 151 | Tabla 158 |
| [2874] | Tabla (n) | Tabla 188 |
| [2878] | Tabla (n) | Tabla 189 |
| [2883] | Tabla (n) | Tabla 190 |
| [2887] | Tabla (n) | Tabla 191 |
| [2892] | Tabla (n) | Tabla 192 |
| [2896] | Tabla (n) | Tabla 193 |
