import type { TipoInstrumento } from "@/types";

const EXTENSIONES_TABLA = [".csv", ".xlsx", ".xls"];

/** ¿El archivo es una tabla? (las pruebas en tabla necesitan su clave de respuestas). */
export function esTabla(archivo: File | null): boolean {
  const nombre = archivo?.name.toLowerCase() ?? "";
  return EXTENSIONES_TABLA.some((ext) => nombre.endsWith(ext));
}

/** ¿Este paso exige la clave de respuestas? */
export function requiereClave(tipo: TipoInstrumento | null, archivo: File | null): boolean {
  return tipo === "Prueba estandarizada" && esTabla(archivo);
}
