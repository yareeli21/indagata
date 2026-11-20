# Cómo se atendió cada observación de la revisión

Cada observación de `observaciones_revision.md` se revisó contra el código local (rama `integracion-pruebas-pa`) y contra `origin/PArturo`, antes de cambiar nada. El resultado está en `documentación/rag tt_alineado.docx`; `rag tt.docx` no se modificó.

**Estados:**
- **Aplicada:** se corrigió como dice la observación.
- **Aplicada con ajuste:** se corrigió, pero distinto de lo que propone, porque el código dice otra cosa.
- **Descartada:** no se cambió, y se explica por qué.
- **No aparece:** el texto no está en esta versión del documento.

**Numeración:**
- Los números de tabla y figura se dan **con la numeración nueva** del documento alineado, y entre paréntesis el número que tenían antes.
- Los números que cita la revisión a veces no coinciden con ninguno de los dos, porque se hizo sobre otra versión; en esos casos me guié por la sección y el contenido.
- El detalle de cada edición (texto anterior → nuevo, evidencia) está en `CAMBIOS.md`.

## Inconsistencias graves

| # | Observación | Estado | Cómo se aplicó |
|---|---|---|---|
| 1 | El umbral tiene tres valores (0.55, 0.35 con zona 0.35–0.50 y 0.65) | Aplicada | Todo dice 0.55, el valor del código (`shared/db/core/config.py:111`). **Tabla 127 (antes 120):** el umbral pasa a «0.55, o al menos 75 % de las palabras de la pregunta (búsqueda híbrida)»; la zona dudosa queda «entre 0.55 y 0.50: vacía con este umbral» (`RAG_ZONA_GRIS_MAX` = 0.50), y «el clasificador no interviene». **6.7.9:** «el de la versión final (0.65)» → «el de la rama PArturo (0.65)», y en la Tabla 163 (antes 161), «0.65 (versión final)» → «0.65 (rama PArturo)». Los 0.35 que quedan son comparaciones medidas (prueba de umbrales y límites de los KPIs), no el umbral del sistema. |
| 2 | El modelo del chat se contradice; todo debe concluir con llama3.2:3b | Aplicada | **Tabla 117 (antes 110):** modelo del chat llama3.2:3b, con la aclaración de que las pruebas marcadas «prueba final en pruebas» de 6.7 se corrieron con gemma3:4b; se agrega el juez externo. **Tabla 126 (antes 119):** «llama3.2:3b (gemma3:4b en las pruebas que lo indican)» en las cuatro etapas. **6.8:** «Redactor: gemma3:4b» → «Redactor en esta comparación: gemma3:4b», más la frase «con el sistema completo, la prueba final de 6.8.1 llevó a elegir llama3.2:3b». **6.8.1:** «terminó con gemma3:4b» → «las pruebas intermedias se corrieron con gemma3:4b». Se agregó un párrafo «Modelo de la versión final»: llama3.2:3b en todas las etapas, por una exactitud parecida con 2.5 veces menos tiempo. |
| 3 | Reglas del prompt: 21 / 20 / 16 en el código | Aplicada con ajuste | El código local tiene **21** (`services/visualization-service/services/prompt.py`); el 16 es de PArturo y se descartó. **Tabla 142 (antes 135):** «20 reglas» → «21 reglas, enviadas según el contenido del mensaje». **5.8.3:** se explica que no se mandan todas: solo las que aplican a cada mensaje (`RAG_PROMPT_MODULAR = True`, `config.py:159`). **Tabla 103 (antes 96):** la fila «Redactar» dice «con las reglas del prompt que aplican a ese mensaje». |
| 4 | 12 intenciones, pero son 13; falta `ranking_preguntas` | Aplicada | «12» → «13» en las cuatro apariciones: Tabla 103, Tabla 106 (antes 99), texto de 5.7.2 y 6.7.2. Se agregó `ranking_preguntas` a la lista de la Tabla 106 y una fila nueva en la Tabla 109 (antes 102). Fuente: `esquemas/plan_consulta.json:135`. |
| 5 | Ventana de 512 tokens en el cap. 3 | Aplicada | 3.3.3 se reescribió: el modelo lee como máximo 128 tokens; la arquitectura BERT admite 512, pero este modelo se entrenó con 128, y lo que pasa de ahí se descarta. |
| 6 | El cap. 3 describe el diseño viejo | Aplicada | RF, RNF, RN y las dos matrices de trazabilidad (Tablas 9 a 13, antes 8 a 12) se reescribieron con el sistema actual, sin notas, como elegiste. Ver el detalle por tema abajo. |
| 6a | Huella MD5 y `/crudos/` | Aplicada | RF_04, RNF_10, RN_03, RN_05 y las matrices: SHA-256 en storage-service, comprobada al descargar. Las fases de DSRM también: MD5 → SHA-256 y sin `/crudos/` (tu decisión D8). RN_05 ahora dice que los archivos repetidos no se rechazan: cada carga es un instrumento nuevo y la huella queda como base para detectarlos después. |
| 6b | KPIs «con una llamada al LLM por pregunta» | Aplicada | RF_06, RNF_05, RN_07 y la matriz: asociación por similitud del perfil semántico (0.45·g + 0.45·p + 0.10·c), con las preguntas que la sustentan y la justificación del modelo; nada queda activo sin la aceptación del investigador. En las fases de DSRM no se cambió (D8: ahí solo MD5 y `/crudos/`). |
| 6c | Catálogo de prompts editable | Aplicada | RF_13 y RN_11 → «Instrucciones del modelo versionadas»: están en el código y en archivos de configuración versionados y no se editan desde la interfaz (DA-13). |
| 6d | Metadatos bloqueados, «para corregir, eliminar» | Aplicada | RN_08 y RNF_11 → «Versionado de metadatos»: corregir crea una versión nueva y la anterior se conserva. |
| 6e | Solo el admin elimina y el crudo se conserva | Aplicada | RN_04, RN_09, RF_14 y RNF_07: eliminan el autor o un administrador, y se borra todo (registros, archivos con el original y vectores). Verificado en `delete_service.py`. |
| 6f | Streamlit (Tabla 11) y bge-m3 (Tabla 18) | Aplicada | Matriz RF (Tabla 12): React 19 con TanStack Start. Tabla 19 (antes 18): paraphrase-multilingual-mpnet-base-v2 y «React 18+» → React 19. Tabla 6 (antes 5): 420 MB → cerca de 1.1 GB. |
| 6g | RNF_01 (< 15 s sin GPU) y RNF_06 (Precision@K ≥ 0.7) no se cumplen | Aplicada con ajuste | Se ajustaron los requisitos a lo que se mide, sin hacerlos a la medida (D9). **RNF_01:** mediana ≤ 20 s por turno con llama3.2:3b en una GPU de 4 GB (medido: 16 s; p90 30 s). **RNF_06:** Hit@8 ≥ 0.90 y MRR ≥ 0.80 con juicios fijados de antemano, y RAGAS como medida aproximada (medido: 1.00 y 0.97). Su fila en la matriz RNF dice cómo se mide. |
| 7 | Datos públicos frente a sintéticos | Descartada | Por tu instrucción: no se tocó nada (cap. 1, RA-03 ni 4.1). |
| 8 | Pruebas con y sin clave | Aplicada | **5.1.2:** instrument-service recibe el archivo respondido y, opcionalmente, el original; si llega una clave, la rechaza con 400 (`upload.py:47-48, 68-70`). Tabla 61 de endpoints: «y con 400 una clave de respuestas». **Tabla 81 (llamadas a storage-service):** sin «la clave». **5.3.4:** «Columnas faltantes respecto a la clave → error» se cambió por la regla real: «Hoja sin delimitador reconocido (coma o punto y coma) → error» (`motor.py:85`). **Cap. 7 (después, a pedido tuyo):** 7.1, 7.3, la Tabla 179 y la Tabla 181 ya no hablan de clave ni de KR-20; las Figuras 50 y 54 son capturas nuevas de la versión actual con pru_04. |
| 9 | «Se dejan fuera los chunks de personas» y la híbrida trae hasta 2 | Aplicada (se corrigió el texto) | Tablas 44 y 45 (antes 43 y 44), 5.6.2, 5.7.1, Tabla 142 y 6.7.4: «en la búsqueda por significado se dejan fuera; en la de palabras entran como máximo dos por instrumento» (`hibrida.py:109`, `_MAX_POR_PERSONA = 2`). |
| 10 | Panel del juez y «Tu calificación» que ya no existen | Aplicada | **CU-08 (Tabla 57):** el nombre pasa a «Consultar en lenguaje natural» y el paso 6 dice lo que muestra «Ver métricas». **DA-18:** indicadores en «Ver métricas» y RAGAS con el juez externo. **Tabla 103:** paso 10 corregido. **5.8.4:** «Bajo demanda… Calcular evaluación» → «Fuera de línea», y los indicadores se ven en «Ver métricas». **6.9 y Tabla 142:** igual. «Tu calificación» no aparecía. |

