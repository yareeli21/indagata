import type { DatosGrafica, Kpi, KpiCatalogo, NoticiasRespuesta } from "@/types";
import { API_URL, ErrorHttp, pedir } from "./client";

/**
 * Métricas del acervo (instrumentos, aprobados para el RAG, KPIs con evidencia,
 * consultas al RAG). GET /visualizacion/kpis/resumen
 */
export async function getKpis(): Promise<Kpi[]> {
  try {
    return await pedir<Kpi[]>(`${API_URL}/visualizacion/kpis/resumen`, { auth: true });
  } catch {
    return []; // sin métricas la tira simplemente no se muestra
  }
}

/**
 * Noticias reales de educación e investigación (RSS de medios y organismos, y GNews
 * si el servidor tiene clave). Sin conexión llega una lista vacía con `aviso`: nunca
 * se muestran noticias inventadas. GET /visualizacion/noticias[?actualizar=true]
 */
export async function getNoticias(actualizar = false): Promise<NoticiasRespuesta> {
  try {
    return await pedir<NoticiasRespuesta>(
      `${API_URL}/visualizacion/noticias${actualizar ? "?actualizar=true" : ""}`,
      { auth: true },
    );
  } catch {
    return { noticias: [], actualizado: null, aviso: "No se pudieron cargar las noticias." };
  }
}

/**
 * Catálogo de KPIs (tabla `kpi`, con sus variables) y cuántos instrumentos del
 * acervo están asociados a cada uno. GET /visualizacion/kpis/catalogo
 */
export async function getCatalogoKpis(): Promise<KpiCatalogo[]> {
  try {
    return await pedir<KpiCatalogo[]>(`${API_URL}/visualizacion/kpis/catalogo`, { auth: true });
  } catch {
    return [];
  }
}

/**
 * Dashboard de un KPI sobre las fuentes de la investigación activa: agregados por
 * nivel, año y tipo, y las preguntas de cada instrumento que miden el KPI.
 * POST /visualizacion/kpis/{kpiId}/datos
 */
export async function getDatosGrafica(
  kpiId: string,
  fuenteIds: string[],
): Promise<DatosGrafica | null> {
  try {
    return await pedir<DatosGrafica>(
      `${API_URL}/visualizacion/kpis/${encodeURIComponent(kpiId)}/datos`,
      {
        method: "POST",
        auth: true,
        body: { instrumentoIds: fuenteIds },
      },
    );
  } catch (e) {
    if ((e as ErrorHttp).status === 404) return null;
    throw e;
  }
}
