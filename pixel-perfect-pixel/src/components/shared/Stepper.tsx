import { motion } from "motion/react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface StepperProps {
  /** Etiquetas de los pasos, en orden. */
  pasos: string[];
  /** Índice del paso actual (0-indexed). */
  actual: number;
  className?: string | undefined;
}

/**
 * Indicador de progreso de los asistentes (Subir instrumento, Armar
 * investigación). En pantallas medianas y grandes muestra todos los pasos con
 * su etiqueta; en móvil, el paso actual y una barra de progreso.
 */
export function Stepper({ pasos, actual, className }: StepperProps) {
  const total = pasos.length;
  const progreso = total > 1 ? Math.round((actual / (total - 1)) * 100) : 100;

  return (
    <nav
      aria-label="Pasos del asistente"
      className={cn("superficie rounded-3xl p-5 sm:p-6", className)}
    >
      {/* Resumen + barra (siempre visible; en md+ acompaña a los círculos) */}
      <div className="flex flex-wrap items-end justify-between gap-2">
        <p className="text-sm font-semibold text-muted-foreground">
          Paso <span className="text-foreground">{actual + 1}</span> de {total}
          <span className="font-display text-lg font-bold text-foreground md:hidden">
            {" "}
            · {pasos[actual]}
          </span>
        </p>
        <p className="font-display text-lg font-bold text-primary tabular-nums">{progreso}%</p>
      </div>
      <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-primary-soft md:hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-primary to-primary-glow"
          initial={false}
          animate={{ width: `${Math.max(progreso, 6)}%` }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>

      <ol className="mt-5 hidden w-full items-start md:flex">
        {pasos.map((paso, i) => {
          const hecho = i < actual;
          const activo = i === actual;
          return (
            <li key={paso} className="relative flex flex-1 flex-col items-center gap-3 text-center">
              {i > 0 && (
                <span
                  aria-hidden
                  className="absolute right-1/2 top-6 h-1 w-full -translate-y-1/2 overflow-hidden rounded-full bg-border"
                >
                  <motion.span
                    className="block h-full bg-primary"
                    initial={false}
                    animate={{ width: i <= actual ? "100%" : "0%" }}
                    transition={{ duration: 0.45, ease: "easeOut" }}
                  />
                </span>
              )}
              <span
                aria-current={activo ? "step" : undefined}
                className={cn(
                  "relative z-10 flex size-12 items-center justify-center rounded-full border-2 font-display text-lg font-bold transition-all duration-300",
                  hecho && "border-primary bg-primary text-primary-foreground",
                  activo &&
                    "scale-110 border-accent bg-hero text-hero-foreground shadow-glow ring-4 ring-accent/25",
                  !hecho && !activo && "border-border bg-card text-muted-foreground",
                )}
              >
                {hecho ? <Check className="size-5" strokeWidth={3} /> : i + 1}
              </span>
              <span
                className={cn(
                  "px-1 text-sm leading-snug",
                  activo
                    ? "font-bold text-foreground"
                    : hecho
                      ? "font-semibold text-primary"
                      : "text-muted-foreground",
                )}
              >
                {paso}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
