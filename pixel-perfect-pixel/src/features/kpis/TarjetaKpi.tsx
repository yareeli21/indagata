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
import { cn } from "@/lib/utils";
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

interface TarjetaKpiProps {
  kpi: KpiCatalogo;
  activo?: boolean;
  onClick: () => void;
}

export function TarjetaKpi({ kpi, activo = false, onClick }: TarjetaKpiProps) {
  const Icono = ICONOS[kpi.icono] ?? BarChart2;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex w-full flex-col gap-3 rounded-2xl border border-border bg-card p-4 text-left shadow-card transition-all",
        "hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        activo && "border-primary/60 bg-primary-soft ring-1 ring-primary/30",
      )}
      aria-pressed={activo}
    >
      <span
        className={cn(
          "flex size-10 items-center justify-center rounded-xl transition-colors",
          activo
            ? "bg-primary text-primary-foreground"
            : "bg-primary/10 text-primary group-hover:bg-primary/20",
        )}
      >
        <Icono className="size-5" />
      </span>

      <div className="space-y-0.5">
        <p
          className={cn(
            "font-display text-sm font-semibold leading-snug",
            activo && "text-primary",
          )}
        >
          {kpi.nombre}
        </p>
        <p className="text-xs text-muted-foreground line-clamp-2">{kpi.descripcionCorta}</p>
      </div>
    </button>
  );
}
