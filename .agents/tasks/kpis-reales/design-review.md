# Revisión de diseño — Integración de KPIs reales (kpis-reales)

Revisor: subagente de revisión de diseño (lectura en frío, sin el contexto que produjo el diseño).
Fuente revisada: `.worktrees/kpis-reales/.agents/tasks/kpis-reales/design.md` (iteración 4) y
`requirements.md`. Todas las afirmaciones del diseño sobre el código se verificaron **leyendo el
código real** del worktree.

## Veredicto

CHANGES_REQUESTED — 1 MEDIUM + 3 NIT. (El veredicto es mecánico: >0 HIGH/MEDIUM ⇒ CHANGES_REQUESTED.)

El diseño está, en lo sustancial, muy maduro: resuelve correctamente los riesgos de más peso que el
prompt pidió vigilar (re-seed programático desde CSV, `kpi_id` sigue siendo SERIAL PK, embedding =
solo `texto_contexto_rag_vectorial`, reconciliación de **todos** los lectores de columnas/metadatos
viejos, endpoint de catálogo coherente con cómo lo llama el frontend, íconos solo del mapa Lucide
existente). El único hallazgo bloqueante es una ambigüedad concreta en el *seam* de inyección de la
reindexación; el resto son NIT.

---

## Hallazgos

### 1. [MEDIUM] El *seam* de inyección de `reindex_kpis` queda ambiguo frente al nuevo `delete_collection`+recrear

**Dónde:** §3.2 y §3.6 del diseño; `services/analysis-service/app/vectorization/core/kpi_indexer.py`
(`reindex_kpis(db, *, collection=None)`).

**Problema.** Hoy `reindex_kpis` resuelve la colección así (verificado en el código):

```python
coleccion = collection or chroma_client.get_or_create_collection(settings.CHROMA_COLLECTION_KPIS)
```

