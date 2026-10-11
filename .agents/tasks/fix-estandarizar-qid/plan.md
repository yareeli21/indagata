# Plan de implementación — fix estandarizar por `question_id`

## Contexto (verificado leyendo el código, no re-investigado)

Bug: `POST /instrumentos/{id}/estandarizar` devuelve HTTP 422 con
`"La pregunta '<text>' no corresponde a ninguna columna del instrumento."`
cuando los encabezados del CSV están sucios o duplicados. Como el paso 2 del
wizard nunca guarda `json_instrumento`, el paso 7 (KPIs sugeridos) queda vacío.

Causa raíz confirmada en
`services/instrument-service/app/services/standardization_service.py`:

- `_resolver_preguntas_tabular(tabla, preguntas)` resuelve la columna de cada
  `PreguntaConfirmada` con `clave = _normalizar(p.text)` y `mapa.get(clave)`;
  si no encuentra, lanza 422.
- `_mapa_headers(tabla)` desambigua headers duplicados añadiendo sufijo
  `__2`, `__3`, … **a la clave normalizada**, no al texto que ve/reenvía el
  usuario. Un header duplicado produce clave `..._item1__2`, que el `text`
  crudo del preview (sin sufijo) nunca iguala → 422. Cualquier transformación
  del texto en la UI rompe el match igual.

Hechos que habilitan la solución robusta:

- `app/standardization/type_detector.py::detectar_tipos` genera cada propuesta
  con `question_id = f"q{idx + 1}"`, donde `idx` es el índice 0-based de la
  columna en `tabla.headers`. Es **estable** y 1-based en el id.
- `app/schemas/estandarizacion.py::PreguntaConfirmada` incluye el campo
  `question_id: str` (confirmado leyendo el schema). El frontend ya lo reenvía;
  el `preview` lo expone como `d.question_id`.
- `app/standardization/domain_builder.py::PreguntaDominio` ya recibe `columna`
  (índice en `RawTable`) y usa `p.text` para `demographics` y para el JSON de
  preguntas. No se toca.

Decisión de diseño: **resolver la columna por `question_id` (índice de columna)
en lugar de por nombre normalizado**, eliminando toda dependencia de
`_normalizar(text)`. Rationale: `question_id` es el único identificador estable
y round-trip entre `preview` y `estandarizar`; el texto no lo es (duplicados,
edición en UI). Es exactamente el camino robusto pedido.

Decisión sobre el fallback por nombre: **incluirlo**, pero sólo como respaldo
cuando `question_id` falta o no parsea (no cuando parsea y está fuera de rango).
Rationale: no rompe ningún flujo que ya mandara `question_id` correcto (el feliz,
que pasa a ser el principal), y da una red de seguridad para payloads viejos o
clientes que no manden `question_id`. Si `question_id` parsea pero el índice está
fuera de rango, se lanza 422 directamente (es un error real, no un caso de
compatibilidad). El fallback reusa `_mapa_headers` + `_normalizar(p.text)` tal
como hoy.

Decisiones que NO cambian (confirmadas en código):

- `_normalizar` y `type_detector` no se tocan (el `question_id` ya se expone).
- La ruta DOCUMENTO (entrevista/prueba) arma una sola pregunta abierta y no pasa
  por `_resolver_preguntas_tabular`: no se toca.
- `PreguntaDominio.text` sigue siendo `p.text` (el texto del usuario). Sólo
  cambia **cómo** se resuelve `columna`.
- No se toca el frontend.

## Comando de build/test (verificado funcionando)

El servicio no tiene virtualenv propio; se usa el venv del repo. Las 20 pruebas
de la etapa pasan hoy con:

```
cd services/instrument-service
& "..\..\.venv\Scripts\python.exe" -m pytest app/standardization/tests -q
```

(equivalente: `C:\Users\yarel\Documents\indagata\indagata\.venv\Scripts\python.exe -m pytest app/standardization/tests -q`
desde la raíz del servicio). Resultado base actual: `20 passed`.

## Items

- [ ] 1. Reescribir la resolución pregunta↔columna por `question_id` en `_resolver_preguntas_tabular`.
      Añadir un helper `_col_desde_question_id(question_id: str, n_cols: int) -> int | None`
      que valide formato `q<entero>` (`question_id[0] == "q"` y `question_id[1:]`
      es dígito), calcule `col = int(question_id[1:]) - 1` y devuelva `col` sólo
      si `0 <= col < n_cols`; devuelve `None` si el formato no parsea (para
      permitir el fallback). En `_resolver_preguntas_tabular`, para cada `p`:
      (a) intentar `col = _col_desde_question_id(p.question_id, len(tabla.headers))`;
      (b) si `col is None` por formato inválido/ausente, intentar fallback por
      nombre: `mapa.get(_normalizar(p.text))` (reusando `_mapa_headers`, que ya
      se calcula al inicio para las notas de duplicados);
      (c) si tras ambos sigue sin resolverse, lanzar 422.
      Caso especial: si `p.question_id` SÍ parsea como `q<entero>` pero el índice
      queda fuera de `[0, len(tabla.headers))`, lanzar 422 directamente (sin
      fallback), porque es un id inválido, no un payload legacy. Implementar esto
      distinguiendo "no parsea" (→ fallback) de "parsea pero fuera de rango"
      (→ 422); una forma simple es que el helper devuelva `None` sólo para
      "no parsea", y validar el rango en el llamador cuando el prefijo es `q` y
      el resto es dígito.
      Conservar intacto el resto del cuerpo actual: `_mapa_headers` para las
      notas de duplicados, `usados.add(col)`, el recálculo de opciones
      `_recalcular_opciones(tabla, col, p.type)` cuando `p.type` está en
      `domain_builder._TIPOS_CON_OPCIONES` y `not p.options`, el recálculo de
      escala likert `_recalcular_escala(tabla, col)` cuando faltan `scale_min`/
      `scale_max`, la construcción de `PreguntaDominio` con `text=p.text`
      (sin cambios de semántica) y la nota final de "Columnas no referenciadas
      por ninguna pregunta (ignoradas)".
      Files: `services/instrument-service/app/services/standardization_service.py`
      Verify: `& "..\..\.venv\Scripts\python.exe" -m pytest app/standardization/tests -q`
      desde `services/instrument-service` — las 20 pruebas existentes siguen
      pasando (incluye `test_flujo_upload_preview_estandarizar`, que manda
      `question_id` q1/q2/q3 y afirma `estado == "estandarizado"` y
      `question_id` resultantes `["q2","q3"]`).

