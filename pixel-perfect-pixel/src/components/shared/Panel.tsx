import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface PanelProps {
  children: ReactNode;
  titulo?: string | undefined;
  descripcion?: ReactNode;
  icono?: LucideIcon | undefined;
  /** Contenido alineado a la derecha del encabezado. */
  acciones?: ReactNode;
  /** Pie del panel (navegación de un asistente, botones). */
  pie?: ReactNode;
  /** Eleva el panel al pasar el mouse. */
  interactivo?: boolean;
  /** Sin padding interno en el cuerpo (tablas, listas a sangre). */
  sinRelleno?: boolean;
  as?: "section" | "div" | "aside";
  className?: string | undefined;
  claseCuerpo?: string | undefined;
}

/** Tarjeta de sección estándar: superficie con profundidad y encabezado opcional. */
export function Panel({
  children,
  titulo,
  descripcion,
  icono: Icono,
  acciones,
  pie,
  interactivo = false,
  sinRelleno = false,
  as: Etiqueta = "section",
  className,
  claseCuerpo,
}: PanelProps) {
  const conEncabezado = Boolean(titulo || acciones);
  return (
    <Etiqueta
      className={cn(
        "superficie flex min-w-0 flex-col overflow-hidden rounded-3xl",
        interactivo &&
          "transition-[transform,box-shadow] duration-300 hover:-translate-y-1 hover:shadow-lift",
        className,
      )}
    >
      {conEncabezado && (
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/70 px-6 py-5 lg:px-8 lg:py-6">
          <div className="flex min-w-0 items-start gap-4">
            {Icono && (
              <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary-soft text-primary">
                <Icono className="size-6" aria-hidden />
              </span>
            )}
            <div className="min-w-0 space-y-1">
              {titulo && (
                <h2 className="font-display text-xl font-bold tracking-tight text-foreground">
                  {titulo}
                </h2>
              )}
              {descripcion && <div className="text-sm text-muted-foreground">{descripcion}</div>}
            </div>
          </div>
          {acciones && <div className="flex flex-wrap items-center gap-3">{acciones}</div>}
        </div>
      )}
      <div className={cn("min-w-0 flex-1", !sinRelleno && "p-6 lg:p-8", claseCuerpo)}>
        {children}
      </div>
      {pie && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/70 bg-primary-soft/40 px-6 py-4 lg:px-8">
          {pie}
        </div>
      )}
    </Etiqueta>
  );
}
