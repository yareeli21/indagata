# Plan de implementación — Etapa de estandarización + 5 fixes del wizard (Indagata)

Rama: `elotro-back` (checkout principal, SIN worktree). Raíz: `C:\Users\yarel\Documents\indagata\indagata`.
Fuente de verdad: `.agents/tasks/wizard-fixes/design.md` (diseño APROBADO) y `findings.md`.
NO revertir el fix CUDA→CPU-only sin commitear en `Dockerfile.analysis-service`.

Hallazgo de exploración que corrige al diseño: los modelos ORM
`MetadatosEnriquecidosEncuestas` / `_Entrevistas` / `_Pruebas` **YA EXISTEN** en
`shared/models/` (`metadatos_encuestas.py`, `metadatos_entrevistas.py`,
`metadatos_pruebasestandarizadas.py`) y ya están registrados en
`shared/models/__init__.py`, con columnas exactas al `01_schema.sql`. El paso de Bug 2
backend **reutiliza** esos modelos; NO los recrea.

Entornos y comandos reales (verificados):
- Python del repo: `.venv\Scripts\python.exe`. PowerShell encadena con `;` (no `&&`).
- Backend: NO hay suite pytest ni config en instrument-service/metadata-service (solo
  analysis-service tiene `tests/` + `conftest.py` con shim de `sys.path`). Los tests
  nuevos se crean con ese mismo patrón de conftest (insertar raíz del servicio y raíz
  del repo en `sys.path`) y se corren con `& "..\..\.venv\Scripts\python.exe" -m pytest`.
  Prueba en aislamiento = `TestClient` de FastAPI con `dependency_overrides` de `get_db`
  y `get_current_user` (ver `services/TESTING.md` §1).
- Frontend: `pixel-perfect-pixel/` usa **vite** (no bun test). Verificación =
  `npm run build` (o `bun run build`) y `npm run lint`.

---

## Parte A — instrument-service: etapa de estandarización + Bug 5

- [ ] 1. Añadir `leer(ruta) -> bytes` al puerto de storage y su implementación local.
      En `app/storage/port.py` agregar el método abstracto `leer` a `StoragePort`
      (docstring: lee por la `ruta` guardada en `raw_data`, lanza `StorageError`). En
      `app/storage/local_backend.py` implementarlo: resolver `settings.raw_path_abs.parent / ruta`
      (igual que `eliminar`, `storage_root = raw_path_abs.parent`, `ruta` tiene forma
      `raw/<uuid>__name.ext`), validar defensa en profundidad (dentro de `storage/`),
      `Path(target).read_bytes()`, y envolver cualquier `OSError` en `StorageError`.
      Files: `services/instrument-service/app/storage/port.py`,
      `services/instrument-service/app/storage/local_backend.py`
      Verify: `& "..\..\.venv\Scripts\python.exe" -m pytest app/standardization/tests -q` desde
      `services/instrument-service` (el test de storage del paso 7 ejercita `leer`/round-trip).

- [ ] 2. Fix Bug 5 en `instrumento_query.py`: eliminar SOLO las dos líneas
      `if id_crudo >= 1: return f"inst_{id_crudo:02d}"` de `_slug_por_id_crudo`,
      conservando la consulta a `_seed_map.json`. Resultado: sin mapeo explícito → `None`
      (sin fallback a semilla); con `_resolver_por_ruta_json` tomando el JSON real primero.
      Files: `services/instrument-service/app/services/instrumento_query.py`
      Verify: test unitario del paso 7 (`_slug_por_id_crudo` sin `_seed_map.json` → `None`;
      con mapa explícito → el slug mapeado). `-m pytest` del servicio pasa.

