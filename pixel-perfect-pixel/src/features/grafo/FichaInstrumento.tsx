import { X } from "lucide-react";
import type { NodoGrafo, Recomendacion } from "@/api/grafo";

interface FichaInstrumentoProps {
  instrumento: NodoGrafo | Recomendacion;
  /** True si el instrumento está en el set activo de la investigación. */
  activo: boolean;
  /** Añade el instrumento al set activo (undefined si ya está activo). */
  onAgregar?: (() => void) | undefined;
  onCerrar: () => void;
}

function esRecomendacion(inst: NodoGrafo | Recomendacion): inst is Recomendacion {
  return "score" in inst;
}

/** Panel lateral con la ficha de un instrumento al hacer clic en su nodo. */
export function FichaInstrumento({
  instrumento,
  activo,
  onAgregar,
  onCerrar,
}: FichaInstrumentoProps) {
  const reco = esRecomendacion(instrumento) ? instrumento : null;

  return (
    <aside className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l border-border bg-card p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-display text-base font-semibold leading-tight text-foreground">
          {instrumento.titulo}
        </h2>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar ficha"
          className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <X className="size-4" />
        </button>
      </div>

      <dl className="space-y-3 text-sm">
        <div>
          <dt className="text-xs font-medium text-muted-foreground">Tipo</dt>
          <dd className="text-foreground">{instrumento.tipo}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-muted-foreground">Autor</dt>
          <dd className="text-foreground">
            {instrumento.autorNombre || "Sin autor"}
            {instrumento.esPropio && " (tú)"}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-muted-foreground">
            KPIs ({instrumento.kpis.length})
          </dt>
          <dd className="flex flex-wrap gap-1.5 pt-1">
            {instrumento.kpis.length === 0 && (
              <span className="text-xs text-muted-foreground">Sin KPIs asociados.</span>
            )}
            {instrumento.kpis.map((kpi) => (
              <span
                key={kpi}
                className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground"
              >
                {kpi}
              </span>
            ))}
          </dd>
        </div>

        {reco && (
          <div className="space-y-2 rounded-xl border border-dashed border-accent bg-accent-soft/40 p-3">
            <p className="text-xs font-semibold text-accent-foreground">{reco.razon}</p>
            <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
              <Metrica etiqueta="Score" valor={reco.score} />
              <Metrica etiqueta="Semántico" valor={reco.score_semantico} />
              <Metrica etiqueta="KPIs" valor={reco.score_kpi} />
            </div>
            {reco.kpis_compartidos.length > 0 && (
              <p className="text-[11px] text-muted-foreground">
                Comparten: {reco.kpis_compartidos.join(", ")}
              </p>
            )}
          </div>
        )}
      </dl>

      {onAgregar && !activo && (
        <button
          type="button"
          onClick={onAgregar}
          className="mt-auto rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
        >
          Agregar a mi investigación
        </button>
      )}
      {activo && (
        <p className="mt-auto rounded-xl bg-primary-soft px-4 py-2 text-center text-xs font-medium text-primary">
          Ya está en tu investigación
        </p>
      )}
    </aside>
  );
}

function Metrica({ etiqueta, valor }: { etiqueta: string; valor: number }) {
  return (
    <div className="rounded-lg bg-card px-1.5 py-1">
      <p className="font-display text-sm font-semibold text-foreground">{valor.toFixed(2)}</p>
      <p className="text-muted-foreground">{etiqueta}</p>
    </div>
  );
}
