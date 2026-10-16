import type {
  DocumentoGenerado,
  DublinCore,
  KpiPropuesto,
  MetadatosTipo,
  PerfilGenerado,
  PropuestaKpis,
} from "@/types";
import { dublinCoreAPayload } from "./carga";
import { ANALYSIS_URL, API_URL, pedir } from "./client";

/**
 * Conocimiento del instrumento (knowledge-service vía api-gateway, prefijo `/conocimiento`).
 *
 * El perfil semántico describe el instrumento (sin métricas, respuestas ni datos
 * técnicos) y es lo único que se usa para asociar KPIs.
 */

/** Perfil con los metadatos del formulario, sin guardar (paso «Aprobar metadatos»). */
export function previsualizarPerfil(
  idCrudo: number,
  dc: DublinCore,
  meta: MetadatosTipo,
): Promise<PerfilGenerado> {
  return pedir<PerfilGenerado>(`${API_URL}/conocimiento/${idCrudo}/perfil/vista-previa`, {
    method: "POST",
    auth: true,
    body: { dublin_core: dublinCoreAPayload(dc), enriquecidos: meta },
  });
}

/** Genera y guarda el perfil con los metadatos ya aprobados (crea una versión nueva). */
export function generarPerfil(idCrudo: number): Promise<PerfilGenerado> {
  return pedir<PerfilGenerado>(`${API_URL}/conocimiento/${idCrudo}/perfil`, {
    method: "POST",
    auth: true,
  });
}

/** Perfil de la versión actual del instrumento. */
export function getPerfil(idCrudo: number): Promise<PerfilGenerado> {
  return pedir<PerfilGenerado>(`${API_URL}/conocimiento/${idCrudo}/perfil`, { auth: true });
}

// ── KPIs desde el perfil (analysis-service directo, con el JWT) ──────────────────

/** KPIs sugeridos para el perfil de la versión actual: puntaje, evidencia y justificación. */
export function proponerKpisPerfil(idCrudo: number): Promise<PropuestaKpis> {
  return pedir<PropuestaKpis>(`${ANALYSIS_URL}/vectorizacion/perfil/propuestas`, {
    method: "POST",
    auth: true,
    body: { id_crudo: idCrudo },
  });
}

export interface DecisionKpiPerfil {
  kpi: KpiPropuesto;
  aceptado: boolean;
  /** Justificación final (la sugerida o la editada por el investigador). */
  justificacion: string;
}

/** Guarda aceptados y rechazados en la versión del conocimiento. */
export function confirmarKpisPerfil(
  idCrudo: number,
  version: number,
  decisiones: DecisionKpiPerfil[],
): Promise<{ estado: string; kpis_asociados: { kpi_id: string; nombre: string }[] }> {
  return pedir(`${ANALYSIS_URL}/vectorizacion/perfil/confirmar`, {
    method: "POST",
    auth: true,
    body: {
      id_crudo: idCrudo,
      version,
      decisiones: decisiones.map(({ kpi, aceptado, justificacion }) => ({
        kpi_id: kpi.kpi_id,
        aceptado,
        score: kpi.score,
        componentes: kpi.componentes,
        evidencia: kpi.evidencia.map((e) => ({
          pregunta_id: e.pregunta_id,
          similitud: e.similitud,
        })),
        justificacion,
        justificacion_origen: kpi.justificacion_origen,
        editada: justificacion.trim() !== kpi.justificacion.trim(),
      })),
    },
  });
}

// ── Documento final (knowledge-service vía api-gateway) ────────────────────────────

/** Genera, valida y guarda el documento final de la versión actual (queda en borrador). */
export function generarDocumento(idCrudo: number): Promise<DocumentoGenerado> {
  return pedir<DocumentoGenerado>(`${API_URL}/conocimiento/${idCrudo}/documento`, {
    method: "POST",
    auth: true,
  });
}

/** Documento final completo, con todas las respuestas («Ver JSON»). */
export function getDocumentoJson(idCrudo: number): Promise<Record<string, unknown>> {
  return pedir<Record<string, unknown>>(`${API_URL}/conocimiento/${idCrudo}/documento/json`, {
    auth: true,
  });
}

/** Publica el documento (vigente); la versión vigente anterior pasa a reemplazada. */
export function publicarDocumento(idCrudo: number, version: number): Promise<{ estado: string }> {
  return pedir(`${API_URL}/conocimiento/${idCrudo}/documento/${version}/publicar`, {
    method: "POST",
    auth: true,
  });
}
