# Verificación — fix estandarizar por `question_id`

Fecha: 2026-10-11. Rama: `elotro-back`. Sin commit (working tree solamente).

## Cambio implementado

`services/instrument-service/app/services/standardization_service.py`

- Nuevo helper `_parsear_question_id(question_id) -> int | None`: valida formato
  `q<entero>` (prefijo `q` + dígitos) y devuelve N (1-based) o `None` si no parsea.
- `_resolver_preguntas_tabular` ahora resuelve la columna de cada
  `PreguntaConfirmada` **por `question_id`**: `col = N - 1`.
  - Si `question_id` parsea pero `col` queda fuera de `[0, len(headers))` → 422
    con mensaje en español que incluye `question_id` y `text`.
  - Si `question_id` falta o no parsea → fallback por nombre normalizado contra
    `_mapa_headers` (comportamiento anterior).
  - Si tras ambos sigue sin resolverse → 422 con mensaje que incluye
    `question_id` y `text`.
- Se conservan: `_mapa_headers` (notas de duplicados), `usados.add(col)`,
  `_recalcular_opciones`, `_recalcular_escala`, `text=p.text` en
  `PreguntaDominio`, y la nota "Columnas no referenciadas por ninguna pregunta
  (ignoradas)". No se tocó `_normalizar`, `type_detector`, la ruta DOCUMENTO ni
  el frontend.

`services/instrument-service/app/standardization/tests/test_estandarizar_api.py`

- 3 pruebas de regresión nuevas (sin tocar las existentes):
  `test_estandarizar_resuelve_por_question_id_con_headers_duplicados`,
  `test_estandarizar_question_id_fuera_de_rango_devuelve_422`,
  `test_estandarizar_fallback_por_nombre_sin_question_id`.

## 1. Docker build + recreate (servicio `instrument-service`)

```
docker compose -p indagata -f .../docker-compose.yml build instrument-service
docker compose -p indagata -f .../docker-compose.yml up -d instrument-service
```

Resultado: build OK (`Image indagata-instrument-service Built`); contenedor
`indagata_instrument_service` recreado y `Started` (postgres recreado como
dependencia, quedó `Healthy`). El servicio monta `./services/instrument-service`
como volumen, así que el código corre tal cual del working tree.

## 2. Flujo end-to-end por el api-gateway (:8000) con curl.exe

- Login `investigador@indagata.com` → `access_token` obtenido (200).

### id_crudo=2 (33 preguntas, HOY fallaba con 422) — CASO CRÍTICO

- `POST /instrumentos/2/estandarizar/preview` → 200, 33 preguntas.
- `POST /instrumentos/2/estandarizar` (reenviando cada pregunta del preview con
  `question_id`, `text`, `type`, `es_demografica` y options/scale cuando aplica):
  - **HTTP_STATUS:200**
  - `estado: "estandarizado"`
  - `json_instrumento` **POBLADO**: `instrument.sections[0].questions[]` con
    question_id q1..q33 y `respondents[]` con `demographics`/`answers`.
  - `ruta_json`: `storage/raw/..__inst_2.estandarizado.v1.json`.
  - Criterio de éxito cumplido: 200 + json_instrumento no vacío.

### id_crudo=1 (refuerzo)

- Preview → 200, 33 preguntas.
- Estandarizar → **HTTP_STATUS:200**, `estado: "estandarizado"`,
  `json_instrumento` no vacío, 30 questions en la sección (3 columnas
  demográficas excluidas de `questions`, como corresponde).

## 3. Tests (pytest con el venv del repo)

```
cd services/instrument-service
& "..\..\.venv\Scripts\python.exe" -m pytest app/standardization/tests -q
```

Resultado: **23 passed** (20 existentes + 3 nuevas de regresión). Incluye
`test_flujo_upload_preview_estandarizar`, `test_type_detector.py` y
`test_domain_builder.py` sin cambios de comportamiento.

## Conclusión

El bug queda corregido: la estandarización de instrumentos tabulares con
encabezados sucios/duplicados ya no devuelve 422; el mapeo pregunta↔columna se
hace por `question_id` estable. id_crudo=2 (el caso reportado) devuelve 200 con
`json_instrumento` poblado, de modo que el wizard puede guardar el paso 2 y el
paso 7 (KPIs sugeridos) ya tiene datos de entrada.
