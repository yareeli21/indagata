import { createFileRoute } from "@tanstack/react-router";
import { BarChart3 } from "lucide-react";
import { PagePlaceholder } from "@/components/layout/PagePlaceholder";

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
  component: () => (
    <PagePlaceholder
      titulo="KPIs"
      descripcion="Indicadores clave del repositorio y novedades de la plataforma."
      icono={BarChart3}
    />
  ),
});
