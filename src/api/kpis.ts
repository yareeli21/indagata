import { kpis, noticias, catalogoKpis } from "@/mocks/data";
import { instrumentos } from "@/mocks/data";
import type { DatosGrafica, Kpi, KpiCatalogo, Noticia } from "@/types";
import { simularRed } from "./client";

export function getKpis(): Promise<Kpi[]> {
  return simularRed(kpis);
}

export function getNoticias(): Promise<Noticia[]> {
  return simularRed(noticias);
}

export function getCatalogoKpis(): Promise<KpiCatalogo[]> {
  return simularRed(catalogoKpis);
}

/**
 * Calcula datos de gráficas para un KPI dado un conjunto de instrumentos (fuentes).
 * Futuro: GET /kpis/{id}/datos?instrumentIds=...
 */
export function getDatosGrafica(
  kpiId: string,
  fuenteIds: string[],
): Promise<DatosGrafica | null> {
  const catalogoEntry = catalogoKpis.find((k) => k.id === kpiId);
  if (!catalogoEntry) return simularRed(null, 150);

  // Instrumentos de las fuentes que tienen este KPI por nombre
  const fuentes = instrumentos.filter(
    (i) => fuenteIds.includes(i.id) && i.kpis.includes(catalogoEntry.nombre),
  );

  if (fuentes.length === 0) return simularRed(null, 150);

  // ── Por nivel educativo (barras) ──
  const conteoNivel: Record<string, number> = {};
  for (const ins of fuentes) {
    conteoNivel[ins.nivel] = (conteoNivel[ins.nivel] ?? 0) + ins.reactivos;
  }
  const porNivel = Object.entries(conteoNivel).map(([etiqueta, valor]) => ({ etiqueta, valor }));

  // ── Por año (líneas) ──
  const conteoAnio: Record<number, number> = {};
  for (const ins of fuentes) {
    conteoAnio[ins.anio] = (conteoAnio[ins.anio] ?? 0) + ins.reactivos;
  }
  const porAnio = Object.entries(conteoAnio)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([etiqueta, valor]) => ({ etiqueta, valor }));

  // ── Por tipo de instrumento (dona) ──
  const conteoTipo: Record<string, number> = {};
  for (const ins of fuentes) {
    conteoTipo[ins.tipo] = (conteoTipo[ins.tipo] ?? 0) + 1;
  }
  const porTipo = Object.entries(conteoTipo).map(([etiqueta, valor]) => ({ etiqueta, valor }));

  return simularRed(
    { kpiId, porNivel, porAnio, porTipo, fuentesConteo: fuentes.length },
    300,
  );
}