**Agregado por tu decisión D1 (no venía en la revisión).** Para las métricas de RAGAS se optó por un juez externo por API, Claude Fable 5.2. Está en un párrafo de 5.8.4, en DA-18, en la Tabla 78 de endpoints, en las Tablas 117 y 126, en 6.8 y en la Tabla 175. Se presenta como herramienta de experimentación, con datos sintéticos, y RNF_09 y RN_10 no cambiaron. **Ese juez está en `origin/PArturo`, no en tu rama local.**

## Errores de contenido

| Observación | Estado | Cómo se aplicó |
|---|---|---|
| DSRM mal expandido | Aplicada | 3.1: «Design Science Research Methodology». |
| De 32 a 4 bits = la cuarta parte | Aplicada | Tabla 7 (antes 6): «de 16 bits a 4 bits… a la cuarta parte», que coincide con el ejemplo de 16 GB. |
| Cuadrático «exponencialmente» | Aplicada | 2.x (LLM): «eleva cuadráticamente». |
| Aprendizaje «supervisado» | Aplicada | «autosupervisado». |
| IDEMPOTENT | Aplicada | «PUT o PATCH para actualizaciones». |
| CORS «previene CSRF» | Aplicada | CORS indica qué orígenes pueden leer las respuestas; no previene CSRF por sí solo. |
| Integridad descrita como confidencialidad; «19977» | Aplicada | Integridad: que la información no se altere ni se destruya sin autorización (hash, registro de cambios, control de quién modifica). Año: 1977. |
| Ley Federal → Ley General | Aplicada | «Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados (LGPDPPSO)», citando el texto publicado en el DOF el 20 de marzo de 2025. |
| «Clases con mayores capitales» | Aplicada | «Las clases con más alumnos podrían reducirse…». |
| Pruebas que «no muestran sesgos» | Aplicada | «Se consideran menos influidas por el criterio del docente». |
| Puertos de Dockerización | Aplicada | La frase dice ahora las excepciones: api-gateway 8006 → 8000, chromadb 8008 → 8000, chroma-viewer 8085 → 8000. 5.1.1 aclara que el gateway usa el 8000 dentro del contenedor y el 8006 en el equipo. |
| 420 MB | Aplicada | Cerca de 1.1 GB en disco, medido en el volumen `hf_cache`. |
| Tabla 130 (antes 123), «33 a 22 columnas» | Descartada | Se verificó con la captura (Figura 34, antes 31): la versión con errores pasa de 36 a 23 columnas; el texto ya estaba bien. |

