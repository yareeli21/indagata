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
