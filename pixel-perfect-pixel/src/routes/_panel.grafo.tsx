import { createFileRoute } from "@tanstack/react-router";
import { GrafoPage } from "@/features/grafo/GrafoPage";

export const Route = createFileRoute("/_panel/grafo")({
  head: () => ({
    meta: [
      { title: "Grafo de recomendación — INDAGATA" },
      {
        name: "description",
        content:
          "Explora el acervo como un grafo y descubre instrumentos complementarios con un score híbrido de KPIs y similitud semántica.",
      },
      { property: "og:title", content: "Grafo de recomendación — INDAGATA" },
      {
        property: "og:description",
        content:
          "Explora el acervo como un grafo y descubre instrumentos complementarios con un score híbrido de KPIs y similitud semántica.",
      },
    ],
  }),
  component: GrafoPage,
});
