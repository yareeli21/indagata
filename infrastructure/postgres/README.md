# PostgreSQL - Indagata

## Estructura

```
postgres/
├── init/
│   ├── 01_schema.sql        # Schema v2.0 (actualizado 2026-09-17)
│   ├── 01_schema_BACKUP.sql # Schema anterior (referencia)
│   └── 04_seed.sql          # Datos maestros (usuarios, KPIs, variables)
├── migrations/
│   └── 03_remove_visibilidad.sql  # Migración histórica
├── SCHEMA_CHANGES.md        # Análisis de cambios del schema
└── README.md
```

---

## Schema v2.0 - Cambios Principales

### **✅ Agregado:**
- Tabla `etl_propuesta` - Propuestas del LLM
- Tabla `metadatos_enriquecidos` - Campos adicionales (JSONB)
- Tabla `kpi_inferido` - KPIs detectados

### **❌ Eliminado:**
- Campo `visibilidad` en `instrumento_procesado`
- Campos `dc_contributor` y `dc_identifier` en `metadatos_dc`

### **🔧 Modificado:**
- Estados ETL: +2 estados (`etl_pendiente`, `etl_aprobado`)
- `ruta_texto_limpio`: Caché de texto extraído

**Ver detalles completos:** `SCHEMA_CHANGES.md`

---

## Inicio rapido

### **1. Iniciar PostgreSQL:**

```powershell
Start-Service -Name postgresql-x64-18
```

### **2. Conectar a la BD:**

```powershell
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag
```

### **3. Recrear BD desde cero:**

```powershell
# a) Backup de datos maestros (opcional)
$env:PGPASSWORD='ttaprobado'; pg_dump -h localhost -U postgres -d aprende_rag -t tt_rag.kpi -t tt_rag.variable -t tt_rag.kpi_variable -t tt_rag.valor_variable -t tt_rag.instituciones -t tt_rag.usuarios > backup_maestras.sql

# b) Drop schema
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -c "DROP SCHEMA IF EXISTS tt_rag CASCADE;"

# c) Recrear schema
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -f postgres\init\01_schema.sql

# d) Cargar datos maestros
$env:PGPASSWORD='ttaprobado'; psql -h localhost -U postgres -d aprende_rag -f postgres\init\04_seed.sql
```

---

## Consultas utiles

### **Ver instrumentos:**
```sql
SELECT instrumento_id, nombre, tipo_instrumento, estado 
FROM tt_rag.instrumento_procesado;
```

### **Ver propuestas ETL:**
```sql
SELECT propuesta_id, tipo, estado_decision, descripcion
FROM tt_rag.etl_propuesta
WHERE instrumento_id = 1;
```

### **Ver KPIs inferidos:**
```sql
SELECT ki.instrumento_id, k.nombrekpi, ki.origen, ki.score_inferencia
FROM tt_rag.kpi_inferido ki
JOIN tt_rag.kpi k ON ki.kpi_id = k.kpi_id;
```

### **Estadisticas:**
```sql
SELECT 'usuarios' as tabla, COUNT(*) as registros FROM tt_rag.usuarios
UNION ALL SELECT 'kpi', COUNT(*) FROM tt_rag.kpi
UNION ALL SELECT 'variable', COUNT(*) FROM tt_rag.variable
UNION ALL SELECT 'instrumentos', COUNT(*) FROM tt_rag.instrumento_procesado
UNION ALL SELECT 'propuestas_etl', COUNT(*) FROM tt_rag.etl_propuesta;
```

---

## Conexion

- **Host:** localhost
- **Puerto:** 5432
- **Usuario:** postgres
- **Password:** ttaprobado
- **Base de datos:** aprende_rag
- **Schema:** tt_rag

---

## Estado actual (v2.0)

- ✅ 18 tablas activas
- ✅ 3 tablas nuevas (ETL workflow)
- ✅ Sin campo `visibilidad` (todo público)
- ✅ 13 campos Dublin Core estándar
- ✅ JSON consolidado con transformaciones
- ✅ Caché de texto con hash SHA256


