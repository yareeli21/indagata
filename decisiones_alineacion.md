# Decisiones de alineación — `documentación/rag tt.docx`

Fases 1 a 5 terminadas el 12 nov. El resultado es `documentación/rag tt_alineado.docx`; el original no se tocó (sigue con la misma huella SHA-256). El detalle de cada edición está en `CAMBIOS.md`. Tus respuestas a D1–D10 y cómo se aplicaron están en la sección 4; lo descartado, en la 5, y lo pendiente, en la 6.

**Fuentes que se usaron**
- **Código local:** rama `integracion-pruebas-pa` (versión unida, con los cambios del 12 nov).
- **Rama remota:** `origin/PArturo` @ `ef2346e` («rajas», 12 nov 02:08), traída solo con `git fetch`. Respecto a la versión unida, solo agrega el juez externo Claude Fable 5.2.

**Cómo se ubican los lugares del documento:** «[n]» es el número de bloque (párrafo o tabla) en el orden en que aparece en `word/document.xml`. Se extrajo de una copia, cuya huella SHA-256 está en `scratchpad/alineacion_tt/original.sha256`.

**Huecos que trae `rag tt.docx` respecto a los capítulos sueltos:** no incluye cuatro ajustes de hoy, que se portan en la Fase 2:
- «Son 21 reglas, pero no se mandan todas…» (5.8.3);
- la fila «Redactar» de la Tabla 96 con «las reglas que aplican»;
- «Prompt del sistema: solo con las reglas que aplican…» (5.8.1);
- «hasta esta prueba, la redacción llevaba…» y «la versión final adopta las reglas por contenido» (6.8.3).

---

## 1. Matriz de valores

