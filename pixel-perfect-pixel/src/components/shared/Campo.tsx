import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CampoProps {
  /** `id` del control que etiqueta. */
  htmlFor: string;
  etiqueta: string;
  children: ReactNode;
  /** Texto de ayuda bajo el control. */
  ayuda?: ReactNode;
  error?: string | null | undefined;
  obligatorio?: boolean;
  className?: string | undefined;
}

/** Campo de formulario con etiqueta visible, ayuda y mensaje de error. */
export function Campo({
  htmlFor,
  etiqueta,
  children,
  ayuda,
  error,
  obligatorio = false,
  className,
}: CampoProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label htmlFor={htmlFor} className="text-sm font-bold text-foreground">
        {etiqueta}
        {obligatorio && (
          <span className="ml-1 text-destructive" aria-hidden>
            *
          </span>
        )}
      </label>
      {children}
      {error ? (
        <p role="alert" className="text-xs font-semibold text-destructive">
          {error}
        </p>
      ) : (
        ayuda && <p className="text-xs text-muted-foreground">{ayuda}</p>
      )}
    </div>
  );
}
