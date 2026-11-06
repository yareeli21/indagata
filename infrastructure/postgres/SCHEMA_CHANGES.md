# Análisis de Cambios: Schema PostgreSQL

**Fecha:** 2026-09-17  
**Comparación:** `01_schema.sql` (antiguo) vs BD actual

---

## 📊 Resumen Ejecutivo

| Categoría | Cantidad |
|-----------|----------|
| **Tablas en BD actual** | 18 |
| **Tablas en schema antiguo** | 15 |
| **Tablas NUEVAS** | 3 |
| **Tablas MODIFICADAS** | 5 |
| **Tablas SIN CAMBIOS** | 6 (maestras) |
| **Tablas ELIMINADAS** | 1 |

---

## ✅ Tablas MAESTRAS (Sin cambios - Conservadas)

Estas tablas **NO se tocan** según tu indicación:

| Tabla | Descripción | Registros |
|-------|-------------|-----------|
| `kpi` | Catálogo de indicadores educativos | 55 |
| `variable` | Variables de medición | 91 |
| `kpi_variable` | Relación KPI-Variable | 116 |
| `pregunta_kpi` | Preguntas asociadas a KPIs | Variable |
| `valor_variable` | Valores categóricos de variables | Variable |
| `instituciones` | Catálogo de instituciones | 2 |

**Estado:** ✅ **Conservadas intactas** en el nuevo schema.

---

## 🆕 Tablas NUEVAS (No existían en schema antiguo)

### **1. `etl_propuesta`**
**Propósito:** Registrar propuestas del LLM (transformaciones, metadatos enriquecidos, KPIs sugeridos)

**Campos clave:**
- `tipo`: transformacion | metadato_enriquecido | kpi_sugerido
- `estado_decision`: pendiente | aceptada | rechazada
- `justificacion`: Análisis del LLM (útil para RAG)

**¿Por qué se agregó?**  
Para implementar el workflow ETL de 4 pasos con aprobación de propuestas.

---

### **2. `metadatos_enriquecidos`**
**Propósito:** Campos adicionales detectados por el LLM (JSONB flexible)

**Campos clave:**
- `metadatos`: JSONB con campos adicionales
- Índice GIN para búsqueda rápida

**¿Por qué se agregó?**  
Para almacenar metadatos inferidos del contenido (propuestas ETL aceptadas).

---

### **3. `kpi_inferido`**
**Propósito:** KPIs asociados al instrumento (manual o por LLM)

**Campos clave:**
- `origen`: registro_manual | propuesta_etl
- `tipo_relacion`: directo | indirecto | complementario | inferido
- `score_inferencia`: Confianza del modelo (0-1)

**¿Por qué se agregó?**  
Para distinguir KPIs agregados manualmente vs detectados por el LLM.

---

## 🔧 Tablas MODIFICADAS

### **1. `instrumento_procesado`**

| Campo | Estado Antiguo | Estado Actual | Cambio |
|-------|---------------|---------------|--------|
| `visibilidad` | VARCHAR(10) | ❌ **Eliminado** | Sistema público ahora |
| `ruta_texto_limpio` | ❌ No existía | ✅ TEXT | Caché de texto extraído |
| `estado` | CHECK 5 valores | CHECK 7 valores | Agregados: `etl_pendiente`, `etl_aprobado` |
| `schema_version` | No existía | VARCHAR(10) DEFAULT '2.0' | Control de versión |

**Razón del cambio:**  
- Eliminar visibilidad: Todo público para RAG colaborativo
- Agregar estados ETL: Workflow de 4 pasos
- Caché de texto: Optimización de rendimiento

---

### **2. `metadatos_dc`**

| Campo | Estado Antiguo | Estado Actual | Cambio |
|-------|---------------|---------------|--------|
| `dc_contributor` | TEXT | ❌ **Eliminado** | No aplica al caso de uso |
| `dc_identifier` | TEXT | ❌ **Eliminado** | Se usa `instrumento_id` |
| Campos totales | 15 | **13** | Consolidación a Dublin Core estándar |

**Razón del cambio:**  
Simplificar a los 13 campos estándar de Dublin Core.

---

### **3. `pipeline_ingesta_log`**

**Antes:** `pipeline_limpieza_log`  
**Ahora:** `pipeline_ingesta_log`

| Campo | Estado Antiguo | Estado Actual | Cambio |
|-------|---------------|---------------|--------|
| `etapa_actual` | No existía | VARCHAR(50) | Trazabilidad granular |
| `n_chunks` | No existía | INTEGER | Métricas de vectorización |
| `modelo_embedding` | No existía | VARCHAR(100) | Trazabilidad del modelo |

