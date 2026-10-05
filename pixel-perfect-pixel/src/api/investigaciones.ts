import { investigaciones } from "@/mocks/data";
import type { Investigacion } from "@/types";
import { simularRed } from "./client";

export function getInvestigaciones(): Promise<Investigacion[]> {
  return simularRed(investigaciones);
}

export function crearInvestigacion(nombre: string, propietarioId: string): Promise<Investigacion> {
  const nueva: Investigacion = {
    id: `res-${Date.now()}`,
    nombre,
    propietarioId,
  };
  return simularRed(nueva, 200);
}
