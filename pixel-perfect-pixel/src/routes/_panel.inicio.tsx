import { createFileRoute } from "@tanstack/react-router";
import { InicioPage } from "@/features/inicio/InicioPage";

export const Route = createFileRoute("/_panel/inicio")({
  head: () => ({
    meta: [
      { title: "Inicio — INDAGATA" },
      {
        name: "description",
        content:
          "Tu punto de partida en INDAGATA: métricas del acervo y accesos a instrumentos, KPIs y chat.",
      },
      { property: "og:title", content: "Inicio — INDAGATA" },
      {
        property: "og:description",
        content: "Métricas del acervo de investigación educativa y accesos a cada módulo.",
      },
    ],
  }),
  component: InicioPage,
});
