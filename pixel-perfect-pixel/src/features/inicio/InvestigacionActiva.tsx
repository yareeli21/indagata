import { Link } from "@tanstack/react-router";
import { BarChart3, FolderOpen, MessageSquare, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Investigacion } from "@/types";

interface InvestigacionActivaProps {
  activa: Investigacion | null;
  /** Número de instrumentos fuente de la investigación activa. */
  fuentes: number;
}

/** Estado de la investigación activa con accesos directos a KPIs y Chat. */
export function InvestigacionActiva({ activa, fuentes }: InvestigacionActivaProps) {
  return (
    <section className="relative flex h-full flex-col overflow-hidden rounded-3xl border border-border bg-card bg-cuadricula p-6 shadow-card md:p-7">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-accent-soft text-accent-strong">
        <Target className="size-7" aria-hidden />
      </span>
      <p className="mt-5 text-sm font-bold uppercase tracking-[0.14em] text-muted-foreground">
        Investigación activa
      </p>

      {activa ? (
        <>
          <h2 className="mt-2 font-display text-2xl font-bold leading-tight tracking-tight">
            {activa.nombre}
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            <span className="font-display text-3xl font-bold text-foreground">{fuentes}</span>{" "}
            {fuentes === 1 ? "instrumento fuente" : "instrumentos fuente"}
          </p>
          <div className="mt-auto flex flex-wrap gap-3 pt-6">
            <Button asChild>
              <Link to="/kpis">
                <BarChart3 /> Ver dashboard
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/chat">
                <MessageSquare /> Consultar
              </Link>
            </Button>
          </div>
        </>
      ) : (
        <>
          <h2 className="mt-2 font-display text-2xl font-bold leading-tight tracking-tight">
            Aún no tienes una investigación activa
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Elige tus instrumentos fuente para obtener dashboards de KPIs y respuestas del chat
            enfocadas en tu proyecto.
          </p>
          <div className="mt-auto pt-6">
            <Button asChild variant="accent">
              <Link to="/investigacion">
                <FolderOpen /> Armar investigación
              </Link>
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
