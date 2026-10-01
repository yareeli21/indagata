import { createFileRoute } from "@tanstack/react-router";
import { KpisPage } from "@/features/kpis/KpisPage";

export const Route = createFileRoute("/_panel/kpis")({
  head: () => ({
    meta: [
      { title: "KPIs — INDAGATA" },
      {
        name: "description",
        content: "Indicadores del acervo de instrumentos y de la actividad de investigación.",
      },
      { property: "og:title", content: "KPIs — INDAGATA" },
      {
        property: "og:description",
        content: "Indicadores del acervo de instrumentos y de la actividad de investigación.",
      },
    ],
  }),
  component: KpisPage,
});
