# cleaning-service (puerto 8007)

Limpia los instrumentos recién subidos, antes de los metadatos. Para cada uno:

1. **Fase automática**: aplica, según el tipo, las transformaciones que no requieren decisión.
2. **Fase asistida**: presenta los hallazgos con una opción sugerida (preseleccionada). La decisión siempre es del investigador.
3. **Confirmación**: genera el CSV limpio (`;`, UTF-8 con BOM) en storage-service y el `reporte_limpieza` (JSONB en `tt_rag.limpieza_ejecucion`).

Principios:
- El archivo crudo nunca se modifica.
- Cada repetición de la limpieza es una versión nueva.
- metadata-service usa la última versión `confirmada`.

## Rutas (vía api-gateway, prefijo `/limpieza`)

| Método | Ruta | Uso |
|---|---|---|
| POST | `/limpieza/{id}/ejecuciones[?nueva=true]` | Fase automática: crea una versión nueva o retoma la que espera decisiones |
| GET | `/limpieza/{id}/ejecuciones/actual` | Última versión |
| GET | `/limpieza/{id}/ejecuciones/{v}` | Fase asistida de la versión `v` |
| PATCH | `/limpieza/{id}/ejecuciones/{v}/decisiones` | Guardado parcial `{decisiones: {hallazgo: opción}}` |
| POST | `/limpieza/{id}/ejecuciones/{v}/confirmar` | Aplica las decisiones y guarda el CSV limpio |
| GET | `/limpieza/{id}/ejecuciones/{v}/vista-final` | Cifras clave y muestra del resultado |

`{id}` es el `id_crudo`. Las rutas requieren el JWT de un investigador autor del instrumento o de un administrador.

## Estructura

- `services/motores/`: un motor por tipo (contrato en `base.py`; registro en `__init__.py`). Los motores son puros (sin red ni BD).
- `services/ejecuciones.py`: ciclo de vida, decisiones, confirmación y reporte.
- `services/storage_client.py`: lee el crudo y guarda el CSV limpio, con token de servicio.
- `config/limpieza.yaml` y `shared/config/escalas_likert.yaml` (compartido con knowledge-service): reglas editables sin tocar código (tokens de vacío, columnas ajenas, umbrales, escalas Likert, opciones de prueba).
- Los lectores de archivos vienen de `shared/parsing` (los mismos que usa instrument-service).

## Base de datos

Migración `infrastructure/postgres/migrations/2026_10_limpieza.sql`:

```powershell
docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_10_limpieza.sql
```

## Medidas estadísticas

`services/motores/estadistica.py` (funciones puras, sin dependencias). Se calculan antes
(fase automática) y después (con las decisiones aplicadas); van al reporte en
`estadistica.{antes,despues}` y a la vista final (pestañas «Estadística» y «Antes y después»).

- **Encuestas:** descriptivos por columna (media, mediana, desviación estándar, cuartiles,
  asimetría y curtosis como Excel/SPSS), frecuencias y moda, atípicos por ±4σ e IQR, y alfa
  de Cronbach por bloque Likert (con «alfa si se elimina» y correlación ítem-total; los ítems
  invertidos se recodifican). Hallazgos nuevos: respuestas en línea recta y encuestados
  incompletos.
- **Pruebas:** dificultad p, discriminación D (grupos extremos del 27 %), punto-biserial
  corregida, distractores, puntajes y KR-20.
- **Entrevistas:** participación por hablante y palabras por turno.

Umbrales en `config/limpieza.yaml` (`encuestas.estadistica`, `pruebas.grupo_extremo`).

Los bloques para el alfa se forman con «Pregunta [aspecto]» o con un prefijo numerado
(`Aportacion_item1`, `Dedicacion_2`…). Los encabezados de cantidades (horas, edad, hijos…;
`encuestas.tipos.palabras_numerica`) se tratan como numéricos, no como escala ni calificación.

**Resumen «En pocas palabras»** (`services/motores/resumen.py`): frases en lenguaje sencillo
con nivel `bien | info | atencion | alerta`, generadas con reglas fijas (sin LLM) a partir de
las medidas. Se calcula al servir la vista final (`vistaFinal.resumen`), así que también
aparece en limpiezas ya confirmadas. Guía para investigadores: `markdowns/METRICAS_LIMPIEZA.md`.

## Pruebas

```powershell
cd services/cleaning-service; ..\..\.venv\Scripts\python.exe -m pytest tests -q
```

## Pruebas estandarizadas: tipos de reactivo y clave propuesta
- **Tipos calificables**, que cuentan en aciertos, puntaje y KR-20:
  - opción múltiple (A–D);
  - verdadero/falso (V/F);
  - **puntos**: respuesta ya calificada 0..máx. El máximo cuenta como acierto y el parcial queda en la respuesta.
- **No calificables**, que se conservan sin respuesta correcta: **escala** (1..máx, sin 0), **Sí/No** y **numérico** libre.
- **La clave es opcional.** Si falta, `services/motores/pruebas/clave.py`:
  1. Detecta los reactivos por sus valores.
  2. Propone, para cada reactivo, la respuesta más elegida por el 27 % de mejor desempeño. Usa la columna de puntaje global (score, puntaje…) si existe; si no, el acuerdo entre alumnos.
  3. Crea la decisión obligatoria `clave-confirmar`, más un hallazgo `clave:<reactivo>` por reactivo para corregir la propuesta.

  El reporte registra `clave_origen: inferida`, `tipos_reactivo` y `puntos_max`.
