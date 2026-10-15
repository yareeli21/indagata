import { Sparkles, X } from "lucide-react";
import type { BusquedaEspacio } from "@/types";
import { ListaVecinos } from "./ListaVecinos";

interface PanelBusquedaProps {
  busqueda: BusquedaEspacio;
  enMapa: (id: string) => boolean;
  onSeleccionar: (id: string) => void;
  onCerrar: () => void;
}

/** Resultados de la búsqueda semántica: lo mismo que el chat usaría como fuentes. */
export function PanelBusqueda({ busqueda, enMapa, onSeleccionar, onCerrar }: PanelBusquedaProps) {
  return (
    <article className="space-y-6" aria-label={`Búsqueda: ${busqueda.texto}`}>
      <header className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <p className="flex items-center gap-2 pt-1 text-xs font-bold uppercase tracking-wide text-muted-foreground">
            <Sparkles className="size-4 text-primary-glow" aria-hidden />
            Búsqueda semántica
          </p>
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Quitar la búsqueda"
            title="Quitar (Esc)"
            className="-mr-2 -mt-1 flex size-10 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-primary-soft hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="size-5" />
          </button>
        </div>
        <h2 className="font-display text-xl font-bold leading-snug text-foreground">
          «{busqueda.texto}»
        </h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Tu frase se convirtió en un vector con el mismo modelo y se proyectó con la misma
          transformación que el resto del mapa: es la estrella. Así encuentra el chat sus fuentes.
        </p>
      </header>

      <div className="space-y-6 border-t border-border/70 pt-6">
        <ListaVecinos
          titulo="Fragmentos que el chat recuperaría"
          vecinos={busqueda.chunks}
          enMapa={enMapa}
          onSeleccionar={onSeleccionar}
          insignia={
            busqueda.fuenteChunks.provisional ? (
              <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[0.75rem] font-bold normal-case tracking-normal text-accent-strong">
                provisionales
              </span>
            ) : undefined
          }
          vacio="Aún no hay chunks del RAG para comparar."
        />
        <ListaVecinos
          titulo="Instrumentos más cercanos"
          vecinos={busqueda.instrumentos}
          enMapa={enMapa}
          onSeleccionar={onSeleccionar}
        />
        <ListaVecinos
          titulo="KPIs más cercanos"
          vecinos={busqueda.kpis}
          enMapa={enMapa}
          onSeleccionar={onSeleccionar}
        />
        <p className="text-xs leading-relaxed text-muted-foreground">
          Similitud coseno entre los vectores completos (768 dimensiones). La posición de la
          estrella es una aproximación en 2D.
        </p>
      </div>
    </article>
  );
}
