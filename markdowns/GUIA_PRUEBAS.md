# Guía para probar Indagata tú misma

Esta guía es para que hagas las pruebas con tus propios instrumentos: qué preparar, qué subir, qué revisar en
cada paso, dónde ver las métricas y cómo leerlas. Todo se hace en la interfaz (`http://localhost:3000`).

---

## 1. Qué hay y dónde

**Instrumentos que ya están en el sistema (25 oct):**

| id | Instrumento | Para qué sirve |
|---|---|---|
| 2–20 | JSON iniciales del proyecto | Base del catálogo; no pasaron por la limpieza |
| 22 | enc_04 (MSLQ-SF) | Encuesta con 8 subescalas |
| 53, 60 | ent_01 | Entrevista de 40 participantes |
| 55 | pru_01 | Prueba: opción múltiple, V/F y respuesta corta |
| 59 | enc_10_turno | Encuesta con turno; resultado conocido: 4 de 30 del vespertino de acuerdo con p4 |
| 61 | enc_09 | Encuesta de carga académica: Likert, opción múltiple, Sí/No, numéricas |
| 109 | enc_11 | Encuesta con los seis tipos de pregunta |
| 110, 111, 112 | pru_02, pru_04, pru_10 | Pruebas con cálculo numérico, Likert conductual y Sí/No |

**El acervo sintético** (`storage/instrumentos_sinteticos/`) tiene 11 encuestas, 10 entrevistas y 10 pruebas.
De ahí se usaron enc_01 (solo su CSV, fuera del sistema), enc_04, enc_05, enc_09, enc_10_turno, enc_11,
ent_01, pru_01, pru_02, pru_04 y pru_10. **Están sin usar** enc_02, enc_03, enc_06, enc_07, enc_08,
ent_02–ent_10, pru_03 y pru_05–pru_09. Cada uno tiene tres archivos: `_respondido` (las respuestas),
`_original` (el cuestionario sin respuestas) y `_metadata.json` (lo que se generó).

**Lo que hice yo**, por si quieres revisarlo: los scripts están en `tools/` (`tools/rag/`, `tools/limpieza/`,
`tools/formatos/`) y las salidas de cada corrida en `evidencias/<tema>_<fecha>/`, que es lo que citan los
capítulos. No necesitas nada de eso para tus pruebas.

---

## 2. Cómo preparar tu instrumento

### Encuesta
- **Respuestas:** CSV o Excel, **una fila por persona y una columna por pregunta**, con encabezados en la
  primera fila.
- **Cuestionario original** (recomendado): TXT o PDF con las preguntas numeradas y, si quieres, secciones
  («SECCIÓN 1: …»). Con él, el sistema toma el texto completo de cada pregunta; sin él, usa los encabezados.

**Tipos de pregunta que reconoce la limpieza, y cómo escribirlos en el CSV:**

| Tipo | Ejemplo de valores en la columna |
|---|---|
| Likert en texto | «Totalmente en desacuerdo» … «Totalmente de acuerdo» (o «Nunca» … «Siempre») |
| Likert numérica | 1, 2, 3, 4, 5 |
| Escala lineal | 1 a 10 («Del 1 al 10, ¿qué tan satisfecho estás?») |
| Opción múltiple (una respuesta) | «Transporte público», «Caminando», «Automóvil» |
| Sí / No | «Sí», «No» |
| Selección múltiple (varias) | «Biblioteca; Tutorías» (separadas por «;» o «,») |
| Jerarquización | «Empleo > Interés > Familia» (de la más a la menos importante) |
| Numérica | 12, 27, 40 («¿Cuántas horas…?») |
| Abierta | Texto libre |

### Prueba estandarizada
- Respuestas: una fila por alumno, una columna por reactivo (A/B/C/D, V/F, puntos 0–2, 1–5, Sí/No o un número).
- **Sin clave de respuestas:** Indagata no califica las pruebas. Si mandas una clave, la carga la rechaza.
  El sistema describe lo que eligieron los alumnos: la opción más elegida, las opciones que nadie eligió y
  cuántas respuestas quedaron nulas o vacías.

### Entrevista
- TXT, DOCX o PDF. Sirven las transcripciones con etiquetas («Entrevistador:» / «Entrevistado:»), con «P1:» y
  «R:», las de Zoom, el VTT de Teams y las transcripciones sin etiquetas.
- Varias personas en un mismo archivo: separa cada una con un bloque «RESPONDENTE: …».

---

## 3. Errores que puedes meter a propósito, y qué debe pasar

En el paso **«Limpieza»**, cada problema aparece como una **tarjeta** con opciones y una sugerida ya marcada.

**Encuestas:**

