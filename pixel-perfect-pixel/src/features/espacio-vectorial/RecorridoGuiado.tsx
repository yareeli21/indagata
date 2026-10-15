import { ArrowLeft, ArrowRight, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PASOS_RECORRIDO } from "./recorrido";
import { SimboloTipo } from "./SimboloTipo";

interface RecorridoGuiadoProps {
  paso: number;
  onCambiar: (paso: number) => void;
  onCerrar: () => void;
  /** Último paso: lanza una búsqueda de ejemplo. */
  onProbar: () => void;
  className?: string | undefined;
}

/** Recorrido de tres pasos sobre el mapa (se puede saltar en cualquier momento). */
export function RecorridoGuiado({
  paso,
  onCambiar,
  onCerrar,
  onProbar,
  className,
}: RecorridoGuiadoProps) {
  const actual = PASOS_RECORRIDO[paso];
  if (!actual) return null;
  const ultimo = paso === PASOS_RECORRIDO.length - 1;
  return (
    <section
      role="dialog"
      aria-modal="false"
      aria-labelledby="recorrido-titulo"
      className={cn(
        "w-[min(24rem,calc(100%-2rem))] rounded-3xl border border-border bg-card/97 p-4 shadow-elevated backdrop-blur-sm sm:p-5",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
          {actual.resaltar ? (
            <SimboloTipo tipo={actual.resaltar} clusterId={actual.resaltar === "kpi" ? 0 : null} />
          ) : (
            <Sparkles className="size-4 text-primary-glow" aria-hidden />
          )}
          Recorrido · {paso + 1} de {PASOS_RECORRIDO.length}
        </p>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Saltar el recorrido"
          className="-mr-2 -mt-2 flex size-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-primary-soft hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X className="size-4" />
        </button>
      </div>
      <h2 id="recorrido-titulo" className="mt-2 font-display text-lg font-bold text-foreground">
        {actual.titulo}
      </h2>
      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{actual.texto}</p>
      <div className="mt-4 flex items-center justify-between gap-2">
        <div className="flex gap-1.5" aria-hidden>
          {PASOS_RECORRIDO.map((p, i) => (
            <span
              key={p.titulo}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i === paso ? "w-6 bg-primary" : "w-1.5 bg-border",
              )}
            />
          ))}
        </div>
        <div className="flex gap-2">
          {paso > 0 && (
            <Button variant="ghost" size="sm" onClick={() => onCambiar(paso - 1)}>
              <ArrowLeft /> Anterior
            </Button>
          )}
          {ultimo ? (
            <Button variant="accent" size="sm" onClick={onProbar}>
              <Sparkles /> Probar un ejemplo
            </Button>
          ) : (
            <Button size="sm" onClick={() => onCambiar(paso + 1)}>
              Siguiente <ArrowRight />
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
