import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EstadoVacioProps {
  icono: LucideIcon;
  titulo: string;
  descripcion: string;
  accion?: ReactNode;
  /** `compacto`: menos alto, para dentro de paneles. */
  compacto?: boolean;
  className?: string | undefined;
}

/** Estado vacío ilustrado: ícono en anillos concéntricos, título y acción. */
export function EstadoVacio({
  icono: Icono,
  titulo,
  descripcion,
  accion,
  compacto = false,
  className,
}: EstadoVacioProps) {
  return (
    <div
      className={cn(
        "relative flex flex-col items-center gap-4 overflow-hidden rounded-3xl border-2 border-dashed border-primary/15 bg-card/70 px-6 text-center",
        compacto ? "py-12" : "py-16 lg:py-20",
        className,
      )}
    >
      {/* Ilustración: anillos concéntricos + ícono en degradado */}
      <div aria-hidden className="relative mb-2 flex size-36 items-center justify-center">
        <span className="absolute inset-0 rounded-full bg-primary-soft/50" />
        <span className="absolute inset-4 rounded-full bg-primary-soft" />
        <span className="absolute -right-1 top-5 size-3 rounded-full bg-accent" />
        <span className="absolute bottom-6 left-1 size-2 rounded-full bg-primary/40" />
        <span className="relative flex size-20 animate-flotar items-center justify-center rounded-3xl bg-hero text-hero-foreground shadow-lift">
          <Icono className="size-10" />
        </span>
      </div>
      <p className="font-display text-2xl font-bold tracking-tight text-foreground">{titulo}</p>
      <p className="max-w-xl text-base leading-relaxed text-muted-foreground">{descripcion}</p>
      {accion && <div className="mt-2 flex flex-wrap justify-center gap-3">{accion}</div>}
    </div>
  );
}
