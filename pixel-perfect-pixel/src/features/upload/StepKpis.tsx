import { Check, ChevronDown, ListChecks, SearchX, Sparkles, X } from "lucide-react";
import { EstadoVacio } from "@/components/shared/EstadoVacio";
import { ProcesandoIA } from "@/components/shared/ProcesandoIA";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { KpiPropuesto } from "@/types";

export type DecisionKpi = "aceptado" | "rechazado";

interface StepKpisProps {
  sugeridos: KpiPropuesto[] | null;
  decisiones: Record<string, DecisionKpi>;
  onDecidir: (id: string, d: DecisionKpi) => void;
  /** Justificaciones editadas por el investigador (por kpi_ref). */
  justificaciones: Record<string, string>;
  onJustificar: (id: string, texto: string) => void;
}

const pct = (x: number) => `${Math.round(x * 100)} %`;

function TarjetaKpi({
  kpi,
  decision,
  justificacion,
  onDecidir,
  onJustificar,
}: {
  kpi: KpiPropuesto;
  decision: DecisionKpi | undefined;
  justificacion: string;
  onDecidir: (d: DecisionKpi) => void;
  onJustificar: (texto: string) => void;
}) {
  const editada = justificacion.trim() !== kpi.justificacion.trim();
  const idTexto = `just-${kpi.kpi_ref}`;
  return (
    <article
      className={cn(
        "space-y-4 rounded-2xl border border-border bg-card p-4 shadow-card transition-opacity sm:p-5",
        decision === "aceptado" && "border-primary ring-1 ring-primary/30",
        decision === "rechazado" && "opacity-60",
      )}
      aria-label={kpi.nombre}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h4 className="font-display text-base font-bold text-foreground">{kpi.nombre}</h4>
          {kpi.dimension && <p className="text-xs text-muted-foreground">{kpi.dimension}</p>}
        </div>
        <span
          className="shrink-0 rounded-full bg-accent-soft px-2.5 py-0.5 text-sm font-semibold text-accent-strong tabular-nums"
          title={`Perfil general ${pct(kpi.componentes.g)} · preguntas ${pct(kpi.componentes.p)} · cobertura ${pct(kpi.componentes.c)}`}
        >
          {pct(kpi.score)}
        </span>
      </div>

      <div className="space-y-1.5">
        <p className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
          <ListChecks className="size-3.5" aria-hidden /> Preguntas que lo sustentan
        </p>
        {kpi.evidencia.length > 0 ? (
          <ul className="space-y-1">
            {kpi.evidencia.map((e) => (
              <li key={e.pregunta_id} className="flex items-start justify-between gap-3 text-sm">
                <span className="min-w-0 text-foreground">{e.texto}</span>
                <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                  {pct(e.similitud)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Se sugiere por la descripción general del instrumento.
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <label
          htmlFor={idTexto}
          className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground"
        >
          <Sparkles className="size-3.5" aria-hidden /> Por qué se relaciona
          <span className="font-normal">
            ·{" "}
            {editada
              ? "editada por ti"
              : kpi.justificacion_origen === "llm"
                ? "sugerida por IA, revísala"
                : "generada automáticamente"}
          </span>
        </label>
        <Textarea
          id={idTexto}
          value={justificacion}
          onChange={(e) => onJustificar(e.target.value)}
          rows={3}
          maxLength={2000}
          className="text-sm"
        />
      </div>

      <Collapsible>
        <CollapsibleTrigger className="group flex items-center gap-1 text-xs font-semibold text-primary">
          Qué mide este KPI
          <ChevronDown
            className="size-3.5 transition-transform group-data-[state=open]:rotate-180"
            aria-hidden
          />
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-2 text-sm text-muted-foreground">
          {kpi.que_mide || kpi.definicion}
        </CollapsibleContent>
      </Collapsible>

      <div className="flex gap-2">
        <Button
          size="sm"
          variant={decision === "aceptado" ? "default" : "outline"}
          onClick={() => onDecidir("aceptado")}
        >
          <Check /> Aceptar
        </Button>
        <Button
          size="sm"
          variant={decision === "rechazado" ? "secondary" : "ghost"}
          onClick={() => onDecidir("rechazado")}
        >
          <X /> Rechazar
        </Button>
      </div>
    </article>
  );
}

export function StepKpis({
  sugeridos,
  decisiones,
  onDecidir,
  justificaciones,
  onJustificar,
}: StepKpisProps) {
  if (!sugeridos) {
    return (
      <ProcesandoIA
        mensaje="Buscando KPIs relacionados…"
        detalle="Comparamos el perfil del instrumento y cada una de sus preguntas con el catálogo de indicadores."
      />
    );
  }
  if (sugeridos.length === 0) {
    return (
      <EstadoVacio
        icono={SearchX}
        titulo="No encontramos KPIs relacionados"
        descripcion="Ningún indicador del catálogo se parece lo suficiente al perfil del instrumento. Puedes continuar sin KPIs."
      />
    );
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Acepta los KPIs que mide tu instrumento. Puedes editar la justificación antes de aceptar;
        los que no aceptes quedan registrados como rechazados.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        {sugeridos.map((k) => (
          <TarjetaKpi
            key={k.kpi_ref}
            kpi={k}
            decision={decisiones[k.kpi_ref]}
            justificacion={justificaciones[k.kpi_ref] ?? k.justificacion}
            onDecidir={(d) => onDecidir(k.kpi_ref, d)}
            onJustificar={(t) => onJustificar(k.kpi_ref, t)}
          />
        ))}
      </div>
    </div>
  );
}
