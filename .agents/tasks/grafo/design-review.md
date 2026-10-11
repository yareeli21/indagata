# Revisión de diseño — Grafo de Recomendación de Instrumentos

**Documento revisado:** `.agents/tasks/grafo/design.md`
**Fuente de verdad:** `markdowns/SPEC_GRAFO_RECOMENDACION.md`
**Modo de revisión:** en frío, verificando cada afirmación del diseño contra el código real del repositorio.

Este diseño es una revisión que ya respondió a un ciclo previo (§13). La reviso de nuevo
en frío, sin asumir que las respuestas de §13 son correctas: verifiqué cada afirmación
contra el código.

---

## Resumen del veredicto

El diseño está muy bien aterrizado. El hallazgo crítico de los **dos espacios de ID**
(`id_instrumento` vs `id_crudo`) es real y está verificado contra el código; su resolución
(exponer `idCrudo` + traducir en `/grafo/investigacion`) es correcta. Los contratos de los
tres endpoints, el score híbrido, la degradación, el schema aditivo y el contrato de
frontend concuerdan con la spec o se desvían de forma justificada y explícita.

Quedan algunas imprecisiones y una ambigüedad de tipos que conviene cerrar antes de
implementar. Ninguna invalida el diseño, pero dos cruzan el umbral MEDIUM.

---

## Hallazgos

### 1. [MEDIUM] Ambigüedad de tipos en la comparación de autor para `excluir_propios` y `esPropio`

**Dónde:** §3.1 (regla de `excluir_propios`), §5 (fila `esPropio`), §6.2.

**Problema:** La regla de exclusión es `autorId == (request.autorId ?? usuario_actual.usuario_id)`.
Verificado en el código: `raw_data.id_owner` es `INTEGER` (schema §2) y
`usuario_actual.usuario_id` es `int` (ORM `Usuario`), pero `request.autorId` llega como
**string** (`RecomendarRequest.autorId: str | None`, §3.1 y §8.1). El diseño especifica
conversión de `instrumentoIds` str→int (§3.3) pero **no** especifica la coerción de tipos
para la comparación de autor. Una comparación `"3" == 3` en Python es `False`, lo que
silenciosamente nunca excluiría nada (o marcaría todo como no-propio). Lo mismo aplica a
`esPropio = raw_data.id_owner == usuario_actual.usuario_id` si en algún punto el owner
viajara como str desde el nodo.

**Fix concreto:** fijar la regla de normalización explícitamente en §3.1:
```python
# El autor efectivo se resuelve SIEMPRE a int antes de comparar.
autor_efectivo: int | None = (
    int(request.autorId) if request.autorId not in (None, "") else usuario_actual.usuario_id
)
# excluir candidatos: raw_data.id_owner (int) == autor_efectivo (int)
```
Y declarar que `autorId` no convertible a int → 422 (ya lo dice §3 para `autorId`, pero sin
unirlo a esta comparación). Documentar que `esPropio` y la exclusión operan ambos en el
espacio `int` del `usuario_id`.

---

### 2. [MEDIUM] El umbral `UMBRAL_ALTO = 0.5` de la etiqueta `razon` es una decisión que la spec no fija y que no está justificada numéricamente

**Dónde:** §2.3.

**Problema:** La spec §3 define las tres razones pero solo dice "ambas altas → Alta afinidad",
sin definir qué es "alta". El diseño elige `0.5` sobre el score crudo de cada señal. La
elección es razonable y el diseño explica *por qué sobre el score crudo y no ponderado*
(bien), pero el valor `0.5` aparece sin referencia ni configurabilidad. Como `razon` es un
campo **del contrato observable** (el usuario lo ve), el umbral determina el comportamiento
visible y hoy es un literal mágico no parametrizable. Además hay una interacción con
`min_score = 0.15`: un candidato puede entrar al resultado con `score_kpi = 0.2` y
`score_semantico = 0.2` (ninguno ≥ 0.5), cayendo siempre en "Contenido similar" aunque
tenga KPIs compartidos reales, porque `score_semantico >= score_kpi` empata a favor de
"Contenido similar". Eso puede etiquetar como "Contenido similar" a un candidato cuyo único
vínculo real son KPIs.

