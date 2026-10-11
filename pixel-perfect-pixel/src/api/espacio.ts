import type { EspacioVectorial } from "@/types";
import { API_URL, pedir } from "./client";

/**
 * Obtiene la proyección 2D del espacio vectorial (colecciones kpis y
 * summary_instrument) del analysis-service por el api-gateway (que ya proxea
 * /vectorizacion/*).
 *
 * En modo desarrollo el endpoint resuelve el usuario sin token (auth:false).
 */
export function getEspacioVectorial(): Promise<EspacioVectorial> {
  return pedir<EspacioVectorial>(`${API_URL}/vectorizacion/espacio`, { auth: false });
}
