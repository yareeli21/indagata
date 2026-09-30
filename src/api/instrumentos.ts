import { instrumentos, investigadores } from "@/mocks/data";
import type { FormatoDescarga, Instrumento, Investigador } from "@/types";
import { simularRed } from "./client";

export function getInstrumentos(): Promise<Instrumento[]> {
  return simularRed([...instrumentos]);
}

export function getInstrumento(id: string): Promise<Instrumento | null> {
  return simularRed(instrumentos.find((i) => i.id === id) ?? null);
}

export function getInvestigadores(): Promise<Investigador[]> {
  return simularRed(investigadores);
}

/** Catálogo de KPIs usados por los instrumentos. Futuro: GET /kpis/catalogo */
export function getCatalogoKpis(): Promise<string[]> {
  return simularRed([...new Set(instrumentos.flatMap((i) => i.kpis))].sort());
}

/** Futuro: DELETE /instrumentos/{id} (borra también todo lo asociado). */
export function eliminarInstrumento(id: string): Promise<void> {
  const idx = instrumentos.findIndex((i) => i.id === id);
  if (idx >= 0) instrumentos.splice(idx, 1);
  return simularRed(undefined, 500);
}

/** Futuro: GET /instrumentos/{id}/descarga?formato=... */
export function descargarInstrumento(id: string, formato: FormatoDescarga): Promise<void> {
  const ins = instrumentos.find((i) => i.id === id);
  if (ins) {
    const contenido = formato === "json" ? JSON.stringify(ins, null, 2) : `${ins.titulo}\n\n${ins.descripcion}`;
    const ext = formato === "crudo" ? "txt" : formato;
    const url = URL.createObjectURL(new Blob([contenido]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ins.id}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }
  return simularRed(undefined, 200);
}
