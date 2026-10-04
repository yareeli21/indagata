import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/PageHeader";
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
      <div className="space-y-8 p-6 md:p-8">
        <PageHeader
          titulo="Acceso restringido"
          descripcion="No tienes permisos para ver esta sección. Se requiere rol administrador."
        />
      </div>
    );
  }

  return <GestionUsuariosPage />;
}