| Error que metes | Tarjeta que debe aparecer | Opción sugerida |
|---|---|---|
| Copiar una fila completa (respuestas idénticas) | Filas duplicadas | Eliminar |
| Un 7 o un 0 en una escala 1–5 | Valores fuera de rango (dice la columna y las filas) | Dejarlos vacíos |
| «No sé» o «No aplica» en una escala | Respuestas «No sé / No aplica» | Conservarlas marcadas |
| «NA», «N/A», «-» | No hay tarjeta: se toman como **vacíos** (es lo correcto) | — |
| Una columna casi vacía (más del 40 %) | Columna muy incompleta | Conservar (eliminar si está vacía en 90 % o más) |
| Una persona que deja más del 50 % sin responder | Encuestados casi sin responder | Eliminar |
| Una persona con la misma respuesta en todo un bloque de 4 o más ítems | Respuestas en línea recta | Conservar |
| Columnas «Marca temporal», «Dirección IP», «ID» | Columnas ajenas al instrumento | Eliminar |
| Un ítem redactado en negativo («No me siento motivado…») | Ítem invertido | Marcarlo como invertido (se recodifica: 5 pasa a 1) |
| Una escala de texto que no está en el diccionario | Escala por confirmar (orden de las opciones) | Confirmar el orden |
| Encabezados en código («P1_4_1») | Rol de la columna (pregunta, contexto, eliminar) | Debes decidir |

**Pruebas:**

| Error que metes | Qué debe pasar |
|---|---|
| El mismo ID en dos filas | Tarjeta «ID repetido» (conservar el primero) |
| «A,B» o «AB» en un reactivo | Respuesta nula, motivo `respuesta_multiple` |
| «?», «#» o «*» | Respuesta nula, motivo `ilegible` |
| «Z» u otra letra que no es opción | Respuesta nula, motivo `caracter_invalido` |
| Una fila completamente vacía | Se elimina y se cuenta como fila vacía |

**Lo que el sistema todavía NO hace** (no lo cuentes como falla de tu prueba):
- No dice qué respuesta es correcta ni cuántos aciertos hubo: las pruebas no se califican. Si preguntas
  al chat por aciertos, te lo aclara y te da la opción más elegida de cada reactivo.
- Una columna de contexto cuyo nombre no contiene ninguna palabra conocida (edad, turno, semestre, nivel,
  beca, trabajo, perfil…) se propone como pregunta. Cambia su rol en la tarjeta.

---

## 4. Paso a paso en la interfaz

Menú **«Subir instrumento»**. Son 7 pasos:

1. **Archivo.** Elige el tipo y sube las respuestas (y el original, si lo tienes). En una prueba no hay clave.
   *Revisa:* que no salga error de formato.
2. **Limpieza.** Decide cada tarjeta; luego **confirma**.
   *Revisa:* que aparezca la tarjeta de cada error que metiste (sección 3). Mira las pestañas
   **«Vista previa»**, **«Estadística»** y **«Antes y después»** (sección 5).
3. **Dublin Core.** Título, autor, tema, etc., propuestos por el sistema.
   *Revisa:* que el título y la descripción tengan sentido; corrige lo que no.
4. **Metadatos del tipo.** Población, nivel, dimensiones o secciones.
   *Revisa:* que las secciones y la población correspondan a tu instrumento.
5. **Aprobar metadatos.** Al aprobar, el instrumento entra al sistema.
6. **KPIs sugeridos.** Indicadores institucionales con su puntaje, la evidencia (qué preguntas lo respaldan)
   y una justificación. Acepta los que de verdad mide tu instrumento.
7. **Guardar.** Publica el documento final; queda disponible en el chat unos minutos después (se indexa en
   segundo plano).

---

## 5. Dónde ver las métricas y cómo leerlas

### a) En la limpieza (paso 2), pestaña «Estadística»
- **«En pocas palabras»:** frases con nivel «En orden», «Dato», «Conviene revisar» o
  «Posible problema». Es el resumen para leer primero.
- **Fiabilidad (α de Cronbach)** por bloque de ítems Likert: ≥ 0.9 excelente, ≥ 0.8 buena, ≥ 0.7 aceptable,
  ≥ 0.6 cuestionable, ≥ 0.5 pobre, < 0.5 inaceptable. Si **«α si se elimina el ítem»** es mayor que el α del
  bloque, ese ítem no va con los demás.
- **Estadística descriptiva:** media, mediana, desviación, cuartiles, asimetría (0 = pareja) y curtosis
  (0 = como la normal; negativa = repartida). **Atípicos** con dos reglas (±4 desviaciones y rango
  intercuartílico).
