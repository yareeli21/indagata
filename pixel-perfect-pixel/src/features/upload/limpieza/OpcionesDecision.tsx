import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { etiquetaOpcion } from "./textos";

interface OpcionesDecisionProps {
  /** Nombre accesible del grupo (el título del hallazgo). */
  etiqueta: string;
  opciones: string[];
  sugerida: string | null;
  /** Opción vigente: la del investigador o, si no decidió, la sugerida. */
  valor: string | null;
  onElegir: (opcion: string) => void;
}

/** Botones de opción para una decisión; marca cuál es la sugerida por el sistema. */
export function OpcionesDecision({
  etiqueta,
  opciones,
  sugerida,
  valor,
  onElegir,
}: OpcionesDecisionProps) {
  return (
    <div role="radiogroup" aria-label={etiqueta} className="flex flex-wrap gap-2">
      {opciones.map((opcion) => {
        const activa = valor === opcion;
        return (
          <button
            key={opcion}
            type="button"
            role="radio"
            aria-checked={activa}
            onClick={() => onElegir(opcion)}
            className={cn(
              "inline-flex min-h-10 items-center gap-2 rounded-xl border px-3.5 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              activa
                ? "border-primary bg-primary text-primary-foreground shadow-card"
                : "border-border bg-card text-foreground hover:border-primary/40 hover:bg-primary-soft",
            )}
          >
            {activa && <Check className="size-4" aria-hidden />}
            {etiquetaOpcion(opcion)}
            {opcion === sugerida && (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[0.7rem] font-bold uppercase tracking-wide",
                  activa ? "bg-primary-foreground/20" : "bg-accent-soft text-accent-strong",
                )}
              >
                sugerida
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
