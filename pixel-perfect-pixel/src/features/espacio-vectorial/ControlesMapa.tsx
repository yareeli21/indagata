import { Maximize2, Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface ControlesMapaProps {
  zoom: number;
  onAcercar: () => void;
  onAlejar: () => void;
  onRestablecer: () => void;
  className?: string | undefined;
}

const boton =
  "flex size-11 items-center justify-center text-foreground transition-colors hover:bg-primary-soft hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring";

/** Botones de zoom del mapa (también con teclado: +, − y 0 sobre el mapa). */
export function ControlesMapa({
  zoom,
  onAcercar,
  onAlejar,
  onRestablecer,
  className,
}: ControlesMapaProps) {
  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-2xl border border-border bg-card/95 shadow-lift backdrop-blur-sm",
        className,
      )}
    >
      <button
        type="button"
        onClick={onAcercar}
        className={boton}
        aria-label="Acercar"
        title="Acercar (+)"
      >
        <Plus className="size-5" />
      </button>
      <span className="border-y border-border py-1 text-center text-xs font-bold tabular-nums text-muted-foreground">
        {Math.round(zoom * 100)}%
      </span>
      <button
        type="button"
        onClick={onAlejar}
        className={boton}
        aria-label="Alejar"
        title="Alejar (−)"
      >
        <Minus className="size-5" />
      </button>
      <button
        type="button"
        onClick={onRestablecer}
        className={cn(boton, "border-t border-border")}
        aria-label="Restablecer la vista"
        title="Restablecer la vista (0)"
      >
        <Maximize2 className="size-5" />
      </button>
    </div>
  );
}
