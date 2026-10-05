import { createFileRoute } from "@tanstack/react-router";
import { InstrumentosPage } from "@/features/instruments/InstrumentosPage";

export const Route = createFileRoute("/_panel/instrumentos/")({
  head: () => ({
    meta: [
      { title: "Mis instrumentos — INDAGATA" },
      {
        name: "description",
        content:
          "Consulta y filtra los instrumentos de recolección de datos registrados en INDAGATA.",
      },
      { property: "og:title", content: "Mis instrumentos — INDAGATA" },
      {
        property: "og:description",
        content: "Repositorio de encuestas, entrevistas y pruebas estandarizadas.",
      },
    ],
  }),
  component: InstrumentosPage,
});
