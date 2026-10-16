import { cn } from "@/lib/utils";
import type { TipoPuntoEspacio } from "@/types";
import { claseCluster } from "./dibujo";

interface SimboloTipoProps {
  tipo: TipoPuntoEspacio;
  /** Para KPIs: grupo temático (define el color). Sin grupo se dibuja el contorno. */
  clusterId?: number | null | undefined;
  className?: string | undefined;
}

/** Misma forma y color que en el mapa: KPI = círculo (color de su grupo), instrumento = rombo, chunk = punto. */
export function SimboloTipo({ tipo, clusterId, className }: SimboloTipoProps) {
  return (
    <span aria-hidden className={cn("inline-flex size-4 items-center justify-center", className)}>
      {tipo === "kpi" &&
        (clusterId == null ? (
          <span className="size-3.5 rounded-full border-[3px] border-primary bg-card" />
        ) : (
          <span className={cn("size-3.5 rounded-full ring-2 ring-card", claseCluster(clusterId))} />
        ))}
      {tipo === "instrumento" && (
        <span className="size-3 rotate-45 rounded-[2px] bg-accent ring-2 ring-card" />
      )}
      {tipo === "chunk" && <span className="size-2 rounded-full bg-chart-4" />}
    </span>
  );
}
