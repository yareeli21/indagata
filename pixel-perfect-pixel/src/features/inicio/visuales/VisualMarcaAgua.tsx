import type { LucideIcon } from "lucide-react";

/** Ícono gigante desvanecido en la esquina (gateways sin visual propio). */
export function VisualMarcaAgua({ icono: Icono }: { icono: LucideIcon }) {
  return <Icono className="absolute -bottom-8 -right-8 size-44 text-primary/[0.06]" />;
}