- **En pruebas** (no se califican): por cada reactivo, la **opción más elegida** y su %, las opciones que
  nadie eligió (en naranja) y el % **sin respuesta válida**. Más del 20 % sin respuesta válida sugiere
  revisar el reactivo. Un reactivo **casi unánime** (≥ 90 % en una opción) describe al grupo, pero no sirve
  para compararlo.
- Pestaña **«Antes y después»:** cómo cambiaron las cifras con tus decisiones (por ejemplo, el α sube al
  recodificar un ítem invertido).

La explicación completa de cada medida está en Desarrollo, X.7.2 (Tabla D.21a y «Cómo se leen las medidas»).

### b) En el catálogo
En **«Instrumentos»**, abre la **vista rápida** de un instrumento: la sección **«Calidad de los datos y
sugerencias de análisis»** repite las medidas de la última limpieza y sugiere análisis (por ejemplo, «puedes
promediar este bloque» si α ≥ 0.70).

### c) En los KPIs sugeridos (paso 6)
- **Puntaje** de cada KPI = 0.45 × parecido con el perfil general + 0.45 × parecido con las preguntas +
  0.10 × cobertura.
- **Evidencia:** las preguntas que más se parecen al KPI, con su similitud.
- Un puntaje alto no garantiza que el KPI sea pertinente: tú decides.

### d) En el chat, debajo de cada respuesta: «Evaluación automática»
Despliégala para ver:
- **Fidelidad:** qué parte de lo que afirma la respuesta está en las fuentes (baja = posible invención).
- **Relevancia:** qué tan directo contesta lo que preguntaste.
- **Precisión del contexto:** si los fragmentos recuperados sirvieron.
- Colores: verde ≥ 70 %, ámbar 40–69 %, rojo < 40 %. Abajo aparecen las **afirmaciones sin respaldo**, si las
  hay.
- **«Fidelidad 100 % por construcción»:** la respuesta es el resultado calculado mostrado tal cual (no la
  redactó el modelo), así que no necesita juez.
- **Son aproximadas:** las calcula un modelo pequeño (`qwen2.5:3b`). Úsalas como orientación y revisa las
  fuentes; la precisión del contexto, en particular, es poco confiable con este juez.

### e) Cómo comprobar tú misma una cifra del chat
Abre el CSV de respuestas en Excel y cuenta: por ejemplo, para «¿cuántos tienen beca?», filtra la columna de
la beca por «Sí» y compara el número con el del chat. Para un porcentaje por grupo, filtra primero el grupo
(por ejemplo «Vespertino») y luego la respuesta.

### f) Cuánto tardó cada paso: «Tiempos del procesamiento»
En la **vista rápida** del catálogo, despliega **«Tiempos del procesamiento»**. Verás:
- **Cómputo total:** la suma de lo que tardó la máquina en cada paso. **No** cuenta el tiempo que tú tardas
  en decidir tarjetas o revisar metadatos. Esta cifra es la que sirve para estimar un servidor.
- **De la carga a lo último:** el reloj completo, **con** tus decisiones incluidas.
- **Respuestas del chat:** la mediana y el p95 de lo que tardó el chat en contestar sobre ese instrumento.
  El p95 es el tiempo bajo el que quedan 95 de cada 100 respuestas.
- Una tabla con cada paso: carga, limpieza automática, aplicar decisiones, propuesta de metadatos,
  aprobación, perfil, KPIs, documento final, publicación, indexación. Los pasos marcados **«en segundo
  plano»** corren después y no te hacen esperar.

Además, debajo de cada respuesta del chat aparece **«Respondió en X s»**.

Los instrumentos procesados antes del 25 oct no tienen tiempos: el panel lo dice. Solo los que subas
desde ahora los registran.

Para defender la duración en un servidor:
1. Sube **instrumentos de distinto tamaño**; por ejemplo, una encuesta de 50, otra de 200 y otra de 500
   personas, o una entrevista corta y una larga.
2. Anota el cómputo de cada paso. Así ves qué paso crece con el tamaño (suele ser la indexación).
3. Anota en qué equipo corrió. Tu laptop está en Desarrollo, Tabla D.1: i5-11320H, 15.8 GB de RAM y
   GTX 1650 de 4 GiB. En un servidor con más memoria y una GPU mayor, los pasos que usan el modelo o los
   *embeddings* serían más rápidos. La limpieza casi no cambiaría.

---

## 6. Plantilla para anotar tus resultados

Así pasas tus pruebas al capítulo de Pruebas sin perder detalle.

| Fecha | Instrumento (archivo) | id | Qué metí a propósito | ¿Apareció la tarjeta? | Métrica que revisé | Valor | Pregunta al chat | Respuesta del chat | Mi cálculo | ¿Coincide? |
|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | |

