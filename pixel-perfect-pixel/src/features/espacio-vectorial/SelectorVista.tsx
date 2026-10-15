import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface SelectorVistaProps {
  alineado: boolean;
  cargando: boolean;
  onCambiar: (alineado: boolean) => void;
}

const OPCIONES = [
  { valor: false, nombre: "Original", ayuda: "Proyección directa de los vectores" },
  { valor: true, nombre: "Alinear grupos", ayuda: "Quita la brecha entre KPIs e instrumentos" },
];

/** Interruptor entre la vista original y la alineada del mapa. */
export function SelectorVista({ alineado, cargando, onCambiar }: SelectorVistaProps) {
  return (
    <div
      role="group"
      aria-label="Vista del mapa"
      className="inline-flex items-center gap-1 rounded-2xl border border-border bg-card/95 p-1 shadow-lift backdrop-blur-sm"
    >
      {OPCIONES.map((o) => {
        const activo = o.valor === alineado;
        return (
          <button
            key={o.nombre}
            type="button"
            aria-pressed={activo}
            title={o.ayuda}
            disabled={cargando}
            onClick={() => !activo && onCambiar(o.valor)}
            className={cn(
              "flex min-h-10 items-center gap-2 rounded-xl px-3.5 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-wait",
              activo
                ? "bg-primary text-primary-foreground shadow-card"
                : "text-muted-foreground hover:bg-primary-soft hover:text-primary",
            )}
          >
            {cargando && !activo && <Loader2 className="size-4 animate-spin" aria-hidden />}
            {o.nombre}
          </button>
        );
      })}
    </div>
  );
}
