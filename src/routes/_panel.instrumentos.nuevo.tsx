import { createFileRoute } from "@tanstack/react-router";
import { Upload } from "lucide-react";
import { PagePlaceholder } from "@/components/layout/PagePlaceholder";

export const Route = createFileRoute("/_panel/instrumentos/nuevo")({
  head: () => ({
    meta: [
      { title: "Subir instrumento — INDAGATA" },
      {
        name: "description",
        content: "Carga y estandariza un nuevo instrumento de recolección de datos.",
      },
      { property: "og:title", content: "Subir instrumento — INDAGATA" },
      {
        property: "og:description",
        content: "Carga y estandariza un nuevo instrumento de recolección de datos.",
      },
    ],
  }),
  component: () => (
    <PagePlaceholder
      titulo="Subir instrumento"
      descripcion="Carga un archivo y completa los metadatos para estandarizarlo."
      icono={Upload}
    />
  ),
});