- [ ] 3. Crear `app/standardization/type_detector.py` con la heurística de tipo por columna
      (design §1.3). Función que recibe un `RawTable` + diccionario de demográficos conocidos
      y devuelve `list[TipoPreguntaDetectado]` con `{question_id, text, type, options?,
      scale_min?, scale_max?, confianza, es_demografica}`. Orden de evaluación: binaria
      (⊆ {si,sí,no,0,1,true,false,verdadero,falso}, card ≤ 2) → likert (enteros contiguos
      1..N, preferencia N≤7, captura scale_min/max) → numerica_continua (todo numérico, no
      likert) → opcion_multiple (distintos ≤ min(12, 0.5·n) y ≥ 2, captura options por
      frecuencia) → abierta (resto / columna vacía, confianza baja). Normaliza a minúsculas
      sin acentos solo para la familia binaria. `es_demografica` por diccionario corto
      (edad, genero/género, carrera, semestre, promedio, empleo, horas_estudio,
      situacion_economica, apoyo_familiar). Preserva orden de `RawTable.headers`.
      Files: `services/instrument-service/app/standardization/type_detector.py`,
      `services/instrument-service/app/standardization/__init__.py`
      Verify: tests de tabla del paso 7 (binaria/likert/opcion_multiple/numerica/abierta/vacía)
      pasan con `-m pytest`.

- [ ] 4. Crear `app/standardization/domain_builder.py` que construye el dict de dominio con el
      esquema EXACTO del seed `storage/raw/inst_01.v1.json` (design §1.4): `instrument_id =
      f"upload_{id_crudo}"`, `schema_version="1.0"`, `instrument.{title,objective,
      dimensions_explored,sections[].questions[]}` con `{question_id,text,type,options?,
      scale_min?,scale_max?}` (`options` solo en opcion_multiple/binaria/likert; `scale_*`
      solo en likert), `metadata.dublin_core={}`, `metadata.survey_specific={}`,
      `design_reference={kpi_hints:[],note:...}`, y `respondents` SOLO tabular (una fila→un
      respondente `r_{i:04d}`, `demographics` de columnas es_demografica, `answers`
      coaccionadas a int/float según type, celda vacía→null). `section.name =
      "Reactivos del módulo"`. OMITE `synthetic_profiles` y `respondents[].profile_id`.
      Documentos: `respondents=[]` y una sola `question` abierta con el texto COMPLETO de
      `ExtractedDocument.text` (vía `read_document`, no el preview).
      Files: `services/instrument-service/app/standardization/domain_builder.py`
      Verify: test de snapshot del paso 7 (dict coincide con esquema reducido del seed) pasa.

- [ ] 5. Crear `app/schemas/estandarizacion.py` (Pydantic v2) con los DTOs de design §1.6:
      `TipoPreguntaDetectado`, `PreviewResponse` (`id_crudo`, `tipo_instrumento`, `preguntas`,
      `n_respondentes_detectados`, `notas`), `PreguntaConfirmada` (`question_id`,`text`,`type`∈
      {binaria,opcion_multiple,likert,numerica_continua,abierta}, `options?`, `scale_min?`,
      `scale_max?`, `es_demografica`=default False), `EstandarizarRequest` (`preguntas` no vacío),
      `EstandarizarResponse` (`id_crudo`,`id_instrumento`,`estado`,`ruta_json`,`json_instrumento`,
      `mensaje`). Validación de escala `1 ≤ scale_min < scale_max ≤ 100` solo si type==likert.
      Files: `services/instrument-service/app/schemas/estandarizacion.py`
      Verify: importa sin error (`-m pytest` recoge los tests que usan estos schemas).