| # | Tema | Qué dice el doc (dónde) | Código local | origin/PArturo | Valor elegido | Por qué |
|---|---|---|---|---|---|---|
| 1 | Umbral de similitud | 0.55 en 5.7.3 [1901], 5.8.1 [1980] y Tabla 105 [1986]; **0.35** en Tabla 120 [2185]; «versión final (0.65)» en 6.7.9 [2493] y fila «0.65 (versión final)» de la Tabla 161 [2501] | `shared/db/core/config.py:111` `RAG_MIN_SCORE = 0.55` | `config.py:109` = 0.65 | **0.55** | Es el más reciente y está medido: en 6.7.9 decide igual que 0.65 y conserva 7 fragmentos correctos más. En 6.7.9, «0.65» debe decir «el de la rama PArturo», no «versión final». |
| 2 | Zona dudosa (clasificador) | Tabla 120: «entre 0.35 y 0.50»; 5.8.1 [1980] ya dice que queda vacía | `config.py:117` `RAG_ZONA_GRIS_MAX = 0.50` (menor que 0.55, así que vacía) | 0.50 con umbral 0.65 (también vacía) | **Vacía: el clasificador existe, pero no interviene** | Decidiste corregir el texto y no el código. |
| 3 | Fuera del dominio | < 0.30 | `config.py:122` `RAG_FUERA_MAX = 0.30` | igual | 0.30 | Sin conflicto. |
| 4 | Modelo del chat | llama3.2:3b en 5.7 [1736] y DA-03; **gemma3:4b** en Tabla 110 [2121], 6.8 [2535] («Redactor: gemma3:4b») y 6.8.1 [2540] («terminó con gemma3:4b»); «gemma3:4b» en 6.7.3 [2366] y 6.7.5–6.7.6 | `config.py:36` y `.env:25` = `llama3.2:3b` | `config.py:36` = llama3.2:3b | **llama3.2:3b** | Lo pediste así. Las pruebas que se corrieron con gemma3:4b se dicen como tales («la prueba final en pruebas se corrió con gemma3:4b»), sin cambiar sus cifras. |
| 5 | Modelo juez | qwen3:4b-instruct, bajo demanda (Tabla 119, 5.8.4 [2028]) | `config.py:136-137`: `RAG_METRICAS_BAJO_DEMANDA = True`, `RAG_JUEZ_MODELO = ""`; el panel «Calcular evaluación» ya no está en el chat (ver #12) | Además, el juez **Claude Fable 5.2** por API: `services/visualization-service/services/juez_fable.py`, `config.py:141` `RAG_JUEZ_FABLE = True` | **Decisión D1** | Choca con «operación local» (RNF_09, RN_10, 1.3 [302] y 2.5.3 [759]) y no está en tu código local. |
| 6 | Reglas del prompt de redacción | 21 en 5.8.3 [1989]; **20** en Tabla 135 [2330]; 21 en 6.8.3 | `services/visualization-service/services/prompt.py:29` `SISTEMA`: 21 reglas (`prompt._REGLAS`, prueba `tests/test_instruccion_partida.py`); se envían por contenido (`config.py:159` `RAG_PROMPT_MODULAR = True`) | 16 (sin las reglas 17–21 de la rama de pruebas) | **21, enviadas según el contenido (mediana 13)** | El «16» de la revisión es de PArturo; el código actual tiene 21. |
| 7 | Intenciones del plan | «12» en Tabla 96 [1734] paso 4, Tabla 99 [1774], [1792] y 6.7.2 [2341]; Tabla 99 omite `ranking_preguntas` | `services/visualization-service/esquemas/plan_consulta.json:135`: 13 valores | 13 | **13** (incluida `ranking_preguntas`) | Código. |
| 8 | Modelo de embeddings y ventana | 3.3.3 [823]: «512 tokens»; Tabla 5 [820]: «420 MB»; Tabla 18 [892]: «Bge-m3»; caps. 4–6: 128 | `config.py:45` `paraphrase-multilingual-mpnet-base-v2`; el chunker mide con el tokenizador (máximo 128); en disco ocupa 1.1 GB (volumen `hf_cache`) | igual | **paraphrase-multilingual-mpnet-base-v2, 768 dimensiones, 128 tokens, ~1.1 GB** | El modelo de Sentence-Transformers trunca en 128, aunque la arquitectura BERT admite 512. |
| 9 | Búsqueda híbrida | 5.7.3 [1901]: hasta 2 chunks de persona por instrumento en la lista por palabras; Tabla 43 [1178], Tabla 44 [1185], 5.6.2 [1698], 5.7.1 [1745], 6.7.2 [2330] y 6.7.4 [2418]: «se dejan fuera» | `services/visualization-service/services/hibrida.py:30` `_K_RRF = 60`, `:109` `_MAX_POR_PERSONA = 2`; `config.py:127-128` `RAG_HIBRIDA = True`, `RAG_MIN_COBERTURA = 0.75` | igual | **Significado (Chroma) + BM25 (PostgreSQL FTS) + RRF k = 60; por significado se excluyen las personas, por palabras entran hasta 2 por instrumento** | Decidiste corregir el texto; 5.7.3 ya lo dice bien y se alinean los demás lugares. |
| 10 | top-k y fragmentos | Hasta 8, con 1 ficha y 3 fragmentos por instrumento (Tabla 120, 5.7.3) | `rag_service` (sin cambios) | igual | Igual | Sin conflicto. |
| 11 | Métricas RAGAS | 5.8.4: fidelidad, relevancia y precisión del contexto con juez local; 3.3.2: faithfulness, answer relevancy y context recall | Local: `services/visualization-service/services/evaluacion.py` (3 métricas, bajo demanda; endpoints `GET/POST /rag/consultas/{id}/metricas`) | `juez_fable.py`: 6 métricas de RAGAS 0.4.3 (precisión y recuerdo del contexto, fidelidad, relevancia, sensibilidad al ruido, corrección factual F1) en segundo plano; `routers/rag.py:77` `juezFable`; UI `EvaluacionFable.tsx` dentro de «Ver métricas» | **Decisión D1** | Ver D1. |
| 12 | Panel del juez y calificación en el chat | CU-08 paso 6 [1249], DA-18 [1223], Tabla 96 paso 10 [1734], 5.8.4 [2028] «Calcular evaluación» y 6.9 [2583] | `pixel-perfect-pixel/src/features/chat/PanelMetricas.tsx` y `CalificacionHumana.tsx` **no se importan**; `BurbujaMensaje.tsx:15` usa `VerMetricas`. El backend conserva `POST …/metricas` y `PUT …/calificacion` | Igual, más `EvaluacionFable.tsx` en «Ver métricas» | **«Ver métricas» sin juez en el chat; el juez y la calificación humana se hacen fuera de línea con scripts (`scripts/modelos/juzgar.py` y `calificar.py`)** | Código. |
| 13 | Puertos | 5.9.3 [2052]: «publica su puerto interno en el mismo del host»; Tabla 108 [2054] (correcta); 5.1.1 [1292]: gateway «puerto 8000» | `docker-compose.yml` | igual | Tabla 108 tal cual; la frase pasa a «salvo api-gateway (8006→8000), chromadb (8008→8000) y chroma-viewer (8085→8000)»; el gateway, «8000 dentro del contenedor, 8006 en el host» | Contradicción interna. |
| 14 | Huella del archivo | RF_04 [840], RNF_10 [845], RN_03 y RN_05 [849], Fase 2 y Fase 5 DSRM [786] [802] y RM-04 [991]: MD5 y `/crudos/` | `services/storage-service/services/file_manager.py:147` `sha256()`; claves `<tipo>/<id>/<versión>__<nombre>` | igual | **SHA-256 en storage-service, con claves versionadas; no se rechazan duplicados** (nota de RM-04 [992]) | Código. |
| 15 | Fórmula de los KPIs | RF_06, RNF_05, RN_07 y Fase 3 [794]: «una llamada al LLM por pregunta» | `config.py:92-96`: 0.45 · 0.45 · 0.10, evidencia ≥ 0.45, máximo 8 | igual | **0.45·g + 0.45·p + 0.10·c por similitud; el LLM solo redacta la justificación** | Código. |
| 16 | Metadatos | RN_08 y RNF_11: bloqueados, «eliminar y rehacer» | Versiones en `limpieza_ejecucion` y `version_conocimiento` (`routers/limpieza.py`, `?nueva=true`) | igual | **Versionados: repetir crea otra versión y la anterior se conserva** | Código y Tabla 45. |
| 17 | Eliminación | RF_14, RN_04 y RN_09: solo el administrador, el crudo se conserva y se registra en rag_log | `services/instrument-service/app/services/delete_service.py:31-33`: el autor (investigador) o el administrador; cascada desde `raw_data` + purga en storage | igual | **Autor o administrador; se borra todo (CU-09, DA-14); no se registra en rag_log** | Código. |
| 18 | Clave en pruebas | 5.1.2 [1301] y [1302]: «en las pruebas, la clave de respuestas»; [1392] «(y la clave)»; 5.3.4 [1443]: «Columnas faltantes respecto a la clave → error»; Tablas 32 y 33 [1074] [1077] (con nota) | `services/instrument-service/app/routers/upload.py:47-48, 68-70`: `archivo_clave` devuelve 400 | igual | **Sin clave** | Código y memoria «pruebas sin calificar». |
| 19 | Frontend | Tabla 11 [856]: «Streamlit»; Tabla 15: «React 18n+»; Tabla 18/20: «React 18+» | `pixel-perfect-pixel/package.json:37,47,76`: TanStack Start 1.168, React 19.2, Vite 8 | igual | **React 19 + TanStack Start + Vite** | Código. |
| 20 | Catálogo de prompts | RF_13 y RN_11: editable por el administrador | No existe (DA-13: instrucciones versionadas en el código y en `config/*.yaml`) | igual | **No existe; se reescribe el requisito** | Código. |
| 21 | Catálogo de KPIs | RF_12: alta, edición y baja desde la interfaz | `scripts/seed_kpis.py` (CSV) + `POST /vectorizacion/kpis/reindex`; sin alta ni edición en la interfaz | igual | **Se carga desde un CSV versionado con un script; el administrador lo reindexa** | Código. |
| 22 | Tiempo de respuesta (RNF_01) | «< 15 s sin GPU» | Medido: mediana 16–17 s y p90 30–37 s con GPU de 4 GB, llama3.2:3b (6.7.9, 6.8.1) | — | **Decisión D9** (propuesta: «mediana ≤ 20 s por turno con llama3.2:3b en una GPU de 4 GB») | Ajustar a lo medible, sin inflar. |
| 23 | Calidad de la recuperación (RNF_06) | «Precision@K y Recall@K ≥ 0.7» | Medido con juicios: Hit@8 = 1.00 y MRR = 0.97 (híbrida, 43 preguntas); elemento conocido MRR = 0.99 | — | **Decisión D9** (propuesta: «Hit@8 ≥ 0.90 y MRR ≥ 0.80 con juicios de relevancia fijados de antemano») | Precision@K no aplica con 1–2 fragmentos relevantes por pregunta (máximo 0.125–0.25 con K = 8). |
| 24 | Vectorización (RNF_04) y KPIs (RNF_05) | 5–30 min «con LLM»; < 15 min con «una llamada por pregunta» | Tabla 174: indexación al RAG 1 min 21 s a 1 min 54 s, sin LLM; propuesta de KPIs 25 s a 1 min 44 s | — | Propuesta: indexación ≤ 5 min y KPIs ≤ 3 min por instrumento de hasta 2,000 respondentes | Lo medido. |
| 25 | Número de contenedores y servicios | 5.9: 14; DA-05: 7 microservicios + gateway | `docker-compose.yml` | igual | Sin cambio | Ya alineado. |

---

## 2. Observaciones de `observaciones_revision.md`

### Inconsistencias graves
| Obs. | Decisión | Detalle |
|---|---|---|
| 1 Umbral | **APLICAR** | 0.55 en todo el documento. En la Tabla 120: «0.55 (o al menos 75 % de las palabras de la pregunta)» y la zona dudosa «vacía con este umbral». En 6.7.9 [2493] y en la Tabla 161, «0.65» queda como el de la rama PArturo. |
| 2 Modelo del chat | **APLICAR** | Tabla 110: «llama3.2:3b (las pruebas de 6.5 a 6.8 marcadas como "prueba final en pruebas" se corrieron con gemma3:4b)». 6.8 «Redactor»: se elige llama3.2:3b con la razón de 6.8.1. 6.8.1: «El sistema empezó con llama3.2:3b, usó gemma3:4b en las pruebas intermedias y terminó con llama3.2:3b». Las cifras medidas con gemma no se tocan. |
| 3 Reglas | **APLICAR, con corrección** | Tabla 135: 20 → 21 («21 reglas; se envían las que aplican»). El «16 en el código» se **descarta**: es de PArturo; el local tiene 21. |
| 4 Intenciones | **APLICAR** | «12» → «13» en las cuatro apariciones; se agrega `ranking_preguntas` a la Tabla 99 y una fila «ranking_preguntas» a la Tabla 102. |
| 5 Ventana 512 | **APLICAR** | 3.3.3 [823] se corrige de forma mínima: «el modelo lee 128 tokens (la arquitectura BERT admite 512, pero este modelo se entrenó y se usa con 128)». Es una corrección factual permitida en una zona protegida. |
| 6 Cap. 3 desactualizado | **APLICAR en RF, RNF, RN y matrices de trazabilidad (Tablas 8–12)**, reescribiendo como elegiste | En la Tabla 5 («420 MB» → «~1.1 GB») y la Tabla 18 («Bge-m3» → el modelo real), corrección factual mínima. Los textos de las Fases DSRM [786–802] (MD5, `/crudos/`, «el LLM infiere los KPIs por pregunta», `.SAV` como salida, cuatro niveles de chunks) quedan fuera de RF/RNF/RN: **Decisión D8**. |
| 6 RNF_01 y RNF_06 | **APLICAR, ajustando** | Ver D9. |
| 7 Públicos frente a sintéticos | **DESCARTAR** | Por tu instrucción: no se toca nada (cap. 1, RA-03, ni el párrafo [952] del cap. 4). |
| 8 Clave en pruebas | **APLICAR** | En 5.1.2 [1301] [1302] y [1392], y en 5.3.4 [1443]: «Columnas faltantes respecto a la clave → error» se cambia por la regla real (reactivos del encabezado; columnas extra → aviso). Las Tablas 32 y 33 (diseño) se quedan con su nota. |
| 9 Chunks de personas | **APLICAR (corregir el texto)** | Tabla 43, Tabla 44, [1698], [1745], Tabla 135, [2418] y [2428]: «por significado se dejan fuera; por palabras entran hasta 2 por instrumento». |
| 10 Panel del juez | **APLICAR** | CU-08 paso 6, DA-18, Tabla 96 paso 10, 5.8.4 «Bajo demanda» y 6.9 [2583]: «Ver métricas» muestra los indicadores sin juez; el juez y la calificación humana se corren fuera de línea. Se ajusta según D1. |

### Errores de contenido
| Error | Decisión | Dónde |
|---|---|---|
| DSRM | **APLICAR** | [772]: «Design Science Research Methodology» |
| 32 → 4 bits | **APLICAR** | Tabla 6 [832]: «a la octava parte» (16 GB → ~4–5 GB coincide con 16 bits; se ajusta la frase mínima: «de 16 bits a 4 bits, a la cuarta parte») |
| Cuadrático y no exponencial | **APLICAR** | [502]: «eleva cuadráticamente» |
| Autosupervisado | **APLICAR** | [461] |
| IDEMPOTENT | **APLICAR** | [717]: «PUT o PATCH para actualizaciones» |
| CORS y CSRF | **APLICAR** | [725]: se reescribe la frase mínima: CORS controla qué orígenes pueden leer las respuestas; no previene CSRF |
| Integridad (CIA) y año del NIST | **APLICAR** | [757]: la integridad garantiza que la información no se altere sin autorización; [755]: «19977» → «1977». *Pendiente de verificar el año exacto de la tríada CIA atribuida al NIST antes de escribirlo.* |
| Ley General | **APLICAR** | [609]: «Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados (LGPDPPSO)» |
| «clases con mayores capitales» | **APLICAR** | [744]: «las clases con más alumnos podrían reducirse…» (traducción de *larger class sizes*) |
| Las pruebas «no muestran sesgos» | **APLICAR** | 4.5.3 [1066]: se quita la afirmación absoluta («se consideran menos influidas por…») |
| Puertos | **APLICAR** | Ver #13 |
| 420 MB | **APLICAR** | Ver #8 |
| Tabla 123, «33 a 22» | **DESCARTAR** | Verificado con la captura (Figura 31): la versión con errores pasa de 36 a 23 columnas (13 eliminadas); la diferencia con la versión sin errores son las 3 columnas metidas, así que 33 → 22 es coherente. El 33 → 32 de `evidencias/cifras_limpieza_2026-10-18` es de una versión anterior de la limpieza. |

### Referencias
| Obs. | Decisión | Detalle |
|---|---|---|
| [99] en el cap. 4 | **APLICAR** | [952] es texto literal «[99]», no un campo de Zotero. Se sustituye por la cita del documento a la fuente correcta ([6], Pentang, instrumentos típicos) o se agrega la fuente (Cohen et al. [18] ya está). |
| Citas autor-año | **APLICAR** | Las de 5.6.3 [1719], 5.7 [1731] [1776] [1903], Tabla 84 [1517], 5.8.4 [2020] y 6.8.3 [2566] pasan a [n]. Las fuentes nuevas se agregan como ítems de Zotero (ver D2): PAL (Gao, Madaan et al., 2023), Rajkumar et al. 2022, Reimers y Gurevych 2020, Zheng et al. 2023, RAGAS (Es et al., ya es [85]), George y Mallery, Robertson y Zaragoza 2009 (BM25), Cormack, Clarke y Büttcher 2009 (RRF), IFEval (Zhou et al., 2023), Liu et al. 2022 y Schluntz y Zhang 2024. Cada una se verifica con búsqueda antes de agregarla. |
| Fuente equivocada | **APLICAR** | [3] (TF-IDF/BM25) → Robertson y Zaragoza; [4] (eficacia de RAG) → [11] Lewis et al.; [23] (HNSW) → Malkov y Yashunin 2018/2020; [42] (calidad del dato) → [51] Pipino et al.; [74] (ley) → texto oficial de la LGPDPPSO (DOF 2017). |
| Duplicadas | **APLICAR** | [1]/[4] (Stoica, EBSCO) y [7]/[37] (Gao et al., RAG survey). Se corrige «Estoica» → «Stoica» y «Yunfan Gaoa» → «Y. Gao». |
| Peffers | **APLICAR** | Peffers, Tuunanen, Rothenberger y Chatterjee, *J. Manag. Inf. Syst.*, vol. 24, núm. 3, pp. 45–77, 2007. |
| MLLMOps | **APLICAR** | [772] [775] [806] y el título 3.3: «LLMOps» y la cita a RAGAS [85]; se quita [86] solo donde sostiene «MLLMOps». |
| Renumerar | **APLICAR, según D2** | Son 83 ítems de Zotero en 156 campos. |

### Estructura, numeración y pendientes
| Obs. | Decisión | Detalle |
|---|---|---|
| «[poner esas preguntas en anexos]» | **YA RESUELTO EN EL TEXTO**, pero remite a un anexo que no existe | 6.7.3 [2366] dice «(encontrados en Anexo C)» y 6.7.6 [2470] «Las Tablas del Anexo C»; **no hay Anexo C**. Se crea el Anexo C con los 79 casos y los 24 del control, copiados de `pruebas_v2_final.docx`, y en 6.7.3 se apunta a la Tabla 138, que ya trae las 20 preguntas. *Se verificará que esas tablas existan en `pruebas_v2_final.docx`.* |
| «(X.9 y X.10)» y «(x.7.8)» | **APLICAR** | Tabla 74 [1364] → «(5.8.1 y 5.7.5)»; Tabla 81 [1427] → «(5.5.7)». |
| Estructura del documento | **APLICAR** | [273] describe los 8 capítulos reales; [287], «Fuera del alcance en TT I», queda fuera del alcance de la edición (está en «Alcance y delimitación», protegido): **Decisión D10**. |
| 6.11–6.13 | **APLICAR** | Tabla 118 [2176] «6.11» → «6.10»; «(sección 6.9)» en [2456] y [2345] apunta a la sección quitada «Cambios en el código»: ver D7. |
| Numeración duplicada | **APLICAR (Fase 4)** | Medido: 174 pies de tabla (1–174) con duplicados 164–168 (el cap. 7 reinicia en 164); el índice de tablas viejo duplica 59–64. Figuras: 71 pies (2–68), con duplicados 18, 59, 60 y 61; el cap. 7 cita figuras 32–49 que no son las suyas. Sin pie: endpoints de instrument-service [1302] y cleaning-service [1306], tablas de comunicación [1390] [1392] [1395] [1397], Tabla de 1.6.11 [436] y las imágenes de «Interfaz en producción» [2810–2820]. |
| Referencias a tablas equivocadas | **APLICAR, recalculadas tras renumerar** | «Tabla 132» → 136 en [2328] y [2405]; «Tabla 115» → 119 en [2339] y [2540]; «Tablas 147 y 165» → 169 en [2594]; «Tabla 30» → 32 en la Tabla 33 [1077]; «La Figura 7» → 8 en [1095]; «Tabla 84» → 87 en [1515]; «Las Tablas 113–122» → «113–120» en [2153]. |
| Índice de figuras | **APLICAR (Fase 4)** | El índice de contenido, el de figuras y el de tablas solo llegan al cap. 4; se regeneran. |
| Texto incompleto | **APLICAR** | 5.3 [1400] «tres niveles:»: el contrato de formatos de `instrument-service` tiene niveles aceptado, aceptado con aviso y rechazado (*se verifica en `app/config/constants.py`*). 6.3 [2125] «tres fuentes»: solo hay dos; se ajusta a «dos fuentes» salvo que encuentre la tercera en `pruebas_v2_final.docx`. 6.5.1 [2192] «seis tipos»: se enumeran siete; pasa a «siete tipos». |
| Tabla 173 (6.9) | **APLICAR** | «Hit@8 y MRR»: 0.95/0.80 → 1.00/0.97 (híbrida, versión final; se deja la semántica entre paréntesis). «Cifras con respaldo»: la de la versión final unida, 630 de 679 (92.8 %), más 234 de 234 con preguntas nuevas; 815 de 856 queda como tercera prueba. |
| Primera persona coloquial | **APLICAR** | 4.5.2 [1058] [1061], 4.6.4 [1143] [1147] [1148] (cap. 4). 7.8 [2675] [2678] está en el cap. 7, protegido: D3. |
| Código sin saltos | **APLICAR** | 5.4 [1466–1498] desde `tools/data_synthesis/generators/*.py`; 5.5.7 [1610–1647] (JSON); 5.7.2 [1769–1772] y [1779–1790]; 5.7.5 [1929–1954]; 6.6.1 [2290–2292] y [2298–2305] desde el código real. Se restaura la sangría con `xml:space="preserve"` en una fuente monoespaciada. |
| Asteriscos de Markdown | **APLICAR** | [1721] «**Ventana de 128 tokens. **» → negrita real. |
| Erratas | **APLICAR** | «Gateaway» ×3 (5.1.1), «vectcorial» (Tabla 15), «Open sourcc» (Tabla 20), «React 18n+» (Tabla 15), «Hasting» (Tabla 18), «Perfi semántico» (5.5.3), «acetados» (Tabla 81), «múlitple» (Tabla 36 y el índice), «columas» (Tabla 32), «retormar» (Tabla de cleaning), «-fsistema» [1155], «Tabla 35Metadatos» [1105]. «6 mentes» y «(78%).kp» no aparecen en el texto actual (se verifica en la Fase 5). |
| Celdas vacías y ecuaciones | **No es error** | Se revisan en el PDF. |

### Encontradas en la lectura (no estaban en la lista)
- **E1.** 6.8.3 [2566]: «la versión final las deja apagadas», pero la versión final adopta las reglas por contenido. Se porta la corrección.
- **E2.** Tabla 163 [2511]: «Control: cumplen» dice «15 (6 parciales, 3 no)» en la columna de la rama de pruebas, pero el texto [2512] dice que esa corrida no existe con llama3.2:3b. Se propone «No se corrió con llama3.2:3b».
- **E3.** Nota pendiente en anexos [2854]: «MOCKUPS SE QUEDAN COMO ANEXOS». Se quita.
- **E4.** El índice de contenido trae «CAPÍTULO» sin número para los caps. 3 y 4, y «10. Anexos». Se regenera.
- **E5.** «Figura 18» duplicada en el cap. 5 ([1384] y [2041]).

---

## 3. Decisiones que necesito de ti

- **D1. Juez Claude Fable 5.2 de PArturo.**
  - No está en tu código local.
  - Manda pregunta, respuesta y contexto a la API de Anthropic, lo que contradice RNF_09, RN_10, 1.3 y 2.5.3 («sin servicios externos»).
  - No hay resultados medidos con él.
  - Opciones:
    - (a) Integrarlo a tu rama como opción **apagada por omisión** y documentarlo como herramienta de evaluación externa: solo con datos sintéticos, fuera del flujo del investigador, con RNF_09 precisando «el flujo de datos de investigación opera en local». En el cap. 6 solo se describiría el método.
    - (b) Documentarlo como trabajo de la otra rama, no integrado.
    - (c) No mencionarlo.
  - **Recomiendo (a) sin resultados**, o (b) si no quieres tocar código.
- **D2. Bibliografía en Zotero.** Los 156 campos de cita y la bibliografía son de Zotero (grupo 6507167). Fusionar duplicados, agregar fuentes y renumerar se puede hacer editando los campos (número mostrado y datos incrustados), pero si alguien pulsa «Refresh» en Zotero se vuelven a imponer los datos de la biblioteca. Opciones:
  - (a) Edito los campos y te dejo la lista de ítems que hay que corregir o agregar en la biblioteca del grupo.
  - (b) Convierto todo a texto fijo (se pierde Zotero).
  - **Recomiendo (a).**
- **D3. Capítulos 7 y 8 (protegidos).**
  - **Contradicciones con el sistema:** la Figura 47 y [2604] hablan de «la clave opcional»; 7.3 [2624–2628] dice que «propuso la clave… KR-20 0.447»; la Tabla 168 dice «Clave propuesta por el sistema». Todo esto contradice «no se califica».
  - **Redacción:** 7.8 usa primera persona.
  - **Numeración:** sus referencias («Tabla 82», «Figura 34») no coinciden con sus pies.
  - ¿Corrijo solo la numeración de las referencias (Fase 4) y te dejo la lista de contradicciones, o no toco nada del 7 y el 8?
- **D4. Anexo «Fichas técnicas de servicios».** Describe endpoints que ya no existen (`/instrumentos/{id}/etl/analyze`, `/metadata/init`, `/etl/proposals`, el 409 por duplicado, `.sav` en la carga). Por tu instrucción no toco su contenido. ¿Lo dejo así y lo anoto como pendiente?
- **D5. Tabla 163, celda de control (E2).** ¿Aplico «No se corrió con llama3.2:3b»?
- **D6. Anexo C.** ¿Lo creo con los 79 casos y los 24 del control (tablas de `pruebas_v2_final.docx`)?
- **D7. «Sigue abierta (6.9)» en 6.7.2 [2345].** Se refiere a la falla de «estrategias/patrones» (ENC-06 y ENC-13), que pediste no mencionar en áreas de oportunidad. La sección 6.9 que citaba ya no existe. ¿Quito solo «y sigue abierta (6.9)» o toda la mención? Lo mismo con «(sección 6.9)» en [2456].
- **D8. Fases DSRM del cap. 3** [786–802]. Fuera de RF/RNF/RN describen el diseño inicial: MD5, `/crudos/`, un LLM por pregunta para los KPIs, el `.SAV` como salida y cuatro niveles de chunks.
  - (a) Corrección factual mínima: MD5 → SHA-256 y quitar `/crudos/`.
  - (b) Dejarlas como el plan inicial de DSRM, sin tocar.
  - **Recomiendo (a) solo en MD5 y `/crudos/`**, porque es un dato técnico falso.
- **D9. Nuevos RNF_01 y RNF_06** (propuesta, contra lo medido):
  - RNF_01: «mediana ≤ 20 s por turno del chat con llama3.2:3b en una GPU de 4 GB». Medido: 16–17 s; p90 30–37 s.
  - RNF_06: «Hit@8 ≥ 0.90 y MRR ≥ 0.80 sobre preguntas con juicios de relevancia fijados de antemano; las métricas RAGAS se reportan como aproximadas». Medido: 1.00 y 0.97 con la híbrida; 0.95 y 0.80 por significado.
  - Las dos se cumplen con margen sin estar hechas a la medida. ¿Las acepto así?
- **D10. «Fuera del alcance en TT I»** [287] está en 1.2.2 (protegido), no en «Estructura del documento». ¿Lo dejo?

---

## 4. Tus respuestas y cómo se aplicaron

Los números de tabla y figura de esta sección son los del original, como en el resto del archivo, salvo los del cap. 7 y los anexos, que ya son los nuevos. El mapa viejo → nuevo está al final de `CAMBIOS.md`. Por ejemplo, en el documento alineado la Tabla 163 es la 165 y la Tabla 173 es la 175.

- **D1. Juez externo.** RNF_09 y RN_10 quedan como estaban. Se agregó aparte que, para obtener las métricas de RAGAS, se optó por un juez externo por API (Claude Fable 5.2), como herramienta de experimentación:
  - en DA-18 (cap. 4);
  - en la Tabla 74 de endpoints (fila `POST /consultas/{id}/metricas?juez=claude-fable-5-2`);
  - en un párrafo nuevo de 5.8.4 (seis métricas de RAGAS 0.4.3, veredictos con salida estructurada, puntajes calculados en código, respuesta de referencia con 12 fragmentos más, tabla `rag_metrica_juez`);
  - en las Tablas 110 y 119 del cap. 6 (fila «Juez externo de RAGAS»), en 6.8 y en las Tablas 135 y 173.

  Se dice que solo se usa con los datos sintéticos de las pruebas y que no se midió su acuerdo con tu calificación. **El juez está en `origin/PArturo` (`services/visualization-service/services/juez_fable.py`), no en tu rama local.**
- **D2. Zotero.** Se editaron los campos (números y datos incrustados) y se reconstruyó la bibliografía. La lista de lo que hay que corregir en la biblioteca del grupo está en la sección 6.
- **D3. Caps. 7 y 8.** Solo numeración:
  - las 23 referencias del cap. 7 apuntan ahora a sus propios pies;
  - sus tablas siguen la numeración del documento (177–181);
  - se agregó el pie de la segunda captura del chat (Figura 68).

  Del contenido solo se corrigió después lo de la clave, a pedido tuyo (sección 6). Lo que «parecía» un pie duplicado en las Figuras 59–61 del original es la copia de respaldo que Word guarda de cada cuadro de texto; las imágenes están y no se borró nada.
- **D4.** Se quitaron las tablas de «Fichas técnicas de servicios» con su título.
- **D5.** Tabla 163, celda de control de la versión unida: «No se corrió con llama3.2:3b».
- **D6. Anexo C.** Se crearon las cinco tablas de `pruebas_v2_final.docx` (encuesta, prueba, entrevista, cortesía y control), con una introducción.
  - 6.7.6 [2444] y [2470] dicen que están en el Anexo C.
  - [2366] decía «(encontrados en Anexo C)» de las 20 preguntas numéricas de 6.7.3, que no son esas; se quitó.
  - «Interfaz en producción» pasa a «Anexo B» (misma lista que el Anexo A), y los mockups quedan bajo el título «Mockups».
- **D7.** Se quitó toda la mención de la falla de «estrategias/patrones» en [2345] y «(sección 6.9)» en [2456].
- **D8. DSRM.** Solo MD5 → SHA-256 y sin `/crudos/` ([786] y [802]).
- **D9.**
  - RNF_01 = «Mediana ≤ 20 s por turno» con llama3.2:3b en una GPU de 4 GB.
  - RNF_06 = «Hit@8 ≥ 0.90 y MRR ≥ 0.80» con juicios fijados de antemano; RAGAS como medida aproximada.
  - RF, RNF, RN y las dos matrices de trazabilidad se reescribieron con el sistema actual.
- **D10.** «Fuera del alcance en TT I» se dejó igual.

## 5. Observaciones descartadas o que no se cambiaron

- **Obs. 7** (datos públicos frente a sintéticos): por tu instrucción.
- **«16 reglas en el código»:** es de PArturo; tu código local tiene 21.
- **Tabla 123, «33 → 22»:** la captura (Figura 31) muestra 36 → 23; el texto ya está bien.
- **Notas «Nota:» del cap. 4** (por ejemplo RM-04 con MD5 y el retiro con `/crudos/`): se dejaron. Siguen tu convención de diseño + nota de implementación, y cada nota ya corrige el dato.
- **Bloques de código de 5.5.7, 5.7.2 y 5.7.5:** sus líneas largas van con sangría de continuación a propósito (son plantillas, ejemplos y texto del prompt), así que se dejaron. Solo se rehicieron los de 5.4, que estaban cortados a la mitad, con el código real.
- **Celdas vacías y ecuaciones:** no son error.

## 6. Pendientes

**En la biblioteca de Zotero (grupo 6507167).** Si pulsas «Refresh» antes de hacer esto, Zotero vuelve a poner los datos viejos de la biblioteca.

1. Fusionar los duplicados:
   - SWJX7J8W («Estoica», *Investigación mediante encuestas…*) en XWYDE4T4 (Stoica, *Survey Research in Education*);
   - YQWS3VSS («Yunfan Gaoa») en Z4Q24JIC (Y. Gao et al.);
   - UV44K79Y (*Attention Is All You Need*) en Z7SGY6RC.
2. Corregir datos:
   - XWYDE4T4: autor I. Stoica; publicación *EBSCO Research Starters: Education*; URL de EBSCO.
   - Z4Q24JIC: arXiv:2312.10997, 2024.
   - AXM5WIAC (Peffers): cuatro autores (Peffers, Tuunanen, Rothenberger, Chatterjee); *J. Manag. Inf. Syst.* 24(3):45–77, 2007; doi 10.2753/MIS0742-1222240302.
   - RMJ7ZTPK (RAGAS): EACL 2024 System Demonstrations, pp. 150–158; doi 10.18653/v1/2024.eacl-demo.16.
3. Agregar 13 fuentes nuevas, que en el documento van como datos incrustados. Al agregarlas, vuelve a insertar cada cita desde Zotero para ligarla.
   - Robertson y Zaragoza 2009 (BM25)
   - Cormack, Clarke y Büttcher 2009 (RRF)
   - Malkov y Yashunin 2020 (HNSW)
   - LGPDPPSO (DOF, 20 mar 2025)
   - Cohen, Manion y Morrison 2018
   - George y Mallery 2003
   - Reimers y Gurevych 2020
   - Gao et al. 2023 (PAL)
   - Rajkumar et al. 2022
   - Zheng et al. 2023
   - Schluntz y Zhang 2024
   - Zhou et al. 2023 (IFEval)
   - Liu et al. 2022
4. Ya no se citan: Duque (*IA Estrecha (ANI)*) y Chandrasehar (sostenía «MLLMOps»).

**En el documento.**

- **Cap. 7, la clave (corregido el 12 nov, a pedido tuyo).**
  - 7.1 y la Figura 50 ya no hablan de clave. La captura se rehízo con la versión actual (paso «Archivo» con pru_04).
  - 7.3 y la Tabla 179 describen lo que eligieron los alumnos, sin KR-20, puntaje ni dificultad. Las cifras salen de `evidencias/pruebas_2026-10-25/cifras_pruebas_regeneradas.json`, y la limpieza actual de pru_04 dio lo mismo.
  - La Figura 54 es una captura nueva de la pestaña «Estadística» de pru_04.
  - La fila «Clave de respuestas obligatoria» de la Tabla 181 dice ahora que las pruebas no se califican.
  - Para tomar las capturas se subió pru_04 dos veces a la base local; las dos copias (136 y 137) se borraron después.
- **Cap. 7, 7.8:** sigue la primera persona («podemos apreciar»). No se tocó, porque es contenido del capítulo protegido.
- **Ajustes que hice por mi cuenta y que puedes revisar:**
  - **Fuentes equivocadas que no estaban en la lista de la revisión:**
    - [494] few-shot: el [16] era una página de Google Cloud; ahora cita a Brown et al.
    - [527] métricas de recuperación: [24, 33] eran Coderhouse y Firth; ahora citan a Manning et al. y Salton y McGill.
  - **Citas nuevas de la técnica:**
    - BM25 y RRF en 5.7.3;
    - HNSW en 4.8.
- **Entrada [4] de la bibliografía (Thakar et al.):** trae «Vol 110 No 15, pp. 60–68v». Es un dato de la biblioteca y conviene revisarlo ahí.
- **Antes de entregar:** abre el documento en Word y, si cambias algo, actualiza los índices con F9.
