import type { TipoInstrumento } from "@/types";

/**
 * Carga en curso guardada en el navegador, para retomar la limpieza si el
 * investigador cierra o recarga la página. Las decisiones viven en el servidor
 * (cleaning-service); aquí solo se recuerda qué instrumento se estaba limpiando.
 */
export interface CargaEnCurso {
  idCrudo: number;
  tipo: TipoInstrumento;
  nombreArchivo: string;
}

const CLAVE = "indagata.carga.enCurso";

export function leerCargaEnCurso(): CargaEnCurso | null {
  try {
    const crudo = window.localStorage.getItem(CLAVE);
    if (!crudo) return null;
    const datos = JSON.parse(crudo) as Partial<CargaEnCurso>;
    return typeof datos.idCrudo === "number" && datos.tipo && datos.nombreArchivo
      ? (datos as CargaEnCurso)
      : null;
  } catch {
    return null;
  }
}

export function guardarCargaEnCurso(carga: CargaEnCurso): void {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(carga));
  } catch {
    // Sin almacenamiento: no se podrá retomar tras recargar, pero el flujo sigue.
  }
}

export function borrarCargaEnCurso(): void {
  try {
    window.localStorage.removeItem(CLAVE);
  } catch {
    // Sin almacenamiento disponible.
  }
}
