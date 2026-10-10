import { getInstrumentosDeInvestigacion } from "@/api/chat";
import type { Instrumento } from "@/types";

/**
 * Instrumentos que son fuente de una investigación: los elegidos al armarla.
 * Las investigaciones creadas antes de guardar la selección usan, como antes,
 * los propios más algunos de otros autores.
 */
export function fuentesDeInvestigacion(
  todos: Instrumento[],
  investigacionId: string,
  miId: string,
): Instrumento[] {
  const elegidos = getInstrumentosDeInvestigacion(investigacionId);
  if (elegidos.length > 0) return todos.filter((i) => elegidos.includes(i.id));
  const propios = todos.filter((i) => i.autorId === miId).slice(0, 3);
  const ajenos = todos.filter((i) => i.autorId !== miId).slice(0, 2);
  return [...propios, ...ajenos];
}
