import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface Paso {
  numero: number;
  etiqueta: string;
}

interface StepperProps {
  pasos: Paso[];
  actual: number; // 1-indexed
}

export function Stepper({ pasos, actual }: StepperProps) {
  return (
    <nav aria-label="Pasos del asistente">
      <ol className="flex items-center gap-0">
        {pasos.map((paso, idx) => {
          const completado = paso.numero < actual;
          const activo = paso.numero === actual;
          const ultimo = idx === pasos.length - 1;

          return (
            <li key={paso.numero} className="flex flex-1 items-center">
              {/* Círculo + etiqueta */}
              <div className="flex flex-col items-center gap-1.5">
                <span
                  aria-current={activo ? "step" : undefined}
                  className={cn(
                    "flex size-8 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors",
                    completado && "border-primary bg-primary text-primary-foreground",
                    activo &&
                      "border-primary bg-primary text-primary-foreground ring-4 ring-primary/20",
                    !completado && !activo && "border-border bg-card text-muted-foreground",
                  )}
                >
                  {completado ? <Check className="size-4" strokeWidth={3} /> : paso.numero}
                </span>
                <span
                  className={cn(
                    "whitespace-nowrap text-xs font-medium",
                    activo ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {paso.etiqueta}
                </span>
              </div>

              {/* Línea conectora (excepto el último) */}
              {!ultimo && (
                <div
                  className={cn(
                    "mb-5 h-0.5 flex-1 transition-colors",
                    completado ? "bg-primary" : "bg-border",
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
