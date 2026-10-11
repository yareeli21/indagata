# Resolución pregunta↔columna por `question_id` en estandarización tabular

El fix reescribe `_resolver_preguntas_tabular` en `standardization_service.py` para mapear cada `PreguntaConfirmada` a su columna de origen por `question_id` (`'q{N}'`, N = índice 1-based de columna) en lugar de por el nombre normalizado del `text`. El bug era que, cuando `_mapa_headers` desambigua encabezados sucios o duplicados con sufijos (`..._item1__2`), el `text` crudo que el preview devuelve al frontend ya no igualaba la clave desambiguada, de modo que `mapa.get(_normalizar(p.text))` fallaba y el endpoint devolvía 422 "no corresponde a ninguna columna" — exactamente el síntoma reportado en id_crudo=2 (33 preguntas). Ahora la columna sale directo del `question_id` estable que genera `type_detector.detectar_tipos`, con fallback por nombre para payloads sin id. Se agregó un helper `_parsear_question_id` y tres pruebas de regresión.

Watch for: ninguna preocupación bloqueante. El diff trae cambios no relacionados (proxy del api-gateway, APIs del frontend, Dockerfile de analysis-service) fuera del alcance declarado del fix — informativo, no bloqueante (possible).

**Verdict**: APPROVED

## High-level view

La resolución de columnas cambió de "match por texto normalizado" a "índice derivado de `question_id`". Dado que `type_detector` ya emitía `question_id = f"q{idx+1}"` y el preview lo expone al frontend, el fix cierra el loop usando ese identificador estable como fuente de verdad para la columna, en vez del `text` que puede divergir tras la desambiguación de headers. La semántica del texto no cambia: el `PreguntaDominio` resultante conserva `text=p.text`.

El manejo de fallos distingue dos casos. Un `question_id` que parsea pero cae fuera de `[0, n_cols)` es un id inválido y aborta con 422 inmediato (fail-closed, no silencioso). Un `question_id` ausente o no parseable degrada al fallback por nombre normalizado, preservando el comportamiento legacy; si ese fallback tampoco resuelve, 422 final. Ambos mensajes 422 incluyen `question_id` y `text`, en español.

Todo lo que no es la resolución de columna se conservó intacto: `_recalcular_opciones` y `_recalcular_escala` cuando faltan options/escala, el marcado de columnas usadas (`usados.add(col)`), y la nota de columnas no referenciadas. La ruta DOCUMENTO, `_normalizar` y `type_detector` no cambiaron de lógica.

La evidencia de ejecución del coder confirma el caso crítico: id_crudo=2 devuelve 200 con `json_instrumento` poblado (q1..q33 en `instrument.sections[0].questions` y `respondents[]`), y la suite pasa 23/23 (20 previas + 3 nuevas).

<details>
<summary>Issues (1)</summary>

1. **Cambios no relacionados en el mismo diff** (possible) — proxy.py del api-gateway, APIs del frontend (`carga.ts`, `client.ts`, `espacio.ts`, `grafo.ts`, `kpis.ts`), `UploadWizard.tsx` y `Dockerfile.analysis-service` aparecen en el diff pero quedan fuera del alcance del fix de estandarización. No bloquean; conviene que la usuaria los separe o los confirme intencionales antes de commitear.

</details>

<details>
<summary>Details</summary>

### Derivación de columna por `question_id` y manejo de fallos

El núcleo es `col = numero - 1` con `numero = _parsear_question_id(p.question_id)`. El helper valida `'q<entero>'` de forma estricta (prefijo `'q'` + `isdigit()`), devolviendo `None` en cualquier otro caso para habilitar el fallback.

```python
numero = _parsear_question_id(p.question_id)
if numero is not None:
    col = numero - 1
    if not (0 <= col < n_cols):
        raise HTTPException(status_code=422, detail=(
            f"La pregunta con question_id '{p.question_id}' "
            f"(texto: '{p.text}') no corresponde a ninguna columna "
            f"del instrumento (hay {n_cols} columnas)."))
else:
    col = mapa.get(_normalizar(p.text))
```

El punto no obvio: un id que parsea pero sale de rango **no** cae al fallback por nombre (eso ocultaría un payload corrupto), aborta de inmediato con 422. El `n_cols = len(tabla.headers)` es consistente con que `type_detector` genera un `q{idx+1}` por header. El segundo 422 (ni id ni nombre resuelven) también incluye `question_id` y `text`.

