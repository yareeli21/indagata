import { cn } from "@/lib/utils";
import type { TipoPuntoEspacio } from "@/types";

/** Misma forma y color que en el mapa: KPI = círculo, instrumento = rombo, chunk = punto. */
export function SimboloTipo({ tipo, className }: { tipo: TipoPuntoEspacio; className?: string }) {
  return (
    <span aria-hidden className={cn("inline-flex size-4 items-center justify-center", className)}>
      {tipo === "kpi" && <span className="size-3.5 rounded-full bg-primary ring-2 ring-card" />}
      {tipo === "instrumento" && (
        <span className="size-3 rotate-45 rounded-[2px] bg-accent ring-2 ring-card" />
      )}
      {tipo === "chunk" && <span className="size-2 rounded-full bg-chart-4" />}
    </span>
  );
}