## Referencias

| Observación | Estado | Cómo se aplicó |
|---|---|---|
| [99] en el cap. 4 | Aplicada | Era texto escrito a mano, no una cita. Ahora es una cita a Cohen, Manion y Morrison, *Research Methods in Education* (2018), con la entrada corregida. |
| Citas autor-año; BM25 y RRF sin fuente | Aplicada | Las 12 citas autor-año pasaron a [n] como campos de Zotero: Gao et al. (PAL) ×3, Rajkumar et al., Zheng et al., Es et al. (RAGAS), Reimers y Gurevych 2019 y 2020, George y Mallery, y las tres de 6.8.3 (Schluntz y Zhang, IFEval, Liu et al.). Se citan BM25 (Robertson y Zaragoza) y RRF (Cormack et al.) en 5.7.3 y en la Tabla 2, y HNSW (Malkov y Yashunin) en 2.x y 4.8. Todas las fuentes nuevas se verificaron con búsqueda. |
| [3] para TF-IDF/BM25 | Aplicada | → Robertson y Zaragoza. |
| [4] para la eficacia de RAG | Aplicada | → Lewis et al. |
| [23] para HNSW | Aplicada | → Malkov y Yashunin. |
| [42] para la calidad del dato | Aplicada | → Pipino, Lee y Wang. |
| [74] para la ley | Aplicada | → texto oficial de la LGPDPPSO (DOF). |
| Duplicadas [1]/[4] y [7]/[37] | Aplicada | Se fusionaron en Stoica y en Y. Gao et al. Apareció además un tercer duplicado, *Attention Is All You Need* (dos entradas), que también se fusionó. |
| [83] Peffers | Aplicada | Cuatro autores, *J. Manag. Inf. Syst.* 24(3):45–77, 2007, con su DOI. |
| MLLMOps y [86] | Aplicada | «LLMOps» en 3.1, 3.3 (título) y en las fases de DSRM; la cita pasa a RAGAS y Chandrasehar ([86]) sale de la bibliografía. |

**Otros ajustes de la bibliografía:**
- Queda con 94 entradas, todas citadas y en orden de aparición (IEEE).
- Salió Duque, que no se citaba en ningún lugar.
- Dos citas equivocadas más, que no venían en la revisión:
  - few-shot, que citaba una página de Google Cloud, ahora cita a Brown et al.;
  - las métricas de recuperación, que citaban a Coderhouse y a Firth, ahora citan a Manning et al. y a Salton y McGill.
