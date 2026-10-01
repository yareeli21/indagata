import { createFileRoute } from "@tanstack/react-router";
import { ChatPage } from "@/features/chat/ChatPage";

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
  component: ChatPage,
});
