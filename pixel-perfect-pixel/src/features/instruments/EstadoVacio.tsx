import type { LucideIcon } from "lucide-react";

interface EstadoVacioProps {
  icono: LucideIcon;
  titulo: string;
  descripcion: string;
  accion?: React.ReactNode;
}

export function EstadoVacio({ icono: Icono, titulo, descripcion, accion }: EstadoVacioProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card px-6 py-16 text-center shadow-card">
      <span className="flex size-12 items-center justify-center rounded-2xl bg-primary-soft text-primary">
        <Icono className="size-6" />
      </span>
      <p className="font-display font-semibold text-foreground">{titulo}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{descripcion}</p>
      {accion}
    </div>
  );
}
