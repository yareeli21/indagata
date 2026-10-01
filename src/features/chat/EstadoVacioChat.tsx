import { Link } from "@tanstack/react-router";
import { FolderOpen, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EstadoVacioChat() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-20 text-center">
      <span className="flex size-16 items-center justify-center rounded-full bg-primary/10 text-primary">
        <MessageSquare className="size-8" />
      </span>
      <div className="space-y-1">
        <p className="text-lg font-semibold">No tienes una investigación activa</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          El chat consulta los instrumentos de tu investigación activa. Arma una
          investigación para empezar.
        </p>
      </div>
      <Button asChild>
        <Link to="/investigacion">
          <FolderOpen />
          Armar investigación
        </Link>
      </Button>
    </div>
  );
}
