import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { GridPattern } from "@/components/efectos/GridPattern";

interface PageHeaderProps {
  titulo: string;
  descripcion?: string;
  /** Contenido alineado a la derecha (acciones, toggles, buscadores). */
  acciones?: ReactNode;
  /** Nivel semántico del encabezado; por defecto h1. */
  as?: "h1" | "h2";
  /** Ícono del módulo, mostrado en un chip junto al título. */
  icono?: LucideIcon | undefined;
  /** Texto corto sobre el título (p. ej. el nombre del módulo). */
  etiqueta?: string | undefined;
  /** `hero`: banda índigo a todo el ancho; `simple`: sobre el lienzo. */
  variante?: "simple" | "hero";
  /** Contenido adicional bajo el título (métricas, chips…). */
  children?: ReactNode;
  className?: string;
}

/**
 * Encabezado de pantalla compartido por todas las vistas del panel: chip con
 * ícono, título grande en font-display y descripción legible.
 */
export function PageHeader({
  titulo,
  descripcion,
  acciones,
  as: Titulo = "h1",
  icono: Icono,
  etiqueta,
  variante = "simple",
  children,
  className,
}: PageHeaderProps) {
  const hero = variante === "hero";

  return (
    <header
      className={cn(
        "relative",
        hero && "overflow-hidden rounded-3xl bg-hero px-6 py-8 shadow-elevated sm:px-10 sm:py-10",
        className,
      )}
    >
      {hero && <GridPattern className="text-hero-foreground/[0.07]" tamano={40} />}
      <div className="relative flex flex-wrap items-end justify-between gap-6">
        <div className="flex min-w-0 items-start gap-4 sm:gap-5">
          {Icono && (
            <span
              className={cn(
                "hidden size-16 shrink-0 items-center justify-center rounded-2xl sm:flex",
                hero
                  ? "bg-accent text-accent-foreground shadow-glow"
                  : "bg-hero text-hero-foreground shadow-lift",
              )}
            >
              <Icono className="size-8" aria-hidden />
            </span>
          )}
          <div className="min-w-0 space-y-2">
            {etiqueta && (
              <p
                className={cn(
                  "text-xs font-bold uppercase tracking-[0.16em]",
                  hero ? "text-accent" : "text-accent-strong",
                )}
              >
                {etiqueta}
              </p>
            )}
            <Titulo
              className={cn(
                "font-display text-3xl font-bold tracking-tight md:text-4xl",
                hero ? "text-hero-foreground" : "text-foreground",
              )}
            >
              {titulo}
            </Titulo>
            {descripcion && (
              <p
                className={cn(
                  "max-w-4xl text-base leading-relaxed",
                  hero ? "text-hero-muted" : "text-muted-foreground",
                )}
              >
                {descripcion}
              </p>
            )}
          </div>
        </div>
        {acciones && <div className="flex flex-wrap items-center gap-3">{acciones}</div>}
      </div>
      {children && <div className="relative mt-6">{children}</div>}
    </header>
  );
}
