import { ArrowRight, Loader2 } from "lucide-react";
import type { ReporteLimpieza } from "@/types";

interface StepLimpiezaProps {
  reporte: ReporteLimpieza | null;
}

export function StepLimpieza({ reporte }: StepLimpiezaProps) {
  if (!reporte) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" /> Limpiando el archivo…
      </div>
    );
  }
  const contadores = [
    { etiqueta: "Duplicados eliminados", valor: reporte.duplicadosEliminados },
    { etiqueta: "Nulos tratados", valor: reporte.nulosTratados },
    { etiqueta: "Columnas normalizadas", valor: reporte.columnasNormalizadas },
  ];
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        {contadores.map((c) => (
          <div key={c.etiqueta} className="rounded-xl border bg-card p-5 shadow-sm">
            <p className="text-3xl font-bold text-primary">{c.valor}</p>
            <p className="text-sm text-muted-foreground">{c.etiqueta}</p>
          </div>
        ))}
      </div>
      <div className="rounded-xl border bg-card">
        <h3 className="border-b px-5 py-3 font-semibold">Antes → después</h3>
        <ul className="divide-y">
          {reporte.cambios.map((c, i) => (
            <li key={i} className="grid grid-cols-[9rem_1fr_auto_1fr] items-center gap-3 px-5 py-3 text-sm">
              <span className="text-muted-foreground">{c.campo}</span>
              <code className="rounded bg-destructive/10 px-2 py-1 text-destructive line-through">{c.antes}</code>
              <ArrowRight className="size-4 text-muted-foreground" />
              <code className="rounded bg-primary/10 px-2 py-1 text-primary">{c.despues}</code>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