**Fix concreto:** (a) exponer `UMBRAL_ALTO` como constante nombrada del módulo con comentario
que lo marque como ajustable (no mágico), y (b) cambiar el desempate para que, cuando hay
KPIs compartidos no vacíos y `score_semantico == score_kpi`, se prefiera "KPIs compartidos"
(señal concreta y explicable) sobre "Contenido similar":
```python
if alto_sem and alto_kpi:
    razon = "Alta afinidad (contenido + KPIs)"
elif score_kpi > 0 and score_kpi >= score_semantico:
    razon = "KPIs compartidos: " + ", ".join(kpis_compartidos)
elif score_semantico > 0:
    razon = "Contenido similar"
else:
    razon = "KPIs compartidos: " + ", ".join(kpis_compartidos)
```
Alternativamente, documentar que `0.5` es un valor de diseño aceptado y dejar el desempate
como está, pero entonces hay que justificar que empatar a favor de "Contenido similar" es
el comportamiento deseado. Cualquiera de las dos cierra la ambigüedad; elegir una.

---

### 3. [NIT] `sim_semantica` para candidatos fuera del top-K queda sin regla explícita de default

**Dónde:** §2.2.

**Problema:** El cálculo hace `|A|` queries con `K = len(acervo)` ("o un K generoso, p. ej.
`len(acervo)`"). Si se usa un K menor que el acervo, un candidato que no aparezca en los
resultados de ninguna query no tendría `sim_semantica` asignado. El diseño no fija qué pasa
en ese caso. Con `K = len(acervo)` el problema no ocurre, pero la frase "o un K generoso"
deja la puerta abierta a una K menor sin regla de default.

**Fix concreto:** fijar la regla: "un candidato sin resultado en ninguna query tiene
`sim_semantica = 0.0`" y usar `K = len(acervo)` (no "generoso") para garantizar cobertura
total con un acervo del tamaño objetivo (~30). Eliminar la frase "o un K generoso".

---

### 4. [NIT] El ejemplo de entrada del Sidebar usa sintaxis JSX que no coincide con el patrón real del archivo

**Dónde:** §8.3.

**Problema:** El diseño propone `{ to: "/grafo", etiqueta: "...", icono: <icono lucide> }`.
Verificado en `Sidebar.tsx`: `OPCIONES` guarda la **referencia al componente**
(`icono: Library`), no un elemento JSX, y se renderiza como `<Icono className="h-4 w-4" />`
tras desestructurar `icono: Icono`. Pasar `icono: <Share2 />` rompería ese renderizado. El
diseño acierta en no reutilizar `Network` (ya lo usa "Espacio vectorial"), pero el ejemplo
de forma es incorrecto.

**Fix concreto:** usar la referencia del componente, igual que las demás entradas:
```tsx
import { Share2 } from "lucide-react";
// ...
{ to: "/grafo", etiqueta: "Grafo de recomendación", icono: Share2 },
```

---

### 5. [NIT] Afirmación imprecisa: `espacio.py` no expone el seam `client=None` a nivel de función

**Dónde:** §2.5 ("igual que el seam ya existente en ... `espacio`") y §10.

**Problema:** El diseño cita a `espacio.py` como ejemplo del seam de inyección de cliente.
Verificado: `espacio.espacio_vectorial(usuario_actual)` **no** acepta `client`; internamente
llama `get_client()` y `get_or_create_collection(nombre, client=client)`. El seam real
(`get_or_create_collection(name, client=None)`) existe en `chroma_client.py` y lo usan
`kpi_search`/`espacio` *internamente*, pero `espacio` no lo expone en su firma. La propuesta
del diseño (exponer `client=None` en `recomendar()`) es correcta y sí tiene precedente en
`chroma_client`; solo la atribución a `espacio` es imprecisa.

**Fix concreto:** cambiar la referencia a "igual que el parámetro `client` de
`chroma_client.get_or_create_collection` / `delete_collection`" (que sí exponen el seam en su
firma), y dejar de citar `espacio` como ejemplo de seam a nivel de función.

---

### 6. [NIT] `fecha_creacion` en el ORM usa `datetime.utcnow` mientras el SQL usa `CURRENT_TIMESTAMP`

**Dónde:** §7.1 (SQL) vs §7.2 (ORM).

