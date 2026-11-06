-- Revierte 2026_18_rag_evaluacion.sql (borra las evaluaciones por juez y las calificaciones humanas).
SET search_path TO tt_rag, public;

BEGIN;
DROP TABLE IF EXISTS rag_calificacion;
DROP TABLE IF EXISTS rag_metrica_juez;
COMMIT;