- [ ] 6. Crear `app/services/standardization_service.py` que orquesta preview y estandarizar
      (design §1.2–§1.7). `preview(db, id_crudo)`: resuelve `RawData` (404 si no existe), lee
      `raw_data.raw_archivo` vía `get_storage().leer` (422 StorageError), parsea con
      `parse_file` (422 ParseError), detecta tipos (tabular) o produce 1 pregunta abierta
      (documento), devuelve `PreviewResponse` con `n_respondentes_detectados` = nº filas (0 doc).
      `estandarizar(db, id_crudo, preguntas)`: valida correspondencia pregunta↔header por
      NOMBRE normalizado (422 si una pregunta referencia header inexistente; headers no
      referenciados → nota; duplicados → sufijo `__2`), re-deriva `respondents.answers` según
      los tipos confirmados, construye el dict con `domain_builder`, lo escribe vía
      `get_storage().guardar(json_bytes, "inst_<id>.estandarizado.v1.json")`, normaliza la ruta
      a relativa-al-proyecto con prefijo `storage/` en `_ruta_relativa_proyecto`
      (`settings.raw_path_abs.parent.name + "/" + StoredRef.ruta`, invariante §1.5), setea
      `procesado.ruta_json`, `estado="estandarizado"`, `fecha_procesamiento=now()`. Reestandarizar:
      sobrescribe (200); 409 si estado ya es `vectorizado`. Rollback de BD elimina el JSON escrito.
      Files: `services/instrument-service/app/services/standardization_service.py`
      Verify: tests de integración del paso 8 (estados/ruta_json/404/422/409) pasan.

- [ ] 7. Crear tests unitarios de la Parte A (sin BD): `type_detector`, `domain_builder`
      (snapshot vs seed reducido), `_ruta_relativa_proyecto` resoluble por
      `_resolver_por_ruta_json`, `_slug_por_id_crudo` tras el fix. Crear
      `app/standardization/tests/conftest.py` con el shim de `sys.path` (raíz del servicio +
      raíz del repo, patrón de `services/analysis-service/tests/conftest.py`).
      Files: `services/instrument-service/app/standardization/tests/conftest.py`,
      `services/instrument-service/app/standardization/tests/test_type_detector.py`,
      `services/instrument-service/app/standardization/tests/test_domain_builder.py`,
      `services/instrument-service/app/standardization/tests/test_instrumento_query.py`
      Verify: `& "..\..\.venv\Scripts\python.exe" -m pytest app/standardization/tests -q`
      desde `services/instrument-service` — todos pasan.

- [ ] 8. Crear `app/routers/standardize.py` con `POST /instrumentos/{id}/estandarizar/preview`
      y `POST /instrumentos/{id}/estandarizar`, ambos protegidos con
      `require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR)` (patrón de `upload.py`/`list.py`,
      `prefix="/instrumentos"`), delegando en `standardization_service`. Registrar el router
      en `services/instrument-service/main.py` (`app.include_router(standardize.router)`,
      conservando health/upload/delete/list). Añadir test de integración TestClient que
      sube→preview→estandariza y afirma `estado="estandarizado"`, `ruta_json` presente,
      y que `GET /instrumentos` tras estandarizar NO devuelve el título de `inst_01.v1.json`
      (Bug 5 end-to-end), con `dependency_overrides` de `get_db`/`get_current_user`.
      Files: `services/instrument-service/app/routers/standardize.py`,
      `services/instrument-service/main.py`,
      `services/instrument-service/app/standardization/tests/test_estandarizar_api.py`
      Verify: `& "..\..\.venv\Scripts\python.exe" -m pytest app/standardization/tests -q` pasa;
      `& "..\..\.venv\Scripts\python.exe" -B -c "import main"` desde el servicio no lanza.

- [ ] 9. (Seed) En `scripts/seed_demo.py`, tras sembrar, escribir/mantener
      `storage/raw/_seed_map.json` con `{"inst_01": <id_crudo>, ...}` real (cambio aditivo,
      para que los instrumentos sembrados sigan resolviéndose tras el fix del Bug 5). Si el
      script no siembra ids deterministas, documentar en el propio script cómo regenerarlo.
      Files: `services/instrument-service/scripts/seed_demo.py`
      Verify: ejecutar el seed (o su dry-run si existe) y confirmar que `_seed_map.json` queda
      escrito; `-m pytest` del servicio sigue verde.

## Parte B — metadata-service: endpoint de metadatos específicos (Bug 2 backend)

