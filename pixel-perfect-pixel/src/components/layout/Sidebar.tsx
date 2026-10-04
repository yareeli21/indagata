import { Link } from "@tanstack/react-router";
import {
  BarChart3,
  FolderOpen,
  MessageSquare,
  Network,
  Upload,
  Library,
  UserPlus,
} from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";

const OPCIONES = [
  { to: "/instrumentos", etiqueta: "Mis instrumentos", icono: Library },
  { to: "/instrumentos/nuevo", etiqueta: "Subir instrumento", icono: Upload },
  { to: "/investigacion", etiqueta: "Armar investigación", icono: FolderOpen },
  { to: "/chat", etiqueta: "Chat", icono: MessageSquare },
  { to: "/kpis", etiqueta: "KPIs", icono: BarChart3 },
  { to: "/espacio", etiqueta: "Espacio vectorial", icono: Network },
] as const;

const OPCIONES_ADMIN = [
  { to: "/usuarios", etiqueta: "Gestión de usuarios", icono: UserPlus },
] as const;

export function Sidebar() {
  const { usuario } = useAuth();
  const opciones =
    usuario?.rol === "Administrador" ? [...OPCIONES, ...OPCIONES_ADMIN] : OPCIONES;

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar px-4 py-6 md:flex">
      <Link
        to="/instrumentos"
        className="mb-8 flex items-center gap-3 rounded-xl px-2 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary font-display text-base font-bold text-primary-foreground shadow-card">
          I
        </span>
        <span className="font-display text-lg font-semibold tracking-tight text-sidebar-foreground">
          INDAGATA
        </span>
      </Link>

      <nav className="flex flex-col gap-1">
        {opciones.map(({ to, etiqueta, icono: Icono }) => (
          <Link
            key={to}
            to={to}
            activeOptions={{ exact: to === "/instrumentos" }}
            className="group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
            activeProps={{
              className: "bg-sidebar-accent font-semibold text-sidebar-accent-foreground",
            }}
          >
            {({ isActive }) => (
              <>
                <span
                  aria-hidden
                  className={`absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-full bg-primary transition-opacity ${
                    isActive ? "opacity-100" : "opacity-0"
                  }`}
                />
                <Icono className="h-4 w-4" />
                {etiqueta}
              </>
            )}
          </Link>
        ))}
      </nav>

      <p className="mt-auto px-3 text-xs leading-relaxed text-muted-foreground">
        Repositorio de instrumentos de investigación educativa en México.
      </p>
    </aside>
  );
}
