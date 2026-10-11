import { API_URL, pedir } from "./client";

/**
 * Cliente de API del Grafo de Recomendación de Instrumentos.
 *
 * El api-gateway proxea /grafo/* hacia el analysis-service (igual que
 * `espacio.ts`). En modo desarrollo el servicio resuelve el usuario
 * sin token (auth:false).
 *
 * Dos espacios de identificadores: el grafo opera en `id` (= id_instrumento);
 * `/rag/index` opera en `idCrudo` (= id_crudo). Los nodos exponen ambos.
 */

export interface NodoGrafo {
  id: string;
  idCrudo: string;
  titulo: string;
  tipo: "Encuesta" | "Entrevista" | "Prueba estandarizada";
  autorId: string;
  autorNombre: string;
  kpis: string[];
  esPropio: boolean;
}

export interface AristaGrafo {
  origen: string;
  destino: string;
  tipo: "kpi_compartido";
  peso: number;
  kpis: string[];
}

export interface Recomendacion extends NodoGrafo {
  score: number;
  score_semantico: number;
  score_kpi: number;
  razon: string;
  kpis_compartidos: string[];
}

export interface RecomendarRequest {
  instrumentoIds: string[];
  autorId?: string;
  w_sem?: number;
  w_kpi?: number;
  top_n?: number;
  min_score?: number;
  excluir_propios?: boolean;
}

/** Grafo base del acervo: todos los instrumentos como nodos + aristas de KPI compartido. */
export function getAcervoGrafo(): Promise<{ nodos: NodoGrafo[]; aristas: AristaGrafo[] }> {
  return pedir<{ nodos: NodoGrafo[]; aristas: AristaGrafo[] }>(
    `${API_URL}/grafo/acervo`,
    { auth: false },
  );
}

/** Recomendaciones en tiempo real para un set activo de instrumentos. */
export function recomendarGrafo(req: RecomendarRequest): Promise<{
  recomendaciones: Recomendacion[];
  parametros: Record<string, number>;
  degradado_semantico: boolean;
}> {
  return pedir(`${API_URL}/grafo/recomendar`, {
    method: "POST",
    body: req,
    auth: false,
  });
}

/**
 * Persiste el snapshot del grafo de una investigación y devuelve los
 * `instrumentoIdsCrudo` (traducidos a id_crudo) para disparar /rag/index.
 */
export function guardarGrafoInvestigacion(req: {
  investigacionId: string;
  instrumentoIds: string[];
  grafo_snapshot: unknown;
}): Promise<{
  ok: boolean;
  investigacionId: string;
  grafoId: number;
  instrumentoIdsCrudo: string[];
}> {
  return pedir(`${API_URL}/grafo/investigacion`, {
    method: "POST",
    body: req,
    auth: false,
  });
}
