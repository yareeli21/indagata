import { BarChart2, ExternalLink } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { ICONOS } from "@/features/kpis/iconos";
import type { KpiCatalogo } from "@/types";

interface DetalleKpiProps {
  kpi: KpiCatalogo | null;
  onCerrar: () => void;
}

export function DetalleKpi({ kpi, onCerrar }: DetalleKpiProps) {
  return (
    <Sheet open={!!kpi} onOpenChange={(o) => !o && onCerrar()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        {kpi && <ContenidoDetalle kpi={kpi} />}
      </SheetContent>
    </Sheet>
  );
}

function ContenidoDetalle({ kpi }: { kpi: KpiCatalogo }) {
  const Icono = ICONOS[kpi.icono] ?? BarChart2;

  return (
    <div className="space-y-6">
      <SheetHeader className="space-y-3 text-left">
        <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icono className="size-6" />
        </div>
        <SheetTitle className="text-xl">{kpi.nombre}</SheetTitle>
        <SheetDescription className="text-base text-foreground/80">
          {kpi.descripcionCorta}
        </SheetDescription>
      </SheetHeader>

      <Separator />

      <SeccionDetalle titulo="¿Qué es?" contenido={kpi.queEs} />
      <SeccionDetalle titulo="¿Qué mide?" contenido={kpi.queMide} />
      <SeccionDetalle titulo="¿Cómo se mide?" contenido={kpi.comoSeMide} />

      {/* Fórmula */}
      <div className="space-y-1.5">
        <h3 className="text-sm font-semibold text-foreground">Fórmula</h3>
        <div className="rounded-lg border bg-muted/50 px-4 py-3">
          <code className="text-sm font-mono text-foreground/90 whitespace-pre-wrap">
            {kpi.formula}
          </code>
        </div>
      </div>

      <Separator />

      <SeccionDetalle titulo="Información general" contenido={kpi.infoGeneral} />

      {/* Fuentes de referencia verificadas */}
      <div className="space-y-1.5">
        <h3 className="text-sm font-semibold text-foreground">Fuentes de referencia</h3>
        {kpi.fuentes && kpi.fuentes.length > 0 ? (
          <ul className="space-y-2">
            {kpi.fuentes.map((f) => (
              <li key={f.url} className="text-sm">
                <a
                  href={f.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-medium text-primary underline-offset-2 hover:underline"
                >
                  {f.organismo}: {f.titulo}
                  {f.anio ? ` (${f.anio})` : ""}
                  <ExternalLink className="size-3.5 shrink-0" aria-hidden />
                </a>
                {f.nota && <p className="text-xs text-muted-foreground">{f.nota}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Este KPI aún no tiene una fuente de referencia verificada. Se agregan en
            infrastructure/postgres/seed/KPI_Fuentes.csv.
          </p>
        )}
      </div>

      {/* Etiquetas */}
      <div className="flex flex-wrap gap-1.5 pb-4">
        {kpi.etiquetas.map((e) => (
          <span
            key={e}
            className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground"
          >
            {e}
          </span>
        ))}
      </div>
    </div>
  );
}

function SeccionDetalle({ titulo, contenido }: { titulo: string; contenido: string }) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-sm font-semibold text-foreground">{titulo}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{contenido}</p>
    </div>
  );
}
