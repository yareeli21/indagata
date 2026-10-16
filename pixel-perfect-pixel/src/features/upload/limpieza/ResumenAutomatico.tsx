import { Sparkles } from "lucide-react";
import type { TransformacionLimpieza } from "@/types";
import { ETIQUETA_REGLA } from "./textos";

interface ResumenAutomaticoProps {
  transformaciones: TransformacionLimpieza[];
  metricas: Record<string, unknown>;
}

function numero(valor: unknown): number | null {
  return typeof valor === "number" ? valor : null;
}

/** Qué hizo la fase automática y en qué estado llegó el archivo. */
export function ResumenAutomatico({ transformaciones, metricas }: ResumenAutomaticoProps) {
  const completitud = numero(metricas["pct_completitud"]);
  // Las métricas dependen del tipo: tabla (encuestas, pruebas) o texto (entrevistas).
  const datos = [
    { etiqueta: "Filas recibidas", valor: numero(metricas["n_respondentes"]) },
    { etiqueta: "Columnas", valor: numero(metricas["n_columnas"]) },
    {
      etiqueta: "Celdas con dato",
      valor: completitud === null ? null : `${Math.round(completitud * 100)} %`,
    },
    { etiqueta: "Filas duplicadas", valor: numero(metricas["n_duplicados"]) },
    { etiqueta: "Palabras", valor: numero(metricas["n_palabras"]) },
    { etiqueta: "Líneas", valor: numero(metricas["n_lineas"]) },
    { etiqueta: "Ruido detectado", valor: numero(metricas["ruido_detectado"]) },
    { etiqueta: "Alumnos", valor: numero(metricas["n_alumnos"]) },
    { etiqueta: "Preguntas", valor: numero(metricas["n_preguntas"]) },
    { etiqueta: "IDs repetidos", valor: numero(metricas["n_ids_duplicados"]) },
  ].filter((d) => d.valor !== null);

  return (
    <section className="space-y-4 rounded-2xl border border-primary/15 bg-primary-soft/40 p-4 sm:p-5">
      <h3 className="flex items-center gap-2 font-display text-base font-bold text-foreground">
        <Sparkles className="size-5 text-primary" aria-hidden /> Lo que hicimos automáticamente
      </h3>
      <ul className="flex flex-wrap gap-2">
        {transformaciones.map((t) => (
          <li
            key={t.regla}
            title={t.detalle}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-foreground"
          >
            {ETIQUETA_REGLA[t.regla] ?? t.detalle}
            {t.afectados !== null && t.afectados > 0 && (
              <span className="rounded-full bg-primary-soft px-1.5 font-bold tabular-nums text-primary">
                {t.afectados}
              </span>
            )}
          </li>
        ))}
      </ul>
      {datos.length > 0 && (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {datos.map((d) => (
            <div key={d.etiqueta} className="rounded-xl bg-card px-3 py-2">
              <dt className="text-xs font-semibold text-muted-foreground">{d.etiqueta}</dt>
              <dd className="font-display text-lg font-bold tabular-nums text-foreground">
                {d.valor}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <p className="text-xs text-muted-foreground">
        El archivo que subiste no se modifica: trabajamos sobre una copia.
      </p>
    </section>
  );
}