§3.2 ordena que, **antes del upsert**, el reindex haga `client.delete_collection(nombre)` y luego
`get_or_create_collection(...)` para recrear. Pero el contrato de inyección actual pasa un **objeto
`collection`**, no un `client` ni un `nombre`. El diseño no especifica qué ocurre cuando se inyecta
`collection` (ruta de tests): ¿se ignora el `delete_collection` (y entonces la colección inyectada
no se purga, dejando puntos huérfanos y falseando la prueba de §3.6 "verificar que delete_collection
+ recrear deja 55 puntos")? ¿O el `delete_collection` opera sobre el nombre fijo
`CHROMA_COLLECTION_KPIS` aunque se haya inyectado otra colección (incoherente)? §3.6 menciona
"inyección de `collection`/`client`" sin fijar cuál usa el reindex, de modo que hay **dos
interpretaciones válidas** y la prueba de integración podría no ejercitar realmente el borrado.

**Por qué importa.** FR-3.5 / CA-4 / CA-6 dependen de que la purga ocurra de verdad (exactamente 55
puntos, sin huérfanos). Un seam mal especificado puede producir una implementación que pase los
tests sin ejercitar el borrado, y el bug (puntos huérfanos del catálogo viejo) solo aparecería en
runtime real.

**Fix concreto.** Fijar la firma y el orden explícitamente. Opción recomendada: inyectar **client**
(no collection) y recrear siempre por nombre dentro de `reindex_kpis`:

```python
def reindex_kpis(db: Session, *, client=None) -> ReindexResult:
    cli = client or chroma_client.get_client()
    nombre = settings.CHROMA_COLLECTION_KPIS
    chroma_client.delete_collection(nombre, client=cli)          # idempotente (traga "no existe")
    coleccion = chroma_client.get_or_create_collection(nombre, client=cli)
    kpis = db.query(KPI).order_by(KPI.kpi_id).all()
    ...
    chroma_client.upsert(coleccion, ids, vectores, textos, metadatas)
```

y actualizar la llamada del router `reindex_kpis(db)` (sin `collection=`). Si por compatibilidad se
quiere conservar `collection=`, el diseño debe decir explícitamente que, cuando se inyecta
`collection`, el reindex **igualmente** llama `delete_collection(nombre, client=...)` recreando por
nombre y descartando el objeto inyectado — pero esto es contradictorio y es más limpio migrar el
seam a `client`. En cualquier caso, la prueba de §3.6 debe inyectar `client` para que el borrado se
ejercite de verdad. Añadir §3.2 la firma final y a §6 la nota de que la llamada del router pierde el
argumento posicional.

---

### 2. [NIT] `derivarEtiquetas`/`elegirIcono`: normalización de acentos no está fijada como regla verificable

**Dónde:** §5.2 (`derivarEtiquetas`) y §5.3 (`elegirIcono`), `pixel-perfect-pixel/src/api/kpis.ts`.

**Problema.** §5.3 dice que la heurística opera "en minúsculas, sin acentos" sobre el nombre, pero
los nombres reales del CSV traen acentos (verificado: p. ej. "Estado de Acreditación…",
"Selectividad de Admisiones"). La regla de `polaridad_rendimiento` en §5.2 usa
`match(/^[A-ZÁÉÍÓÚÑ]+/)` (sí contempla acentos), pero `elegirIcono` solo dice "sin acentos" sin fijar
**cómo** se quitan. Dos implementadores podrían diferir (quitar acentos con
`normalize("NFD").replace(/\p{Diacritic}/gu,"")` vs. no quitarlos), y las claves de la heurística
(`acredit`, `graduaci`, `ensenanza`, `tecnolog`…) ya están escritas sin acentos, por lo que **sin**
la normalización varias ramas nunca disparan y todo cae a `BarChart2`.

**Por qué importa.** No rompe CA-7 (el fallback `BarChart2` siempre es válido), pero degrada la
calidad del mapeo de íconos de forma silenciosa.

**Fix concreto.** Fijar en §5.3 la normalización exacta antes de comparar:
`const n = nombre.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");` y comparar las
claves contra `n`. Añadir un caso de prueba unitario con un nombre acentuado (p. ej.
"Acreditación") que debe resolver a `Award`, no al fallback.

---

### 3. [NIT] El seam `reindex_kpis` también afecta la prueba unitaria de "sin None" de metadata

**Dónde:** §3.6 (testabilidad) y §3.1.

**Problema.** §3.1 reescribe el dict de metadata con `or ""`. §3.6 lista como unit test "construcción
del dict de metadata (sin `None`)", pero el dict se construye **inline** dentro de `reindex_kpis`
(verificado en el código actual), no en una función pura extraíble. Tal como está, no hay unidad
testeable sin levantar la ruta completa de reindex. El diseño no decide si extraer la construcción
del metadato a una función pura (como sí hace con `leer_kpis_csv` en §1.5 y `mapearKpi` en §5.5).

**Fix concreto.** Decidir explícitamente: extraer `build_kpi_metadata(kpi: KPI) -> dict` como función
pura (igual que `build_kpi_text`) para que §3.6 tenga una unidad real que probar, o bien reformular
§3.6 para que esa verificación sea parte de la prueba de integración del reindex (y no se liste como
"unit"). Preferible lo primero por simetría con el resto del diseño.

---

### 4. [NIT] Falta nota operativa de que la `secuencia` de `kpi_id` también se reinicia en el flujo on-demand con `DROP TABLE`

**Dónde:** §1.4 (comando on-demand para BD ya levantada).

**Problema.** §1.1/§1.3 garantizan IDs contiguos 1..55 vía `TRUNCATE ... RESTART IDENTITY`. En el
flujo on-demand §1.4 propone, cuando no se recrea el volumen, `DROP TABLE IF EXISTS tt_rag.kpi
CASCADE` + re-`CREATE`. Eso recrea la secuencia `SERIAL` desde 1 (correcto), pero el diseño no
menciona que el `DROP ... CASCADE` **elimina las constraints FK de las tablas hijas** y que esas FKs
solo se recrean si se re-corre `01_schema.sql` completo (que es `CREATE TABLE IF NOT EXISTS`, es
decir, no recreará las hijas que ya existen, por lo que sus FKs hacia `kpi` quedarían **sin
recrear**). El propio diseño ya reconoce esto ("por eso en una BD viva se prefiere recrear el
volumen"), pero lo deja como preferencia, no como advertencia dura. Un operador que elija el camino
`DROP TABLE` a mano podría quedarse con las tablas hijas **sin** su FK hacia `kpi(kpi_id)`,
contradiciendo CA-3 (FK intactas) sin que nada lo detecte.

**Por qué importa.** CA-3 exige FKs válidas tras el reseed; el camino on-demand manual puede violarlo
silenciosamente.

**Fix concreto.** En §1.4, marcar el `DROP TABLE … CASCADE` manual como **desaconsejado** (no solo
"menos preferido") y, si se usa, exigir recrear explícitamente las constraints FK de
`kpi_variable`, `kpi_inferido`, `valor_variable_inferido` y `kpi_inferido_chunk` tras el nuevo
`CREATE TABLE kpi`, o directamente prescribir recrear el volumen como **único** camino soportado en
pruebas. Alternativa más limpia: usar `TRUNCATE ... RESTART IDENTITY CASCADE` (que no toca
constraints) incluso para el cambio de forma no es posible porque cambian columnas; por eso lo
correcto es documentar que el único camino sin riesgo de FK es recrear el volumen.

---

## Supuestos verificados (leídos contra el código)

- **`shared/models/kpi.py`** tiene hoy exactamente las 6 columnas viejas
  (`nombre_kpi, descripcion, categoria, ambito, url_documentacion, formula`) + `kpi_id` PK
  autoincremental. ✓ (coincide con §2)
- **`shared/schemas/kpi.py`** usa los nombres viejos y su docstring afirma "Refleja 1:1 la tabla
  tt_rag.kpi"; `KPIRead` usa `from_attributes=True`. ✓ (justifica §2.1; quedaría inconsistente si no
  se reescribe)
- **`shared/schemas/__init__.py`** exporta `KPIBase/KPICreate/KPIUpdate/KPIRead` en `__all__`. ✓ (los
  nombres no cambian ⇒ `__init__.py` no se toca, como dice §6)
- **`01_schema.sql`**: `kpi` es `kpi_id SERIAL PRIMARY KEY` + 6 columnas viejas. Las 4 tablas hijas
  (`kpi_variable`, `kpi_inferido`, `valor_variable_inferido` vía `kpi_inferido`, `kpi_inferido_chunk`
  vía `kpi_inferido`) referencian `kpi(kpi_id)` con `ON DELETE CASCADE`. ✓ (confirma que un
  `TRUNCATE … CASCADE` vacía las hijas sin dropear constraints, CA-3; y confirma el riesgo del
  Hallazgo 4 en el camino `DROP TABLE`)
- **`kpi_indexer.py`**: `build_kpi_text` concatena nombre+descripcion+categoria+ambito (debe
  reducirse a solo RAG); metadata usa `kpi_id, nombre_kpi, categoria, ambito`. ✓ (coincide con §3.1)
- **`kpi_search.py`**: `KpiMatch(kpi_id, nombre_kpi, categoria, ambito, score)` y `search_kpis` lee
  `meta.get("nombre_kpi"/"categoria"/"ambito")`. ✓ (coincide con §3.3)
- **`proposal_service.py`**: construye `PropuestaKPI(kpi_id, nombre_kpi, categoria, ambito, score)`. ✓
- **`enrichment_service.py`**: lee `kpis[d.kpi_id].nombre_kpi` y escribe la clave `inferred_kpis` con
  `"nombre_kpi"`. ✓ (ambos puntos listados en §3.3/§3.4)
- **`espacio.py`** y **`infrastructure/chroma-viewer/app.py`**: ambos `_label_for` rama `kpis` leen
  `meta.get("nombre_kpi")`. ✓
- **`schemas/vectorizacion.py`**: `PropuestaKPI(nombre_kpi, categoria, ambito)` y
  `KpiAgregado(nombre_kpi)` existen tal como dice §3.4. ✓
- **`main.py`**: importa `from app.vectorization.routers import espacio, health, vectorizacion` y
  registra 3 routers. ✓ (confirma que registrar `kpis` exige **dos** ediciones, §4.2)
- **No hay colisión de ruta**: `vectorizacion.py` expone `POST /vectorizacion/kpis/reindex`; el nuevo
  router expondría `GET /vectorizacion/kpis/catalogo`. Método y path distintos. ✓
- **`UsuarioActual`** existe en `app/vectorization/dependencies.py` y las rutas hermanas
  (`espacio`, `vectorizacion`) lo usan. ✓ (justifica el guard elegido en §4.2)
- **`instrument-service/app/routers/list.py`**: `GET /instrumentos/kpis/catalogo` → `list[str]`
  existe y está declarado antes de `/{id:int}`. ✓ (se conserva intacto, §4.1)
- **`client.ts`**: `ANALYSIS_URL` existe (`VITE_ANALYSIS_URL ?? http://localhost:8002`). ✓ (el
  frontend puede llamar directo, §5.1)
- **`carga.ts`**: declara interfaces locales `PropuestaKPI { nombre_kpi, categoria?, ambito? }` y
  `KpiAgregado { nombre_kpi }`, y las lee en `proponerKpis` (`p.nombre_kpi`) y `confirmarKpis` (ambas
  ramas, `k.nombre_kpi`). El build de TS no detectaría la rotura (interfaces locales). ✓ (confirma el
  Hallazgo HIGH de la iteración 3, ya atendido en §3.4/§5.1/§6)
- **`kpis.ts`**: hoy emite `icono: "ChartBar"` (inválido) y llama `API_URL/instrumentos/kpis/catalogo`
  (list[str]). ✓ (justifica la reescritura de §5.1–5.3)
- **`TarjetaKpi.tsx` / `DetalleKpi.tsx`**: el mapa `ICONOS` contiene exactamente las 15 claves
  listadas en requisitos/diseño (`Award, BarChart2, BookOpen, Briefcase, Calculator, ClipboardCheck,
  Heart, Home, Laptop, MessageCircle, Monitor, Shield, Smile, Users, Zap`), con fallback `?? BarChart2`
  en ambos componentes. ✓ (confirma que `ChartBar` nunca existió y que el conjunto de §5.3 es exacto)
- **`src/types/index.ts`**: `KpiCatalogo` tiene todos los campos del mapeo (`id, nombre,
  descripcionCorta, queEs, queMide, comoSeMide, formula, infoGeneral, icono, etiquetas`). ✓ (no se
  toca el tipo, §6)
- **`seed_demo.py`**: vive en `services/instrument-service/scripts/` y usa `parents[3]` para la raíz
  del repo. El `seed_kpis.py` propuesto vive en `services/analysis-service/scripts/` (misma
  profundidad), por lo que `parents[3]` es correcto. ✓ (confirma §1.3)
- **CSV `infrastructure/postgres/seed/kpis_ampliados.csv`** leído con `csv.DictReader(utf-8-sig)`:
  **55 filas** de datos, **8 columnas** en el orden exacto afirmado, **0** valores vacíos en
  `Texto_Contexto_RAG_Vectorial`, **55 nombres únicos**. ✓ (confirma CA-1 y que el "46" del usuario es
  erróneo; el CSV manda)
- **CSV aún NO está dentro del worktree** `.worktrees/kpis-reales/infrastructure/postgres/seed/`. ✓
  (el diseño lo marca como primer paso de §6: copiarlo/versionarlo antes del seed)
- **`_disabled/04_seed.sql`** existe y está deshabilitado. ✓ (queda obsoleto, §1.2)

## Supuestos no verificados / incorrectos

Ninguna afirmación del diseño resultó **falsa** al contrastarla con el código. Puntos que el diseño
reconoce como no verificables en esta fase (no son errores):

- El CSV debe **copiarse** al worktree antes del seed; a la fecha de la revisión no está (verificado).
  El diseño ya lo trata como paso de implementación (§6, primer ítem) y el script aborta limpio
  (exit code 2) si corre antes de la copia (§1.3).
- El comportamiento en runtime de `delete_collection`+recrear sobre una Chroma real no se ejecutó en
  esta revisión (es un gate de verificación en runtime, CA-4/CA-6); el Hallazgo 1 apunta a que el
  *diseño* del seam debe quedar inequívoco para que esa verificación sea significativa.