**Razón del cambio:**  
Mayor trazabilidad del pipeline completo (no solo limpieza).

---

### **4. `permiso_instrumento`**

| Campo | Estado Antiguo | Estado Actual | Cambio |
|-------|---------------|---------------|--------|
| Relación con visibilidad | Dependía de campo | ❌ **Independiente** | Permisos solo para escritura |

**Razón del cambio:**  
Lectura pública, permisos solo para modificar/eliminar.

---

### **5. `raw_data`**

**Sin cambios estructurales**, pero integración mejorada con el pipeline.

---

## ❌ Tablas ELIMINADAS del schema antiguo

### **1. `pipeline_limpieza_log` → Renombrada a `pipeline_ingesta_log`**

No es eliminación, es **renombre + expansión**.

---

## 📋 Tablas SIN CAMBIOS (Funcionales)

| Tabla | Propósito |
|-------|-----------|
| `usuarios` | Gestión de usuarios |
| `documento_vectorizado` | Chunks vectorizados |
| `rag_log` | Log de consultas RAG |
| `prompt` | Catálogo de prompts versionados |
| `raw_data` | Versiones de archivos crudos |

---

## 🔄 Migración desde schema antiguo

### **Si tienes BD con schema antiguo:**

```sql
-- 1. Eliminar campo visibilidad (ya ejecutado)
ALTER TABLE tt_rag.instrumento_procesado 
DROP COLUMN IF EXISTS visibilidad;

-- 2. Agregar campo ruta_texto_limpio
ALTER TABLE tt_rag.instrumento_procesado 
ADD COLUMN IF NOT EXISTS ruta_texto_limpio TEXT;

-- 3. Actualizar constraint de estados
ALTER TABLE tt_rag.instrumento_procesado 
DROP CONSTRAINT IF EXISTS instrumento_procesado_estado_check;

ALTER TABLE tt_rag.instrumento_procesado 
ADD CONSTRAINT instrumento_procesado_estado_check 
CHECK (estado IN ('pendiente', 'metadata_registrado', 'etl_pendiente', 'etl_aprobado', 'en_ingesta', 'vectorizado', 'error'));

-- 4. Eliminar campos de metadatos_dc
ALTER TABLE tt_rag.metadatos_dc 
DROP COLUMN IF EXISTS dc_contributor,
DROP COLUMN IF EXISTS dc_identifier;

-- 5. Crear tablas nuevas
-- Ejecutar: 01_schema_actualizado.sql (solo las 3 tablas nuevas)
```

---

## ✅ Recomendaciones

### **Opción A: Backup + Recrear (RECOMENDADO)**

```powershell
# 1. Backup de datos maestros
$env:PGPASSWORD='ttaprobado'; pg_dump -h localhost -U postgres -d aprende_rag -t tt_rag.kpi -t tt_rag.variable -t tt_rag.kpi_variable -t tt_rag.valor_variable -t tt_rag.instituciones -t tt_rag.usuarios > backup_maestras.sql

# 2. Drop schema completo
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -c "DROP SCHEMA tt_rag CASCADE;"

# 3. Recrear con schema actualizado
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -f postgres/init/01_schema_actualizado.sql

# 4. Restaurar datos maestros
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -f backup_maestras.sql

# 5. Cargar seed data
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -f postgres/init/04_seed.sql
```

### **Opción B: Migración incremental**

Si tienes instrumentos en producción que no quieres perder, ejecutar las migraciones SQL una por una.

---

## 📝 Archivo Actualizado

**Nuevo archivo:** `postgres/init/01_schema_actualizado.sql`  
**Conserva:** Tablas maestras intactas  
**Agrega:** 3 tablas nuevas (ETL workflow)  
**Actualiza:** 5 tablas modificadas  
**Elimina:** Campo `visibilidad` y 2 campos DC

**✅ Listo para producción**

---

## 🎯 Próximos Pasos

1. ✅ **Revisar** `01_schema_actualizado.sql`
2. ✅ **Backup** de datos maestros
3. ✅ **Recrear BD** con schema nuevo
4. ✅ **Probar** workflow completo (upload → metadata → ETL → approve)
5. ✅ **Verificar** JSON consolidado con transformaciones

**¿Proceder con el reemplazo de `01_schema.sql`?**

---

## 2026-10 · Limpieza de instrumentos (cleaning-service)

Migración: `migrations/2026_10_limpieza.sql` (rollback: `2026_10_limpieza_ROLLBACK.sql`).

