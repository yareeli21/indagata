import type { Instrumento, NivelEducativo, TipoInstrumento } from "@/types";

export interface Filtros {
  palabra: string;
  kpis: string[];
  nivel: NivelEducativo | null;
  tipo: TipoInstrumento | null;
  desde: string;
  hasta: string;
}

export const FILTROS_VACIOS: Filtros = { palabra: "", kpis: [], nivel: null, tipo: null, desde: "", hasta: "" };

export function aplicarFiltros(lista: Instrumento[], f: Filtros): Instrumento[] {
  const q = f.palabra.trim().toLowerCase();
  return lista.filter((i) => {
    if (q && ![i.titulo, i.descripcion, ...i.etiquetas].some((t) => t.toLowerCase().includes(q))) return false;
    if (f.kpis.length && !f.kpis.some((k) => i.kpis.includes(k))) return false;
    if (f.nivel && i.nivel !== f.nivel) return false;
    if (f.tipo && i.tipo !== f.tipo) return false;
    if (f.desde && i.fecha < f.desde) return false;
    if (f.hasta && i.fecha > f.hasta) return false;
    return true;
  });
}

export function hayFiltros(f: Filtros): boolean {
  return !!(f.palabra.trim() || f.kpis.length || f.nivel || f.tipo || f.desde || f.hasta);
}

export function formatearFecha(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
}
