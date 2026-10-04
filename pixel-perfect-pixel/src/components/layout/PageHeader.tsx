import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  titulo: string;
  descripcion?: string;
  /** Contenido alineado a la derecha (acciones, toggles, buscadores). */
  acciones?: ReactNode;
  /** Nivel semántico del encabezado; por defecto h1. */
  as?: "h1" | "h2";
  className?: string;
}

/**
 * Encabezado de pantalla con la jerarquía del login aprobado:
 * título en font-display sobre texto secundario en text-muted-foreground.
 * Unifica el espaciado de todas las pantallas del panel.
 */
export function PageHeader({
  titulo,
  descripcion,
  acciones,
  as: Titulo = "h1",
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="space-y-1">
        <Titulo className="font-display text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
          {titulo}
        </Titulo>
        {descripcion && <p className="max-w-prose text-sm text-muted-foreground">{descripcion}</p>}
      </div>
      {acciones && <div className="flex flex-wrap items-center gap-3">{acciones}</div>}
    </div>
  );
}
