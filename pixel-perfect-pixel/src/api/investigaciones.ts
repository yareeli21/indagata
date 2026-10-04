import type { Investigacion } from "@/types";

/**
 * No hay servicio de investigaciones en el backend de esta tanda. La lista se
 * persiste en el cliente (localStorage) para que el flujo "crear investigación →
 * juntar instrumentos → chatear" sea real de punta a punta. Las firmas no cambian.
 */
const CLAVE_INVESTIGACIONES = "indagata.investigaciones";

function leerInvestigaciones(): Investigacion[] {
  try {
    const crudo = window.localStorage.getItem(CLAVE_INVESTIGACIONES);
    if (!crudo) return [];
    const datos = JSON.parse(crudo) as Investigacion[];
    return Array.isArray(datos) ? datos : [];
  } catch {
    return [];
  }
}

function escribirInvestigaciones(lista: Investigacion[]): void {
  try {
    window.localStorage.setItem(CLAVE_INVESTIGACIONES, JSON.stringify(lista));
  } catch {
    /* almacenamiento no disponible: se mantiene solo en memoria del proceso */
  }
}

export function getInvestigaciones(): Promise<Investigacion[]> {
  return Promise.resolve(leerInvestigaciones());
}

export function crearInvestigacion(nombre: string, propietarioId: string): Promise<Investigacion> {
  const nueva: Investigacion = {
    id: `res-${Date.now()}`,
    nombre,
    propietarioId,
  };
  const lista = leerInvestigaciones();
  lista.push(nueva);
  escribirInvestigaciones(lista);
  return Promise.resolve(nueva);
}
