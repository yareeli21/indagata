import { cn } from "@/lib/utils";
import type { EstadoInstrumento } from "@/types";

/**
 * Color semántico por estado del instrumento, siempre vía tokens de diseño:
 * - Estandarizado: verde azulado (éxito), es el estado "aprobado".
 * - En revisión: ámbar/crema de acento.
 * - Borrador: neutro.
 */
const ESTILO: Record<EstadoInstrumento, { caja: string; punto: string }> = {
  Estandarizado: { caja: "bg-success-soft text-success", punto: "bg-success" },
  "En revisión": { caja: "bg-accent-soft text-accent-foreground", punto: "bg-accent" },
  Borrador: { caja: "bg-muted text-muted-foreground", punto: "bg-muted-foreground/60" },
};

export function EstadoBadge({ estado }: { estado: EstadoInstrumento }) {
  const estilo = ESTILO[estado];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold",
        estilo.caja,
      )}
    >
      <span aria-hidden className={cn("size-2 rounded-full", estilo.punto)} />
      {estado}
    </span>
  );
}
