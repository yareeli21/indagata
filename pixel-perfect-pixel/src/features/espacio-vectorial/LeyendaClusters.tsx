import { cn } from "@/lib/utils";
import type { ClusterEspacio } from "@/types";
import { claseCluster } from "./dibujo";

interface LeyendaClustersProps {
  clusters: ClusterEspacio[];
  ocultos: ReadonlySet<number>;
  onAlternar: (id: number) => void;
}

/**
 * Grupos temáticos de KPIs (k-means sobre los vectores originales). Cada grupo
 * se nombra por su KPI más representativo y se puede mostrar u ocultar.
 */
export function LeyendaClusters({ clusters, ocultos, onAlternar }: LeyendaClustersProps) {
  return (
    <ul className="space-y-2">
      {clusters.map((c) => {
        const activo = !ocultos.has(c.id);
        return (
          <li key={c.id}>
            <button
              type="button"
              aria-pressed={activo}
              onClick={() => onAlternar(c.id)}
              title={c.representativos.join(" · ")}
              className={cn(
                "flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                activo ? "hover:bg-primary-soft" : "opacity-45 hover:opacity-80",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "mt-1 size-3.5 shrink-0 rounded-full ring-2 ring-card",
                  activo ? claseCluster(c.id) : "border-2 border-dashed border-muted-foreground",
                )}
              />
              <span className="min-w-0 flex-1">
                <span className="line-clamp-2 text-sm font-semibold leading-snug text-foreground">
                  {c.etiqueta}
                </span>
                {c.representativos.length > 1 && (
                  <span className="mt-0.5 line-clamp-1 block text-xs text-muted-foreground">
                    también {c.representativos.slice(1).join(" · ")}
                  </span>
                )}
              </span>
              <span className="shrink-0 text-xs font-bold tabular-nums text-muted-foreground">
                {c.tamano}
              </span>
              <span className="sr-only">{activo ? "Ocultar grupo" : "Mostrar grupo"}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
