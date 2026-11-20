# Observaciones de la revisión del documento localizado en indagata/documentation/rag_tt.docx

## Inconsistencias graves 

1. El umbral tiene tres valores distintos en el documento:
   - 0.55 en el capítulo 5 (RAG, dominio acotado, y la Tabla 105, "alcanzan 55 %");
   - 0.35, con una zona dudosa de 0.35 a 0.50, en la Tabla 120 (6.4.2);
   - 0.65 en el texto de 6.7.9 ("el de la versión final (0.65)").
2. El modelo del chat se contradice:
   - el capítulo 5 dice que se eligió llama3.2:3b sobre gemma3:4b; Todo debe concluir con que se hace uso de lla,a3.2:3b
   - la Tabla del entorno de pruebas (6.2) dice que el modelo del chat es gemma3:4b;
   - la sección 6.8 concluye "Redactor: gemma3:4b", y 6.8.1 dice "terminó con gemma3:4b".
3. El número de reglas del prompt: el capítulo 5 dice 21, la Tabla 135 dice 20 y el código local tiene 16.
4. El número de intenciones: dice "12 intenciones" (Tabla 99 y en 6.7.2), pero el prompt y el código tienen 13. La Tabla 99 omite ranking_preguntas.
5. La ventana del modelo de embeddings: el capítulo 3 dice 512 tokens, y el 4, el 5 y el 6 (y el diseño de los chunks) dicen 128. El de 128 es el correcto.
6. El capítulo 3 sigue describiendo el diseño viejo, sin las notas aclaratorias que sí tiene el 4:
   - Huella del archivo: MD5 y /crudos/ (RF_04, RNF_10, RN_03, RN_05), cuando se usa SHA-256 en storage-service.
   - KPIs: inferidos "con una llamada al LLM por pregunta" (RF_06, RNF_05, RN_07, Fase 3), cuando se asocian por similitud con la fórmula 0.45·g + 0.45·p + 0.10·c.
   - Prompts: un catálogo editable por el administrador (RF_13 y RN_11), que no existe (DA-13).
   - Metadatos: bloqueados y "para corregir, eliminar" (RN_08 y RNF_11), cuando hay versiones.
   - Eliminación: solo el administrador puede eliminar y el archivo crudo se conserva (RN_04 y RN_09), cuando según CU-09 y DA-14 también borra el autor y se elimina todo.
   - Componentes técnicos: el frontend aparece como "Streamlit" (Tabla 11) y el modelo de embeddings como "bge-m3" (Tabla 18).
   - Requisitos no cumplidos: RNF_01 pide menos de 15 s sin GPU, y el capítulo 6 midió de 17 a 43 s de mediana con GPU. RNF_06 pide Precision@K de al menos 0.7, y nunca se mide Precision@K. Hay que reconocerlo o ajustar el requisito.
7. Datos públicos frente a sintéticos: el capítulo 1 (Originalidad) y RA-03 dicen que se valida "con instrumentos de fuentes públicas", pero todo el capítulo 6 usa datos sintéticos (el capítulo 5 lo explica bien).
8. Pruebas estandarizadas con y sin clave: 5.3 dice "sin clave de respuestas", pero la descripción de instrument-service menciona "la clave de respuestas" y las validaciones dicen "Columnas faltantes respecto a la clave → error".
9. "La búsqueda deja fuera los chunks de personas" (Tabla 43, 5.6.2 y 6.7.4): en el código de PArturo no se cumple, porque la búsqueda híbrida trae hasta 2 respondentes por instrumento. Hay que alinear el código o el texto.
10. Funciones de la interfaz que ya no existen: CU-08 (paso 6), la Tabla 96 (paso 10), la Tabla 107 y 6.9 dicen que el usuario puede pedir el juez y calificar la respuesta ("Calcular evaluación", "Tu calificación"). Ese panel se quitó del chat el 9 de noviembre.

## Errores de contenido

- DSRM se expande como "Data Science Methodology for Research". Es Design Science Research Methodology: así lo dice la misma referencia [83] de Peffers.
- Cuantización: "de 32 a 4 bits reduce el tamaño a la cuarta parte". Sería una octava parte; de 16 a 4 bits sí es una cuarta.
- Atención: "complejidad cuadrática… eleva exponencialmente" la memoria. Cuadrático no es exponencial.
- Modelos fundacionales "entrenados mediante aprendizaje supervisado". Es autosupervisado, y la frase siguiente lo contradice.
- Métodos HTTP: "IDEMPOTENT para actualizaciones" no es un método; son PUT o PATCH.
- CORS "previene CSRF". No es así: CORS controla las lecturas entre orígenes, no evita CSRF.
- Integridad (tríada CIA): se describe como control de acceso, que es confidencialidad. Además dice "NIST… en 19977".
- Ley de datos: "Ley Federal de Protección de Datos Personales en Posesión de Sujetos Obligados". El nombre correcto es Ley General; la Federal es la de particulares.
- Analítica prescriptiva: "clases con mayores capitales" es una traducción sin sentido.
- Pruebas estandarizadas "no muestran sesgos": es una afirmación fuerte, sin cita.
- Puertos (Dockerización): "cada contenedor publica su puerto interno en el mismo puerto del host", y la misma Tabla 108 lo contradice (8006→8000, 8008→8000, 8085→8000).
- Tamaño del modelo de embeddings: "pesa 420 MB". Conviene verificarlo; ronda 1 GB.
- Columnas en la Tabla 123: de "33 a 22 columnas" en la encuesta sin errores, cuando solo se quitó una columna.

