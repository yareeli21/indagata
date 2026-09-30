import { createFileRoute } from "@tanstack/react-router";
import { UploadWizard } from "@/features/upload/UploadWizard";

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
  component: UploadWizard,
});
