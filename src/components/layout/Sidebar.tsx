import { Link } from "@tanstack/react-router";
import { BarChart3, FolderOpen, MessageSquare, Upload, Library } from "lucide-react";

const OPCIONES = [
  { to: "/instrumentos", etiqueta: "Mis instrumentos", icono: Library },
  { to: "/instrumentos/nuevo", etiqueta: "Subir instrumento", icono: Upload },
  { to: "/investigacion", etiqueta: "Armar investigación", icono: FolderOpen },
  { to: "/chat", etiqueta: "Chat", icono: MessageSquare },
  { to: "/kpis", etiqueta: "KPIs", icono: BarChart3 },
] as const;

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar px-4 py-6 md:flex">
      <Link to="/instrumentos" className="mb-8 flex items-center gap-3 px-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-base font-bold text-primary-foreground">
          I
        </span>
        <span className="text-lg font-semibold tracking-tight text-sidebar-foreground">
          INDAGATA
        </span>
      </Link>

      <nav className="flex flex-col gap-1">
        {OPCIONES.map(({ to, etiqueta, icono: Icono }) => (
          <Link
            key={to}
            to={to}
            activeOptions={{ exact: to === "/instrumentos" }}
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            activeProps={{
              className: "bg-sidebar-accent text-sidebar-accent-foreground",
            }}
          >
            <Icono className="h-4 w-4" />
            {etiqueta}
          </Link>
        ))}
      </nav>

      <p className="mt-auto px-3 text-xs leading-relaxed text-muted-foreground">
        Repositorio de instrumentos de investigación educativa en México.
      </p>
    </aside>
  );
}