- [ ] 2. Definir el mensaje 422 nuevo, en español, que incluya `question_id` y `text`.
      Reemplazar el detalle actual (`"La pregunta '<text>' no corresponde a
      ninguna columna del instrumento."`) por un mensaje que nombre ambos
      campos y la causa concreta. Usar dos variantes según el fallo:
      - Fuera de rango / id inválido:
        `f"La pregunta con question_id '{p.question_id}' (texto: '{p.text}') "
        f"no corresponde a ninguna columna del instrumento (hay "
        f"{len(tabla.headers)} columnas)."`
      - Sin resolver tras fallback por nombre (id ausente o no parseable y texto
        sin match): el mismo formato, dejando claro que no se pudo mapear por id
        ni por nombre.
      Mantener `status_code=status.HTTP_422_UNPROCESSABLE_ENTITY`.
      Files: `services/instrument-service/app/services/standardization_service.py`
      Verify: incluida en el item 4 (prueba de regresión del 422). Como chequeo
      intermedio, la suite del item 1 debe seguir en verde tras el cambio de
      texto.

- [ ] 3. Confirmar que no se rompe la ruta DOCUMENTO ni `_mapa_headers`/`_normalizar`.
      Revisión sin cambios funcionales: `estandarizar` sigue llamando
      `_resolver_preguntas_tabular` sólo en la rama tabular (`familia is not
      DOCUMENTO`); la rama documento usa `construir_documento`. `_mapa_headers`
      se conserva (sus notas de duplicados siguen apareciendo). `_normalizar`
      y `type_detector` quedan intactos.
      Files: ninguno (verificación de que el diff del item 1 no tocó estas rutas).
      Verify: `& "..\..\.venv\Scripts\python.exe" -m pytest app/standardization/tests -q`
      — 20 passed; en particular `test_type_detector.py` (question_id/text
      estables) y `test_domain_builder.py` siguen pasando.

- [ ] 4. Añadir pruebas de regresión del fix en `test_estandarizar_api.py`.
      Agregar casos nuevos (sin borrar los existentes) que reproduzcan el bug y
      prueben el camino robusto, usando el mismo `client` fixture:
      - Encabezados duplicados/sucios: subir un CSV cuyos headers normalicen a la
        misma clave (p. ej. `"Organizacion y  item1,Organizacion_y__item1,comentario"`),
        hacer `preview`, y mandar a `estandarizar` las preguntas con los
        `question_id` que devolvió el preview (q1, q2, q3) — afirmar
        `status_code == 200`, `estado == "estandarizado"` y que los
        `question_id` del JSON de dominio son los esperados. Antes del fix esto
        daba 422.
      - `question_id` fuera de rango (p. ej. `q99`) → afirmar 422 y que el
        `detail` contiene el `question_id` y el `text`.
      - (Opcional, documenta el fallback) `question_id` ausente/no parseable pero
        `text` que sí casa con un header único → afirmar 200 (fallback por
        nombre funciona).
      Seguir el patrón del test existente (TestClient, `_FakeStorage`, SQLite en
      memoria con `tt_rag`). No modificar el flujo feliz actual.
      Files: `services/instrument-service/app/standardization/tests/test_estandarizar_api.py`
      Verify: `& "..\..\.venv\Scripts\python.exe" -m pytest app/standardization/tests -q`
      desde `services/instrument-service` — todas las pruebas (existentes +
      nuevas) pasan.

## Tests existentes que deben seguir pasando (regresión)

Todos en `services/instrument-service/app/standardization/tests/`:

- `test_estandarizar_api.py::test_flujo_upload_preview_estandarizar` — flujo
  upload→preview→estandarizar; manda `question_id` q1/q2/q3; afirma estado,
  `ruta_json` y `question_id` resultantes. Es la cobertura directa del cambio.
- `test_type_detector.py` (11 casos) — detección de tipos; en especial
  `test_orden_y_question_ids_estables` (ids q1,q2,q3 estables). No debe cambiar.
- `test_domain_builder.py` — construcción del JSON de dominio desde
  `PreguntaDominio` (incluye `columna`). No debe cambiar.
- `test_instrumento_query.py` — consulta de instrumentos (no relacionado con el
  mapeo, pero parte de la suite que debe quedar en verde).

Base actual medida: `20 passed`.

## Supuestos / lagunas

- Se asume que el frontend reenvía `question_id` tal cual lo dio el `preview`
  (confirmado por el enunciado y por el schema `PreguntaConfirmada`). El fallback
  por nombre cubre payloads que no lo hagan.
- No se cambia el contrato de respuesta ni la semántica de `text` guardado, así
  que no hay impacto visible para el usuario salvo que estandarizar ahora
  funciona con headers duplicados/sucios.
