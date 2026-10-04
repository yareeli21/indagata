import { createFileRoute } from "@tanstack/react-router";
import { EspacioVectorialPage } from "@/features/espacio-vectorial/EspacioVectorialPage";

export const Route = createFileRoute("/_panel/espacio")({
  head: () => ({
    meta: [
      { title: "Espacio vectorial — INDAGATA" },
      {
        name: "description",
        content:
          "Proyección 2D de los embeddings de ChromaDB coloreada por colección (KPIs e instrumentos).",
      },
      { property: "og:title", content: "Espacio vectorial — INDAGATA" },
      {
        property: "og:description",
        content:
          "Proyección 2D de los embeddings de ChromaDB coloreada por colección (KPIs e instrumentos).",
      },
    ],
  }),
  component: EspacioVectorialPage,
});
