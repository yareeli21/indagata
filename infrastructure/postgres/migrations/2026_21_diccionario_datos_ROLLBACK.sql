-- Deshace 2026_21_diccionario_datos.sql (los instrumentos pierden la referencia a su diccionario de datos; los
-- significados ya aplicados siguen en el reporte de su limpieza).
ALTER TABLE tt_rag.raw_data DROP COLUMN IF EXISTS raw_archivo_diccionario;
