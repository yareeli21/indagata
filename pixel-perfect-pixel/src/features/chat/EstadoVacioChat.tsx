import { Link } from "@tanstack/react-router";
import { FolderOpen, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EstadoVacio } from "@/components/shared/EstadoVacio";

export function EstadoVacioChat() {
  return (
    <EstadoVacio
      icono={MessageSquare}
      titulo="No tienes una investigación activa"
      descripcion="El chat consulta los instrumentos de tu investigación activa. Arma una investigación para empezar."
      accion={
        <Button asChild variant="accent" size="lg">
          <Link to="/investigacion">
            <FolderOpen />
            Armar investigación
          </Link>
        </Button>
      }
    />
  );
}