| Cambio | Detalle |
|---|---|
| Tabla nueva `limpieza_ejecucion` | Una fila por ejecución (versión) de la limpieza: `estado` (`esperando_decisiones` / `confirmada` / `fallida`), investigador, fechas, `ruta_csv_limpio` (key en storage) y `reporte` JSONB (reporte_limpieza con decisiones). `UNIQUE (id_crudo, version)`. |
| Columna nueva `raw_data.raw_archivo_clave` | Clave de respuestas de las pruebas estandarizadas tabulares. Se eliminó en `2026_16_sin_clave` (las pruebas ya no se califican). |

---

## 2026-11 · Versiones del conocimiento (knowledge-service)

Migración: `migrations/2026_11_conocimiento.sql` (rollback: `2026_11_conocimiento_ROLLBACK.sql`).

| Cambio | Detalle |
|---|---|
| Tabla nueva `version_conocimiento` | Una fila por versión: `perfil` (perfil semántico, JSONB), `decisiones_kpi` (KPIs aceptados y rechazados con score, componentes, evidencia y justificación), `ruta_documento` (key del documento final en storage), `esquema_version`, `avisos`, `sha256`, `id_limpieza`, `id_usuario` y fechas por etapa. `estado`: `perfil_aprobado` / `kpis_confirmados` / `borrador` / `vigente` / `reemplazado`. `UNIQUE (id_crudo, version)`. |

---

## 2026-15 · Tiempos de cómputo de cada paso

Migración: `migrations/2026_15_tiempo_proceso.sql` (rollback: `2026_15_tiempo_proceso_ROLLBACK.sql`).

| Cambio | Detalle |
|---|---|
| Tabla nueva `tiempo_proceso` | Una fila por operación automática de un instrumento (carga, limpieza, metadatos, aprobación, perfil, KPIs, documento, indexación): `servicio`, `paso`, `inicio`, `fin`, `duracion_ms` y `detalle` JSONB. Borrado en cascada con `raw_data`. |

---

## 2026-16 · Las pruebas estandarizadas ya no se califican

Migración: `migrations/2026_16_sin_clave.sql` (rollback: `2026_16_sin_clave_ROLLBACK.sql`, que recrea la columna vacía).

| Cambio | Detalle |
|---|---|
| Columna eliminada `raw_data.raw_archivo_clave` | Indagata ya no recibe clave de respuestas: describe lo que contestaron los alumnos, sin marcar respuestas como correctas (25 oct 2026). |

---

## 2026-17 · Plan y tiempos por etapa en `rag_log`

Migración: `migrations/2026_17_rag_log_plan.sql` (rollback: `2026_17_rag_log_plan_ROLLBACK.sql`).

| Cambio | Detalle |
|---|---|
| Columna nueva `rag_log.plan` (JSONB) | Plan JSON de la etapa de interpretación del chat (intención, filtros, límite, campos…), con las correcciones del catálogo y del anclaje y los intentos (28 oct 2026). |
| Columna nueva `rag_log.tiempos` (JSONB) | Milisegundos de cada etapa: interpretación, ejecución, redacción y verificación. |

---

## 2026-18 · Evaluación por juez y calificación humana del chat

Migración: `migrations/2026_18_rag_evaluacion.sql` (rollback: `2026_18_rag_evaluacion_ROLLBACK.sql`).

| Cambio | Detalle |
|---|---|
| Tabla nueva `rag_metrica_juez` | Una evaluación (fidelidad, relevancia, precisión del contexto) por respuesta y por modelo juez, `UNIQUE (rag_log_id, modelo_juez)`. Permite que varios jueces califiquen las mismas respuestas (experimento redactor × juez, 28 oct 2026). `rag_log.metricas` conserva la del juez por defecto. |
| Tabla nueva `rag_calificacion` | Calificación humana de cada respuesta: `calificacion` 0–2 (mal, parcial, bien), `entendio`, `fundamenta` (NULL = no aplica), `comentario`, `usuario_id`. |

---

## 2026-19 · Se quitan las tablas sin uso

Migración: `migrations/2026_19_quitar_tablas_sin_uso.sql` (rollback: `2026_19_quitar_tablas_sin_uso_ROLLBACK.sql`, las vuelve a crear vacías).

| Tabla quitada | Por qué (las cuatro tenían 0 filas, 28 oct 2026) |
|---|---|
| `prompts` | Los prompts viven en el código (`visualization-service/services/prompt.py`); ningún servicio la leía ni la escribía. |
| `variable`, `kpi_variable` | `seed_kpis.py` nunca las llenó; el catálogo de KPIs mostraba siempre el texto de respaldo. Se quitó su lectura en `query_engine.catalogo_kpis`. |
| `valor_variable_inferido` | Ningún servicio la escribía ni la leía. |

Las secciones anteriores de este archivo son historia: mencionan estas tablas tal como existían entonces.

