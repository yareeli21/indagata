-- Búsqueda híbrida del chat (11 nov 2026): índice de texto completo en español sobre el texto de cada fragmento
-- indexado. visualization-service/services/hibrida.py busca con to_tsvector('spanish', chunk_texto) y combina el
-- resultado con la búsqueda semántica de Chroma (RRF). No cambia datos; se puede aplicar en caliente.
-- Aplicar: docker compose exec postgres psql -U postgres -d indagata_db -f /migrations/2026_20_busqueda_hibrida.sql
CREATE INDEX IF NOT EXISTS idx_documento_vectorizado_texto
    ON tt_rag.documento_vectorizado USING gin (to_tsvector('spanish', chunk_texto));
