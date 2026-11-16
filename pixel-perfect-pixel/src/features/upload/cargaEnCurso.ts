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

/** Por usuario (16 nov): la carga a medias de una cuenta no debe aparecerle a otra en el mismo navegador. */
const clave = (usuarioId: string) => `indagata.carga.enCurso.${usuarioId}`;

export function leerCargaEnCurso(usuarioId: string): CargaEnCurso | null {
  try {
    const crudo = window.localStorage.getItem(clave(usuarioId));
    if (!crudo) return null;
    const datos = JSON.parse(crudo) as Partial<CargaEnCurso>;
    return typeof datos.idCrudo === "number" && datos.tipo && datos.nombreArchivo
      ? (datos as CargaEnCurso)
      : null;
  } catch {
    return null;
  }
}

export function guardarCargaEnCurso(usuarioId: string, carga: CargaEnCurso): void {
  try {
    window.localStorage.setItem(clave(usuarioId), JSON.stringify(carga));
  } catch {
    // Sin almacenamiento: no se podrá retomar tras recargar, pero el flujo sigue.
  }
}

export function borrarCargaEnCurso(usuarioId: string): void {
  try {
    window.localStorage.removeItem(clave(usuarioId));
  } catch {
    // Sin almacenamiento disponible.
  }
}
