-- Quita cuatro tablas vacías que ningún flujo llenaba (28 oct 2026):
--   prompts                  los prompts viven en el código (visualization-service/services/prompt.py); nadie la leía.
--   variable, kpi_variable   el catálogo de KPIs nunca cargó variables (seed_kpis.py no las llena); la pantalla de KPIs
--                            usaba siempre el texto de respaldo «Se estima con los reactivos…».
--   valor_variable_inferido  ningún servicio la escribía ni la leía.
-- Las cuatro tenían 0 filas al quitarlas. El ROLLBACK las vuelve a crear vacías.
SET search_path TO tt_rag, public;

BEGIN;
DROP TABLE IF EXISTS valor_variable_inferido;
DROP TABLE IF EXISTS kpi_variable;
DROP TABLE IF EXISTS variable;
DROP TABLE IF EXISTS prompts;
COMMIT;