### Ruta DOCUMENTO y detectores sin cambios

El filtro del diff sobre `DOCUMENTO|_normalizar|type_detector|detectar_tipos` solo arroja menciones dentro del docstring y la línea del fallback (`mapa.get(_normalizar(p.text))`): `_normalizar` se sigue usando igual, sin cambio de lógica. La rama DOCUMENTO (que arma una sola pregunta `q1` abierta) está fuera de las líneas tocadas. `type_detector.detectar_tipos` ya exponía `question_id = f"q{idx+1}"` antes del fix (confirmado en `type_detector.py`), así que el fix consume un contrato preexistente, no lo introduce.

### Cobertura de pruebas

Las tres pruebas nuevas cubren los tres caminos del fix sin tocar las existentes:

- `test_estandarizar_resuelve_por_question_id_con_headers_duplicados`: el caso que motivó el bug — headers que colisionan al normalizar (`"Organizacion y  item1"` vs `"Organizacion_y__item1"`). Verifica que el preview emite `["q1","q2","q3"]` y que reenviar con esos ids produce 200 con las tres columnas como preguntas. Esta es la regresión que importa.
- `test_estandarizar_question_id_fuera_de_rango_devuelve_422`: id `q99` sobre un instrumento chico → 422, y asegura que el detalle contiene `q99` y `edad` (verifica el contenido del mensaje, no solo el status).
- `test_estandarizar_fallback_por_nombre_sin_question_id`: `question_id` vacío → fallback por nombre único resuelve 200.

No probado: colisión del fallback por nombre con headers duplicados sin `question_id` (es decir, el camino else cuando `_normalizar` colisiona) — pero ese es precisamente el escenario que el fix hace improbable en producción, ya que el frontend siempre reenvía el `question_id` del preview. Tampoco hay prueba unitaria aislada de `_parsear_question_id` para entradas límite (`"q"`, `"q0"`, `"qabc"`, `"1"`); quedan cubiertas indirectamente. No es bloqueante.

### Evidencia de ejecución (leída, no re-ejecutada)

`verification.md` documenta: build y recreate de `instrument-service` OK (código montado como volumen desde el working tree), login de investigador 200, y el caso crítico id_crudo=2 → `POST /instrumentos/2/estandarizar` con **HTTP 200**, `estado: "estandarizado"` y `json_instrumento` **poblado** (`instrument.sections[0].questions[]` con q1..q33 y `respondents[]`). Refuerzo con id_crudo=1 (200, 30 questions tras excluir 3 demográficas). Suite `pytest app/standardization/tests` → **23 passed**. La evidencia del 200 con json poblado para id_crudo=2 está presente y es explícita, de modo que no procede rechazo por evidencia faltante.

### Cambios no relacionados en el diff

El `--stat` muestra, además de los dos archivos del fix: `infrastructure/docker/Dockerfile.analysis-service`, `services/api-gateway/proxy/proxy.py` (+62) y cinco archivos del frontend (`carga.ts`, `client.ts`, `espacio.ts`, `grafo.ts`, `kpis.ts`, `UploadWizard.tsx`). Caen fuera del alcance declarado (el fix de `_resolver_preguntas_tabular`). No se revisaron a profundidad porque no pertenecen a esta tarea; se señalan para que la usuaria decida separarlos en otro commit o confirme que son intencionales. No bloquean este veredicto porque el criterio de aceptación es sobre el instrument-service, que está correcto.

</details>

<details>
<summary>Archivos</summary>

- `services/instrument-service/app/services/standardization_service.py` — nuevo `_parsear_question_id`; `_resolver_preguntas_tabular` resuelve columna por `question_id` con fallback por nombre y 422 informativos.
- `services/instrument-service/app/standardization/tests/test_estandarizar_api.py` — 3 pruebas de regresión (duplicados por id, fuera de rango 422, fallback por nombre).
- (fuera de alcance) `services/api-gateway/proxy/proxy.py`, `infrastructure/docker/Dockerfile.analysis-service`, `pixel-perfect-pixel/src/api/{carga,client,espacio,grafo,kpis}.ts`, `pixel-perfect-pixel/src/features/upload/UploadWizard.tsx`.

Diff completo: `git diff elotro-back`.

</details>
