-- ============================================================================
-- RESET de instrumentos para re-analizar con el flujo SIS corregido.
-- Deja los instrumentos en 'metadata_registrado' y borra el análisis previo
-- (propuestas duplicadas, KPIs, metadatos enriquecidos, mejoras, JSON/SAV).
--
-- NO borra: el instrumento, sus metadatos DC, ni el archivo original.
--
-- Ejecutar:
--   $env:PGPASSWORD='ttaprobado'
--   psql -h localhost -U postgres -d aprende_rag -v ON_ERROR_STOP=1 -f postgres/migrations/reset_instrumentos_sis.sql
-- ============================================================================

SET search_path TO tt_rag, public;

BEGIN;

-- Borrar análisis previo de TODOS los instrumentos.
DELETE FROM etl_propuesta;
DELETE FROM kpi_inferido WHERE origen = 'propuesta_etl';
DELETE FROM metadatos_enriquecidos;
DELETE FROM improvement_opportunity;

-- Volver los instrumentos ya procesados al punto previo al análisis.
UPDATE instrumento_procesado
SET estado = 'metadata_registrado',
    ruta_json = NULL,
    ruta_sav  = NULL
WHERE estado IN ('etl_aprobado', 'etl_pendiente_limpieza', 'etl_pendiente_enriquecimiento');

COMMIT;

-- Verificación:
SELECT instrumento_id, tipo_instrumento, estado FROM instrumento_procesado ORDER BY instrumento_id;
