-- 2026_21 — Nivel educativo «Licenciatura» en los instrumentos ya cargados (15 nov 2026).
--
-- La carga solo admite instrumentos de licenciatura (StepDublinCore / UploadWizard fijan «Licenciatura»), pero
-- los instrumentos anteriores conservaban niveles inferidos («Posgrado», «Secundaria», «No especificado»…).
-- Solo cambia el parámetro del nivel; no toca el resto de los metadatos ni re-vectoriza:
--   * metadatos_dc.dc_coverage           «<nivel> — <detalle>» → «Licenciatura — <detalle>»; sin detalle → «Licenciatura»
--   * version_conocimiento.perfil        nivel_educativo → «Licenciatura» (todas las versiones)
--   * metadatos_enriquecidos_pruebas     nivel_educativo → «Licenciatura»
--   * documento_vectorizado              línea «Nivel educativo: …» de la ficha y chunk_metadata.nivel
-- Las mismas dos cosas de documento_vectorizado se cambian en Chroma con
-- services/storage-service/scripts/nivel_licenciatura_chroma.py (conserva los embeddings).
--
-- Idempotente. Sin ROLLBACK automático: el respaldo de las tablas está en storage/_respaldos/nivel_2026-11-15/.
-- Aplicar: docker compose exec postgres psql -U postgres -d indagata_db -v ON_ERROR_STOP=1 -f /migrations/2026_21_nivel_licenciatura.sql

BEGIN;

-- Cobertura con un nivel al inicio y un detalle tras « — » o « – »: se conserva el detalle.
UPDATE tt_rag.metadatos_dc
SET dc_coverage = 'Licenciatura — ' || btrim(regexp_replace(dc_coverage, '^[^—–]*[—–]', ''))
WHERE dc_coverage ~* '^\s*(posgrado|media superior|bachillerato|secundaria|primaria|preescolar|no especificado)'
  AND dc_coverage ~ '\s[—–]\s';

-- Todo lo demás que no empiece con «Licenciatura» (niveles sin detalle, vacíos o texto que no es un nivel).
UPDATE tt_rag.metadatos_dc
SET dc_coverage = 'Licenciatura'
WHERE dc_coverage IS NULL OR trim(dc_coverage) = '' OR dc_coverage !~* '^\s*licenciatura';

UPDATE tt_rag.version_conocimiento
SET perfil = jsonb_set(perfil, '{nivel_educativo}', '"Licenciatura"')
WHERE perfil->>'nivel_educativo' IS DISTINCT FROM 'Licenciatura';

UPDATE tt_rag.metadatos_enriquecidos_pruebas
SET nivel_educativo = 'Licenciatura'
WHERE nivel_educativo IS DISTINCT FROM 'Licenciatura';

UPDATE tt_rag.documento_vectorizado
SET chunk_texto = regexp_replace(chunk_texto, 'Nivel educativo: [^\n]*', 'Nivel educativo: Licenciatura', 'g')
WHERE chunk_texto ~ 'Nivel educativo: ' AND chunk_texto !~ 'Nivel educativo: Licenciatura(\n|$)';

UPDATE tt_rag.documento_vectorizado
SET chunk_metadata = jsonb_set(chunk_metadata, '{nivel}', '"Licenciatura"')
WHERE chunk_metadata ? 'nivel' AND chunk_metadata->>'nivel' <> 'Licenciatura';

COMMIT;
