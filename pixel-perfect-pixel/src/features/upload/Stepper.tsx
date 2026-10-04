import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface StepperProps {
  pasos: string[];
  actual: number;
}

export function Stepper({ pasos, actual }: StepperProps) {
  return (
    <ol className="flex w-full items-start">
      {pasos.map((paso, i) => {
        const hecho = i < actual;
        const activo = i === actual;
        return (
          <li key={paso} className="relative flex flex-1 flex-col items-center gap-2 text-center">
            {i > 0 && (
              <span
                className={cn(
                  "absolute right-1/2 top-4 h-0.5 w-full -translate-y-1/2",
                  i <= actual ? "bg-primary" : "bg-border",
                )}
              />
            )}
            <span
              aria-current={activo ? "step" : undefined}
              className={cn(
                "relative z-10 flex size-8 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors",
                hecho && "border-primary bg-primary text-primary-foreground",
                activo &&
                  "border-primary bg-primary text-primary-foreground ring-4 ring-primary/20",
                !hecho && !activo && "border-border bg-card text-muted-foreground",
              )}
            >
              {hecho ? <Check className="size-4" strokeWidth={3} /> : i + 1}
            </span>
            <span
              className={cn(
                "hidden text-xs sm:block",
                activo ? "font-semibold text-foreground" : "text-muted-foreground",
              )}
            >
              {paso}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
