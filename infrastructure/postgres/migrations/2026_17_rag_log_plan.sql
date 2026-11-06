-- Rediseño del chat en cuatro etapas (28 oct 2026): cada consulta guarda el plan de la etapa de interpretación
-- y el tiempo de cada etapa (interpretación, ejecución, redacción, verificación).
SET search_path TO tt_rag, public;

BEGIN;
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS plan    JSONB;  -- plan validado, correcciones e intentos
ALTER TABLE rag_log ADD COLUMN IF NOT EXISTS tiempos JSONB;  -- {"interpretacion": ms, "ejecucion": ms, …}
COMMIT;
