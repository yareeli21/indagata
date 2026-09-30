import { createFileRoute } from "@tanstack/react-router";
import { MessageSquare } from "lucide-react";
import { PagePlaceholder } from "@/components/layout/PagePlaceholder";

export const Route = createFileRoute("/_panel/chat")({
  head: () => ({
    meta: [
      { title: "Chat — INDAGATA" },
      {
        name: "description",
        content: "Consulta con IA los instrumentos y reactivos del repositorio.",
      },
      { property: "og:title", content: "Chat — INDAGATA" },
      {
        property: "og:description",
        content: "Consulta con IA los instrumentos y reactivos del repositorio.",
      },
    ],
  }),
  component: () => (
    <PagePlaceholder
      titulo="Chat"
      descripcion="Pregunta en lenguaje natural sobre los instrumentos de tu investigación activa."
      icono={MessageSquare}
    />
  ),
});
