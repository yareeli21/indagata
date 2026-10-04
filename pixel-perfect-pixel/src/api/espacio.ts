import type { EspacioVectorial } from "@/types";
import { ANALYSIS_URL, pedir } from "./client";

/**
 * Obtiene la proyección 2D del espacio vectorial (colecciones kpis y
 * summary_instrument) desde analysis-service. El api-gateway NO proxea
 * /vectorizacion/*, por eso se llama directo a ANALYSIS_URL.
 *
 * En modo desarrollo el endpoint resuelve el usuario sin token (auth:false).
 */
export function getEspacioVectorial(): Promise<EspacioVectorial> {
  return pedir<EspacioVectorial>(`${ANALYSIS_URL}/vectorizacion/espacio`, { auth: false });
}
