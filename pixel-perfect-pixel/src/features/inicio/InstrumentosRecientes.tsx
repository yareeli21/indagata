import { Link } from "@tanstack/react-router";
import { ArrowRight, FileText } from "lucide-react";
import { Cargando } from "@/components/shared/Cargando";
import { Button } from "@/components/ui/button";
import { TipoBadge } from "@/features/instruments/TipoBadge";
import { EstadoBadge } from "@/features/instruments/EstadoBadge";
import type { Instrumento } from "@/types";

interface InstrumentosRecientesProps {
  /** `null` mientras carga. */
  instrumentos: Instrumento[] | null;
}

/** Lista de los instrumentos más recientes del acervo. */
export function InstrumentosRecientes({ instrumentos }: InstrumentosRecientesProps) {
  return (
    <section className="flex h-full flex-col rounded-3xl border border-border bg-card p-6 shadow-card md:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-bold tracking-tight md:text-2xl">
            Recién llegados al acervo
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Los últimos instrumentos que se sumaron a la plataforma.
          </p>
        </div>
        <Button asChild variant="ghost" className="text-primary">
          <Link to="/instrumentos">
            Ver todos <ArrowRight />
          </Link>
        </Button>
      </div>

      {instrumentos === null ? (
        <Cargando
          variante="lista"
          cantidad={4}
          etiqueta="Cargando instrumentos…"
          className="mt-5"
        />
      ) : instrumentos.length === 0 ? (
        <p className="flex flex-1 items-center justify-center py-12 text-center text-sm text-muted-foreground">
          Aún no hay instrumentos. ¡Sé quien inaugure el acervo!
        </p>
      ) : (
        <ul className="mt-5 grid gap-3 sm:grid-cols-2">
          {instrumentos.map((i) => (
            <li key={i.id}>
              <Link
                to="/instrumentos"
                className="group flex h-full gap-4 rounded-2xl border border-border bg-background p-4 transition-colors hover:border-primary/30 hover:bg-primary-soft/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary group-hover:bg-primary group-hover:text-primary-foreground">
                  <FileText className="size-6" aria-hidden />
                </span>
                <div className="min-w-0 space-y-2">
                  <p className="line-clamp-2 font-display text-base font-semibold leading-snug text-foreground">
                    {i.titulo}
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <TipoBadge tipo={i.tipo} />
                    <EstadoBadge estado={i.estado} />
                    <span className="text-sm text-muted-foreground">
                      {i.nivel} · {i.anio}
                    </span>
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
