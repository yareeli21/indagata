-- Deshace 2026_20_busqueda_hibrida.sql (sin el índice, la búsqueda por palabras sigue funcionando, más lenta).
DROP INDEX IF EXISTS tt_rag.idx_documento_vectorizado_texto;
