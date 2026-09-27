# API — Routers

> Flujo vigente del wizard de carga. Sustituye a la versión anterior, que documentaba
> los endpoints `etl/extract` y `etl/approve` y el estado `etl_pendiente` (flujo antiguo, ya reemplazado).

## Endpoints disponibles

### **Carga de instrumentos** (`routers_carga.py`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/instrumentos/upload` | POST | Subir archivo (.csv, .xlsx, .sav, .pdf) + tipo de instrumento. Codebook opcional (encuestas). |
| `/instrumentos/{id}/metadata/init` | GET | Obtener metadatos autocompletados (para pre-poblar el formulario) |
| `/instrumentos/{id}/metadata` | POST | Registrar los 13 metadatos Dublin Core (7 manuales). Inmutable |
| `/instrumentos/{id}/analyze` | POST | Analizar con el SIS (limpieza, profiling, enriquecimiento, KPIs, mejoras) ⚠️ requiere Ollama |
| `/instrumentos/{id}/etl/proposals` | GET | Ver propuestas generadas por el SIS (idempotente) |
| `/instrumentos/{id}/approve/cleaning` | POST | Paso 4a — decidir propuestas de limpieza (transformaciones) |
| `/instrumentos/{id}/approve/enrichment` | POST | Paso 4b — decidir metadatos enriquecidos + KPIs. Genera JSON consolidado (y .SAV si es encuesta) |

> **Nota:** el endpoint `POST /instrumentos/ingesta` está **deshabilitado (comentado)** en `routers_carga.py`.
> No es código muerto: es un punto de extensión reservado para el **módulo de vectorización futuro**,
> que procesará instrumentos en estado `etl_aprobado`.

### **Visualización de instrumentos** (`routers_visualizacion.py`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/kpis` | GET | Catálogo de KPIs disponibles |
| `/instrumentos` | GET | Listar instrumentos (con filtros) |
| `/instrumentos/{id}` | GET | Detalle completo del instrumento |
| `/instrumentos/{id}/download` | GET | Descargar (`?type=original\|json\|sav`) |
| `/instrumentos/{id}` | DELETE | Eliminar instrumento (solo propietario) |

---

## Flujo wizard de carga (vigente)

```
1. upload → archivo + tipo (+ codebook opcional en encuestas)
   Estado: pendiente

2. metadata/init → autocompletados
   metadata → 7 campos manuales
   Estado: metadata_registrado

3. analyze → ejecuta el SIS completo (S1..S9, requiere Ollama)
   Persiste propuestas de limpieza, metadatos enriquecidos, KPIs y mejoras.
   Estado: etl_pendiente_limpieza
   (Reanalizable: puede repetirse desde 'metadata_registrado' o 'etl_pendiente_limpieza')

4a. approve/cleaning → decidir transformaciones (drop_columns, normalize_scale)
    Genera el dataset limpio.
    Estado: etl_pendiente_enriquecimiento

4b. approve/enrichment → decidir metadatos enriquecidos + KPIs
    Genera storage/json/{id}.json (consolidado) y, si es encuesta, el .SAV.
    Estado: etl_aprobado ✅
```

> **Estado final del módulo de carga:** `etl_aprobado`. El JSON consolidado queda disponible para descarga.
> La transición a `vectorizado` corresponde al futuro módulo de vectorización (RAG principal), aún no implementado.

---

## Permisos

### **Lectura (público):**
- ✅ Todos pueden ver/descargar cualquier instrumento (RAG colaborativo)

### **Escritura (solo propietario):**
- ✅ Analizar y aprobar (cleaning/enrichment)
- ✅ Eliminar instrumento

### **Eliminación:**
Operación irreversible que borra:
- Registro en BD + archivos en disco
- (El borrado en ChromaDB es un no-op hoy; se activará con el módulo de vectorización)
- Para modificar: eliminar y re-subir

---

## Autenticación (estado actual y futuro)

> **Modo desarrollo.** `get_current_user` en `dependencies_instrumentos.py` devuelve un usuario fijo
> (`_DEV_USER_ID = 1`) sin pedir token. El bloque de **autenticación real (JWT)** ya está escrito pero
> comentado: **NO es código muerto**, es funcionalidad futura pendiente de integración. Se activará cuando
> exista `POST /auth/token`. Ver `backend/README.md` para el procedimiento de reactivación.

---

## Testing

- **Swagger UI:** http://localhost:8000/docs
- **Timeout:** el paso `analyze` (SIS + Ollama) puede tardar 30-180s (configurar timeout en el cliente: 300000ms)

---

## Errores comunes

| Código | Causa | Solución |
|--------|-------|----------|
| 404 | Instrumento no existe | Verificar ID con `GET /instrumentos` |
| 409 | Estado incorrecto para el paso | Revisar estado actual con `GET /instrumentos/{id}` |
| 422 | El SIS no pudo procesar el archivo (ilegible/vacío) | Revisar el archivo subido |
| 403 | Sin permiso de propietario | Usar el usuario creador |
| 500 | Ollama no responde (paso `analyze`) | Verificar `http://localhost:11434` |

---

## Documentación relacionada

- **Visión general del backend y capas:** `../../README.md`
- **Auditoría arquitectónica:** `../../ARCHITECTURE_AUDIT_REPORT.md`
- **Arquitectura del SIS y extensión por instrumento:** `../../survey_intelligence/docs/ARQUITECTURA_SIS.md`, `../../survey_intelligence/docs/GUIA_EXTENSION_INSTRUMENTOS.md`
