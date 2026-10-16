import { Eye, EyeOff, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TipoPuntoEspacio } from "@/types";
import { SimboloTipo } from "./SimboloTipo";

interface ElementoLeyenda {
  tipo: TipoPuntoEspacio;
  nombre: string;
  descripcion: string;
  /** null = aún no se ha cargado (se carga al activarlo). */
  conteo: number | null;
  /** Insignia junto al nombre, p. ej. «provisionales». */
  insignia?: string | undefined;
  cargando?: boolean | undefined;
}

interface LeyendaInteractivaProps {
  elementos: ElementoLeyenda[];
  visibles: ReadonlySet<TipoPuntoEspacio>;
  onAlternar: (tipo: TipoPuntoEspacio) => void;
}

/** Leyenda que además muestra u oculta cada tipo de punto en el mapa. */
export function LeyendaInteractiva({ elementos, visibles, onAlternar }: LeyendaInteractivaProps) {
  return (
    <ul className="space-y-3">
      {elementos.map((e) => {
        const activo = visibles.has(e.tipo);
        return (
          <li key={e.tipo}>
            <button
              type="button"
              aria-pressed={activo}
              onClick={() => onAlternar(e.tipo)}
              className={cn(
                "group flex w-full items-center gap-4 rounded-2xl border p-4 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                activo
                  ? "border-border bg-card shadow-card hover:border-primary/30 hover:shadow-lift"
                  : "border-dashed border-border bg-transparent opacity-60 hover:opacity-90",
              )}
            >
              <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft">
                <SimboloTipo tipo={e.tipo} className="scale-150" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-display text-base font-bold text-foreground">
                      {e.nombre}
                    </span>
                    {e.insignia && (
                      <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[0.75rem] font-bold text-accent-strong">
                        {e.insignia}
                      </span>
                    )}
                  </span>
                  <span className="font-display text-xl font-bold tabular-nums text-foreground">
                    {e.cargando ? (
                      <Loader2 className="size-5 animate-spin text-primary" aria-label="Cargando" />
                    ) : (
                      (e.conteo ?? "—")
                    )}
                  </span>
                </span>
                <span className="block text-xs leading-snug text-muted-foreground">
                  {e.descripcion}
                </span>
              </span>
              {activo ? (
                <Eye className="size-5 shrink-0 text-primary" aria-hidden />
              ) : (
                <EyeOff className="size-5 shrink-0 text-muted-foreground" aria-hidden />
              )}
              <span className="sr-only">{activo ? "Ocultar" : "Mostrar"}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
