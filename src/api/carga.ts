import { kpisSugeridosEjemplo, reporteLimpiezaEjemplo } from "@/mocks/carga";
import type { KpiSugerido, ReporteLimpieza } from "@/types";
import { simularRed } from "./client";

/** Futuro: POST /instrumentos/limpieza con el archivo. */
export function limpiarArchivo(_archivo: File): Promise<ReporteLimpieza> {
  return simularRed(reporteLimpiezaEjemplo, 700);
}

/** Futuro: POST /kpis/sugeridos con la descripción del instrumento. */
export function getKpisSugeridos(_descripcion: string): Promise<KpiSugerido[]> {
  return simularRed(kpisSugeridosEjemplo, 600);
}

/** Futuro: POST /instrumentos con el JSON final. */
export function guardarInstrumento(documento: unknown): Promise<{ id: string }> {
  void documento;
  return simularRed({ id: `ins-${Date.now()}` }, 800);
}
