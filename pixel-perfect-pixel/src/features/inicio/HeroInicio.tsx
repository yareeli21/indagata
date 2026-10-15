import { Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { MessageSquare, Sparkles, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GridPattern } from "@/components/efectos/GridPattern";
import { BorderBeam } from "@/components/efectos/BorderBeam";
import { NumberTicker } from "@/components/efectos/NumberTicker";
import type { TipoInstrumento } from "@/types";

export interface ConteoTipo {
  tipo: TipoInstrumento;
  total: number;
}

interface HeroInicioProps {
  nombre: string;
  totalInstrumentos: number | null;
  conteoTipos: ConteoTipo[];
  totalKpis: number;
}

/** Hero de bienvenida: propuesta de valor, CTAs y "panel" con cifras del acervo. */
export function HeroInicio({ nombre, totalInstrumentos, conteoTipos, totalKpis }: HeroInicioProps) {
  const maximo = Math.max(1, ...conteoTipos.map((c) => c.total));

  return (
    <section className="relative overflow-hidden rounded-3xl bg-hero shadow-elevated">
      <GridPattern className="text-hero-foreground/[0.07]" tamano={44} />
      <div className="relative grid gap-10 px-6 py-10 sm:px-10 sm:py-12 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:items-center xl:px-14 xl:py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="space-y-6"
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-hero-foreground/20 bg-hero-foreground/10 px-4 py-1.5 text-sm font-semibold text-hero-foreground">
            <Sparkles className="size-4 text-accent" aria-hidden />
            Observatorio de investigación educativa
          </span>
          <h1 className="font-display text-3xl font-bold leading-[1.1] tracking-tight text-hero-foreground sm:text-4xl xl:text-5xl 2xl:text-6xl">
            Hola, {nombre}.{" "}
            <span className="block text-accent">Convierte tus instrumentos en evidencia.</span>
          </h1>
          <p className="max-w-2xl text-base leading-relaxed text-hero-muted sm:text-lg">
            Sube encuestas, entrevistas y pruebas; INDAGATA las estandariza, descubre qué KPIs
            educativos miden y te deja conversar con todo el acervo para fundamentar tu
            investigación.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <Button asChild size="lg" variant="accent">
              <Link to="/instrumentos/nuevo">
                <Upload /> Subir instrumento
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-hero-foreground/30 bg-hero-foreground/10 text-hero-foreground shadow-none hover:border-hero-foreground/50 hover:bg-hero-foreground/20 hover:text-hero-foreground"
            >
              <Link to="/chat">
                <MessageSquare /> Preguntar al acervo
              </Link>
            </Button>
          </div>
        </motion.div>

        {/* Panel de cifras del acervo */}
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
        >
          <BorderBeam duracion={8} className="shadow-elevated" claseContenido="bg-hero">
            <div className="space-y-6 rounded-[inherit] bg-hero-foreground/[0.06] p-6 sm:p-7">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-hero-muted">Instrumentos en el acervo</p>
                  <p className="mt-1 font-display text-5xl font-bold leading-none text-hero-foreground">
                    {totalInstrumentos === null ? (
                      "—"
                    ) : (
                      <NumberTicker valor={String(totalInstrumentos)} />
                    )}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-hero-muted">KPIs educativos</p>
                  <p className="mt-1 font-display text-3xl font-bold leading-none text-accent">
                    <NumberTicker valor={String(totalKpis)} />
                  </p>
                </div>
              </div>

              <ul className="space-y-4" aria-label="Instrumentos por tipo">
                {conteoTipos.map((c, i) => (
                  <li key={c.tipo} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-semibold text-hero-foreground">{c.tipo}</span>
                      <span className="font-bold tabular-nums text-hero-muted">{c.total}</span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-hero-foreground/10">
                      <motion.div
                        className="h-full rounded-full bg-accent"
                        initial={{ width: 0 }}
                        animate={{ width: `${(c.total / maximo) * 100}%` }}
                        transition={{ duration: 1, delay: 0.4 + i * 0.12, ease: [0.16, 1, 0.3, 1] }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </BorderBeam>
        </motion.div>
      </div>
    </section>
  );
}
