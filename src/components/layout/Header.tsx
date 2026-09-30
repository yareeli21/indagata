import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/features/auth/AuthContext";
import { ResearchSelector } from "./ResearchSelector";

export function Header() {
  const { usuario, salir } = useAuth();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border bg-card px-4 md:px-8">
      <ResearchSelector />

      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium text-foreground">{usuario?.nombre}</p>
        </div>
        <Badge variant="secondary" className="rounded-full">
          {usuario?.rol}
        </Badge>
        <Button variant="ghost" size="sm" onClick={salir} className="text-muted-foreground">
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Cerrar sesión</span>
        </Button>
      </div>
    </header>
  );
}