## Referencias

- [99] se cita en el capítulo 4, pero la bibliografía termina en [87].
- Citas en formato autor-año mezcladas con el formato numérico (Gao et al. 2023, Rajkumar et al. 2022, Zheng et al. 2023, Es et al. 2024, Reimers y Gurevych 2020, George y Mallery). Varias no están en la bibliografía. También faltan BM25 (Robertson y Zaragoza) y RRF (Cormack et al.), que ya se usan en el sistema.
- Citas que apuntan a la fuente equivocada:
  - [3], un estudio de gestión de datos, se cita para TF-IDF/BM25;
  - [4], EBSCO, se cita para la eficacia de RAG;
  - [23], ServiceNow, se cita para HNSW;
  - [42], GeeksforGeeks sobre CNN, se cita para la calidad del dato;
  - [74], un blog, se cita para la ley de datos.
- Duplicadas: [1] y [4] son la misma obra (y el autor aparece como "Estoica"), y [7] y [37] también ("Yunfan Gaoa").
- [83] Peffers: faltan autores y el año es 2007, no 2014.
- "MLLMOps" no es un marco reconocido y su única cita [86] es débil. Conviene hablar de LLMOps o citar directamente RAGAS.

## Estructura, numeración y pendientes

- Una nota pendiente quedó en el texto: "[poner esas preguntas en anexos]" (6.7.3).
- Referencias vacías "(X.9 y X.10)" y "(x.7.8)" en el capítulo 5.
- "Estructura del documento" (cap. 1) dice que el capítulo 5 son las conclusiones, y el documento tiene 8 capítulos. También sigue diciendo "Fuera del alcance en TT I".
- Secciones citadas que no existen: 6.11, 6.12 y 6.13; el capítulo 6 llega a 6.10.
- Tablas numeradas dos veces: 59–64 se usan dos veces y 114 también. El entorno de pruebas aparece como "Tabla 110" en el texto y como "Tabla 114" en el título. Saltan de 169 a 172, y hay tablas sin número (endpoints de instrument-service y del gateway).
- Referencias a tablas equivocadas:
  - "Tabla 132" por 136;
  - "Tabla 115" por 119;
  - "Tablas 147 y 164" por 168;
  - "Tabla 30" por 32.
- El índice de figuras no coincide: tiene dos "Figura 1", la 39–46 repetida y salta de 16 a 23.
- Texto incompleto:
  - "Cada formato está en uno de tres niveles:" (5.3) y la lista no aparece;
  - "Los datos vienen de tres fuentes:" (6.3) y solo hay dos;
  - "Los seis tipos" de enc_11 y se enumeran siete.
- La Tabla 172 (6.9), que pretende resumir la versión final, mezcla versiones:
  - Hit@8/MRR son de la búsqueda semántica (0.95/0.80) y no de la híbrida (MRR 0.97);
  - "815 de 856 cifras" es de la tercera prueba, no de la final.
- Tono y redacción desiguales: hay primera persona coloquial ("vamos a…", "pasamos al…") en entrevistas y en la estandarización de entrevistas.
- El código en el documento perdió los saltos de línea y la sangría (5.4 y 6.6.1), y en 5.6 quedaron asteriscos de Markdown en "Ventana de 128 tokens.".
- Erratas sueltas: "Gateaway", "vectcorial", "Open sourcc", "React 18n+", "Hasting", "Perfi semántico", "acetados", "múlitple", "columas", "retormar", "-fsistema", "6 mentes", "(78%).kp" y "Tabla 35Metadatos".

## Avisos sobre cómo se leyó el documento

- Las celdas vacías de algunas tablas (125, 126, 138, 145 y 169) probablemente son celdas combinadas o con el mismo valor repetido, que se juntan al extraer el texto. No se marcaron como error; conviene revisarlas en Word.
- Las ecuaciones de Word (atención, coseno, z-score, IQR) no se pueden leer en texto plano. Hay que revisar en el archivo que se vean bien.
