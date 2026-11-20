-- Diccionario de datos de un instrumento (14 nov 2026): archivo opcional que acompaña a los microdatos
-- (variable, pregunta, valor y etiqueta). La limpieza lo lee para dar texto a las preguntas en código y
-- significado a sus códigos de respuesta. Columna nueva y opcional: no cambia datos; se puede aplicar en caliente.
-- Aplicar: docker compose exec postgres psql -U postgres -d indagata_db -f /migrations/2026_21_diccionario_datos.sql
ALTER TABLE tt_rag.raw_data ADD COLUMN IF NOT EXISTS raw_archivo_diccionario TEXT;
