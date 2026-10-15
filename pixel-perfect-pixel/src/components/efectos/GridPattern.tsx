import { useId } from "react";
import { cn } from "@/lib/utils";

interface GridPatternProps {
  className?: string;
  /** Tamaño de cada celda en px. */
  tamano?: number;
}

/**
 * Cuadrícula decorativa con desvanecido radial (inspirada en GridPattern de
 * Magic UI). Hereda el color del texto (`currentColor`), así que se tiñe con
 * clases de token, p. ej. `text-hero-foreground/10`.
 */
export function GridPattern({ className, tamano = 40 }: GridPatternProps) {
  const id = useId();
  return (
    <svg
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 h-full w-full [mask-image:radial-gradient(ellipse_at_top_right,black_20%,transparent_70%)]",
        className,
      )}
    >
      <defs>
        <pattern id={id} width={tamano} height={tamano} patternUnits="userSpaceOnUse">
          <path d={`M ${tamano} 0 L 0 0 0 ${tamano}`} fill="none" stroke="currentColor" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
