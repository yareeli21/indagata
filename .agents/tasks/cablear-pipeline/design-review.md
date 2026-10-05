# Revisión en frío — Diseño "Cablear el pipeline de carga (pasos 1-4)" (iteración 2)

Revisión independiente del documento `design.md` sin el contexto que lo produjo.
Cada afirmación concreta (endpoints, firmas, mapeos, shapes ORM, patrón de proxy) se
verificó leyendo el código real en el worktree
`c:\Users\yarel\Documents\indagata\indagata\.worktrees\cablear-pipeline`.

Veredicto mecánico: 0 HIGH, 0 MEDIUM, 3 NIT → **APPROVED** (sólo HIGH/MEDIUM bloquean;
ningún hallazgo se degradó para desbloquear).

---

## Resumen

El diseño es inusualmente sólido en su verificación de fondo: casi todas sus
afirmaciones concretas resisten la lectura directa del código. En particular:

- Los endpoints citados existen con las firmas que el diseño describe
  (`/instrumentos/upload`, `/api/metadata/metadata/{id}/...`, `/vectorizacion/propuestas`,
  `/vectorizacion/confirmar`, `/instrumentos/kpis/catalogo`).
- El BLOCKER de `dc_manager` (§4.0) es real y está correctamente diagnosticado:
  `dc_manager.py` referencia atributos ORM inexistentes y fallaría con 500.
- Los mapeos (`parseo→ReporteLimpieza`, `PropuestaKPI→KpiSugerido`, `list[str]→KpiCatalogo`)
  están anclados en los tipos reales de `src/types/index.ts` y en los schemas Pydantic.
- El patrón de proxy propuesto replica exactamente la iteración 1.
- Todo permanece en español; las firmas exportadas se conservan; los pasos sin backend
  quedan mock con TODO explícito; no se inventan endpoints.

Los 3 NIT son imprecisiones menores que no cambian ninguna decisión de implementación.

---

## Hallazgos

### 1. [NIT] §4.5 — la frase "acepta vacío/null y responde 200" es imprecisa para `dc_title`

**Dónde:** §4.5, línea "Hecho verificado: `register_dc` recibe `request: dict` … acepta
vacío/`null` y responde **200**. **No hay 422.**"

**Problema:** La afirmación es correcta para `dc_subject` (nullable, se persiste `[]`),
pero **no** para `dc_title`. Verificado:
- `shared/models/metadatos_dc.py` → `dc_title: Mapped[str] = mapped_column(Text, nullable=False)`.
- `infrastructure/postgres/init/01_schema.sql` → `dc_title TEXT NOT NULL`.

`register_dc` hace `dc_title=request.get("dc_title")`; si el campo se **omite**, se
inserta `None` → `IntegrityError` → el router lo captura en su `except Exception` genérico
y responde **500**, no 200. (Una cadena vacía `""` sí entraría, porque `NOT NULL` sólo
bloquea `NULL`.) En la práctica esto no ocurre porque `puedeContinuar[2]` del wizard exige
`dc.titulo.trim()`, de modo que el POST siempre lleva un título no vacío — y el propio
diseño documenta correctamente esa guarda local en la tabla de errores. Por eso es NIT y
no bloquea.

**Fix concreto:** Acotar la frase: "`register_dc` no valida obligatoriedad vía Pydantic;
`dc_subject` vacío/omitido se persiste con 200. `dc_title` es `NOT NULL` en modelo y DDL:
si se omite (→ `None`) la inserción falla con 500; una cadena vacía `""` sí se persiste.
En la práctica el wizard garantiza `dc_title` no vacío (`puedeContinuar[2]`), así que el
caso 500-por-título-nulo no se alcanza desde la UI."

### 2. [NIT] §11.2 — la suposición "DDL de `metadatos_dc` no verificado" ya es verificable y resulta correcta

