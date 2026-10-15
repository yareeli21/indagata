import { createFileRoute } from "@tanstack/react-router";
import { ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Pagina } from "@/components/layout/Pagina";
import { GestionUsuariosPage } from "@/features/usuarios/GestionUsuariosPage";
import { useAuth } from "@/features/auth/AuthContext";

export const Route = createFileRoute("/_panel/usuarios")({
  head: () => ({
    meta: [
      { title: "Gestión de usuarios — INDAGATA" },
      {
        name: "description",
        content: "Alta de nuevos usuarios de INDAGATA. Disponible solo para administradores.",
      },
      { property: "og:title", content: "Gestión de usuarios — INDAGATA" },
      {
        property: "og:description",
        content: "Alta de nuevos usuarios de INDAGATA. Disponible solo para administradores.",
      },
    ],
  }),
  component: UsuariosRoute,
});

function UsuariosRoute() {
  const { usuario } = useAuth();

  if (usuario?.rol !== "Administrador") {
    return (
      <Pagina>
        <PageHeader
          icono={ShieldAlert}
          titulo="Acceso restringido"
          descripcion="No tienes permisos para ver esta sección. Se requiere rol administrador."
        />
      </Pagina>
    );
  }

  return <GestionUsuariosPage />;
}
