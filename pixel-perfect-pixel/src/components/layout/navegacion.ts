import {
  BarChart3,
  FolderOpen,
  LayoutDashboard,
  Library,
  MessageSquare,
  Network,
  Upload,
  UserPlus,
  type LucideIcon,
} from "lucide-react";
import type { Rol } from "@/types";

export interface OpcionNavegacion {
  to:
    | "/inicio"
    | "/instrumentos"
    | "/instrumentos/nuevo"
    | "/investigacion"
    | "/chat"
    | "/kpis"
    | "/espacio"
    | "/usuarios";
  etiqueta: string;
  icono: LucideIcon;
}

export interface GrupoNavegacion {
  titulo: string | null;
  opciones: OpcionNavegacion[];
}

/** Navegación del panel, compartida por el Sidebar y el menú móvil. */
export function gruposNavegacion(rol: Rol | undefined): GrupoNavegacion[] {
  const grupos: GrupoNavegacion[] = [
    {
      titulo: null,
      opciones: [{ to: "/inicio", etiqueta: "Inicio", icono: LayoutDashboard }],
    },
    {
      titulo: "Explorar",
      opciones: [
        { to: "/instrumentos", etiqueta: "Mis instrumentos", icono: Library },
        { to: "/kpis", etiqueta: "KPIs", icono: BarChart3 },
        { to: "/espacio", etiqueta: "Espacio vectorial", icono: Network },
      ],
    },
    {
      titulo: "Crear",
      opciones: [
        { to: "/instrumentos/nuevo", etiqueta: "Subir instrumento", icono: Upload },
        { to: "/investigacion", etiqueta: "Armar investigación", icono: FolderOpen },
        { to: "/chat", etiqueta: "Chat", icono: MessageSquare },
      ],
    },
  ];
  if (rol === "Administrador") {
    grupos.push({
      titulo: "Administración",
      opciones: [{ to: "/usuarios", etiqueta: "Gestión de usuarios", icono: UserPlus }],
    });
  }
  return grupos;
}

/** Rutas que solo deben marcarse activas con coincidencia exacta. */
export const RUTAS_EXACTAS = new Set<string>(["/inicio", "/instrumentos"]);
