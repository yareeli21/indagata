import { createFileRoute } from "@tanstack/react-router";
import { FolderOpen } from "lucide-react";
import { PagePlaceholder } from "@/components/layout/PagePlaceholder";

export const Route = createFileRoute("/_panel/investigacion")({
  head: () => ({
    meta: [
      { title: "Armar investigación — INDAGATA" },
      {
        name: "description",
        content: "Agrupa instrumentos y define el alcance de tu proyecto de investigación.",
      },
      { property: "og:title", content: "Armar investigación — INDAGATA" },
      {
        property: "og:description",
        content: "Agrupa instrumentos y define el alcance de tu proyecto de investigación.",
      },
    ],
  }),
  component: () => (
    <PagePlaceholder
      titulo="Armar investigación"
      descripcion="Selecciona instrumentos y niveles educativos para conformar tu proyecto."
      icono={FolderOpen}
    />
  ),
});
