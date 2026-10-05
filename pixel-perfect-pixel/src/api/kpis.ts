import { kpis, noticias, catalogoKpis } from "@/mocks/data";
import { instrumentos } from "@/mocks/data";
import type { DatosGrafica, Kpi, KpiCatalogo, Noticia } from "@/types";
import { API_URL, pedir, simularRed } from "./client";

// TODO: no hay endpoint de KPIs de tablero (p. ej. GET /kpis/tablero); queda mock.
export function getKpis(): Promise<Kpi[]> {
  return simularRed(kpis);
}

// TODO: no hay endpoint de noticias (p. ej. GET /noticias); queda mock.
export function getNoticias(): Promise<Noticia[]> {
  return simularRed(noticias);
}

/**
 * Catálogo de KPIs real: GET /instrumentos/kpis/catalogo (gateway) → list[str]
 * (unión de nombres de KPIs de los instrumentos). El backend solo expone NOMBRES;
 * `KpiCatalogo` es más rico, así que los campos de texto quedan vacíos con TODO.
 * Si la respuesta viene vacía (p. ej. antes de confirmar KPIs) se degrada a mock
 * para no dejar la página en blanco.
 */
export async function getCatalogoKpis(): Promise<KpiCatalogo[]> {
  let nombres: string[] = [];
  try {
    nombres = await pedir<string[]>(`${API_URL}/instrumentos/kpis/catalogo`, { auth: true });
  } catch {
    // Fallback a mock ante fallo de red/servicio para no romper la página.
    return simularRed(catalogoKpis);
  }

  if (!nombres || nombres.length === 0) return simularRed(catalogoKpis);

  // Mapeo list[str] → KpiCatalogo[]. TODO: no hay endpoint con la descripción
  // detallada del KPI (tt_rag.kpi tiene descripcion/categoria/ambito/formula, pero
  // no se expone); falta un GET /instrumentos/kpis/catalogo-detallado.
  return nombres.map((nombre) => ({
    id: nombre.toLowerCase().replace(/\s+/g, "-"),
    nombre,
    descripcionCorta: "",
    queEs: "",
    queMide: "",
    comoSeMide: "",
    formula: "",
    infoGeneral: "",
    icono: "ChartBar",
    etiquetas: [],
  }));
}

/**
 * Calcula datos de gráficas para un KPI dado un conjunto de instrumentos (fuentes).
 * TODO: no hay endpoint de datos de gráfica (p. ej. GET /kpis/{id}/datos?instrumentIds=...);
 * queda mock.
 */
export function getDatosGrafica(kpiId: string, fuenteIds: string[]): Promise<DatosGrafica | null> {
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

  return simularRed({ kpiId, porNivel, porAnio, porTipo, fuentesConteo: fuentes.length }, 300);
}
