import type { KpiCatalogo } from "@/types";

interface FichaKpiProps {
  kpi: KpiCatalogo | undefined;
  /** Resumen del mapa, por si el catálogo no está disponible. */
  resumen: string;
}

/** Definición del KPI (qué es, qué mide, cómo se mide, fórmula). */
export function FichaKpi({ kpi, resumen }: FichaKpiProps) {
  if (!kpi) {
    return resumen ? (
      <p className="text-sm leading-relaxed text-muted-foreground">{resumen}</p>
    ) : null;
  }
  const secciones = [
    { titulo: "Qué es", texto: kpi.queEs },
    { titulo: "Qué mide", texto: kpi.queMide },
    { titulo: "Cómo se mide", texto: kpi.comoSeMide },
  ].filter((s) => s.texto);
  return (
    <div className="space-y-4">
      {secciones.map((s) => (
        <section key={s.titulo} className="space-y-1">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            {s.titulo}
          </h3>
          <p className="text-sm leading-relaxed text-foreground">{s.texto}</p>
        </section>
      ))}
      {kpi.formula && (
        <section className="space-y-1">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Fórmula
          </h3>
          <p className="rounded-xl bg-primary-soft px-3 py-2 font-mono text-sm leading-relaxed text-primary">
            {kpi.formula}
          </p>
        </section>
      )}
    </div>
  );
}
