import type { LucideIcon } from "lucide-react";

interface EstadoVacioProps {
  icono: LucideIcon;
  titulo: string;
  descripcion: string;
  accion?: React.ReactNode;
}

export function EstadoVacio({ icono: Icono, titulo, descripcion, accion }: EstadoVacioProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed bg-card px-6 py-16 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary"><Icono className="size-6" /></span>
      <p className="font-semibold">{titulo}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{descripcion}</p>
      {accion}
    </div>
  );
}
