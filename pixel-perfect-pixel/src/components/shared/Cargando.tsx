import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface CargandoProps {
  /** Forma del contenido que se está cargando. */
  variante?: "tarjetas" | "tabla" | "lista" | "formulario";
  /** Número de elementos de relleno. */
  cantidad?: number;
  /** Texto para lectores de pantalla. */
  etiqueta?: string;
  className?: string | undefined;
}

/**
 * Esqueletos animados con la forma del contenido final, en lugar de un texto
 * "Cargando…". Anuncia el estado a tecnologías de asistencia.
 */
export function Cargando({
  variante = "tarjetas",
  cantidad = 6,
  etiqueta = "Cargando…",
  className,
}: CargandoProps) {
  const elementos = Array.from({ length: cantidad }, (_, i) => i);

  return (
    <div role="status" aria-live="polite" className={cn("w-full", className)}>
      <span className="sr-only">{etiqueta}</span>

      {variante === "tarjetas" && (
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(17rem,1fr))]">
          {elementos.map((i) => (
            <div key={i} className="superficie space-y-4 rounded-3xl p-6">
              <div className="flex items-center gap-3">
                <Skeleton className="size-12 rounded-2xl" />
                <Skeleton className="h-5 flex-1" />
              </div>
              <Skeleton className="h-4 w-11/12" />
              <Skeleton className="h-4 w-3/4" />
              <div className="flex gap-2 pt-2">
                <Skeleton className="h-7 w-24 rounded-full" />
                <Skeleton className="h-7 w-20 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      )}

      {variante === "tabla" && (
        <div className="superficie overflow-hidden rounded-3xl">
          <div className="flex gap-6 border-b border-border/70 bg-primary-soft/40 px-6 py-4">
            {[40, 15, 30, 15].map((w, i) => (
              <Skeleton key={i} className="h-4" style={{ width: `${w}%` }} />
            ))}
          </div>
          {elementos.map((i) => (
            <div key={i} className="flex items-center gap-6 border-b border-border/50 px-6 py-5">
              <Skeleton className="h-5 w-[40%]" />
              <Skeleton className="h-7 w-[15%] rounded-full" />
              <Skeleton className="h-5 w-[30%]" />
              <Skeleton className="h-5 w-[15%]" />
            </div>
          ))}
        </div>
      )}

      {variante === "lista" && (
        <div className="space-y-3">
          {elementos.map((i) => (
            <div key={i} className="superficie flex items-center gap-4 rounded-2xl p-4">
              <Skeleton className="size-12 shrink-0 rounded-xl" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-5 w-2/3" />
                <Skeleton className="h-4 w-1/3" />
              </div>
            </div>
          ))}
        </div>
      )}

      {variante === "formulario" && (
        <div className="grid gap-6 md:grid-cols-2">
          {elementos.map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-12 w-full" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