Para la duración, usa esta otra (capítulo de Pruebas, Tabla P.23):

| Instrumento | Tamaño | Carga | Limpieza (automática + aplicar) | Metadatos | Aprobación + indexación | Perfil | KPIs | Documento | Indexación al RAG | Cómputo total | Punta a punta | Chat p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | |

Consejo: haz **un cambio a la vez** (un tipo de error por archivo, o anótalos todos con su fila y columna),
así sabes exactamente qué tarjeta corresponde a qué error.

---

## 7. Repetir las pruebas del chat de la tesis

Así cualquier persona del equipo repite, en su computadora, las corridas del capítulo de Pruebas con los mismos
instrumentos y las mismas preguntas.

**1. Configura los modelos.** En `.env` deben quedar `OLLAMA_MODEL=gemma3:4b`,
`RAG_JUEZ_MODELO=qwen3:4b-instruct` y, mientras pruebas, `RAG_CACHE_HORAS=0`, para que una pregunta repetida se
responda de nuevo. Descarga los modelos como dice `LEVANTAR_LA_APP.md`, paso 7.1, y recrea los servicios:
`docker compose up -d`.

**2. Sube los tres instrumentos** con el asistente completo: carga, limpieza, metadatos, KPIs, documento final y
publicar. Anota el **id** que recibe cada uno, porque en tu computadora será distinto:

| En la tesis | Archivo (`storage/instrumentos_sinteticos/`) | Casos |
|---|---|---|
| 127 (encuesta) | `encuestas/Encuesta2_Simulada_2000_SUCIA.csv` | `casos.json`: 14 casos, 28 turnos |
| 130 (prueba) | `pruebas/pru_03_sucio_no_contemplado.csv` | `casos_pru03.json`: 12 casos, 22 turnos |
| 129 (entrevista) | `entrevistas/ent_11_salud_mental_ruido.txt` | `casos_ent11.json`: 8 casos, 13 turnos |
| 131 (entrevista, ruido no contemplado) | `entrevistas/ent_11_salud_mental_ruido_no_contemplado.txt` | Prueba de ruido; mismas preguntas que la 129 |

**3. Regenera los casos con tus ids.** Las cifras esperadas se calculan de tu base:
```powershell
docker compose exec visualization-service python scripts/modelos/generar_casos.py --instrumento <id de la encuesta>
docker compose exec visualization-service python scripts/modelos/generar_casos_fase6.py --prueba <id de la prueba> --entrevista <id de la entrevista>
```

**4. Corre las preguntas en el chat**, una conversación por caso. Corre desde el host, con el chat sin usar mientras
tanto:
```powershell
$env:PYTHONIOENCODING="utf-8"; .venv\Scripts\python.exe -u services\visualization-service\scripts\modelos\correr_casos.py casos.json casos_pru03.json casos_ent11.json
```
Al final imprime la corrida, por ejemplo `gemma3:4b=1845-1910`. Con otro redactor, cambia `OLLAMA_MODEL`, recrea
`visualization-service` y repite.

**5. Califica** las respuestas, una vez por archivo de casos (0 mal, 1 parcial, 2 bien):
```powershell
docker compose exec visualization-service python scripts/modelos/calificar.py --casos casos.json --corrida gemma3:4b=<inicio>-<fin>
```

**6. Juez y reporte**, también por archivo de casos:
```powershell
docker compose exec visualization-service python scripts/modelos/juzgar.py --casos casos.json --juez qwen3:4b-instruct --corrida gemma3:4b=<inicio>-<fin>
docker compose exec visualization-service python scripts/modelos/reporte.py --casos casos.json --corrida gemma3:4b=<inicio>-<fin>
```
El reporte queda en `storage/evaluacion_modelos/<fecha>/`. Detalles en
`services/visualization-service/scripts/modelos/README.md`.

**7. Exporta tus calificaciones a CSV** para revisarlas en Excel o compartirlas con el equipo. Cada quien las guarda en
su propia base, así que cada quien exporta las suyas cuando termina de calificar:
```powershell
docker compose exec visualization-service python scripts/modelos/exportar.py
```
Queda en `storage/evaluacion_modelos/exportes/<fecha-hora>_calificaciones.csv`: una fila por consulta calificada, con
la pregunta, la respuesta, quién calificó, la calificación, el comentario, lo recuperado del RAG y las métricas de cada
juez. `--desde 1845 --hasta 1910` exporta solo un rango de consultas; `--todas` incluye las que no tienen calificación.
Si lo vuelves a correr después de calificar más, sale un archivo nuevo con todo lo calificado hasta ese momento.
