import { createFileRoute } from "@tanstack/react-router";
import { ArmarInvestigacionPage } from "@/features/research/ArmarInvestigacionPage";

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
  component: ArmarInvestigacionPage,
});
