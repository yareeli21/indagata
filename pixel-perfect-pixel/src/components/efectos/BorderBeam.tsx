import type { ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

interface BorderBeamProps {
  children: ReactNode;
  /** Clases del contenedor externo (radio, sombra, tamaño). */
  className?: string | undefined;
  /** Clases del contenido interno (fondo opaco, padding). */
  claseContenido?: string | undefined;
  /** Segundos por vuelta. */
  duracion?: number;
}

/**
 * Marco con un haz de luz ámbar que recorre el borde (inspirado en BorderBeam
 * de Magic UI). El haz es un degradado cónico que gira detrás del contenido;
 * el contenido, con fondo opaco y 1.5px de margen, solo deja ver el borde.
 */
export function BorderBeam({ children, className, claseContenido, duracion = 6 }: BorderBeamProps) {
  const reducido = useReducedMotion();
  return (
    <div className={cn("relative overflow-hidden rounded-3xl p-[1.5px]", className)}>
      <div aria-hidden className="absolute inset-0 bg-hero-foreground/15" />
      <motion.div
        aria-hidden
        className="absolute left-1/2 top-1/2 aspect-square w-[220%] -translate-x-1/2 -translate-y-1/2 bg-[conic-gradient(from_0deg,transparent_0deg,var(--accent)_50deg,transparent_100deg)]"
        animate={reducido ? {} : { rotate: 360 }}
        transition={{ duration: duracion, ease: "linear", repeat: Infinity }}
      />
      <div className={cn("relative h-full rounded-[calc(1.5rem-1.5px)]", claseContenido)}>
        {children}
      </div>
    </div>
  );
}
