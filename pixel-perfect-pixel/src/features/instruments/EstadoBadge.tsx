import { cn } from "@/lib/utils";
import type { EstadoInstrumento } from "@/types";

/**
 * Color semántico por estado del instrumento, siempre vía tokens de diseño:
 * - Estandarizado: primario (navy), es el estado "aprobado".
 * - En revisión: ámbar/crema de acento.
 * - Borrador: neutro.
 */
const ESTILO: Record<EstadoInstrumento, string> = {
  Estandarizado: "bg-primary/10 text-primary",
  "En revisión": "bg-accent-soft text-accent-foreground",
  Borrador: "bg-muted text-muted-foreground",
};

export function EstadoBadge({ estado }: { estado: EstadoInstrumento }) {
  return (
    <span
      className={cn(
        "inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium",
        ESTILO[estado],
      )}
    >
      {estado}
    </span>
  );
}
