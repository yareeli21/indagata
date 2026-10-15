import { cn } from "@/lib/utils";
import type { TipoInstrumento } from "@/types";

const ESTILO: Record<TipoInstrumento, { caja: string; punto: string }> = {
  Encuesta: { caja: "bg-primary-soft text-primary", punto: "bg-primary" },
  Entrevista: { caja: "bg-secondary text-secondary-foreground", punto: "bg-chart-4" },
  "Prueba estandarizada": { caja: "bg-accent-soft text-accent-foreground", punto: "bg-accent" },
};

export function TipoBadge({ tipo }: { tipo: TipoInstrumento }) {
  const estilo = ESTILO[tipo];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold",
        estilo.caja,
      )}
    >
      <span aria-hidden className={cn("size-2 rounded-full", estilo.punto)} />
      {tipo}
    </span>
  );
}
