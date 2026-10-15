import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProcesandoIAProps {
  /** Qué se está haciendo (p. ej. "Buscando KPIs por similitud semántica…"). */
  mensaje: ReactNode;
  /** Detalle opcional bajo el mensaje. */
  detalle?: ReactNode;
  className?: string | undefined;
}

/**
 * Estado de procesamiento (LLM, embeddings, limpieza): tarjeta con ícono
 * pulsante y barra de progreso indeterminada.
 */
export function ProcesandoIA({ mensaje, detalle, className }: ProcesandoIAProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "relative flex flex-col items-center gap-5 overflow-hidden rounded-3xl border border-primary/15 bg-primary-soft/40 px-6 py-12 text-center",
        className,
      )}
    >
      <div aria-hidden className="relative flex size-20 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-primary/15 [animation-duration:2s]" />
        <span className="relative flex size-16 items-center justify-center rounded-2xl bg-hero text-accent shadow-lift">
          <Sparkles className="size-8" />
        </span>
      </div>
      <div className="space-y-1.5">
        <p className="font-display text-xl font-bold text-foreground">{mensaje}</p>
        {detalle && <p className="text-sm text-muted-foreground">{detalle}</p>}
      </div>
      <div aria-hidden className="h-2 w-full max-w-md overflow-hidden rounded-full bg-primary/10">
        <div className="h-full w-2/5 animate-indeterminado rounded-full bg-gradient-to-r from-primary via-primary-glow to-accent" />
      </div>
    </div>
  );
}
