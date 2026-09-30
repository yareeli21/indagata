import { instrumentos, investigadores } from "@/mocks/data";
import type { Instrumento, Investigador } from "@/types";
import { simularRed } from "./client";

export function getInstrumentos(): Promise<Instrumento[]> {
  return simularRed(instrumentos);
}

export function getInstrumento(id: string): Promise<Instrumento | null> {
  return simularRed(instrumentos.find((i) => i.id === id) ?? null);
}

export function getInvestigadores(): Promise<Investigador[]> {
  return simularRed(investigadores);
}
