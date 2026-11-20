import { useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  ListChecks,
  Plus,
  Search,
  SearchX,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { EstadoVacio } from "@/components/shared/EstadoVacio";
import { ProcesandoIA } from "@/components/shared/ProcesandoIA";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { KpiCatalogo, KpiPropuesto } from "@/types";

export type DecisionKpi = "aceptado" | "rechazado";

/** KPI que el investigador agrega del catálogo porque el sistema no lo sugirió. */
export interface KpiManual {
  kpi: KpiCatalogo;
  motivo: string;
}

interface StepKpisProps {
  sugeridos: KpiPropuesto[] | null;
  decisiones: Record<string, DecisionKpi>;
  onDecidir: (id: string, d: DecisionKpi) => void;
  /** Justificaciones editadas por el investigador (por kpi_ref). */
  justificaciones: Record<string, string>;
  onJustificar: (id: string, texto: string) => void;
  /** Catálogo completo de KPIs (para agregar uno a mano). */
  catalogo: KpiCatalogo[];
  manuales: KpiManual[];
  onAgregarManual: (kpi: KpiCatalogo) => void;
  onQuitarManual: (id: string) => void;
  onMotivoManual: (id: string, motivo: string) => void;
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
  catalogo,
  manuales,
  onAgregarManual,
  onQuitarManual,
  onMotivoManual,
}: StepKpisProps) {
  if (!sugeridos) {
    return (
      <ProcesandoIA
        mensaje="Buscando KPIs relacionados…"
        detalle="Comparamos el perfil del instrumento y cada una de sus preguntas con el catálogo de indicadores."
      />
    );
  }
  const manual = (
    <SeccionManual
      catalogo={catalogo}
      sugeridos={sugeridos}
      manuales={manuales}
      onAgregar={onAgregarManual}
      onQuitar={onQuitarManual}
      onMotivo={onMotivoManual}
    />
  );
  if (sugeridos.length === 0) {
    return (
      <div className="space-y-6">
        <EstadoVacio
          icono={SearchX}
          titulo="No encontramos KPIs relacionados"
          descripcion="Ningún indicador del catálogo se parece lo suficiente al perfil del instrumento. Puedes continuar sin KPIs o agregar uno manualmente."
        />
        {manual}
      </div>
    );
  }
  return (
    <div className="space-y-6">
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
      {manual}
    </div>
  );
}

/** Máximo de resultados de la búsqueda en el catálogo. */
const MAX_RESULTADOS = 8;

/**
 * Agregar KPIs a mano: por si el sistema no infirió uno que el instrumento sí mide. Se buscan en el catálogo
 * (sin los ya sugeridos, que se aceptan arriba) y quedan aceptados con el motivo que escriba el investigador.
 */
function SeccionManual({
  catalogo,
  sugeridos,
  manuales,
  onAgregar,
  onQuitar,
  onMotivo,
}: {
  catalogo: KpiCatalogo[];
  sugeridos: KpiPropuesto[];
  manuales: KpiManual[];
  onAgregar: (kpi: KpiCatalogo) => void;
  onQuitar: (id: string) => void;
  onMotivo: (id: string, motivo: string) => void;
}) {
  const [busqueda, setBusqueda] = useState("");
  const disponibles = useMemo(() => {
    const ocupados = new Set([
      ...sugeridos.map((k) => String(k.kpi_id)),
      ...manuales.map((m) => m.kpi.id),
    ]);
    const q = busqueda.trim().toLowerCase();
    return catalogo
      .filter((k) => !ocupados.has(k.id))
      .filter(
        (k) =>
          !q ||
          k.nombre.toLowerCase().includes(q) ||
          k.descripcionCorta.toLowerCase().includes(q) ||
          k.etiquetas.some((e) => e.toLowerCase().includes(q)),
      );
  }, [catalogo, sugeridos, manuales, busqueda]);

  return (
    <section
      aria-labelledby="titulo-kpi-manual"
      className="space-y-4 rounded-2xl border border-dashed border-border p-4 sm:p-5"
    >
      <div className="space-y-1">
        <h3 id="titulo-kpi-manual" className="font-display text-base font-bold text-foreground">
          ¿Falta algún KPI? Agrégalo manualmente
        </h3>
        <p className="text-sm text-muted-foreground">
          Si consideras que tu instrumento mide un indicador que el sistema no sugirió, búscalo en
          el catálogo y agrégalo. Quedará aceptado y registrado como agregado por ti.
        </p>
      </div>

      {manuales.length > 0 && (
        <ul className="space-y-3">
          {manuales.map((m) => (
            <li
              key={m.kpi.id}
              className="space-y-2 rounded-xl border border-primary bg-card p-3 ring-1 ring-primary/30"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-foreground">{m.kpi.nombre}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {m.kpi.descripcionCorta}
                  </p>
                </div>
                <Button size="sm" variant="ghost" onClick={() => onQuitar(m.kpi.id)}>
                  <Trash2 /> Quitar
                </Button>
              </div>
              <Textarea
                value={m.motivo}
                onChange={(e) => onMotivo(m.kpi.id, e.target.value)}
                maxLength={1500}
                rows={2}
                placeholder="¿Por qué lo mide tu instrumento? (opcional; p. ej. qué preguntas lo cubren)"
                aria-label={`Motivo para agregar ${m.kpi.nombre}`}
              />
            </li>
          ))}
        </ul>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Buscar en el catálogo de KPIs…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          maxLength={80}
          aria-label="Buscar KPI en el catálogo"
        />
      </div>
      {catalogo.length === 0 ? (
        <p className="text-sm text-muted-foreground">No se pudo cargar el catálogo de KPIs.</p>
      ) : disponibles.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {busqueda.trim()
            ? `No hay KPIs que coincidan con "${busqueda}".`
            : "Ya no quedan KPIs por agregar."}
        </p>
      ) : (
        <ul className="divide-y divide-border rounded-xl border border-border">
          {disponibles.slice(0, MAX_RESULTADOS).map((k) => (
            <li key={k.id} className="flex items-center justify-between gap-3 px-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground">{k.nombre}</p>
                <p className="text-xs text-muted-foreground line-clamp-1">{k.descripcionCorta}</p>
              </div>
              <Button size="sm" variant="outline" onClick={() => onAgregar(k)}>
                <Plus /> Agregar
              </Button>
            </li>
          ))}
        </ul>
      )}
      {disponibles.length > MAX_RESULTADOS && (
        <p className="text-xs text-muted-foreground">
          Mostrando {MAX_RESULTADOS} de {disponibles.length}; escribe para filtrar.
        </p>
      )}
    </section>
  );
}
