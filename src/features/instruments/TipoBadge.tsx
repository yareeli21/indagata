import { cn } from "@/lib/utils";
import type { TipoInstrumento } from "@/types";

const ESTILO: Record<TipoInstrumento, string> = {
  Encuesta: "bg-primary/10 text-primary",
  Entrevista: "bg-secondary text-secondary-foreground",
  "Prueba estandarizada": "bg-accent-soft text-accent-foreground",
};

export function TipoBadge({ tipo }: { tipo: TipoInstrumento }) {
  return (
    <span className={cn("inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium", ESTILO[tipo])}>
      {tipo}
    </span>
  );
}
