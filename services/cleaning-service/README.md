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
- **Pruebas** (no se califican): por reactivo, distribución de respuestas, opción más elegida,
  opciones que nadie eligió, nulas, no respondidas y media en los numéricos; reactivos con mucha
  no respuesta y casi unánimes.
- **Entrevistas:** participación por hablante y palabras por turno.

Umbrales en `config/limpieza.yaml` (`encuestas.estadistica`, `pruebas.umbral_sin_respuesta`, `pruebas.umbral_casi_unanime`).

Los bloques para el alfa se forman con «Pregunta [aspecto]» o con un prefijo numerado
(`Aportacion_item1`, `Dedicacion_2`…). Los encabezados de cantidades (horas, edad, hijos…;
`encuestas.tipos.palabras_numerica`) se tratan como numéricos, no como escala ni calificación.

**Resumen «En pocas palabras»** (`services/motores/resumen.py`): frases en lenguaje sencillo
con nivel `bien | info | atencion | alerta`, generadas con reglas fijas (sin LLM) a partir de
las medidas. Se calcula al servir la vista final (`vistaFinal.resumen`), así que también
aparece en limpiezas ya confirmadas. Cómo leer cada medida: `documentación/02_Desarrollo.md`, X.7.2.

## Errores de archivos reales (2 nov)

Medidos con los generadores de `tools/limpieza/` (versiones «no contempladas» de enc_06, pru_03 y ent_11).

| Tipo | Se corrige solo (y se reporta) | Lo decide el investigador | No se detecta (limitación) |
|---|---|---|---|
| Todos | Acentos rotos («SÃ­» → «Sí», `motores/codificacion.py`); encabezado repetido a mitad del archivo | Fila corrida una columna o con celdas de más (`motores/filas.py`: reparar, eliminar o conservar) | — |
| Encuestas | Coma decimal, número con su etiqueta («4 (De acuerdo)»), número con palabras, unidad («19 años») (`encuestas/numeros.py`); «Yes»/«S»/«True» en columnas Sí/No | Fila de totales o promedios; segunda fila con el texto de las preguntas; «1»/«0» en columnas Sí/No; opción poco frecuente casi igual a otra («Una vez al mse») (`encuestas/categorias.py`) | Sinónimos («Jamás»), «Otro: texto», casi duplicados con otro ID |
| Pruebas | «B)», «(C)», «AA», letras de otro alfabeto, «N/R», «Sin respuesta», «-» (`tokens_no_respondida`) | Reactivo sin ninguna respuesta (conservar con 100 % NR o eliminar); ID escrito distinto («r0067», «R082») | Números en lugar de letras (1 → A), mismo alumno con otro ID |
| Entrevistas | Encabezados y pies de página repetidos; minuto pegado a la etiqueta («Entrevistada (min 23):») | Anotaciones del transcriptor («[inaudible]», «(risas)»: quitar o conservar; lista en `anotaciones_transcriptor`); muletillas «eh», «mmm» (conservar, sugerido, o quitar; lista en `muletillas`) | Muletillas ambiguas («este», «o sea»), arranques en falso, errores del reconocimiento de voz, etiquetas abreviadas («E:») |

Las letras espaciadas que empiezan con una palabra de una letra («o a n s i e d a d») se resuelven con el
vocabulario del propio documento; si no alcanza, se unen y se avisa («uniones dudosas»).

## Pruebas

```powershell
cd services/cleaning-service; ..\..\.venv\Scripts\python.exe -m pytest tests -q
```

## Pruebas estandarizadas: tipos de reactivo (sin calificar)
Indagata no califica las pruebas: no recibe clave de respuestas ni marca respuestas como correctas.
`services/motores/pruebas/tipos.py` reconoce el tipo de cada columna por sus valores:
- opción múltiple (A–D) y verdadero/falso (V/F);
- **puntos**: enteros 0..máx con algún 0 (una respuesta corta ya puntuada);
- **escala**: enteros 1..máx sin 0; **Sí/No**; **numérico** libre.

Puntos, escala, Sí/No y numérico solo se reconocen si el encabezado parece un reactivo (P3, item_2…). En esas
columnas se toleran respuestas sucias (ilegibles y de varias letras no cuentan; basta el 60 % de letras
válidas). Las columnas de contexto (`services/configuracion.py::es_contexto`, la misma regla que en encuestas)
se conservan al final del CSV limpio. El reporte registra `tipos_reactivo`, `orden_reactivos` y `puntos_max`.
