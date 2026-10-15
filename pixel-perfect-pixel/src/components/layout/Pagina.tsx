import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PaginaProps {
  children: ReactNode;
  /**
   * Para vistas tipo aplicación (p. ej. Chat): la página ocupa la altura
   * disponible y sus hijos gestionan su propio scroll.
   */
  ajustarAlto?: boolean;
  className?: string | undefined;
}

/**
 * Contenedor único de las pantallas del panel: ancho completo junto al sidebar
 * con márgenes proporcionales al tamaño de pantalla. Ninguna página debe
 * limitar su ancho con `max-w-*`/`mx-auto`.
 */
export function Pagina({ children, ajustarAlto = false, className }: PaginaProps) {
  return (
    <div
      className={cn(
        "w-full min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-10 2xl:px-14",
        ajustarAlto ? "flex min-h-0 flex-1 flex-col gap-6" : "space-y-8 lg:space-y-10",
        className,
      )}
    >
      {children}
    </div>
  );
}
