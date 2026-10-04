-- ============================================================================
-- DEMO / THROWAWAY  -- Filas padre raw_data + instrumento_procesado para los 21
-- instrumentos (encuestas inst_01..inst_21) usados en la asociación de KPIs.
-- ----------------------------------------------------------------------------
-- raw_data (NOT NULL: id_owner, tipo_instrumento, nombre_archivo, raw_archivo)
--   id_owner = 1 (admin@indagata.local)
--   tipo_instrumento = 'encuesta'
--   nombre_archivo = inst_NN.v1.json
--   raw_archivo = /app/storage/raw/inst_NN.v1.json
--   raw_archivo_original = /app/storage/raw/inst_NN.md
-- instrumento_procesado (NOT NULL sin default: id_crudo; estado default 'recibido')
--   id_crudo = raw_data recién creado; ruta_json = /app/storage/raw/inst_NN.v1.json
-- Idempotente: limpia primero. Datos de demostración; se reemplazarán por reales.
-- ============================================================================
SET search_path TO tt_rag, public;

TRUNCATE instrumento_procesado RESTART IDENTITY CASCADE;
TRUNCATE raw_data RESTART IDENTITY CASCADE;

DO $$
DECLARE
    n       int;
    nn      text;
    v_crudo int;
BEGIN
    FOR n IN 1..21 LOOP
        nn := lpad(n::text, 2, '0');
        INSERT INTO raw_data (id_owner, tipo_instrumento, nombre_archivo, raw_archivo, raw_archivo_original)
        VALUES (
            1,
            'encuesta',
            format('inst_%s.v1.json', nn),
            format('/app/storage/raw/inst_%s.v1.json', nn),
            format('/app/storage/raw/inst_%s.md', nn)
        )
        RETURNING id_crudo INTO v_crudo;

        INSERT INTO instrumento_procesado (id_crudo, estado, ruta_json)
        VALUES (
            v_crudo,
            'recibido',
            format('/app/storage/raw/inst_%s.v1.json', nn)
        );
    END LOOP;
END $$;

-- Mapeo inst_NN -> id_instrumento (lo consume el paso de vectorización).
SELECT ip.id_instrumento, rd.nombre_archivo
FROM instrumento_procesado ip
JOIN raw_data rd ON rd.id_crudo = ip.id_crudo
ORDER BY ip.id_instrumento;