**Dónde:** §11.2 y §4.0 (nota "⚠️ Suposición a confirmar: … No se leyó el DDL de
`metadatos_dc`; se marca como pendiente.").

**Problema:** El DDL **sí** está en el repo
(`infrastructure/postgres/init/01_schema.sql`) y se puede leer. Verificado: la tabla
`metadatos_dc` tiene `id_crudo INTEGER PRIMARY KEY REFERENCES raw_data(id_crudo)`, es
decir **coincide** con el modelo `shared` (`id_crudo` como PK). La suposición es, de hecho,
cierta, pero dejarla como "pendiente" subestima lo que ya se puede confirmar y podría
llevar al implementador a tratar como riesgo algo ya resuelto.

**Fix concreto:** Cambiar §11.2 de "pendiente" a verificado: "DDL de `metadatos_dc`
confirmado en `infrastructure/postgres/init/01_schema.sql`: `id_crudo INTEGER PRIMARY KEY
REFERENCES raw_data(id_crudo)` — coincide con el modelo `shared.MetadatosDC`. El arreglo
de `dc_manager` (filtrar/crear por `id_crudo`) es consistente con el esquema real." Esto
refuerza, no debilita, la decisión del §4.0.

### 3. [NIT] §6.4 / §11.3 — contrato de storage-service no verificado, pero el router existe y es legible

**Dónde:** §6.4 ("`storage-service` … el contrato `POST /almacenamiento/json?tipo=analysis`
**no está verificado** (no se leyó el router de storage-service)") y §11.3.

**Problema:** La decisión de **no** cablear `guardarInstrumento` a storage (y devolver el
id real con un TODO) es razonable y honesta — no bloquea. Pero el diseño deja el contrato
como caja negra cuando el servicio está presente en el worktree
(`services/storage-service/`). Como `guardarInstrumento` no se cablea en esta iteración, la
omisión no tiene impacto funcional; de ahí NIT.

**Fix concreto:** Opcional pero recomendado: una línea en §6.4 indicando la ruta del router
real a consultar cuando se decida cablear (`services/storage-service/...`), o afirmar
explícitamente que se difiere la lectura a la iteración que efectivamente cablee storage.
No es necesario para aprobar esta iteración.

---

## Suposiciones verificadas (confirmadas contra el código real)

1. **`POST /instrumentos/upload`** — `instrument-service/app/routers/upload.py`: multipart,
   `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)` (requiere Bearer), campos `archivo`
   (UploadFile, req), `tipo_instrumento` (Form str, req), `archivo_original` (UploadFile,
   opcional). 201. ✔ Coincide con §2.1.
2. **`UploadResponse`** — `app/schemas/upload.py`: devuelve **ambos** `id_crudo` e
   `id_instrumento`, `archivo_respondido: ArchivoRegistrado` con `parseo: ParseoArchivo|null`
   (tabular: `headers/n_columns/n_rows/preview_rows/sheet`; documento:
   `n_chars/n_words/n_pages/text_preview`; comunes: `encoding/notes[]`). ✔ Coincide con §2.1.
3. **Extensiones y tipos** — `app/config/constants.py`: `.csv/.xlsx/.xls` (tabular) +
   `.pdf/.txt/.docx` (documento), 100 MB, enum `encuesta|entrevista|prueba_estandarizada`.
   **No** acepta `.md/.json`. ✔ Coincide con §2.3, §2.4, §2.6.
4. **Modelos ORM** — `shared/models/`:
   - `RawData` PK `id_crudo`; tiene `tipo_instrumento`, `nombre_archivo`, `raw_archivo`,
     `raw_archivo_original`, `id_owner`, `fecha_carga`. ✔
   - `InstrumentoProcesado` PK `id_instrumento`, FK `id_crudo`; tiene
     `ruta_de_archivo_limpio`, `ruta_json`, `estado`, `fecha_procesamiento`,
     `fecha_aprobado`. **No** tiene `instrumento_id`, `nombre`, `archivo_nombre`,
     `tipo_instrumento`, `ruta_archivo`. ✔ Coincide con §1.1 y confirma el BLOCKER §4.0.
   - `MetadatosDC` PK `id_crudo` (no `instrumento_id`). ✔
5. **BLOCKER §4.0 (`dc_manager.py`)** — Verificado línea a línea: usa
   `InstrumentoProcesado.instrumento_id`, `instrumento.ruta_archivo`,
   `instrumento.tipo_instrumento`, `instrumento.nombre`, `instrumento.archivo_nombre`,
   `MetadatosDC.instrumento_id`, y en `register_dc` setea `instrumento.nombre`. Todos
   inexistentes → `AttributeError`/500 contra el esquema real. ✔ Diagnóstico correcto.
   `get_initial_data` hardcodea `usuario_nombre = "Sistema"` → `dc_creator: "Sistema"`;
   `register_dc` lee `request.get("dc_creator", "Sistema")` y `request.get("dc_subject",
   [])`. ✔ Coincide con §4.3/§4.4.
6. **Rutas de metadata (doble segmento)** — `routers/metadata.py` usa
   `APIRouter(prefix="/metadata")` con `@router.get("/metadata/{instrumento_id}/init")`,
   `@router.post("/metadata/{instrumento_id}")`, etc.; `main.py` monta con `prefix="/api"`.
   Composición real `/api/metadata/metadata/{instrumento_id}/...`. Endpoints dependen sólo
   de `get_db` (sin auth). ✔ Coincide con §4.1, §4.2.
7. **`/vectorizacion/propuestas`** — `analysis-service/.../routers/vectorizacion.py`:
   multipart, campos `archivo_json` (UploadFile), `instrumento_original` (UploadFile),
   `tipo_instrumento` (Form str), `id_instrumento` (Form int). Respuesta
   `PropuestasResponse{id_instrumento, tipo_instrumento, metadatos_clave,
   propuestas[{kpi_id, nombre_kpi, categoria?, ambito?, score}], mensaje}`. ✔ Coincide §6.1.
8. **`/vectorizacion/confirmar`** — JSON `ConfirmarRequest{id_instrumento, decisiones[{kpi_id,
   aceptado, score?}], json_instrumento}`; `ConfirmarResponse{id_instrumento,
   kpis_agregados[{kpi_id, nombre_kpi, score?}], json_enriquecido, mensaje}`. ✔ Coincide §6.3.
9. **Auth dev-mode** — `vectorization/dependencies.py` + `shared/db/core/config.py`:
   `AUTH_DEV_MODE=True`, `DEV_USER_ID=1`; `get_current_user` resuelve el usuario sin token.
   `espacio.ts` ya llama `/vectorizacion/*` directo a `ANALYSIS_URL` con `auth:false`. ✔
   Coincide con §6.1.
10. **`/instrumentos/kpis/catalogo`** — `instrument-service/app/routers/list.py`: devuelve
    `list[str]`, exige `require_rol(...)` (auth), y `GET /instrumentos/{id}` usa `id_crudo`.
    ✔ Coincide con §7.1 y §1.1 (por eso `getCatalogoKpis` usa `auth:true`).
11. **Tipos frontend** — `src/types/index.ts`: `TIPOS_INSTRUMENTO=["Encuesta","Entrevista",
    "Prueba estandarizada"]`; `ReporteLimpieza{duplicadosEliminados, nulosTratados,
    columnasNormalizadas, cambios}`, `CambioLimpieza{campo, antes, despues}`;
    `KpiSugerido{id, nombre, coincidencia}`; `KpiCatalogo{id, nombre, descripcionCorta,
    queEs, queMide, comoSeMide, formula, infoGeneral, icono, etiquetas[]}`;
    `DublinCore{titulo, creador, tema, descripcion, fecha, idioma, derechos,
    cobertura: NivelEducativo|""}`. ✔ Coinciden con §2.3, §3.2, §6.2, §7.1, §4.4.
12. **`carga.ts` actual** — Exporta `limpiarArchivo(_archivo: File)`,
    `getKpisSugeridos(_descripcion: string)`, `guardarInstrumento(documento: unknown)`, los
    tres mock. ✔ Firmas que el diseño promete conservar coinciden.
13. **`client.ts`** — `API_URL` (:8000), `ANALYSIS_URL` (:8002), `pedir()` fuerza
    `Content-Type: application/json`, `leerToken()`, `ErrorHttp.status`, 401→"Usuario o
    contraseña incorrectos". ✔ Coincide con §0 y §2.5.
14. **`UploadWizard.tsx`** — 7 entradas en `PASOS`, estado `paso` 0..6, "Paso {paso+1} de 7".
    `useEffect`: `if (paso===1 && archivo && !reporte) limpiarArchivo(...).then(setReporte);
    if (paso===5 && !sugeridos) getKpisSugeridos(dc.descripcion).then(setSugeridos);`.
    `puedeContinuar[2] = !!dc.titulo.trim() && !!dc.creador.trim() && !!dc.descripcion.trim()
    && !!dc.cobertura` (**`dc.tema` NO está** en la guarda). `dc.creador` default
    `usuario?.nombre ?? ""`. `decisiones: Record<string, DecisionKpi>`. ✔ Coincide con §0.1,
    §3.1, §4.3, §4.5, §6.1, §8, §8.a — incluida la corrección MEDIUM-1 (tema no guardado).
15. **Patrón de proxy (iteración 1)** — `api-gateway/proxy/proxy.py`: `proxy_request` reenvía
    status+body transparentes, `_ruta_upstream(prefijo, path)` sin barra final, rutas base +
    `{path:path}` para evitar 307, Authorization conservado (`_HEADERS_A_QUITAR` sólo quita
    host/content-length). `SERVICES["metadata"]="http://metadata-service:8003"`. El docstring
    dice explícitamente que metadata "NO se proxea" (confirma el NIT-6 del propio diseño).
    ✔ El bloque propuesto en §5.1 replica el patrón exacto.
16. **`espacio.ts`** — precedente de llamada directa a `ANALYSIS_URL` con `auth:false`. ✔
    Coincide con la justificación de §5.2/§6.1.
17. **inst_01** — `storage/raw/inst_01.v1.json`: `metadata.dublin_core["dc:subject"]` es el
    string `"calidad académica, exigencia, estándares, …"` (coma-separado); `q9`/`q10` abiertas
    con `answers` `null`. `inst_01.md` es el instrumento original (sólo preguntas). ✔ Coincide
    con §3.2, §4.4, §8.b.
18. **`seed_demo.py`** — `seed_map[inst] = raw.id_crudo` (mapea a `id_crudo`, NO
    `id_instrumento`); `InstrumentoProcesado` se crea con `ruta_json` y estado
    "estandarizado". ✔ Confirma la regla de IDs §1.1 y §8.b (hallazgo HIGH-1 ya incorporado
    correctamente).

## Suposiciones no verificadas / incorrectas

- **Incorrecta (menor):** §4.5 generaliza "acepta vacío/null y responde 200" a todos los
  campos; para `dc_title` (`NOT NULL` en modelo y DDL) un título **omitido** produce 500, no
  200. Ver hallazgo NIT-1. No cambia ninguna decisión porque el wizard garantiza título no
  vacío.
- **Ya verificable (el diseño la dejó "pendiente"):** §11.2 DDL de `metadatos_dc` — leído y
  confirmado consistente con el modelo `shared` (`id_crudo` PK). Ver NIT-2.
- **Deliberadamente diferida (aceptable):** §6.4/§11.3 contrato de
  `storage-service /almacenamiento/json` — no leído; como `guardarInstrumento` no se cablea
  esta iteración, no afecta. Ver NIT-3.
- **Correctamente marcada como condición, no como hecho:** §1.1/§11.8 la igualdad
  `id_crudo == id_instrumento == N` sólo vale en BD recién truncada. El diseño ya la trata
  como suposición del script de demo y propone resolver `id_instrumento` desde `id_crudo`.
  Verificado en `seed_demo.py`. Sin hallazgo.
- **MIME multipart en navegador** (§11.4) y **mapeo `dc_language` "es"↔"Español"** (§11.5):
  anotados como riesgos de implementación con mitigación concreta; razonables, sin hallazgo.

---

## Conclusión

Ningún hallazgo HIGH o MEDIUM. Los 3 NIT son correcciones de redacción/alcance que no
alteran decisiones de implementación. Las correcciones que el diseño dice haber hecho
respecto a sus revisiones previas (HIGH-1 IDs, HIGH-2 `dc_creator`, MEDIUM-1 `dc.tema` fuera
de la guarda, MEDIUM-2 arreglo de `dc_manager` obligatorio, MEDIUM-3 sin 422, MEDIUM-4
`limpiarArchivo` sin "o/o", NITs de pasos/stub/fallback) están todas respaldadas por el
código real.

**Veredicto: APPROVED.**
