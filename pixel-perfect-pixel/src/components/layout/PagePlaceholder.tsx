import type { LucideIcon } from "lucide-react";
import { EstadoVacio } from "@/components/shared/EstadoVacio";
import { PageHeader } from "./PageHeader";
import { Pagina } from "./Pagina";

interface PagePlaceholderProps {
  titulo: string;
  descripcion: string;
  icono: LucideIcon;
}

export function PagePlaceholder({ titulo, descripcion, icono }: PagePlaceholderProps) {
  return (
    <Pagina>
      <PageHeader titulo={titulo} descripcion={descripcion} icono={icono} />
      <EstadoVacio
        icono={icono}
        titulo="Pantalla en construcción"
        descripcion="El contenido de esta sección se agregará en el siguiente paso."
      />
    </Pagina>
  );
}