**Problema:** El SQL define `fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP` (hora del
servidor, con zona local del servidor Postgres), y el ORM define
`default=datetime.utcnow` (hora UTC calculada en Python). Como la tabla se crea por SQL y la
fila se inserta por ORM, el default efectivo será el de Python (UTC), nunca el de la columna.
Es exactamente el mismo patrón que ya usa `kpi_calculo.py` (verificado), así que es
*consistente con el repo*, pero mezcla dos relojes/zonas. No bloquea, pero es una
inconsistencia latente.

**Fix concreto:** aceptable mantener el patrón del repo (consistencia > pureza). Si se quiere
cerrar: usar `server_default=func.now()` en el ORM (como hace `kpi_inferido.fecha_inferencia`,
verificado) para que el default lo ponga Postgres y haya un solo reloj.

---

## Preguntas del gate (checklist)

| Pregunta del gate | Resultado |
|---|---|
| Score híbrido: pesos suman 1.0, defaults 0.6/0.4, min_score 0.15, top_n 10 | ✅ Concuerda con spec; suma 1.0 validada (tol. 1e-6) |
| `razon` labels exactas en español | ✅ Literales exactos de la spec; umbral de "alta" es decisión propia (ver #2) |
| Degradación fuerza `w_sem=0` + `degradado_semantico` | ✅ §2.4, verificado contra RNF-4 de la spec |
| Cliente Chroma inyectable | ✅ `recomendar(..., client=None)`; seam real en `chroma_client` (ver #5) |
| 3 endpoints request/response exactos | ✅ Con `idCrudo` aditivo y `degradado_semantico`; desviación de `/investigacion` justificada |
| Schema aditivo, no destructivo, dentro de la transacción | ✅ Verificado: dentro de `BEGIN;…COMMIT;`, tras `kpi_calculo`, antes de Índices |
| Decisión `/rag/index` concreta y justificada | ✅ Frontend llama; `guardarContexto` existe y postea a `API_URL/rag/index` |
| Espeja `kpi_search.py`, no duplica vectores | ✅ Reutiliza `get_point`/`query`/`_distance_to_score`; única pieza nueva es Jaccard |
| Contrato frontend completo (api/grafo.ts, React Flow, sidebar, 100% ES) | ✅ Completo; ejemplo de sidebar con forma incorrecta (ver #4) |

---

## Suposiciones verificadas (correctas)

1. **Dos espacios de ID (§1, §9-D):** VERIFICADO. `kpi_inferido.id_procesado` es FK a
   `instrumento_procesado.id_instrumento` (schema §10 + `kpi_inferido.py`);
   `summary_instrument` se indexa con `str(id_instrumento)` (`kpi_search.index_summary`);
   `/rag/index` resuelve por `id_crudo` (`sources._resolver_desde_bd`: docstring literal
   "clave = `str(id_crudo)`" y `where(InstrumentoProcesado.id_crudo == id_crudo)`). El
   hallazgo crítico es real.
2. **Entrypoint y routers (§4, §9-A):** VERIFICADO. `services/analysis-service/main.py` es el
   entrypoint; routers se importan con `from app.vectorization.routers import ...` y se
   registran con `app.include_router(...)`.
3. **Patrón de auth del router (§4):** VERIFICADO. `UsuarioActual`/`DBSession` en
   `app.vectorization.dependencies`; `AUTH_DEV_MODE` resuelve `DEV_USER_ID` sin token.
4. **Llamada directa a `ANALYSIS_URL` (§6):** VERIFICADO. `espacio.ts` y el docstring de
   `kpi_calculo.py` confirman que el gateway no proxea estas rutas; `client.ts` expone
   `ANALYSIS_URL`.
5. **`pedir()` (§8.1):** VERIFICADO. Firma `{method, body, auth}`, mapea errores a mensajes
   en español, `auth:false` no adjunta token. Concuerda con el uso en `grafo.ts`.
6. **`IndexRequest`/`IndexResponse` (§6.3, §9-E):** VERIFICADO. `IndexRequest` =
   `{investigacionId, instrumentoIds, reindexar}`; `IndexResponse` =
   `{coleccion, total_chunks, instrumentos, mensaje}` — **sin** `ok`. El diseño lo corrige
   bien (el `ok` es de `/grafo/investigacion`).
7. **`_clamp_top_k` del RAG (§3):** VERIFICADO. `max(1, min(20, v))`, dominio = chunks del
   chat, distinto del `top_n` de instrumentos del grafo.
8. **Schema aditivo dentro de la transacción (§7.1):** VERIFICADO. El bloque
   `BEGIN;…COMMIT;` existe; `kpi_calculo` es el último `CREATE TABLE` antes de la sección de
   índices; `search_path TO tt_rag, public` permite referenciar `usuario(usuario_id)` sin
   cualificar.
9. **`map_instrumento.mapear_tipo` (§5, §9-C):** VERIFICADO. `_TIPO_MAP` =
   `{encuesta, entrevista, prueba_estandarizada}`, default "Encuesta" + `logger.warning`,
   keyed sobre `raw_data.tipo_instrumento` lowercase-snake. El helper replicado en el diseño
   es idéntico. `sources._mapear_tipo` sí parte de `dc:type` y cae a "Encuesta" (menos fiable),
   como afirma el diseño.
10. **`raw_data` como fuente de nodo (§5):** VERIFICADO. `tipo_instrumento` (NOT NULL),
    `id_owner`, `nombre_archivo` existen; `metadatos_dc.dc_title` y `usuario.nombre` existen
    para `titulo`/`autorNombre` por los JOINs descritos.
11. **Registro del ORM (§7.2):** VERIFICADO. `shared/models/__init__.py` registra cada tabla
    por import + `__all__`; el modelo nuevo debe sumarse ahí. El estilo ORM 2.0
    (`Mapped`/`mapped_column`, `SCHEMA`, `JSONB`, FK cualificada con `{SCHEMA}.`) coincide con
    `kpi_calculo.py`/`kpi_inferido.py`.
12. **No duplica lógica de vectores (§10):** VERIFICADO. `_distance_to_score`,
    `chroma_client.query`, `get_point`, `get_or_create_collection(name, client=...)` existen y
    son reutilizables; `espacio.py` confirma la alternativa numpy (`collection.get(
    include=["embeddings"])` + PCA) que el diseño cita como descartada.
13. **Flujo de chat / `guardarContexto` (§6.3):** VERIFICADO. `chat.ts::guardarContexto`
    persiste en cliente y hace `POST ${API_URL}/rag/index` con `{investigacionId,
    instrumentoIds}` (ids = `str(id_crudo)`, comentado en el propio archivo).

---

## Suposiciones no verificadas / incorrectas

1. **[Incorrecta, menor]** El seam `client=None` atribuido a `espacio` (§2.5, §10) no existe a
   nivel de la firma de `espacio_vectorial`; el seam real está en
   `chroma_client.get_or_create_collection`/`delete_collection`. Ver hallazgo #5.
2. **[Incorrecto, menor]** El ejemplo de entrada del Sidebar con JSX (`icono: <icono lucide>`)
   no coincide con el patrón real (referencia de componente). Ver hallazgo #4.
3. **[No verificada, reconocida por el diseño — §9-F]** Cobertura de datos: que los
   instrumentos sembrados tengan simultáneamente vector en `summary_instrument` y filas en
   `kpi_inferido`. No es verificable por lectura de código (depende del estado de BD/Chroma de
   pruebas). El diseño ya la marca como "a confirmar en verificación" y degrada con gracia
   (sin vector → no puntúa semántico; sin KPIs → `solape_kpi = 0`). No bloquea el diseño pero
   condiciona el gate de aceptación §9 de la spec.
4. **[No verificada, operativa — §9-B]** Que `01_schema.sql` solo corre en init de volumen
   limpio es correcto como comportamiento de los init scripts de la imagen de Postgres; el
   diseño lo reconoce y pide un paso operativo en el PLAN (ejecutar el `CREATE TABLE IF NOT
   EXISTS` a mano o recrear el volumen). Correcto, no bloquea el diseño.
5. **[Latente, consistente con el repo — §7.2]** El default de `fecha_creacion` será el de
   Python (`datetime.utcnow`), no el `CURRENT_TIMESTAMP` del SQL. Ver hallazgo #6.

---

## Veredicto

**CHANGES_REQUESTED.**

Conteo mecánico: **2 MEDIUM** (#1 ambigüedad de tipos en comparación de autor; #2 umbral/
desempate de `razon`) y **4 NIT** (#3, #4, #5, #6). Como hay más de cero hallazgos HIGH/MEDIUM,
el veredicto es CHANGES_REQUESTED. Ninguno invalida la arquitectura; son cierres de ambigüedad
y correcciones de atribución que evitan bugs silenciosos (sobre todo #1) y dejan el documento
listo para implementación sin interpretación del coder.