- [ ] 10. Crear `services/metadata-service/services/specific_manager.py` con
      `SpecificMetadataManager.upsert(db, instrumento_id, tipo, campos)` (patrón de `DCManager`):
      resuelve `id_crudo` desde `id_instrumento` vía `InstrumentoProcesado`, valida `tipo`
      contra `raw_data.tipo_instrumento` (409 si no coincide), hace UPSERT por `id_crudo` sobre
      el modelo YA EXISTENTE del tipo (`MetadatosEnriquecidosEncuestas/_Entrevistas/_Pruebas`
      de `shared/models/`). Solo persiste campos no vacíos; `palabras_clave`/`dimensiones`/
      `mapeo_de_reactivos_por_seccion` como JSON (lista/objeto), string vacío→NULL; numéricos
      `n_respondentes`/`n_poblacion` enteros ≥0 (422 si no parsea). Rollback+500 ante
      `SQLAlchemyError`. (NO crear modelos ORM: ya existen y están en `__init__.py`.)
      Files: `services/metadata-service/services/specific_manager.py`
      Verify: test del paso 12 (upsert por tipo, mismatch 409) pasa con `-m pytest`.

- [ ] 11. Crear `services/metadata-service/routers/specific.py` con
      `router = APIRouter(prefix="/metadata")` y `@router.post("/{instrumento_id}/especificos")`
      (sin segundo `/metadata`), que recibe `{tipo, campos}` y delega en `SpecificMetadataManager`.
      Registrar en `services/metadata-service/main.py`: importar `specific` junto a
      `health, metadata, enrichment` y añadir
      `app.include_router(specific.router, prefix="/api", tags=["metadata-especificos"])`
      DESPUÉS de `metadata` y antes de `enrichment` (design §6.1). Ruta final:
      `POST /api/metadata/{id}/especificos` (cae bajo el prefijo `/api/metadata/*` que el
      gateway ya proxea; no tocar el gateway).
      Files: `services/metadata-service/routers/specific.py`,
      `services/metadata-service/main.py`
      Verify: `& "..\..\.venv\Scripts\python.exe" -B -c "import main"` desde
      `services/metadata-service` no lanza; test de ruteo del paso 12 verde.

- [ ] 12. Crear tests de la Parte B (TestClient + `dependency_overrides` de `get_db`):
      afirmar que tras registrar `specific`, `POST /api/metadata/metadata/{id}` sigue
      resolviendo a `register_metadata`, `POST /api/metadata/{id}/especificos` resuelve al
      handler nuevo, y `GET /api/metadata/metadata/{id}/init` sigue resolviendo (design §8,
      Hallazgo 5); upsert por tipo y mismatch 409. Crear `tests/conftest.py` con shim de
      `sys.path` (raíz servicio + raíz repo).
      Files: `services/metadata-service/tests/conftest.py`,
      `services/metadata-service/tests/test_specific.py`
      Verify: `& "..\..\.venv\Scripts\python.exe" -m pytest tests -q` desde
      `services/metadata-service` — todos pasan.

## Parte C — frontend: wizard (Bugs 1, 2-fe, 3-fe, 4 y reorden)

- [ ] 13. (Bug 1 — tipos y API) En `pixel-perfect-pixel/src/types/index.ts` añadir
      `fuente?: string; relacion?: string;` a `DublinCore`, y los tipos de estandarización
      (`TipoPreguntaUI`, `PreguntaPreview`, `EstandarizarPreviewResponse`,
      `EstandarizarResponse`, `MetadatosEspecificos`). En `src/api/carga.ts` añadir
      `estandarizarPreview(idCrudo)` → `POST ${API_URL}/instrumentos/{id}/estandarizar/preview`
      (auth), `estandarizar(idCrudo, preguntas)` → `POST ${API_URL}/instrumentos/{id}/estandarizar`
      (auth), y `registrarMetadatosEspecificos(idInstrumento, tipo, campos)` →
      `POST ${API_URL}/api/metadata/{id}/especificos` (auth), con parseo de listas por comas y
      numéricos, y mapeo 409/422 a mensaje español (patrón de `registrarMetadatos`). El mapeo
      etiqueta UI→backend de tipo de pregunta vive aquí (Binaria→binaria, etc.).
      Files: `pixel-perfect-pixel/src/types/index.ts`, `pixel-perfect-pixel/src/api/carga.ts`
      Verify: `npm run build` y `npm run lint` en `pixel-perfect-pixel/` sin errores.

