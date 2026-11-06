import { useState } from "react";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TransformacionLimpieza } from "@/types";
import { TablaUbicacion } from "./TablaUbicacion";
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
  const [abierta, setAbierta] = useState<string | null>(null);
  const seleccionada = transformaciones.find(
    (t) => t.regla === abierta && (t.casos?.length ?? 0) > 0,
  );
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
        {transformaciones.map((t) => {
          const conCasos = (t.casos?.length ?? 0) > 0;
          const contenido = (
            <>
              {ETIQUETA_REGLA[t.regla] ?? t.detalle}
              {t.afectados !== null && t.afectados > 0 && (
                <span className="rounded-full bg-primary-soft px-1.5 font-bold tabular-nums text-primary">
                  {t.afectados}
                </span>
              )}
            </>
          );
          const clase =
            "inline-flex items-center gap-1.5 rounded-full border bg-card px-3 py-1 text-xs font-semibold text-foreground";
          return (
            <li key={t.regla} title={t.detalle}>
              {conCasos ? (
                <button
                  type="button"
                  aria-expanded={abierta === t.regla}
                  onClick={() => setAbierta(abierta === t.regla ? null : t.regla)}
                  className={cn(
                    clase,
                    "underline-offset-2 hover:underline",
                    abierta === t.regla ? "border-primary" : "border-border",
                  )}
                >
                  {contenido}
                </button>
              ) : (
                <span className={cn(clase, "border-border")}>{contenido}</span>
              )}
            </li>
          );
        })}
      </ul>
      {transformaciones.some((t) => (t.casos?.length ?? 0) > 0) && !seleccionada && (
        <p className="text-xs text-muted-foreground">
          Haz clic en un cambio para ver exactamente en qué filas se hizo.
        </p>
      )}
      {seleccionada && (
        <div className="space-y-2 rounded-xl bg-card p-3">
          <p className="text-sm text-foreground">{seleccionada.detalle}</p>
          {seleccionada.columnas && Object.keys(seleccionada.columnas).length > 0 && (
            <p className="text-xs text-muted-foreground">
              Por pregunta:{" "}
              {Object.entries(seleccionada.columnas)
                .map(([c, n]) => `${c.length > 50 ? `${c.slice(0, 50)}…` : c} (${n})`)
                .join(" · ")}
            </p>
          )}
          <TablaUbicacion
            celdas={seleccionada.casos ?? []}
            total={seleccionada.afectados ?? undefined}
          />
        </div>
      )}
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