- **Pendiente en tu biblioteca de Zotero:** está la lista en `decisiones_alineacion.md` §6. Si pulsas «Refresh» antes de hacerla, Zotero vuelve a poner los datos viejos.

## Estructura, numeración y pendientes

| Observación | Estado | Cómo se aplicó |
|---|---|---|
| «[poner esas preguntas en anexos]» | Aplicada | Se creó el **Anexo C** con las tablas de preguntas de `pruebas_v2_final.docx`: encuesta, prueba, entrevista y cortesía (79 casos), más el control (24); son las Tablas 183 a 187. 6.7.6 dice que están en el Anexo C. Se quitó «(encontrados en Anexo C)» de 6.7.3, porque esas 20 preguntas son otras. |
| «(X.9 y X.10)» y «(x.7.8)» | Aplicada | → «(5.8.1 y 5.7.5)» y «(5.5.7)». |
| Estructura del documento | Aplicada | Se reescribió con los 8 capítulos reales. «Fuera del alcance en TT I» se dejó, como pediste (D10). |
| Secciones 6.11–6.13 | Aplicada | La Tabla 125 (antes 118) remite a 6.10. Se quitó la remisión a «(sección 6.9)», junto con la mención de la falla que pediste quitar (D7). |
| Tablas numeradas dos veces, sin número, saltos | Aplicada | Todos los pies son ahora campos SEQ, en orden: 187 tablas y 83 figuras, sin duplicados ni saltos. Se agregaron pies a las tablas que no tenían: endpoints de instrument-service y cleaning-service, prefijos del gateway, llamadas a storage-service, comunicación por base de datos y por ChromaDB, contraste del cap. 1 y catálogo de KPIs. 157 referencias del texto se ajustaron a la numeración nueva. |
| Referencias a tablas equivocadas | Aplicada | «Tabla 132» → la de resultados por versión (hoy 143); «Tabla 115» → parámetros (hoy 126); «Tablas 147 y 165» → tiempos por modelo (hoy 171); «Tabla 30» → pasos de limpieza de pruebas (hoy 33). También «Figura 7» → la del flujo de KPIs (hoy 8) y «Tabla 84» → la de «Antes y después» (hoy 94). |
| Índice de figuras | Aplicada | Word regeneró el índice general, el de tablas (187) y el de figuras (83). El cap. 7 tenía sus propias referencias desfasadas; ahora apuntan a sus pies (tu decisión D3). Las «Figuras 59–61 repetidas» eran la copia de respaldo de tres cuadros de texto, no duplicados. |
| Texto incompleto | Aplicada | 5.3: se agregó la lista de los tres niveles (ideal, aceptado con aviso, rechazado). 6.3: «tres fuentes» → «dos fuentes». 6.5.1: «seis tipos» → «siete tipos». |
| Tabla 175 (antes 173), el resumen de la versión final, mezcla versiones | Aplicada | Hit@8/MRR: 1.00/0.97 con la híbrida (0.97 y 0.94 en el control), con la semántica entre paréntesis. Cifras con respaldo: 630 de 679 (92.8 %) y 234 de 234 en las preguntas nuevas, en lugar de «815 de 856». Se actualizaron también las filas de exactitud y de tiempo con la versión final. |
| Primera persona coloquial | Aplicada en el cap. 4 | Se reescribieron en tono impersonal los párrafos de limpieza y estandarización de entrevistas (4.5.2 y 4.6.4). En el cap. 7 (7.8) queda «podemos apreciar», porque es contenido protegido. |
| Código sin saltos de línea | Aplicada | 5.4: los cuatro bloques se reescribieron con el código real, una línea por renglón y con su sangría (`base_generator.py`, `coherencia_encuestas.json`, `coherencia.py`, `prueba_generator.py`, `entrevista_generator.py`). 6.6.1 ya estaba bien. Los asteriscos de «Ventana de 128 tokens.» se volvieron negrita real. |
| Erratas | Aplicada | Gateaway, vectcorial, Open sourcc, React 18n+, Hasting, Perfi semántico, acetados, múlitple, columas, retormar, -fsistema y «Tabla 35Metadatos». Además: «administrados», «Verdadero/false», «nueva versión nueva», «Version». **No aparecen en esta versión:** «6 mentes» y «(78%).kp». |

## Avisos sobre cómo se leyó el documento

| Aviso | Estado |
|---|---|
| Celdas que parecen vacías (combinadas) | No las cambié ni las revisé una por una en Word. Queda para tu revisión visual. |
| Ecuaciones de Word | No las toqué y siguen como objetos de ecuación. No revisé una por una que se vean bien en el PDF. |