- [ ] 14. (Bug 1 — formulario DC) En `src/features/upload/StepDublinCore.tsx` añadir dos
      `Campo` (inputs) para **Fuente** (`fuente`) y **Relación** (`relacion`), opcionales,
      `maxLength={120}`. Marcar **Fecha** e **Idioma** como informativos (nota con ícono `Info`:
      "El sistema fija la fecha de registro y el idioma (es)."). NO cambiar `derechos`
      (ya `maxLength={120}`, respeta VARCHAR(255)). En `UploadWizard.tsx`, en el bloque de
      registro DC, incluir `if (dc.fuente) metadatos.dc_source = dc.fuente;` y
      `if (dc.relacion) metadatos.dc_relation = dc.relacion;`. POST sigue a
      `/api/metadata/metadata/{id}`.
      Files: `pixel-perfect-pixel/src/features/upload/StepDublinCore.tsx`,
      `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx`
      Verify: `npm run build` y `npm run lint` sin errores.

- [ ] 15. (Bug 2 — formulario del tipo) En `src/features/upload/StepMetadatosTipo.tsx`
      reemplazar `CAMPOS_POR_TIPO` por los campos REALES de cada tabla (design §6.2):
      Encuesta (`n_respondentes` pre-rellenado con `n_respondentes_detectados` del preview y
      editable, `n_poblacion`, `objetivo`, `carrera`, `poblacion_objetivo`,
      `constructo_principal`, `palabras_clave`→lista por comas, `dimensiones`→lista por comas,
      `notas_contextuales`, `notas_interpretacion`), Entrevista (`identificador_propio`,
      `objetivo`, `metodologia`, `institucion`, `derechos`), Prueba (`unidad_de_aprendizaje`,
      `tipo_de_prueba`, `nivel_educativo`, `objetivo_de_evaluacion` principales + resto en
      sección "Más detalles"; `mapeo_de_reactivos_por_seccion` OMITIDO). Estado sigue
      `MetadatosTipo = Record<string,string>` con claves = columnas reales.
      Files: `pixel-perfect-pixel/src/features/upload/StepMetadatosTipo.tsx`
      Verify: `npm run build` y `npm run lint` sin errores.

