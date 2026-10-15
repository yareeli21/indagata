import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { ArrowRight, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OpcionNavegacion } from "@/components/layout/navegacion";

interface GatewayProps {
  to: OpcionNavegacion["to"];
  titulo: string;
  descripcion: string;
  cta: string;
  icono: LucideIcon;
  /** Dato destacado (p. ej. "12 instrumentos"). */
  dato?: string | undefined;
  /** Visual decorativo (mini-gráfica, constelación…). */
  visual?: ReactNode;
  /** Variante "destacada": fondo hero índigo. */
  destacado?: boolean;
  className?: string;
}

/**
 * Punto de entrada a un módulo (bento card inspirada en Magic UI). Toda la
 * tarjeta es un enlace; el visual es decorativo (aria-hidden).
 */
export function Gateway({
  to,
  titulo,
  descripcion,
  cta,
  icono: Icono,
  dato,
  visual,
  destacado = false,
  className,
}: GatewayProps) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      className={cn("h-full", className)}
    >
      <Link
        to={to}
        className={cn(
          "group relative flex h-full min-h-56 flex-col overflow-hidden rounded-3xl border p-6 transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:p-7",
          destacado
            ? "border-transparent bg-hero text-hero-foreground shadow-elevated hover:shadow-glow"
            : "border-border bg-card text-card-foreground shadow-card hover:border-primary/30 hover:shadow-lift",
        )}
      >
        {visual && (
          <div aria-hidden className="pointer-events-none absolute inset-0">
            {visual}
          </div>
        )}

        <div className="relative flex items-start justify-between gap-4">
          <span
            className={cn(
              "flex size-14 items-center justify-center rounded-2xl transition-transform group-hover:scale-105",
              destacado
                ? "bg-accent text-accent-foreground"
                : "bg-primary-soft text-primary group-hover:bg-primary group-hover:text-primary-foreground",
            )}
          >
            <Icono className="size-7" aria-hidden />
          </span>
          {dato && (
            <span
              className={cn(
                "rounded-full px-3 py-1 text-sm font-bold",
                destacado
                  ? "bg-hero-foreground/10 text-hero-foreground"
                  : "bg-accent-soft text-accent-foreground",
              )}
            >
              {dato}
            </span>
          )}
        </div>

        <div className="relative mt-auto space-y-2 pt-8">
          <h3
            className={cn(
              "font-display text-xl font-bold tracking-tight md:text-2xl",
              destacado ? "text-hero-foreground" : "text-foreground",
            )}
          >
            {titulo}
          </h3>
          <p
            className={cn(
              "max-w-md text-sm leading-relaxed",
              destacado ? "text-hero-muted" : "text-muted-foreground",
            )}
          >
            {descripcion}
          </p>
          <span
            className={cn(
              "inline-flex items-center gap-2 pt-2 text-sm font-bold",
              destacado ? "text-accent" : "text-primary",
            )}
          >
            {cta}
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
          </span>
        </div>
      </Link>
    </motion.div>
  );
}
