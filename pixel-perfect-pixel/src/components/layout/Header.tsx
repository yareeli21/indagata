import { useState } from "react";
import { LogOut, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useAuth } from "@/features/auth/AuthContext";
import { ResearchSelector } from "./ResearchSelector";
import { ListaNavegacion, Marca, TarjetaSubir } from "./Sidebar";

function iniciales(nombre: string | undefined): string {
  if (!nombre) return "?";
  const partes = nombre.trim().split(/\s+/);
  return ((partes[0]?.[0] ?? "") + (partes[1]?.[0] ?? "")).toUpperCase() || "?";
}

export function Header() {
  const { usuario, salir } = useAuth();
  const [menuAbierto, setMenuAbierto] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex h-18 shrink-0 items-center justify-between gap-3 border-b border-border bg-card/85 px-4 backdrop-blur-md sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3">
        {/* Menú móvil */}
        <Sheet open={menuAbierto} onOpenChange={setMenuAbierto}>
          <SheetTrigger asChild>
            <Button variant="outline" size="icon" className="md:hidden" aria-label="Abrir menú">
              <Menu />
            </Button>
          </SheetTrigger>
          <SheetContent
            side="left"
            className="flex w-[85vw] max-w-sm flex-col gap-8 overflow-y-auto bg-sidebar px-5 py-6"
          >
            <SheetTitle className="sr-only">Menú de navegación</SheetTitle>
            <Marca />
            <ListaNavegacion onNavegar={() => setMenuAbierto(false)} />
            <div className="mt-auto">
              <TarjetaSubir onNavegar={() => setMenuAbierto(false)} />
            </div>
          </SheetContent>
        </Sheet>

        <div className="min-w-0">
          <ResearchSelector />
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-bold leading-tight text-foreground">{usuario?.nombre}</p>
          <p className="text-sm text-muted-foreground">{usuario?.rol}</p>
        </div>
        <span
          aria-hidden
          className="flex size-11 items-center justify-center rounded-full bg-primary-soft font-display text-sm font-bold text-primary ring-2 ring-card"
        >
          {iniciales(usuario?.nombre)}
        </span>
        <Button variant="ghost" onClick={salir} className="px-3 text-muted-foreground">
          <LogOut />
          <span className="hidden xl:inline">Cerrar sesión</span>
          <span className="sr-only xl:hidden">Cerrar sesión</span>
        </Button>
      </div>
    </header>
  );
}
