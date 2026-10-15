import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { VecinoEspacio } from "@/types";
import { SimboloTipo } from "./SimboloTipo";

interface ListaVecinosProps {
  titulo: string;
  vecinos: VecinoEspacio[];
  /** Ids presentes en el mapa: solo esos se pueden seleccionar. */
  enMapa: (id: string) => boolean;
  onSeleccionar: (id: string) => void;
  insignia?: ReactNode | undefined;
  vacio?: string | undefined;
}

function porcentaje(v: number) {
  return `${Math.round(v * 100)} %`;
}

/** Lista de vecinos con su similitud coseno; un clic los selecciona en el mapa. */
export function ListaVecinos({
  titulo,
  vecinos,
  enMapa,
  onSeleccionar,
  insignia,
  vacio,
}: ListaVecinosProps) {
  return (
    <section className="space-y-3">
      <h3 className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
        {titulo}
        {insignia}
      </h3>
      {vecinos.length === 0 ? (
        <p className="text-sm text-muted-foreground">{vacio ?? "Sin resultados."}</p>
      ) : (
        <ol className="space-y-1.5">
          {vecinos.map((v) => {
            const seleccionable = enMapa(v.id);
            const contenido = (
              <>
                <SimboloTipo tipo={v.tipo} clusterId={v.clusterId} className="mt-0.5 shrink-0" />
                <span className="min-w-0 flex-1 space-y-1.5">
                  <span
                    className={cn(
                      "block text-sm font-semibold leading-snug text-foreground",
                      v.tipo === "chunk" ? "line-clamp-3 font-normal" : "line-clamp-2",
                    )}
                  >
                    {v.tipo === "chunk" ? v.texto || v.etiqueta : v.etiqueta}
                  </span>
                  {v.tipo === "chunk" && (
                    <span className="line-clamp-1 block text-xs text-muted-foreground">
                      {v.etiqueta}
                    </span>
                  )}
                  <span className="flex items-center gap-2">
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                      <span
                        className="block h-full rounded-full bg-primary"
                        style={{ width: `${Math.max(4, Math.min(100, v.similitud * 100))}%` }}
                      />
                    </span>
                    <span className="w-11 text-right text-xs font-bold tabular-nums text-foreground">
                      {porcentaje(v.similitud)}
                    </span>
                  </span>
                </span>
                {seleccionable && (
                  <ChevronRight
                    className="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
                    aria-hidden
                  />
                )}
              </>
            );
            return (
              <li key={v.id}>
                {seleccionable ? (
                  <button
                    type="button"
                    onClick={() => onSeleccionar(v.id)}
                    className="group flex w-full items-start gap-3 rounded-xl px-2.5 py-2 text-left transition-colors hover:bg-primary-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {contenido}
                  </button>
                ) : (
                  <div className="flex items-start gap-3 px-2.5 py-2">{contenido}</div>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
