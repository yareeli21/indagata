import type { MapaEspacio } from "@/types";
import { API_URL, pedir } from "./client";

interface OpcionesMapa {
  /** Incluir los chunks del RAG (fuente provisional por ahora). */
  chunks?: boolean;
}

/**
 * Mapa 2D del espacio de embeddings (KPIs, instrumentos y, opcionalmente,
 * chunks) proyectado con PCA. GET /visualizacion/espacio/mapa (visualization-service).
 */
export function getMapaEspacio({ chunks = false }: OpcionesMapa = {}): Promise<MapaEspacio> {
  return pedir<MapaEspacio>(`${API_URL}/visualizacion/espacio/mapa?chunks=${chunks}`, {
    auth: true,
  });
}
