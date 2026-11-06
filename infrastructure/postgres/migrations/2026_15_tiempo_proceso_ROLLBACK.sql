-- Revierte 2026_15_tiempo_proceso.sql (borra los tiempos registrados).
SET search_path TO tt_rag, public;

BEGIN;
DROP TABLE IF EXISTS tiempo_proceso;
COMMIT;
