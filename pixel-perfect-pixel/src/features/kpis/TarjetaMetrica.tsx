import { Minus, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";
import { NumberTicker } from "@/components/efectos/NumberTicker";
import { cn } from "@/lib/utils";
import type { Kpi } from "@/types";

interface TarjetaMetricaProps {
  kpi: Kpi;
  /** Ícono decorativo opcional para la métrica. */
  icono?: LucideIcon | undefined;
  /** Oculta la píldora de variación (métricas calculadas en el cliente). */
  mostrarVariacion?: boolean;
  className?: string;
}

/** Métrica resumida del acervo: valor grande animado + variación accesible. */
export function TarjetaMetrica({
  kpi,
  icono: Icono,
  mostrarVariacion = true,
  className,
}: TarjetaMetricaProps) {
  const sube = kpi.variacion > 0;
  const baja = kpi.variacion < 0;
  const IconoVariacion = sube ? TrendingUp : baja ? TrendingDown : Minus;

  return (
    <div
      className={cn(
        "group relative h-full overflow-hidden rounded-2xl border border-border bg-card p-5 shadow-card transition-shadow hover:shadow-lift md:p-6",
        className,
      )}
    >
      {/* Barra de acento superior */}
      <span aria-hidden className="absolute inset-x-0 top-0 h-1 bg-accent" />
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-muted-foreground">{kpi.etiqueta}</p>
        {Icono && (
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
            <Icono className="size-5" aria-hidden />
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
        <NumberTicker
          valor={kpi.valor}
          className="font-display text-4xl font-bold leading-none tracking-tight text-foreground"
        />
        {mostrarVariacion && kpi.variacion !== 0 && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-bold",
              sube && "bg-success-soft text-success",
              baja && "bg-destructive/10 text-destructive",
              !sube && !baja && "bg-muted text-muted-foreground",
            )}
          >
            <IconoVariacion className="size-4" aria-hidden />
            <span aria-hidden>
              {sube ? "+" : ""}
              {kpi.variacion}%
            </span>
            <span className="sr-only">
              {sube
                ? `aumentó ${kpi.variacion}%`
                : baja
                  ? `disminuyó ${Math.abs(kpi.variacion)}%`
                  : "sin cambio"}
            </span>
          </span>
        )}
      </div>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{kpi.detalle}</p>
    </div>
  );
}
