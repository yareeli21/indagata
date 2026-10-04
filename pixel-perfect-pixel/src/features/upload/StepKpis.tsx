import { Check, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { KpiSugerido } from "@/types";

export type DecisionKpi = "aceptado" | "rechazado";

interface StepKpisProps {
  sugeridos: KpiSugerido[] | null;
  decisiones: Record<string, DecisionKpi>;
  onDecidir: (id: string, d: DecisionKpi) => void;
}

export function StepKpis({ sugeridos, decisiones, onDecidir }: StepKpisProps) {
  if (!sugeridos) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" /> Buscando KPIs por similitud semántica…
      </div>
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {sugeridos.map((k) => {
        const d = decisiones[k.id];
        return (
          <div
            key={k.id}
            className={cn(
              "space-y-4 rounded-2xl border border-border bg-card p-5 shadow-card transition-opacity",
              d === "aceptado" && "border-primary ring-1 ring-primary/30",
              d === "rechazado" && "opacity-50",
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <p className="font-medium">{k.nombre}</p>
              <span className="shrink-0 rounded-full bg-accent-soft px-2.5 py-0.5 text-sm font-semibold text-accent-foreground">
                {k.coincidencia}%
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-accent" style={{ width: `${k.coincidencia}%` }} />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant={d === "aceptado" ? "default" : "outline"}
                onClick={() => onDecidir(k.id, "aceptado")}
              >
                <Check /> Aceptar
              </Button>
              <Button
                size="sm"
                variant={d === "rechazado" ? "secondary" : "ghost"}
                onClick={() => onDecidir(k.id, "rechazado")}
              >
                <X /> Rechazar
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
