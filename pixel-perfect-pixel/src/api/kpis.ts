import { kpis, noticias, catalogoKpis } from "@/mocks/data";
import { instrumentos } from "@/mocks/data";
import { ICONOS_VALIDOS } from "@/features/kpis/iconos";
import type { DatosGrafica, Kpi, KpiCatalogo, Noticia } from "@/types";
import { ANALYSIS_URL, pedir, simularRed } from "./client";

/** DTO del catálogo real que devuelve analysis-service (8 campos, todos string). */
interface KpiCatalogoDTO {
  id: string;
  nombre: string;
  descripcion_ampliada_educativa: string;
  polaridad_rendimiento: string;
  tipo_objetivo_estrategico: string;
  formula_metrica_calculo: string;
  comportamiento_direccional_causalidad: string;
  razon_estrategica_decisiones: string;
}

// TODO: no hay endpoint de KPIs de tablero (p. ej. GET /kpis/tablero); queda mock.
export function getKpis(): Promise<Kpi[]> {
  return simularRed(kpis);
}

// TODO: no hay endpoint de noticias (p. ej. GET /noticias); queda mock.
export function getNoticias(): Promise<Noticia[]> {
  return simularRed(noticias);
}

/**
 * Catálogo de KPIs real: GET /vectorizacion/kpis/catalogo (analysis-service directo,
 * `auth: false`, igual que `espacio.ts`; el gateway NO proxea /vectorizacion/*).
 * Mapea cada `KpiCatalogoDTO` a `KpiCatalogo` (Opción B) con `mapearKpi`. Ante error
 * de red o respuesta vacía se degrada al mock para no dejar la página en blanco.
 */
export async function getCatalogoKpis(): Promise<KpiCatalogo[]> {
  let dtos: KpiCatalogoDTO[];
  try {
    dtos = await pedir<KpiCatalogoDTO[]>(`${ANALYSIS_URL}/vectorizacion/kpis/catalogo`, {
      auth: false,
    });
  } catch {
    // Fallback a mock ante fallo de red/servicio para no romper la página.
    return simularRed(catalogoKpis);
  }

  if (!dtos || dtos.length === 0) return simularRed(catalogoKpis);

  return dtos.map(mapearKpi);
}

/** Mapeo puro DTO → KpiCatalogo (Opción B, design.md §5.2). */
function mapearKpi(dto: KpiCatalogoDTO): KpiCatalogo {
  return {
    id: dto.id,
    nombre: dto.nombre,
    descripcionCorta: dto.descripcion_ampliada_educativa,
    queEs: dto.descripcion_ampliada_educativa,
    queMide: dto.comportamiento_direccional_causalidad,
    comoSeMide: dto.formula_metrica_calculo,
    formula: dto.formula_metrica_calculo,
    infoGeneral: dto.razon_estrategica_decisiones,
    etiquetas: derivarEtiquetas(dto.polaridad_rendimiento, dto.tipo_objetivo_estrategico),
    icono: elegirIcono(dto.nombre),
  };
}

/**
 * Deriva pocas etiquetas cortas (design.md §5.2): la primera palabra en MAYÚSCULAS
 * de `polaridad` y una etiqueta corta de `tipo` (texto antes del primer `/` o `(`,
 * recortado a ~24 caracteres). Filtra vacíos y deduplica.
 */
function derivarEtiquetas(polaridad: string, tipo: string): string[] {
  const etiquetas: string[] = [];

  const polaridadMatch = (polaridad ?? "").match(/^[A-ZÁÉÍÓÚÑ]+/);
  if (polaridadMatch) etiquetas.push(polaridadMatch[0]);

  const tipoCorto = (tipo ?? "").split(/[/(]/)[0].trim().slice(0, 24).trim();
  if (tipoCorto) etiquetas.push(tipoCorto);

  return [...new Set(etiquetas.filter((e) => e.length > 0))];
}

/**
 * Heurística de ícono (design.md §5.3): normaliza acentos (NFD) antes de comparar
 * el nombre contra claves sin acentos. Garantiza, con `ICONOS_VALIDOS`, que jamás
 * devuelve una clave fuera del mapa; el fallback es `BarChart2` (nunca `ChartBar`).
 */
function elegirIcono(nombre: string): string {
  const n = (nombre ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  let candidato = "BarChart2";
  if (/acredit|ranking|logro|premio/.test(n)) candidato = "Award";
  else if (/admis|selectiv|requisit/.test(n)) candidato = "ClipboardCheck";
  else if (/donaci|financ|coleg|matricula|fondo|ingreso|costo|beca/.test(n))
    candidato = "Briefcase";
  else if (/asistenc|graduaci|desercion|retencion|permanencia/.test(n)) candidato = "Users";
  else if (/clase|aula|docente|profesor|ensenanza/.test(n)) candidato = "BookOpen";
  else if (/formula|puntaje|calificacion|examen|prueba|calculo/.test(n)) candidato = "Calculator";
  else if (/segurid|bienestar|riesgo/.test(n)) candidato = "Shield";
  else if (/salud|socioemocional|psico/.test(n)) candidato = "Heart";
  else if (/satisfacc|clima/.test(n)) candidato = "Smile";
  else if (/monitor|pantalla/.test(n)) candidato = "Monitor";
  else if (/online|digital|plataforma|tecnolog/.test(n)) candidato = "Laptop";
  else if (/convenio|colaboraci|comunicaci/.test(n)) candidato = "MessageCircle";
  else if (/energia|eficiencia|producti/.test(n)) candidato = "Zap";
  else if (/campus|instalaci|infraestruc/.test(n)) candidato = "Home";

  return ICONOS_VALIDOS.has(candidato) ? candidato : "BarChart2";
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
