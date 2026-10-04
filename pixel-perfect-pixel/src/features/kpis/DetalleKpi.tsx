import {
  Award,
  BarChart2,
  BookOpen,
  Briefcase,
  Calculator,
  ClipboardCheck,
  Heart,
  Home,
  Laptop,
  MessageCircle,
  Monitor,
  Shield,
  Smile,
  Users,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import type { KpiCatalogo } from "@/types";

const ICONOS: Record<string, LucideIcon> = {
  Award,
  BarChart2,
  BookOpen,
  Briefcase,
  Calculator,
  ClipboardCheck,
  Heart,
  Home,
  Laptop,
  MessageCircle,
  Monitor,
  Shield,
  Smile,
  Users,
  Zap,
};

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
