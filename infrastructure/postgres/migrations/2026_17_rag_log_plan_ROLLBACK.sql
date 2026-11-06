-- Revierte 2026_17_rag_log_plan.sql (borra los planes y tiempos registrados).
SET search_path TO tt_rag, public;

BEGIN;
ALTER TABLE rag_log DROP COLUMN IF EXISTS tiempos;
ALTER TABLE rag_log DROP COLUMN IF EXISTS plan;
COMMIT;