- [ ] 16. (Bug 3 — componente de tipos) Crear
      `src/features/upload/StepTiposPregunta.tsx`: tabla de preguntas con `text` (solo lectura),
      `select` de `type` (5 opciones español: Binaria, Opción múltiple, Likert, Numérica
      continua, Abierta), `scale_min/max` visibles solo si Likert, toggle "¿Es demográfica?" y
      badge de `confianza`. Caso documento (`preguntas.length===1 && type==='abierta'`): mostrar
      estado informativo ("Este instrumento es un documento de texto; no se tipifican preguntas
      individuales"), avanzar sin edición, texto UI truncado pero texto completo preservado en
      el estado (design §7, NIT #2). Todo en español, tokens semánticos.
      Files: `pixel-perfect-pixel/src/features/upload/StepTiposPregunta.tsx`
      Verify: `npm run build` y `npm run lint` sin errores.

- [ ] 17. (Reorden + Bug 4) Reescribir el flujo de `UploadWizard.tsx` a 9 pasos (design §7):
      0 Archivo, 1 Limpieza, **2 Tipos de pregunta (NUEVO)**, 3 Dublin Core, 4 Metadatos del
      tipo, 5 Vista previa JSON, 6 KPIs sugeridos, 7 Calcular KPIs, 8 Guardar. Actualizar
      `PASOS` (9 entradas con "Tipos de pregunta" en índice 2), `PASO_CALCULO=7`,
      `PASO_GUARDAR=8`, el array `puedeContinuar` y los `paso === N` desplazados +1 a partir del
      antiguo 2. Nuevo estado `tiposDetectados`/`tiposConfirmados`/`nRespondentesDetectados`.
      Paso 2: al ENTRAR llamar `estandarizarPreview`; al AVANZAR llamar `estandarizar` y
      `setJsonInstrumento(resp.json_instrumento)`. Paso 4: al avanzar llamar
      `registrarMetadatosEspecificos` y construir `surveyEspecifico` POR TIPO (espejo de
      `CAMPOS_ESPECIFICOS_POR_TIPO`: encuesta constructo_principal/dimensiones/palabras_clave/
      carrera/notas_contextuales/notas_interpretacion; entrevista objetivo/metodologia; prueba
      unidad_de_aprendizaje/taxonomia_bloom/objetivo_de_evaluacion/competencias).
      Añadir helper puro `enriquecerJson(base, dc, surveyEspecifico)` que devuelve copia INMUTABLE
      escribiendo SOLO `dc:title/dc:subject/dc:description/dc:coverage` en
      `metadata.dublin_core` y `survey_specific` fusionado (design §1.4bis). Reescribir el
      `useEffect` de KPIs (ahora paso 6): guarda `if (!jsonInstrumento) { setSugeridos([]); return; }`,
      `original = originalDeTextoPlano ?? Blob(textoDerivadoDePreguntas(json), text/markdown)`,
      `jsonEnriquecido = enriquecerJson(...)`, `setJsonInstrumento(jsonEnriquecido)`,
      `archivoJson = Blob(JSON.stringify(jsonEnriquecido))`, `proponerKpis(...)`. El `catch`
      DIFERENCIA 503 (toast con instrucciones de Chroma/Ollama + reindex) de lista vacía
      legítima (setSugeridos([]) sin toast) usando `e.status`. `guardar()` del paso 8 consume el
      `jsonInstrumento` enriquecido ya en estado. Mantener INTACTOS cálculo de KPIs, grafo y
      archivo original. Textos en español.
      Files: `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx`
      Verify: `npm run build` y `npm run lint` sin errores.

- [ ] 18. (Bug 4 — restricción del original) En `src/features/upload/StepArchivo.tsx` restringir
      el `accept` del input de archivo ORIGINAL a `.md,.txt` y validar la extensión al
      seleccionarlo/soltarlo (rechazar binarios con mensaje claro en español); si no es texto,
      cae al respaldo `textoDerivadoDePreguntas`. El archivo respondido conserva su `accept`
      actual. (design §4, Hallazgo 3).
      Files: `pixel-perfect-pixel/src/features/upload/StepArchivo.tsx`
      Verify: `npm run build` y `npm run lint` sin errores.

## Parte D — verificación de integración

- [ ] 19. Verificación cruzada end-to-end y de documentación. Correr toda la suite backend
      (`-m pytest`) de instrument-service y metadata-service y el `npm run build` + `npm run lint`
      del frontend; confirmar que `import main` de ambos servicios no lanza. Documentar en el
      runbook (o `arrancar.ps1` si aplica) el prerrequisito operativo:
      `POST /vectorizacion/kpis/reindex` tras cada arranque y que Chroma/Ollama deben estar
      arriba (causa #1 de "0 KPIs" = 503 del servicio de vectorización, design §4).
      Files: (verificación; cambios de doc solo si procede)
      Verify: suites backend verdes; `npm run build` y `npm run lint` sin errores.

---

Notas / supuestos:
- El metadata-service NO aplica auth de rol en sus routers (perímetro en el gateway); el
  endpoint `/especificos` sigue ese patrón.
- Los tests de integración que requieren Chroma/Ollama (propuestas/index_summary) se validan
  manualmente con el stack arriba; los unitarios usan dobles/TestClient sin esos servicios.
- Si al correr pytest faltan dependencias de parser (openpyxl/pypdf/python-docx) en el venv,
  instalarlas desde `services/instrument-service/requirements.txt` antes de verificar.
